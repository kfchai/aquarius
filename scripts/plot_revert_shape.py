"""Visualize the SHAPE of the mean-reversion (short-gamma) basket — the mirror of the
long-gamma butterfly — from the real alt cross-sectional residual trades.

Panels:
  (a) Payoff vs dislocation: the short-gamma TENT (this strategy) overlaid on the
      long-gamma butterfly (old idea). Same axes -> the mirror is the whole point.
  (b) The residual z-swarm over time (all axes) with entry (+/-z_entry) & stop (+/-z_stop)
      bands — what "dislocations" actually look like.
  (c) Per-trade net P&L histogram — the NEGATIVE SKEW (many small wins, few big losses).
  (d) Realized payoff: each trade's EXIT z vs its net P&L — empirical proof the shape is
      a tent (win near the centre, capped losses out in the wings / stops).

    python scripts/plot_revert_shape.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import MRParams, run_convergence  # noqa: E402

HIST = pathlib.Path("data/history")
EMA, ZWIN = 168, 168
ZE, ZX, ZS = 1.5, 0.3, 5.0   # entry / exit / stop in sigma
ALTS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK",
        "LTC", "ADA", "SUI", "NEAR", "APT", "ARB", "OP"]


def load_resid():
    s = {}
    for n in ALTS:
        f = HIST / f"spot_{n}.parquet"
        if f.exists():
            df = pd.read_parquet(f).sort_values("ts")
            s[n] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    prices = pd.DataFrame(s).dropna()
    lp = np.log(prices)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    return resid, z


def main():
    resid, z = load_resid()
    mrp = MRParams(lookback=ZWIN, z_entry=ZE, z_exit=ZX, z_stop=ZS)
    trades = []
    for a in resid.columns:
        za = z[a].to_numpy()
        tr, _ = run_convergence(resid[a].to_numpy(), za, mrp, 20.0)  # 20bps realistic cost
        for t in tr:
            t["exit_z"] = za[t["exit_i"]]
            t["entry_z"] = za[t["entry_i"]]
            trades.append(t)
    T = pd.DataFrame(trades)
    net = T["net_bps"].to_numpy()

    fig, axs = plt.subplots(2, 2, figsize=(15, 10))

    # (a) the two shapes, same axes — mirror image
    ax = axs[0, 0]
    x = np.linspace(-7, 7, 600)
    tent = np.clip(ZE - np.abs(x), -(ZS - ZE), ZE - ZX)       # short-gamma: this strategy
    fly = np.clip(np.abs(x) - ZE, 0, None)                    # long-gamma: old butterfly
    fly = np.where(np.abs(x) > ZE, np.minimum(fly, ZS - ZE), -0.3)
    ax.plot(x, tent, lw=2.5, color="crimson", label="THIS basket — mean-reversion (short-gamma)")
    ax.plot(x, fly, lw=2.0, color="seagreen", ls="--", label="old butterfly (long-gamma)")
    ax.axhline(0, color="k", lw=0.7)
    for b in (-ZE, ZE):
        ax.axvline(b, color="gray", ls=":", lw=0.8)
    for b in (-ZS, ZS):
        ax.axvline(b, color="firebrick", ls=":", lw=0.8)
    ax.annotate("PROFIT here\n(gap closes)", (0, ZE - ZX), (0, 2.2),
                ha="center", color="crimson", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="crimson"))
    ax.annotate("BLEED in the wings\n(gap widens) — capped at the STOP", (ZS, -(ZS - ZE)),
                (1.0, -4.5), ha="center", color="firebrick", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="firebrick"))
    ax.set_title("(a) Payoff SHAPE vs dislocation — the mirror of the butterfly", fontsize=11)
    ax.set_xlabel("dislocation (sigma from the pack)"); ax.set_ylabel("payoff")
    ax.legend(fontsize=8, loc="lower center"); ax.grid(alpha=0.25)

    # (b) residual z swarm
    ax = axs[0, 1]
    t0 = z.index[0]
    days = (z.index.to_numpy() - t0) / 1000 / 86400
    for a in z.columns:
        ax.plot(days, z[a].to_numpy(), lw=0.4, alpha=0.5)
    for b in (-ZE, ZE):
        ax.axhline(b, color="gray", ls="--", lw=1.0)
    for b in (-ZS, ZS):
        ax.axhline(b, color="firebrick", ls="--", lw=1.0)
    ax.set_ylim(-7, 7)
    ax.set_title(f"(b) The residual swarm — {len(z.columns)} alts, dislocations both ways",
                 fontsize=11)
    ax.set_xlabel("days"); ax.set_ylabel("z (sigma from the pack)")
    ax.text(days[-1] * 0.5, ZE + 0.2, "entry band +/-1.5", color="gray", fontsize=8)
    ax.text(days[-1] * 0.5, ZS + 0.2, "stop band +/-5", color="firebrick", fontsize=8)

    # (c) per-trade net P&L — negative skew
    ax = axs[1, 0]
    ax.hist(net, bins=60, color="steelblue", edgecolor="white")
    ax.axvline(0, color="k", lw=0.8)
    ax.axvline(net.mean(), color="green", lw=1.5, label=f"mean {net.mean():+.0f} bps")
    ax.axvline(np.median(net), color="orange", lw=1.5, label=f"median {np.median(net):+.0f} bps")
    ax.axvline(net.min(), color="red", lw=1.2, label=f"worst {net.min():+.0f} bps")
    sk = pd.Series(net).skew()
    ax.set_title(f"(c) Per-trade net P&L ({len(net)} trades) — skew={sk:+.2f} "
                 f"(many small wins, few big losses)", fontsize=11)
    ax.set_xlabel("net bps per trade"); ax.set_ylabel("count")
    ax.legend(fontsize=8)

    # (d) realized payoff: exit z vs net P&L
    ax = axs[1, 1]
    stp = T["stopped"].to_numpy().astype(bool)
    ax.scatter(T["exit_z"][~stp], net[~stp], s=8, alpha=0.4, color="seagreen", label="converged (win)")
    ax.scatter(T["exit_z"][stp], net[stp], s=10, alpha=0.5, color="firebrick", label="stopped (loss)")
    ax.axhline(0, color="k", lw=0.7); ax.axvline(0, color="k", lw=0.7)
    ax.set_title("(d) Realized payoff: where it EXITED vs P&L — win at centre, lose in wings",
                 fontsize=11)
    ax.set_xlabel("exit z (sigma from the pack)"); ax.set_ylabel("net bps")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    fig.suptitle("Mean-reversion basket — SHORT-GAMMA tent (inverse of the long-gamma butterfly)",
                 fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "revert_shape.png"
    fig.savefig(path, dpi=110)
    print(f"saved {path}")
    print(f"trades={len(net)}  mean={net.mean():+.1f}bps  median={np.median(net):+.1f}bps  "
          f"worst={net.min():+.0f}bps  win%={(net>0).mean()*100:.0f}  skew={sk:+.2f}")
    print(f"stopped trades={stp.sum()} ({stp.mean()*100:.0f}%)  "
          f"avg stopped loss={net[stp].mean():+.0f}bps  avg win={net[net>0].mean():+.0f}bps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
