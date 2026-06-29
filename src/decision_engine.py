from __future__ import annotations

from dataclasses import dataclass


ASSET_LABELS = {
    "cash": "现金/货币基金",
    "bond": "债券/短债",
    "broad_index": "宽基指数基金/ETF",
    "global_index": "海外/全球指数",
    "sector_theme": "行业基金/主题ETF",
    "active_fund": "主动基金",
    "stock": "个股观察仓",
    "quant_experiment": "量化实验仓",
}

TARGET_RANGES = {
    "保守": {
        "cash": (0.20, 0.35),
        "bond": (0.25, 0.45),
        "broad_index": (0.20, 0.35),
        "global_index": (0.05, 0.15),
        "sector_theme": (0.00, 0.05),
        "active_fund": (0.00, 0.10),
        "stock": (0.00, 0.02),
        "quant_experiment": (0.00, 0.03),
    },
    "稳健": {
        "cash": (0.15, 0.30),
        "bond": (0.15, 0.30),
        "broad_index": (0.35, 0.50),
        "global_index": (0.05, 0.15),
        "sector_theme": (0.00, 0.08),
        "active_fund": (0.00, 0.15),
        "stock": (0.00, 0.03),
        "quant_experiment": (0.00, 0.05),
    },
    "稳健偏进取": {
        "cash": (0.10, 0.20),
        "bond": (0.10, 0.20),
        "broad_index": (0.40, 0.60),
        "global_index": (0.10, 0.20),
        "sector_theme": (0.00, 0.10),
        "active_fund": (0.00, 0.20),
        "stock": (0.00, 0.05),
        "quant_experiment": (0.00, 0.10),
    },
    "激进": {
        "cash": (0.10, 0.20),
        "bond": (0.05, 0.15),
        "broad_index": (0.40, 0.60),
        "global_index": (0.10, 0.25),
        "sector_theme": (0.00, 0.10),
        "active_fund": (0.00, 0.20),
        "stock": (0.00, 0.05),
        "quant_experiment": (0.00, 0.10),
    },
}


@dataclass
class AllocationCandidate:
    key: str
    reason: str
    weight: float


def _money(value) -> float:
    return max(float(value or 0), 0.0)


def _weights(asset_amounts: dict[str, float], total_asset: float) -> dict[str, float]:
    base = max(total_asset, sum(_money(v) for v in asset_amounts.values()), 0.0)
    if base <= 0:
        return {key: 0.0 for key in ASSET_LABELS}
    return {key: _money(asset_amounts.get(key, 0)) / base for key in ASSET_LABELS}


def _add_allocation(allocations: dict[str, float], key: str, amount: float) -> None:
    if amount <= 0:
        return
    allocations[key] = allocations.get(key, 0.0) + amount


def _round_allocations(allocations: dict[str, float], total: float) -> dict[str, float]:
    rounded = {key: round(value, 2) for key, value in allocations.items() if value > 0.01}
    diff = round(total - sum(rounded.values()), 2)
    if rounded and abs(diff) >= 0.01:
        first_key = next(iter(rounded))
        rounded[first_key] = round(max(rounded[first_key] + diff, 0), 2)
    return rounded


