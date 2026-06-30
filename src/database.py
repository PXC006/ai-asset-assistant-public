import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from .auth import current_user_key
from .config import APP_VERSION, DATA_DIR, DB_PATH, DEFAULT_CURRENT_AGE, DEFAULT_MONTHLY_EXPENSE, DEFAULT_MONTHLY_INVESTMENT, DEFAULT_TARGET_AGE, DEFAULT_TARGET_ASSET


DEFAULT_DECISION_PROFILE = {
    "profile_name": "默认方案",
    "current_age": DEFAULT_CURRENT_AGE,
    "target_age": DEFAULT_TARGET_AGE,
    "target_asset": DEFAULT_TARGET_ASSET,
    "total_asset": 0.0,
    "emergency_fund": 0.0,
    "monthly_expense": DEFAULT_MONTHLY_EXPENSE,
    "monthly_investment": DEFAULT_MONTHLY_INVESTMENT,
    "cash_amount": 0.0,
    "bond_amount": 0.0,
    "broad_index_amount": 0.0,
    "global_index_amount": 0.0,
    "sector_theme_amount": 0.0,
    "active_fund_amount": 0.0,
    "stock_amount": 0.0,
    "quant_experiment_amount": 0.0,
    "risk_preference": "稳健",
    "updated_at": "",
    "is_default": True,
}

