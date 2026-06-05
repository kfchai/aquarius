"""Backfill public history into data/history/*.parquet.

    python scripts/backfill.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import (  # noqa: E402
    fetch_ccxt_ohlcv,
    fetch_hl_candles,
    fetch_hl_funding,
)

OUT = pathlib.Path("data/history")
TF = "1h"
SPOT_SINCE = "2025-01-01T00:00:00Z"
HL_SINCE = "2025-12-01T00:00:00Z"

# (name, kind, args)
JOBS = [
    ("paxg_binance", "ccxt", ("binance", "PAXG/USDT")),
    ("xaut_binance", "ccxt", ("binance", "XAUT/USDT")),   # ~70d (clean same-venue)
    ("xaut_bitfinex", "ccxt", ("bitfinex", "XAUT/USD")),  # long history (cross-venue)
    ("perp_gold_xyz", "hl_candles", ("xyz:GOLD",)),
    ("perp_gold_xyz_funding", "hl_funding", ("xyz:GOLD",)),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, kind, args in JOBS:
        try:
            if kind == "ccxt":
                df = fetch_ccxt_ohlcv(*args, timeframe=TF, since_iso=SPOT_SINCE)
            elif kind == "hl_candles":
                df = fetch_hl_candles(*args, interval=TF, start_iso=HL_SINCE)
            else:
                df = fetch_hl_funding(*args, start_iso=HL_SINCE)
            if df.empty:
                print(f"  {name:24s} EMPTY")
                continue
            path = OUT / f"{name}.parquet"
            df.to_parquet(path, index=False)
            print(f"  {name:24s} {len(df):6d} rows  {df['dt'].min()} .. {df['dt'].max()}")
        except Exception as e:  # noqa: BLE001
            print(f"  {name:24s} FAIL {type(e).__name__}: {str(e)[:80]}")
    print(f"-> {OUT.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
