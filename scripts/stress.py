"""Funding-flip / de-peg STRESS test — does the convexity overlay earn its keep?

A diversified carry basket's worst case is a CORRELATED deleveraging crisis: all legs'
funding flips negative together (corr -> 1, so no diversification benefit) AND the basis
blows out. We model one representative leg (= the basket under a common shock) over a calm
month + a 1-week crisis, and test the overlay against ITS charter gate:
  (a) calm-regime bleed <= 1% / month, AND (b) cuts crisis drawdown >= 50%.

    python scripts/stress.py
"""

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import OverlayParams, run_breakout_overlay  # noqa: E402
from aquarius.config import load_config  # noqa: E402

BPY = 8760
CALM, CRISIS = 720, 168          # hours: ~30d calm + ~1wk crisis
PHI = 0.9                         # AR(1) mean-reversion of the calm basis


def synth_path(rng, spread_vol=8.0, depeg=200.0, calm_apr=8.0, crisis_apr=-40.0):
    n = CALM + CRISIS
    s = np.zeros(n)
    eps = spread_vol * np.sqrt(1 - PHI**2)
    for t in range(1, CALM):
        s[t] = PHI * s[t - 1] + rng.normal(0, eps)
    step = -depeg / CRISIS
    for k in range(CRISIS):
        t = CALM + k
        s[t] = PHI * s[t - 1] + rng.normal(0, eps) + step
    funding = np.empty(n)
    funding[:CALM] = calm_apr / 100 / BPY
    funding[CALM:] = crisis_apr / 100 / BPY
    return s, funding


def carry_pnl(spread, funding):
    p = np.zeros(len(spread))
    p[1:] = np.diff(spread)
    return p + funding * 1e4


def crisis_loss(pnl):
    eq = np.cumsum(pnl)
    base = eq[CALM - 1]
    return float(-(eq[CALM:] - base).min())  # max drawdown from crisis onset (positive bps)


def main():
    cfg = load_config()
    f = cfg["fees_bps"]
    cost = 2 * (f["binance_spot_maker"] + f["perp_gold_xyz_maker"])
    op = OverlayParams(lookback=168, z_band=2.5, z_exit=0.5)
    sizes = [0.0, 0.5, 1.0, 2.0, 3.0]
    seeds = 60

    print(f"Stress: {CALM}h calm (funding +8% APR) + {CRISIS}h crisis (funding -40% APR, "
          f"basis -200 bps).\nOverlay z_band=2.5, cost={cost:.0f}bps/flip. Median over {seeds} seeds.\n")
    print(f"  {'size':>5s} {'crisisLoss':>11s} {'vs carry':>9s} {'calmBleed%/mo':>13s}  gate(>=50% & <=1%/mo)")

    base_loss = None
    for size in sizes:
        losses, bleeds = [], []
        for sd in range(seeds):
            rng = np.random.default_rng(sd)
            spread, funding = synth_path(rng)
            carry = carry_pnl(spread, funding)
            ov, _ = run_breakout_overlay(spread, op, cost)
            pnl = carry + size * ov
            losses.append(crisis_loss(pnl))
            bleeds.append(float(np.sum(size * ov[:CALM]) / 100))  # % over the 30d calm window
        loss = float(np.median(losses)); bleed = float(np.median(bleeds))
        if size == 0.0:
            base_loss = loss
        red = (base_loss - loss) / base_loss * 100 if base_loss else 0.0
        ok = (red >= 50) and (bleed >= -1.0)
        print(f"  {size:5.1f} {loss:11.0f} {red:8.0f}% {bleed:13.2f}  "
              f"{'PASS' if ok and size>0 else ('carry-only' if size==0 else 'no')}")

    print("\nNOTE: synthetic correlated shock (worst case: corr->1, no diversification). "
          "Calm bleed\nshould be small & negative (a cost); crisis loss should shrink with overlay size.")


if __name__ == "__main__":
    raise SystemExit(main())
