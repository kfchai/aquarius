"""Venue adapters: normalize each venue's market data into a Quote."""

from .cex_spot import CexSpotAdapter
from .hyperliquid import HyperliquidAdapter

__all__ = ["CexSpotAdapter", "HyperliquidAdapter"]
