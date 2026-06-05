"""Genuine multi-leg manifold butterfly on the STABLECOIN basket (clean hourly data,
recurring real de-pegs). The proper netted version that findings-08 was NOT.

  dev_i = (price_i / EMA(price_i) - 1) bps         (each stable off its own fair line)
  centroid_t = mean_i(dev_i)                         (common USDT-denominator move)
  residual_i = dev_i - centroid_t                    (RELATIVE de-peg; sum_i = 0 => netted)
  long-gamma on each residual, summed = netted butterfly.
Compares netted (manifold) vs un-netted (findings-08-style) to isolate what netting buys.

    python scripts/butterfly_manifold_stables.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import DonchianParams, run_gamma_additive  # noqa: E402

HIST = pathlib.Path("data/history")
P = DonchianParams(entry_n=48, exit_n=12, deadband_bps=30, ref_n=720)
EMA = 168
COST = 2.0


def skew(x):
    x = np.asarray(x, float); x = x[x != 0]
    return float(((x - x.mean()) ** 3).mean() / x.std() ** 3) if len(x) > 2 and x.std() else float("nan")


def score(pnl):
    pnl = np.asarray(pnl, float); eq = np.cumsum(pnl); dd = eq - np.maximum.accumulate(eq)
    return float(eq[-1]), float(dd.min()), skew(pnl)


def main():
    axes = sorted(p.stem[len("stable_"):] for p in HIST.glob("stable_*.parquet"))
    dev = {}
    for a in axes:
        df = pd.read_parquet(HIST / f"stable_{a}.parquet").sort_values("ts")
        price = df["close"]
        fair = price.ewm(span=EMA, min_periods=24).mean()
        dev[a] = pd.Series(((price / fair - 1.0) * 1e4).to_numpy(), index=df["ts"].to_numpy())
    dev = pd.DataFrame(dev).sort_index()
    cent = dev.mean(axis=1)
    resid = dev.sub(cent, axis=0)
    yrs = (dev.index[-1] - dev.index[0]) / 1000 / 86400 / 365
    print(f"stablecoin manifold: axes={axes}  ~{yrs:.1f}y")
    print(f"  deviation std: " + " ".join(f"{a}:{dev[a].std():.0f}" for a in axes))
    print(f"  residual  std: " + " ".join(f"{a}:{resid[a].std():.0f}" for a in axes))

    def basket(frame):
        legs, caps = {}, []
        for a in axes:
            s = frame[a].dropna()
            tb, pb = run_gamma_additive(s.to_numpy(), P, COST)
            legs[a] = pd.Series(pb, index=s.index)
            for t in tb:
                caps.append((a, s.index[t["exit_i"]], t["net_bps"]))
        return pd.concat(legs, axis=1).fillna(0).sum(axis=1), caps

    B, caps = basket(resid)     # netted (manifold)
    S, _ = basket(dev)          # un-netted (single-axis sum)
    bn, bdd, bsk = score(B.to_numpy())
    sn, sdd, ssk = score(S.to_numpy())
    print(f"\nNETTED manifold butterfly : net={bn:8.0f} bps ({bn/100/yrs:5.1f}%/yr)  maxDD={bdd:7.0f}  skew={bsk:5.1f}")
    print(f"un-netted single-axis sum : net={sn:8.0f} bps ({sn/100/yrs:5.1f}%/yr)  maxDD={sdd:7.0f}  skew={ssk:5.1f}")

    print("\n  biggest captures (netted):")
    for a, when, net in sorted(caps, key=lambda x: -x[2])[:8]:
        print(f"    {pd.to_datetime(when, unit='ms', utc=True).date()}  {a:6s} {net:+.0f} bps")
    print("\nVERDICT: does cross-sectional netting make the genuine manifold butterfly net-positive?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
