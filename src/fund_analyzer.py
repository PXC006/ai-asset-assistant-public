import pandas as pd

from .metrics import calculate_asset_metrics


def analyze_fund_dataframe(df: pd.DataFrame) -> dict:
    """Analyze fund/ETF price or NAV history with the shared metrics engine."""
    return calculate_asset_metrics(df)
