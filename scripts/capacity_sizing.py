"""Capacity-realistic sizing study for the reversal basket — what is it worth in DOLLARS?

On top of the honest fills (base + state-dependent range-slippage + carry + 1-bar lag), add TRUE
size-dependent impact per fill: impact_bps = K * sqrt(order_notional / that-bar's-$volume) (square-root
law), charged at entry AND exit, per leg, using each coin's ACTUAL hourly $-volume over 5y.

Sweep gross book size G across legs, for two allocations:
  equal   : every leg gets G/N (thin coins pay heavy impact)
  liq     : legs weighted by each coin's median $-volume (put dollars where the depth is)

Reports Sharpe-at-size, net return %/yr, net $/yr, and max drawdown % as G grows — so we can read
the deployable ceiling and the dollar value, not just a scale-free Sharpe.

    python scripts/capacity_sizing.py
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
K_IMPACT = 100.0    # impact bps = K*sqrt(participation); 1% participation -> 10bps/side
K_VOL = 0.10
CARRY = 20.0
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA", "NEAR"]
SIZES = [10_000, 30_000, 100_000, 300_000, 1_000_000, 3_000_000, 10_000_000]


def load():
    close, tr, dvol = {}, {}, {}
    for n in COINS:
        df = pd.read_parquet(HIST / f"long_{n}.parquet").sort_values("ts")
        ts = df["ts"].to_numpy()
        close[n] = pd.Series(df["close"].to_numpy(), index=ts)
        tr[n] = pd.Series(((df["high"] - df["low"]) / df["close"] * 1e4).to_numpy(), index=ts)
        dvol[n] = pd.Series((df["close"] * df["volume"]).to_numpy(), index=ts)
    close = pd.DataFrame(close).dropna()
    lp = np.log(close)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    TR = pd.DataFrame(tr).reindex(resid.index)
    DV = pd.DataFrame(dvol).reindex(resid.index)
    DV = DV.fillna(DV.median())
    return resid, z, TR, DV


def book_dollars(resid, z, TR, DV, w):
    """w: dict coin->leg notional$. Returns (book$ per bar, mean participation%)."""
    n = len(resid)
    carry_bar = CARRY / 100 * 1e4 / PPY
    out = np.zeros(n)
    parts = []
    for a in resid.columns:
        wa = w[a]
        dv = DV[a].to_numpy()
        part = np.clip(np.where(dv > 0, wa / dv, 1.0), 0, 1.0)
        impact = K_IMPACT * np.sqrt(part)                       # bps per side
        hc = (BASE + K_VOL * np.nan_to_num(TR[a].to_numpy())) / 2 + impact
        sp, _ = run_axis(resid[a].to_numpy(), z[a].to_numpy(), hc, carry_bar, lag=1)
        out += sp * wa / 1e4                                    # bps -> dollars
        parts.append(np.median(part) * 100)
    return out, float(np.mean(parts))


def stats(bookd, G, yrs):
    mu, sd = bookd.mean(), bookd.std()
    sharpe = mu / sd * np.sqrt(PPY) if sd > 0 else 0.0
    eq = np.cumsum(bookd)
    maxdd = (eq - np.maximum.accumulate(eq)).min()
    ann = bookd.sum() / yrs
    return sharpe, ann / G * 100, ann, maxdd / G * 100


def main():
    resid, z, TR, DV = load()
    na = resid.shape[1]
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    meddv = DV.median()
    print(f"{na} alts, {yrs:.1f}y. impact=K*sqrt(part), K={K_IMPACT:.0f} (1% vol->10bps/side). "
          f"k_vol={K_VOL}, carry={CARRY:.0f}%/yr, lag=1.")
    print(f"median hourly $-vol per coin: min ${meddv.min()/1e6:.1f}M (thinnest) .. "
          f"max ${meddv.max()/1e6:.0f}M (BTC/ETH).\n")

    liqw = (meddv / meddv.sum()).to_dict()
    curves = {}
    for wname in ["equal", "liq"]:
        print(f"=== {wname}-weighted ===")
        print(f"  {'gross$':>10s} {'$/leg':>9s} {'medPart%':>9s} | {'Sharpe':>7s} "
              f"{'ret%/yr':>8s} {'net$/yr':>11s} {'maxDD%':>7s}")
        rows = []
        for G in SIZES:
            w = {c: G / na for c in COINS} if wname == "equal" else {c: liqw[c] * G for c in COINS}
            bookd, mp = book_dollars(resid, z, TR, DV, w)
            sh, ret, nety, dd = stats(bookd, G, yrs)
            legmin = min(w.values()); legmax = max(w.values())
            legstr = f"{legmin/1e3:.0f}-{legmax/1e3:.0f}k" if wname == "liq" else f"{G/na/1e3:.0f}k"
            print(f"  {G:10,.0f} {legstr:>9s} {mp:9.2f} | {sh:7.2f} {ret:8.1f} "
                  f"{nety:11,.0f} {dd:7.1f}")
            rows.append((G, sh, nety))
        curves[wname] = rows
        print()

    # plot: Sharpe vs size, and net$/yr vs size
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.5))
    for wname, rows in curves.items():
        Gs = [r[0] for r in rows]
        axs[0].plot(Gs, [r[1] for r in rows], "o-", label=wname)
        axs[1].plot(Gs, [r[2] for r in rows], "o-", label=wname)
    axs[0].axhline(1.5, color="green", ls=":", label="Sharpe 1.5 gate")
    axs[0].set_xscale("log"); axs[0].set_title("Sharpe vs gross book size"); axs[0].set_xlabel("gross $")
    axs[0].set_ylabel("annualized Sharpe"); axs[0].legend(); axs[0].grid(alpha=0.3)
    axs[1].set_xscale("log"); axs[1].set_title("Net $/yr vs gross book size (the dollar value)")
    axs[1].set_xlabel("gross $"); axs[1].set_ylabel("net $/yr"); axs[1].legend(); axs[1].grid(alpha=0.3)
    fig.suptitle("Capacity-realistic sizing — where impact eats the edge", fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "capacity_sizing.png"
    fig.savefig(path, dpi=110)
    print(f"saved {path}")
    print("Read: deployable ceiling ~ where Sharpe falls through ~2-3; net$/yr rises then flattens/falls "
          "as impact wins. liq-weighting should push the ceiling higher (dollars follow depth).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
