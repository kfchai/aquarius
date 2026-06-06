"""Long-gamma overlay as a tail hedge for the reversal book.

Core = short-gamma mean-reversion (vol-scaled, sector-neutral residuals — the current engine).
Overlay = per-coin long-gamma breakout (run_gamma_additive): goes WITH a residual that trends past
the danger zone, so it PROFITS exactly when a core leg runs to its stop. Net = core + λ·overlay.

Sweep λ: does a small overlay cut the tail (maxDD / worst bar / crisis) enough to justify its calm
bleed (the insurance premium)? 5y 30-coin set, screening model (relative comparison).

    python scripts/overlay_test.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.backtest.strategy import (  # noqa: E402
    DonchianParams, MRParams, run_convergence, run_gamma_additive,
)
from aquarius.paper.shadow import ShadowConfig, residualize  # noqa: E402

HIST = pathlib.Path("data/history")
PPY, GROSS, COST = 24 * 365, 100_000.0, 20.0
CRISES = [("LUNA", "2022-05-07", "2022-05-16"), ("FTX", "2022-11-07", "2022-11-21")]


def load_close():
    s = {}
    for p in sorted(HIST.glob("long_*.parquet")):
        df = pd.read_parquet(p).sort_values("ts")
        s[p.stem[len("long_"):]] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    return pd.DataFrame(s).dropna()


def main():
    cfg = ShadowConfig(sector_neutral=True)
    resid, z = residualize(load_close(), cfg)
    n, N = len(resid), resid.shape[1]
    base = GROSS / N
    dti = pd.to_datetime(resid.index, unit="ms", utc=True)
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    mrp = MRParams(lookback=cfg.zwin, z_entry=1.5, z_exit=0.3, z_stop=5.0)
    db = float(np.nanmedian(resid.std()))
    dp = DonchianParams(entry_n=48, exit_n=12, deadband_bps=db, ref_n=720)

    vols = {a: pd.Series(np.diff(resid[a].to_numpy(), prepend=resid[a].to_numpy()[0]))
            .rolling(168, min_periods=24).std().shift(1).to_numpy() for a in resid.columns}
    vbar = float(np.nanmedian(np.concatenate([v[np.isfinite(v)] for v in vols.values()])))

    core = np.zeros(n)
    overlay = np.zeros(n)
    for a in resid.columns:
        ra = resid[a].to_numpy()
        trades, step = run_convergence(ra, z[a].to_numpy(), mrp, COST)
        va = vols[a]; notion = np.zeros(n)
        for t in trades:
            i0 = t["entry_i"]
            vv = va[i0] if (i0 < n and np.isfinite(va[i0]) and va[i0] > 0) else vbar
            notion[i0:t["exit_i"] + 1] = base * float(np.clip(vbar / vv, 1 / 3, 3.0))
        core += step * notion / 1e4
        _, ov = run_gamma_additive(ra, dp, COST)            # long-gamma breakout on the residual
        overlay += ov * base / 1e4

    def stats(book):
        eq = np.cumsum(book); dd = (eq - np.maximum.accumulate(eq)).min()
        sh = book.mean() / book.std() * np.sqrt(PPY) if book.std() > 0 else 0.0
        cr = {nm: book[np.asarray((dti >= pd.Timestamp(a, tz='utc')) & (dti < pd.Timestamp(b, tz='utc')))].sum()
              for nm, a, b in CRISES}
        return sh, book.sum() / yrs / GROSS * 100, dd / GROSS * 100, book.min(), cr

    print(f"{N} coins, {yrs:.1f}y. overlay-alone ret = {overlay.sum()/yrs/GROSS*100:+.0f}%/yr "
          f"(calm bleed = insurance premium).\n")
    print(f"  {'lambda':>7s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD%':>7s} {'worst-bar$':>10s} "
          f"{'LUNA$':>7s} {'FTX$':>7s}")
    rows = []
    for lam in [0.0, 0.1, 0.2, 0.35, 0.5]:
        sh, ret, dd, worst, cr = stats(core + lam * overlay)
        rows.append((lam, sh, ret, dd, worst))
        print(f"  {lam:7.2f} {sh:7.2f} {ret:8.0f} {dd:7.1f} {worst:10.0f} "
              f"{cr['LUNA']:7.0f} {cr['FTX']:7.0f}")

    # chart: maxDD% and ret%/yr vs lambda
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
    lams = [r[0] for r in rows]
    ax[0].plot(lams, [-r[3] for r in rows], "o-", color="#dc2626")
    ax[0].set_title("Tail vs overlay size", fontsize=11); ax[0].set_xlabel("λ (overlay fraction)")
    ax[0].set_ylabel("|max drawdown| %"); ax[0].grid(alpha=0.3)
    ax[1].plot(lams, [r[2] for r in rows], "o-", color="#2563eb")
    ax[1].set_title("Return vs overlay size", fontsize=11); ax[1].set_xlabel("λ (overlay fraction)")
    ax[1].set_ylabel("return %/yr"); ax[1].grid(alpha=0.3)
    fig.suptitle("Long-gamma overlay: does a small λ cut the tail without killing return? (5y)", fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures") / "overlay_test.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\nsaved {out}")
    print("Read: worth it only if a small λ shrinks |maxDD| meaningfully while ret stays close to λ=0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