VALID_RISK_PREFERENCES = {"保守", "稳健", "稳健偏进取", "激进"}


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _clean_decision_profile(raw_data: dict | None) -> dict:
    profile = DEFAULT_DECISION_PROFILE.copy()
    raw_data = raw_data or {}
    for key, default_value in DEFAULT_DECISION_PROFILE.items():
        if key in {"is_default", "updated_at"}:
            continue
        value = raw_data.get(key)
        profile[key] = default_value if _is_missing_value(value) or value == "" else value

    profile["profile_name"] = "默认方案"
    if profile.get("risk_preference") not in VALID_RISK_PREFERENCES:
        profile["risk_preference"] = DEFAULT_DECISION_PROFILE["risk_preference"]
    return profile


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_columns(cursor: sqlite3.Cursor, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_database() -> None:
    """Initialize all tables safely without deleting existing user data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                current_age INTEGER,
                target_age INTEGER,
                target_asset REAL,
                monthly_expense REAL,
                risk_preference TEXT,
                current_asset REAL DEFAULT 0,
                monthly_investment REAL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_columns(
            cursor,
            "user_profile",
            {
                "current_asset": "REAL DEFAULT 0",
                "monthly_investment": "REAL DEFAULT 0",
                "user_key": "TEXT DEFAULT ''",
                "updated_at": "TEXT",
            },
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cashflow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                month TEXT,
                income REAL,
                expense REAL,
                saving REAL,
                saving_rate REAL,
                investment_amount REAL,
                special_expense_note TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_columns(cursor, "cashflow_records", {"updated_at": "TEXT"})
        _ensure_columns(cursor, "cashflow_records", {"user_key": "TEXT DEFAULT ''"})
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cashflow_records_user_month ON cashflow_records(user_key, month)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS asset_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                asset_type TEXT,
                asset_name TEXT,
                asset_code TEXT,
                amount REAL,
                cost REAL,
                current_value REAL,
                risk_level TEXT,
                buy_date TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_columns(cursor, "asset_records", {"buy_date": "TEXT", "updated_at": "TEXT"})
        _ensure_columns(cursor, "asset_records", {"user_key": "TEXT DEFAULT ''"})
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                code TEXT,
                name TEXT,
                asset_type TEXT,
                pool_type TEXT,
                note TEXT,
                risk_level TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_columns(cursor, "watchlist", {"updated_at": "TEXT"})
        _ensure_columns(cursor, "watchlist", {"user_key": "TEXT DEFAULT ''"})
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                report_month TEXT,
                report_text TEXT,
                created_at TEXT
            )
            """
        )
        _ensure_columns(cursor, "monthly_reports", {"user_key": "TEXT DEFAULT ''"})
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decision_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                profile_name TEXT,
                current_age INTEGER,
                target_age INTEGER,
                target_asset REAL,
                total_asset REAL,
                emergency_fund REAL,
                monthly_expense REAL,
                monthly_investment REAL,
                cash_amount REAL,
                bond_amount REAL,
                broad_index_amount REAL,
                global_index_amount REAL,
                sector_theme_amount REAL,
                active_fund_amount REAL,
                stock_amount REAL,
                quant_experiment_amount REAL,
                risk_preference TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_columns(
            cursor,
            "decision_profiles",
            {
                "user_key": "TEXT DEFAULT ''",
                "profile_name": "TEXT",
                "current_age": "INTEGER",
                "target_age": "INTEGER",
                "target_asset": "REAL",
                "total_asset": "REAL",
                "emergency_fund": "REAL",
                "monthly_expense": "REAL",
                "monthly_investment": "REAL",
                "cash_amount": "REAL",
                "bond_amount": "REAL",
                "broad_index_amount": "REAL",
                "global_index_amount": "REAL",
                "sector_theme_amount": "REAL",
                "active_fund_amount": "REAL",
                "stock_amount": "REAL",
                "quant_experiment_amount": "REAL",
                "risk_preference": "TEXT",
                "updated_at": "TEXT",
            },
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_decision_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                decision_month TEXT,
                profile_name TEXT,
                total_asset REAL,
                emergency_fund REAL,
                monthly_expense REAL,
                monthly_investment REAL,
                risk_preference TEXT,
                input_json TEXT,
                result_json TEXT,
                action_items TEXT,
                warnings TEXT,
                explanation TEXT,
                created_at TEXT
            )
            """
        )
        _ensure_columns(
            cursor,
            "monthly_decision_records",
            {
                "decision_month": "TEXT",
                "user_key": "TEXT DEFAULT ''",
                "profile_name": "TEXT",
                "total_asset": "REAL",
                "emergency_fund": "REAL",
                "monthly_expense": "REAL",
                "monthly_investment": "REAL",
                "risk_preference": "TEXT",
                "input_json": "TEXT",
                "result_json": "TEXT",
                "action_items": "TEXT",
                "warnings": "TEXT",
                "explanation": "TEXT",
                "created_at": "TEXT",
            },
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT DEFAULT '',
                trade_date TEXT,
                code TEXT,
                name TEXT,
                asset_type TEXT,
                action TEXT,
                amount REAL,
                note TEXT,
                created_at TEXT
            )
            """
        )
        _ensure_columns(
            cursor,
            "trade_records",
            {
                "trade_date": "TEXT",
                "user_key": "TEXT DEFAULT ''",
                "code": "TEXT",
                "name": "TEXT",
                "asset_type": "TEXT",
                "action": "TEXT",
                "amount": "REAL",
                "note": "TEXT",
                "created_at": "TEXT",
            },
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_data_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                asset_type TEXT,
                data_source TEXT,
                analysis_scope TEXT,
                price_type TEXT,
                start_date TEXT,
                end_date TEXT,
                latest_date TEXT,
                latest_close REAL,
                rows_count INTEGER,
                data_json TEXT,
                data_hash TEXT,
                fetch_status TEXT,
                error_message TEXT,
                updated_at TEXT,
                app_version TEXT,
                UNIQUE(code, asset_type, data_source, analysis_scope, price_type)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS failed_fetch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                asset_type TEXT,
                data_source TEXT,
                analysis_scope TEXT,
                price_type TEXT,
                error_message TEXT,
                failed_at TEXT,
                retry_count INTEGER DEFAULT 1,
                last_success_at TEXT,
                app_version TEXT
            )
            """
        )
        conn.commit()


def init_db() -> None:
    init_database()


@contextmanager
def get_connection():
    init_database()
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def fetch_df(query: str, params: tuple = ()) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def _user_key(user_key: str | None = None) -> str:
    return str(user_key or current_user_key() or "").strip().lower()


def clear_user_data(user_key: str | None = None) -> None:
    key = _user_key(user_key)
    if not key:
        return
    tables = [
        "decision_profiles",
        "monthly_decision_records",
        "cashflow_records",
        "watchlist",
        "asset_records",
        "trade_records",
        "monthly_reports",
    ]
    with get_connection() as conn:
        for table in tables:
            conn.execute(f"DELETE FROM {table} WHERE user_key=?", (key,))
        conn.execute("DELETE FROM user_profile WHERE user_key=?", (key,))
        conn.execute("DELETE FROM app_settings WHERE key LIKE ?", (f"{key}:%",))
        conn.commit()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_load(value: Any, fallback: Any) -> Any:
    if value is None or value == "":
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def upsert_user_profile(**values) -> None:
    ts = now_text()
    key = _user_key()
    values = dict(values)
    values["user_key"] = key
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM user_profile WHERE user_key=? ORDER BY id LIMIT 1", (key,)).fetchone()
        if existing:
            fields = ", ".join([f"{key}=?" for key in values.keys()])
            conn.execute(f"UPDATE user_profile SET {fields}, updated_at=? WHERE id=?", (*values.values(), ts, existing[0]))
        else:
            keys = ", ".join(values.keys())
            placeholders = ", ".join(["?"] * len(values))
            conn.execute(
                f"INSERT INTO user_profile ({keys}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
                (*values.values(), ts, ts),
            )
        conn.commit()


def get_user_profile() -> dict | None:
    df = fetch_df("SELECT * FROM user_profile WHERE user_key=? ORDER BY id LIMIT 1", (_user_key(),))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def load_cashflow_record_by_month(month: str, user_key: str | None = None) -> dict | None:
    df = fetch_df("SELECT * FROM cashflow_records WHERE user_key=? AND month = ? LIMIT 1", (_user_key(user_key), month,))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def load_recent_cashflow_records(limit: int = 12, user_key: str | None = None) -> pd.DataFrame:
    return fetch_df("SELECT * FROM cashflow_records WHERE user_key=? ORDER BY month DESC LIMIT ?", (_user_key(user_key), limit))


def save_cashflow_record(record: dict, user_key: str | None = None) -> None:
    record = record.copy()
    ts = now_text()
    key = _user_key(user_key)
    month = str(record.get("month", "")).strip()
    if not month:
        raise ValueError("月份不能为空")
    income = float(record.get("income", 0.0) or 0.0)
    expense = float(record.get("expense", 0.0) or 0.0)
    investment_amount = float(record.get("investment_amount", 0.0) or 0.0)
    saving = income - expense
    saving_rate = saving / income if income > 0 else 0.0
    with get_connection() as conn:
        existing = conn.execute("SELECT created_at FROM cashflow_records WHERE user_key=? AND month = ? LIMIT 1", (key, month)).fetchone()
        created_at = existing[0] if existing and existing[0] else ts
        if existing:
            conn.execute(
                """
                UPDATE cashflow_records
                SET income=?, expense=?, saving=?, saving_rate=?, investment_amount=?,
                    special_expense_note=?, updated_at=?
                WHERE user_key=? AND month=?
                """,
                (income, expense, saving, saving_rate, investment_amount, record.get("special_expense_note", ""), ts, key, month),
            )
        else:
            conn.execute(
                """
                INSERT INTO cashflow_records
                (user_key, month, income, expense, saving, saving_rate, investment_amount, special_expense_note, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    month,
                    income,
                    expense,
                    saving,
                    saving_rate,
                    investment_amount,
                    record.get("special_expense_note", ""),
                    created_at,
                    ts,
                ),
            )
        conn.commit()


