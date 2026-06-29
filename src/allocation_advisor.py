from .asset_allocation import check_allocation_deviation
from .config import ASSET_TYPES
from .emergency_fund import evaluate_emergency_fund


def recommend_monthly_allocation(
    emergency_fund_amount: float,
    monthly_expense: float,
    weights: dict[str, float],
    monthly_available: float,
    risk_preference: str = "稳健",
) -> dict:
    """综合备用金、当前占比和风险偏好，生成本月新增资金方向。"""
    evaluation = evaluate_emergency_fund(emergency_fund_amount, monthly_expense)
    if emergency_fund_amount < monthly_expense * 6:
        return {
            "优先事项": "补备用金",
            "建议分配": {"现金/货币基金": monthly_available},
            "提醒": [evaluation["建议"]],
        }

    deviations = check_allocation_deviation(weights, risk_preference)
    low_assets = [item["资产类别"] for item in deviations if item["状态"] == "偏低"]
    high_assets = [item["资产类别"] for item in deviations if item["状态"] == "偏高"]
    candidates = [asset for asset in low_assets if asset not in {"个股", "量化实验仓"}]
    if not candidates:
        candidates = ["宽基指数基金/ETF", "海外/全球 ETF", "债券/短债"]

    allocation = {asset_type: 0.0 for asset_type in ASSET_TYPES}
    each = monthly_available / len(candidates) if candidates else 0.0
    for asset_type in candidates:
        allocation[asset_type] = each

    reminders = []
    if high_assets:
        reminders.append("以下资产暂时不建议加仓：" + "、".join(high_assets))
    if weights.get("个股", 0) > 0.05:
        reminders.append("个股仓位超过 5%，暂不适合扩大个股观察仓。")
    if weights.get("量化实验仓", 0) > 0.10:
        reminders.append("量化实验仓超过 10%，建议先控制实验仓规模。")
    if not reminders:
        reminders.append("本月可围绕低配资产做温和补充，保持长期定投节奏。")

    return {"优先事项": "按目标配置补低配资产", "建议分配": allocation, "提醒": reminders}
