def emergency_targets(monthly_expense: float) -> dict[str, float]:
    """计算 3/6/12 个月备用金目标。"""
    return {"最低备用金": monthly_expense * 3, "标准备用金": monthly_expense * 6, "安心备用金": monthly_expense * 12}


def evaluate_emergency_fund(current_fund: float, monthly_expense: float) -> dict:
    """判断备用金等级并给出投资限制建议。"""
    targets = emergency_targets(monthly_expense)
    if current_fund < targets["最低备用金"]:
        level = "不足 3 个月"
        advice = "不建议新增高风险投资，优先补足现金安全垫。"
    elif current_fund < targets["标准备用金"]:
        level = "3-6 个月"
        advice = "可以小额定投，但不建议扩大股票、行业基金或量化实验仓。"
    elif current_fund < targets["安心备用金"]:
        level = "6-12 个月"
        advice = "可以正常长期定投，同时继续保留充足现金比例。"
    else:
        level = "12 个月以上"
        advice = "备用金充足，多余部分可考虑进入长期投资账户。"
    return {"等级": level, "建议": advice, **targets}

