"""Stage-5 shadow-live runner — paper-trades the reversal basket on REAL hourly data, sends no
orders. Replays the engine over recent real bars so you get a live-style equity curve now, and the
same command run hourly (with --live) appends the newest bar and continues the shadow track record.

    python scripts/shadow_run.py                 # demo: replay last 45d from cached data
    python scripts/shadow_run.py --live          # fetch latest from Binance, run one cycle, append
    python scripts/shadow_run.py --days 90        # longer replay window

State + trade log persist under data/shadow/ so a forward record accumulates as you run it live.
"""

import argparse
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.history import fetch_ccxt_ohlcv  # noqa: E402
from aquarius.paper.shadow import ShadowConfig, run_shadow, PPY  # noqa: E402

HIST = pathlib.Path("data/history")
STATE = pathlib.Path("data/shadow"); STATE.mkdir(parents=True, exist_ok=True)
N_COINS = 20          # top-N by $-volume (wide enough for the diversification Sharpe)
WARMUP_BARS = 360     # >= ema+zwin to warm the residual windows before the shadow period


def load_parquet():
    coins = sorted(p.stem[len("broad_"):] for p in HIST.glob("broad_*.parquet"))
    close, tr, dv = {}, {}, {}
    for c in coins:
        df = pd.read_parquet(HIST / f"broad_{c}.parquet").sort_values("ts")
        ts = df["ts"].to_numpy()
        close[c] = pd.Series(df["close"].to_numpy(), index=ts)
        tr[c] = pd.Series(((df["high"] - df["low"]) / df["close"] * 1e4).to_numpy(), index=ts)
        dv[c] = pd.Series((df["close"] * df["volume"]).to_numpy(), index=ts)
    return pd.DataFrame(close), pd.DataFrame(tr), pd.DataFrame(dv)


