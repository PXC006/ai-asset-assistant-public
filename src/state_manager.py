import math
from typing import Any
from datetime import date

import streamlit as st

from .cashflow import calculate_cashflow
from .database import (
    DEFAULT_DECISION_PROFILE,
    load_cashflow_record_by_month,
    load_latest_decision_profile,
    load_recent_cashflow_records,
    save_cashflow_record,
    save_decision_profile,
)


DECISION_FIELD_KEYS = {
    "profile_name": "decision_profile_name",
    "current_age": "decision_current_age",
    "target_age": "decision_target_age",
    "target_asset": "decision_target_asset",
    "total_asset": "decision_total_asset",
    "emergency_fund": "decision_emergency_fund",
    "monthly_expense": "decision_monthly_expense",
    "monthly_investment": "decision_monthly_investment",
    "cash_amount": "decision_cash_amount",
    "bond_amount": "decision_bond_amount",
    "broad_index_amount": "decision_broad_index_amount",
    "global_index_amount": "decision_global_index_amount",
    "sector_theme_amount": "decision_sector_theme_amount",
    "active_fund_amount": "decision_active_fund_amount",
    "stock_amount": "decision_stock_amount",
    "quant_experiment_amount": "decision_quant_experiment_amount",
    "risk_preference": "decision_risk_preference",
}

CASHFLOW_FIELD_KEYS = {
    "month": "cashflow_page_month",
    "income": "cashflow_page_income",
    "expense": "cashflow_page_expense",
    "investment_amount": "cashflow_page_investment_amount",
    "special_expense_note": "cashflow_page_special_expense_note",
}

STATE_MANAGER_VERSION = "2026-06-28-state-v3"
VALID_RISK_PREFERENCES = {"保守", "稳健", "稳健偏进取", "激进"}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(math.isnan(value))
    except (TypeError, ValueError):
        return False


def _defaulted(profile: dict, field: str) -> Any:
    value = profile.get(field)
    if _is_missing(value) or value == "":
        return DEFAULT_DECISION_PROFILE[field]
    if field == "risk_preference" and value not in VALID_RISK_PREFERENCES:
        return DEFAULT_DECISION_PROFILE[field]
    return value


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _float_value(value: Any, default: float = 0.0) -> float:
    if _is_missing(value) or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mark_loaded_meta(profile: dict) -> None:
    st.session_state["decision_profile_loaded"] = True
    st.session_state["decision_profile_updated_at"] = profile.get("updated_at", "")
    st.session_state["decision_profile_is_default"] = bool(profile.get("is_default", True))
    st.session_state.setdefault("decision_data_dirty", False)


def _decision_keys_exist() -> bool:
    return all(key in st.session_state for key in DECISION_FIELD_KEYS.values())


def clear_decision_state() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("decision_"):
            del st.session_state[key]


def load_decision_state_from_database() -> dict:
    profile = load_latest_decision_profile()
    for field, key in DECISION_FIELD_KEYS.items():
        st.session_state[key] = _defaulted(profile, field)
    st.session_state["decision_data_dirty"] = False
    _mark_loaded_meta(profile)
    st.session_state["decision_state_manager_version"] = STATE_MANAGER_VERSION
    return profile


def init_decision_state() -> None:
    if (
        st.session_state.get("decision_profile_loaded")
        and st.session_state.get("decision_state_manager_version") == STATE_MANAGER_VERSION
        and _decision_keys_exist()
    ):
        if st.session_state.get("decision_risk_preference") not in VALID_RISK_PREFERENCES:
            st.session_state["decision_risk_preference"] = DEFAULT_DECISION_PROFILE["risk_preference"]
        return

    load_decision_state_from_database()


def get_decision_state_as_profile() -> dict:
    profile = {}
    for field, key in DECISION_FIELD_KEYS.items():
        value = st.session_state.get(key, DEFAULT_DECISION_PROFILE[field])
        profile[field] = DEFAULT_DECISION_PROFILE[field] if _is_missing(value) or value == "" else value
    profile["profile_name"] = profile.get("profile_name") or "默认方案"
    return profile