def generate_monthly_investment_plan(
    current_age,
    target_age,
    target_asset,
    total_asset,
    emergency_fund,
    monthly_expense,
    monthly_investment,
    asset_amounts,
    risk_preference,
):
    """生成本月投资分配建议。

    这个函数只做资产配置辅助分析，不输出买卖指令，也不预测涨跌。
    """
    current_age = int(current_age or 0)
    target_age = int(target_age or 0)
    target_asset = _money(target_asset)
    total_asset = _money(total_asset)
    emergency_fund = _money(emergency_fund)
    monthly_expense = max(_money(monthly_expense), 1.0)
    monthly_investment = _money(monthly_investment)
    risk_preference = risk_preference if risk_preference in TARGET_RANGES else "稳健"
    asset_amounts = {key: _money(asset_amounts.get(key, 0)) for key in ASSET_LABELS}
    if total_asset <= 0:
        total_asset = sum(asset_amounts.values())

    ranges = TARGET_RANGES[risk_preference].copy()
    if total_asset < 100_000:
        ranges["stock"] = (0.0, min(ranges["stock"][1], 0.03))
        ranges["quant_experiment"] = (0.0, min(ranges["quant_experiment"][1], 0.05))

    weights = _weights(asset_amounts, total_asset)
    three_months = monthly_expense * 3
    six_months = monthly_expense * 6
    remaining = monthly_investment
    allocations: dict[str, float] = {}
    priority: list[dict] = []
    avoid: list[dict] = []
    warnings: list[str] = []
    explanation: list[str] = []

    def prioritize(key: str, reason: str, weight: float) -> None:
        priority.append({"资产类别": ASSET_LABELS[key], "原因": reason, "当前占比": weights.get(key, 0), "优先级": weight})

    if emergency_fund < three_months:
        cash_amount = min(remaining, monthly_investment * 0.8)
        _add_allocation(allocations, "cash", cash_amount)
        remaining -= cash_amount
        prioritize("cash", "当前备用金不足 3 个月生活费，先把现金安全垫补起来。", 100)
        explanation.append("备用金还没到 3 个月生活费，本月最重要的是提高抗风险能力。")
        for key, reason in {
            "sector_theme": "核心资产还没搭好，行业主题波动较大。",
            "stock": "当前阶段个股波动可能影响长期计划。",
            "quant_experiment": "先完成现金安全垫，再做策略实验。",
        }.items():
            avoid.append({"资产类别": ASSET_LABELS[key], "原因": reason})
        warnings.append("备用金低于 3 个月生活费，不建议新增高风险资产。")
    elif emergency_fund < six_months:
        cash_amount = min(remaining, monthly_investment * 0.4)
        _add_allocation(allocations, "cash", cash_amount)
        remaining -= cash_amount
        prioritize("cash", "当前备用金低于 6 个月生活费，本月至少拿一部分补现金安全垫。", 95)
        explanation.append("备用金还没到标准线，剩余资金再考虑宽基指数或短债。")
        avoid.append({"资产类别": ASSET_LABELS["stock"], "原因": "备用金还没达标，不建议急着开个股观察仓。"})
        avoid.append({"资产类别": ASSET_LABELS["quant_experiment"], "原因": "实验仓应放在现金安全垫达标之后。"})
        avoid.append({"资产类别": ASSET_LABELS["sector_theme"], "原因": "行业主题不适合放在核心资产之前。"})

    candidates: list[AllocationCandidate] = []
    if weights["broad_index"] < ranges["broad_index"][0]:
        candidates.append(AllocationCandidate("broad_index", "当前长期增长类核心资产偏少，可以优先把宽基指数基金/ETF搭起来。", 90))
    if weights["bond"] < ranges["bond"][0]:
        candidates.append(AllocationCandidate("bond", "当前稳定资产偏少，适当配置债券/短债有助于降低组合波动。", 75))
    if emergency_fund >= six_months and weights["global_index"] < ranges["global_index"][0]:
        candidates.append(AllocationCandidate("global_index", "核心资产初步稳定后，可以用小比例全球指数分散单一市场风险。", 60))
    if weights["cash"] < ranges["cash"][0] and emergency_fund >= six_months:
        candidates.append(AllocationCandidate("cash", "现金比例偏低，保留流动性可以减少临时用钱时被迫卖出。", 55))
    if not candidates and remaining > 0:
        candidates.extend(
            [
                AllocationCandidate("broad_index", "如果没有明显短板，本月可以继续围绕宽基指数基金/ETF做长期配置。", 70),
                AllocationCandidate("bond", "留一部分给稳定资产，让组合不要全部依赖权益市场。", 45),
            ]
        )

    candidates = sorted(candidates, key=lambda item: item.weight, reverse=True)
    if remaining > 0 and candidates:
        total_weight = sum(item.weight for item in candidates)
        for item in candidates:
            amount = remaining * item.weight / total_weight
            _add_allocation(allocations, item.key, amount)
            prioritize(item.key, item.reason, item.weight)
            explanation.append(item.reason)

    if weights["sector_theme"] > 0.10:
        avoid.append({"资产类别": ASSET_LABELS["sector_theme"], "原因": "当前行业主题占比超过 10%，本月不建议继续加仓。"})
        warnings.append("行业主题基金占比偏高，容易让组合受单一行业影响。")
    elif weights["broad_index"] < ranges["broad_index"][0]:
        avoid.append({"资产类别": ASSET_LABELS["sector_theme"], "原因": "核心宽基资产还没搭起来，行业主题暂时只适合观察。"})

    if weights["stock"] > ranges["stock"][1]:
        warnings.append("个股仓位已经偏高，建议控制观察仓规模。")
        avoid.append({"资产类别": ASSET_LABELS["stock"], "原因": "个股仓位已超过建议上限，本月不建议继续加。"})
    elif total_asset < 100_000:
        avoid.append({"资产类别": ASSET_LABELS["stock"], "原因": "总资产低于 10 万时，个股观察仓建议很小，先搭核心资产。"})

    if weights["quant_experiment"] > ranges["quant_experiment"][1]:
        warnings.append("量化实验仓占比偏高，可能影响核心复利计划。")
        avoid.append({"资产类别": ASSET_LABELS["quant_experiment"], "原因": "实验仓已超过建议上限，本月不建议继续加。"})
    elif total_asset < 100_000:
        avoid.append({"资产类别": ASSET_LABELS["quant_experiment"], "原因": "总资产低于 10 万时，量化实验仓先保持很小或不开启。"})

    if weights["cash"] < ranges["cash"][0]:
        warnings.append("现金/货币基金占比偏低，要注意流动性。")
    if weights["broad_index"] < ranges["broad_index"][0]:
        warnings.append("宽基指数基金/ETF占比偏低，长期核心资产还需要搭建。")

    deduped_avoid = []
    seen_avoid = set()
    for item in avoid:
        key = (item["资产类别"], item["原因"])
        if key not in seen_avoid:
            deduped_avoid.append(item)
            seen_avoid.add(key)
    avoid = deduped_avoid

    stock_ok = total_asset >= 100_000 and emergency_fund >= six_months and weights["stock"] <= ranges["stock"][1]
    quant_ok = total_asset >= 100_000 and emergency_fund >= six_months and weights["quant_experiment"] <= ranges["quant_experiment"][1]
    health_flags = [w for w in warnings if "偏高" in w or "不足" in w or "偏低" in w]
    allocation_health = "整体可继续优化" if health_flags else "整体较健康"

    action_items = []
    for key, amount in _round_allocations(allocations, monthly_investment).items():
        pct = amount / monthly_investment if monthly_investment else 0
        action_items.append(f"把本月可投资金额中的 {amount:.0f} 元（约 {pct:.0%}）放到{ASSET_LABELS[key]}方向。")
    if avoid:
        avoid_names = list(dict.fromkeys(item["资产类别"] for item in avoid))
        action_items.append("本月暂时不加仓：" + "、".join(avoid_names[:4]) + "。")
    action_items.append("具体标的先放入观察池，确认风险和费用后再由你自己决定。")

    return {
        "recommended_allocations": _round_allocations(allocations, monthly_investment),
        "priority_list": sorted(priority, key=lambda item: item["优先级"], reverse=True),
        "avoid_list": avoid,
        "warnings": warnings,
        "explanation": explanation,
        "action_items": action_items,
        "weights": weights,
        "target_ranges": ranges,
        "allocation_health": allocation_health,
        "should_fill_emergency_fund_first": emergency_fund < six_months,
        "can_open_stock_watch": stock_ok,
        "can_open_quant_experiment": quant_ok,
        "years_left": max(target_age - current_age, 0),
        "target_gap": max(target_asset - total_asset, 0),
        "risk_notice": "以上内容仅用于个人资产管理辅助分析，不构成投资建议；不预测涨跌，用户需要自己做最终决策。",
    }
