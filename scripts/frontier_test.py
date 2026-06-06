"""Return-vs-drawdown frontier: how much more return does each lever buy, and at what tail?

All configs on ONE window (broad 35-coin set, ~3y) for a fair comparison:
  equal-11      : 11 majors, equal weight                (baseline)
  volscale-11   : 11 majors, inverse-vol sizing          (better tail, same Sharpe)
  equal-35      : 35 coins, equal weight                 (breadth)
  volscale-35   : 35 coins, inverse-vol sizing           (breadth + better tail)
  volscale-35 ×L: levered to the baseline drawdown budget (return boost from spare risk)

Frontier chart: up-and-left = more return for less risk. Leverage just slides a config along a ray
from the origin (Sharpe constant). Window has no major crisis -> absolute Sharpe is optimistic;
the RELATIVE gains are the point.

    python scripts/frontier_test.py
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
MAJORS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA", "NEAR"]


def load(coins):
    s = {}
    for n in coins:
        f = HIST / f"broad_{n}.parquet"
        if f.exists():
            df = pd.read_parquet(f).sort_values("ts")
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
    book = np.zeros(n); tp = []
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
            tp.append(t["net_bps"] / 1e4 * w)
        book += step * notion / 1e4
    return book, np.array(tp)


def stats(book, tp, yrs, lev=1.0):
    b = book * lev
    eq = np.cumsum(b); dd = (eq - np.maximum.accumulate(eq)).min()
    sh = book.mean() / book.std() * np.sqrt(PPY) if book.std() > 0 else 0.0
    return {"sharpe": sh, "ret": b.sum() / yrs / GROSS * 100, "maxdd": dd / GROSS * 100,
            "worst": (tp * lev).min()}


def main():
    coins = sorted(p.stem[len("broad_"):] for p in HIST.glob("broad_*.parquet"))
    resid35, z35 = load(coins)
    resid11, z11 = load(MAJORS)
    yrs = (resid35.index[-1] - resid35.index[0]) / 1000 / 86400 / 365

    rows = {}
    for name, (rr, zz, sc) in {
        "equal-11": (resid11, z11, "equal"),
        "volscale-11": (resid11, z11, "volscale"),
        "equal-35": (resid35, z35, "equal"),
        "volscale-35": (resid35, z35, "volscale"),
    }.items():
        book, tp = run(rr, zz, sc)
        rows[name] = (book, tp, stats(book, tp, yrs))

    # lever volscale-35 to the baseline (equal-11) drawdown budget
    budget = -rows["equal-11"][2]["maxdd"]
    bookv, tpv, sv = rows["volscale-35"]
    lev = budget / -sv["maxdd"]
    rows[f"volscale-35 ×{lev:.1f}"] = (bookv, tpv, stats(bookv, tpv, yrs, lev))

    print(f"{len(coins)} coins, {yrs:.1f}y window (no major crisis — relative comparison).\n")
    print(f"  {'config':16s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD%':>7s} {'worst$':>8s}")
    for name, (_, _, s) in rows.items():
        print(f"  {name:16s} {s['sharpe']:7.2f} {s['ret']:8.0f} {s['maxdd']:7.1f} {s['worst']:8.0f}")

    # frontier chart
    fig, ax = plt.subplots(figsize=(11, 7.5))
    colors = {"equal-11": "#9ca3af", "volscale-11": "#60a5fa", "equal-35": "#f59e0b",
              "volscale-35": "#2563eb"}
    for name, (_, _, s) in rows.items():
        c = colors.get(name, "#dc2626")
        ax.scatter(-s["maxdd"], s["ret"], s=160, color=c, edgecolor="white", zorder=5)
        ax.annotate(f"{name}\nSharpe {s['sharpe']:.1f}", (-s["maxdd"], s["ret"]),
                    xytext=(8, 6), textcoords="offset points", fontsize=9)
    # leverage ray through volscale-35
    sv = rows["volscale-35"][2]
    ray = np.linspace(0, 2.2, 50)
    ax.plot(-sv["maxdd"] * ray, sv["ret"] * ray, color="#2563eb", ls=":", lw=1, zorder=1,
            label="volscale-35 leverage ray")
    ax.axvline(budget, color="#dc2626", ls="--", lw=1, label=f"baseline risk budget ({budget:.1f}% DD)")
    ax.set_xlabel("max drawdown %  (risk →)"); ax.set_ylabel("return %/yr  (↑ better)")
    ax.set_title(f"Return-vs-drawdown frontier — each lever moves you up/left ({yrs:.1f}y)", fontsize=12)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    ax.set_xlim(0, None); ax.set_ylim(0, None)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "return_frontier.png"
    fig.savefig(path, dpi=110)
    print(f"\nsaved {path}")
    print("Read: up-and-left is better. Breadth lifts the whole point; vol-scaling shifts left "
          "(less risk); leverage slides along the ray to spend the freed risk budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
