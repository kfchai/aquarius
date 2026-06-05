"""Pivot backtest: tokenized-gold cash-and-carry WITH funding credited.

Long XAUT spot / short xyz:GOLD perp = delta-neutral, earns funding (~8.69% APR)
while it waits to converge. Tests:
  (A) always-on carry — hold the whole window: funding + basis move - one round trip.
  (B) timed, low-frequency entries (carry-direction only, min-hold) with a cost sweep.

    python scripts/backtest_carry.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.engine import run_montecarlo, run_raw  # noqa: E402
from aquarius.backtest.strategy import MRParams  # noqa: E402
from aquarius.config import load_config  # noqa: E402

HIST = pathlib.Path("data/history")
BPY = 8760


def load(name):
    return pd.read_parquet(HIST / f"{name}.parquet")


def basis_with_funding(spot_name, perp="perp_gold_xyz", fund="perp_gold_xyz_funding"):
    s = load(spot_name)[["ts", "close"]].rename(columns={"close": "spot"})
    p = load(perp)[["ts", "close"]].rename(columns={"close": "perp"})
    m = s.merge(p, on="ts", how="inner").sort_values("ts").reset_index(drop=True)
    m["spread_bps"] = (m["spot"] - m["perp"]) / m["perp"] * 1e4
    f = load(fund)[["time", "fundingRate"]].rename(columns={"time": "fts"}).sort_values("fts")
    m = pd.merge_asof(m, f, left_on="ts", right_on="fts", direction="nearest", tolerance=3_600_000)
    m["fundingRate"] = m["fundingRate"].fillna(0.0)
    return m


def main():
    cfg = load_config()
    f = cfg["fees_bps"]
    cost = 2 * (f["binance_spot_maker"] + f["perp_gold_xyz_maker"])  # 23 bps modeled

    for spot_name, label in [("xaut_binance", "XAUT/Binance (clean ~70d)"),
                             ("xaut_bitfinex", "XAUT/Bitfinex (longer ~5.5mo)")]:
        m = basis_with_funding(spot_name)
        spread = m["spread_bps"].to_numpy()
        funding = m["fundingRate"].to_numpy()
        yrs = (m["ts"].iloc[-1] - m["ts"].iloc[0]) / 1000 / 86400 / 365
        print(f"\n{'='*80}\nBASIS carry — {label}")
        print(f"  bars={len(spread)}  span={yrs:.2f}y  modeled round-trip cost={cost:.0f} bps  "
              f"basis mean={np.nanmean(spread):.1f} bps")

        # (A) always-on carry: hold long-spot/short-perp the whole window
        fund_total = float(np.nansum(funding) * 1e4)          # side=+1 short perp earns it
        basis_move = float(spread[-1] - spread[0])            # long spread MtM
        carry_net = fund_total + basis_move - cost
        print(f"  (A) ALWAYS-ON carry: funding={fund_total:+.0f}  basis_move={basis_move:+.0f}  "
              f"-cost={-cost:.0f}  => NET {carry_net:+.0f} bps  "
              f"(= {carry_net/100/ max(yrs,1e-9):.1f}%/yr on notional)")

        # (B) timed, carry-direction, low-frequency — with vs without funding
        params = MRParams(lookback=168, z_entry=1.5, z_exit=0.25, z_stop=4.0,
                          min_hold=48, side_filter=+1)  # long-spot/short-perp only, hold >=2d
        nofund = run_raw(spread, params, cost, BPY, funding=None)
        wifund = run_raw(spread, params, cost, BPY, funding=funding)
        print(f"  (B) timed carry  z_entry=1.5 min_hold=48 side=+1:")
        print(f"        no funding : trades={nofund['n_trades']:3d}  net={nofund['net_bps_total']:8.1f}  "
              f"avg_hold={nofund['avg_hold_bars']:.0f}h  win={nofund['win_rate']*100:3.0f}%  "
              f"Sharpe={nofund['sharpe_ann']:.2f}  maxDD={nofund['max_dd_bps']:.0f}")
        print(f"        + funding  : trades={wifund['n_trades']:3d}  net={wifund['net_bps_total']:8.1f}  "
              f"(funding {wifund['funding_bps_total']:+.0f})  win={wifund['win_rate']*100:3.0f}%  "
              f"Sharpe={wifund['sharpe_ann']:.2f}  maxDD={wifund['max_dd_bps']:.0f}")

        # cost sweep (with funding)
        sweep = [(c, run_raw(spread, params, float(c), BPY, funding=funding)["net_bps_total"])
                 for c in [0, 5, 10, 15, 23, 30, 40]]
        be = next((c for c, n in sweep if n <= 0), None)
        print("        cost sweep (net @ cost, +funding): " +
              "  ".join(f"{c}->{n:.0f}" for c, n in sweep) + f"   break-even ~{be} bps")

        # MC intrabar on the timed carry (with funding)
        mc = run_montecarlo(spread, params, cost, BPY, substeps=12, n_seeds=40, funding=funding)
        print(f"        MC intrabar: net median={mc['net_bps_median']:.0f}  "
              f"profitable seeds={mc['frac_seeds_profitable']*100:.0f}%")

    print(f"\n{'='*80}\nNOTE: funding credited from real xyz:GOLD history. Spot-vs-perp is inherently "
          "cross-venue\n(spot CEX vs HL perp). Candle closes; modeled cost; de-peg tail not in PnL.")


if __name__ == "__main__":
    raise SystemExit(main())
