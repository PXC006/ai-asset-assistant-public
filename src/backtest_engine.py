import math
from datetime import date

import pandas as pd

from .config import DEFAULT_FEE_RATE
from .risk_engine import calculate_max_drawdown


RISK_FREE_RATE = 0.02


def prepare_price_data(df: pd.DataFrame, start_date=None, end_date=None) -> tuple[pd.DataFrame, list[str]]:
    """清洗行情数据，并把回测区间限制在真实历史数据范围内。"""
    messages: list[str] = []
    if df is None or df.empty or "date" not in df.columns or "close" not in df.columns:
        return pd.DataFrame(), ["行情数据为空或缺少 date / close 列。"]

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    if data.empty:
        return pd.DataFrame(), ["清洗后没有可用行情数据。"]

    min_date = data["date"].min().normalize()
    max_date = data["date"].max().normalize()
    requested_start = pd.to_datetime(start_date).normalize() if start_date else min_date
    requested_end = pd.to_datetime(end_date).normalize() if end_date else max_date

    today = pd.Timestamp(date.today())
    if requested_end > today:
        messages.append("回测只能基于历史数据，结束日期已自动调整为最新可用交易日。")
    if requested_end > max_date:
        messages.append("回测只能基于历史数据，结束日期已自动调整为最新可用交易日。")
    if requested_start < min_date:
        requested_start = min_date
    if requested_end > max_date:
        requested_end = max_date

    if requested_start > requested_end:
        return pd.DataFrame(), ["回测开始日期晚于结束日期，请重新选择。"]

    data = data[(data["date"] >= requested_start) & (data["date"] <= requested_end)].copy()
    if data.empty:
        return pd.DataFrame(), ["筛选后的数据为空，请调整回测日期。"]

    actual_years = max((data["date"].max() - data["date"].min()).days / 365.25, 0)
    if actual_years < 1:
        messages.append("样本时间较短，参考价值有限。")

    return data.reset_index(drop=True), list(dict.fromkeys(messages))


def _years_between(start, end) -> float:
    days = max((pd.to_datetime(end) - pd.to_datetime(start)).days, 1)
    return days / 365.25


def _annualize_simple(total_return: float, years: float) -> float:
    """用简化公式估算年化收益率。"""
    if years <= 0 or total_return <= -1:
        return 0.0
    return float((1 + total_return) ** (1 / years) - 1)


def _worst_year(equity: pd.Series) -> str:
    if not isinstance(equity.index, pd.DatetimeIndex) or len(equity) < 2:
        return "-"
    yearly = equity.resample("YE").last().pct_change().dropna()
    return "-" if yearly.empty else str(yearly.idxmin().year)


