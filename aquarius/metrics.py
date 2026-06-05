"""Derived market-neutral metrics: funding APR, wrapper-spread, cash-and-carry basis.

All spreads are in basis points (1 bp = 0.01%). These are the *edge* signals we
forward-collect in Stage 2 (no usable history exists — see research/recon-report.md).
"""

from __future__ import annotations


def funding_apr(hourly_funding: float) -> float:
    """Hyperliquid funding is charged hourly; annualize it. e.g. 6.25e-6 -> ~5.48%."""
    return hourly_funding * 24.0 * 365.0


def wrapper_spread_bps(mid_a: float, mid_b: float) -> float:
    """Relative spread between two wrappers of the same underlying (a vs b), in bps.

    Positive => a richer than b. Both legs should track the same asset (e.g. PAXG vs
    XAUT, each = 1 oz gold), so this is delta-neutral to gold itself.
    """
    mid = (mid_a + mid_b) / 2.0
    return (mid_a - mid_b) / mid * 1e4 if mid else float("nan")


def basis_bps(spot_mid: float, perp_mid: float) -> float:
    """Cash-and-carry basis: tokenized-gold spot vs gold perp, in bps.

    Positive => spot rich to perp (sell spot / buy perp); negative => spot cheap.
    """
    return (spot_mid - perp_mid) / perp_mid * 1e4 if perp_mid else float("nan")


def compute_metrics(quotes_by_label: dict, cfg_metrics: dict) -> dict:
    """Compute all configured wrapper-spreads and bases from a snapshot's quotes."""
    out: dict = {}
    for w in cfg_metrics.get("wrapper_spreads", []) or []:
        a = quotes_by_label.get(w["a"])
        b = quotes_by_label.get(w["b"])
        if a is not None and b is not None:
            out[f"wspread_{w['name']}_bps"] = wrapper_spread_bps(a.mid, b.mid)
    for bb in cfg_metrics.get("bases", []) or []:
        s = quotes_by_label.get(bb["spot"])
        p = quotes_by_label.get(bb["perp"])
        if s is not None and p is not None:
            out[f"basis_{bb['name']}_bps"] = basis_bps(s.mid, p.mid)
    return out
