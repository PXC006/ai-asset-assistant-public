import re
from typing import Any

import pandas as pd


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


def _result(success: bool, asset_type: str, data: pd.DataFrame | None, message: str, asset_name: str = "") -> dict[str, Any]:
    return {
        "success": success,
        "asset_type": asset_type,
        "asset_name": asset_name or "",
        "data": data if data is not None else pd.DataFrame(columns=["date", "close"]),
        "message": message,
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


def fetch_asset_data_auto(code: str, preferred_type: str = "自动识别") -> dict[str, Any]:
    """自动识别 ETF、LOF、开放式基金、A股或美股ETF，并返回统一行情数据。"""
    code = str(code or "").strip().upper()
    if not code:
        return _result(False, "未知", None, "请输入代码。")

    attempts: list[tuple[str, Any, str]] = []
    if preferred_type == "自动识别":
        if re.fullmatch(r"[A-Z.]{1,10}", code):
            attempts = [("美股ETF", _try_us_etf, "已自动识别为美股ETF，使用 yfinance 行情数据。")]
        elif re.fullmatch(r"\d{6}", code):
            attempts = [
                ("ETF", _try_china_etf, "已自动识别为ETF，使用场内ETF行情数据。"),
                ("LOF", _try_china_lof, "该代码不是普通ETF，已自动识别为LOF/场内基金。"),
                ("开放式基金", _try_open_fund, "该代码不是ETF，已自动识别为开放式基金，使用净值数据分析。"),
                ("股票", _try_china_stock, "已自动识别为A股股票，使用股票行情数据。"),
            ]
        else:
            return _result(False, "未知", None, "代码格式暂不支持。请尝试 6 位中国市场代码或 SPY、QQQ、VOO 这类美股代码。")
    else:
        mapping = {
            "中国ETF": ("ETF", _try_china_etf, "按中国ETF接口获取数据。"),
            "中国LOF": ("LOF", _try_china_lof, "按中国LOF接口获取数据。"),
            "中国开放式基金": ("开放式基金", _try_open_fund, "按开放式基金净值接口获取数据。"),
            "中国股票": ("股票", _try_china_stock, "按A股股票接口获取数据。"),
            "美股ETF": ("美股ETF", _try_us_etf, "按美股ETF接口获取数据。"),
        }
        if preferred_type not in mapping:
            return fetch_asset_data_auto(code, preferred_type="自动识别")
        attempts = [mapping[preferred_type]]

    errors = []
    for asset_type, func, success_message in attempts:
        data, error = func(code)
        if not data.empty:
            return _result(True, asset_type, data, success_message, asset_name=code)
        errors.append(f"{asset_type}: {error}")

    return _result(
        False,
        "未知",
        None,
        "未获取到该代码数据。可能原因：代码不存在、代码类型暂不支持、数据源异常或网络问题。请尝试使用候选标的池里的常见标的。"
        + (" 详细尝试：" + "；".join(errors) if errors else ""),
    )
