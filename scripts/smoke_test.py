"""Live smoke test: one real poll of every venue + a cost-model sanity check.

Hits live public APIs (no keys). Prints the snapshot, applies the cost model to
the observed gold cash-and-carry, and exits non-zero if anything looks broken.

    python scripts/smoke_test.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.config import load_config  # noqa: E402
from aquarius.costmodel import cash_and_carry_round_trip, net_edge_bps  # noqa: E402
from aquarius.recorder import Recorder  # noqa: E402


def main() -> int:
    cfg = load_config()
    rec = Recorder(cfg)
    row = rec.poll_once()
    rec.hl.close()

    print("=== live snapshot ===")
    for k in sorted(row):
        v = row[k]
        if isinstance(v, float):
            print(f"  {k:32s} {v:,.4f}")
        else:
            print(f"  {k:32s} {v}")

    ok = True
    if row.get("n_ok", 0) < 2:
        print("FAIL: fewer than 2 venues returned data"); ok = False
    if row.get("n_err", 0):
        print(f"WARN: {row['n_err']} venue error(s): {row.get('errors')}")

    # cost-model sanity on the gold cash-and-carry (XAUT spot vs xyz:GOLD perp)
    fees = cfg["fees_bps"]
    spot_spread = row.get("xaut_binance_spread_bps")
    perp_spread = row.get("perp_gold_xyz_spread_bps")
    basis = row.get("basis_xaut_vs_perp_bps")
    if None not in (spot_spread, perp_spread, basis):
        rt = cash_and_carry_round_trip(
            spot_fee_bps=fees["binance_spot_maker"],
            spot_spread_bps=spot_spread,
            perp_fee_bps=fees["perp_gold_xyz_maker"],
            perp_spread_bps=perp_spread,
            mode="maker",
        )
        net = net_edge_bps(abs(basis), rt["total_bps"])
        print("\n=== cost model — gold cash-and-carry (maker, round trip) ===")
        print(f"  observed |basis|      {abs(basis):8.2f} bps")
        print(f"  round-trip cost       {rt['total_bps']:8.2f} bps  {rt['breakdown']}")
        print(f"  net edge              {net:8.2f} bps  ({'CLEARS' if net > 0 else 'does NOT clear'} cost)")
    else:
        print("WARN: missing fields for cost-model check (gold legs not all present)")

    print("\nSMOKE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
