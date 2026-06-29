from .risk_engine import saving_rate_status


def calculate_cashflow(income: float, expense: float, investment_amount: float = 0.0) -> dict:
    """计算月度结余、储蓄率和状态。"""
    saving = income - expense
    saving_rate = saving / income if income > 0 else 0.0
    return {
        "saving": saving,
        "saving_rate": saving_rate,
        "investment_amount": investment_amount,
        "status": saving_rate_status(saving_rate),
    }


def detect_expense_anomaly(current_expense: float, previous_expenses: list[float]) -> str:
    """如果本月支出明显高于过去 6 个月平均值，给出提醒。"""
    recent = [value for value in previous_expenses[-6:] if value is not None]
    if len(recent) < 3:
        return "历史数据较少，暂不判断异常。"
    avg = sum(recent) / len(recent)
    if avg > 0 and current_expense > avg * 1.3:
        return "本月支出异常，建议复盘特殊支出。"
    return "本月支出未发现明显异常。"