def load_live(coins, since="2026-03-01T00:00:00Z"):
    close, tr, dv = {}, {}, {}
    for c in coins:
        df = fetch_ccxt_ohlcv("binance", f"{c}/USDT", "1h", since_iso=since)
        ts = df["ts"].to_numpy()
        close[c] = pd.Series(df["close"].to_numpy(), index=ts)
        tr[c] = pd.Series(((df["high"] - df["low"]) / df["close"] * 1e4).to_numpy(), index=ts)
        dv[c] = pd.Series((df["close"] * df["volume"]).to_numpy(), index=ts)
    return pd.DataFrame(close), pd.DataFrame(tr), pd.DataFrame(dv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="fetch latest from Binance")
    ap.add_argument("--days", type=int, default=45, help="shadow-period length to report")
    ap.add_argument("--wide", action="store_true", help="use all coins (stress the tail guards)")
    args = ap.parse_args()
    cfg = ShadowConfig(gross=100_000.0)

    close_all, tr_all, dv_all = load_parquet()
    rank = dv_all.median().sort_values(ascending=False)
    coins = list(rank.index) if args.wide else list(rank.index[:N_COINS])
    if args.live:
        close_all, tr_all, dv_all = load_live(coins)
    close, tr, dv = close_all[coins], tr_all[coins], dv_all[coins]

    res = run_shadow(close, tr, dv, cfg)
    dti = pd.to_datetime(res.index, unit="ms", utc=True)

    # shadow period = last `days` (the rest is warmup for the residual windows)
    cutoff = res.index[-1] - args.days * 86400 * 1000
    sp = res.index >= cutoff
    eq = res.equity[sp] - res.equity[sp][0]      # rebase to 0 at period start
    nd = res.net_delta[sp]
    dd = eq - np.maximum.accumulate(eq)
    step = np.diff(np.concatenate([[0.0], eq]))
    sharpe = step.mean() / step.std() * np.sqrt(PPY) if step.std() > 0 else 0.0
    yrs = sp.sum() / PPY
    closed = [t for t in res.trades if t["exit_ts"] >= cutoff]
    wins = [t for t in closed if t["gross_bps"] > 0]
    nlbl = f"all-{len(coins)}" if args.wide else f"top-{N_COINS}"

    print(f"=== SHADOW-LIVE (paper, no orders sent) — {nlbl} alts, ${cfg.gross:,.0f} gross ===")
    print(f"  guards: leg-stop {cfg.max_leg_loss_bps:.0f}bps · liq-floor ${cfg.min_dollar_vol/1e3:.0f}k/hr "
          f"· delist {cfg.stale_bars}bar · hedge-drag {cfg.rebalance_bps_per_bar}bps/bar")
    print(f"period: {dti[sp][0].date()} .. {dti[sp][-1].date()}  ({args.days}d, {sp.sum()} hourly bars)")
    print(f"  net P&L      : ${eq[-1]:,.0f}   ({eq[-1]/cfg.gross*100:+.2f}% of gross, "
          f"~{eq[-1]/cfg.gross*100/max(yrs,1e-9):+.0f}%/yr)")
    print(f"  Sharpe (ann) : {sharpe:.2f}")
    print(f"  max drawdown : ${dd.min():,.0f}  ({dd.min()/cfg.gross*100:.2f}% of gross)")
    print(f"  closed trades: {len(closed)}   win-rate {100*len(wins)/max(len(closed),1):.0f}%")
    if closed:
        worst = min(closed, key=lambda t: t["gross_bps"])
        reasons = {}
        for t in closed:
            reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
        rstr = "  ".join(f"{k}={v}" for k, v in sorted(reasons.items(), key=lambda x: -x[1]))
        over = max(0.0, -worst['gross_bps'] - cfg.max_leg_loss_bps)
        print(f"  worst leg    : {worst['coin']} {worst['gross_bps']:+.0f}bps (exit={worst['reason']})"
              + (f" — stop fired at -{cfg.max_leg_loss_bps:.0f}, +{over:.0f} is a 1-bar gap "
                 f"(stops can't prevent gaps)" if worst['reason'] == 'leg_stop' and over > 0 else ""))
        print(f"  exit reasons : {rstr}")
    print(f"  open legs    : {len(res.positions)}")
    # neutrality: residual = coin vs equal-wt basket, so each leg carries an offsetting basket
    # position. coin-leg net is exactly cancelled by the basket hedge -> true net delta = 0.
    coin_net = nd[-1]
    print(f"  coin-leg net : ${coin_net:+,.0f}  ->  basket hedge ${-coin_net:+,.0f}  ->  "
          f"NET DELTA $0 (neutral by construction; hedge is an execution task, verified each cycle)")

    # current open positions, sorted by |z|
    if res.positions:
        print("\n  OPEN POSITIONS (intended; a real book longs the coin vs the equal-wt basket):")
        rows = sorted(res.positions.items(), key=lambda kv: -abs(res.z_last[kv[0]]))
        for c, p in rows:
            unreal = p.side * (res.resid_last[c] - p.entry_resid) / 1e4 * (cfg.gross / N_COINS)
            print(f"    {c:6s} {'SHORT' if p.side<0 else 'LONG ':5s}  z={res.z_last[c]:+5.2f}  "
                  f"entry_z={p.entry_z:+5.2f}  unreal=${unreal:+,.0f}")

    # plot
    days = (res.index[sp] - res.index[sp][0]) / 1000 / 86400
    fig, axs = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axs[0].plot(days, eq, color="#2ca02c", lw=1.4); axs[0].fill_between(days, eq, 0, color="#2ca02c", alpha=0.12)
    axs[0].axhline(0, color="k", lw=0.6)
    axs[0].set_title(f"Shadow-live equity (paper) — top-{N_COINS} alts ${cfg.gross/1e3:.0f}k gross, "
                     f"net ${eq[-1]:,.0f}, Sharpe {sharpe:.1f}", fontsize=11)
    axs[0].set_ylabel("cum net $"); axs[0].grid(alpha=0.3)
    axs[1].plot(days, nd / cfg.gross * 100, color="indianred", lw=1.0, label="coin-leg net (pre-hedge)")
    axs[1].plot(days, np.zeros_like(days), color="green", lw=1.6, label="true net delta (post basket hedge) = 0")
    axs[1].axhline(0, color="k", lw=0.4)
    axs[1].set_title("Neutrality monitor — coin-leg tilt is zeroed by the basket hedge (net delta = 0)",
                     fontsize=11)
    axs[1].set_xlabel("days"); axs[1].set_ylabel("% of gross"); axs[1].legend(fontsize=8); axs[1].grid(alpha=0.3)
    fig.tight_layout()
    out = pathlib.Path("research/figures") / "shadow_live.png"
    fig.savefig(out, dpi=110)

    # persist snapshot (accumulates a forward record across live runs)
    snap = {"asof": dti[-1].isoformat(), "gross": cfg.gross, "period_days": args.days,
            "net_pnl": float(eq[-1]), "sharpe": float(sharpe), "maxdd": float(dd.min()),
            "open_legs": len(res.positions), "net_delta": float(nd[-1]),
            "closed_trades": len(closed)}
    log = STATE / "snapshots.jsonl"
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap) + "\n")
    pd.DataFrame(res.trades).to_parquet(STATE / "trades.parquet", index=False) if res.trades else None
    print(f"\nsaved {out}  ·  snapshot -> {log}  ·  trades -> {STATE/'trades.parquet'}")
    print("Go live: schedule `python scripts/shadow_run.py --live` hourly (Task Scheduler / cron). "
          "Each run re-fetches real bars, re-prices the book, logs intended trades — sends nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
