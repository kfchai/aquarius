"""Carry + convexity overlay: does the long-gamma overlay lift Sharpe past the gate?

Book 1 (carry): always-on long-spot/short-perp + funding (long-spread, +d(spread)).
Book 2 (overlay): option-free long-gamma momentum on the same spread (run_breakout_overlay).
Combined PnL = carry + size * overlay. Sweep overlay size and z_band.

    python scripts/backtest_overlay.py
"""

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import OverlayParams, run_breakout_overlay  # noqa: E402
from aquarius.config import load_config  # noqa: E402
from scripts.backtest_carry import basis_with_funding  # noqa: E402

BPY = 8760


def score(pnl: np.ndarray) -> dict:
    eq = np.cumsum(pnl)
    dd = eq - np.maximum.accumulate(eq)
    sharpe = pnl.mean() / pnl.std(ddof=1) * np.sqrt(BPY) if pnl.std(ddof=1) > 0 else float("nan")
    return {"net": float(eq[-1]), "sharpe": float(sharpe), "maxdd": float(dd.min())}


def main():
    cfg = load_config()
    f = cfg["fees_bps"]
    cost = 2 * (f["binance_spot_maker"] + f["perp_gold_xyz_maker"])  # 23 bps

    for spot, label in [("xaut_binance", "XAUT/Binance ~70d"),
                        ("xaut_bitfinex", "XAUT/Bitfinex ~5.5mo")]:
        m = basis_with_funding(spot)
        spread = m["spread_bps"].to_numpy()
        funding = m["fundingRate"].to_numpy()
        n = len(spread)
        yrs = (m["ts"].iloc[-1] - m["ts"].iloc[0]) / 1000 / 86400 / 365

        # carry per-bar pnl: always-on long-spread + funding, one-off entry cost
        carry = np.zeros(n)
        carry[1:] = np.diff(spread)
        carry += funding * 1e4
        carry[0] -= cost

        print(f"\n{'='*86}\n{label}   span={yrs:.2f}y  cost={cost:.0f}bps")
        c = score(carry)
        print(f"  carry alone           : net={c['net']:7.0f}  Sharpe={c['sharpe']:5.2f}  "
              f"maxDD={c['maxdd']/100:5.1f}%   (%/yr={c['net']/100/max(yrs,1e-9):.1f})")

        # overlay alone (unit) for transparency
        for zb in (2.0, 2.5, 3.0):
            ov, flips = run_breakout_overlay(spread, OverlayParams(z_band=zb), cost)
            o = score(ov)
            print(f"  overlay z_band={zb} alone: net={o['net']:7.0f}  Sharpe={o['sharpe']:5.2f}  "
                  f"flips={flips:3d}   (long-gamma bleed/payoff)")

        print(f"  {'COMBINED carry+size*overlay':28s}  size:   " +
              "   ".join(f"{s:>4.2f}" for s in (0.25, 0.5, 1.0, 1.5, 2.0)))
        for zb in (2.0, 2.5, 3.0):
            ov, _ = run_breakout_overlay(spread, OverlayParams(z_band=zb), cost)
            sharpes, nets = [], []
            for s in (0.25, 0.5, 1.0, 1.5, 2.0):
                r = score(carry + s * ov)
                sharpes.append(r["sharpe"])
                nets.append(r["net"])
            print(f"    z_band={zb}  Sharpe   :        " +
                  "  ".join(f"{x:5.2f}" for x in sharpes))
            print(f"    z_band={zb}  net(bps) :        " +
                  "  ".join(f"{x:5.0f}" for x in nets))

    print(f"\n{'='*86}\nGATE: carry+overlay needs Sharpe >= 1.5 with net still positive. "
          "Overlay bleeds standalone\n(long-gamma premium); it earns its keep only if it cuts the "
          "carry's variance enough.")


if __name__ == "__main__":
    raise SystemExit(main())
