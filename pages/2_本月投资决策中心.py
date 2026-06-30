import json

import pandas as pd
import plotly.express as px
import streamlit as st

from src.auth import current_user_key, render_user_sidebar, require_user_key
from src.database import (
    fetch_df,
    get_decision_record_by_id,
    load_latest_decision_profile,
    load_monthly_decision_records,
    save_monthly_decision_record,
)
from src.decision_engine import ASSET_LABELS, generate_monthly_investment_plan
from src.state_manager import (
    DECISION_FIELD_KEYS,
    clear_decision_state,
    get_decision_state_as_profile,
    init_decision_state,
    load_decision_state_from_database,
    reset_decision_state_to_default,
    save_decision_state,
)
from src.utils import CHINESE_COLUMN_MAP, format_currency, format_percent, show_risk_notice
from src.ui_style import apply_global_style
from src.ui_components import info_box, metric_card, page_header


st.set_page_config(page_title="本月投资决策中心", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
apply_global_style()
require_user_key()
render_user_sidebar()

FIELD_KEYS = {
    "profile_name": "decision_profile_name",
    "current_age": "decision_current_age",
    "target_age": "decision_target_age",
    "target_asset": "decision_target_asset",
    "total_asset": "decision_total_asset",
    "emergency_fund": "decision_emergency_fund",
    "monthly_expense": "decision_monthly_expense",
    "monthly_investment": "decision_monthly_investment",
    "cash_amount": "decision_cash_amount",
    "bond_amount": "decision_bond_amount",
    "broad_index_amount": "decision_broad_index_amount",
    "global_index_amount": "decision_global_index_amount",
    "sector_theme_amount": "decision_sector_theme_amount",
    "active_fund_amount": "decision_active_fund_amount",
    "stock_amount": "decision_stock_amount",
    "quant_experiment_amount": "decision_quant_experiment_amount",
    "risk_preference": "decision_risk_preference",
}

RISK_OPTIONS = ["保守", "稳健", "稳健偏进取", "激进"]


def mark_decision_dirty() -> None:
    st.session_state["decision_data_dirty"] = True


def current_profile_from_session() -> dict:
    return get_decision_state_as_profile()


def reset_session_to_default() -> None:
    reset_decision_state_to_default()


def go_to_candidate_screener(asset_class: str, direction: str) -> None:
    st.session_state["candidate_prefill_asset_class"] = asset_class
    st.session_state["candidate_prefill_direction"] = direction
    st.session_state["candidate_prefill_from_decision"] = True
    try:
        st.switch_page("pages/5_候选标的池.py")
    except Exception:
        st.success("已设置筛选方向。请点击左侧“动态候选筛选器”查看。")


def summarize_action_items(action_json: str) -> str:
    try:
        items = json.loads(action_json or "[]")
        if isinstance(items, list) and items:
            return items[0]
    except Exception:
        pass
    return "暂无摘要"


def render_dict_as_chinese_table(data: dict) -> None:
    rows = []
    for key, value in (data or {}).items():
        label = CHINESE_COLUMN_MAP.get(key, ASSET_LABELS.get(key, key))
        if isinstance(value, (dict, list)):
            display_value = json.dumps(value, ensure_ascii=False)
        else:
            display_value = "" if value is None else str(value)
        rows.append({"项目": label, "内容": display_value})
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("暂无数据。")


def aggregate_holdings_to_profile() -> tuple[dict, list[str]]:
    df = fetch_df("SELECT asset_type, current_value FROM asset_records WHERE user_key=?", (current_user_key(),))
    if df.empty:
        return {}, ["持仓池暂无资产，无法汇总。"]

    mapping = {
        "现金/货币基金": "cash_amount",
        "债券/短债": "bond_amount",
        "宽基指数基金/ETF": "broad_index_amount",
        "海外/全球指数": "global_index_amount",
        "海外/全球 ETF": "global_index_amount",
        "行业基金/主题ETF": "sector_theme_amount",
        "行业基金/主题 ETF": "sector_theme_amount",
        "主动基金": "active_fund_amount",
        "个股": "stock_amount",
        "量化实验仓": "quant_experiment_amount",
    }
    result = {field: 0.0 for field in FIELD_KEYS if field.endswith("_amount")}
    unknown = []
    for _, row in df.iterrows():
        asset_type = str(row.get("asset_type", ""))
        amount = float(row.get("current_value") or 0)
        field = mapping.get(asset_type)
        if field:
            result[field] += amount
        else:
            unknown.append(asset_type)
    result["total_asset"] = sum(result.values())
    return result, list(dict.fromkeys(unknown))


def render_plan(plan: dict, monthly_investment: float, asset_amounts: dict) -> None:
    st.subheader("本月资金分配建议")
    st.write(f"你本月可投资金额为 {format_currency(monthly_investment)}。下面是按当前目标、备用金和资产结构生成的辅助方案。")
    alloc_rows = []
    for key, amount in plan["recommended_allocations"].items():
        alloc_rows.append({"资产方向": ASSET_LABELS[key], "建议金额": amount, "建议比例": amount / monthly_investment if monthly_investment else 0})
    if alloc_rows:
        alloc_df = pd.DataFrame(alloc_rows)
        show_df = alloc_df.copy()
        show_df["建议金额"] = show_df["建议金额"].map(format_currency)
        show_df["建议比例"] = show_df["建议比例"].map(format_percent)
        st.dataframe(show_df, width="stretch", hide_index=True)
        fig = px.pie(alloc_df, names="资产方向", values="建议金额", title="本月建议分配比例")
        fig.update_layout(paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14", font_color="#CBD5E1", legend_title_text="资产方向")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("本月可投资金额为 0，建议先确认现金流。")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("资产配置状态", plan["allocation_health"], "组合健康度")
    with c2:
        metric_card("是否先补备用金", "是" if plan["should_fill_emergency_fund_first"] else "否", "现金安全垫优先级", "warning" if plan["should_fill_emergency_fund_first"] else "positive")
    with c3:
        metric_card("个股观察仓", "可少量观察" if plan["can_open_stock_watch"] else "暂不优先", "控制单一波动")
    with c4:
        metric_card("量化实验仓", "可少量实验" if plan["can_open_quant_experiment"] else "暂不优先", "不影响核心计划")

    st.subheader("本月优先补哪类资产")
    if plan["priority_list"]:
        priority_df = pd.DataFrame(
            [
                {"优先顺序": idx + 1, "资产类别": item["资产类别"], "当前占比": format_percent(item["当前占比"]), "原因": item["原因"]}
                for idx, item in enumerate(plan["priority_list"][:5])
            ]
        )
        st.dataframe(priority_df, width="stretch", hide_index=True)

    st.subheader("本月暂时不要加仓")
    if plan["avoid_list"]:
        st.dataframe(pd.DataFrame(plan["avoid_list"]), width="stretch", hide_index=True)
    else:
        st.success("没有明显超标或不适合加仓的类别。")

    st.subheader("当前资产结构")
    weight_rows = [{"资产类别": ASSET_LABELS[key], "当前金额": asset_amounts[key], "当前占比": plan["weights"].get(key, 0)} for key in ASSET_LABELS]
    weights_df = pd.DataFrame(weight_rows)
    chart_df = weights_df[weights_df["当前金额"] > 0]
    if not chart_df.empty:
        fig = px.pie(chart_df, names="资产类别", values="当前金额", title="当前资产配置")
        fig.update_layout(paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14", font_color="#CBD5E1", legend_title_text="资产类别")
        st.plotly_chart(fig, width="stretch")
    display_weights = weights_df.copy()
    display_weights["当前金额"] = display_weights["当前金额"].map(format_currency)
    display_weights["当前占比"] = display_weights["当前占比"].map(format_percent)
    st.dataframe(display_weights, width="stretch", hide_index=True)

    st.subheader("本月行动清单")
    for idx, item in enumerate(plan["action_items"], start=1):
        st.write(f"{idx}. {item}")

    st.subheader("下一步去看哪些候选池")
    priority_names = [item["资产类别"] for item in plan["priority_list"][:3]]
    st.caption("本月建议优先查看的不是单只标的，而是对应资产方向下的一组候选观察范围。")
    if any("现金" in name for name in priority_names):
        if st.button("去筛选现金/货币基金候选标的"):
            go_to_candidate_screener("现金/货币基金", "货币基金")
    if any("债券" in name or "短债" in name for name in priority_names):
        if st.button("去筛选债券/短债候选标的"):
            go_to_candidate_screener("债券/短债", "短债")
    if any("宽基" in name for name in priority_names):
        st.write("本月建议优先查看：宽基指数 -> 沪深300 / 中证500 / 中证A500")
        if st.button("去筛选宽基候选标的"):
            go_to_candidate_screener("宽基指数", "沪深300")
    if any("海外" in name or "全球" in name for name in priority_names):
        if st.button("去筛选全球/海外指数候选标的"):
            go_to_candidate_screener("全球/海外指数", "标普500")

    st.subheader("原因说明")
    for text in dict.fromkeys(plan["explanation"]):
        st.write(f"- {text}")
    for warning in dict.fromkeys(plan["warnings"]):
        info_box(warning, "warning")
    info_box(plan["risk_notice"], "danger")


try:
    init_decision_state()
    if st.session_state.get("decision_risk_preference") not in RISK_OPTIONS:
        st.session_state["decision_risk_preference"] = "稳健"
except Exception as exc:
    st.error(f"加载配置失败：{exc}")
    reset_session_to_default()
    st.warning("已临时使用统一默认配置，避免输入框显示错误的最小值。请检查数据库后重新加载。")

page_header("本月投资决策中心", "根据目标、备用金、当前资产结构和风险偏好，生成本月资金分配建议。")

if st.session_state.get("decision_profile_is_default"):
    info_box("你正在使用默认配置，请填写后保存。", "warning")
else:
    info_box(f"已加载上次保存配置，更新时间：{st.session_state.get('decision_profile_updated_at')}", "success")
if st.session_state.get("decision_data_dirty"):
    info_box("当前会话中已修改，尚未保存。切换页面不会丢失当前会话数据，但关闭程序前请保存。", "warning")
else:
    info_box("当前配置已保存。切换页面不会丢失已保存数据。", "info")

top1, top2, top3, top4, top5 = st.columns(5)
if top1.button("保存当前配置", type="primary"):
    try:
        save_decision_state()
        st.success("当前配置已保存。")
    except Exception as exc:
        st.error(f"保存配置失败：{exc}")
if top2.button("重置为默认值"):
    reset_session_to_default()
    st.info("已重置为默认配置，尚未保存到数据库。")
if top3.button("从本地数据库重新加载"):
    try:
        clear_decision_state()
        load_decision_state_from_database()
        st.success("已从本地数据库重新加载。")
        st.rerun()
    except Exception as exc:
        st.error(f"从本地数据库重新加载失败：{exc}")
if top4.button("从持仓池汇总当前资产"):
    summary, unknown_types = aggregate_holdings_to_profile()
    if summary:
        for field, value in summary.items():
            if field in FIELD_KEYS:
                st.session_state[FIELD_KEYS[field]] = value
        st.session_state["decision_data_dirty"] = True
        st.success("已从持仓池汇总当前资产。请确认后点击“保存当前配置”。")
    if unknown_types:
        st.warning("以下持仓类型暂时无法完整分类：" + "、".join(unknown_types))
if top5.button("查看历史决策记录"):
    st.session_state["show_decision_history"] = True

st.subheader("基础目标")
c1, c2, c3, c4 = st.columns(4)
c1.number_input("当前年龄", min_value=0, max_value=100, step=1, key="decision_current_age", on_change=mark_decision_dirty)
c2.number_input("目标年龄", min_value=0, max_value=100, step=1, key="decision_target_age", on_change=mark_decision_dirty)
c3.number_input("目标资产", min_value=0.0, step=10_000.0, key="decision_target_asset", on_change=mark_decision_dirty)
c4.selectbox("风险偏好", RISK_OPTIONS, key="decision_risk_preference", on_change=mark_decision_dirty)

st.subheader("本月现金流和安全垫")
f1, f2, f3, f4 = st.columns(4)
f1.number_input("当前总资产", min_value=0.0, step=1_000.0, key="decision_total_asset", on_change=mark_decision_dirty)
f2.number_input("当前备用金", min_value=0.0, step=500.0, key="decision_emergency_fund", on_change=mark_decision_dirty)
f3.number_input("月支出", min_value=0.0, step=100.0, key="decision_monthly_expense", on_change=mark_decision_dirty)
f4.number_input("本月可投资金额", min_value=0.0, step=100.0, key="decision_monthly_investment", on_change=mark_decision_dirty)

st.subheader("当前资产结构")
a1, a2, a3, a4 = st.columns(4)
a1.number_input("当前现金/货币基金金额", min_value=0.0, step=500.0, key="decision_cash_amount", on_change=mark_decision_dirty)
a2.number_input("当前债券/短债金额", min_value=0.0, step=500.0, key="decision_bond_amount", on_change=mark_decision_dirty)
a3.number_input("当前宽基指数基金/ETF金额", min_value=0.0, step=500.0, key="decision_broad_index_amount", on_change=mark_decision_dirty)
a4.number_input("当前海外/全球指数金额", min_value=0.0, step=500.0, key="decision_global_index_amount", on_change=mark_decision_dirty)
b1, b2, b3, b4 = st.columns(4)
b1.number_input("当前行业基金/主题ETF金额", min_value=0.0, step=500.0, key="decision_sector_theme_amount", on_change=mark_decision_dirty)
b2.number_input("当前主动基金金额", min_value=0.0, step=500.0, key="decision_active_fund_amount", on_change=mark_decision_dirty)
b3.number_input("当前个股金额", min_value=0.0, step=500.0, key="decision_stock_amount", on_change=mark_decision_dirty)
b4.number_input("当前量化实验仓金额", min_value=0.0, step=500.0, key="decision_quant_experiment_amount", on_change=mark_decision_dirty)

asset_amounts = {
    "cash": st.session_state["decision_cash_amount"],
    "bond": st.session_state["decision_bond_amount"],
    "broad_index": st.session_state["decision_broad_index_amount"],
    "global_index": st.session_state["decision_global_index_amount"],
    "sector_theme": st.session_state["decision_sector_theme_amount"],
    "active_fund": st.session_state["decision_active_fund_amount"],
    "stock": st.session_state["decision_stock_amount"],
    "quant_experiment": st.session_state["decision_quant_experiment_amount"],
}

if st.button("生成本月投资决策", type="primary"):
    try:
        input_data = current_profile_from_session()
        required_fields = [
            "current_age",
            "target_age",
            "target_asset",
            "total_asset",
            "monthly_expense",
            "monthly_investment",
        ]
        if any(float(input_data.get(field) or 0) <= 0 for field in required_fields):
            st.warning("请先填写基础目标、月支出、本月可投资金额和当前资产结构，再生成本月投资决策。")
        else:
            plan = generate_monthly_investment_plan(
                current_age=input_data["current_age"],
                target_age=input_data["target_age"],
                target_asset=input_data["target_asset"],
                total_asset=input_data["total_asset"],
                emergency_fund=input_data["emergency_fund"],
                monthly_expense=input_data["monthly_expense"],
                monthly_investment=input_data["monthly_investment"],
                asset_amounts=asset_amounts,
                risk_preference=input_data["risk_preference"],
            )
            save_decision_state()
            save_monthly_decision_record(input_data, plan)
            st.session_state["last_decision_plan"] = plan
            st.success("本月决策记录已保存。")
            render_plan(plan, float(input_data["monthly_investment"] or 0), asset_amounts)
    except Exception as exc:
        st.error(f"生成或保存决策失败：{exc}")
elif "last_decision_plan" in st.session_state:
    render_plan(st.session_state["last_decision_plan"], float(st.session_state["decision_monthly_investment"] or 0), asset_amounts)

st.subheader("历史决策记录")
try:
    records = load_monthly_decision_records(limit=12)
    if records.empty:
        st.info("还没有历史决策记录。点击“生成本月投资决策”后会自动保存。")
    else:
        table = records.copy()
        table["主要建议"] = table["action_items"].map(summarize_action_items)
        table = table.rename(
            columns={
                "id": "ID",
                "decision_month": "月份",
                "total_asset": "总资产",
                "monthly_investment": "本月可投资金额",
                "risk_preference": "风险偏好",
                "created_at": "创建时间",
            }
        )
        st.dataframe(table[["ID", "月份", "总资产", "本月可投资金额", "风险偏好", "主要建议", "创建时间"]], width="stretch", hide_index=True)
        record_id = st.selectbox("查看详情", records["id"].astype(int).tolist(), key="decision_history_record_id")
        detail = get_decision_record_by_id(int(record_id))
        if detail:
            st.write("当时输入的数据")
            render_dict_as_chinese_table(detail["input_json"])
            result = detail["result_json"]
            allocations = result.get("recommended_allocations", {})
            if allocations:
                st.write("当时生成的本月资金分配建议")
                alloc_df = pd.DataFrame(
                    [
                        {"资产方向": ASSET_LABELS.get(key, key), "建议金额": format_currency(amount)}
                        for key, amount in allocations.items()
                    ]
                )
                st.dataframe(alloc_df, width="stretch", hide_index=True)
            if detail.get("action_items"):
                st.write("行动清单")
                for idx, item in enumerate(detail["action_items"], start=1):
                    st.write(f"{idx}. {item}")
            if detail.get("warnings"):
                st.write("风险提示")
                for item in detail["warnings"]:
                    st.warning(item)
            if detail.get("explanation"):
                st.write("原因说明")
                for item in detail["explanation"]:
                    st.write(f"- {item}")
except Exception as exc:
    st.error(f"读取历史决策记录失败：{exc}")

with st.expander("高级调试：当前加载的数据"):
    try:
        database_profile = load_latest_decision_profile()
    except Exception as exc:
        database_profile = {"读取数据库失败": str(exc)}
    session_profile = {key: st.session_state.get(key) for key in DECISION_FIELD_KEYS.values()}
    widget_values = {
        field: {
            "输入框 key": key,
            "当前值": st.session_state.get(key),
        }
        for field, key in DECISION_FIELD_KEYS.items()
    }
    st.write("数据库读取结果")
    st.json(database_profile)
    st.write("当前 session_state 里的 decision_* 数据")
    st.json(session_profile)
    st.write("当前输入框实际使用的 key 和数值")
    st.json(widget_values)

show_risk_notice()
