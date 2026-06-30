import hashlib
import json
import os
import platform
import re
from typing import Any

import pandas as pd

try:
    from .config import APP_VERSION
except Exception:
    APP_VERSION = "unknown-version"
from .database import load_market_data_cache, log_failed_fetch, save_market_data_cache


ETF_PREFIXES = ("510", "511", "512", "513", "515", "516", "517", "518", "519", "560", "561", "562", "563", "588", "159")
LOF_PREFIXES = ("501", "502", "160", "161", "162", "163", "164", "165", "166", "167")
OPEN_FUND_PREFIXES = ("000", "001", "002", "003", "004", "005", "006", "007", "008", "009")
STOCK_PREFIXES = ("600", "601", "603", "605", "300", "301", "688")

ASSET_TYPE_LABELS = {
    "ETF": "ETF",
    "LOF": "LOF / 场内基金",
    "OPEN_FUND": "开放式基金",
    "A_STOCK": "A 股股票",
    "US_ETF": "美股 / 海外 ETF",
    "UNKNOWN": "未知",
}

SOURCE_OPTIONS_MAP = {
    "ETF 场内行情": "ETF",
    "LOF / 场内基金行情": "LOF",
    "开放式基金净值": "OPEN_FUND",
    "A 股股票行情": "A_STOCK",
    "美股 / 海外 ETF": "US_ETF",
    "中国ETF": "ETF",
    "中国LOF": "LOF",
    "中国开放式基金": "OPEN_FUND",
    "中国股票": "A_STOCK",
    "美股ETF": "US_ETF",
}


def infer_asset_type_by_code(code: str) -> str:
    """根据代码本身确定优先资产类型，不依赖接口成功顺序。"""
    code = str(code or "").strip().upper()
    if re.fullmatch(r"[A-Z.]{1,10}", code):
        return "US_ETF"
    if not re.fullmatch(r"\d{6}", code):
        return "UNKNOWN"
    if code.startswith(ETF_PREFIXES):
        return "ETF"
    if code.startswith(LOF_PREFIXES):
        return "LOF"
    if code.startswith(OPEN_FUND_PREFIXES):
        return "OPEN_FUND"
    if code.startswith(STOCK_PREFIXES):
        return "A_STOCK"
    return "UNKNOWN"


def _asset_label(asset_key: str) -> str:
    return ASSET_TYPE_LABELS.get(asset_key, asset_key or "未知")


def _runtime_versions() -> dict[str, str]:
    versions = {
        "pandas": pd.__version__,
        "numpy": "",
        "streamlit": "",
        "akshare": "",
    }
    try:
        import numpy as np

        versions["numpy"] = np.__version__
    except Exception:
        pass
    try:
        import streamlit as st

        versions["streamlit"] = st.__version__
    except Exception:
        pass
    try:
        import akshare as ak

        versions["akshare"] = getattr(ak, "__version__", "")
    except Exception:
        pass
    return versions


def current_environment_label() -> str:
    if os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("STREAMLIT_CLOUD"):
        return "cloud"
    cwd = os.getcwd().lower().replace("\\", "/")
    home = str(os.getenv("HOME", "")).lower().replace("\\", "/")
    if "site-packages" in cwd or "/mount/src" in cwd or "appuser" in home:
        return "cloud"
    return "local"

def _pick_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if df is None or df.empty:
        return None
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for name in candidates:
        key = str(name).strip().lower()
        if key in normalized:
            return normalized[key]
    for col in df.columns:
        text = str(col)
        if any(name in text for name in candidates):
            return col
    return None


