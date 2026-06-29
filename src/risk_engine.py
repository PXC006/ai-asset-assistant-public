import numpy as np
import pandas as pd

from .config import RISK_FREE_RATE


def _close_series(data: pd.DataFrame | pd.Series) -> pd.Series:
    """从 DataFrame 或 Series 中提取净值/价格序列。"""
    if isinstance(data, pd.Series):
        series = data.copy()
    else:
        if "close" not in data.columns:
            raise ValueError("数据中缺少 close 列")
        series = data["close"].copy()
    return pd.to_numeric(series, errors="coerce").dropna()


def calculate_max_drawdown(data: pd.DataFrame | pd.Series) -> float:
    """计算最大回撤，返回负数比例。"""
    close = _close_series(data)
    if close.empty:
        return 0.0
    cumulative_max = close.cummax()
    drawdown = close / cumulative_max - 1
    return float(drawdown.min())


def calculate_annualized_volatility(data: pd.DataFrame | pd.Series) -> float:
    """按日收益率计算年化波动率。"""
    close = _close_series(data)
    returns = close.pct_change().dropna()
    if returns.empty:
        return 0.0
    return float(returns.std() * np.sqrt(252))


def calculate_sharpe_ratio(data: pd.DataFrame | pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    """计算年化夏普比率。"""
    close = _close_series(data)
    returns = close.pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return 0.0
    excess_daily = returns.mean() - risk_free_rate / 252
    return float(excess_daily / returns.std() * np.sqrt(252))


def calculate_return_by_period(data: pd.DataFrame, months: int) -> float | None:
    """计算近 N 个月收益率；数据不足时返回 None。"""
    if data.empty or "date" not in data.columns:
        return None
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date")
    end_date = frame["date"].max()
    start_date = end_date - pd.DateOffset(months=months)
    period = frame[frame["date"] >= start_date]
    if len(period) < 2:
        return None
    start = float(period["close"].iloc[0])
    end = float(period["close"].iloc[-1])
    return None if start == 0 else end / start - 1


def classify_risk_level(max_drawdown: float, volatility: float) -> str:
    """根据回撤和波动率给出风险等级。"""
    if max_drawdown <= -0.35 or volatility >= 0.35:
        return "高风险"
    if max_drawdown <= -0.20 or volatility >= 0.22:
        return "中高风险"
    if max_drawdown <= -0.10 or volatility >= 0.12:
        return "中风险"
    return "低风险"


def saving_rate_status(saving_rate: float) -> str:
    """判断储蓄率水平。"""
    if saving_rate >= 0.5:
        return "优秀"
    if saving_rate >= 0.3:
        return "正常"
    return "偏低，需要检查支出"

