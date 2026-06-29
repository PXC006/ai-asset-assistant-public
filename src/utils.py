import pandas as pd
import streamlit as st

from .config import RISK_NOTICE


CHINESE_COLUMN_MAP = {
    "id": "ID",
    "month": "月份",
    "report_month": "报告月份",
    "decision_month": "决策月份",
    "trade_date": "交易日期",
    "income": "收入",
    "expense": "支出",
    "saving": "结余",
    "saving_rate": "储蓄率",
    "investment_amount": "当月实际投资金额",
    "special_expense_note": "特殊支出备注",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "code": "代码",
    "name": "名称",
    "asset_type": "资产类型",
    "asset_name": "资产名称",
    "asset_code": "资产代码",
    "amount": "买入金额",
    "cost": "成本",
    "current_value": "当前金额",
    "buy_date": "买入日期",
    "pool_type": "所属池子",
    "action": "动作",
    "risk_level": "风险等级",
    "note": "备注",
    "current_age": "当前年龄",
    "target_age": "目标年龄",
    "target_asset": "目标资产",
    "total_asset": "当前总资产",
    "emergency_fund": "当前备用金",
    "monthly_expense": "月支出",
    "monthly_investment": "本月可投资金额",
    "cash_amount": "现金/货币基金",
    "bond_amount": "债券/短债",
    "broad_index_amount": "宽基指数基金/ETF",
    "global_index_amount": "海外/全球指数",
    "sector_theme_amount": "行业基金/主题ETF",
    "active_fund_amount": "主动基金",
    "stock_amount": "个股",
    "quant_experiment_amount": "量化实验仓",
    "risk_preference": "风险偏好",
    "profile_name": "方案名称",
    "input_json": "输入数据",
    "result_json": "决策结果",
    "action_items": "行动清单",
    "warnings": "风险提示",
    "explanation": "原因说明",
    "report_text": "月报内容",
    "key": "设置项",
    "value": "内容",
}


def translate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a DataFrame with user-facing Chinese column names."""
    if df is None:
        return pd.DataFrame()
    return df.rename(columns={col: CHINESE_COLUMN_MAP.get(col, col) for col in df.columns})


def format_currency(value: float) -> str:
    return f"{float(value or 0):,.0f} 元"


def format_percent(value: float) -> str:
    return f"{float(value or 0) * 100:.2f}%"


def show_risk_notice() -> None:
    st.info(RISK_NOTICE)


def to_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows or [])
