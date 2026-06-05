"""Backfill extra funding-carry legs: Binance spot + Hyperliquid perp candles + funding
for a few liquid majors, to test diversification alongside gold.

    python scripts/backfill_perps.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import (  # noqa: E402
    fetch_ccxt_ohlcv, fetch_hl_candles, fetch_hl_funding,
)

OUT = pathlib.Path("data/history")
START = "2025-12-01T00:00:00Z"      # overlap the gold perp window (~5.5mo)
COINS = {c: f"{c}/USDT" for c in [
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK",
    "LTC", "ADA", "SUI", "NEAR", "APT", "ARB", "OP",
]}


def save(df, name):
    if df is None or df.empty:
        print(f"  {name:22s} EMPTY"); return
    df.to_parquet(OUT / f"{name}.parquet", index=False)
    print(f"  {name:22s} {len(df):6d} rows  {df['dt'].min()} .. {df['dt'].max()}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for coin, spot_sym in COINS.items():
        try:
            save(fetch_ccxt_ohlcv("binance", spot_sym, "1h", START), f"spot_{coin}")
            save(fetch_hl_candles(coin, "1h", START), f"perp_{coin}")
            save(fetch_hl_funding(coin, START), f"funding_{coin}")
        except Exception as e:  # noqa: BLE001
            print(f"  {coin} FAIL {type(e).__name__}: {str(e)[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
