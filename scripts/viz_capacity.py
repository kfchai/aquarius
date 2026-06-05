"""Dashboard for the capacity + breadth study (findings-13). One figure, six panels:
  A Sharpe vs gross size, by basket config
  B Net $/yr vs gross size (log) — the dollar value
  C Sharpe-vs-capacity FRONTIER (Sharpe vs net$/yr, points = sizes)
  D Max drawdown % vs gross size
  E Diversification win: Sharpe & maxDD at $100k, by breadth
  F Equity curve of the recommended small-capital config (wide equal-weight @ $100k)

    python scripts/viz_capacity.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.breadth_capacity import (  # noqa: E402
    all_coins, series, residualize, book_dollars, stats,
)

SIZES = [100_000, 300_000, 1_000_000, 3_000_000, 10_000_000, 30_000_000]
CFGS = ["top-10", "top-20", "top-35", "top-35-liq"]
COL = {"top-10": "#1f77b4", "top-20": "#ff7f0e", "top-35": "#2ca02c", "top-35-liq": "#d62728"}


def prep(close_all, tr_all, dv_all, ordered, cfg):
    if cfg == "top-35-liq":
        sel = ordered
    else:
        sel = ordered[: int(cfg.split("-")[1])]
    resid, z = residualize(close_all[sel])
    TR = tr_all.reindex(resid.index)[sel]
    DV = dv_all.reindex(resid.index)[sel].fillna(dv_all[sel].median())
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    medv = dv_all[sel].median()
    lw = (medv / medv.sum()).to_dict()
    return resid, z, TR, DV, yrs, sel, lw


def weight(cfg, sel, lw, G):
    if cfg == "top-35-liq":
        return {c: lw[c] * G for c in sel}
    return G / len(sel)


def main():
    coins = all_coins()
    close_all, tr_all, dv_all = series(coins)
    ordered = list(dv_all.median().sort_values(ascending=False).index)

    data = {}          # cfg -> list of (G, sharpe, net$, maxdd%)
    eq_reco = None
    for cfg in CFGS:
        resid, z, TR, DV, yrs, sel, lw = prep(close_all, tr_all, dv_all, ordered, cfg)
        rows = []
        for G in SIZES:
            w = weight(cfg, sel, lw, G)
            bookd = book_dollars(resid, z, TR, DV, w)
            sh, ret, nety, dd = stats(bookd, G, yrs)
            rows.append((G, sh, nety, dd))
            if cfg == "top-35" and G == 100_000:
                eq_reco = (np.cumsum(bookd), resid.index)
        data[cfg] = rows

    fig, axs = plt.subplots(2, 3, figsize=(19, 11))

    # A Sharpe vs size
    ax = axs[0, 0]
    for cfg in CFGS:
        ax.plot(SIZES, [r[1] for r in data[cfg]], "o-", color=COL[cfg], label=cfg)
    ax.axhline(1.5, color="gray", ls=":", label="Sharpe 1.5 gate")
    ax.set_xscale("log"); ax.set_title("A · Sharpe vs gross book size", fontsize=11)
    ax.set_xlabel("gross $"); ax.set_ylabel("annualized Sharpe"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # B Net $/yr vs size
    ax = axs[0, 1]
    for cfg in CFGS:
        ax.plot(SIZES, [max(r[2], 1) for r in data[cfg]], "o-", color=COL[cfg], label=cfg)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_title("B · Net $/yr vs gross size (the dollar value)", fontsize=11)
    ax.set_xlabel("gross $"); ax.set_ylabel("net $/yr"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # C frontier: Sharpe vs net$
    ax = axs[0, 2]
    for cfg in CFGS:
        xs = [r[2] for r in data[cfg]]; ys = [r[1] for r in data[cfg]]
        ax.plot(xs, ys, "o-", color=COL[cfg], label=cfg)
    # annotate sizes on the liq line
    for G, sh, nety, dd in data["top-35-liq"]:
        if nety > 0:
            ax.annotate(f"${G/1e6:.1f}M", (nety, sh), fontsize=7, color=COL["top-35-liq"],
                        xytext=(3, 3), textcoords="offset points")
    ax.axhline(1.5, color="gray", ls=":")
    ax.set_xscale("log"); ax.set_title("C · Frontier: Sharpe vs net $/yr", fontsize=11)
    ax.set_xlabel("net $/yr"); ax.set_ylabel("Sharpe"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # D maxDD vs size
    ax = axs[1, 0]
    for cfg in CFGS:
        ax.plot(SIZES, [r[3] for r in data[cfg]], "o-", color=COL[cfg], label=cfg)
    ax.axhline(-10, color="red", ls=":", label="-10% gate")
    ax.set_xscale("log"); ax.set_title("D · Max drawdown % vs gross size", fontsize=11)
    ax.set_xlabel("gross $"); ax.set_ylabel("max drawdown %"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # E diversification win at $100k
    ax = axs[1, 1]
    tiers = ["top-10", "top-20", "top-35"]
    shp = [data[c][0][1] for c in tiers]
    ddp = [abs(data[c][0][3]) for c in tiers]
    x = np.arange(len(tiers)); w = 0.38
    ax.bar(x - w/2, shp, w, color="steelblue", label="Sharpe")
    ax.bar(x + w/2, ddp, w, color="indianred", label="|maxDD| %")
    ax.set_xticks(x); ax.set_xticklabels(tiers)
    ax.set_title("E · Diversification win at $100k (more legs)", fontsize=11)
    ax.set_ylabel("value"); ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
    for i, (s, d) in enumerate(zip(shp, ddp)):
        ax.text(i - w/2, s + 0.1, f"{s:.1f}", ha="center", fontsize=8)
        ax.text(i + w/2, d + 0.1, f"{d:.1f}", ha="center", fontsize=8)

    # F recommended config equity curve
    ax = axs[1, 2]
    eq, idx = eq_reco
    days = (idx.to_numpy() - idx[0]) / 1000 / 86400
    ax.plot(days, eq, color="#2ca02c", lw=1.3)
    ax.fill_between(days, eq, 0, color="#2ca02c", alpha=0.12)
    tot = eq[-1]; yrs = days[-1] / 365
    ax.set_title(f"F · Recommended: wide(35) equal-wt @ $100k\n"
                 f"net ${tot:,.0f} over {yrs:.1f}y (~${tot/yrs:,.0f}/yr, Sharpe "
                 f"{data['top-35'][0][1]:.1f})", fontsize=10)
    ax.set_xlabel("days"); ax.set_ylabel("cum net $"); ax.grid(alpha=0.3)

    fig.suptitle("Capacity & breadth dashboard — reversal basket (3y, honest fills + true sqrt-impact)",
                 fontsize=14)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "capacity_dashboard.png"
    fig.savefig(path, dpi=108)
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