def save_cashflow(record: dict, user_key: str | None = None) -> None:
    save_cashflow_record(record, user_key=user_key)


def add_asset(record: dict, user_key: str | None = None) -> None:
    ts = now_text()
    key = _user_key(user_key)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO asset_records
            (user_key, asset_type, asset_name, asset_code, amount, cost, current_value, risk_level, buy_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                record.get("asset_type", ""),
                record.get("asset_name", ""),
                record.get("asset_code", ""),
                record.get("amount", 0),
                record.get("cost", 0),
                record.get("current_value", 0),
                record.get("risk_level", "中风险"),
                record.get("buy_date", ""),
                ts,
                ts,
            ),
        )
        conn.commit()


def delete_by_id(table: str, row_id: int, user_key: str | None = None) -> None:
    if table not in {"asset_records", "watchlist", "monthly_reports"}:
        raise ValueError("不允许删除该表")
    with get_connection() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id=? AND user_key=?", (row_id, _user_key(user_key)))
        conn.commit()


def add_watch_item(record: dict, user_key: str | None = None) -> None:
    ts = now_text()
    key = _user_key(user_key)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO watchlist
            (user_key, code, name, asset_type, pool_type, note, risk_level, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                record.get("code", ""),
                record.get("name", ""),
                record.get("asset_type", ""),
                record.get("pool_type", "观察池"),
                record.get("note", ""),
                record.get("risk_level", "中风险"),
                ts,
                ts,
            ),
        )
        conn.commit()


