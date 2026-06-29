from __future__ import annotations

from .decision_engine import ASSET_LABELS, TARGET_RANGES


def _money(value) -> float:
    return max(float(value or 0), 0.0)


def _weights(current_allocation: dict[str, float]) -> dict[str, float]:
    total = sum(_money(value) for value in (current_allocation or {}).values())
    if total <= 0:
        return {key: 0.0 for key in ASSET_LABELS}
    return {key: _money((current_allocation or {}).get(key, 0.0)) / total for key in ASSET_LABELS}


def _target_ranges(risk_preference: str, target_allocation: dict | None) -> dict[str, tuple[float, float]]:
    if target_allocation:
        ranges = {}
        for key in ASSET_LABELS:
            value = target_allocation.get(key)
            if isinstance(value, (list, tuple)) and len(value) == 2:
                ranges[key] = (float(value[0]), float(value[1]))
            elif isinstance(value, (int, float)):
                center = float(value)
                ranges[key] = (max(center - 0.03, 0.0), min(center + 0.03, 1.0))
        if ranges:
            return ranges
    return TARGET_RANGES.get(risk_preference, TARGET_RANGES["稳健"])


def generate_rebalance_suggestions(
    current_allocation,
    target_allocation,
    emergency_fund,
    monthly_expense,
    risk_preference,
    holdings,
):
    current_allocation = current_allocation or {}
    emergency_fund = _money(emergency_fund)
    monthly_expense = _money(monthly_expense)
    ranges = _target_ranges(risk_preference, target_allocation)
    weights = _weights(current_allocation)

    overweight_assets = []
    underweight_assets = []
    sell_suggestions = []
    buy_suggestions = []
    warnings = [
        "不建议因为短期涨跌卖出。卖出和再平衡应基于资产比例、风险控制和个人目标变化。",
    ]
    explanation = []

    if monthly_expense > 0 and emergency_fund < monthly_expense * 3:
        warnings.append("备用金低于 3 个月生活费，优先补现金，暂停新增高风险资产。")
        buy_suggestions.append("优先把新增资金补到现金/货币基金，先恢复安全垫。")

    for key, label in ASSET_LABELS.items():
        weight = weights.get(key, 0.0)
        low, high = ranges.get(key, (0.0, 1.0))
        if weight > high:
            item = {"asset_key": key, "asset_name": label, "current_weight": weight, "target_high": high}
            overweight_assets.append(item)
            explanation.append(f"{label}当前占比约 {weight:.1%}，高于目标上限 {high:.1%}。")
            if weight >= high + 0.05 or (high > 0 and weight >= high * 1.5):
                sell_suggestions.append(f"{label}明显高于目标范围，可以考虑逐步降低，但不建议一次性清仓。")
            else:
                sell_suggestions.append(f"{label}略高于目标范围，本月先暂停继续加仓。")
        elif weight < low:
            underweight_assets.append({"asset_key": key, "asset_name": label, "current_weight": weight, "target_low": low})
            buy_suggestions.append(f"{label}低于目标范围，优先用新增资金慢慢补上。")

    if weights.get("sector_theme", 0.0) > 0.10:
        warnings.append("行业基金/主题ETF占比超过 10%，波动较大，本月不建议继续加仓。")
    if weights.get("stock", 0.0) > 0.05:
        warnings.append("个股仓位超过 5%，单一波动会影响长期计划，不建议继续加仓。")
    if weights.get("quant_experiment", 0.0) > 0.10:
        warnings.append("量化实验仓超过 10%，可能影响核心复利计划，建议控制比例。")

    high_risk_weight = weights.get("sector_theme", 0.0) + weights.get("stock", 0.0) + weights.get("quant_experiment", 0.0)
    if high_risk_weight > 0.20:
        warnings.append("行业、个股和实验仓合计占比偏高，建议先把核心资产和备用金放在前面。")

    rebalance_needed = bool(overweight_assets or underweight_assets or len(warnings) > 1)
    if not sell_suggestions:
        sell_suggestions.append("当前不建议因为短期波动卖出。优先按本月新增资金补低配资产。")
    if not buy_suggestions:
        buy_suggestions.append("当前没有明显低配资产，本月按既定计划执行即可。")
    if not explanation:
        explanation.append("当前资产比例没有明显偏离。继续按月执行计划，比频繁调整更重要。")

    return {
        "rebalance_needed": rebalance_needed,
        "overweight_assets": overweight_assets,
        "underweight_assets": underweight_assets,
        "sell_suggestions": list(dict.fromkeys(sell_suggestions)),
        "buy_suggestions": list(dict.fromkeys(buy_suggestions)),
        "warnings": list(dict.fromkeys(warnings)),
        "explanation": list(dict.fromkeys(explanation)),
    }
