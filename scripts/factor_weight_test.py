"""Does a market-cap-weighted 'pack mean' beat equal-weight for the residual signal?

The pack mean defines the factor we strip out. Test three weightings of BOTH cross-sectional means
(market level + common factor) on the 5y 30-coin set, vol-scaled, screening model:
  equal   : every coin weighted the same (current)
  cap     : weighted by trailing $-volume (proxy for market cap — BTC/ETH dominate the mean)
  sqrtcap : weighted by sqrt($-volume) (gentler concentration)

    python scripts/factor_weight_test.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import MRParams, run_convergence  # noqa: E402

HIST = pathlib.Path("data/history")
EMA, ZWIN, PPY = 168, 168, 24 * 365
GROSS, COST = 100_000.0, 20.0
CRISES = [("LUNA", "2022-05-07", "2022-05-16"), ("FTX", "2022-11-07", "2022-11-21")]


def load():
    close, dvol = {}, {}
    for p in sorted(HIST.glob("long_*.parquet")):
        c = p.stem[len("long_"):]
        df = pd.read_parquet(p).sort_values("ts"); ts = df["ts"].to_numpy()
        close[c] = pd.Series(df["close"].to_numpy(), index=ts)
        dvol[c] = pd.Series((df["close"] * df["volume"]).to_numpy(), index=ts)
    return pd.DataFrame(close).dropna(), pd.DataFrame(dvol)


def wmean(x, W):
    """Cross-sectional weighted mean per row (broadcast back to a column)."""
    return (x * W).sum(axis=1) / W.sum(axis=1)


def build(close, W):
    lp = np.log(close)
    ratio = lp.sub(wmean(lp, W), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(wmean(dev, W), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    return resid, z


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
    close, dvol = load()
    capw = dvol.rolling(168, min_periods=24).median().reindex(close.index).ffill().fillna(dvol.median())
    weights = {
        "equal": pd.DataFrame(1.0, index=close.index, columns=close.columns),
        "cap": capw,
        "sqrtcap": np.sqrt(capw),
    }
    print(f"{close.shape[1]} coins, {(close.index[-1]-close.index[0])/1000/86400/365:.1f}y. "
          f"vol-scaled, screening model.\n")
    print(f"  {'pack mean':10s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD%':>7s} {'LUNA$':>7s} {'FTX$':>7s}")
    for name, W in weights.items():
        resid, z = build(close, W)
        dti = pd.to_datetime(resid.index, unit="ms", utc=True)
        yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
        book = run(resid, z)
        eq = np.cumsum(book); dd = (eq - np.maximum.accumulate(eq)).min()
        sh = book.mean() / book.std() * np.sqrt(PPY)
        cr = [book[np.asarray((dti >= pd.Timestamp(a, tz='utc')) & (dti < pd.Timestamp(b, tz='utc')))].sum()
              for _, a, b in CRISES]
        print(f"  {name:10s} {sh:7.2f} {book.sum()/yrs/GROSS*100:8.0f} {dd/GROSS*100:7.1f} "
              f"{cr[0]:7.0f} {cr[1]:7.0f}")
    print("\nRead: cap-weighting wins only if Sharpe clearly beats equal without a worse tail. "
          "(My prior: equal-weight holds up — cap-weighting starves BTC/ETH of signal.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
