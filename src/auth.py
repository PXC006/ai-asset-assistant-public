import re

import streamlit as st


USER_KEY_PATTERN = re.compile(r"^[a-z0-9_-]{3,32}$")


def normalize_user_key(value: str) -> str:
    return str(value or "").strip().lower()


def is_valid_user_key(value: str) -> bool:
    key = normalize_user_key(value)
    return bool(USER_KEY_PATTERN.fullmatch(key))


def current_user_key(default: str = "") -> str:
    try:
        return normalize_user_key(st.session_state.get("current_user_key", default))
    except Exception:
        return default


def clear_current_user_session() -> None:
    for key in list(st.session_state.keys()):
        if key != "current_user_key":
            del st.session_state[key]


def render_entry_gate() -> bool:
    if current_user_key():
        return True

    st.title("AI复利资产助手｜朋友体验版")
    st.caption("请输入你的密室码，进入你的个人体验空间。")
    st.write("你可以自己设置一个容易记住的密室码，例如：")
    st.write("friend001 / test003 / px003-k7 / xiaowang / laoli2026")
    st.info("请记住你的密室码。下次输入同一个密室码，可以继续查看自己的体验数据。")

    key = st.text_input("请输入密室码 / 体验邀请码", key="entry_user_key")
    if st.button("进入我的密室", type="primary"):
        normalized = normalize_user_key(key)
        if not is_valid_user_key(normalized):
            st.warning("密室码只能包含英文、数字、下划线或中横线，长度 3–32 位。")
        else:
            st.session_state["current_user_key"] = normalized
            clear_current_user_session()
            st.session_state["current_user_key"] = normalized
            st.rerun()

    st.warning(
        "当前密室码仅用于朋友体验版区分数据，不是正式账号密码。"
        "如果别人知道你的密室码，也可能进入同一个体验空间。"
        "请勿填写敏感个人资产信息。本工具仅用于个人资产管理辅助分析，不构成投资建议。"
    )
    st.stop()
    return False


def render_user_sidebar() -> None:
    key = current_user_key()
    if not key:
        return
    st.sidebar.caption(f"当前密室码：{key}")
    st.sidebar.info("朋友体验版｜密室码仅用于区分数据｜不是正式账号系统｜请勿填写敏感个人资产信息｜不构成投资建议")
    st.sidebar.caption("体验数据和缓存数据可能因云端应用重启、休眠或更新而丢失。")
    if st.sidebar.button("切换密室码"):
        st.session_state.pop("current_user_key", None)
        clear_current_user_session()
        st.rerun()
    st.sidebar.divider()
    st.sidebar.checkbox("确认清空当前密室数据", key="confirm_clear_current_room")
    if st.sidebar.button("清空当前密室数据"):
        if not st.session_state.get("confirm_clear_current_room"):
            st.sidebar.warning("请先勾选确认，只会清空当前密室码下的个人体验数据。")
        else:
            from .database import clear_user_data

            clear_user_data(key)
            clear_current_user_session()
            st.session_state["current_user_key"] = key
            st.session_state["confirm_clear_current_room"] = False
            st.sidebar.success("当前密室数据已清空。")
            st.rerun()


def require_user_key() -> str:
    render_entry_gate()
    render_user_sidebar()
    return current_user_key()
