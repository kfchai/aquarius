"""Multi-axis butterfly: run the tip-zone long-gamma rule across many dislocation-prone
stablecoin axes (each delta-neutral), aggregate, and ask the real question —
is there STEADY positive long-gamma flow across MULTIPLE real de-pegs, or one lucky event?

    python scripts/butterfly_basket.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import DonchianParams, run_donchian_gamma  # noqa: E402

HIST = pathlib.Path("data/history")
P = DonchianParams(entry_n=72, exit_n=12, deadband_bps=30, ref_n=720)
COST = 2.0       # bps round-trip (stablecoin pairs, maker)
EVENT_BPS = 50   # a "captured dislocation" = a trade netting more than this


def skew(x):
    x = np.asarray(x, float); x = x[x != 0.0]
    return float(((x - x.mean()) ** 3).mean() / x.std() ** 3) if len(x) > 2 and x.std() else float("nan")


def main():
    axes = sorted(p.stem[len("stable_"):] for p in HIST.glob("stable_*.parquet"))
    if not axes:
        print("no stable_*.parquet — run scripts/backfill_stables.py first"); return 1
    per_axis, all_trades = {}, []
    print("per-axis (deadband long-gamma):")
    print(f"  {'axis':6s} {'window':23s} {'net bps':>9s} {'events':>7s} {'best':>7s} {'bleed/mo%':>10s}")
    for name in axes:
        df = pd.read_parquet(HIST / f"stable_{name}.parquet").sort_values("ts").reset_index(drop=True)
        price = df["close"].to_numpy()
        trades, sp = run_donchian_gamma(price, P, COST)
        per_axis[name] = pd.Series(sp, index=df["ts"].to_numpy())
        dts = pd.to_datetime(df["dt"])
        wins = [t for t in trades if t["net_bps"] > EVENT_BPS]
        for t in trades:
            all_trades.append((name, dts.iloc[t["exit_i"]], t["net_bps"]))
        months = len(price) / 24 / 30
        bleed = sum(t["net_bps"] for t in trades if t["net_bps"] <= 0)
        print(f"  {name:6s} {dts.iloc[0].date()}..{dts.iloc[-1].date()}  {sp.sum():9.0f} "
              f"{len(wins):7d} {max((t['net_bps'] for t in trades), default=0):7.0f} "
              f"{bleed/100/max(months,1e-9):10.2f}")

    basket = pd.concat(per_axis, axis=1).sort_index().fillna(0.0).sum(axis=1)
    yrs = (basket.index[-1] - basket.index[0]) / 1000 / 86400 / 365
    print(f"\nBASKET ({len(axes)} axes, equal notional):")
    print(f"  net = {basket.sum():.0f} bps over ~{yrs:.1f}y  ({basket.sum()/100/max(yrs,1e-9):.1f}%/yr per unit notional)")
    print(f"  per-bar skew = {skew(basket.to_numpy()):.1f}  (long-gamma: many ~0 + rare spikes)")

    print("\n  biggest captures (when & where — are they spread out?):")
    for name, when, net in sorted(all_trades, key=lambda x: -x[2])[:12]:
        print(f"    {when.date()}  {name:6s} +{net:.0f} bps")

    pos = sum(n for *_, n in all_trades if n > 0)
    neg = sum(n for *_, n in all_trades if n <= 0)
    print(f"\n  total event payoff = +{pos:.0f} bps | total bleed = {neg:.0f} bps | "
          f"ratio = {abs(pos/neg):.1f}x" if neg else "")
    n_events = sum(1 for *_, n in all_trades if n > EVENT_BPS)
    print(f"  distinct captured dislocations (>{EVENT_BPS} bps): {n_events}")
    print("\nVERDICT: steady flow = several captures spread across time/axes with bounded bleed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
