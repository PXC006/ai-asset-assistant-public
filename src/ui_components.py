import html

import streamlit as st

from .config import PUBLIC_EMPTY_MODE, PUBLIC_MODE_NOTICE
from .auth import require_user_key


STATUS_CLASS = {
    "positive": "ui-value-positive",
    "negative": "ui-value-negative",
    "warning": "ui-value-warning",
    "neutral": "ui-value-neutral",
}


def page_header(title: str, subtitle: str = "") -> None:
    require_user_key()
    if PUBLIC_EMPTY_MODE:
        st.caption(PUBLIC_MODE_NOTICE)
        st.caption("体验数据和缓存数据可能因云端应用重启、休眠或更新而丢失。")
    st.markdown(f"# {html.escape(title)}")
    if subtitle:
        st.caption(subtitle)


def metric_card(title: str, value, subtitle: str = "", status: str = "neutral") -> None:
    value_class = STATUS_CLASS.get(status, STATUS_CLASS["neutral"])
    st.markdown(
        f"""
        <div class="ui-metric-card">
            <div class="ui-metric-title">{html.escape(str(title))}</div>
            <div class="ui-metric-value {value_class}">{html.escape(str(value))}</div>
            <div class="ui-metric-subtitle">{html.escape(str(subtitle))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_box(text: str, type: str = "info") -> None:
    css_type = {
        "info": "ui-info",
        "success": "ui-success",
        "warning": "ui-warning",
        "danger": "ui-danger",
    }.get(type, "ui-info")
    st.markdown(f'<div class="ui-info-box {css_type}">{html.escape(str(text))}</div>', unsafe_allow_html=True)


def section_card(title: str, content: str = "") -> None:
    st.markdown(
        f"""
        <div class="ui-section-card">
            <h3>{html.escape(str(title))}</h3>
            <p>{html.escape(str(content))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(risk_level: str) -> str:
    text = str(risk_level or "未评级")
    if "低" in text:
        cls = "ui-badge-green"
    elif "高" in text:
        cls = "ui-badge-red" if "中高" not in text else "ui-badge-orange"
    elif "中" in text:
        cls = "ui-badge-blue"
    else:
        cls = "ui-badge"
    return f'<span class="ui-badge {cls}">{html.escape(text)}</span>'


def category_badge(category: str) -> str:
    text = str(category or "未分类")
    if "核心" in text or "评分较高" in text:
        cls = "ui-badge-gold"
    elif "高风险" in text or "暂不" in text:
        cls = "ui-badge-red" if "暂不" in text else "ui-badge-orange"
    elif "观察" in text:
        cls = "ui-badge-blue"
    else:
        cls = "ui-badge"
    return f'<span class="ui-badge {cls}">{html.escape(text)}</span>'


def format_currency(value) -> str:
    return f"{float(value or 0):,.0f} 元"


def format_percent(value) -> str:
    return f"{float(value or 0):.2%}"
