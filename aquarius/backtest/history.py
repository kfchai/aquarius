"""Public historical data backfill — CEX spot OHLCV (ccxt) + Hyperliquid perp candles/funding.

Free, no keys. Candle CLOSES only — no historical bid/ask (that stays live-collected).
"""

from __future__ import annotations

import json
import time
import urllib.request

import ccxt
import httpx
import pandas as pd

HL_URL = "https://api.hyperliquid.xyz/info"


def fetch_llama_chart(coin: str, start_iso: str = "2022-01-01T00:00:00Z",
                      end_iso: str | None = None, period: str = "1d",
                      chunk: int = 300) -> pd.DataFrame:
    """DefiLlama free historical prices (full on-chain history), paginated in
    `chunk`-point requests (the API caps span per call). `coin` = 'chain:address'.
    Returns ts(ms), price, dt. One coin per call (multi-coin requests 400)."""
    step = {"1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800}.get(period, 86400)
    cur = int(pd.Timestamp(start_iso).timestamp())
    end = int(pd.Timestamp(end_iso).timestamp()) if end_iso else int(time.time())
    rows: list = []
    while cur < end:
        url = f"https://coins.llama.fi/chart/{coin}?start={cur}&span={chunk}&period={period}"
        raw = json.loads(urllib.request.urlopen(url, timeout=60).read())
        coins = raw.get("coins", {})
        pts = list(coins.values())[0].get("prices", []) if coins else []
        if not pts:
            break
        rows += pts
        nxt = pts[-1]["timestamp"] + step
        if nxt <= cur:  # no progress
            break
        cur = nxt
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ts"] = (df["timestamp"] * 1000).astype("int64")
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df[["ts", "price", "dt"]].drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def _now_ms() -> int:
    return int(time.time() * 1000)


def fetch_ccxt_ohlcv(
    exchange_id: str, symbol: str, timeframe: str = "1h",
    since_iso: str = "2025-01-01T00:00:00Z", limit: int = 1000,
) -> pd.DataFrame:
    """Paginated OHLCV. Columns: ts(ms), open, high, low, close, volume, dt(UTC)."""
    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    since = ex.parse8601(since_iso)
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    rows: list = []
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not batch:
            break
        rows += batch
        new_since = batch[-1][0] + tf_ms
        if new_since <= since:  # no progress (some venues cap a call below `limit`)
            break
        since = new_since
        if since >= _now_ms():
            break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df


def _hl_post(body: dict):
    with httpx.Client(timeout=30) as c:
        r = c.post(HL_URL, json=body)
        r.raise_for_status()
        return r.json()


def fetch_hl_candles(
    coin: str, interval: str = "1h", start_iso: str = "2025-12-01T00:00:00Z"
) -> pd.DataFrame:
    start = int(pd.Timestamp(start_iso).timestamp() * 1000)
    raw = _hl_post({"type": "candleSnapshot",
                    "req": {"coin": coin, "interval": interval,
                            "startTime": start, "endTime": _now_ms()}})
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    df = df.rename(columns={"t": "ts", "o": "open", "h": "high",
                            "l": "low", "c": "close", "v": "volume"})
    for k in ["open", "high", "low", "close", "volume"]:
        df[k] = df[k].astype(float)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df[["ts", "open", "high", "low", "close", "volume", "dt"]]


def fetch_hl_funding(coin: str, start_iso: str = "2025-12-01T00:00:00Z") -> pd.DataFrame:
    start = int(pd.Timestamp(start_iso).timestamp() * 1000)
    end = _now_ms()
    rows: list = []
    cur = start
    while True:
        batch = _hl_post({"type": "fundingHistory", "coin": coin,
                          "startTime": cur, "endTime": end})
        if not batch:
            break
        rows += batch
        last = batch[-1]["time"]
        if len(batch) < 500 or last <= cur:
            break
        cur = last + 1
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    return df
