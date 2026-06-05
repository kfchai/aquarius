"""Backfill a BROAD liquid-alt universe (hourly) to test the 'many tiny legs' capacity thesis:
does spreading the book across more coins raise BOTH Sharpe (diversification) and capacity
(smaller per-leg orders -> lower sqrt-impact)?

~2y common window (since 2023-06) so most mid-caps exist. Saved under `broad_` prefix.

    python scripts/backfill_broad.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import fetch_ccxt_ohlcv  # noqa: E402

OUT = pathlib.Path("data/history")
START = "2023-06-01T00:00:00Z"
COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA",
    "NEAR", "DOT", "ATOM", "UNI", "AAVE", "FIL", "ETC", "XLM", "ALGO", "ICP",
    "HBAR", "GRT", "SAND", "MANA", "AXS", "APE", "CRV", "INJ", "ARB", "OP",
    "APT", "SUI", "RUNE", "EGLD", "FLOW",
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for c in COINS:
        path = OUT / f"broad_{c}.parquet"
        try:
            df = fetch_ccxt_ohlcv("binance", f"{c}/USDT", "1h", since_iso=START)
            if df.empty:
                print(f"  {c:6s} EMPTY"); continue
            df.to_parquet(path, index=False)
            ok += 1
            print(f"  {c:6s} {len(df):6d} rows  {df['dt'].min().date()} .. {df['dt'].max().date()}")
        except Exception as e:  # noqa: BLE001
            print(f"  {c:6s} FAIL {type(e).__name__}: {str(e)[:70]}")
    print(f"\n{ok}/{len(COINS)} coins saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
