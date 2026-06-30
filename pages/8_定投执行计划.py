from datetime import date

import pandas as pd
import streamlit as st

from src.auth import render_user_sidebar, require_user_key
from src.database import (
    load_latest_monthly_decision_record,
    load_latest_decision_profile,
    load_recent_trade_records,
    save_trade_record,
    update_holding_from_trade,
)
from src.decision_engine import ASSET_LABELS, TARGET_RANGES
from src.execution_plan import generate_dca_execution_plan
from src.rebalance_engine import generate_rebalance_suggestions
from src.utils import format_currency, translate_columns
from src.ui_style import apply_global_style
from src.ui_components import info_box, metric_card, page_header


st.set_page_config(page_title="定投执行计划", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
apply_global_style()
require_user_key()
render_user_sidebar()


ASSET_KEY_BY_LABEL = {value: key for key, value in ASSET_LABELS.items()}
TRADE_ASSET_OPTIONS = list(ASSET_LABELS.values())


def _asset_amounts_from_profile(profile: dict) -> dict[str, float]:
    return {
        "cash": float(profile.get("cash_amount", 0.0) or 0.0),
        "bond": float(profile.get("bond_amount", 0.0) or 0.0),
        "broad_index": float(profile.get("broad_index_amount", 0.0) or 0.0),
        "global_index": float(profile.get("global_index_amount", 0.0) or 0.0),
        "sector_theme": float(profile.get("sector_theme_amount", 0.0) or 0.0),
        "active_fund": float(profile.get("active_fund_amount", 0.0) or 0.0),
        "stock": float(profile.get("stock_amount", 0.0) or 0.0),
        "quant_experiment": float(profile.get("quant_experiment_amount", 0.0) or 0.0),
    }


def _avoid_texts(avoid_list) -> list[str]:
    texts = []
    for item in avoid_list or []:
        if isinstance(item, dict):
            asset = item.get("资产类别") or item.get("资产") or item.get("asset") or item.get("asset_name") or item.get("name") or ""
            reason = item.get("原因") or item.get("reason") or ""
            texts.append(f"{asset}：{reason}" if reason else str(asset or item))
        else:
            texts.append(str(item))
    return [text for text in texts if text and text != "None"]


def _latest_decision() -> dict | None:
    try:
        return load_latest_monthly_decision_record()
    except Exception as exc:
        st.error(f"读取最新本月投资决策失败：{exc}")
        st.exception(exc)
        return None


def _positive_allocations(allocations: dict) -> dict[str, float]:
    clean = {}
    for key, value in (allocations or {}).items():
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount > 0:
            clean[key] = amount
    return clean


def _render_plan_result(plan: dict, avoid_texts: list[str], auto_generate_checklist: bool) -> None:
    st.subheader("本月定投执行计划")
    info_box(plan.get("summary", "已生成本月定投执行计划。"), "info")
    if plan.get("execution_dates"):
        st.write("建议执行日期：" + "、".join(plan["execution_dates"]))

    steps = plan.get("allocation_steps", [])
    if steps and auto_generate_checklist:
        step_df = pd.DataFrame(steps).rename(columns={"date": "执行日期", "asset_name": "资产类别", "amount": "金额"})
        display_df = step_df[["执行日期", "资产类别", "金额"]].assign(金额=step_df["金额"].map(format_currency))
        st.dataframe(display_df, width="stretch", hide_index=True)
    elif steps:
        st.info("已关闭自动执行清单。你仍可以根据上方建议日期和金额手动记录。")
    else:
        st.info("本月暂时没有可执行步骤。")

    st.write("执行提醒")
    st.write("- 不需要预测当天涨跌。")
    st.write("- 不建议因为当天市场上涨或下跌就临时改变计划。")
    st.write("- 如果心理压力较大，可以分批执行，降低一次性买入的压力。")

    if plan.get("skip_rules") or avoid_texts:
        st.subheader("本月暂不建议")
        for item in list(dict.fromkeys(plan.get("skip_rules", []) + avoid_texts)):
            st.warning(item)

    for warning in plan.get("warnings", []):
        st.info(warning)


page_header("定投执行计划", "把本月资产配置建议转成执行日期、分批金额和交易记录，不预测短期涨跌。")

profile = load_latest_decision_profile()
decision = _latest_decision()

if decision:
    decision_input = decision.get("input_json", {})
    decision_result = decision.get("result_json", {})
    info_box(f"已读取最新本月投资决策：{decision.get('decision_month')}，生成时间：{decision.get('created_at')}", "success")
else:
    decision_input = profile
    decision_result = {}
    info_box("请先在本月投资决策中心生成本月投资决策。", "warning")
    st.page_link("pages/2_本月投资决策中心.py", label="去本月投资决策中心", icon="➡️")

monthly_investment = float(decision_input.get("monthly_investment", profile.get("monthly_investment", 0.0)) or 0.0)
recommended_allocations = _positive_allocations(decision_result.get("recommended_allocations") or {})

emergency_fund = float(decision_input.get("emergency_fund", profile.get("emergency_fund", 0.0)) or 0.0)
monthly_expense = float(decision_input.get("monthly_expense", profile.get("monthly_expense", 0.0)) or 0.0)
risk_preference = decision_input.get("risk_preference", profile.get("risk_preference", "稳健")) or "稳健"
current_allocation = _asset_amounts_from_profile(profile)
avoid_texts = _avoid_texts(decision_result.get("avoid_list", []))
latest_decision_found = decision is not None

st.subheader("本月建议概览")
overview1, overview2, overview3, overview4 = st.columns(4)
with overview1:
    metric_card("本月可投资金额", format_currency(monthly_investment), "来自最新月度决策", "positive")
with overview2:
    metric_card("当前备用金", format_currency(emergency_fund), "现金安全垫")
with overview3:
    metric_card("月支出", format_currency(monthly_expense), "用于判断安全垫")
with overview4:
    metric_card("风险偏好", risk_preference, "执行计划会保持克制")

if recommended_allocations:
    alloc_rows = [
        {"资产类别": ASSET_LABELS.get(key, key), "建议金额": amount}
        for key, amount in recommended_allocations.items()
        if float(amount or 0) > 0
    ]
    if alloc_rows:
        alloc_df = pd.DataFrame(alloc_rows)
        st.dataframe(alloc_df.assign(建议金额=alloc_df["建议金额"].map(format_currency)), width="stretch", hide_index=True)
    else:
        st.info("当前建议分配金额为 0，暂时没有需要执行的投入。")
else:
    st.info("当前没有可执行的建议分配。")

st.subheader("执行参数")
with st.form("execution_plan_form"):
    manual_mode = False
    manual_allocations = {}
    form_monthly_investment = monthly_investment
    if not latest_decision_found:
        manual_mode = st.checkbox(
            "没有读取到本月投资决策，手动输入本月计划投入金额",
            value=True,
            key="dca_manual_mode",
        )
        if manual_mode:
            st.caption("手动模式只生成基础执行清单。后续仍建议先在“本月投资决策中心”生成完整月度决策。")
            m1, m2, m3 = st.columns(3)
            form_monthly_investment = m1.number_input(
                "本月计划投入金额",
                min_value=0.0,
                value=max(monthly_investment, 0.0),
                step=100.0,
                key="dca_manual_monthly_investment",
            )
            manual_allocations["cash"] = m2.number_input("现金/货币基金金额", min_value=0.0, value=0.0, step=100.0, key="dca_manual_cash")
            manual_allocations["broad_index"] = m3.number_input("宽基指数金额", min_value=0.0, value=max(form_monthly_investment, 0.0), step=100.0, key="dca_manual_broad")
            m4, m5, m6 = st.columns(3)
            manual_allocations["bond"] = m4.number_input("债券/短债金额", min_value=0.0, value=0.0, step=100.0, key="dca_manual_bond")
            manual_allocations["global_index"] = m5.number_input("海外指数金额", min_value=0.0, value=0.0, step=100.0, key="dca_manual_global")
            manual_allocations["sector_theme"] = m6.number_input("行业主题金额", min_value=0.0, value=0.0, step=100.0, key="dca_manual_sector")

    c1, c2, c3 = st.columns(3)
    salary_day = c1.number_input("工资到账日", min_value=1, max_value=28, value=10, step=1, key="dca_salary_day")
    execution_mode = c2.selectbox("定投执行方式", ["自动匹配", "工资到账后一次性投", "分两次投", "分三次投"], key="dca_execution_mode")
    offset_label = c3.selectbox("默认定投执行日", ["工资到账后第 1 天", "工资到账后第 2 天", "工资到账后第 3 天"], key="dca_offset_label")
    d1, d2, d3 = st.columns(3)
    allow_volatility_split = d1.toggle("市场波动较大时允许分批", value=True, key="dca_allow_volatility_split")
    min_single_amount = d2.number_input("单笔最小投入金额", min_value=0.0, value=100.0, step=100.0, key="dca_min_single_amount")
    auto_generate_checklist = d3.toggle("自动生成执行清单", value=True, key="dca_auto_generate_checklist")
    submitted = st.form_submit_button("生成定投执行计划", type="primary", key="generate_dca_plan_btn")

if submitted:
    st.session_state["dca_plan_button_clicked"] = True
elif "dca_plan_button_clicked" not in st.session_state:
    st.session_state["dca_plan_button_clicked"] = False
debug_error = None
debug_result = st.session_state.get("dca_plan_result")

if submitted:
    try:
        offset_days = int(offset_label.split("第 ")[1].split(" 天")[0])
        plan_monthly_investment = float(form_monthly_investment or 0)
        plan_allocations = _positive_allocations(manual_allocations if manual_mode else recommended_allocations)

        if not latest_decision_found:
            st.warning("请先在本月投资决策中心生成本月投资决策。")
            st.session_state["dca_plan_generated"] = False
            st.session_state["dca_plan_result"] = None
        elif plan_monthly_investment <= 0:
            st.warning("本月可投资金额为 0，无法生成定投计划。")
            st.session_state["dca_plan_generated"] = False
            st.session_state["dca_plan_result"] = None
        elif not plan_allocations:
            st.warning("没有可执行的资产分配金额，无法生成定投计划。")
            st.session_state["dca_plan_generated"] = False
            st.session_state["dca_plan_result"] = None
        else:
            result = generate_dca_execution_plan(
                monthly_investment=plan_monthly_investment,
                recommended_allocations=plan_allocations,
                salary_day=int(salary_day),
                execution_mode=execution_mode,
                emergency_fund=emergency_fund,
                monthly_expense=monthly_expense,
                risk_preference=risk_preference,
                current_allocation=current_allocation,
                execution_offset_days=offset_days,
                allow_volatility_split=allow_volatility_split,
                min_single_amount=min_single_amount,
            )
            st.session_state["dca_plan_generated"] = True
            st.session_state["dca_plan_result"] = result
            st.session_state["dca_plan_error"] = ""
            st.session_state["dca_plan_context"] = {
                "latest_decision_found": latest_decision_found,
                "monthly_investment": plan_monthly_investment,
                "recommended_allocations": plan_allocations,
                "execution_mode": execution_mode,
                "salary_day": int(salary_day),
                "auto_generate_checklist": bool(auto_generate_checklist),
                "manual_mode": bool(manual_mode),
            }
            debug_result = result
            st.success("已生成本月定投执行计划。")
    except Exception as exc:
        debug_error = str(exc)
        st.session_state["dca_plan_generated"] = False
        st.session_state["dca_plan_error"] = debug_error
        st.error(f"生成定投执行计划失败：{exc}")
        st.exception(exc)

if st.session_state.get("dca_plan_generated"):
    result = st.session_state.get("dca_plan_result") or {}
    context = st.session_state.get("dca_plan_context") or {}
    _render_plan_result(result, avoid_texts, bool(context.get("auto_generate_checklist", True)))
else:
    st.info("设置参数后点击“生成定投执行计划”，这里会显示本月执行日期、资产类别和金额。")

st.subheader("卖出 / 再平衡规则")
rebalance = generate_rebalance_suggestions(
    current_allocation=current_allocation,
    target_allocation=decision_result.get("target_ranges") or TARGET_RANGES.get(risk_preference),
    emergency_fund=emergency_fund,
    monthly_expense=monthly_expense,
    risk_preference=risk_preference,
    holdings=[],
)
if rebalance["rebalance_needed"]:
    st.write("当前需要关注资产比例是否偏离。建议先暂停继续加仓超配资产，用新增资金补低配资产；如果超配严重，再考虑分批减仓。")
else:
    st.write("当前不建议因为短期波动卖出。优先按本月新增资金补低配资产。")

col_a, col_b = st.columns(2)
with col_a:
    st.write("优先买入 / 补充")
    for item in rebalance["buy_suggestions"]:
        st.write(f"- {item}")
with col_b:
    st.write("卖出 / 降低仓位")
    for item in rebalance["sell_suggestions"]:
        st.write(f"- {item}")

for text in rebalance["warnings"]:
    st.warning(text)
for text in rebalance["explanation"]:
    st.write(f"- {text}")

st.info("卖出和再平衡应基于资产比例、风险控制和个人目标变化，不应只因为短期涨跌做决定。")

st.subheader("记录本月执行结果")
with st.form("trade_record_form"):
    t1, t2, t3 = st.columns(3)
    trade_date = t1.date_input("实际执行日期", value=date.today())
    asset_label = t2.selectbox("实际买入资产类别", TRADE_ASSET_OPTIONS)
    action = t3.selectbox("动作", ["定投", "买入", "卖出", "调整"])
    r1, r2, r3 = st.columns(3)
    code = r1.text_input("标的代码")
    name = r2.text_input("标的名称")
    amount = r3.number_input("实际买入金额", min_value=0.0, value=0.0, step=100.0)
    note = st.text_area("备注", value="按本月定投执行计划记录。")
    update_holding = st.checkbox("同步更新持仓池金额", value=True, help="买入或定投会增加持仓池中对应标的金额。")
    save_trade = st.form_submit_button("记录本月执行结果", type="primary")

if save_trade:
    record = {
        "trade_date": trade_date.isoformat(),
        "code": code.strip(),
        "name": name.strip() or code.strip(),
        "asset_type": asset_label,
        "action": action,
        "amount": amount,
        "note": note,
    }
    try:
        save_trade_record(record)
        if update_holding:
            update_holding_from_trade(record)
        st.success("执行结果已记录。后续 AI 月报会读取这些交易记录。")
        st.rerun()
    except Exception as exc:
        st.error(f"保存执行记录失败：{exc}")

recent_trades = load_recent_trade_records(20)
st.subheader("最近执行记录")
if recent_trades.empty:
    st.info("还没有执行记录。")
else:
    table = translate_columns(recent_trades)
    if "金额" in table.columns:
        table["金额"] = table["金额"].map(format_currency)
    st.dataframe(table, width="stretch", hide_index=True)

with st.expander("高级调试：定投计划生成状态"):
    context = st.session_state.get("dca_plan_context") or {}
    st.write(
        {
            "是否点击生成按钮": st.session_state.get("dca_plan_button_clicked", False),
            "是否读取到最新本月决策记录": latest_decision_found,
            "monthly_investment": context.get("monthly_investment", monthly_investment),
            "recommended_allocations": context.get("recommended_allocations", recommended_allocations),
            "execution_mode": context.get("execution_mode", st.session_state.get("dca_execution_mode")),
            "salary_day": context.get("salary_day", st.session_state.get("dca_salary_day")),
            "generate_dca_execution_plan 返回结果": st.session_state.get("dca_plan_result"),
            "错误信息": debug_error or st.session_state.get("dca_plan_error", ""),
        }
    )

st.warning("定投计划仅用于帮助你执行长期资产配置，不代表未来收益，也不构成投资建议。请结合自身收入、支出、风险承受能力独立决策。")
