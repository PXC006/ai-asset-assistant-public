import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st

from src.config import RISK_NOTICE
from src.database import init_db, load_latest_decision_profile
from src.auth import require_user_key
from src.ui_style import apply_global_style
from src.ui_components import format_currency, metric_card, page_header, info_box


st.set_page_config(
    page_title="AI复利资产助手",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_global_style()
init_db()
require_user_key()
profile = load_latest_decision_profile()
has_saved_profile = not profile.get("is_default", True)


def target_summary(profile_data: dict) -> tuple[str, str]:
    target_age = int(profile_data.get("target_age", 0) or 0)
    target_asset = float(profile_data.get("target_asset", 0) or 0)
    if target_age > 0 and target_asset > 0:
        asset_text = f"{target_asset / 10000:.0f}万" if target_asset >= 10000 else format_currency(target_asset)
        return f"{target_age}岁 {asset_text}", "已读取本月投资决策中心保存的目标"
    return "目标未设置", "请先进入“本月投资决策中心”填写目标和当前资产。"

page_header("AI 复利资产助手", "从工资结余出发，管理现金流、控制风险、长期配置基金/ETF。")

st.markdown(
    """
    这是一个本地运行的个人长期复利资产管理工具。它不做自动交易，不预测短期涨跌，
    只帮助你把长期目标、现金流、备用金、资产配置和月度复盘放在同一个系统里。
    """
)

col1, col2, col3 = st.columns(3)
with col1:
    value, subtitle = target_summary(profile)
    metric_card("目标状态", value, subtitle, "positive" if has_saved_profile else "warning")
with col2:
    metric_card("收益情景", "3% / 5% / 8%", "用于情景测算")
with col3:
    metric_card("风险偏好", str(profile.get("risk_preference", "稳健") or "稳健"), "辅助分析，不预测短期涨跌")

st.subheader("建议使用顺序")
st.write("1. 先进入本月投资决策中心设置目标和当前资产。")
st.write("2. 每月记录现金流和实际投资金额。")
st.write("3. 检查备用金是否足够，再看资产方向推荐。")
st.write("4. 对基金/ETF 做基础分析，最后生成月报复盘。")

info_box(RISK_NOTICE, "warning")