def _normalize_candidate_list(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["代码", "名称", "最新价", "涨跌幅", "成交额", "规模", "数据来源"])

    code_col = _pick_column(df, ["代码", "基金代码", "symbol", "code"])
    name_col = _pick_column(df, ["名称", "基金简称", "基金名称", "name"])
    price_col = _pick_column(df, ["最新价", "最新净值", "单位净值", "price"])
    change_col = _pick_column(df, ["涨跌幅", "日增长率", "change"])
    amount_col = _pick_column(df, ["成交额", "成交额(元)", "成交金额", "amount"])
    size_col = _pick_column(df, ["规模", "基金规模", "资产净值"])

    if code_col is None or name_col is None:
        return pd.DataFrame(columns=["代码", "名称", "最新价", "涨跌幅", "成交额", "规模", "数据来源"])

    result = pd.DataFrame(
        {
            "代码": df[code_col].astype(str).str.strip(),
            "名称": df[name_col].astype(str).str.strip(),
            "最新价": df[price_col] if price_col else None,
            "涨跌幅": df[change_col] if change_col else None,
            "成交额": df[amount_col] if amount_col else None,
            "规模": df[size_col] if size_col else None,
            "数据来源": source,
        }
    )
    result = result[(result["代码"] != "") & (result["名称"] != "")]
    return result.drop_duplicates(subset=["代码"]).reset_index(drop=True)


def fetch_china_etf_list() -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        if not hasattr(ak, "fund_etf_spot_em"):
            return pd.DataFrame(), "当前 AKShare 版本没有 fund_etf_spot_em 接口。"
        return _normalize_candidate_list(ak.fund_etf_spot_em(), "AKShare ETF列表"), None
    except Exception as exc:
        return pd.DataFrame(), f"ETF 列表获取失败：{exc}"


def fetch_china_lof_list() -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        if not hasattr(ak, "fund_lof_spot_em"):
            return pd.DataFrame(), "当前 AKShare 版本没有 fund_lof_spot_em 接口。"
        return _normalize_candidate_list(ak.fund_lof_spot_em(), "AKShare LOF列表"), None
    except Exception as exc:
        return pd.DataFrame(), f"LOF 列表获取失败：{exc}"


def fetch_open_fund_list() -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        funcs = ["fund_open_fund_daily_em", "fund_open_fund_rank_em"]
        for func_name in funcs:
            if hasattr(ak, func_name):
                func = getattr(ak, func_name)
                try:
                    df = func()
                except TypeError:
                    df = func(symbol="全部")
                normalized = _normalize_candidate_list(df, f"AKShare {func_name}")
                if not normalized.empty:
                    return normalized, None
        return pd.DataFrame(), "当前 AKShare 版本未找到可用的开放式基金列表接口。"
    except Exception as exc:
        return pd.DataFrame(), f"开放式基金列表获取失败：{exc}"


def fetch_available_fund_candidates() -> tuple[pd.DataFrame, list[str]]:
    frames = []
    errors = []
    for func in [fetch_china_etf_list, fetch_china_lof_list, fetch_open_fund_list]:
        df, error = func()
        if error:
            errors.append(error)
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["代码", "名称", "最新价", "涨跌幅", "成交额", "规模", "数据来源"]), errors
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["代码"]).reset_index(drop=True), errors


