"""Test the 'many tiny legs' thesis: does widening the basket (more coins) raise BOTH Sharpe
(diversification) AND capacity (smaller per-leg orders -> lower sqrt-impact)?

Tiers = top-N coins by median $-volume from the broad 35-coin set (nested: top10 c top20 c top35).
Equal-weight, full honest fills + true size-impact, swept across gross book size. Window 2023-06..
2026-06 (~3y, no 2022 crisis) — so absolute Sharpe differs from the 5y run; the RELATIVE move across
N is the point.

    python scripts/breadth_capacity.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.honest_fill import run_axis, BASE, PPY  # noqa: E402

HIST = pathlib.Path("data/history")
EMA, ZWIN = 168, 168
K_IMPACT, K_VOL, CARRY = 100.0, 0.10, 20.0
SIZES = [100_000, 300_000, 1_000_000, 3_000_000, 10_000_000, 30_000_000]
TIERS = [10, 20, 35]


def all_coins():
    return sorted(p.stem[len("broad_"):] for p in HIST.glob("broad_*.parquet"))


def series(coins):
    close, tr, dvol = {}, {}, {}
    for n in coins:
        df = pd.read_parquet(HIST / f"broad_{n}.parquet").sort_values("ts")
        ts = df["ts"].to_numpy()
        close[n] = pd.Series(df["close"].to_numpy(), index=ts)
        tr[n] = pd.Series(((df["high"] - df["low"]) / df["close"] * 1e4).to_numpy(), index=ts)
        dvol[n] = pd.Series((df["close"] * df["volume"]).to_numpy(), index=ts)
    return (pd.DataFrame(close), pd.DataFrame(tr), pd.DataFrame(dvol))


def residualize(close):
    close = close.dropna()
    lp = np.log(close)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    return resid, z


def book_dollars(resid, z, TR, DV, w):
    """w: scalar (equal $/leg) or dict coin->$/leg (liquidity-weighted)."""
    n = len(resid)
    carry_bar = CARRY / 100 * 1e4 / PPY
    out = np.zeros(n)
    for a in resid.columns:
        wa = w[a] if isinstance(w, dict) else w
        dv = DV[a].to_numpy()
        part = np.clip(np.nan_to_num(wa / np.where(dv > 0, dv, np.nan), nan=1.0), 0, 1.0)
        hc = (BASE + K_VOL * np.nan_to_num(TR[a].to_numpy())) / 2 + K_IMPACT * np.sqrt(part)
        sp, _ = run_axis(resid[a].to_numpy(), z[a].to_numpy(), hc, carry_bar, lag=1)
        out += sp * wa / 1e4
    return out


def stats(bookd, G, yrs):
    mu, sd = bookd.mean(), bookd.std()
    sh = mu / sd * np.sqrt(PPY) if sd > 0 else 0.0
    eq = np.cumsum(bookd)
    dd = (eq - np.maximum.accumulate(eq)).min()
    return sh, bookd.sum() / yrs / G * 100, bookd.sum() / yrs, dd / G * 100


def main():
    coins = all_coins()
    close_all, tr_all, dv_all = series(coins)
    rank = dv_all.median().sort_values(ascending=False)
    ordered = list(rank.index)
    print(f"{len(coins)} coins, window {pd.to_datetime(close_all.index[0], unit='ms').date()}.."
          f"{pd.to_datetime(close_all.index[-1], unit='ms').date()}. equal-weight, K={K_IMPACT:.0f}.")
    print(f"liquidity rank (median $-vol M): "
          + ", ".join(f"{c}={rank[c]/1e6:.0f}" for c in ordered[:6]) + " ... "
          + ", ".join(f"{c}={rank[c]/1e6:.1f}" for c in ordered[-3:]) + "\n")

    curves = {}
    for N in TIERS:
        sel = ordered[:N]
        resid, z = residualize(close_all[sel])
        TR = tr_all.reindex(resid.index)[sel]
        DV = dv_all.reindex(resid.index)[sel].fillna(dv_all[sel].median())
        yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
        print(f"=== top-{N} legs ({yrs:.1f}y) ===")
        print(f"  {'gross$':>11s} {'$/leg':>8s} | {'Sharpe':>7s} {'ret%/yr':>8s} "
              f"{'net$/yr':>12s} {'maxDD%':>7s}")
        rows = []
        for G in SIZES:
            gleg = G / N
            bookd = book_dollars(resid, z, TR, DV, gleg)
            sh, ret, nety, dd = stats(bookd, G, yrs)
            print(f"  {G:11,.0f} {gleg/1e3:7.0f}k | {sh:7.2f} {ret:8.1f} {nety:12,.0f} {dd:7.1f}")
            rows.append((G, sh, nety))
        curves[N] = rows
        print()

    # the combination: wide universe (35) BUT liquidity-weighted (dollars follow depth)
    resid, z = residualize(close_all[ordered])
    TR = tr_all.reindex(resid.index)[ordered]
    DV = dv_all.reindex(resid.index)[ordered].fillna(dv_all[ordered].median())
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    medv = dv_all[ordered].median()
    lw = (medv / medv.sum()).to_dict()
    print("=== top-35 legs, LIQUIDITY-weighted (breadth + depth-proportional sizing) ===")
    print(f"  {'gross$':>11s} {'$/leg rng':>12s} | {'Sharpe':>7s} {'ret%/yr':>8s} "
          f"{'net$/yr':>12s} {'maxDD%':>7s}")
    rows = []
    for G in SIZES:
        w = {c: lw[c] * G for c in ordered}
        bookd = book_dollars(resid, z, TR, DV, w)
        sh, ret, nety, dd = stats(bookd, G, yrs)
        lo, hi = min(w.values()), max(w.values())
        print(f"  {G:11,.0f} {lo/1e3:.0f}-{hi/1e3:.0f}k | {sh:7.2f} {ret:8.1f} {nety:12,.0f} {dd:7.1f}")
        rows.append((G, sh, nety))
    curves["35-liq"] = rows
    print()

    fig, axs = plt.subplots(1, 2, figsize=(15, 5.5))
    for N, rows in curves.items():
        Gs = [r[0] for r in rows]
        axs[0].plot(Gs, [r[1] for r in rows], "o-", label=f"top-{N}")
        axs[1].plot(Gs, [r[2] for r in rows], "o-", label=f"top-{N}")
    axs[0].axhline(1.5, color="green", ls=":", label="Sharpe 1.5")
    axs[0].set_xscale("log"); axs[0].set_title("Sharpe vs size, by basket breadth")
    axs[0].set_xlabel("gross $"); axs[0].set_ylabel("Sharpe"); axs[0].legend(); axs[0].grid(alpha=0.3)
    axs[1].set_xscale("log"); axs[1].set_yscale("log")
    axs[1].set_title("Net $/yr vs size, by basket breadth")
    axs[1].set_xlabel("gross $"); axs[1].set_ylabel("net $/yr"); axs[1].legend(); axs[1].grid(alpha=0.3)
    fig.suptitle("Many tiny legs: does breadth raise Sharpe AND capacity?", fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "breadth_capacity.png"
    fig.savefig(path, dpi=110)
    print(f"saved {path}")
    print("Read: if top-35 holds higher Sharpe at large G and a higher net$/yr ceiling than top-10, "
          "'many tiny legs' raises capacity. Compare same-G rows across tiers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
