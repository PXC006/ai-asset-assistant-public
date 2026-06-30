import hashlib
import json

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from src.config import APP_VERSION
except Exception:
    APP_VERSION = "unknown-version"
from src.auth import current_user_key
from src.database import add_watch_item, fetch_df
from src.data_fetcher import build_consistency_report, fetch_asset_data_with_cache, infer_asset_type_by_code
from src.fund_analyzer import analyze_fund_dataframe
from src.utils import format_percent, show_risk_notice
from src.ui_style import apply_global_style
from src.ui_components import page_header


st.set_page_config(page_title="基金ETF分析", page_icon="🔎", layout="wide", initial_sidebar_state="expanded")
apply_global_style()

EXAMPLES = {
    "宽基ETF｜沪深300ETF示例 510300": ("510300", "沪深300ETF示例", "宽基ETF"),
    "宽基ETF｜中证500ETF示例 510500": ("510500", "中证500ETF示例", "宽基ETF"),
    "债券/短债｜国债ETF示例 511010": ("511010", "国债ETF示例", "债券/短债"),
    "红利低波｜红利ETF示例 510880": ("510880", "红利ETF示例", "红利低波"),
    "海外ETF｜标普500ETF示例 513500": ("513500", "标普500ETF示例", "海外ETF"),
    "行业主题｜芯片ETF示例 512760": ("512760", "芯片ETF示例", "行业主题"),
    "普通基金｜开放式基金示例 005827": ("005827", "开放式基金示例", "普通基金"),
    "LOF/场内基金｜白酒LOF示例 161725": ("161725", "白酒LOF示例", "LOF/场内基金"),
    "美股ETF｜SPY": ("SPY", "SPY", "美股ETF"),
    "美股ETF｜QQQ": ("QQQ", "QQQ", "美股ETF"),
}

SCOPE_OPTIONS = ["自动识别", "ETF 场内行情", "LOF / 场内基金行情", "开放式基金净值", "A 股股票行情", "美股 / 海外 ETF"]
LEGACY_SCOPE_MAP = {
    "中国ETF": "ETF 场内行情",
    "中国LOF": "LOF / 场内基金行情",
    "中国开放式基金": "开放式基金净值",
    "中国股票": "A 股股票行情",
    "美股ETF": "美股 / 海外 ETF",
}


@st.cache_data(ttl=21600, show_spinner=False)
def load_strict_asset_data(code: str, scope: str, app_version: str, force_refresh: bool = False):
    return fetch_asset_data_with_cache(code, analysis_scope=scope, force_refresh=force_refresh, strict=True)


