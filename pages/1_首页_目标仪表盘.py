import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import CORE_RETURN_OPTIONS, STAGE_GOALS
from src.auth import render_user_sidebar, require_user_key
from src.database import load_latest_decision_profile
from src.decision_engine import generate_monthly_investment_plan
from src.goal_calculator import calculate_future_value, calculate_progress_status, calculate_required_monthly_investment
from src.utils import format_currency, show_risk_notice
from src.ui_style import apply_global_style
from src.ui_components import info_box, metric_card, page_header


st.set_page_config(page_title="首页目标仪表盘", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
apply_global_style()
require_user_key()
render_user_sidebar()

page_header("首页｜目标仪表盘", "读取本月投资决策中心最新保存的数据，显示目标进度、现金安全垫和本月状态。")

try:
    profile = load_latest_decision_profile()
except Exception as exc:
    st.error(f"读取个人配置失败：{exc}")
    profile = {}

has_saved_profile = not profile.get("is_default", True)

if not has_saved_profile:
    info_box("还没有保存过本月投资决策中心数据，当前全部显示 0 或未设置。", "warning")
else:
    info_box(f"数据来源：本月投资决策中心最新保存的数据。更新时间：{profile.get('updated_at', '-')}", "success")

current_age = int(profile.get("current_age", 0) or 0)
target_age = int(profile.get("target_age", 0) or 0)
target_asset = float(profile.get("target_asset", 0) or 0)
current_asset = float(profile.get("total_asset", 0))
monthly_investment = float(profile.get("monthly_investment", 0) or 0)
monthly_expense = float(profile.get("monthly_expense", 0) or 0)
emergency_fund = float(profile.get("emergency_fund", 0))
risk_preference = profile.get("risk_preference", "稳健") or "稳健"

years = max(target_age - current_age, 0)
expected_5 = calculate_future_value(current_asset, monthly_investment, 0.05, years)
status = calculate_progress_status(expected_5, target_asset)
required_5 = calculate_required_monthly_investment(target_asset, current_asset, 0.05, years)

asset_amounts = {
    "cash": float(profile.get("cash_amount", 0)),
    "bond": float(profile.get("bond_amount", 0)),
    "broad_index": float(profile.get("broad_index_amount", 0)),
    "global_index": float(profile.get("global_index_amount", 0)),
    "sector_theme": float(profile.get("sector_theme_amount", 0)),
    "active_fund": float(profile.get("active_fund_amount", 0)),
    "stock": float(profile.get("stock_amount", 0)),
    "quant_experiment": float(profile.get("quant_experiment_amount", 0)),
}
if not any(asset_amounts.values()):
    asset_amounts["cash"] = emergency_fund

plan = None
if has_saved_profile:
    plan = generate_monthly_investment_plan(
        current_age=current_age,
        target_age=target_age,
        target_asset=target_asset,
        total_asset=current_asset,
        emergency_fund=emergency_fund,
        monthly_expense=monthly_expense,
        monthly_investment=monthly_investment,
        asset_amounts=asset_amounts,
        risk_preference=risk_preference,
    )


def setting_text(value, suffix: str = "") -> str:
    return f"{value}{suffix}" if value else "未设置"

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("当前总资产", format_currency(current_asset), f"距离目标年龄还有 {years} 年" if target_age and current_age else "目标年龄未设置")
with col2:
    metric_card("目标资产", format_currency(target_asset), f"目标年龄：{setting_text(target_age, ' 岁')}", "positive")
with col3:
    metric_card("距离目标", format_currency(max(target_asset - current_asset, 0)), "还需要继续积累" if target_asset else "目标资产未设置", "warning")
with col4:
    metric_card("本月可投资金额", format_currency(monthly_investment), f"目标进度：{status}" if target_asset else "目标进度未设置", "neutral")

st.subheader("下一步建议")
if not has_saved_profile:
    info_box("未设置。请先进入本月投资决策中心填写并保存基础目标、月支出、本月可投资金额和当前资产结构。", "info")
elif plan["should_fill_emergency_fund_first"]:
    info_box("本月最重要的一件事：先补备用金。现金安全垫没达标时，不建议急着加个股、行业主题或量化实验仓。", "warning")
elif plan["weights"].get("broad_index", 0) < 0.40:
    info_box("本月最重要的一件事：优先搭建宽基指数基金/ETF这类长期核心资产。", "info")
else:
    info_box("本月可以按资产配置计划继续推进，注意不要让单一高风险资产占比过高。", "success")

if plan:
    for warning in plan["warnings"][:3]:
        st.write(f"- {warning}")
st.page_link("pages/2_本月投资决策中心.py", label="进入本月投资决策中心", icon="➡️")

rows = []
for annual_return in CORE_RETURN_OPTIONS:
    value = calculate_future_value(current_asset, monthly_investment, annual_return, years)
    rows.append({"年化假设": f"{annual_return:.0%}", "目标年龄预计资产": value, "进度": calculate_progress_status(value, target_asset)})
st.subheader("目标测算")
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

st.write(
    f"按照当前每月投入 {format_currency(monthly_investment)}，假设年化 5%，"
    f"{setting_text(target_age, ' 岁')}预计资产约为 {format_currency(expected_5)}。"
    f"若想提高达成概率，可考虑把月投入逐步提升到 {format_currency(required_5)} 左右。"
)

projection_rows = []
for annual_return in CORE_RETURN_OPTIONS:
    for month in range(years * 12 + 1):
        projection_rows.append(
            {
                "年份": current_age + month / 12,
                "预计资产": calculate_future_value(current_asset, monthly_investment, annual_return, month / 12),
                "年化假设": f"{annual_return:.0%}",
            }
        )
if projection_rows:
    df = pd.DataFrame(projection_rows)
    fig = px.line(df, x="年份", y="预计资产", color="年化假设", title="资产增长预测曲线")
    fig.add_hline(y=target_asset, line_dash="dash", annotation_text="目标资产")
    fig.update_layout(paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14", font_color="#CBD5E1")
    fig.update_xaxes(gridcolor="#263241", title="年龄")
    fig.update_yaxes(gridcolor="#263241", title="预计资产（元）")
    st.plotly_chart(fig, width="stretch")

st.subheader("阶段目标")
if has_saved_profile:
    stage_rows = [{"年龄": age, "目标区间": f"{low/10000:.0f}-{high/10000:.0f} 万"} for age, (low, high) in STAGE_GOALS.items()]
    if stage_rows:
        st.dataframe(pd.DataFrame(stage_rows), width="stretch", hide_index=True)
    else:
        info_box("暂无阶段参考。你可以根据自己保存的目标年龄和目标资产做长期拆分。", "info")
else:
    info_box("目标未设置。保存本月投资决策中心数据后，这里会展示阶段参考。", "info")
show_risk_notice()

