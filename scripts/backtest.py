"""Backtest the convergence structure on backfilled history.

For each candidate spread: reconstruct it (bps), show the distribution vs cost,
run the mean-reversion strategy on raw closes AND on Monte-Carlo intra-bar paths,
and sweep cost to find break-even.

    python scripts/backtest.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.engine import (  # noqa: E402
    run_montecarlo, run_raw, spread_distribution,
)
from aquarius.backtest.strategy import MRParams  # noqa: E402
from aquarius.config import load_config  # noqa: E402

HIST = pathlib.Path("data/history")
BARS_PER_YEAR = 8760  # hourly


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(HIST / f"{name}.parquet")


def aligned_spread(a_name: str, b_name: str, kind: str) -> tuple[np.ndarray, pd.DataFrame]:
    a = load(a_name)[["ts", "close"]].rename(columns={"close": "a"})
    b = load(b_name)[["ts", "close"]].rename(columns={"close": "b"})
    m = a.merge(b, on="ts", how="inner").sort_values("ts").reset_index(drop=True)
    if kind == "wrapper":  # (a - b) / mid
        spread = (m["a"] - m["b"]) / ((m["a"] + m["b"]) / 2) * 1e4
    else:                  # basis: (spot - perp) / perp ; a=spot, b=perp
        spread = (m["a"] - m["b"]) / m["b"] * 1e4
    m["spread_bps"] = spread
    return spread.to_numpy(), m


def report(title: str, spread: np.ndarray, m: pd.DataFrame, cost_bps: float, params: MRParams):
    yrs = (m["ts"].iloc[-1] - m["ts"].iloc[0]) / 1000 / 86400 / 365
    print(f"\n{'='*78}\n{title}\n  bars={len(spread)}  span={yrs:.2f}y  modeled round-trip cost={cost_bps:.1f} bps")

    dist = spread_distribution(spread, cost_bps, params.lookback)
    print(f"  spread: mean={dist['spread_mean_bps']:.1f}  std={dist['spread_std_bps']:.1f} bps | "
          f"|dev| p50={dist['abs_dev_p50_bps']:.1f}  p95={dist['abs_dev_p95_bps']:.1f} bps | "
          f"frac(|dev|>cost)={dist['frac_dev_gt_cost']*100:.1f}%")

    raw = run_raw(spread, params, cost_bps, BARS_PER_YEAR)
    print(f"  RAW closes : trades={raw['n_trades']:4d}  net={raw['net_bps_total']:8.1f} bps  "
          f"gross={raw['gross_bps_total']:8.1f}  avg/trade={raw['avg_net_per_trade']:6.2f}  "
          f"win={raw['win_rate']*100:4.0f}%  Sharpe={raw['sharpe_ann']:5.2f}  "
          f"maxDD={raw['max_dd_bps']:7.1f}  stops={raw['n_stops']}")

    mc = run_montecarlo(spread, params, cost_bps, BARS_PER_YEAR, substeps=12, n_seeds=50)
    print(f"  MC intrabar: net median={mc['net_bps_median']:8.1f} bps  "
          f"[p25={mc['net_bps_p25']:.1f}, p75={mc['net_bps_p75']:.1f}]  "
          f"profitable seeds={mc['frac_seeds_profitable']*100:.0f}%  "
          f"Sharpe~{mc['sharpe_ann_median']:.2f}")

    # cost sweep -> break-even
    sweep = []
    for c in [0, 5, 10, 20, 23, 30, 40, 60]:
        r = run_raw(spread, params, float(c), BARS_PER_YEAR)
        sweep.append((c, r["net_bps_total"], r["n_trades"]))
    be = next((c for c, net, _ in sweep if net <= 0), None)
    print("  cost sweep (net bps @ cost): " +
          "  ".join(f"{c}->{net:.0f}" for c, net, _ in sweep) +
          f"   break-even cost ~{be} bps" if be is not None else "")


def main() -> int:
    cfg = load_config()
    f = cfg["fees_bps"]
    params = MRParams(lookback=168, z_entry=2.0, z_exit=0.5, z_stop=4.0)

    # perp funding context (tailwind for the basis structure, not credited below)
    fund = load("perp_gold_xyz_funding")
    apr = fund["fundingRate"].mean() * 24 * 365 * 100
    print(f"xyz:GOLD mean funding over history: {apr:.2f}% APR "
          f"(basis cash-and-carry earns this on top — not included in PnL below)")

    structures = [
        ("BASIS — XAUT(binance) spot vs xyz:GOLD perp", "xaut_binance", "perp_gold_xyz",
         "basis", 2 * (f["binance_spot_maker"] + f["perp_gold_xyz_maker"])),
        ("WRAPPER (same-venue) — PAXG vs XAUT, Binance", "paxg_binance", "xaut_binance",
         "wrapper", 2 * (f["binance_spot_maker"] + f["binance_spot_maker"])),
        ("WRAPPER (cross-venue) — PAXG(binance) vs XAUT(bitfinex)", "paxg_binance", "xaut_bitfinex",
         "wrapper", 2 * (f["binance_spot_maker"] + f["binance_spot_maker"])),
    ]
    for title, a, b, kind, cost in structures:
        try:
            spread, m = aligned_spread(a, b, kind)
            report(title, spread, m, cost, params)
        except Exception as e:  # noqa: BLE001
            print(f"\n{title}\n  FAIL {type(e).__name__}: {e}")

    print(f"\n{'='*78}\nNOTE: candle-close reconstruction + synthetic intra-bar paths (no real "
          "bid/ask).\nCost is modeled & pessimistic. Basis PnL excludes the funding tailwind above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
