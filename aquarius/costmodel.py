"""Execution cost model — the POC linchpin.

Core law (CLAUDE.md): an edge exists only if realized edge > honestly-measured
cost-hurdle. This module turns fees + observed spreads into a round-trip cost in bps,
so any measured wrapper-spread / basis can be judged net of cost.

A "leg fill" costs: the fee, plus half the spread *if* you cross (taker). A maker
fill pays only the fee (you post and wait). A full cash-and-carry round trip is
4 fills: open spot, open perp, close spot, close perp.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LegFill:
    name: str
    fee_bps: float       # per-side fee (negative = rebate)
    spread_bps: float    # current book spread of that leg
    mode: str = "maker"  # "maker" (post) or "taker" (cross)

    def cost_bps(self) -> float:
        crossing = self.spread_bps / 2.0 if self.mode == "taker" else 0.0
        return self.fee_bps + crossing


def round_trip_cost_bps(legs: list[LegFill]) -> float:
    """Total cost in bps for a set of fills (e.g. the 4 fills of a carry round trip)."""
    return sum(leg.cost_bps() for leg in legs)


def cash_and_carry_round_trip(
    spot_fee_bps: float,
    spot_spread_bps: float,
    perp_fee_bps: float,
    perp_spread_bps: float,
    mode: str = "maker",
) -> dict:
    """Round-trip cost of a tokenized-gold cash-and-carry (open + close, both legs).

    Returns the total and the per-leg breakdown, all in bps.
    """
    legs = [
        LegFill("spot_open", spot_fee_bps, spot_spread_bps, mode),
        LegFill("perp_open", perp_fee_bps, perp_spread_bps, mode),
        LegFill("spot_close", spot_fee_bps, spot_spread_bps, mode),
        LegFill("perp_close", perp_fee_bps, perp_spread_bps, mode),
    ]
    total = round_trip_cost_bps(legs)
    return {
        "total_bps": total,
        "breakdown": {leg.name: leg.cost_bps() for leg in legs},
        "mode": mode,
    }


def net_edge_bps(gross_edge_bps: float, cost_bps: float) -> float:
    """Edge after cost. Positive => the trade clears the cost-hurdle."""
    return gross_edge_bps - cost_bps
