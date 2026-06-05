"""Two rotation modes compared on the stablecoin residual basket (dense ladder):
  PROFIT-driven : bank a leg when it hits profit_take; reopen if that breaks the shape.
  SKEW-driven   : do nothing until net_delta skews past tol; then close the most-profitable
                  leg on the OVER-loaded side to un-skew (profit = selection, not trigger).

Honest fills: entry = actual residual at open (no phantom rung profit). Reports whether
skew-driven keeps the shape balanced AND banks positive without forced reopens.

    python scripts/shape_metric.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.butterfly import Leg, shape_health  # noqa: E402

HIST = pathlib.Path("data/history")
EMA = 168
PROFIT_TAKE, MAX_LOSS, EXIT_ZONE = 30.0, 60.0, 6.0
TOL, GAMMA_MIN, COST = 2.0, 0.0, 2.0
SKEW_TOL, MIN_PROFIT = 1.5, 5.0
SKEW_TOL_EXP = 40.0   # bps of net wing-exposure imbalance tolerated before rebalancing
DB, STEP, RUNGS = 8.0, 6.0, 6   # dense ladder (redundancy ~2 from prior sweep)


def residuals():
    axes = sorted(p.stem[len("stable_"):] for p in HIST.glob("stable_*.parquet"))
    dev = {}
    for a in axes:
        df = pd.read_parquet(HIST / f"stable_{a}.parquet").sort_values("ts")
        fair = df["close"].ewm(span=EMA, min_periods=24).mean()
        dev[a] = pd.Series(((df["close"] / fair - 1) * 1e4).to_numpy(), index=df["ts"].to_numpy())
    dev = pd.DataFrame(dev).sort_index()
    return axes, dev.sub(dev.mean(axis=1), axis=0)


def run(axes, resid, mode):
    legs: dict[str, Leg] = {}
    banked = 0.0
    n_bank = n_reopen = n_cut = n_unfix = 0
    rec = []
    rows = resid.to_dict("index")

    def prof(leg, rd):
        return leg.side * (rd[leg.axis] - leg.entry)

    for ts in resid.index:
        rd = {a: v for a, v in rows[ts].items() if not (isinstance(v, float) and np.isnan(v))}
        for a, v in rd.items():                                   # open ladder rungs (entry = v)
            for r in range(1, RUNGS + 1):
                key = f"{a}#{r}"
                if abs(v) > DB + (r - 1) * STEP and key not in legs:
                    legs[key] = Leg(a, 1 if v > 0 else -1, v)
        for key in list(legs):                                    # hard cut + normalize exit (both modes)
            leg = legs[key]
            if leg.axis not in rd:
                continue
            p = prof(leg, rd)
            if p <= -MAX_LOSS:
                banked += p - COST; n_cut += 1; del legs[key]
            elif abs(rd[leg.axis]) < EXIT_ZONE:
                banked += p - COST; del legs[key]

        if mode == "profit":
            for key in list(legs):
                leg = legs[key]
                if leg.axis in rd and prof(leg, rd) >= PROFIT_TAKE:
                    others = [l for k, l in legs.items() if k != key]
                    keeps = shape_health(others, rd, TOL, GAMMA_MIN)["holds"]
                    banked += prof(leg, rd) - COST; n_bank += 1; del legs[key]
                    if not keeps and abs(rd[leg.axis]) > abs(leg.entry):
                        legs[key] = Leg(leg.axis, leg.side, leg.entry); n_reopen += 1; banked -= COST
        else:  # skew-driven, EXPOSURE-weighted bi-directional skew
            guard = 0
            while guard < 50:
                guard += 1
                # skew = Σ size·(resid - centroid); centroid=0 for demeaned residuals
                S = sum(l.size * rd[l.axis] for l in legs.values() if l.axis in rd)
                if abs(S) <= SKEW_TOL_EXP:
                    break
                over = 1 if S > 0 else -1            # up-heavy -> close a long(up) leg
                cands = [(k, prof(l, rd)) for k, l in legs.items()
                         if l.side == over and l.axis in rd and prof(l, rd) > MIN_PROFIT]
                if not cands:
                    n_unfix += 1
                    break
                k = max(cands, key=lambda x: x[1])[0]
                banked += prof(legs[k], rd) - COST; n_bank += 1; del legs[k]

        h = shape_health(list(legs.values()), rd, TOL, GAMMA_MIN)
        rec.append((h["holds"], h["redundancy"], abs(h["net_delta"]), len(legs)))

    R = pd.DataFrame(rec, columns=["holds", "redun", "absd", "nlegs"])
    act = R[R["nlegs"] > 0]
    return {"holds": act["holds"].mean() * 100, "absd": act["absd"].mean(),
            "redun": act["redun"].mean(), "legs": act["nlegs"].mean(),
            "banked": banked, "banks": n_bank, "reopens": n_reopen, "cuts": n_cut,
            "unfix": n_unfix}


def main():
    axes, resid = residuals()
    print(f"axes={axes}  dense ladder db={DB} step={STEP} rungs={RUNGS}\n")
    print(f"  {'mode':14s} {'holds%':>7s} {'mean|delta|':>11s} {'redun':>6s} {'legs':>5s} "
          f"{'banked':>9s} {'banks':>6s} {'reopens':>8s} {'cuts':>5s} {'skew_unfix':>11s}")
    for mode in ["profit", "skew"]:
        m = run(axes, resid, mode)
        print(f"  {mode:14s} {m['holds']:7.1f} {m['absd']:11.2f} {m['redun']:6.2f} {m['legs']:5.1f} "
              f"{m['banked']:9.0f} {m['banks']:6d} {m['reopens']:8d} {m['cuts']:5d} {m['unfix']:11d}")
    print("\nSKEW-driven wins if: keeps mean|delta| low (balanced), banked >= profit-mode, "
          "and reopens -> 0.\n(P&L still subject to the long-gamma reversion cost via cuts/normalize-exits.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