def save_monthly_report(report_month: str, report_text: str, user_key: str | None = None) -> None:
    key = _user_key(user_key)
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM monthly_reports WHERE user_key=? AND report_month=? LIMIT 1", (key, report_month)).fetchone()
        if existing:
            conn.execute("UPDATE monthly_reports SET report_text=?, created_at=? WHERE id=?", (report_text, now_text(), existing[0]))
            conn.commit()
            return
        conn.execute(
            """
            INSERT INTO monthly_reports (user_key, report_month, report_text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, report_month, report_text, now_text()),
        )
        conn.commit()


def save_decision_profile(profile_data: dict, user_key: str | None = None) -> None:
    key = _user_key(user_key)
    existing_df = fetch_df(
        """
        SELECT *
        FROM decision_profiles
        WHERE user_key=? AND (profile_name = '默认方案' OR profile_name IS NULL OR profile_name = '')
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (key,),
    )
    merged_data = {}
    if not existing_df.empty:
        merged_data.update(existing_df.iloc[0].to_dict())
    merged_data.update(profile_data or {})
    data = _clean_decision_profile(merged_data)
    data["updated_at"] = now_text()
    data["user_key"] = key
    fields = ["user_key"] + [field for field in DEFAULT_DECISION_PROFILE if field != "is_default"]
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM decision_profiles WHERE user_key=? AND profile_name=? LIMIT 1", (key, "默认方案")).fetchone()
        if existing:
            updates = ", ".join([f"{field}=?" for field in fields if field not in {"user_key", "profile_name"}])
            values = [data.get(field) for field in fields if field not in {"user_key", "profile_name"}]
            conn.execute(f"UPDATE decision_profiles SET {updates} WHERE id=?", (*values, existing[0]))
        else:
            placeholders = ", ".join(["?"] * len(fields))
            conn.execute(
                f"INSERT INTO decision_profiles ({', '.join(fields)}) VALUES ({placeholders})",
                tuple(data.get(field) for field in fields),
            )
        conn.commit()


