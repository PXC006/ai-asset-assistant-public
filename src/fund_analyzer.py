import pandas as pd

from .risk_engine import (
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_return_by_period,
    calculate_sharpe_ratio,
    classify_risk_level,
)


def analyze_fund_dataframe(df: pd.DataFrame) -> dict:
    """对基金/ETF 净值数据做基础风险收益分析。"""
    if df.empty or len(df) < 2:
        return {"error": "数据不足，无法分析。"}

    max_drawdown = calculate_max_drawdown(df)
    volatility = calculate_annualized_volatility(df)
    sharpe = calculate_sharpe_ratio(df)
    total_return = df["close"].iloc[-1] / df["close"].iloc[0] - 1
    years = max((pd.to_datetime(df["date"]).max() - pd.to_datetime(df["date"]).min()).days / 365.25, 1 / 365)
    annual_return = (1 + total_return) ** (1 / years) - 1
    risk_level = classify_risk_level(max_drawdown, volatility)

    score = 50
    score += min(max(annual_return, -0.2), 0.2) / 0.2 * 20
    score += max(0, 1 + max_drawdown) * 15
    score += max(0, 1 - volatility) * 10
    score += max(min(sharpe, 2), -1) / 2 * 10
    score += min(len(df) / 750, 1) * 10
    score = round(max(min(score, 100), 0), 1)

    if score >= 80:
        label = "适合长期观察或核心定投候选"
    elif score >= 60:
        label = "可以观察，需要控制仓位"
    elif score >= 40:
        label = "风险较高，谨慎"
    else:
        label = "不适合当前阶段"

    return {
        "总收益": total_return,
        "年化收益": annual_return,
        "近1月收益": calculate_return_by_period(df, 1),
        "近3月收益": calculate_return_by_period(df, 3),
        "近6月收益": calculate_return_by_period(df, 6),
        "近1年收益": calculate_return_by_period(df, 12),
        "近3年收益": calculate_return_by_period(df, 36),
        "最大回撤": max_drawdown,
        "年化波动率": volatility,
        "夏普比率": sharpe,
        "风险等级": risk_level,
        "评分": score,
        "结论": label,
    }

