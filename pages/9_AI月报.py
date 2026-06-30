from datetime import date

import streamlit as st

from src.auth import current_user_key
from src.database import fetch_df, load_latest_decision_profile, load_monthly_decision_records, load_recent_trade_records, save_monthly_report
from src.report_generator import generate_ai_report
from src.utils import format_currency, translate_columns
from src.ui_style import apply_global_style
from src.ui_components import info_box, page_header


st.set_page_config(page_title="AI月报", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
apply_global_style()

page_header("AI 月报", "把现金流、目标进度、定投执行和风险提示整理成一份月度资产报告。")

profile = load_latest_decision_profile()
cashflow_df = fetch_df("SELECT * FROM cashflow_records WHERE user_key=? ORDER BY month DESC LIMIT 1", (current_user_key(),))
decision_df = load_monthly_decision_records(1)
trade_df = load_recent_trade_records(20)

default_income = float(cashflow_df["income"].iloc[0]) if not cashflow_df.empty else 0.0
default_expense = float(cashflow_df["expense"].iloc[0]) if not cashflow_df.empty else 0.0
planned_amount = float(decision_df["monthly_investment"].iloc[0]) if not decision_df.empty else float(profile.get("monthly_investment", 0.0) or 0.0)
actual_amount = 0.0
if not trade_df.empty:
    report_month_prefix = date.today().strftime("%Y-%m")
    month_trades = trade_df[trade_df["trade_date"].astype(str).str.startswith(report_month_prefix)]
    actual_amount = float(month_trades["amount"].sum()) if not month_trades.empty else 0.0

with st.form("report_form"):
    report_month = st.text_input("报告月份", value=date.today().strftime("%Y-%m"), key="report_month")
    col1, col2, col3 = st.columns(3)
    income = col1.number_input("本月收入", min_value=0.0, value=default_income, step=100.0, key="report_income")
    expense = col2.number_input("本月支出", min_value=0.0, value=default_expense, step=100.0, key="report_expense")
    current_asset = col3.number_input("当前总资产", min_value=0.0, value=float(profile.get("total_asset", 0.0)), step=1000.0, key="report_current_asset")
    emergency_fund = col1.number_input("当前备用金", min_value=0.0, value=float(profile.get("emergency_fund", 0.0)), step=500.0, key="report_emergency_fund")
    monthly_investment = col2.number_input("每月投入", min_value=0.0, value=float(profile.get("monthly_investment", 0.0)), step=100.0, key="report_monthly_investment")
    target_asset = col3.number_input("目标资产", min_value=0.0, value=float(profile.get("target_asset", 0.0)), step=10000.0, key="report_target_asset")
    submitted = st.form_submit_button("生成月报")

if submitted:
    if cashflow_df.empty and decision_df.empty and trade_df.empty:
        info_box("暂无可生成月报的数据，请先填写现金流、资产配置和执行记录。", "warning")
    else:
        years = max(int(profile.get("target_age", 0)) - int(profile.get("current_age", 0)), 1)
        text = generate_ai_report(
            {
                "income": income,
                "expense": expense,
                "current_asset": current_asset,
                "target_asset": target_asset,
                "monthly_investment": monthly_investment,
                "years": years,
                "emergency_fund": emergency_fund,
                "monthly_expense": float(profile.get("monthly_expense", 0.0)),
                "planned_amount": planned_amount,
                "actual_amount": actual_amount,
            }
        )
        execution_rate = actual_amount / planned_amount if planned_amount > 0 else 0.0
        execution_text = (
            "\n\n本月执行情况\n\n"
            f"本月计划投入 {format_currency(planned_amount)}，实际记录执行 {format_currency(actual_amount)}，"
            f"执行率约 {execution_rate:.0%}。"
            "执行记录主要用于复盘是否按长期计划推进，不用于判断短期涨跌。"
        )
        text = text + execution_text
        save_monthly_report(report_month, text)
        st.subheader("本月报告")
        st.write(text)

st.subheader("本月执行记录")
if trade_df.empty:
    info_box("还没有定投执行记录。", "info")
else:
    st.dataframe(translate_columns(trade_df), use_container_width=True, hide_index=True)

st.subheader("历史月报")
report_df = fetch_df("SELECT * FROM monthly_reports WHERE user_key=? ORDER BY report_month DESC", (current_user_key(),))
if report_df.empty:
    st.info("还没有历史月报。")
else:
    st.dataframe(translate_columns(report_df), use_container_width=True, hide_index=True)