def sync_decision_to_emergency_state() -> None:
    if "emergency_page_monthly_expense" in st.session_state:
        st.session_state["emergency_page_monthly_expense"] = st.session_state["decision_monthly_expense"]
    if "emergency_page_emergency_fund" in st.session_state:
        st.session_state["emergency_page_emergency_fund"] = st.session_state["decision_emergency_fund"]
    if "emergency_page_loaded" in st.session_state:
        st.session_state["emergency_page_data_dirty"] = False
        st.session_state["emergency_page_is_default"] = False
        st.session_state["emergency_page_updated_at"] = "刚刚"


def sync_emergency_to_decision_state() -> None:
    if "decision_monthly_expense" in st.session_state:
        st.session_state["decision_monthly_expense"] = st.session_state["emergency_page_monthly_expense"]
    if "decision_emergency_fund" in st.session_state:
        st.session_state["decision_emergency_fund"] = st.session_state["emergency_page_emergency_fund"]
    if "decision_profile_loaded" in st.session_state:
        st.session_state["decision_profile_is_default"] = False
        st.session_state["decision_profile_updated_at"] = "刚刚"


def save_decision_state() -> dict:
    profile = get_decision_state_as_profile()
    save_decision_profile(profile)
    st.session_state["decision_data_dirty"] = False
    st.session_state["decision_profile_is_default"] = False
    st.session_state["decision_profile_updated_at"] = "刚刚"
    sync_decision_to_emergency_state()
    return profile


def reset_decision_state_to_default() -> None:
    for field, key in DECISION_FIELD_KEYS.items():
        st.session_state[key] = DEFAULT_DECISION_PROFILE[field]
    st.session_state["decision_profile_loaded"] = True
    st.session_state["decision_data_dirty"] = True
    st.session_state["decision_profile_is_default"] = True
    st.session_state["decision_profile_updated_at"] = ""
    st.session_state["decision_state_manager_version"] = STATE_MANAGER_VERSION


def init_emergency_state() -> None:
    if (
        st.session_state.get("emergency_page_loaded")
        and st.session_state.get("emergency_state_manager_version") == STATE_MANAGER_VERSION
    ):
        return

    profile = load_latest_decision_profile()
    saved_monthly_expense = float(_defaulted(profile, "monthly_expense"))
    saved_emergency_fund = float(_defaulted(profile, "emergency_fund"))

    st.session_state["emergency_page_monthly_expense"] = saved_monthly_expense
    st.session_state["emergency_page_emergency_fund"] = saved_emergency_fund
    st.session_state["emergency_page_loaded"] = True
    st.session_state["emergency_page_data_dirty"] = False
    st.session_state["emergency_page_updated_at"] = profile.get("updated_at", "")
    st.session_state["emergency_page_is_default"] = bool(profile.get("is_default", True))
    st.session_state["emergency_state_manager_version"] = STATE_MANAGER_VERSION


def save_emergency_state() -> dict:
    profile = load_latest_decision_profile()
    profile["monthly_expense"] = st.session_state.get("emergency_page_monthly_expense", DEFAULT_DECISION_PROFILE["monthly_expense"])
    profile["emergency_fund"] = st.session_state.get("emergency_page_emergency_fund", DEFAULT_DECISION_PROFILE["emergency_fund"])
    save_decision_profile(profile)
    st.session_state["emergency_page_data_dirty"] = False
    st.session_state["emergency_page_is_default"] = False
    st.session_state["emergency_page_updated_at"] = "刚刚"
    sync_emergency_to_decision_state()
    return profile


def reset_emergency_state_to_default() -> None:
    st.session_state["emergency_page_monthly_expense"] = DEFAULT_DECISION_PROFILE["monthly_expense"]
    st.session_state["emergency_page_emergency_fund"] = DEFAULT_DECISION_PROFILE["emergency_fund"]
    st.session_state["emergency_page_data_dirty"] = True


