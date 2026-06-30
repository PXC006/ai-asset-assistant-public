from __future__ import annotations

from datetime import datetime

import pandas as pd

from .data_fetcher import fetch_asset_data_auto, fetch_available_fund_candidates
from .risk_engine import (
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_return_by_period,
    calculate_sharpe_ratio,
)
from .static_candidates import STATIC_CANDIDATES


ASSET_CLASS_DIRECTIONS = {
    "现金/货币基金": ["货币基金", "现金管理"],
    "债券/短债": ["国债", "短债", "中短债", "可转债"],
    "宽基指数": ["沪深300", "中证500", "中证A500", "中证1000", "创业板", "科创板", "上证50"],
    "全球/海外指数": ["标普500", "纳斯达克100", "恒生指数", "恒生科技", "全球指数"],
    "红利低波": ["红利", "红利低波", "高股息"],
    "行业主题": ["半导体", "新能源", "医药", "消费", "AI", "军工", "证券"],
    "主动基金": ["主动权益", "均衡配置", "固收+"],
}


DIRECTION_KEYWORDS = {
    "货币基金": ["货币", "现金", "添利", "收益"],
    "现金管理": ["现金", "货币", "短融"],
    "沪深300": ["沪深300", "300ETF", "HS300", "300"],
    "中证500": ["中证500", "500ETF", "500"],
    "中证A500": ["中证A500", "A500"],
    "中证1000": ["中证1000", "1000ETF", "1000"],
    "创业板": ["创业板", "创业板ETF", "创业"],
    "科创板": ["科创", "科创板", "科创50"],
    "上证50": ["上证50", "50ETF"],
    "国债": ["国债", "政金债", "利率债"],
    "短债": ["短债", "中短债"],
    "中短债": ["中短债", "短债"],
    "可转债": ["可转债", "转债"],
    "红利": ["红利", "高股息", "股息"],
    "红利低波": ["红利低波", "低波"],
    "高股息": ["高股息", "股息", "红利"],
    "标普500": ["标普500", "标普", "S&P500", "SP500"],
    "纳斯达克100": ["纳指", "纳斯达克", "纳斯达克100", "NASDAQ", "QQQ"],
    "恒生指数": ["恒生指数", "恒生ETF", "恒指"],
    "恒生科技": ["恒生科技", "恒科"],
    "全球指数": ["全球", "海外", "MSCI"],
    "半导体": ["半导体", "芯片", "集成电路"],
    "新能源": ["新能源", "光伏", "电池"],
    "医药": ["医药", "医疗", "生物医药"],
    "消费": ["消费", "食品饮料", "白酒"],
    "AI": ["AI", "人工智能", "智能"],
    "军工": ["军工", "国防"],
    "证券": ["证券", "券商"],
    "主动权益": ["成长", "价值", "精选", "优选"],
    "均衡配置": ["均衡", "平衡", "配置"],
    "固收+": ["固收", "稳健", "增强"],
}


FALLBACK_CANDIDATES = [
    ("510300", "沪深300ETF", "宽基指数", "沪深300", "中风险", 150.0),
    ("159919", "沪深300ETF", "宽基指数", "沪深300", "中风险", 120.0),
    ("510310", "沪深300ETF易方达", "宽基指数", "沪深300", "中风险", 80.0),
    ("510500", "中证500ETF", "宽基指数", "中证500", "中高风险", 90.0),
    ("159922", "中证500ETF", "宽基指数", "中证500", "中高风险", 65.0),
    ("512500", "中证500ETF", "宽基指数", "中证500", "中高风险", 45.0),
    ("563360", "中证A500ETF", "宽基指数", "中证A500", "中风险", 40.0),
    ("159351", "中证A500ETF", "宽基指数", "中证A500", "中风险", 38.0),
    ("512100", "中证1000ETF", "宽基指数", "中证1000", "高风险", 55.0),
    ("159845", "中证1000ETF", "宽基指数", "中证1000", "高风险", 38.0),
    ("159915", "创业板ETF", "宽基指数", "创业板", "高风险", 70.0),
    ("588000", "科创50ETF", "宽基指数", "科创板", "高风险", 50.0),
    ("510050", "上证50ETF", "宽基指数", "上证50", "中风险", 110.0),
    ("511010", "国债ETF", "债券/短债", "国债", "低风险", 30.0),
    ("511260", "十年国债ETF", "债券/短债", "国债", "低风险", 20.0),
    ("511090", "30年国债ETF", "债券/短债", "国债", "中风险", 18.0),
    ("511360", "短债ETF", "债券/短债", "短债", "低风险", 18.0),
    ("511380", "可转债ETF", "债券/短债", "可转债", "中高风险", 35.0),
    ("510880", "红利ETF", "红利低波", "红利", "中风险", 80.0),
    ("515180", "红利低波ETF", "红利低波", "红利低波", "中风险", 45.0),
    ("159905", "深红利ETF", "红利低波", "红利", "中风险", 35.0),
    ("513500", "标普500ETF", "全球/海外指数", "标普500", "中高风险", 85.0),
    ("513100", "纳指ETF", "全球/海外指数", "纳斯达克100", "高风险", 90.0),
    ("159941", "纳指ETF", "全球/海外指数", "纳斯达克100", "高风险", 60.0),
    ("159920", "恒生ETF", "全球/海外指数", "恒生指数", "高风险", 55.0),
    ("513180", "恒生科技指数ETF", "全球/海外指数", "恒生科技", "高风险", 70.0),
    ("512760", "芯片ETF", "行业主题", "半导体", "高风险", 75.0),
    ("512480", "半导体ETF", "行业主题", "半导体", "高风险", 65.0),
    ("516160", "新能源ETF", "行业主题", "新能源", "高风险", 35.0),
    ("512010", "医药ETF", "行业主题", "医药", "高风险", 60.0),
    ("159928", "消费ETF", "行业主题", "消费", "高风险", 50.0),
    ("512880", "证券ETF", "行业主题", "证券", "高风险", 55.0),
]


