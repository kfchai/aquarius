"""Portal core — compute the shadow-trading state + live charts. No Flask here, so this is
testable offline (SOURCE=local reads cached broad_*.parquet; SOURCE=live fetches via ccxt).

Produces a state dict with stats, current positions, and four base64 PNGs:
  capital  — equity ($) + drawdown over the shadow window
  butterfly— the live short-gamma TENT with each open leg plotted where it sits right now
  swarm    — current z-dislocation of every coin (entry / stop bands)
  neutral  — coin-leg tilt vs the basket-hedge-zeroed net delta
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import pathlib
import sqlite3
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.paper.shadow import ShadowConfig, run_shadow, PPY  # noqa: E402
from aquarius.backtest.history import fetch_ccxt_ohlcv  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCHANGE = os.environ.get("EXCHANGE", "bybit")
SOURCE = os.environ.get("SOURCE", "live")           # 'live' | 'local'
N_COINS = int(os.environ.get("N_COINS", "20"))
GROSS = float(os.environ.get("GROSS", "100000"))
DAYS = int(os.environ.get("DAYS", "30"))
DATA_DIR = pathlib.Path(os.environ.get("DATA_DIR", str(ROOT / "data" / "shadow")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"        # disposable rendered view (atomic write, self-heals)
DB_FILE = DATA_DIR / "shadow.db"            # durable truth — per-bar P&L + trades (SQLite/WAL)

COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA",
         "NEAR", "DOT", "ATOM", "UNI", "AAVE", "FIL", "ETC", "XLM", "INJ", "ARB",
         "OP", "APT", "SUI", "ICP", "HBAR"]
CFG = ShadowConfig(gross=GROSS)
log = logging.getLogger("aquarius")


# ---------- data ----------
def _frame(close, tr, dv):
    return pd.DataFrame(close), pd.DataFrame(tr), pd.DataFrame(dv)


def load_local():
    hist = ROOT / "data" / "history"
    close, tr, dv = {}, {}, {}
    for c in COINS:
        f = hist / f"broad_{c}.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f).sort_values("ts")
        ts = d["ts"].to_numpy()
        close[c] = pd.Series(d["close"].to_numpy(), index=ts)
        tr[c] = pd.Series(((d["high"] - d["low"]) / d["close"] * 1e4).to_numpy(), index=ts)
        dv[c] = pd.Series((d["close"] * d["volume"]).to_numpy(), index=ts)
    return _frame(close, tr, dv)


def load_live():
    since = pd.Timestamp(time.time() - (DAYS + 20) * 86400, unit="s", tz="utc").isoformat()
    close, tr, dv = {}, {}, {}
    for c in COINS:
        try:
            d = fetch_ccxt_ohlcv(EXCHANGE, f"{c}/USDT", "1h", since_iso=since)
            if d.empty:
                continue
            ts = d["ts"].to_numpy()
            close[c] = pd.Series(d["close"].to_numpy(), index=ts)
            tr[c] = pd.Series(((d["high"] - d["low"]) / d["close"] * 1e4).to_numpy(), index=ts)
            dv[c] = pd.Series((d["close"] * d["volume"]).to_numpy(), index=ts)
        except Exception:  # noqa: BLE001  — skip a coin that the venue lacks/blocks
            continue
    return _frame(close, tr, dv)


# ---------- durable store (SQLite/WAL) ----------
def _db():
    con = sqlite3.connect(DB_FILE, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("CREATE TABLE IF NOT EXISTS pnl(ts INTEGER PRIMARY KEY, delta REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS trades(id TEXT PRIMARY KEY, coin TEXT, side INTEGER,"
                " entry_ts INTEGER, exit_ts INTEGER, gross_bps REAL, reason TEXT, cost_bps REAL DEFAULT 0)")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    if "cost_bps" not in [r[1] for r in con.execute("PRAGMA table_info(trades)").fetchall()]:
        con.execute("ALTER TABLE trades ADD COLUMN cost_bps REAL DEFAULT 0")  # migrate old DBs
    return con


def persist(pnl_by_ts: dict, trades: list, now_iso: str):
    """Upsert new per-bar P&L and closed trades; record live_since once. Atomic per transaction."""
    con = _db()
    try:
        with con:  # one transaction — commit-or-rollback, never a half-write
            con.executemany("INSERT INTO pnl(ts,delta) VALUES(?,?) "
                            "ON CONFLICT(ts) DO UPDATE SET delta=excluded.delta",
                            list(pnl_by_ts.items()))
            con.executemany("INSERT INTO trades(id,coin,side,entry_ts,exit_ts,gross_bps,reason,cost_bps) "
                            "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                            [(f"{t['exit_ts']}_{t['coin']}", t["coin"], t["side"], t["entry_ts"],
                              t["exit_ts"], t["gross_bps"], t["reason"], t.get("cost_bps", 0.0))
                             for t in trades])
            con.execute("INSERT INTO meta(k,v) VALUES('live_since',?) ON CONFLICT(k) DO NOTHING",
                        (now_iso,))
    finally:
        con.close()


def load_series():
    con = _db()
    try:
        ts, dl = zip(*con.execute("SELECT ts,delta FROM pnl ORDER BY ts").fetchall()) or ((), ())
        trades = con.execute("SELECT gross_bps,reason,exit_ts FROM trades").fetchall()
        live = con.execute("SELECT v FROM meta WHERE k='live_since'").fetchone()
    except ValueError:
        ts, dl, trades, live = (), (), [], None
    finally:
        con.close()
    return np.array(ts, dtype="int64"), np.array(dl, dtype=float), trades, (live[0] if live else None)


_COLS = "coin,side,entry_ts,exit_ts,gross_bps,reason,cost_bps"


def _fmt_trades(rows, notional):
    """Format DB trade rows. pnl = NET (gross residual move − realized round-trip cost) × notional;
    alloc = capital allocated to the leg (equal-weight notional)."""
    out = []
    for coin, side, ets, xts, g, reason, cost in rows:
        net_bps = g - (cost or 0.0)
        out.append({"coin": coin, "side": "SHORT" if side < 0 else "LONG",
                    "exit": pd.to_datetime(int(xts), unit="ms", utc=True).strftime("%m-%d %H:%M"),
                    "hold": int((xts - ets) / 3_600_000), "reason": reason,
                    "alloc": round(notional), "gross_bps": round(g), "cost_bps": round(cost or 0.0),
                    "pnl": round(net_bps / 1e4 * notional)})
    return out


def db_stats():
    """Quick persistence check for the boot log: does the durable store already hold data?"""
    if not DB_FILE.exists():
        return False, 0, None
    con = _db()
    try:
        n = con.execute("SELECT COUNT(*) FROM pnl").fetchone()[0]
        r = con.execute("SELECT v FROM meta WHERE k='live_since'").fetchone()
    finally:
        con.close()
    return True, n, (r[0] if r else None)


def load_recent_trades(live_ms: int, notional: float, limit: int = 30):
    con = _db()
    try:
        rows = con.execute(f"SELECT {_COLS} FROM trades WHERE exit_ts>=? "
                           "ORDER BY exit_ts DESC LIMIT ?", (live_ms, limit)).fetchall()
    finally:
        con.close()
    return _fmt_trades(rows, notional)


def load_closed_page(live_since: str, notional: float, page: int = 1, per_page: int = 12):
    """One page of forward closed trades, newest first. Returns (rows, total, n_pages)."""
    live_ms = int(pd.Timestamp(live_since).value // 1_000_000) if live_since else 0
    con = _db()
    try:
        total = con.execute("SELECT COUNT(*) FROM trades WHERE exit_ts>=?", (live_ms,)).fetchone()[0]
        rows = con.execute(f"SELECT {_COLS} FROM trades WHERE exit_ts>=? "
                           "ORDER BY exit_ts DESC LIMIT ? OFFSET ?",
                           (live_ms, per_page, (page - 1) * per_page)).fetchall()
    finally:
        con.close()
    return _fmt_trades(rows, notional), total, max(1, (total + per_page - 1) // per_page)


def _write_state_atomic(state: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, STATE_FILE)  # atomic rename — reader never sees a partial file


def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=92, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------- charts ----------
def fig_capital(days, eq, dd, fwd_hours):
    fig, ax = plt.subplots(2, 1, figsize=(8.4, 5.0), sharex=True,
                           gridspec_kw={"height_ratios": [2.3, 1]})
    ax[0].plot(days, eq, color="#16a34a", lw=1.6); ax[0].fill_between(days, eq, 0, color="#16a34a", alpha=0.12)
    ax[0].axhline(0, color="#888", lw=0.6); ax[0].set_ylabel("cum net $")
    ax[0].set_title("Capital — forward paper record (no orders sent)", fontsize=11, loc="left")
    ax[0].grid(alpha=0.25)
    if fwd_hours < 2:
        ax[0].annotate("forward record just started — accumulating…", (0.5, 0.5),
                       xycoords="axes fraction", ha="center", color="#94a3b8", fontsize=11)
    ax[1].fill_between(days, dd, 0, color="#dc2626", alpha=0.30); ax[1].plot(days, dd, color="#dc2626", lw=0.9)
    ax[1].set_ylabel("drawdown $"); ax[1].set_xlabel(f"days forward (live · {fwd_hours}h)")
    ax[1].grid(alpha=0.25)
    fig.tight_layout()
    return _b64(fig)


def fig_butterfly(positions, z_last, cfg):
    ze, zx, zs = cfg.z_entry, cfg.z_exit, cfg.z_stop
    x = np.linspace(-7, 7, 600)
    tent = np.clip(ze - np.abs(x), -(zs - ze), ze - zx)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    # take-profit band: legs are closed when the dislocation reverts into |z| <= z_exit
    ax.axvspan(-zx, zx, color="#16a34a", alpha=0.18, zorder=1)
    for b in (-zx, zx):
        ax.axvline(b, color="#16a34a", ls="--", lw=0.9, zorder=1)
    ax.plot(x, tent, color="#b91c1c", lw=2.4, zorder=2)
    ax.axhline(0, color="#888", lw=0.6)
    for b in (-ze, ze):
        ax.axvline(b, color="#9ca3af", ls=":", lw=0.9)
    for b in (-zs, zs):
        ax.axvline(b, color="#dc2626", ls=":", lw=0.9)
    ax.annotate(f"take-profit |z|≤{zx:g}σ", (0, -(zs - ze) + 0.2), ha="center", va="bottom",
                color="#15803d", fontsize=8)
    zs_held = []
    for c, p in positions.items():
        zc = z_last.get(c, 0.0)
        zs_held.append(zc)
        y = float(np.clip(ze - abs(zc), -(zs - ze), ze - zx))
        col = "#dc2626" if p.side < 0 else "#2563eb"
        ax.scatter([zc], [y], s=70, color=col, edgecolor="white", lw=0.8, zorder=4)
        ax.annotate(c, (zc, y), fontsize=7, xytext=(0, 7), textcoords="offset points", ha="center")
    if zs_held:
        xc = float(np.mean(zs_held))
        ax.axvline(xc, color="#1d4ed8", ls="--", lw=1.1)
        ax.annotate(f"book x≈{xc:+.1f}σ", (xc, ze - zx), fontsize=8, color="#1d4ed8",
                    xytext=(4, -2), textcoords="offset points")
    ax.annotate("PROFIT (gap closes)", (0, ze - zx + 0.15), ha="center", color="#b91c1c", fontsize=8)
    ax.annotate("← short legs", (zs - 0.3, -(zs - ze) + 0.3), ha="right", color="#dc2626", fontsize=7)
    ax.annotate("long legs →", (-zs + 0.3, -(zs - ze) + 0.3), ha="left", color="#2563eb", fontsize=7)
    ax.set_title("Live butterfly — where the book sits on the short-gamma tent", fontsize=11, loc="left")
    ax.set_xlabel("dislocation (σ from the pack)"); ax.set_ylabel("payoff posture")
    ax.grid(alpha=0.25)
    return _b64(fig)


def fig_swarm(z_now, positions, cfg):
    items = sorted(z_now.items(), key=lambda kv: kv[1])
    coins = [c for c, _ in items]; vals = [v for _, v in items]
    y = np.arange(len(coins))
    cols = ["#dc2626" if v > 0 else "#2563eb" for v in vals]
    held = set(positions)
    fig, ax = plt.subplots(figsize=(8.4, 6.2))
    ax.hlines(y, 0, vals, color=cols, lw=2.2, alpha=0.85)
    ax.scatter(vals, y, s=[55 if c in held else 22 for c in coins],
               color=cols, edgecolor=["black" if c in held else "white" for c in coins], lw=0.8, zorder=3)
    for b in (-cfg.z_entry, cfg.z_entry):
        ax.axvline(b, color="#9ca3af", ls="--", lw=1.0)
    for b in (-cfg.z_stop, cfg.z_stop):
        ax.axvline(b, color="#dc2626", ls=":", lw=1.0)
    ax.axvline(0, color="#444", lw=0.7)
    ax.set_yticks(y); ax.set_yticklabels(coins, fontsize=8)
    ax.set_xlabel("z (σ from the pack) — filled dot = position held")
    ax.set_title("Live dislocations — entry ±1.5σ, stop ±5σ", fontsize=11, loc="left")
    ax.grid(alpha=0.2, axis="x")
    return _b64(fig)


def fig_neutral(days, coin_net, gross):
    fig, ax = plt.subplots(figsize=(8.4, 3.0))
    ax.plot(days, coin_net / gross * 100, color="#ef4444", lw=1.0, label="coin-leg tilt (pre-hedge)")
    ax.plot(days, np.zeros_like(days), color="#16a34a", lw=2.0, label="net delta after basket hedge = 0")
    ax.axhline(0, color="#888", lw=0.5)
    ax.set_ylabel("% of gross"); ax.set_xlabel("days")
    ax.set_title("Delta-neutrality monitor", fontsize=11, loc="left")
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.25)
    return _b64(fig)


# ---------- compute ----------
def compute():
    t0 = time.time()
    close_all, tr_all, dv_all = load_local() if SOURCE == "local" else load_live()
    if close_all.shape[1] < 8:
        raise RuntimeError(f"only {close_all.shape[1]} coins from {EXCHANGE}/{SOURCE} — "
                           "venue may be geo-blocked; set EXCHANGE env to okx/kraken/binance.")
    rank = dv_all.median().sort_values(ascending=False)
    coins = list(rank.index[:N_COINS])
    close, tr, dv = close_all[coins], tr_all[coins], dv_all[coins]
    log.info("fetched %d/%d coins (%s) · %d bars · %.1fs", close_all.shape[1], len(COINS),
             ",".join(coins[:6]) + "…", len(close), time.time() - t0)

    res = run_shadow(close, tr, dv, CFG)
    notional = GROSS / len(coins)
    now_iso = pd.Timestamp(t0, unit="s", tz="utc").isoformat()

    # --- persist this cycle's per-bar P&L + closed trades to the durable store, then read back
    #     the FULL accumulated forward record (survives redeploys via the /data volume) ---
    bar_delta = np.diff(np.concatenate([[0.0], res.equity]))          # $ per bar (incl costs)
    pnl_by_ts = {int(res.index[i]): float(bar_delta[i]) for i in range(len(res.index))}
    persist(pnl_by_ts, res.trades, now_iso)
    ts, deltas, all_trades, live_since = load_series()

    # FORWARD-ONLY: headline stats + curve cover only bars AFTER the portal first ran
    # (live_since); the backfilled context that seeds the engine is excluded.
    live_ms = int(pd.Timestamp(live_since).value // 1_000_000) if live_since else (int(ts[0]) if len(ts) else 0)
    fwd = (ts >= live_ms) if len(ts) else np.zeros(0, bool)
    f_ts, deltas_f = (ts[fwd], deltas[fwd]) if len(ts) else (ts, deltas)
    eq = np.cumsum(deltas_f) if len(deltas_f) else np.zeros(1)
    dd = eq - np.maximum.accumulate(eq)
    sharpe = float(deltas_f.mean() / deltas_f.std() * np.sqrt(PPY)) if len(deltas_f) > 1 and deltas_f.std() > 0 else 0.0
    span_ms = (f_ts[-1] - f_ts[0]) if len(f_ts) > 1 else 1
    yrs = max(span_ms / 1000 / 86400 / 365, 1e-9)
    days = (f_ts - f_ts[0]) / 1000 / 86400 if len(f_ts) else np.zeros(1)
    fwd_hours = int(len(f_ts))
    closed = [t for t in all_trades if t[2] >= live_ms]   # (gross_bps, reason, exit_ts)
    wins = [t for t in closed if t[0] > 0]
    dti = pd.to_datetime(res.index, unit="ms", utc=True)
    # neutrality monitor stays a CURRENT-window view from the latest run
    win_sp = res.index >= (res.index[-1] - DAYS * 86400 * 1000)
    nd = res.net_delta[win_sp]
    nd_days = (res.index[win_sp] - res.index[win_sp][0]) / 1000 / 86400

    posn = []
    for c, p in sorted(res.positions.items(), key=lambda kv: -abs(res.z_last[kv[0]])):
        unreal = p.side * (res.resid_last[c] - p.entry_resid) / 1e4 * notional
        posn.append({"coin": c, "side": "SHORT" if p.side < 0 else "LONG",
                     "z": round(res.z_last[c], 2), "entry_z": round(p.entry_z, 2),
                     "alloc": round(notional), "unreal": round(unreal)})
    pos_simple = {c: {"side": p.side} for c, p in res.positions.items()}

    reasons = {}
    for t in closed:
        reasons[t[1]] = reasons.get(t[1], 0) + 1

    state = {
        "updated": dti[-1].isoformat(), "computed_at": now_iso,
        "live_since": live_since, "forward_hours": fwd_hours,
        "source": SOURCE, "exchange": EXCHANGE, "n_coins": len(coins), "coins": coins,
        "gross": GROSS, "window_days": DAYS,
        "net_pnl": round(float(eq[-1])), "pct": round(float(eq[-1] / GROSS * 100), 2),
        "ann_pct": round(float(eq[-1] / GROSS * 100 / yrs)), "sharpe": round(sharpe, 2),
        "maxdd": round(float(dd.min())), "maxdd_pct": round(float(dd.min() / GROSS * 100), 2),
        "win_rate": round(100 * len(wins) / max(len(closed), 1)),
        "n_trades": len(closed), "open_legs": len(res.positions),
        "coin_net": round(float(nd[-1])), "reasons": reasons,
        "positions": posn,
        "closed": load_recent_trades(live_ms, notional),
        "img_capital": fig_capital(days, eq, dd, fwd_hours),
        "img_butterfly": fig_butterfly(res.positions, res.z_last, CFG),
        "img_swarm": fig_swarm(res.z_last, pos_simple, CFG),
        "img_neutral": fig_neutral(nd_days, nd, GROSS),
        "error": None,
    }
    _write_state_atomic(state)
    return state


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return None


if __name__ == "__main__":
    s = compute()
    print(f"computed ok — source={s['source']} coins={s['n_coins']} "
          f"net=${s['net_pnl']:,} ({s['ann_pct']}%/yr) sharpe={s['sharpe']} "
          f"open={s['open_legs']} imgs={[k for k in s if k.startswith('img_')]}")
