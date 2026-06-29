from .config import ALLOCATION_TARGETS, ASSET_TYPES


def calculate_asset_weights(asset_amounts: dict[str, float]) -> dict[str, float]:
    """根据各类资产金额计算占比。"""
    normalized = {asset_type: float(asset_amounts.get(asset_type, 0) or 0) for asset_type in ASSET_TYPES}
    total = sum(max(value, 0) for value in normalized.values())
    if total <= 0:
        return {asset_type: 0.0 for asset_type in ASSET_TYPES}
    return {asset_type: max(value, 0) / total for asset_type, value in normalized.items()}


def check_allocation_deviation(weights: dict[str, float], risk_preference: str = "稳健") -> list[dict]:
    """检查当前配置是否偏离建议区间。"""
    targets = ALLOCATION_TARGETS.get(risk_preference, ALLOCATION_TARGETS["稳健"])
    deviations = []
    for asset_type, (low, high) in targets.items():
        weight = weights.get(asset_type, 0.0)
        if weight < low:
            deviations.append({"资产类别": asset_type, "当前占比": weight, "建议下限": low, "建议上限": high, "状态": "偏低"})
        elif weight > high:
            deviations.append({"资产类别": asset_type, "当前占比": weight, "建议下限": low, "建议上限": high, "状态": "偏高"})
    return deviations


def generate_rebalance_suggestions(weights: dict[str, float], risk_preference: str = "稳健") -> list[str]:
    """根据偏离情况生成温和的再平衡提示。"""
    suggestions = []
    for item in check_allocation_deviation(weights, risk_preference):
        asset_type = item["资产类别"]
        if item["状态"] == "偏低":
            suggestions.append(f"{asset_type}当前占比偏低，后续新增资金可优先考虑逐步补足。")
        else:
            suggestions.append(f"{asset_type}当前占比偏高，本月建议暂停新增或降低新增比例。")
    if weights.get("个股", 0) > 0.05:
        suggestions.append("个股总仓位超过 5%，需要控制单一资产风险。")
    if weights.get("行业基金/主题 ETF", 0) > 0.10:
        suggestions.append("行业基金/主题 ETF 占比超过 10%，行业集中度偏高。")
    if weights.get("量化实验仓", 0) > 0.10:
        suggestions.append("量化实验仓超过 10%，可能影响核心复利计划的稳定性。")
    if not suggestions:
        suggestions.append("当前配置整体处于建议区间内，可以继续按长期计划执行。")
    return suggestions
