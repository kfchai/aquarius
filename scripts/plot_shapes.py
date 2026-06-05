"""Snapshot the butterfly's implied payoff shape at several dates and plot them.

Runs the with-the-move ladder rotation on the stablecoin residual basket, snapshots the
live legs at chosen dates, and draws each basket's implied long-gamma payoff:
each leg adds a capped ramp ("wing") starting at its entry; the deadband is the flat tip.
Wing asymmetry (left vs right height) = the skew.

    python scripts/plot_shapes.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.butterfly import Leg  # noqa: E402

HIST = pathlib.Path("data/history")
EMA = 168
DB, STEP, RUNGS = 8.0, 6.0, 6
EXIT_ZONE, MAX_LOSS = 6.0, 60.0
WIDTH = 25.0     # bps over which each wing ramps to its cap
N_SNAPS = 20     # snapshots spread across the active timeline


def residuals():
    axes = sorted(p.stem[len("stable_"):] for p in HIST.glob("stable_*.parquet"))
    dev = {}
    for a in axes:
        df = pd.read_parquet(HIST / f"stable_{a}.parquet").sort_values("ts")
        fair = df["close"].ewm(span=EMA, min_periods=24).mean()
        dev[a] = pd.Series(((df["close"] / fair - 1) * 1e4).to_numpy(), index=df["ts"].to_numpy())
    dev = pd.DataFrame(dev).sort_index()
    return axes, dev.sub(dev.mean(axis=1), axis=0)


def payoff(legs, x):
    """Implied butterfly VALUE vs dislocation level x (bps). Wings ramp from the
    deadband 'strikes' (±DB), like a standard option payoff — so a far-out dislocation
    sits high in the wing, not at its base. Flat tip inside the deadband."""
    p = np.full_like(x, -0.4 if legs else 0.0)  # tip (cost) inside the deadband
    for lg in legs:
        if lg.side > 0:          # up-leg -> right wing, ramping from +DB
            p += lg.size * np.clip((x - DB) / WIDTH, 0, 1)
        else:                    # down-leg -> left wing, ramping from -DB
            p += lg.size * np.clip((-x - DB) / WIDTH, 0, 1)
    return p


def main():
    axes, resid = residuals()
    legs: dict[str, Leg] = {}
    active = []   # (ts, [legs]) for every step that holds a basket
    rows = resid.to_dict("index")
    for ts in resid.index:
        rd = {a: v for a, v in rows[ts].items() if not (isinstance(v, float) and np.isnan(v))}
        for a, v in rd.items():
            for r in range(1, RUNGS + 1):
                key = f"{a}#{r}"
                if abs(v) > DB + (r - 1) * STEP and key not in legs:
                    legs[key] = Leg(a, 1 if v > 0 else -1, v)
        for key in list(legs):
            lg = legs[key]
            if lg.axis in rd and (abs(rd[lg.axis]) < EXIT_ZONE
                                  or lg.side * (rd[lg.axis] - lg.entry) <= -MAX_LOSS):
                del legs[key]
        if legs:
            active.append((ts, list(legs.values()), dict(rd)))

    # pick N snapshots spread evenly across the active CALENDAR timeline
    ats = np.array([a[0] for a in active])
    targets = np.linspace(ats[0], ats[-1], N_SNAPS)
    picks = [active[int(np.argmin(np.abs(ats - t)))] for t in targets]

    def classify(up, dn):
        if up == 0 or dn == 0:
            return ("BEAR spread (broken)" if up == 0 else "BULL spread (broken)"), "red"
        if abs(up - dn) >= 2:
            return ("RIGHT-skew fly" if up > dn else "LEFT-skew fly"), "darkorange"
        return "butterfly", "green"

    x = np.linspace(-120, 120, 600)
    fig, axs = plt.subplots(4, 5, figsize=(19, 12))
    counts = {"butterfly": 0, "skew": 0, "broken": 0}
    for ax, (ts, lg, rd) in zip(axs.flat, picks):
        up = sum(l.size for l in lg if l.side > 0)
        dn = sum(l.size for l in lg if l.side < 0)
        tag, color = classify(up, dn)
        counts["broken" if color == "red" else ("skew" if color == "darkorange" else "butterfly")] += 1
        ax.plot(x, payoff(lg, x), lw=2, color=color)
        ax.axhline(0, color="k", lw=0.7); ax.axvline(0, color="k", lw=0.7)
        # current composite x (size-weighted mean live dislocation) + per-leg ticks
        xs = [rd[l.axis] for l in lg if l.axis in rd]
        xc = float(np.mean(xs)) if xs else 0.0
        for xi in {round(v) for v in xs}:
            ax.axvline(xi, color="gray", alpha=0.18, lw=0.6)
        ax.axvline(xc, color="royalblue", ls="--", lw=1.1)
        ax.plot([xc], [float(payoff(lg, np.array([xc]))[0])], "o", color="royalblue", ms=6, zorder=5)
        d = pd.Timestamp(ts, unit="ms", tz="utc").date()
        ax.set_title(f"{d}  n={len(lg)} ({int(up)}/{int(dn)})  {tag}   x≈{xc:.0f}", fontsize=9)
        ax.grid(alpha=0.25); ax.tick_params(labelsize=7)
    fig.suptitle("Payoff shapes over time — GREEN=real butterfly, ORANGE=skewed, "
                 "RED=broken wing (bull/bear spread, NOT neutral)", fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "butterfly_shapes.png"
    fig.savefig(path, dpi=105)

    # honest census over ALL active steps (not just the 20 shown)
    cen = {"butterfly": 0, "skew": 0, "broken": 0}
    for _, lg, _ in active:
        u = sum(l.size for l in lg if l.side > 0); d_ = sum(l.size for l in lg if l.side < 0)
        _, c = classify(u, d_)
        cen["broken" if c == "red" else ("skew" if c == "darkorange" else "butterfly")] += 1
    tot = max(len(active), 1)
    all_res = [abs(rd[l.axis]) for _, lg, rd in active for l in lg if l.axis in rd]
    deep = np.mean([r >= DB + WIDTH for r in all_res]) * 100 if all_res else 0
    comp = [abs(np.mean([rd[l.axis] for l in lg if l.axis in rd])) for _, lg, rd in active]
    in_wing = np.mean([c >= DB + WIDTH for c in comp]) * 100 if comp else 0
    print(f"saved {path}  (shown: {counts})")
    print(f"leg depth: mean|resid|={np.mean(all_res):.0f}bps, deep-in-wing(>{int(DB+WIDTH)}bps)={deep:.0f}% of legs")
    print(f"composite-x: in a wing(>{int(DB+WIDTH)}bps)={in_wing:.0f}% of active steps (else near tip)")
    print(f"census over all {len(active)} active steps: "
          f"real butterfly {cen['butterfly']/tot*100:.0f}% | skewed {cen['skew']/tot*100:.0f}% | "
          f"BROKEN-WING spread {cen['broken']/tot*100:.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
