from .config import RISK_NOTICE
from .goal_calculator import calculate_future_value, calculate_progress_status, calculate_required_monthly_investment
from .utils import format_currency, format_percent


def generate_rule_based_report(context: dict) -> str:
    """在没有 OpenAI API Key 时生成规则模板月报。"""
    income = context.get("income", 0.0)
    expense = context.get("expense", 0.0)
    saving = income - expense
    saving_rate = saving / income if income > 0 else 0.0
    current_asset = context.get("current_asset", 0.0)
    target_asset = context.get("target_asset", 0.0)
    monthly_investment = context.get("monthly_investment", 0.0)
    years = context.get("years", 15)
    emergency_fund = context.get("emergency_fund", 0.0)
    monthly_expense = context.get("monthly_expense", 0.0)
    expected = calculate_future_value(current_asset, monthly_investment, 0.05, years)
    required = calculate_required_monthly_investment(target_asset, current_asset, 0.05, years)
    status = calculate_progress_status(expected, target_asset)

    lines = [
        f"本月收入 {format_currency(income)}，支出 {format_currency(expense)}，结余 {format_currency(saving)}，储蓄率约 {format_percent(saving_rate)}。",
        f"当前总资产为 {format_currency(current_asset)}，距离 {format_currency(target_asset)} 目标还差 {format_currency(max(target_asset - current_asset, 0))}。",
        f"按当前每月投入 {format_currency(monthly_investment)}、年化 5% 估算，目标年龄预计资产约 {format_currency(expected)}，当前进度为：{status}。",
        f"如果希望提高达成概率，可把月投入逐步提升到约 {format_currency(required)} 左右，并保持不加杠杆、不满仓的原则。",
        f"当前备用金为 {format_currency(emergency_fund)}，6 个月生活费标准约 {format_currency(monthly_expense * 6)}。",
        "下个月优先事项：先保证现金流稳定，再围绕低配资产做长期、分散、可承受的配置。",
        RISK_NOTICE,
    ]
    return "\n\n".join(lines)


def generate_ai_report(context: dict) -> str:
    """公开体验版使用本地规则模板生成月报，不读取任何 API Key。"""
    return generate_rule_based_report(context)
