from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.backtest_engine import buy_and_hold_backtest, fixed_investment_backtest, moving_average_backtest
from src.config import APP_VERSION
from src.data_fetcher import fetch_asset_data_auto
from src.utils import format_currency, format_percent, show_risk_notice
from src.ui_style import apply_global_style
from src.ui_components import page_header


st.set_page_config(page_title="量化实验室", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
apply_global_style()

BACKTEST_NOTICE = "回测不代表未来收益。以上内容仅用于个人资产管理辅助分析，不构成投资建议。未来行情无法通过历史回测直接预测。"
SOURCE_OPTIONS = ["自动识别", "中国ETF", "中国LOF", "中国开放式基金", "中国股票", "美股ETF"]
EXAMPLES = {
    "宽基ETF｜沪深300ETF示例 510300": "510300",
    "债券/短债｜国债ETF示例 511010": "511010",
    "红利低波｜红利ETF示例 510880": "510880",
    "海外ETF｜标普500ETF示例 513500": "513500",
    "行业主题｜芯片ETF示例 512760": "512760",
    "普通基金｜开放式基金示例 005827": "005827",
    "LOF/场内基金｜白酒LOF示例 161725": "161725",
    "美股ETF｜SPY": "SPY",
}

METRIC_HELP = {
    "累计投入本金": "实际投入过的钱，不包含市场涨跌带来的收益。",
    "期末账户资产": "回测结束日账户持有资产的市值。",
    "投资净收益": "期末账户资产减去累计投入本金。",
    "总收益率": "投资净收益 / 累计投入本金。",
    "近似年化收益率": "按简化公式估算，仅供参考。",
    "最大回撤": "账户从阶段高点跌到阶段低点的最大跌幅。",
    "夏普比率": "收益和波动的综合指标，越高通常越好。",
    "交易次数": "买入或卖出的次数，次数越多越受手续费影响。",
    "最差年份": "回测中年度表现最差的一年。",
}


@st.cache_data(ttl=21600, show_spinner=False)
def load_market_data(source: str, code: str, app_version: str):
    return fetch_asset_data_auto(code, preferred_type=source, strict=True)


def pct_or_na(value) -> str:
    return "无法估算" if value is None else format_percent(float(value))


def metric_with_help(label: str, value: str) -> None:
    st.metric(label, value)
    st.caption(METRIC_HELP.get(label, ""))


def show_common_metrics(metrics: dict) -> None:
    row1 = st.columns(4)
    with row1[0]:
        metric_with_help("累计投入本金", format_currency(metrics.get("累计投入本金", 0)))
    with row1[1]:
        metric_with_help("期末账户资产", format_currency(metrics.get("期末账户资产", 0)))
    with row1[2]:
        metric_with_help("投资净收益", format_currency(metrics.get("投资净收益", 0)))
    with row1[3]:
        metric_with_help("总收益率", pct_or_na(metrics.get("总收益率")))

    row2 = st.columns(5)
    with row2[0]:
        metric_with_help("近似年化收益率", pct_or_na(metrics.get("近似年化收益率")))
    with row2[1]:
        metric_with_help("最大回撤", pct_or_na(metrics.get("最大回撤")))
    with row2[2]:
        metric_with_help("夏普比率", f"{metrics.get('夏普比率', 0):.2f}")
    with row2[3]:
        metric_with_help("交易次数", str(metrics.get("交易次数", 0)))
    with row2[4]:
        metric_with_help("最差年份", str(metrics.get("最差年份", "-")))
    st.caption(f"实际回测区间：{metrics.get('实际开始日期', '-')} 至 {metrics.get('实际结束日期', '-')}")
    st.caption(metrics.get("年化收益率说明", "近似年化收益率按简化公式估算，仅供参考。"))


def fixed_investment_chart(curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["账户总资产曲线"], mode="lines", name="账户总资产曲线"))
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["累计投入本金曲线"], mode="lines", name="累计投入本金曲线"))
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["投资净收益曲线"], mode="lines", name="投资净收益曲线"))
    fig.update_layout(title="简单定投回测曲线", xaxis_title="日期", yaxis_title="金额（元）", hovermode="x unified")
    return fig


def buy_hold_chart(curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["买入持有资产曲线"], mode="lines", name="买入持有资产曲线"))
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["累计投入本金"], mode="lines", name="初始本金"))
    fig.update_layout(title="买入持有基准", xaxis_title="日期", yaxis_title="金额（元）", hovermode="x unified")
    return fig


