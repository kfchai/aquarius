"""THE genuine multi-leg manifold butterfly (what the design called for, finally built).

Basket: ETH + LSTs (stETH, cbETH, rETH) — multiple "wrappers" of ETH with a MOVING centroid.
  1. ratio_i = LST_i / ETH ; fair_i = EMA(ratio_i)  -> moving centroid ("imaginary tip")
  2. dev_i  = (ratio_i / fair_i - 1) in bps          -> wrapper i off its fair line
  3. centroid_t = mean_i(dev_i)                       -> the common move (shared ETH/LST factor)
  4. residual_i = dev_i - centroid_t                  -> RELATIVE dislocation (sum_i=0 => netted,
                                                         delta-neutral to ETH AND the common move)
  5. long-gamma on each residual, summed = netted butterfly (profits when ONE wrapper breaks vs peers).

    python scripts/butterfly_manifold.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import DonchianParams, run_gamma_additive  # noqa: E402

HIST = pathlib.Path("data/history")
AXES = ["stETH", "cbETH", "rETH"]
EMA = 30
P = DonchianParams(entry_n=7, exit_n=3, deadband_bps=50, ref_n=30)
COST = 20.0   # bps round-trip (LSTs trade on ETH L1 — gas-heavy; swept below)


def daily(name):
    df = pd.read_parquet(HIST / f"lst_{name}.parquet")[["ts", "price"]]
    day = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.floor("D")
    return df.assign(day=day).groupby("day")["price"].last()


def skew(x):
    x = np.asarray(x, float); x = x[x != 0]
    return float(((x - x.mean()) ** 3).mean() / x.std() ** 3) if len(x) > 2 and x.std() else float("nan")


def score(pnl):
    pnl = np.asarray(pnl, float); eq = np.cumsum(pnl); dd = eq - np.maximum.accumulate(eq)
    return float(eq[-1]), float(dd.min()), skew(pnl)


def butterfly_pnl(resid, cost):
    legs = {}
    caps = []
    for a in AXES:
        r = resid[a].dropna()
        tb, pb = run_gamma_additive(r.to_numpy(), P, cost)
        legs[a] = pd.Series(pb, index=r.index)
        for t in tb:
            caps.append((a, r.index[t["exit_i"]], t["net_bps"]))
    return pd.concat(legs, axis=1).fillna(0).sum(axis=1), caps


def main():
    px = pd.concat({n: daily(n) for n in ["WETH"] + AXES}, axis=1).sort_index().dropna(subset=["WETH"])
    dev = pd.DataFrame(index=px.index)
    for a in AXES:
        ratio = px[a] / px["WETH"]
        fair = ratio.ewm(span=EMA, min_periods=5).mean()
        dev[a] = (ratio / fair - 1.0) * 1e4
    cent = dev.mean(axis=1)
    resid = dev.sub(cent, axis=0)
    yrs = (px.index[-1] - px.index[0]).days / 365

    print(f"LST manifold: axes={AXES}  {px.index[0].date()}..{px.index[-1].date()} (~{yrs:.1f}y)")
    print(f"  deviation std (bps): " + "  ".join(f"{a}:{dev[a].std():.0f}" for a in AXES))
    print(f"  residual  std (bps): " + "  ".join(f"{a}:{resid[a].std():.0f}" for a in AXES) +
          "   <- smaller = common move netted out")
    smin = dev["stETH"].min()
    print(f"  worst stETH deviation = {smin:.0f} bps @ {dev['stETH'].idxmin().date()} (the de-peg)")

    B, caps = butterfly_pnl(resid, COST)                  # netted (manifold)
    S, _ = butterfly_pnl(dev, COST)                       # un-netted (single-axis sum)
    bn, bdd, bsk = score(B.to_numpy())
    sn, sdd, ssk = score(S.to_numpy())
    print(f"\nNETTED manifold butterfly : net={bn:7.0f} bps ({bn/100/yrs:5.1f}%/yr)  maxDD={bdd:6.0f}  skew={bsk:5.1f}")
    print(f"un-netted single-axis sum : net={sn:7.0f} bps ({sn/100/yrs:5.1f}%/yr)  maxDD={sdd:6.0f}  skew={ssk:5.1f}")

    print("\n  biggest captures (netted):")
    for a, when, net in sorted(caps, key=lambda x: -x[2])[:10]:
        print(f"    {when.date()}  {a:6s} {net:+.0f} bps")

    print("\n  cost sweep (netted net bps): " +
          "  ".join(f"{c}->{score(butterfly_pnl(resid, float(c))[0].to_numpy())[0]:.0f}" for c in [5, 10, 20, 40]))
    print("\nVERDICT: (a) does netting beat the un-netted sum?  (b) is it net-positive after L1-gas cost?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
