"""Crisis-test the wide basket: does breadth + vol-scaling survive LUNA/3AC/FTX?

Breadth was only tested on the no-crisis 3y window; vol-scaling was crisis-tested on 11 coins.
This runs the WIDE basket (all long_ coins, ~30, 5y back to 2021) through the real cascades, both
equal-weight and vol-scaled, with per-crisis and per-year isolation.

    python scripts/crisis_breadth_test.py
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
EMA, ZWIN, PPY = 168, 168, 24 * 365
GROSS, COST = 100_000.0, 20.0
CRISES = [("LUNA", "2022-05-07", "2022-05-16"), ("3AC", "2022-06-12", "2022-06-19"),
          ("FTX", "2022-11-07", "2022-11-21"), ("Aug-24", "2024-08-04", "2024-08-07")]


def load():
    coins = sorted(p.stem[len("long_"):] for p in HIST.glob("long_*.parquet"))
    s = {}
    for n in coins:
        df = pd.read_parquet(HIST / f"long_{n}.parquet").sort_values("ts")
        s[n] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    close = pd.DataFrame(s).dropna()
    lp = np.log(close)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    return resid, z


def run(resid, z, scheme):
    n, N = len(resid), resid.shape[1]
    base = GROSS / N
    mrp = MRParams(lookback=ZWIN, z_entry=1.5, z_exit=0.3, z_stop=5.0)
    vols = {a: pd.Series(np.diff(resid[a].to_numpy(), prepend=resid[a].to_numpy()[0]))
            .rolling(168, min_periods=24).std().shift(1).to_numpy() for a in resid.columns}
    vbar = float(np.nanmedian(np.concatenate([v[np.isfinite(v)] for v in vols.values()])))
    book = np.zeros(n)
    for a in resid.columns:
        ra = resid[a].to_numpy()
        trades, step = run_convergence(ra, z[a].to_numpy(), mrp, COST)
        va = vols[a]; notion = np.zeros(n)
        for t in trades:
            i0 = t["entry_i"]
            if scheme == "equal":
                w = base
            else:
                vv = va[i0] if (i0 < n and np.isfinite(va[i0]) and va[i0] > 0) else vbar
                w = base * float(np.clip(vbar / vv, 1 / 3, 3.0))
            notion[i0:t["exit_i"] + 1] = w
        book += step * notion / 1e4
    return book


def main():
    resid, z = load()
    N = resid.shape[1]
    dti = pd.to_datetime(resid.index, unit="ms", utc=True)
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    days = (resid.index.to_numpy() - resid.index[0]) / 1000 / 86400
    print(f"WIDE basket: {N} coins, {yrs:.1f}y ({dti[0].date()}..{dti[-1].date()}), ${GROSS:,.0f}.\n")

    books = {s: run(resid, z, s) for s in ["equal", "volscale"]}
    for scheme, book in books.items():
        eq = np.cumsum(book); dd = (eq - np.maximum.accumulate(eq)).min()
        sh = book.mean() / book.std() * np.sqrt(PPY)
        print(f"=== {scheme} ===  Sharpe {sh:.2f} · ret {book.sum()/yrs/GROSS*100:.0f}%/yr · "
              f"maxDD {dd/GROSS*100:.1f}%")
        cr = []
        for name, a, b in CRISES:
            m = np.asarray((dti >= pd.Timestamp(a, tz='utc')) & (dti < pd.Timestamp(b, tz='utc')))
            cr.append(f"{name} {book[m].sum():+.0f}$")
        print("   crises: " + "  ".join(cr))
        yr = []
        for y in sorted(set(dti.year)):
            m = np.asarray(dti.year == y)
            if m.sum() > 100 and book[m].std() > 0:
                yr.append(f"{y}:{book[m].mean()/book[m].std()*np.sqrt(PPY):.1f}")
        print("   per-yr Sharpe: " + "  ".join(yr) + "\n")

    # chart: equity + crisis bands, both schemes
    fig, ax = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    col = {"equal": "#6b7280", "volscale": "#2563eb"}
    for s, book in books.items():
        ax[0].plot(days, np.cumsum(book) / 1000, color=col[s], lw=1.3, label=s)
        dd = (np.cumsum(book) - np.maximum.accumulate(np.cumsum(book))) / 1000
        ax[1].plot(days, dd, color=col[s], lw=1.0, label=s)
    for name, a, b in CRISES:
        d0 = (pd.Timestamp(a, tz='utc').value // 1_000_000 - resid.index[0]) / 1000 / 86400
        d1 = (pd.Timestamp(b, tz='utc').value // 1_000_000 - resid.index[0]) / 1000 / 86400
        for x in ax:
            x.axvspan(d0, d1, color="red", alpha=0.18)
        ax[0].text((d0 + d1) / 2, 5, name, ha="center", fontsize=7, color="darkred")
    ax[0].set_title(f"Wide basket ({N} coins, {yrs:.1f}y) through crises — equity $k", fontsize=12)
    ax[0].set_ylabel("cum $k"); ax[0].legend(); ax[0].grid(alpha=0.25)
    ax[1].set_title("Drawdown $k (vol-scaled should be shallower)", fontsize=11)
    ax[1].set_xlabel("days from 2021-06"); ax[1].set_ylabel("drawdown $k"); ax[1].legend(); ax[1].grid(alpha=0.25)
    fig.tight_layout()
    out = pathlib.Path("research/figures") / "crisis_breadth.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"saved {out}")
    print("GO if: wide basket stays high-Sharpe, every year positive, crises positive — "
          "then breadth+vol-scaling is safe to make the default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
