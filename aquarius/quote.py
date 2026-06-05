"""Normalized quote across venues (spot + perp), flattened for tabular storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Quote:
    label: str
    venue: str
    symbol: str
    ts_ms: int
    bid: float
    ask: float
    bid_sz: float
    ask_sz: float
    # perp-only extras (None for spot)
    mark: Optional[float] = None
    oracle: Optional[float] = None
    funding: Optional[float] = None  # per-hour (Hyperliquid)
    open_interest: Optional[float] = None
    premium: Optional[float] = None
    day_ntl_vlm: Optional[float] = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_bps(self) -> float:
        m = self.mid
        return (self.ask - self.bid) / m * 1e4 if m else float("nan")

    def to_flat(self) -> dict:
        """Flatten to label-prefixed columns for one snapshot row."""
        from .metrics import funding_apr

        p = self.label
        row = {
            f"{p}_bid": self.bid,
            f"{p}_ask": self.ask,
            f"{p}_mid": self.mid,
            f"{p}_spread_bps": self.spread_bps,
            f"{p}_bid_sz": self.bid_sz,
            f"{p}_ask_sz": self.ask_sz,
        }
        if self.mark is not None:  # perp
            row[f"{p}_mark"] = self.mark
            row[f"{p}_oracle"] = self.oracle
            row[f"{p}_funding_hr"] = self.funding
            row[f"{p}_funding_apr"] = (
                funding_apr(self.funding) if self.funding is not None else None
            )
            row[f"{p}_oi"] = self.open_interest
            row[f"{p}_premium"] = self.premium
            row[f"{p}_day_ntl_vlm"] = self.day_ntl_vlm
        return row