def load_latest_decision_profile(user_key: str | None = None) -> dict:
    key = _user_key(user_key)
    df = fetch_df(
        """
        SELECT *
        FROM decision_profiles
        WHERE user_key=? AND (profile_name = '默认方案' OR profile_name IS NULL OR profile_name = '')
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (key,),
    )
    if df.empty:
        return DEFAULT_DECISION_PROFILE.copy()
    row = df.iloc[0].to_dict()
    profile = _clean_decision_profile(row)
    profile["updated_at"] = row.get("updated_at", "")
    profile["is_default"] = False
    return profile


def save_monthly_decision_record(input_data: dict, result_data: dict, user_key: str | None = None) -> None:
    ts = now_text()
    key = _user_key(user_key)
    decision_month = datetime.now().strftime("%Y-%m")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO monthly_decision_records
            (user_key, decision_month, profile_name, total_asset, emergency_fund, monthly_expense, monthly_investment,
             risk_preference, input_json, result_json, action_items, warnings, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                decision_month,
                input_data.get("profile_name", "默认方案"),
                input_data.get("total_asset", 0),
                input_data.get("emergency_fund", 0),
                input_data.get("monthly_expense", 0),
                input_data.get("monthly_investment", 0),
                input_data.get("risk_preference", ""),
                _json_dump(input_data),
                _json_dump(result_data),
                _json_dump(result_data.get("action_items", [])),
                _json_dump(result_data.get("warnings", [])),
                _json_dump(result_data.get("explanation", [])),
                ts,
            ),
        )
        conn.commit()


def load_monthly_decision_records(limit: int = 12, user_key: str | None = None) -> pd.DataFrame:
    return fetch_df(
        """
        SELECT id, decision_month, profile_name, total_asset, emergency_fund, monthly_expense,
               monthly_investment, risk_preference, action_items, warnings, explanation, created_at
        FROM monthly_decision_records
        WHERE user_key=?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (_user_key(user_key), limit),
    )


def load_latest_monthly_decision_record() -> dict | None:
    records = load_monthly_decision_records(1)
    if records.empty:
        return None
    return get_decision_record_by_id(int(records.iloc[0]["id"]))


def get_decision_record_by_id(record_id: int, user_key: str | None = None) -> dict | None:
    df = fetch_df("SELECT * FROM monthly_decision_records WHERE id=? AND user_key=?", (record_id, _user_key(user_key)))
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    row["input_json"] = _json_load(row.get("input_json"), {})
    row["result_json"] = _json_load(row.get("result_json"), {})
    row["action_items"] = _json_load(row.get("action_items"), [])
    row["warnings"] = _json_load(row.get("warnings"), [])
    row["explanation"] = _json_load(row.get("explanation"), [])
    return row


def save_app_setting(key: str, value: str, user_key: str | None = None) -> None:
    owner = _user_key(user_key)
    scoped_key = f"{owner}:{key}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (scoped_key, value, now_text()),
        )
        conn.commit()


def load_app_setting(key: str, default=None, user_key: str | None = None):
    df = fetch_df("SELECT value FROM app_settings WHERE key=?", (f"{_user_key(user_key)}:{key}",))
    if df.empty:
        return default
    return df.iloc[0]["value"]


def _cache_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def load_market_data_cache(
    code: str,
    asset_type: str,
    data_source: str,
    analysis_scope: str,
    price_type: str,
    *,
    max_age_hours: int | None = 6,
) -> dict | None:
    df = fetch_df(
        """
        SELECT *
        FROM market_data_cache
        WHERE code=? AND asset_type=? AND data_source=? AND analysis_scope=? AND price_type=?
        LIMIT 1
        """,
        (code, asset_type, data_source, analysis_scope, price_type),
    )
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    updated_at = _cache_timestamp(row.get("updated_at"))
    row["is_stale"] = True
    if max_age_hours is None:
        row["is_stale"] = False
    elif updated_at is not None:
        row["is_stale"] = datetime.now() - updated_at > timedelta(hours=max_age_hours)
    try:
        payload = json.loads(row.get("data_json") or "[]")
        data = pd.DataFrame(payload)
        if not data.empty:
            data["date"] = pd.to_datetime(data["date"], errors="coerce")
            data["close"] = pd.to_numeric(data["close"], errors="coerce")
            data = data.dropna().sort_values("date").reset_index(drop=True)
        row["data"] = data
    except Exception:
        row["data"] = pd.DataFrame(columns=["date", "close"])
    return row