def moving_average_chart(curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["策略资产曲线"], mode="lines", name="策略资产曲线"))
    fig.add_trace(go.Scatter(x=curve["date"], y=curve["买入持有基准曲线"], mode="lines", name="买入持有基准曲线"))
    buys = curve[curve["动作"] == "买入"]
    sells = curve[curve["动作"] == "卖出"]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys["date"], y=buys["策略资产曲线"], mode="markers", name="买入点", marker=dict(symbol="triangle-up", size=10)))
    if not sells.empty:
        fig.add_trace(go.Scatter(x=sells["date"], y=sells["策略资产曲线"], mode="markers", name="卖出点", marker=dict(symbol="triangle-down", size=10)))
    fig.update_layout(title="均线策略 vs 买入持有基准", xaxis_title="日期", yaxis_title="金额（元）", hovermode="x unified")
    return fig


page_header("量化实验室", "用历史数据理解策略表现，不预测未来；默认不加杠杆、不做空。")
st.info("回测开始日期 / 结束日期代表使用这段历史行情模拟策略表现。回测只能基于过去已经发生的数据，不能预测未来。")

top1, top2, top3, top4 = st.columns([1, 1.5, 1, 1])
source = top1.selectbox("数据源", SOURCE_OPTIONS, index=0)
example = top2.selectbox("常用示例代码", ["手动输入"] + list(EXAMPLES.keys()))
default_code = EXAMPLES[example] if example != "手动输入" else "510300"
code = top3.text_input("代码", value=default_code)
strategy = top4.selectbox("策略", ["简单定投", "均线策略", "买入持有基准"])

result = load_market_data(source, code, APP_VERSION) if code else {"success": False, "data": pd.DataFrame(), "message": "请输入代码。", "asset_type": "未知"}
if result["success"]:
    st.success(f"{result['message']} 当前识别类型：{result['asset_type']}。")
    df = result["data"].copy()
    latest_date = pd.to_datetime(df["date"]).max().date()
    earliest_date = pd.to_datetime(df["date"]).min().date()
else:
    st.warning(result["message"])
    df = pd.DataFrame()
    latest_date = date.today()
    earliest_date = date.today() - timedelta(days=365 * 5)

st.subheader("回测参数")
param1, param2, param3, param4 = st.columns(4)
initial_capital = param1.number_input("初始本金", min_value=0.0, value=10_000.0, step=1_000.0)
monthly_investment = param2.number_input("每月定投金额", min_value=0.0, value=3_000.0, step=500.0, disabled=strategy != "简单定投")
fee_rate = param3.number_input("手续费率", min_value=0.0, max_value=0.05, value=0.001, step=0.0005, format="%.4f")
param4.metric("最新可用交易日", latest_date.isoformat())

date1, date2, date3, date4 = st.columns(4)
default_start = max(earliest_date, latest_date - timedelta(days=365 * 5))
start_date = date1.date_input("回测开始日期", value=default_start, min_value=earliest_date, max_value=latest_date)
end_date = date2.date_input("回测结束日期", value=latest_date, min_value=earliest_date, max_value=latest_date)

if strategy == "均线策略":
    short_window = date3.number_input("短期均线天数", min_value=5, max_value=120, value=20, step=5)
    long_window = date4.number_input("长期均线天数", min_value=20, max_value=250, value=60, step=5)
else:
    short_window = 20
    long_window = 60

if st.button("开始回测", type="primary"):
    if df.empty:
        st.warning("请先确认数据可以正常获取。")
    elif start_date > end_date:
        st.warning("回测开始日期晚于结束日期，请重新选择。")
    elif strategy == "均线策略" and short_window >= long_window:
        st.warning("短期均线天数应小于长期均线天数。")
    else:
        if strategy == "简单定投":
            curve, metrics = fixed_investment_backtest(df=df, initial_capital=initial_capital, monthly_investment=monthly_investment, fee_rate=fee_rate, start_date=start_date, end_date=end_date)
        elif strategy == "均线策略":
            curve, metrics = moving_average_backtest(df=df, initial_capital=initial_capital, short_window=short_window, long_window=long_window, fee_rate=fee_rate, start_date=start_date, end_date=end_date)
        else:
            curve, metrics = buy_and_hold_backtest(df=df, initial_capital=initial_capital, fee_rate=fee_rate, start_date=start_date, end_date=end_date)

        for message in metrics.get("提示", []):
            st.warning(message)
        if curve.empty:
            st.warning("筛选后的数据为空，无法完成回测。请调整日期范围或检查代码。")
        else:
            st.subheader("回测结果")
            show_common_metrics(metrics)
            if strategy == "简单定投":
                st.plotly_chart(fixed_investment_chart(curve), width="stretch")
            elif strategy == "买入持有基准":
                st.plotly_chart(buy_hold_chart(curve), width="stretch")
            else:
                beat_text = "跑赢基准" if metrics.get("是否跑赢基准") else "未跑赢基准"
                st.write(f"是否跑赢基准：{beat_text}。基准总收益率：{format_percent(metrics.get('基准总收益率', 0))}。")
                st.plotly_chart(moving_average_chart(curve), width="stretch")
            st.warning(BACKTEST_NOTICE)

show_risk_notice()

