from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_fetcher import fetch_asset_data_with_cache
from src.database import init_db


DEFAULT_CODES = [
    "510300",
    "510500",
    "511010",
    "513500",
    "512760",
    "161725",
    "501225",
    "005827",
    "SPY",
    "QQQ",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Update public market-data cache.")
    parser.add_argument("codes", nargs="*", default=DEFAULT_CODES)
    parser.add_argument("--scope", default="自动识别")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    init_db()
    ok = 0
    failed = 0
    for code in args.codes:
        result = fetch_asset_data_with_cache(code, args.scope, force_refresh=args.force, strict=True)
        if result.get("success"):
            ok += 1
            print(f"OK {code} {result.get('asset_type')} rows={result.get('rows')} latest={result.get('latest_date')}")
        else:
            failed += 1
            print(f"FAIL {code} {result.get('message')}")
    print(f"done ok={ok} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
