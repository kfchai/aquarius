"""Backfill dislocation-prone USD-stablecoin axes (hourly) for the multi-axis butterfly.
Each is a delta-neutral residual that should sit at 1.0 and occasionally de-pegs.

    python scripts/backfill_stables.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import fetch_ccxt_ohlcv  # noqa: E402

OUT = pathlib.Path("data/history")
# (name, exchange, symbol, since) — different real de-peg events at different times
JOBS = [
    ("USDC", "okx", "USDC/USDT", "2022-01-01T00:00:00Z"),      # Mar-2023 SVB de-peg -> 0.87
    ("TUSD", "binance", "TUSD/USDT", "2022-06-01T00:00:00Z"),  # Jun-2025 de-peg -> 0.91
    ("FDUSD", "binance", "FDUSD/USDT", "2023-07-01T00:00:00Z"),# Apr-2025 de-peg -> 0.87
    ("BUSD", "binance", "BUSD/USDT", "2022-06-01T00:00:00Z"),  # 2023 wind-down wobbles
    ("USDP", "binance", "USDP/USDT", "2022-06-01T00:00:00Z"),
    ("USDD", "binance", "USDD/USDT", "2022-06-01T00:00:00Z"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, exid, sym, since in JOBS:
        try:
            df = fetch_ccxt_ohlcv(exid, sym, "1h", since_iso=since, limit=300)
            if df.empty:
                print(f"  {name:6s} EMPTY"); continue
            df.to_parquet(OUT / f"stable_{name}.parquet", index=False)
            print(f"  {name:6s} {len(df):6d} rows  {df['dt'].min()} .. {df['dt'].max()}  "
                  f"min_low={df['low'].min():.4f}")
        except Exception as e:  # noqa: BLE001
            print(f"  {name:6s} FAIL {type(e).__name__}: {str(e)[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
