"""Diversification robustness: does a basket of delta-neutral funding carries clear
Sharpe >= 1.5 WITHOUT hindsight?

Auto-discovers all carry legs in data/history. Reports per-leg Sharpe, correlation
(incl. tail correlation), and basket Sharpe under: equal-weight (no hindsight),
inverse-vol (in-sample, hindsight), and WALK-FORWARD inverse-vol (out-of-sample).

    python scripts/diversify.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

HIST = pathlib.Path("data/history")
BPY = 8760
WF_WINDOW = 720  # 30d trailing for out-of-sample inverse-vol weighting


def discover_legs():
    legs = {"GOLD": ("xaut_bitfinex", "perp_gold_xyz", "perp_gold_xyz_funding")}
    for p in sorted(HIST.glob("perp_*.parquet")):
        coin = p.stem[len("perp_"):]
        if coin == "gold_xyz":
            continue
        if (HIST / f"spot_{coin}.parquet").exists() and (HIST / f"funding_{coin}.parquet").exists():
            legs[coin] = (f"spot_{coin}", p.stem, f"funding_{coin}")
    return legs


def carry_returns(spot_name, perp_name, fund_name):
    s = pd.read_parquet(HIST / f"{spot_name}.parquet")[["ts", "close"]].rename(columns={"close": "spot"})
    p = pd.read_parquet(HIST / f"{perp_name}.parquet")[["ts", "close"]].rename(columns={"close": "perp"})
    m = s.merge(p, on="ts").sort_values("ts").reset_index(drop=True)
    m["spread_bps"] = (m["spot"] - m["perp"]) / m["perp"] * 1e4
    f = pd.read_parquet(HIST / f"{fund_name}.parquet")[["time", "fundingRate"]].rename(
        columns={"time": "fts"}).sort_values("fts")
    m = pd.merge_asof(m, f, left_on="ts", right_on="fts", direction="nearest", tolerance=3_600_000)
    m["fundingRate"] = m["fundingRate"].fillna(0.0)
    ret = m["spread_bps"].diff().fillna(0.0) + m["fundingRate"] * 1e4
    return pd.Series(ret.to_numpy(), index=m["ts"].to_numpy())


def sharpe(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return x.mean() / x.std(ddof=1) * np.sqrt(BPY) if len(x) > 1 and x.std(ddof=1) > 0 else float("nan")


def avg_offdiag(corr):
    m = corr.to_numpy()
    return float(m[~np.eye(len(m), dtype=bool)].mean())


def main():
    legs = discover_legs()
    rets = pd.concat({k: carry_returns(*v) for k, v in legs.items()}, axis=1).dropna()
    yrs = (rets.index[-1] - rets.index[0]) / 1000 / 86400 / 365
    print(f"legs={len(rets.columns)} {list(rets.columns)}\ncommon window: {len(rets)} bars (~{yrs:.2f}y)\n")

    print("per-leg Sharpe:")
    leg_sh = {k: sharpe(rets[k]) for k in rets.columns}
    print("  " + "  ".join(f"{k}:{leg_sh[k]:.2f}" for k in rets.columns))
    pos = sum(s > 0 for s in leg_sh.values())
    print(f"  positive-Sharpe legs: {pos}/{len(leg_sh)}")

    corr = rets.corr()
    eqr = rets.mean(axis=1)
    tail = rets[eqr <= eqr.quantile(0.10)]
    print(f"\ncorrelation: avg pairwise = {avg_offdiag(corr):.2f}  |  "
          f"avg in worst-10% bars (tail) = {avg_offdiag(tail.corr()):.2f}  <- corr->1 risk")

    # weighting schemes
    eq = rets.mean(axis=1)
    ivw = (1 / rets.std()); ivw /= ivw.sum()
    iv = (rets * ivw).sum(axis=1)
    vol = rets.rolling(WF_WINDOW).std()
    w = (1.0 / vol).shift(1)
    w = w.div(w.sum(axis=1), axis=0)
    wf = (rets * w).sum(axis=1).iloc[WF_WINDOW:]

    print("\nbasket Sharpe:")
    print(f"  equal-weight (NO hindsight)      = {sharpe(eq):5.2f}   ({eq.sum()/100/max(yrs,1e-9):.1f}%/yr)")
    print(f"  inverse-vol  (in-sample/hindsight)= {sharpe(iv):5.2f}")
    print(f"  walk-forward inverse-vol (OOS)   = {sharpe(wf):5.2f}   <- the honest weighted number")
    avg_leg = np.nanmean(list(leg_sh.values()))
    print(f"  avg single-leg = {avg_leg:.2f}  |  ideal-if-uncorrelated = {avg_leg*np.sqrt(len(rets.columns)):.2f}")

    print(f"\nGATE 1.5 -> equal-weight: {'PASS' if sharpe(eq)>=1.5 else 'FAIL'} | "
          f"walk-forward: {'PASS' if sharpe(wf)>=1.5 else 'FAIL'}")
    print(f"CAVEATS: single ~{yrs:.1f}y window, benign funding regime; tail corr shows crisis risk; "
          "cost one-off.")


if __name__ == "__main__":
    raise SystemExit(main())