def metrics_hash(analysis: dict) -> str:
    clean = {}
    for key, value in (analysis or {}).items():
        if isinstance(value, float):
            clean[key] = round(value, 10)
        else:
            clean[key] = value
    payload = json.dumps(clean, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def init_fund_analysis_state() -> None:
    st.session_state.setdefault("fund_analysis_code", "")
    st.session_state.setdefault("fund_analysis_name", "")
    st.session_state.setdefault("fund_analysis_scope", "自动识别")
    st.session_state.setdefault("fund_analysis_example", "手动输入")

    prefill_code = st.session_state.get("analysis_prefill_code", "")
    loaded_code = st.session_state.get("analysis_prefill_loaded_code", "")
    if st.session_state.get("analysis_prefill_from_candidate") and prefill_code and prefill_code != loaded_code:
        st.session_state["fund_analysis_code"] = prefill_code
        st.session_state["fund_analysis_name"] = st.session_state.get("analysis_prefill_name", "")
        incoming_scope = st.session_state.get("analysis_prefill_preferred_type", "自动识别")
        st.session_state["fund_analysis_scope"] = LEGACY_SCOPE_MAP.get(incoming_scope, incoming_scope)
        if st.session_state["fund_analysis_scope"] not in SCOPE_OPTIONS:
            st.session_state["fund_analysis_scope"] = "自动识别"
        st.session_state["analysis_prefill_loaded_code"] = prefill_code


def apply_example_code() -> None:
    example = st.session_state.get("fund_analysis_example")
    if example and example != "手动输入":
        code, name, _category = EXAMPLES[example]
        st.session_state["fund_analysis_code"] = code
        st.session_state["fund_analysis_name"] = name
        st.session_state["fund_analysis_scope"] = "自动识别"
        st.session_state["analysis_prefill_from_candidate"] = False


def clear_analysis_target() -> None:
    for key in [
        "fund_analysis_code",
        "fund_analysis_name",
        "analysis_prefill_from_candidate",
        "analysis_prefill_code",
        "analysis_prefill_name",
        "analysis_prefill_asset_type",
        "analysis_prefill_asset_direction",
        "analysis_prefill_risk_level",
        "analysis_prefill_loaded_code",
        "analysis_prefill_source",
    ]:
        st.session_state.pop(key, None)
    st.session_state["fund_analysis_code"] = ""
    st.session_state["fund_analysis_name"] = ""
    st.session_state["fund_analysis_scope"] = "自动识别"
    st.session_state["fund_analysis_example"] = "手动输入"


def add_current_to_watchlist() -> None:
    code = st.session_state.get("fund_analysis_code", "").strip()
    if not code:
        st.warning("请先填写代码。")
        return
    exists = fetch_df("SELECT id FROM watchlist WHERE user_key=? AND code=? LIMIT 1", (current_user_key(), code))
    if not exists.empty:
        st.info("该标的已在自选池中。")
        return
    add_watch_item(
        {
            "code": code,
            "name": st.session_state.get("fund_analysis_name", "").strip() or code,
            "asset_type": st.session_state.get("analysis_prefill_asset_type", "候选观察"),
            "pool_type": "观察池",
            "risk_level": st.session_state.get("analysis_prefill_risk_level", "中风险"),
            "note": "从候选池分析页面加入",
        }
    )
    st.success("已加入自选池。")


init_fund_analysis_state()

page_header("基金 / ETF 分析", "像体检报告一样查看标的历史表现、风险等级、回撤和候选池适配情况。")

if st.session_state.get("analysis_prefill_from_candidate"):
    source_label = st.session_state.get("analysis_prefill_source", "候选池")
    st.success(
        f"已从{source_label}带入标的：{st.session_state.get('fund_analysis_code', '')} - "
        f"{st.session_state.get('fund_analysis_name', '')}。你可以点击下方按钮获取并分析数据。"
    )
    st.info("候选观察不等于买入建议，分析结果仅用于辅助判断。")

c1, c2, c3 = st.columns([1.2, 1.6, 1.2])
c1.selectbox("分析口径", SCOPE_OPTIONS, key="fund_analysis_scope")
c2.selectbox("常用示例代码", ["手动输入"] + list(EXAMPLES.keys()), key="fund_analysis_example", on_change=apply_example_code)
c3.text_input("代码", key="fund_analysis_code")

n1, n2 = st.columns([2, 1])
n1.text_input("名称", key="fund_analysis_name")
if n2.button("清空当前分析标的", on_click=clear_analysis_target):
    st.info("已清空当前分析标的，可以手动输入其他代码。")

if st.session_state.get("analysis_prefill_from_candidate"):
    if st.button("加入自选池"):
        add_current_to_watchlist()

refresh = st.button("刷新数据，忽略缓存")
if refresh:
    load_strict_asset_data.clear()
    st.session_state["fund_force_refresh_once"] = True
    st.success("已清除基金ETF分析页数据缓存，请点击“获取并分析”重新获取。")

if st.button("获取并分析", type="primary"):
    code = st.session_state.get("fund_analysis_code", "").strip()
    scope = st.session_state.get("fund_analysis_scope", "自动识别")
    if not code:
        st.warning("请先输入基金、ETF 或股票代码。")
    else:
        force_refresh = bool(st.session_state.pop("fund_force_refresh_once", False))
        result = load_strict_asset_data(code.upper(), scope, APP_VERSION, force_refresh)
        if not result["success"]:
            st.warning(result["message"])
            diagnosis = {
                "代码": result.get("code", code.upper()),
                "自动识别类型": result.get("inferred_asset_type", ""),
                "用户选择口径": scope,
                "实际使用口径": result.get("actual_scope", ""),
                "数据源": result.get("data_source", ""),
                "是否使用备用源": "是" if result.get("used_fallback") else "否",
                "strict 模式": "是" if result.get("strict") else "否",
                "是否来自缓存": "是" if result.get("from_cache") else "否",
                "是否旧缓存": "是" if result.get("cache_stale") else "否",
                "缓存更新时间": result.get("cache_updated_at", ""),
                "错误": "；".join(result.get("errors", [])),
                "当前 APP_VERSION": APP_VERSION,
            }
            st.dataframe(pd.DataFrame([diagnosis]), width="stretch", hide_index=True)
        else:
            df = result["data"]
            st.success(f"{result['message']} 当前识别类型：{result['asset_type']}。")
            if result.get("quote_type") == "基金单位净值":
                st.info("当前使用基金单位净值口径。")
            elif result.get("quote_type") == "场内交易价格":
                st.info("当前使用场内交易价格口径。")
            else:
                st.info(f"当前使用{result.get('quote_type', '统一 close 序列')}口径。")
            analysis = analyze_fund_dataframe(df)
            if "error" in analysis:
                st.warning(analysis["error"])
            else:
                mh = metrics_hash(analysis)
                diagnosis = {
                    "代码": result.get("code", code.upper()),
                    "名称": st.session_state.get("fund_analysis_name", "").strip() or result.get("asset_name", code.upper()),
                    "自动识别类型": result.get("inferred_asset_type", ""),
                    "用户选择口径": scope,
                    "实际使用口径": result.get("actual_scope", ""),
                    "数据源": result.get("data_source", ""),
                    "是否使用备用源": "是" if result.get("used_fallback") else "否",
                    "strict 模式": "是" if result.get("strict") else "否",
                    "是否来自缓存": "是" if result.get("from_cache") else "否",
                    "是否旧缓存": "是" if result.get("cache_stale") else "否",
                    "缓存更新时间": result.get("cache_updated_at", ""),
                    "起始日期": result.get("first_date", ""),
                    "结束日期": result.get("latest_date", ""),
                    "最新交易日 / 最新净值日期": result.get("latest_date", ""),
                    "最新价格 / 最新净值": result.get("latest_close", ""),
                    "数据行数": result.get("rows", 0),
                    "数据口径": result.get("quote_type", ""),
                    "复权 / 净值口径": result.get("adjustment", ""),
                    "指标计算版本": APP_VERSION,
                }
                st.subheader("数据诊断")
                st.dataframe(pd.DataFrame([diagnosis]), width="stretch", hide_index=True)

                consistency = build_consistency_report(result, metrics_hash=mh)
                st.subheader("一致性检查")
                st.dataframe(pd.DataFrame([consistency]), width="stretch", hide_index=True)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("评分", analysis.get("评分", "-"))
                col2.metric("结论", analysis.get("结论", "候选观察"))
                col3.metric("最大回撤", format_percent(analysis.get("最大回撤", 0)))
                col4.metric("年化波动率", format_percent(analysis.get("年化波动率", 0)))

                rows = []
                for key, value in analysis.items():
                    if isinstance(value, float) and key not in {"夏普比率", "评分"}:
                        value = format_percent(value)
                    rows.append({"指标": key, "数值": value})
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                chart_df = df.rename(columns={"date": "日期", "close": "净值或价格"})
                fig = px.line(
                    chart_df,
                    x="日期",
                    y="净值或价格",
                    title="净值 / 价格走势",
                    labels={"日期": "日期", "净值或价格": "净值或价格"},
                )
                fig.update_layout(xaxis_title="日期", yaxis_title="净值或价格", legend_title_text="项目")
                st.plotly_chart(fig, width="stretch")
                st.info("分析结果只用于判断是否值得继续观察，不构成买入建议。")
                st.caption(f"自动识别原始结果：{infer_asset_type_by_code(code)}；缓存版本：{APP_VERSION}；历史数据缓存 TTL：6 小时。")

show_risk_notice()
