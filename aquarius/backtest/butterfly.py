"""Butterfly shape-integrity metric + rotation engine.

The butterfly is a STANDING basket of legs across residual axes. As dislocations move
legs into profit you bank them — but only if the structure survives. `shape_health`
measures whether the basket is still a valid butterfly:

  net_delta  = Σ side_i·size_i           -> market-neutral?  (target |net_delta| <= tol)
  net_gamma  = Σ size_i · (+1 if leg is WITH the current dislocation else -1)
                                          -> still long the wings?  (target > gamma_min)
  wings_ok   = at least one +side and one -side leg live  -> both wings covered?
  shape_holds = all three
  redundancy = how many legs can be dropped one-at-a-time while shape_holds stays true
               (the headline: how much you can scalp before you must reopen)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Leg:
    axis: str
    side: int        # +1 long the residual (opened when resid>0), -1 short (resid<0)
    entry: float     # residual value at entry (bps)
    size: float = 1.0


def _raw(legs: list[Leg], resid: dict) -> tuple[float, float, bool]:
    net_delta = sum(l.side * l.size for l in legs)
    net_gamma = sum(l.size * (1.0 if (resid.get(l.axis, 0.0) >= 0) == (l.side > 0) else -1.0)
                    for l in legs)
    has_up = any(l.side > 0 for l in legs)
    has_dn = any(l.side < 0 for l in legs)
    return net_delta, net_gamma, (has_up and has_dn)


def shape_health(legs: list[Leg], resid: dict, tol: float = 1.0, gamma_min: float = 0.0) -> dict:
    nd, ng, wings = _raw(legs, resid)
    holds = abs(nd) <= tol and ng > gamma_min and wings
    budget = 0
    for i in range(len(legs)):
        rest = legs[:i] + legs[i + 1:]
        nd2, ng2, w2 = _raw(rest, resid)
        if abs(nd2) <= tol and ng2 > gamma_min and w2:
            budget += 1
    return {"net_delta": nd, "net_gamma": ng, "wings_ok": wings,
            "holds": holds, "redundancy": budget}
