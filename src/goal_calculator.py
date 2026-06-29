import math


def calculate_future_value(current_asset: float, monthly_investment: float, annual_return: float, years: float) -> float:
    """计算当前资产加每月定投在未来的预计资产。"""
    months = max(int(round(years * 12)), 0)
    monthly_return = annual_return / 12
    if months == 0:
        return float(current_asset)
    if abs(monthly_return) < 1e-12:
        return float(current_asset + monthly_investment * months)
    return float(
        current_asset * (1 + monthly_return) ** months
        + monthly_investment * (((1 + monthly_return) ** months - 1) / monthly_return)
    )


def calculate_required_monthly_investment(target_asset: float, current_asset: float, annual_return: float, years: float) -> float:
    """反推达到目标资产所需的每月投入金额。"""
    months = max(int(round(years * 12)), 0)
    if months == 0:
        return 0.0 if current_asset >= target_asset else math.inf
    monthly_return = annual_return / 12
    if abs(monthly_return) < 1e-12:
        return max((target_asset - current_asset) / months, 0.0)
    future_current = current_asset * (1 + monthly_return) ** months
    annuity_factor = ((1 + monthly_return) ** months - 1) / monthly_return
    return max((target_asset - future_current) / annuity_factor, 0.0)


def calculate_progress_status(expected_asset: float, target_asset: float) -> str:
    """根据预计资产与目标资产判断进度。"""
    if target_asset <= 0:
        return "正常"
    ratio = expected_asset / target_asset
    if ratio >= 1.05:
        return "超前"
    if ratio >= 0.90:
        return "正常"
    return "落后"


def build_projection_series(current_asset: float, monthly_investment: float, annual_return: float, years: int) -> list[dict]:
    """生成按月资产预测序列，供图表展示。"""
    rows = []
    for month in range(0, years * 12 + 1):
        rows.append(
            {
                "月份": month,
                "年份": round(month / 12, 2),
                "预计资产": calculate_future_value(current_asset, monthly_investment, annual_return, month / 12),
            }
        )
    return rows

