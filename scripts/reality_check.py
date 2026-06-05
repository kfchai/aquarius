"""Reality-check the alt mean-reversion result: is it a real edge or microstructure
(bid-ask bounce) that dies under a 1-bar execution lag and realistic cost?

Lag = act on LAST bar's signal, fill at THIS bar (no same-bar look-ahead / no trading
the instantaneous bounce). Sweep cost. If P&L collapses with lag/cost -> it was a mirage.

    python scripts/reality_check.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import MRParams, run_convergence  # noqa: E402

HIST = pathlib.Path("data/history")
EMA, ZWIN = 168, 168
ALTS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK",
        "LTC", "ADA", "SUI", "NEAR", "APT", "ARB", "OP"]


def load_resid():
    s = {}
    for n in ALTS:
        f = HIST / f"spot_{n}.parquet"
        if f.exists():
            df = pd.read_parquet(f).sort_values("ts")
            s[n] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    prices = pd.DataFrame(s).dropna()
    lp = np.log(prices)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    return resid, z


def main():
    resid, z = load_resid()
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    mrp = MRParams(lookback=ZWIN, z_entry=1.5, z_exit=0.3, z_stop=5.0)
    print(f"alts-15 mean-reversion, {yrs:.1f}y. P&L (%/yr) by execution lag x cost:\n")
    print(f"  {'lag(bars)':>10s} " + "".join(f"{c:>9}bps" for c in [8, 20, 40, 80]))
    for lag in [0, 1, 2, 3]:
        zl = z.shift(lag)
        row = []
        for cost in [8, 20, 40, 80]:
            pnl = 0.0
            for a in resid.columns:
                _, sm = run_convergence(resid[a].to_numpy(), zl[a].to_numpy(), mrp, float(cost))
                pnl += sm.sum()
            row.append(pnl / 100 / max(yrs, 1e-9))
        print(f"  {lag:>10d} " + "".join(f"{v:>+12.0f}" for v in row))
    print("\nIf rows collapse toward 0 (or negative) at lag>=1 / higher cost -> bid-ask-bounce "
          "mirage, not a tradeable edge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
