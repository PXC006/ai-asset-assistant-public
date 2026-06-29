from __future__ import annotations

from datetime import date
from calendar import monthrange

from .decision_engine import ASSET_LABELS


HIGH_RISK_ASSETS = {"sector_theme", "stock", "quant_experiment"}


def _money(value) -> float:
    return max(float(value or 0), 0.0)


def _clamp_day(year: int, month: int, day: int) -> date:
    return date(year, month, min(max(int(day), 1), monthrange(year, month)[1]))


def _execution_dates(salary_day: int, mode: str, offset_days: int) -> list[date]:
    today = date.today()
    base = _clamp_day(today.year, today.month, salary_day)
    first_day = min(base.day + int(offset_days), monthrange(today.year, today.month)[1])
    first = _clamp_day(today.year, today.month, first_day)
    if mode == "分三次投":
        days = [first.day, min(first.day + 10, monthrange(today.year, today.month)[1]), min(first.day + 20, monthrange(today.year, today.month)[1])]
    elif mode == "分两次投":
        days = [first.day, min(first.day + 15, monthrange(today.year, today.month)[1])]
    else:
        days = [first.day]
    deduped = []
    for day in days:
        item = _clamp_day(today.year, today.month, day)
        if item not in deduped:
            deduped.append(item)
    return deduped


def _mode_weights(mode: str, monthly_investment: float) -> list[float]:
    if monthly_investment <= 3000 and mode != "分两次投" and mode != "分三次投":
        return [1.0]
    if mode == "分三次投":
        return [0.4, 0.3, 0.3]
    if mode == "分两次投":
        return [0.5, 0.5]
    return [1.0]


def _round_allocations(allocations: dict[str, float], total: float) -> dict[str, float]:
    clean = {key: round(_money(value), 2) for key, value in allocations.items() if _money(value) > 0}
    diff = round(_money(total) - sum(clean.values()), 2)
    if clean and abs(diff) >= 0.01:
        first_key = next(iter(clean))
        clean[first_key] = round(max(clean[first_key] + diff, 0), 2)
    return clean


def generate_dca_execution_plan(
    monthly_investment,
    recommended_allocations,
    salary_day,
    execution_mode,
    emergency_fund,
    monthly_expense,
    risk_preference,
    current_allocation,
    execution_offset_days=1,
    allow_volatility_split=True,
    min_single_amount=100.0,
):
    monthly_investment = _money(monthly_investment)
    emergency_fund = _money(emergency_fund)
    monthly_expense = _money(monthly_expense)
    min_single_amount = max(_money(min_single_amount), 0.0)
    allocations = _round_allocations(recommended_allocations or {}, monthly_investment)

    warnings = [
        "不需要预测当天涨跌，也不建议因为一天的市场波动临时改变长期计划。",
    ]
    skip_rules = []

    if monthly_expense > 0 and emergency_fund < monthly_expense * 3:
        warnings.append("当前备用金低于 3 个月生活费，本月应优先补现金安全垫。")
        skip_rules.extend(["暂不新增行业主题基金", "暂不新增个股", "暂不开启量化实验仓"])
    elif monthly_expense > 0 and emergency_fund < monthly_expense * 6:
        warnings.append("当前备用金低于 6 个月生活费，建议本月至少 30%-50% 用于补现金安全垫。")

    for key in HIGH_RISK_ASSETS:
        if allocations.get(key, 0) > 0 and monthly_expense > 0 and emergency_fund < monthly_expense * 6:
            skip_rules.append(f"备用金未达标前，{ASSET_LABELS.get(key, key)}不建议新增。")

    if monthly_investment <= 0:
        return {
            "execution_plan": [],
            "execution_dates": [],
            "allocation_steps": [],
            "warnings": warnings + ["本月可投资金额为 0，暂时没有需要执行的定投计划。"],
            "skip_rules": list(dict.fromkeys(skip_rules)),
            "summary": "本月没有可执行金额。建议先确认现金流和备用金，再决定是否投入。",
        }

    mode = execution_mode
    if execution_mode == "自动匹配":
        if monthly_investment <= 3000:
            mode = "工资到账后一次性投"
        elif monthly_investment <= 8000:
            mode = "分两次投"
        else:
            mode = "分三次投"

    if allow_volatility_split and monthly_investment > 3000 and mode == "工资到账后一次性投":
        warnings.append("如果心理压力较大，可以分批执行，降低一次性买入的压力；这不是为了猜低点。")

    dates = _execution_dates(int(salary_day), mode, int(execution_offset_days))
    weights = _mode_weights(mode, monthly_investment)
    if len(weights) != len(dates):
        weights = weights[: len(dates)]
        total_weight = sum(weights) or 1
        weights = [value / total_weight for value in weights]

    allocation_steps = []
    execution_plan = []
    for idx, item_date in enumerate(dates):
        date_weight = weights[idx]
        step_items = []
        for asset_key, amount in allocations.items():
            step_amount = round(amount * date_weight, 2)
            if 0 < step_amount < min_single_amount and len(dates) > 1:
                continue
            step_items.append(
                {
                    "asset_key": asset_key,
                    "asset_name": ASSET_LABELS.get(asset_key, asset_key),
                    "amount": step_amount,
                }
            )
            allocation_steps.append(
                {
                    "date": item_date.isoformat(),
                    "asset_key": asset_key,
                    "asset_name": ASSET_LABELS.get(asset_key, asset_key),
                    "amount": step_amount,
                }
            )
        execution_plan.append({"date": item_date.isoformat(), "items": step_items, "total_amount": round(sum(i["amount"] for i in step_items), 2)})

    summary = f"本月计划投入 {monthly_investment:.2f} 元，建议按“{mode}”执行，重点是按计划补充低配资产，而不是猜短期涨跌。"
    return {
        "execution_plan": execution_plan,
        "execution_dates": [item.isoformat() for item in dates],
        "allocation_steps": allocation_steps,
        "warnings": list(dict.fromkeys(warnings)),
        "skip_rules": list(dict.fromkeys(skip_rules)),
        "summary": summary,
    }
