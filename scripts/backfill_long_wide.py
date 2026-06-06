"""Extend the 5-year (long_) set to a WIDE basket so breadth can be crisis-tested through
LUNA/3AC/FTX. Adds the coins that existed by ~2021 (drops the too-young ARB/OP/APT/SUI).

    python scripts/backfill_long_wide.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import fetch_ccxt_ohlcv  # noqa: E402

OUT = pathlib.Path("data/history")
START = "2021-06-01T00:00:00Z"
# beyond the 11 already in long_: liquid alts that existed by mid-2021
ADD = ["DOT", "ATOM", "UNI", "AAVE", "FIL", "ETC", "XLM", "ALGO", "ICP", "HBAR",
       "GRT", "SAND", "MANA", "AXS", "CRV", "INJ", "RUNE", "EGLD", "FLOW"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for c in ADD:
        path = OUT / f"long_{c}.parquet"
        try:
            df = fetch_ccxt_ohlcv("binance", f"{c}/USDT", "1h", since_iso=START)
            if df.empty:
                print(f"  {c:6s} EMPTY"); continue
            df.to_parquet(path, index=False)
            ok += 1
            print(f"  {c:6s} {len(df):7d} rows  {df['dt'].min().date()} .. {df['dt'].max().date()}")
        except Exception as e:  # noqa: BLE001
            print(f"  {c:6s} FAIL {type(e).__name__}: {str(e)[:70]}")
    print(f"\n{ok}/{len(ADD)} added; long_ set now has {len(list(OUT.glob('long_*.parquet')))} coins.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
