from datetime import date

import plotly.express as px
import streamlit as st

from src.cashflow import calculate_cashflow, detect_expense_anomaly
from src.auth import render_user_sidebar, require_user_key
from src.database import load_cashflow_record_by_month, load_recent_cashflow_records, save_cashflow_record
from src.utils import format_currency, format_percent, show_risk_notice, translate_columns
from src.ui_style import apply_global_style
from src.ui_components import info_box, metric_card, page_header


st.set_page_config(page_title="现金流记录", page_icon="💧", layout="wide", initial_sidebar_state="expanded")
apply_global_style()
require_user_key()
render_user_sidebar()

page_header("现金流记录", "记录每月收入、支出、结余和真实投入金额，看清长期复利计划的现金来源。")

current_month = date.today().strftime("%Y-%m")
month = st.text_input("月份", value=current_month, help="格式示例：2026-06").strip() or current_month

existing = load_cashflow_record_by_month(month)
if existing:
    info_box(f"已从本地数据库加载 {month} 的现金流记录。", "success")
else:
    info_box(f"{month} 还没有保存记录，当前显示空白默认值。", "info")

form_version = str((existing or {}).get("updated_at") or "new").replace(" ", "_").replace(":", "-")
form_key = f"cashflow_form_{month}_{form_version}"

with st.form(form_key):
    col1, col2, col3 = st.columns(3)
    income = col1.number_input(
        "收入",
        min_value=0.0,
        value=float(existing["income"]) if existing else 0.0,
        step=100.0,
        key=f"cf_form_income_{month}_{form_version}",
    )
    expense = col2.number_input(
        "支出",
        min_value=0.0,
        value=float(existing["expense"]) if existing else 0.0,
        step=100.0,
        key=f"cf_form_expense_{month}_{form_version}",
    )
    investment_amount = col3.number_input(
        "当月实际投资金额",
        min_value=0.0,
        value=float(existing["investment_amount"]) if existing else 0.0,
        step=100.0,
        key=f"cf_form_investment_amount_{month}_{form_version}",
    )
    note = st.text_area(
        "特殊支出备注",
        value=str(existing.get("special_expense_note") or "") if existing else "",
        key=f"cf_form_note_{month}_{form_version}",
    )
    submitted = st.form_submit_button("保存现金流", type="primary")

if submitted:
    try:
        save_cashflow_record(
            {
                "month": month,
                "income": income,
                "expense": expense,
                "investment_amount": investment_amount,
                "special_expense_note": note,
            }
        )
        st.success("现金流已保存。")
        st.rerun()
    except Exception as exc:
        st.error(f"保存现金流失败：{exc}")

saved_or_current = load_cashflow_record_by_month(month)
if saved_or_current:
    display_income = float(saved_or_current["income"])
    display_expense = float(saved_or_current["expense"])
    display_investment = float(saved_or_current["investment_amount"])
else:
    display_income = float(income) if "income" in locals() else 0.0
    display_expense = float(expense) if "expense" in locals() else 0.0
    display_investment = float(investment_amount) if "investment_amount" in locals() else 0.0

result = calculate_cashflow(display_income, display_expense, display_investment)
metric1, metric2, metric3 = st.columns(3)
with metric1:
    metric_card("本月结余", format_currency(result["saving"]), "收入减去支出", "positive" if result["saving"] >= 0 else "negative")
with metric2:
    metric_card("储蓄率", format_percent(result["saving_rate"]), "结余占收入比例", "positive" if result["saving_rate"] >= 0.3 else "warning")
with metric3:
    metric_card("现金流状态", result["status"], "用于判断本月投入能力")

df = load_recent_cashflow_records(12)
if not df.empty:
    anomaly = detect_expense_anomaly(display_expense, df.sort_values("month")["expense"].tolist())
    st.info(anomaly)

    chart_df = df.sort_values("month").copy()
    amount_long = chart_df.melt(
        id_vars="month",
        value_vars=["income", "expense", "saving", "investment_amount"],
        var_name="项目",
        value_name="金额（元）",
    )
    amount_long["项目"] = amount_long["项目"].map(
        {
            "income": "收入",
            "expense": "支出",
            "saving": "结余",
            "investment_amount": "当月实际投资金额",
        }
    )
    amount_long = amount_long.rename(columns={"month": "月份"})
    amount_fig = px.bar(
        amount_long,
        x="月份",
        y="金额（元）",
        color="项目",
        barmode="group",
        title="最近 12 个月现金流",
        labels={"月份": "月份", "金额（元）": "金额（元）", "项目": "项目"},
    )
    amount_fig.update_layout(xaxis_title="月份", yaxis_title="金额（元）", legend_title_text="项目")
    amount_fig.update_layout(paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14", font_color="#CBD5E1")
    amount_fig.update_xaxes(gridcolor="#263241")
    amount_fig.update_yaxes(gridcolor="#263241")
    st.plotly_chart(amount_fig, use_container_width=True)

    rate_df = chart_df.rename(columns={"month": "月份", "saving_rate": "储蓄率"})
    rate_fig = px.line(
        rate_df,
        x="月份",
        y="储蓄率",
        title="最近 12 个月储蓄率",
        markers=True,
        labels={"月份": "月份", "储蓄率": "储蓄率"},
    )
    rate_fig.update_layout(xaxis_title="月份", yaxis_title="储蓄率", legend_title_text="项目")
    rate_fig.update_yaxes(tickformat=".0%")
    rate_fig.update_layout(paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14", font_color="#CBD5E1")
    rate_fig.update_xaxes(gridcolor="#263241")
    rate_fig.update_yaxes(gridcolor="#263241")
    st.plotly_chart(rate_fig, use_container_width=True)

    display_df = translate_columns(df)
    if "储蓄率" in display_df.columns:
        display_df["储蓄率"] = display_df["储蓄率"].apply(format_percent)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("暂无现金流记录，请先填写并保存本月现金流。")

show_risk_notice()
