import streamlit as st

from src.database import load_latest_decision_profile, save_decision_profile
from src.emergency_fund import emergency_targets, evaluate_emergency_fund
from src.utils import format_currency, show_risk_notice
from src.ui_style import apply_global_style
from src.ui_components import info_box, metric_card, page_header


st.set_page_config(page_title="备用金管理", page_icon="🛟", layout="wide", initial_sidebar_state="expanded")
apply_global_style()

page_header("备用金管理", "管理现金安全垫，先保证生活和突发支出，再推进长期投资计划。")

profile = load_latest_decision_profile()
current_monthly_expense = float(profile.get("monthly_expense", 3000.0) or 0.0)
current_emergency_fund = float(profile.get("emergency_fund", 0.0) or 0.0)
form_version = str(profile.get("updated_at") or "new").replace(" ", "_").replace(":", "-")

info_box(f"已从本地数据库加载备用金配置。更新时间：{profile.get('updated_at') or '-'}", "success")

with st.form(f"emergency_fund_form_{form_version}"):
    col1, col2 = st.columns(2)
    monthly_expense = col1.number_input(
        "月支出",
        min_value=0.0,
        value=current_monthly_expense,
        step=100.0,
        key=f"emergency_monthly_expense_{form_version}",
    )
    emergency_fund = col2.number_input(
        "当前备用金金额",
        min_value=0.0,
        value=current_emergency_fund,
        step=100.0,
        key=f"emergency_fund_{form_version}",
    )
    submitted = st.form_submit_button("保存备用金配置", type="primary")

if submitted:
    try:
        latest_profile = load_latest_decision_profile()
        latest_profile["monthly_expense"] = monthly_expense
        latest_profile["emergency_fund"] = emergency_fund
        save_decision_profile(latest_profile)
        st.success("备用金配置已保存。")
        st.rerun()
    except Exception as exc:
        st.error(f"保存备用金配置失败：{exc}")

display_profile = load_latest_decision_profile()
display_monthly_expense = float(display_profile.get("monthly_expense", 0.0) or 0.0)
display_emergency_fund = float(display_profile.get("emergency_fund", 0.0) or 0.0)
targets = emergency_targets(display_monthly_expense)
evaluation = (
    evaluate_emergency_fund(display_emergency_fund, display_monthly_expense)
    if display_monthly_expense > 0
    else {"等级": "待填写", "建议": "请先填写月支出，系统才能判断备用金是否充足。"}
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("最低备用金", format_currency(targets["最低备用金"]), "约 3 个月支出", "warning")
with col2:
    metric_card("标准备用金", format_currency(targets["标准备用金"]), "约 6 个月支出", "neutral")
with col3:
    metric_card("安心备用金", format_currency(targets["安心备用金"]), "约 12 个月支出", "positive")

if display_monthly_expense > 0:
    covered_months = display_emergency_fund / display_monthly_expense
    with col4:
        metric_card("可覆盖月数", f"{covered_months:.1f} 个月", "当前备用金覆盖能力", "positive" if covered_months >= 6 else "warning")
else:
    with col4:
        metric_card("可覆盖月数", "待填写", "请先填写月支出", "warning")

metric_card("当前备用金等级", evaluation["等级"], evaluation["建议"], "positive" if "6" in evaluation["等级"] or "12" in evaluation["等级"] else "warning")
st.write(evaluation["建议"])

if display_monthly_expense <= 0:
    info_box("请先填写月支出，系统才能计算备用金覆盖月份。", "warning")
else:
    progress_base = targets["安心备用金"] if targets["安心备用金"] else 1
    st.progress(min(display_emergency_fund / progress_base, 1.0))

show_risk_notice()
