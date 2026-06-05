"""CEX spot adapter via ccxt (public order books — XAUT/PAXG). No auth/keys."""

from __future__ import annotations

import time

import ccxt

from ..quote import Quote


class CexSpotAdapter:
    def __init__(self, exchange_id: str):
        self.exchange_id = exchange_id
        self.ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})

    def fetch(self, symbol: str, label: str, depth: int = 5) -> Quote:
        ob = self.ex.fetch_order_book(symbol, limit=depth)
        # some venues return [price, amount, ...] — take the first two fields only
        bid_px, bid_sz = (ob["bids"][0][:2] if ob["bids"] else (float("nan"), 0.0))
        ask_px, ask_sz = (ob["asks"][0][:2] if ob["asks"] else (float("nan"), 0.0))
        # prefer the exchange's own timestamp when present
        ts = ob.get("timestamp") or int(time.time() * 1000)
        return Quote(
            label=label,
            venue=self.exchange_id,
            symbol=symbol,
            ts_ms=int(ts),
            bid=float(bid_px),
            ask=float(ask_px),
            bid_sz=float(bid_sz),
            ask_sz=float(ask_sz),
        )