def _sharpe_from_returns(returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    returns = pd.to_numeric(returns, errors="coerce").dropna()
    if returns.empty or math.isclose(float(returns.std()), 0.0):
        return 0.0
    excess_daily = returns.mean() - risk_free_rate / 252
    return float(excess_daily / returns.std() * math.sqrt(252))


def _metrics_from_equity(equity: pd.Series, invested: float, trades: int, messages: list[str]) -> dict:
    ending_asset = float(equity.iloc[-1]) if len(equity) else 0.0
    profit = ending_asset - invested
    total_return = profit / invested if invested > 0 else 0.0
    years = _years_between(equity.index[0], equity.index[-1]) if len(equity) else 0.0
    return {
        "累计投入本金": float(invested),
        "期末账户资产": ending_asset,
        "期末资产": ending_asset,
        "投资净收益": float(profit),
        "总收益率": float(total_return),
        "近似年化收益率": _annualize_simple(total_return, years),
        "最大回撤": calculate_max_drawdown(pd.DataFrame({"close": equity})),
        "夏普比率": _sharpe_from_returns(equity.pct_change()),
        "交易次数": int(trades),
        "最差年份": _worst_year(equity),
        "实际开始日期": equity.index[0].date().isoformat() if len(equity) else "-",
        "实际结束日期": equity.index[-1].date().isoformat() if len(equity) else "-",
        "提示": messages,
        "年化收益率说明": "按简化公式估算，仅供参考。",
    }


def fixed_investment_backtest(
    df,
    initial_capital=10000,
    monthly_investment=3000,
    fee_rate=0.001,
    start_date=None,
    end_date=None,
):
    """简单定投：初始本金买入，之后每月首个可交易日定投。"""
    data, messages = prepare_price_data(df, start_date, end_date)
    if data.empty:
        return pd.DataFrame(), {"提示": messages}

    shares = 0.0
    invested = 0.0
    trades = 0
    previous_equity = 0.0
    last_month = None
    rows = []

    for idx, row in data.iterrows():
        current_date = row["date"]
        price = float(row["close"])
        contribution = 0.0
        month_key = current_date.strftime("%Y-%m")

        if idx == 0 and initial_capital > 0:
            contribution += float(initial_capital)
        if monthly_investment > 0 and month_key != last_month:
            contribution += float(monthly_investment)
            last_month = month_key

        if contribution > 0 and price > 0:
            shares += contribution * (1 - fee_rate) / price
            invested += contribution
            trades += 1

        equity = shares * price
        daily_return = 0.0 if previous_equity <= 0 else (equity - contribution - previous_equity) / previous_equity
        rows.append(
            {
                "date": current_date,
                "账户总资产曲线": equity,
                "账户总资产": equity,
                "累计投入本金曲线": invested,
                "累计投入本金": invested,
                "投资净收益曲线": equity - invested,
                "投资净收益": equity - invested,
                "日收益率": daily_return,
            }
        )
        previous_equity = equity

    result = pd.DataFrame(rows).set_index("date")
    metrics = _metrics_from_equity(result["账户总资产"], float(result["累计投入本金"].iloc[-1]), trades, messages)
    metrics["初始本金"] = float(initial_capital)
    metrics["每月定投金额"] = float(monthly_investment)
    metrics["夏普比率"] = _sharpe_from_returns(result["日收益率"])
    return result.reset_index(), metrics


def buy_and_hold_backtest(
    df,
    initial_capital=10000,
    fee_rate=DEFAULT_FEE_RATE,
    start_date=None,
    end_date=None,
):
    """买入持有基准：初始本金一次性买入并长期持有。"""
    data, messages = prepare_price_data(df, start_date, end_date)
    if data.empty or initial_capital <= 0:
        return pd.DataFrame(), {"提示": messages}

    first_price = float(data["close"].iloc[0])
    shares = float(initial_capital) * (1 - fee_rate) / first_price
    data["买入持有资产曲线"] = data["close"] * shares
    data["账户总资产"] = data["买入持有资产曲线"]
    data["累计投入本金"] = float(initial_capital)
    data["投资净收益"] = data["账户总资产"] - float(initial_capital)
    equity = data.set_index("date")["账户总资产"]
    metrics = _metrics_from_equity(equity, float(initial_capital), 1, messages)
    metrics["初始本金"] = float(initial_capital)
    return data[["date", "买入持有资产曲线", "账户总资产", "累计投入本金", "投资净收益"]], metrics


def moving_average_backtest(
    df,
    initial_capital=10000,
    short_window=20,
    long_window=60,
    fee_rate=DEFAULT_FEE_RATE,
    start_date=None,
    end_date=None,
):
    """均线策略：短均线高于长均线时持有，否则空仓。"""
    data, messages = prepare_price_data(df, start_date, end_date)
    if data.empty or initial_capital <= 0:
        return pd.DataFrame(), {"提示": messages}

    data = data.set_index("date")
    data["短均线"] = data["close"].rolling(short_window).mean()
    data["长均线"] = data["close"].rolling(long_window).mean()
    target_signal = (data["短均线"] > data["长均线"]).astype(int)

    cash = float(initial_capital)
    shares = 0.0
    position = 0
    trades = 0
    rows = []
    first_price = float(data["close"].iloc[0])
    buy_hold_shares = float(initial_capital) * (1 - fee_rate) / first_price

    for current_date, row in data.iterrows():
        price = float(row["close"])
        signal = int(target_signal.loc[current_date])
        action = ""

        if signal == 1 and position == 0 and cash > 0 and price > 0:
            shares = cash * (1 - fee_rate) / price
            cash = 0.0
            position = 1
            trades += 1
            action = "买入"
        elif signal == 0 and position == 1:
            cash = shares * price * (1 - fee_rate)
            shares = 0.0
            position = 0
            trades += 1
            action = "卖出"

        strategy_asset = cash + shares * price
        benchmark_asset = buy_hold_shares * price
        rows.append(
            {
                "date": current_date,
                "策略资产曲线": strategy_asset,
                "策略收益曲线": strategy_asset,
                "买入持有基准曲线": benchmark_asset,
                "动作": action,
                "close": price,
            }
        )

    result = pd.DataFrame(rows).set_index("date")
    equity = result["策略资产曲线"]
    metrics = _metrics_from_equity(equity, float(initial_capital), trades, messages)
    benchmark_total_return = float(result["买入持有基准曲线"].iloc[-1] / float(initial_capital) - 1)
    metrics["基准总收益率"] = benchmark_total_return
    metrics["是否跑赢基准"] = metrics["总收益率"] > benchmark_total_return
    return result.reset_index(), metrics