def save_market_data_cache(
    *,
    code: str,
    asset_type: str,
    data_source: str,
    analysis_scope: str,
    price_type: str,
    data: pd.DataFrame,
    data_hash: str,
    fetch_status: str = "success",
    error_message: str = "",
) -> None:
    frame = data.copy() if data is not None else pd.DataFrame(columns=["date", "close"])
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["date", "close"])
    latest_date = "" if frame.empty else str(frame["date"].iloc[-1])
    latest_close = None if frame.empty else float(frame["close"].iloc[-1])
    start_date = "" if frame.empty else str(frame["date"].iloc[0])
    rows_count = int(len(frame))
    data_json = frame[["date", "close"]].to_json(orient="records", force_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO market_data_cache
            (code, asset_type, data_source, analysis_scope, price_type, start_date, end_date, latest_date,
             latest_close, rows_count, data_json, data_hash, fetch_status, error_message, updated_at, app_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code, asset_type, data_source, analysis_scope, price_type)
            DO UPDATE SET
                start_date=excluded.start_date,
                end_date=excluded.end_date,
                latest_date=excluded.latest_date,
                latest_close=excluded.latest_close,
                rows_count=excluded.rows_count,
                data_json=excluded.data_json,
                data_hash=excluded.data_hash,
                fetch_status=excluded.fetch_status,
                error_message=excluded.error_message,
                updated_at=excluded.updated_at,
                app_version=excluded.app_version
            """,
            (
                code,
                asset_type,
                data_source,
                analysis_scope,
                price_type,
                start_date,
                latest_date,
                latest_date,
                latest_close,
                rows_count,
                data_json,
                data_hash,
                fetch_status,
                error_message,
                now_text(),
                APP_VERSION,
            ),
        )
        conn.commit()


def log_failed_fetch(
    *,
    code: str,
    asset_type: str,
    data_source: str,
    analysis_scope: str,
    price_type: str,
    error_message: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO failed_fetch_log
            (code, asset_type, data_source, analysis_scope, price_type, error_message, failed_at, retry_count, app_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (code, asset_type, data_source, analysis_scope, price_type, error_message, now_text(), APP_VERSION),
        )
        conn.commit()


def save_trade_record(record: dict, user_key: str | None = None) -> None:
    ts = now_text()
    key = _user_key(user_key)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO trade_records
            (user_key, trade_date, code, name, asset_type, action, amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                record.get("trade_date", datetime.now().strftime("%Y-%m-%d")),
                record.get("code", ""),
                record.get("name", ""),
                record.get("asset_type", ""),
                record.get("action", "定投"),
                float(record.get("amount", 0.0) or 0.0),
                record.get("note", ""),
                ts,
            ),
        )
        conn.commit()


def load_recent_trade_records(limit: int = 20, user_key: str | None = None) -> pd.DataFrame:
    return fetch_df(
        """
        SELECT id, trade_date, code, name, asset_type, action, amount, note, created_at
        FROM trade_records
        WHERE user_key=?
        ORDER BY trade_date DESC, id DESC
        LIMIT ?
        """,
        (_user_key(user_key), limit),
    )


def update_holding_from_trade(record: dict, user_key: str | None = None) -> None:
    action = record.get("action", "定投")
    if action not in {"买入", "定投"}:
        return
    amount = float(record.get("amount", 0.0) or 0.0)
    if amount <= 0:
        return
    code = record.get("code", "")
    name = record.get("name", "")
    asset_type = record.get("asset_type", "")
    ts = now_text()
    key = _user_key(user_key)
    with get_connection() as conn:
        existing = None
        if code:
            existing = conn.execute("SELECT id, amount, cost, current_value FROM asset_records WHERE user_key=? AND asset_code=? LIMIT 1", (key, code)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE asset_records
                SET amount=?, cost=?, current_value=?, updated_at=?
                WHERE id=?
                """,
                (
                    float(existing[1] or 0) + amount,
                    float(existing[2] or 0) + amount,
                    float(existing[3] or 0) + amount,
                    ts,
                    int(existing[0]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO asset_records
                (user_key, asset_type, asset_name, asset_code, amount, cost, current_value, risk_level, buy_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    asset_type,
                    name,
                    code,
                    amount,
                    amount,
                    amount,
                    "中风险",
                    record.get("trade_date", datetime.now().strftime("%Y-%m-%d")),
                    ts,
                    ts,
                ),
            )
        conn.commit()