if STATIC_CANDIDATES:
    FALLBACK_CANDIDATES = STATIC_CANDIDATES


def _money(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("万", "").replace("亿", "")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fallback_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "代码": code,
                "名称": name,
                "资产大类": asset_class,
                "方向": direction,
                "风险等级": risk_level,
                "成交额": amount,
                "规模": None,
                "数据来源": "内置基础示例池",
            }
            for code, name, asset_class, direction, risk_level, amount in FALLBACK_CANDIDATES
        ]
    )


def _filter_by_direction(df: pd.DataFrame, asset_class: str, direction: str) -> pd.DataFrame:
    keywords = DIRECTION_KEYWORDS.get(direction, [direction])
    frame = df.copy()
    if "资产大类" in frame.columns:
        frame = frame[(frame["资产大类"].isna()) | (frame["资产大类"] == asset_class)]
    text = (frame["名称"].fillna("") + " " + frame["代码"].fillna("")).astype(str)
    mask = text.apply(lambda value: any(keyword.lower() in value.lower() for keyword in keywords))
    result = frame[mask].copy()
    result["资产大类"] = result.get("资产大类", asset_class)
    result["方向"] = result.get("方向", direction)
    result["资产大类"] = result["资产大类"].fillna(asset_class)
    result["方向"] = result["方向"].fillna(direction)
    return result


def _score_metrics(asset_class: str, direction: str, history: pd.DataFrame, liquidity: float | None) -> dict:
    if history is None or history.empty or len(history) < 2:
        return {
            "近1年收益": None,
            "近3年收益": None,
            "最大回撤": None,
            "年化波动率": None,
            "夏普比率": None,
            "数据起始日期": "暂无",
            "数据年限": 0.0,
            "评分": 62,
            "备注": "暂未取得足够历史行情，先作为低置信度候选观察；请进入分析页再获取数据。",
        }

    history = history.sort_values("date").copy()
    years = max((pd.to_datetime(history["date"]).max() - pd.to_datetime(history["date"]).min()).days / 365.25, 0.01)
    one_year = calculate_return_by_period(history, 12)
    three_year = calculate_return_by_period(history, 36)
    max_drawdown = calculate_max_drawdown(history)
    volatility = calculate_annualized_volatility(history)
    sharpe = calculate_sharpe_ratio(history)

    data_score = min(years / 3, 1) * 15
    liquidity_score = 8 if liquidity is None else min(max(liquidity, 0) / 50, 1) * 15
    long_return = three_year if three_year is not None else one_year
    return_score = 10 if long_return is None else max(min((long_return + 0.2) / 0.5, 1), 0) * 20
    drawdown_score = max(min((0.45 + max_drawdown) / 0.45, 1), 0) * 20
    volatility_score = max(min((0.45 - volatility) / 0.45, 1), 0) * 10
    sharpe_score = max(min((sharpe + 0.5) / 2.5, 1), 0) * 10
    completeness_score = 5 if len(history) >= 240 else 2
    score = data_score + liquidity_score + return_score + drawdown_score + volatility_score + sharpe_score + completeness_score

    if years < 1:
        score -= 15
    if liquidity is not None and liquidity < 5:
        score -= 10
    if max_drawdown <= -0.45:
        score -= 12
    if volatility >= 0.45:
        score -= 8

    return {
        "近1年收益": one_year,
        "近3年收益": three_year,
        "最大回撤": max_drawdown,
        "年化波动率": volatility,
        "夏普比率": sharpe,
        "数据起始日期": pd.to_datetime(history["date"]).min().strftime("%Y-%m-%d"),
        "数据年限": round(years, 1),
        "评分": round(max(min(score, 100), 0), 1),
        "备注": "基于历史行情估算，费用和规模字段可能不完整。",
    }


