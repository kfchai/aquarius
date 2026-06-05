"""Offline unit tests for the cost model. Run: python tests/test_costmodel.py"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.costmodel import (  # noqa: E402
    LegFill,
    cash_and_carry_round_trip,
    net_edge_bps,
    round_trip_cost_bps,
)


def test_leg_maker_pays_only_fee():
    # maker posts -> no spread crossing
    assert LegFill("x", fee_bps=1.5, spread_bps=4.0, mode="maker").cost_bps() == 1.5
    # rebate
    assert LegFill("x", fee_bps=-0.25, spread_bps=4.0, mode="maker").cost_bps() == -0.25


def test_leg_taker_crosses_half_spread():
    assert LegFill("x", fee_bps=4.5, spread_bps=4.0, mode="taker").cost_bps() == 4.5 + 2.0


def test_round_trip_sum():
    legs = [LegFill("a", 1.0, 0, "maker"), LegFill("b", 2.0, 0, "maker")]
    assert round_trip_cost_bps(legs) == 3.0


def test_cash_and_carry_maker():
    # all-maker round trip = 2*(spot_fee + perp_fee), no spread cost
    rt = cash_and_carry_round_trip(
        spot_fee_bps=10.0, spot_spread_bps=8.0,
        perp_fee_bps=1.5, perp_spread_bps=2.0, mode="maker",
    )
    assert math.isclose(rt["total_bps"], 2 * (10.0 + 1.5))  # = 23.0
    # this is the sobering reality: ~23 bps round trip on a maker carry


def test_net_edge():
    assert net_edge_bps(30.0, 23.0) == 7.0
    assert net_edge_bps(15.0, 23.0) == -8.0  # does not clear cost


if __name__ == "__main__":
    fns = [
        test_leg_maker_pays_only_fee,
        test_leg_taker_crosses_half_spread,
        test_round_trip_sum,
        test_cash_and_carry_maker,
        test_net_edge,
    ]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nALL {len(fns)} COSTMODEL TESTS PASSED")
