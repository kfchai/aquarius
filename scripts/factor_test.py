"""Does a cleaner (multi-factor) residual revert better? Compare three constructions on the 5y
30-coin set, vol-scaled, with crisis isolation.

  single  : resid = dev − cross-sectional MEAN(dev)        [current — one common factor]
  sector  : resid = dev − SECTOR-mean(dev)                 [remove sector rotations too; CAUSAL]
  pca2    : resid = dev − top-2 principal components       [remove 2 factors; FULL-SAMPLE = hindsight]

If sector/pca lift Sharpe AND hold the tail, a cleaner residual is worth adopting. (Screening model:
run_convergence, flat 20bps — absolute numbers inflated; the RELATIVE gap across variants is the point.)

    python scripts/factor_test.py
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
CRISES = [("LUNA", "2022-05-07", "2022-05-16"), ("FTX", "2022-11-07", "2022-11-21")]
SECTORS = {
    "SoV/pay": ["BTC", "LTC", "XRP", "XLM", "ETC", "DOGE"],
    "L1": ["ETH", "SOL", "BNB", "AVAX", "NEAR", "ADA", "DOT", "ATOM", "ALGO", "ICP", "HBAR", "EGLD", "FLOW"],
    "DeFi": ["UNI", "AAVE", "CRV", "INJ", "RUNE"],
    "Infra": ["LINK", "GRT", "FIL"],
    "Gaming": ["SAND", "MANA", "AXS"],
}


def dev_matrix():
    coins = sorted(p.stem[len("long_"):] for p in HIST.glob("long_*.parquet"))
    s = {}
    for n in coins:
        df = pd.read_parquet(HIST / f"long_{n}.parquet").sort_values("ts")
        s[n] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    close = pd.DataFrame(s).dropna()
    lp = np.log(close)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    return dev.dropna()


def to_z(resid):
    resid = resid.dropna()
    return resid, (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)


def build(dev, kind):
    if kind == "single":
        r = dev.sub(dev.mean(axis=1), axis=0)
    elif kind == "sector":
        coin2sec = {c: s for s, cs in SECTORS.items() for c in cs}
        sec = pd.Series({c: coin2sec.get(c, "L1") for c in dev.columns})
        secmean = dev.T.groupby(sec).transform("mean").T          # each coin − its sector mean
        r = dev - secmean
    else:  # pca2 — remove top-2 PCs (full-sample SVD = hindsight, exploratory ceiling)
        M = dev.to_numpy(); Mc = M - M.mean(0)
        U, S, Vt = np.linalg.svd(Mc, full_matrices=False)
        k = 2
        recon = U[:, :k] @ np.diag(S[:k]) @ Vt[:k, :]
        r = pd.DataFrame(Mc - recon, index=dev.index, columns=dev.columns)
    return to_z(r)


def run(resid, z):
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
            vv = va[i0] if (i0 < n and np.isfinite(va[i0]) and va[i0] > 0) else vbar
            notion[i0:t["exit_i"] + 1] = base * float(np.clip(vbar / vv, 1 / 3, 3.0))
        book += step * notion / 1e4
    return book


def main():
    dev = dev_matrix()
    print(f"{dev.shape[1]} coins, {(dev.index[-1]-dev.index[0])/1000/86400/365:.1f}y. vol-scaled, screening model.\n")
    print(f"  {'residual':10s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD%':>7s} {'LUNA$':>7s} {'FTX$':>7s}")
    books = {}
    for kind in ["single", "sector", "pca2"]:
        resid, z = build(dev, kind)
        dti = pd.to_datetime(resid.index, unit="ms", utc=True)
        yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
        book = run(resid, z); books[kind] = (book, resid.index)
        eq = np.cumsum(book); dd = (eq - np.maximum.accumulate(eq)).min()
        sh = book.mean() / book.std() * np.sqrt(PPY)
        cr = []
        for name, a, b in CRISES:
            m = np.asarray((dti >= pd.Timestamp(a, tz='utc')) & (dti < pd.Timestamp(b, tz='utc')))
            cr.append(book[m].sum())
        print(f"  {kind:10s} {sh:7.2f} {book.sum()/yrs/GROSS*100:8.0f} {dd/GROSS*100:7.1f} "
              f"{cr[0]:7.0f} {cr[1]:7.0f}")

    fig, ax = plt.subplots(figsize=(13, 6))
    col = {"single": "#6b7280", "sector": "#16a34a", "pca2": "#dc2626"}
    for kind, (book, idx) in books.items():
        d = (idx.to_numpy() - idx[0]) / 1000 / 86400
        ax.plot(d, np.cumsum(book) / 1000, color=col[kind], lw=1.3, label=kind)
    ax.set_title("Residual construction: single vs sector-neutral vs PCA-2 (vol-scaled, 5y) — equity $k",
                 fontsize=12)
    ax.set_xlabel("days from 2021"); ax.set_ylabel("cum $k"); ax.legend(); ax.grid(alpha=0.25)
    fig.tight_layout()
    out = pathlib.Path("research/figures") / "factor_compare.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\nsaved {out}")
    print("Read: if sector (causal) lifts Sharpe over single without a worse tail -> adopt it. "
          "pca2 is full-sample hindsight (an upside ceiling, not directly tradeable).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
