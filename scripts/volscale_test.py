"""Does volatility-scaled (risk-parity) sizing cap the loss tail WITHOUT compromising the edge?

Equal-weight  : every leg gets the same $ notional.
Vol-scaled    : leg notional ∝ 1/(trailing residual vol) — jumpy/gap-prone coins get LESS capital,
                so each leg contributes ~equal risk and the bad legs do less damage. Causal (uses
                only trailing vol available at entry), capped to [1/3x, 3x] to avoid extremes.

Run on the 5y 11-coin set (incl. LUNA/3AC/FTX) so the tail and crises are visible. Compares
Sharpe / return / max drawdown / worst trade / 5th-pctile trade / per-crisis P&L.

    python scripts/volscale_test.py
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
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA", "NEAR"]
CRISES = [("LUNA", "2022-05-07", "2022-05-16"), ("FTX", "2022-11-07", "2022-11-21")]


def load():
    s = {}
    for n in COINS:
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
    # global median residual-return vol sets the scale for inverse-vol weighting
    vols = {a: pd.Series(np.diff(resid[a].to_numpy(), prepend=resid[a].to_numpy()[0]))
            .rolling(168, min_periods=24).std().shift(1).to_numpy() for a in resid.columns}
    vbar = float(np.nanmedian(np.concatenate([v[np.isfinite(v)] for v in vols.values()])))

    book = np.zeros(n)
    trade_pnls = []
    for a in resid.columns:
        ra = resid[a].to_numpy()
        trades, step = run_convergence(ra, z[a].to_numpy(), mrp, COST)
        va = vols[a]
        notion = np.zeros(n)
        for t in trades:
            i0 = t["entry_i"]
            if scheme == "equal":
                w = base
            else:  # vol-scaled, sized at entry vol (causal), capped
                v = va[i0] if (i0 < n and np.isfinite(va[i0]) and va[i0] > 0) else vbar
                w = base * float(np.clip(vbar / v, 1 / 3, 3.0))
            notion[t["entry_i"]:t["exit_i"] + 1] = w
            trade_pnls.append(t["net_bps"] / 1e4 * w)
        book += step * notion / 1e4
    return book, np.array(trade_pnls)


def stats(book, tp, yrs, dti):
    eq = np.cumsum(book)
    dd = (eq - np.maximum.accumulate(eq)).min()
    sh = book.mean() / book.std() * np.sqrt(PPY) if book.std() > 0 else 0.0
    out = {"sharpe": sh, "ret": book.sum() / yrs / GROSS * 100, "maxdd": dd / GROSS * 100,
           "worst": tp.min(), "p05": np.percentile(tp, 5), "ntr": len(tp)}
    for name, a, b in CRISES:
        m = np.asarray((dti >= pd.Timestamp(a, tz="utc")) & (dti < pd.Timestamp(b, tz="utc")))
        out[name] = book[m].sum()
    return out


def main():
    resid, z = load()
    dti = pd.to_datetime(resid.index, unit="ms", utc=True)
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    print(f"{resid.shape[1]} coins, {yrs:.1f}y, ${GROSS:,.0f} gross, cost={COST:.0f}bps.\n")
    print(f"  {'scheme':12s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD%':>7s} {'worst$':>8s} "
          f"{'p05$':>7s} {'LUNA$':>8s} {'FTX$':>8s} {'ntr':>6s}")
    res, books, tps = {}, {}, {}
    for scheme in ["equal", "volscale"]:
        book, tp = run(resid, z, scheme)
        res[scheme] = stats(book, tp, yrs, dti)
        books[scheme], tps[scheme] = book, tp
        s = res[scheme]
        print(f"  {scheme:12s} {s['sharpe']:7.2f} {s['ret']:8.0f} {s['maxdd']:7.1f} "
              f"{s['worst']:8.0f} {s['p05']:7.0f} {s['LUNA']:8.0f} {s['FTX']:8.0f} {s['ntr']:6d}")
    e, v = res["equal"], res["volscale"]
    print(f"\n  vol-scaled vs equal: Sharpe {v['sharpe']/e['sharpe']-1:+.0%}, "
          f"return {v['ret']/e['ret']-1:+.0%}, worst-trade {v['worst']/e['worst']-1:+.0%}, "
          f"maxDD {v['maxdd']/e['maxdd']-1:+.0%}, "
          f"Calmar {(v['ret']/-v['maxdd'])/(e['ret']/-e['maxdd'])-1:+.0%}")

    # ---- visualization ----
    days = (resid.index.to_numpy() - resid.index[0]) / 1000 / 86400
    col = {"equal": "#6b7280", "volscale": "#2563eb"}
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))

    ax = axs[0, 0]
    for sc in ["equal", "volscale"]:
        ax.plot(days, np.cumsum(books[sc]) / 1000, color=col[sc], lw=1.3, label=sc)
    for name, a, b in CRISES:
        d0 = (pd.Timestamp(a, tz="utc").value // 1_000_000 - resid.index[0]) / 1000 / 86400
        d1 = (pd.Timestamp(b, tz="utc").value // 1_000_000 - resid.index[0]) / 1000 / 86400
        ax.axvspan(d0, d1, color="red", alpha=0.15)
    ax.set_title("A · Equity ($k) — red = crises", fontsize=11)
    ax.set_xlabel("days"); ax.set_ylabel("cum $k"); ax.legend(); ax.grid(alpha=0.25)

    ax = axs[0, 1]
    for sc in ["equal", "volscale"]:
        eq = np.cumsum(books[sc]); dd = (eq - np.maximum.accumulate(eq)) / 1000
        ax.plot(days, dd, color=col[sc], lw=1.1, label=sc)
    ax.set_title(f"B · Drawdown ($k) — vol-scaled cuts maxDD {v['maxdd']/e['maxdd']-1:+.0%}", fontsize=11)
    ax.set_xlabel("days"); ax.set_ylabel("drawdown $k"); ax.legend(); ax.grid(alpha=0.25)

    ax = axs[1, 0]
    lo = min(tps["equal"].min(), tps["volscale"].min())
    bins = np.linspace(lo, 200, 70)
    for sc in ["equal", "volscale"]:
        ax.hist(tps[sc], bins=bins, color=col[sc], alpha=0.55, label=sc)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_title("C · Per-trade P&L ($) — left tail shrinks (vol-scaled)", fontsize=11)
    ax.set_xlabel("trade P&L $"); ax.set_ylabel("count"); ax.set_yscale("log"); ax.legend(); ax.grid(alpha=0.25)

    ax = axs[1, 1]
    labels = ["Sharpe", "ret %/yr", "|maxDD| %", "|worst| $k", "Calmar"]
    ev = [e["sharpe"], e["ret"], -e["maxdd"], -e["worst"] / 1000, e["ret"] / -e["maxdd"]]
    vv = [v["sharpe"], v["ret"], -v["maxdd"], -v["worst"] / 1000, v["ret"] / -v["maxdd"]]
    x = np.arange(len(labels)); w = 0.38
    ax.bar(x - w / 2, ev, w, color=col["equal"], label="equal")
    ax.bar(x + w / 2, vv, w, color=col["volscale"], label="volscale")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_title("D · Metrics (lower |maxDD|/|worst| = better tail)", fontsize=11)
    ax.legend(); ax.grid(alpha=0.25, axis="y")
    for i, (a_, b_) in enumerate(zip(ev, vv)):
        ax.text(i - w / 2, a_, f"{a_:.0f}" if a_ > 5 else f"{a_:.1f}", ha="center", va="bottom", fontsize=7)
        ax.text(i + w / 2, b_, f"{b_:.0f}" if b_ > 5 else f"{b_:.1f}", ha="center", va="bottom", fontsize=7)

    fig.suptitle("Volatility-scaled sizing — same Sharpe, smaller tail (5y incl. LUNA/3AC/FTX)", fontsize=14)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "volscale_compare.png"
    fig.savefig(path, dpi=110)
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
