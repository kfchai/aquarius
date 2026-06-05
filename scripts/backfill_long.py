"""Backfill MULTI-YEAR hourly OHLCV for the older alt subset (existed by 2021), to test the
reversal basket out-of-sample THROUGH real crises (LUNA, 3AC, FTX, Aug-2024 unwind).

The 4 youngest of the 15 (SUI/APT/ARB/OP) didn't exist in 2022 and the residual basket join is
limited by the youngest member -> excluded here so we can reach the 2022 cascades. Saved under a
`long_` prefix so the 6-month `spot_` set stays intact.

    python scripts/backfill_long.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import fetch_ccxt_ohlcv  # noqa: E402

OUT = pathlib.Path("data/history")
START = "2021-06-01T00:00:00Z"   # covers 2021 top, LUNA, 3AC, FTX, 2023-24, Aug-24 unwind
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA", "NEAR"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for c in COINS:
        path = OUT / f"long_{c}.parquet"
        try:
            df = fetch_ccxt_ohlcv("binance", f"{c}/USDT", "1h", since_iso=START)
            if df.empty:
                print(f"  {c:6s} EMPTY"); continue
            df.to_parquet(path, index=False)
            print(f"  {c:6s} {len(df):7d} rows  {df['dt'].min()} .. {df['dt'].max()}")
        except Exception as e:  # noqa: BLE001
            print(f"  {c:6s} FAIL {type(e).__name__}: {str(e)[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
