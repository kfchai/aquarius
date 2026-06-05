"""Funding-gated carry: hold long-spot/short-perp only while funding pays.

Sweeps entry/exit funding thresholds (in APR) and compares Sharpe to the always-on
carry. The gate reads the slow funding level, not the noisy spread.

    python scripts/backtest_funding_gated.py
"""

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.engine import run_funding_gated_scored  # noqa: E402
from aquarius.backtest.strategy import FundingGateParams  # noqa: E402
from aquarius.config import load_config  # noqa: E402
from scripts.backtest_carry import basis_with_funding  # noqa: E402

BPY = 8760


def apr_to_hr(apr_pct: float) -> float:
    return apr_pct / 100.0 / BPY


def main():
    cfg = load_config()
    f = cfg["fees_bps"]
    cost = 2 * (f["binance_spot_maker"] + f["perp_gold_xyz_maker"])  # 23 bps

    # (label, f_entry_apr, f_exit_apr, smooth, min_hold)
    configs = [
        ("always-on (baseline)", -999.0, -999.0, 1, 0),
        ("gate >0% / <0%",         0.0,    0.0,   8, 0),
        ("gate >5% / <0%",         5.0,    0.0,   8, 24),
        ("gate >5% / <2% (hyst)",  5.0,    2.0,   8, 24),
        ("gate >10% / <3%",       10.0,    3.0,   8, 24),
    ]

    for spot, label in [("xaut_binance", "XAUT/Binance ~70d"),
                        ("xaut_bitfinex", "XAUT/Bitfinex ~5.5mo")]:
        m = basis_with_funding(spot)
        spread = m["spread_bps"].to_numpy()
        funding = m["fundingRate"].to_numpy()
        yrs = (m["ts"].iloc[-1] - m["ts"].iloc[0]) / 1000 / 86400 / 365
        print(f"\n{'='*84}\n{label}   span={yrs:.2f}y  cost={cost:.0f}bps  "
              f"mean funding={funding.mean()*BPY*100:.1f}% APR")
        print(f"  {'config':24s} {'net':>7s} {'%/yr':>6s} {'Sharpe':>7s} {'maxDD%':>7s} "
              f"{'inMkt':>6s} {'trades':>6s} {'fund':>7s}")
        for name, fe, fx, sm, mh in configs:
            p = FundingGateParams(f_entry=apr_to_hr(fe), f_exit=apr_to_hr(fx),
                                  smooth=sm, min_hold=mh, side=+1)
            r = run_funding_gated_scored(spread, funding, p, cost, BPY)
            print(f"  {name:24s} {r['equity_bps']:7.0f} {r['equity_bps']/100/max(yrs,1e-9):6.1f} "
                  f"{r['sharpe_ann']:7.2f} {r['max_dd_bps']/100:7.1f} "
                  f"{r['time_in_market']*100:5.0f}% {r['n_trades']:6d} {r['funding_bps_total']:7.0f}")

        # cost sweep on the best-by-Sharpe simple gate
        best = FundingGateParams(f_entry=apr_to_hr(5.0), f_exit=apr_to_hr(0.0),
                                 smooth=8, min_hold=24, side=+1)
        sweep = [(c, run_funding_gated_scored(spread, funding, best, float(c), BPY))
                 for c in [0, 5, 10, 15, 23, 30]]
        print("  cost sweep (gate >5%/<0%, net bps): " +
              "  ".join(f"{c}->{r['equity_bps']:.0f}" for c, r in sweep))

    print(f"\n{'='*84}\nNOTE: gate reads funding level (slow) so it does not whipsaw on intra-bar "
          "spread noise.\nBasis-widening MtM still applies while held (the de-peg tail the overlay would cap).")


if __name__ == "__main__":
    raise SystemExit(main())