def _cashflow_default_values(month: str) -> dict:
    recent = load_recent_cashflow_records(1)
    income = 0.0
    expense = 0.0
    if not recent.empty:
        income = _float_value(recent.iloc[0].get("income"), 0.0)
        expense = _float_value(recent.iloc[0].get("expense"), 0.0)
    return {
        "month": month,
        "income": income,
        "expense": expense,
        "investment_amount": 0.0,
        "special_expense_note": "",
    }


def load_cashflow_state_for_month(month: str | None = None) -> dict:
    month = (month or _current_month()).strip() or _current_month()
    record = load_cashflow_record_by_month(month)
    values = _cashflow_default_values(month) if record is None else {
        "month": record.get("month") or month,
        "income": _float_value(record.get("income")),
        "expense": _float_value(record.get("expense")),
        "investment_amount": _float_value(record.get("investment_amount")),
        "special_expense_note": record.get("special_expense_note") or "",
    }
    for field, key in CASHFLOW_FIELD_KEYS.items():
        st.session_state[key] = values[field]
    st.session_state["cashflow_page_loaded"] = True
    st.session_state["cashflow_page_loaded_month"] = month
    st.session_state["cashflow_page_has_saved_record"] = record is not None
    st.session_state["cashflow_page_data_dirty"] = False
    st.session_state["cashflow_page_updated_at"] = "" if record is None else record.get("updated_at") or record.get("created_at", "")
    return values


def init_cashflow_state() -> None:
    if st.session_state.get("cashflow_page_loaded"):
        return
    load_cashflow_state_for_month(_current_month())


def handle_cashflow_month_change() -> None:
    month = st.session_state.get("cashflow_page_month") or _current_month()
    if month != st.session_state.get("cashflow_page_loaded_month"):
        load_cashflow_state_for_month(month)


def mark_cashflow_dirty() -> None:
    st.session_state["cashflow_page_data_dirty"] = True


def clear_cashflow_current_month_inputs() -> None:
    month = st.session_state.get("cashflow_page_month") or _current_month()
    st.session_state["cashflow_page_income"] = 0.0
    st.session_state["cashflow_page_expense"] = 0.0
    st.session_state["cashflow_page_investment_amount"] = 0.0
    st.session_state["cashflow_page_special_expense_note"] = ""
    st.session_state["cashflow_page_loaded_month"] = month
    st.session_state["cashflow_page_has_saved_record"] = False
    st.session_state["cashflow_page_data_dirty"] = True


def get_cashflow_state_as_record() -> dict:
    income = _float_value(st.session_state.get("cashflow_page_income"))
    expense = _float_value(st.session_state.get("cashflow_page_expense"))
    investment_amount = _float_value(st.session_state.get("cashflow_page_investment_amount"))
    result = calculate_cashflow(income, expense, investment_amount)
    return {
        "month": st.session_state.get("cashflow_page_month") or _current_month(),
        "income": income,
        "expense": expense,
        "saving": result["saving"],
        "saving_rate": result["saving_rate"],
        "investment_amount": investment_amount,
        "special_expense_note": st.session_state.get("cashflow_page_special_expense_note", ""),
    }


def save_cashflow_state() -> dict:
    record = get_cashflow_state_as_record()
    save_cashflow_record(record)
    st.session_state["cashflow_page_data_dirty"] = False
    st.session_state["cashflow_page_loaded"] = True
    st.session_state["cashflow_page_loaded_month"] = record["month"]
    st.session_state["cashflow_page_has_saved_record"] = True
    st.session_state["cashflow_page_updated_at"] = "刚刚"
    return record


def sync_cashflow_expense_to_emergency_state() -> dict:
    profile = load_latest_decision_profile()
    profile["monthly_expense"] = _float_value(st.session_state.get("cashflow_page_expense"))
    save_decision_profile(profile)
    if "emergency_page_monthly_expense" in st.session_state:
        st.session_state["emergency_page_monthly_expense"] = profile["monthly_expense"]
        st.session_state["emergency_page_data_dirty"] = False
    if "decision_monthly_expense" in st.session_state:
        st.session_state["decision_monthly_expense"] = profile["monthly_expense"]
    return profile
