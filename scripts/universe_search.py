"""Universe search: which crypto basket gives the butterfly what it needs —
cross-sectional residuals that EXTEND (trend), are TWO-SIDED, and frequent?

For each candidate basket: build residuals (idiosyncratic deviation from the equal-weight
log-basket, detrended, cross-sectionally demeaned, z-scored), then measure the structural
discriminators — and a long-gamma P&L. The key metric is EXTEND-vs-REVERT: does a
dislocation grow over the next day (good, reaches the wing) or shrink (bad, the peg trap)?

    python scripts/universe_search.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import (  # noqa: E402
    DonchianParams, MRParams, run_convergence, run_gamma_additive,
)

HIST = pathlib.Path("data/history")
EMA, ZWIN, ZE, H = 168, 168, 1.5, 24   # detrend / z window / z-entry / horizon (bars)

UNIVERSES = {
    "stablecoins": ("stable_", ["USDC", "TUSD", "FDUSD", "BUSD", "USDP"]),
    "alts-15":     ("spot_", ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK",
                              "LTC", "ADA", "SUI", "NEAR", "APT", "ARB", "OP"]),
    "L1-6":        ("spot_", ["SOL", "AVAX", "NEAR", "APT", "SUI", "ADA"]),
}


def load(prefix, names):
    s = {}
    for n in names:
        f = HIST / f"{prefix}{n}.parquet"
        if f.exists():
            df = pd.read_parquet(f).sort_values("ts")
            s[n] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    return pd.DataFrame(s).dropna()


def residualize(prices):
    lp = np.log(prices)
    ratio = lp.sub(lp.mean(axis=1), axis=0)                      # idiosyncratic vs equal-wt basket
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0)                    # cross-sectional residual (bps)
    z = resid / resid.rolling(ZWIN, min_periods=24).std()
    return resid.dropna(), z.reindex(resid.dropna().index)


def metrics(name, prices):
    resid, z = residualize(prices)
    if len(resid) < ZWIN + H:
        print(f"  {name:12s} too little data"); return
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    Z = z.to_numpy()

    # extend-vs-revert: given |z|>ZE, mean change in |z| over next H bars (>0 extends)
    deltas = []
    for j in range(Z.shape[1]):
        zc = Z[:, j]
        idx = np.where(np.abs(zc[:-H]) > ZE)[0]
        deltas += list(np.abs(zc[idx + H]) - np.abs(zc[idx]))
    extend = float(np.nanmean(deltas)) if deltas else float("nan")

    any_disloc = (np.abs(z) > ZE).any(axis=1)
    two_sided = ((z > ZE).any(axis=1) & (z < -ZE).any(axis=1))
    freq = any_disloc.mean() * 100
    two = two_sided.mean() * 100

    # long-gamma P&L on residuals (vol-scaled deadband), summed across axes
    db = float(np.nanmedian(resid.std())) * 1.0
    cost = 8.0 if prefix_is_spot(name) else 2.0
    p = DonchianParams(entry_n=48, exit_n=12, deadband_bps=db, ref_n=720)
    mrp = MRParams(lookback=ZWIN, z_entry=1.5, z_exit=0.3, z_stop=5.0)
    lg = mr = 0.0
    for a in resid.columns:
        _, sp = run_gamma_additive(resid[a].to_numpy(), p, cost)            # long-gamma (butterfly)
        lg += sp.sum()
        _, sm = run_convergence(resid[a].to_numpy(), z[a].to_numpy(), mrp, cost)  # short-gamma (revert)
        mr += sm.sum()
    print(f"  {name:12s} ext/rev={extend:+.2f}  freq={freq:3.0f}%  2-sided={two:3.0f}%  db={db:5.0f}  "
          f"cost={cost:.0f}  | LONG-gamma={lg/100/max(yrs,1e-9):+6.0f}%/yr  "
          f"MEAN-REVERT={mr/100/max(yrs,1e-9):+6.0f}%/yr")


def prefix_is_spot(name):
    return name != "stablecoins"


def main():
    print(f"extend/revert > 0 = dislocations EXTEND (reach the wing); < 0 = REVERT (peg trap)\n")
    for name, (prefix, names) in UNIVERSES.items():
        prices = load(prefix, names)
        if prices.empty:
            print(f"  {name:12s} no data"); continue
        metrics(name, prices)
    print("\nWANTED: extend/revert > 0, two-sided high, LGpnl > 0. That's a universe the butterfly can work on.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
