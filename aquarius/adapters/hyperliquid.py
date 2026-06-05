"""Hyperliquid public info API adapter (perps incl. HIP-3 builder dexs).

Market data only — no auth, no keys. Confirmed shapes (2026):
  metaAndAssetCtxs(dex) -> [meta, ctxs]; ctx has markPx/oraclePx/midPx/funding/
                           openInterest/premium/dayNtlVlm (index-aligned to universe).
  l2Book(coin)          -> {levels: [bids, asks]} with px/sz/n per level.
HIP-3 coins are namespaced, e.g. "xyz:GOLD".
"""

from __future__ import annotations

import time

import httpx

from ..quote import Quote


class HyperliquidAdapter:
    def __init__(self, api_url: str, timeout_sec: float = 15.0):
        self.api_url = api_url
        self._client = httpx.Client(timeout=timeout_sec)
        self._idx_cache: dict[str, dict[str, int]] = {}  # dex -> {coin: index}

    def _post(self, body: dict):
        r = self._client.post(self.api_url, json=body)
        r.raise_for_status()
        return r.json()

    def _index_of(self, coin: str, dex: str, meta: dict) -> int:
        cache = self._idx_cache.setdefault(dex, {})
        if coin not in cache:
            cache.clear()
            for i, a in enumerate(meta["universe"]):
                cache[a["name"]] = i
        return cache[coin]

    def fetch_perp(self, coin: str, dex: str, label: str) -> Quote:
        meta, ctxs = self._post({"type": "metaAndAssetCtxs", "dex": dex})
        ctx = ctxs[self._index_of(coin, dex, meta)]
        lb = self._post({"type": "l2Book", "coin": coin})
        bids, asks = lb["levels"][0], lb["levels"][1]
        bid = float(bids[0]["px"]) if bids else float("nan")
        ask = float(asks[0]["px"]) if asks else float("nan")
        bid_sz = float(bids[0]["sz"]) if bids else 0.0
        ask_sz = float(asks[0]["sz"]) if asks else 0.0
        return Quote(
            label=label,
            venue="hyperliquid",
            symbol=coin,
            ts_ms=int(time.time() * 1000),
            bid=bid,
            ask=ask,
            bid_sz=bid_sz,
            ask_sz=ask_sz,
            mark=float(ctx["markPx"]),
            oracle=float(ctx["oraclePx"]),
            funding=float(ctx["funding"]),
            open_interest=float(ctx["openInterest"]),
            premium=float(ctx.get("premium", "nan")),
            day_ntl_vlm=float(ctx.get("dayNtlVlm", "nan")),
        )

    def close(self) -> None:
        self._client.close()
