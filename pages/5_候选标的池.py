import pandas as pd
import streamlit as st

from src.auth import current_user_key, render_user_sidebar, require_user_key
from src.candidate_screener import ASSET_CLASS_DIRECTIONS, screen_candidates_by_direction
from src.database import add_watch_item, fetch_df
from src.utils import format_percent, show_risk_notice
from src.ui_style import apply_global_style
from src.ui_components import page_header


st.set_page_config(page_title="动态候选筛选器", page_icon="📋", layout="wide", initial_sidebar_state="expanded")
apply_global_style()
require_user_key()
render_user_sidebar()


def init_filter_state() -> None:
    st.session_state.setdefault("candidate_asset_class", "宽基指数")
    st.session_state.setdefault("candidate_direction", "沪深300")
    st.session_state.setdefault("candidate_max_results", 10)
    st.session_state.setdefault("candidate_mode", "快速候选池")
    if st.session_state.get("candidate_prefill_from_decision"):
        asset_class = st.session_state.get("candidate_prefill_asset_class", "宽基指数")
        direction = st.session_state.get("candidate_prefill_direction", "沪深300")
        if asset_class in ASSET_CLASS_DIRECTIONS:
            st.session_state["candidate_asset_class"] = asset_class
            if direction in ASSET_CLASS_DIRECTIONS[asset_class]:
                st.session_state["candidate_direction"] = direction
        st.session_state["candidate_prefill_from_decision"] = False


def sync_direction_options() -> None:
    asset_class = st.session_state["candidate_asset_class"]
    options = ASSET_CLASS_DIRECTIONS[asset_class]
    if st.session_state.get("candidate_direction") not in options:
        st.session_state["candidate_direction"] = options[0]


def format_metric(value) -> str:
    if value is None or pd.isna(value):
        return "暂无"
    return format_percent(float(value))


def format_liquidity(value) -> str:
    if value is None or pd.isna(value):
        return "暂无"
    return f"{float(value):,.0f}"


def prefill_analysis(row: dict, source_label: str = "动态候选筛选器") -> None:
    st.session_state["analysis_prefill_code"] = row["代码"]
    st.session_state["analysis_prefill_name"] = row["名称"]
    st.session_state["analysis_prefill_asset_type"] = row["资产大类"]
    st.session_state["analysis_prefill_asset_direction"] = row["方向"]
    st.session_state["analysis_prefill_risk_level"] = row["风险等级"]
    st.session_state["analysis_prefill_preferred_type"] = "自动识别"
    st.session_state["analysis_prefill_from_candidate"] = True
    st.session_state["analysis_prefill_source"] = source_label
    try:
        st.switch_page("pages/6_基金ETF分析.py")
    except Exception:
        st.success("已带入该标的信息。请点击左侧“基金ETF分析”，进入后会自动填入代码。")


def add_candidate_to_watchlist(row: dict) -> None:
    exists = fetch_df("SELECT id FROM watchlist WHERE user_key=? AND code=? LIMIT 1", (current_user_key(), row["代码"]))
    if not exists.empty:
        st.info("该标的已在自选池中。")
        return
    add_watch_item(
        {
            "code": row["代码"],
            "name": row["名称"],
            "asset_type": row["资产大类"],
            "pool_type": "观察池",
            "note": f"动态候选筛选器：{row['方向']}，分类：{row['分类']}。候选观察不等于买入建议。",
            "risk_level": row["风险等级"],
        }
    )
    st.success(f"{row['名称']} 已加入自选池。")


init_filter_state()

page_header(
    "动态候选筛选器",
    "这里不是系统直接给出单只基金配置指令，而是根据资产方向帮你筛出可以进一步观察的基金/ETF。"
    "你需要结合基金ETF分析、自身风险承受能力和长期目标独立决策。"
)
st.info(
    "这个页面用于根据资产方向筛选候选基金/ETF。系统会尽量根据规模或成交额、历史收益、最大回撤、"
    "波动率、夏普比率和数据完整性给出候选观察列表。候选观察不等于买入建议。"
)

c1, c2, c3, c4 = st.columns([1.2, 1.2, 0.8, 1.0])
c1.selectbox("资产大类", list(ASSET_CLASS_DIRECTIONS.keys()), key="candidate_asset_class", on_change=sync_direction_options)
c2.selectbox("具体方向", ASSET_CLASS_DIRECTIONS[st.session_state["candidate_asset_class"]], key="candidate_direction")
c3.number_input("最多显示数量", min_value=3, max_value=20, step=1, key="candidate_max_results")
c4.selectbox("筛选模式", ["快速候选池", "深度动态筛选"], key="candidate_mode")

if st.button("开始筛选候选标的", type="primary"):
    with st.spinner("正在筛选候选标的。快速模式不调用重型行情接口；深度模式可能需要更久。"):
        st.session_state["candidate_last_result"] = screen_candidates_by_direction(
            st.session_state["candidate_asset_class"],
            st.session_state["candidate_direction"],
            max_results=int(st.session_state["candidate_max_results"]),
            mode="deep" if st.session_state.get("candidate_mode") == "深度动态筛选" else "quick",
        )

result = st.session_state.get("candidate_last_result")
if result:
    results_df = result["results"]
    if result["is_fallback"]:
        st.warning(f"{result['message']} 当前为基础示例池，非实时动态筛选。")
    else:
        st.success(result["message"])
    if result.get("errors"):
        with st.expander("数据接口提示"):
            for error in result["errors"]:
                st.write(f"- {error}")

    if results_df.empty:
        st.warning("当前方向暂未筛出候选标的，请换一个方向再试。")
    else:
        display_df = results_df.copy()
        for col in ["近1年收益", "近3年收益", "最大回撤", "年化波动率"]:
            display_df[col] = display_df[col].map(format_metric)
        display_df["夏普比率"] = display_df["夏普比率"].map(lambda x: "暂无" if x is None or pd.isna(x) else f"{float(x):.2f}")
        display_df["成交额/规模"] = display_df["成交额/规模"].map(format_liquidity)
        st.dataframe(
            display_df[
                [
                    "排名",
                    "代码",
                    "名称",
                    "资产大类",
                    "方向",
                    "评分",
                    "分类",
                    "风险等级",
                    "近1年收益",
                    "近3年收益",
                    "最大回撤",
                    "年化波动率",
                    "夏普比率",
                    "成交额/规模",
                    "费用",
                    "数据起始日期",
                    "数据年限",
                    "备注",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("候选标的操作")
        for _, row in results_df.iterrows():
            item = row.to_dict()
            with st.container(border=True):
                left, mid, right = st.columns([2, 3, 2])
                left.write(f"{item['排名']}. {item['代码']} - {item['名称']}")
                mid.write(f"分类：{item['分类']}｜评分：{item['评分']}｜风险：{item['风险等级']}")
                a1, a2 = right.columns(2)
                if a1.button("去分析该标的", key=f"analyze_dynamic_{item['代码']}"):
                    prefill_analysis(item)
                if a2.button("加入自选池", key=f"watch_dynamic_{item['代码']}"):
                    add_candidate_to_watchlist(item)

st.info("结果仅用于个人资产管理辅助分析，不构成投资建议。行业主题类不能作为核心资产，候选观察不等于买入建议。")
show_risk_notice()