def _normalize_frame(df: pd.DataFrame, date_col: str | None = None, close_col: str | None = None) -> pd.DataFrame:
    """把不同数据源统一成 date | close 两列。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "close"])

    columns = list(df.columns)
    date_candidates = [date_col, "date", "Date", "日期", "净值日期", "交易日期"]
    close_candidates = [close_col, "close", "Close", "收盘", "单位净值", "累计净值", "最新价"]

    picked_date = next((col for col in date_candidates if col in columns), None)
    picked_close = next((col for col in close_candidates if col in columns), None)
    if picked_date is None or picked_close is None:
        return pd.DataFrame(columns=["date", "close"])

    result = df[[picked_date, picked_close]].copy()
    result.columns = ["date", "close"]
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["close"] = pd.to_numeric(result["close"], errors="coerce")
    return result.dropna().sort_values("date").reset_index(drop=True)


def _data_hash(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return ""
    normalized = df[["date", "close"]].copy()
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.strftime("%Y-%m-%d")
    normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce").round(8)
    payload = normalized.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _data_profile(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "first_date": "",
            "latest_date": "",
            "latest_close": None,
            "rows": 0,
            "close_head_3": [],
            "close_tail_3": [],
            "data_hash": "",
        }
    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    return {
        "first_date": frame["date"].iloc[0].date().isoformat(),
        "latest_date": frame["date"].iloc[-1].date().isoformat(),
        "latest_close": float(frame["close"].iloc[-1]),
        "rows": int(len(frame)),
        "close_head_3": [round(float(x), 6) for x in frame["close"].head(3).tolist()],
        "close_tail_3": [round(float(x), 6) for x in frame["close"].tail(3).tolist()],
        "data_hash": _data_hash(frame),
    }


def _result(
    success: bool,
    asset_type: str,
    data: pd.DataFrame | None,
    message: str,
    asset_name: str = "",
    *,
    code: str = "",
    inferred_type: str = "UNKNOWN",
    selected_scope: str = "自动识别",
    actual_scope: str = "",
    data_source: str = "",
    quote_type: str = "",
    adjustment: str = "",
    used_fallback: bool = False,
    strict: bool = True,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    frame = data if data is not None else pd.DataFrame(columns=["date", "close"])
    profile = _data_profile(frame)
    return {
        "success": success,
        "asset_type": asset_type,
        "inferred_asset_type": _asset_label(inferred_type),
        "asset_name": asset_name or "",
        "code": code,
        "data": frame,
        "message": message,
        "selected_scope": selected_scope,
        "actual_scope": actual_scope or asset_type,
        "data_source": data_source,
        "quote_type": quote_type,
        "adjustment": adjustment,
        "used_fallback": used_fallback,
        "strict": strict,
        "errors": errors or [],
        "app_version": APP_VERSION,
        "environment": current_environment_label(),
        "runtime_versions": _runtime_versions(),
        **profile,
    }


def fetch_china_etf_data(code: str) -> tuple[pd.DataFrame, str | None]:
    result = fetch_asset_data_auto(code, preferred_type="中国ETF")
    return result["data"], None if result["success"] else result["message"]


def fetch_china_lof_data(code: str) -> tuple[pd.DataFrame, str | None]:
    result = fetch_asset_data_auto(code, preferred_type="中国LOF")
    return result["data"], None if result["success"] else result["message"]


def fetch_china_fund_data(code: str) -> tuple[pd.DataFrame, str | None]:
    result = fetch_asset_data_auto(code, preferred_type="中国开放式基金")
    return result["data"], None if result["success"] else result["message"]


def fetch_us_etf_data(symbol: str) -> tuple[pd.DataFrame, str | None]:
    result = fetch_asset_data_auto(symbol, preferred_type="美股ETF")
    return result["data"], None if result["success"] else result["message"]


def fetch_stock_data(code: str) -> tuple[pd.DataFrame, str | None]:
    result = fetch_asset_data_auto(code, preferred_type="中国股票")
    return result["data"], None if result["success"] else result["message"]


def _try_china_etf(code: str) -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="")
        data = _normalize_frame(df, "日期", "收盘")
        if data.empty:
            return data, "ETF接口未返回可用行情。"
        return data, None
    except Exception as exc:
        return pd.DataFrame(columns=["date", "close"]), f"ETF接口失败：{exc}"


def _try_china_lof(code: str) -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        if not hasattr(ak, "fund_lof_hist_em"):
            return pd.DataFrame(columns=["date", "close"]), "当前 AKShare 版本没有 fund_lof_hist_em 接口。"
        df = ak.fund_lof_hist_em(symbol=code, period="daily", adjust="")
        data = _normalize_frame(df, "日期", "收盘")
        if data.empty:
            return data, "LOF接口未返回可用行情。"
        return data, None
    except Exception as exc:
        return pd.DataFrame(columns=["date", "close"]), f"LOF接口失败：{exc}"


def _try_open_fund(code: str) -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        data = _normalize_frame(df, "净值日期", "单位净值")
        if data.empty:
            return data, "开放式基金净值接口未返回可用数据。"
        return data, None
    except Exception as exc:
        return pd.DataFrame(columns=["date", "close"]), f"开放式基金接口失败：{exc}"


def _try_china_stock(code: str) -> tuple[pd.DataFrame, str | None]:
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        data = _normalize_frame(df, "日期", "收盘")
        if data.empty:
            return data, "A股接口未返回可用行情。"
        return data, None
    except Exception as exc:
        return pd.DataFrame(columns=["date", "close"]), f"A股接口失败：{exc}"


def _try_us_etf(code: str) -> tuple[pd.DataFrame, str | None]:
    try:
        import yfinance as yf

        df = yf.download(code, period="10y", progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        data = _normalize_frame(df.reset_index(), "Date", "Close")
        if data.empty:
            return data, "yfinance未返回可用行情。"
        return data, None
    except Exception as exc:
        return pd.DataFrame(columns=["date", "close"]), f"美股ETF接口失败：{exc}"


FETCHERS: dict[str, tuple[Any, str, str, str]] = {
    "ETF": (_try_china_etf, "AKShare ETF", "场内交易价格", "不复权行情"),
    "LOF": (_try_china_lof, "AKShare LOF", "场内交易价格", "不复权行情"),
    "OPEN_FUND": (_try_open_fund, "AKShare 开放式基金净值", "基金单位净值", "基金单位净值"),
    "A_STOCK": (_try_china_stock, "AKShare A股", "复权行情", "前复权行情"),
    "US_ETF": (_try_us_etf, "yfinance", "不复权行情", "不复权行情"),
}


def _candidate_attempts(inferred: str) -> list[str]:
    ordered = [inferred] if inferred in FETCHERS else []
    for key in ["ETF", "LOF", "OPEN_FUND", "A_STOCK", "US_ETF"]:
        if key not in ordered:
            ordered.append(key)
    return ordered


def _selected_asset_key(code: str, analysis_scope: str) -> str:
    if analysis_scope == "自动识别":
        return infer_asset_type_by_code(code)
    return SOURCE_OPTIONS_MAP.get(analysis_scope, SOURCE_OPTIONS_MAP.get(str(analysis_scope), "UNKNOWN"))


def _cache_identity(code: str, analysis_scope: str) -> dict[str, str]:
    asset_key = _selected_asset_key(code, analysis_scope)
    source_name = ""
    quote_type = ""
    if asset_key in FETCHERS:
        _func, source_name, quote_type, _adjustment = FETCHERS[asset_key]
    return {
        "code": str(code or "").strip().upper(),
        "asset_key": asset_key,
        "asset_type": _asset_label(asset_key),
        "data_source": source_name,
        "analysis_scope": analysis_scope if analysis_scope != "自动识别" else _asset_label(asset_key),
        "price_type": quote_type,
    }


def _result_from_cache(cache: dict, identity: dict[str, str], selected_scope: str, *, stale: bool) -> dict[str, Any]:
    frame = cache.get("data", pd.DataFrame(columns=["date", "close"]))
    message = "已使用本地缓存数据。"
    if stale:
        message = "实时数据接口暂不可用，已使用同一口径的旧缓存数据。"
    result = _result(
        True,
        identity["asset_type"],
        frame,
        message,
        asset_name=identity["code"],
        code=identity["code"],
        inferred_type=infer_asset_type_by_code(identity["code"]),
        selected_scope=selected_scope,
        actual_scope=identity["analysis_scope"],
        data_source=identity["data_source"],
        quote_type=identity["price_type"],
        adjustment=FETCHERS.get(identity["asset_key"], (None, "", "", ""))[3],
        used_fallback=False,
        strict=True,
    )
    result["from_cache"] = True
    result["cache_stale"] = stale
    result["cache_updated_at"] = cache.get("updated_at", "")
    return result


def _failure_message(code: str, selected_key: str, strict: bool, errors: list[str]) -> str:
    label = _asset_label(selected_key)
    if selected_key == "LOF" and strict:
        return (
            f"当前代码 {code} 按 LOF / 场内基金识别，但 LOF 数据接口获取失败。"
            "你可以手动切换为开放式基金净值口径重新分析。"
            + (" 详细错误：" + "；".join(errors) if errors else "")
        )
    return f"当前代码 {code} 按 {label} 口径获取数据失败。" + (" 详细错误：" + "；".join(errors) if errors else "")


def fetch_asset_data_auto(code: str, preferred_type: str = "自动识别", strict: bool = True) -> dict[str, Any]:
    """按确定性代码规则识别资产类型，并按 strict 控制是否允许备用口径。"""
    code = str(code or "").strip().upper()
    if not code:
        return _result(False, "未知", None, "请输入代码。", strict=strict)

    inferred = infer_asset_type_by_code(code)
    if preferred_type == "自动识别":
        if inferred == "UNKNOWN":
            return _result(
                False,
                "未知",
                None,
                "代码格式暂不支持。请尝试 6 位中国市场代码或 SPY、QQQ、VOO 这类美股代码。",
                code=code,
                inferred_type=inferred,
                selected_scope=preferred_type,
                strict=strict,
            )
        attempts = [inferred] if strict else _candidate_attempts(inferred)
    else:
        selected_key = SOURCE_OPTIONS_MAP.get(preferred_type)
        if selected_key is None:
            return fetch_asset_data_auto(code, preferred_type="自动识别", strict=strict)
        attempts = [selected_key]

    errors = []
    for idx, selected_key in enumerate(attempts):
        func, source_name, quote_type, adjustment = FETCHERS[selected_key]
        data, error = func(code)
        if not data.empty:
            actual_label = _asset_label(selected_key)
            if preferred_type == "自动识别":
                message = f"已按代码规则自动识别为{actual_label}，使用{quote_type}口径。"
            else:
                message = f"已按用户选择的{preferred_type}获取数据，使用{quote_type}口径。"
            return _result(
                True,
                actual_label,
                data,
                message,
                asset_name=code,
                code=code,
                inferred_type=inferred,
                selected_scope=preferred_type,
                actual_scope=preferred_type if preferred_type != "自动识别" else actual_label,
                data_source=source_name,
                quote_type=quote_type,
                adjustment=adjustment,
                used_fallback=idx > 0,
                strict=strict,
                errors=errors,
            )
        errors.append(f"{_asset_label(selected_key)}: {error}")
        if strict:
            break

    return _result(
        False,
        _asset_label(attempts[0] if attempts else inferred),
        None,
        _failure_message(code, attempts[0] if attempts else inferred, strict, errors),
        code=code,
        inferred_type=inferred,
        selected_scope=preferred_type,
        actual_scope=_asset_label(attempts[0] if attempts else inferred),
        data_source=FETCHERS.get(attempts[0], (None, "", "", ""))[1] if attempts else "",
        quote_type=FETCHERS.get(attempts[0], (None, "", "", ""))[2] if attempts else "",
        adjustment=FETCHERS.get(attempts[0], (None, "", "", ""))[3] if attempts else "",
        strict=strict,
        errors=errors,
    )


def fetch_asset_data_with_cache(
    code: str,
    analysis_scope: str = "自动识别",
    *,
    force_refresh: bool = False,
    strict: bool = True,
    cache_ttl_hours: int = 6,
) -> dict[str, Any]:
    """Fetch market data with a strict same-scope cache."""
    normalized_code = str(code or "").strip().upper()
    if not normalized_code:
        return _result(False, "未知", None, "请输入代码。", strict=strict)

    identity = _cache_identity(normalized_code, analysis_scope)
    if identity["asset_key"] not in FETCHERS:
        return fetch_asset_data_auto(normalized_code, preferred_type=analysis_scope, strict=strict)

    fresh_cache = None
    if not force_refresh:
        fresh_cache = load_market_data_cache(
            identity["code"],
            identity["asset_type"],
            identity["data_source"],
            identity["analysis_scope"],
            identity["price_type"],
            max_age_hours=cache_ttl_hours,
        )
        if fresh_cache is not None and not fresh_cache.get("is_stale") and not fresh_cache.get("data", pd.DataFrame()).empty:
            return _result_from_cache(fresh_cache, identity, analysis_scope, stale=False)

    live_result = fetch_asset_data_auto(normalized_code, preferred_type=analysis_scope, strict=strict)
    if live_result.get("success"):
        live_identity = {
            "code": live_result.get("code", identity["code"]),
            "asset_key": identity["asset_key"],
            "asset_type": live_result.get("asset_type", identity["asset_type"]),
            "data_source": live_result.get("data_source", identity["data_source"]),
            "analysis_scope": live_result.get("actual_scope", identity["analysis_scope"]),
            "price_type": live_result.get("quote_type", identity["price_type"]),
        }
        save_market_data_cache(
            code=live_identity["code"],
            asset_type=live_identity["asset_type"],
            data_source=live_identity["data_source"],
            analysis_scope=live_identity["analysis_scope"],
            price_type=live_identity["price_type"],
            data=live_result.get("data", pd.DataFrame()),
            data_hash=live_result.get("data_hash", ""),
            fetch_status="success",
            error_message="",
        )
        live_result["from_cache"] = False
        live_result["cache_stale"] = False
        live_result["cache_updated_at"] = ""
        return live_result

    log_failed_fetch(
        code=identity["code"],
        asset_type=identity["asset_type"],
        data_source=identity["data_source"],
        analysis_scope=identity["analysis_scope"],
        price_type=identity["price_type"],
        error_message=live_result.get("message", ""),
    )
    stale_cache = fresh_cache or load_market_data_cache(
        identity["code"],
        identity["asset_type"],
        identity["data_source"],
        identity["analysis_scope"],
        identity["price_type"],
        max_age_hours=None,
    )
    if stale_cache is not None and not stale_cache.get("data", pd.DataFrame()).empty:
        cached = _result_from_cache(stale_cache, identity, analysis_scope, stale=True)
        cached["errors"] = live_result.get("errors", [])
        return cached
    live_result["from_cache"] = False
    live_result["cache_stale"] = False
    live_result["cache_updated_at"] = ""
    return live_result


def build_consistency_report(result: dict[str, Any], metrics_hash: str = "") -> dict[str, Any]:
    versions = result.get("runtime_versions", {})
    return {
        "code": result.get("code", ""),
        "infer_asset_type_by_code": result.get("inferred_asset_type", ""),
        "实际使用数据源": result.get("data_source", ""),
        "latest_date": result.get("latest_date", ""),
        "latest_close": result.get("latest_close", None),
        "first_date": result.get("first_date", ""),
        "rows": result.get("rows", 0),
        "close_head_3": json.dumps(result.get("close_head_3", []), ensure_ascii=False),
        "close_tail_3": json.dumps(result.get("close_tail_3", []), ensure_ascii=False),
        "data_hash": result.get("data_hash", ""),
        "metrics_hash": metrics_hash,
        "akshare 版本": versions.get("akshare", ""),
        "pandas 版本": versions.get("pandas", ""),
        "numpy 版本": versions.get("numpy", ""),
        "streamlit 版本": versions.get("streamlit", ""),
        "当前环境": result.get("environment", ""),
        "当前 APP_VERSION": result.get("app_version", APP_VERSION),
        "Python": platform.python_version(),
    }