def _classify(asset_class: str, direction: str, score: float, max_drawdown) -> str:
    high_risk_direction = asset_class == "行业主题" or direction in {"创业板", "科创板", "中证1000", "纳斯达克100", "恒生科技"}
    if score < 50:
        return "暂不适合"
    if high_risk_direction:
        return "高风险观察" if score >= 60 else "暂不适合"
    if max_drawdown is not None and max_drawdown <= -0.35:
        return "高风险观察"
    if score >= 80 and asset_class in {"现金/货币基金", "债券/短债", "宽基指数", "红利低波"}:
        return "核心观察"
    if score >= 60:
        return "普通观察"
    return "暂不适合"


def _static_screen_candidates(asset_class: str, direction: str, max_results: int = 10) -> dict:
    filtered = _filter_by_direction(_fallback_frame(), asset_class, direction)
    rows = []
    for _, item in filtered.head(max_results).iterrows():
        rows.append(
            {
                "代码": item.get("代码", ""),
                "名称": item.get("名称", ""),
                "资产大类": item.get("资产大类", asset_class),
                "方向": item.get("方向", direction),
                "评分": 62,
                "分类": "候选观察",
                "风险等级": item.get("风险等级", "中风险"),
                "近1年收益": None,
                "近3年收益": None,
                "最大回撤": None,
                "年化波动率": None,
                "夏普比率": None,
                "成交额/规模": _money(item.get("成交额")) or _money(item.get("规模")),
                "费用": "暂无",
                "数据起始日期": "未联网",
                "数据年限": 0.0,
                "备注": "快速模式仅展示常用示例候选，不生成收益、回撤、夏普等历史指标；请进入基金ETF分析页按严格口径分析。",
                "数据来源": "内置基础示例池",
            }
        )
    result = pd.DataFrame(rows)
    if not result.empty:
        result.insert(0, "排名", range(1, len(result) + 1))
    return {
        "results": result,
        "is_fallback": True,
        "message": "当前为快速候选池：仅读取内置常用示例，不调用重型行情接口。",
        "errors": [],
    }


def screen_candidates_by_direction(asset_class: str, direction: str, max_results: int = 10, mode: str = "quick") -> dict:
    if mode != "deep":
        return _static_screen_candidates(asset_class, direction, max_results=max_results)

    live_df, errors = fetch_available_fund_candidates()
    using_fallback = live_df.empty
    source_message = ""
    if using_fallback:
        source = _fallback_frame()
        source_message = "当前未能获取动态基金列表，已使用内置基础示例池。"
    else:
        source = live_df
        source_message = f"当前为动态筛选结果，数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}。"

    filtered = _filter_by_direction(source, asset_class, direction)
    if filtered.empty and not using_fallback:
        fallback_filtered = _filter_by_direction(_fallback_frame(), asset_class, direction)
        if not fallback_filtered.empty:
            filtered = fallback_filtered
            using_fallback = True
            source_message = "动态列表中没有筛到足够标的，已使用内置基础示例池兜底。"

    rows = []
    for _, item in filtered.head(max(max_results * 2, max_results)).iterrows():
        code = str(item.get("代码", "")).strip()
        if not code:
            continue
        data_result = fetch_asset_data_auto(code, preferred_type="自动识别", strict=False)
        history = data_result.get("data", pd.DataFrame()) if data_result.get("success") else pd.DataFrame()
        liquidity = _money(item.get("成交额")) or _money(item.get("规模"))
        metrics = _score_metrics(asset_class, direction, history, liquidity)
        category = _classify(asset_class, direction, metrics["评分"], metrics["最大回撤"])
        rows.append(
            {
                "代码": code,
                "名称": item.get("名称", code),
                "资产大类": item.get("资产大类", asset_class),
                "方向": item.get("方向", direction),
                "评分": metrics["评分"],
                "分类": category,
                "风险等级": item.get("风险等级") or ("高风险" if category == "高风险观察" else "中风险"),
                "近1年收益": metrics["近1年收益"],
                "近3年收益": metrics["近3年收益"],
                "最大回撤": metrics["最大回撤"],
                "年化波动率": metrics["年化波动率"],
                "夏普比率": metrics["夏普比率"],
                "成交额/规模": liquidity,
                "费用": "暂无",
                "数据起始日期": metrics["数据起始日期"],
                "数据年限": metrics["数据年限"],
                "备注": metrics["备注"],
                "数据来源": item.get("数据来源", "动态列表"),
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["评分", "成交额/规模"], ascending=[False, False], na_position="last").head(max_results)
        result.insert(0, "排名", range(1, len(result) + 1))

    return {
        "results": result,
        "is_fallback": using_fallback,
        "message": source_message,
        "errors": errors,
    }
