from datetime import date

import plotly.express as px
import streamlit as st

from src.database import add_asset, delete_by_id, fetch_df
from src.utils import show_risk_notice, translate_columns
from src.ui_style import apply_global_style
from src.ui_components import info_box, page_header


st.set_page_config(page_title="自选池和持仓池", page_icon="📌", layout="wide", initial_sidebar_state="expanded")
apply_global_style()

page_header("自选池和持仓池", "区分候选观察和真实持仓，让后续资产配置、再平衡和月报有数据可用。")
info_box("自选池是你的观察名单，表示你想继续关注，但不代表已经买入。", "info")
info_box("持仓池是你真实已经买入的资产，用于后续汇总资产配置和风险。", "info")

tab1, tab2 = st.tabs(["自选池：准备长期观察", "持仓池：真实已经买入"])

with tab1:
    watch_df = fetch_df("SELECT * FROM watchlist ORDER BY id DESC")
    if watch_df.empty:
        st.warning("自选池还没有标的。建议先去“候选标的池”选择方向，再加入自选池。")
        st.page_link("pages/5_候选标的池.py", label="去候选标的池", icon="➡️")
    else:
        st.dataframe(translate_columns(watch_df), use_container_width=True, hide_index=True)
        st.subheader("自选池操作")
        ids = watch_df["id"].astype(int).tolist()
        selected_id = st.selectbox(
            "选择一个自选标的",
            ids,
            format_func=lambda x: f"{x} - {watch_df.loc[watch_df['id'] == x, 'name'].iloc[0]}",
            key="watch_selected_id",
        )
        selected = watch_df[watch_df["id"] == selected_id].iloc[0].to_dict()
        c1, c2, _ = st.columns(3)
        if c1.button("删除该自选标的"):
            delete_by_id("watchlist", int(selected_id))
            st.success("已删除。请刷新页面查看最新列表。")
        with c2:
            st.page_link("pages/6_基金ETF分析.py", label="分析该标的", icon="🔎")
        st.caption("分析页打开后，可以把代码复制到输入框；后续可继续优化为自动带参数跳转。")

        with st.expander("转入持仓池：我已经真实买入了这个标的"):
            with st.form("move_to_holding"):
                h1, h2, h3, h4 = st.columns(4)
                buy_amount = h1.number_input("买入金额", min_value=0.0, value=1000.0, step=100.0)
                cost = h2.number_input("成本", min_value=0.0, value=buy_amount, step=100.0)
                current_value = h3.number_input("当前金额", min_value=0.0, value=buy_amount, step=100.0)
                buy_date = h4.date_input("买入日期", value=date.today())
                if st.form_submit_button("保存到持仓池"):
                    add_asset(
                        {
                            "asset_type": selected.get("asset_type", ""),
                            "asset_name": selected.get("name", ""),
                            "asset_code": selected.get("code", ""),
                            "amount": buy_amount,
                            "cost": cost,
                            "current_value": current_value,
                            "risk_level": selected.get("risk_level", "中风险"),
                            "buy_date": buy_date.isoformat(),
                        }
                    )
                    st.success("已转入持仓池。自选记录会保留，方便继续观察。")

with tab2:
    asset_df = fetch_df("SELECT * FROM asset_records ORDER BY id DESC")
    if asset_df.empty:
        st.warning("持仓池还没有资产。只有真实买入后，才建议加入持仓池。")
    else:
        st.dataframe(translate_columns(asset_df), use_container_width=True, hide_index=True)
        pie_df = (
            asset_df.groupby("asset_type", as_index=False)["current_value"]
            .sum()
            .rename(columns={"asset_type": "资产类型", "current_value": "当前金额"})
        )
        fig = px.pie(
            pie_df,
            names="资产类型",
            values="当前金额",
            title="持仓资产类别占比",
            labels={"资产类型": "资产类型", "当前金额": "当前金额"},
        )
        fig.update_layout(legend_title_text="资产类型")
        st.plotly_chart(fig, use_container_width=True)

        delete_asset_id = st.selectbox("选择要删除的持仓 ID", asset_df["id"].astype(int).tolist(), key="delete_asset_id")
        if st.button("删除该持仓"):
            delete_by_id("asset_records", int(delete_asset_id))
            st.success("已删除。请刷新页面查看最新列表。")

    with st.expander("手动添加真实持仓"):
        with st.form("manual_holding"):
            c1, c2, c3, c4 = st.columns(4)
            asset_code = c1.text_input("代码")
            asset_name = c2.text_input("名称")
            asset_type = c3.selectbox(
                "资产类型",
                [
                    "现金/货币基金",
                    "债券/短债",
                    "宽基指数基金/ETF",
                    "海外/全球指数",
                    "行业基金/主题ETF",
                    "主动基金",
                    "个股",
                    "量化实验仓",
                ],
            )
            buy_date = c4.date_input("买入日期", value=date.today())
            d1, d2, d3 = st.columns(3)
            amount = d1.number_input("买入金额", min_value=0.0, value=0.0, step=100.0)
            cost = d2.number_input("成本", min_value=0.0, value=0.0, step=100.0)
            current_value = d3.number_input("当前金额", min_value=0.0, value=0.0, step=100.0)
            if st.form_submit_button("添加到持仓池"):
                add_asset(
                    {
                        "asset_type": asset_type,
                        "asset_name": asset_name,
                        "asset_code": asset_code,
                        "amount": amount,
                        "cost": cost,
                        "current_value": current_value,
                        "risk_level": "中风险",
                        "buy_date": buy_date.isoformat(),
                    }
                )
                st.success("已添加到持仓池。")

st.info("以上内容仅用于个人资产管理辅助分析，不构成投资建议。候选观察不等于买入建议，请结合自身情况独立决策。")
show_risk_notice()
