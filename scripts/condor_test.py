"""Reshape the short-gamma tent and measure whether the new shape is BETTER (tail + Sharpe
+ cost-robustness), on the real alt cross-sectional residuals.

Configs (all on the same 15-alt residual basket):
  butterfly        : enter 1.5, take profit at z=0.3 (hold to the centre), stop z=5   [baseline tent]
  condor           : enter 1.5, take profit at z=1.0 (flat top, skip the noisy centre), stop z=5
  condor+shallow   : condor + tight stop z=3 (shallower wings, cut trends faster)
  condor+overlay   : condor + a sliver (lambda) of long-gamma 'valley' on the SAME residual,
                     which pays exactly where the tent's wing bleeds (the deep runs that don't revert)

Metrics: annualized Sharpe (the >=1.5 gate), annualized return, max drawdown, worst single trade,
win%, and a cost-sensitivity check at 40 & 80 bps round-trip.

    python scripts/condor_test.py
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

HIST = pathlib.Path("data/history")
EMA, ZWIN = 168, 168
PPY = 24 * 365   # hourly periods per year
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


def book(resid, z, z_exit, z_stop, cost, lam=0.0):
    """Return (book_step_pnl, trades). book = summed tent + lam*valley over all axes."""
    n = len(resid)
    tent = np.zeros(n)
    valley = np.zeros(n)
    trades = []
    db = float(np.nanmedian(resid.std()))
    dp = DonchianParams(entry_n=48, exit_n=12, deadband_bps=db, ref_n=720)
    mrp = MRParams(lookback=ZWIN, z_entry=1.5, z_exit=z_exit, z_stop=z_stop)
    for a in resid.columns:
        ra = resid[a].to_numpy()
        tr, sp = run_convergence(ra, z[a].to_numpy(), mrp, cost)
        tent += sp
        trades += tr
        if lam > 0:
            _, vp = run_gamma_additive(ra, dp, cost)
            valley += vp
    return tent + lam * valley, trades


def stats(step, trades, n_axes, yrs):
    eq = np.cumsum(step)
    dd = eq - np.maximum.accumulate(eq)
    mu, sd = step.mean(), step.std()
    sharpe = mu / sd * np.sqrt(PPY) if sd > 0 else 0.0
    ret = step.sum() / n_axes / 100 / yrs          # %/yr per unit gross notional
    maxdd = dd.min() / n_axes                       # bps per unit gross notional
    net = np.array([t["net_bps"] for t in trades]) if trades else np.array([0.0])
    return {"sharpe": sharpe, "ret": ret, "maxdd": maxdd,
            "worst": net.min(), "win": (net > 0).mean() * 100, "ntr": len(trades), "eq": eq}


def main():
    resid, z = load_resid()
    na = resid.shape[1]
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    days = (resid.index.to_numpy() - resid.index[0]) / 1000 / 86400

    configs = [
        ("butterfly",      dict(z_exit=0.3, z_stop=5.0, lam=0.0)),
        ("condor",         dict(z_exit=1.0, z_stop=5.0, lam=0.0)),
        ("condor+shallow", dict(z_exit=1.0, z_stop=3.0, lam=0.0)),
        ("condor+overlay", dict(z_exit=1.0, z_stop=5.0, lam=0.35)),
    ]

    print(f"alt residual basket: {na} legs, {yrs:.1f}y, hourly. cost=20bps unless noted.\n")
    print(f"  {'config':16s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD(bps)':>11s} "
          f"{'worst-tr':>9s} {'win%':>5s} {'ntr':>5s} | {'ret@40':>7s} {'ret@80':>7s}")
    curves = {}
    for name, p in configs:
        step, tr = book(resid, z, p["z_exit"], p["z_stop"], 20.0, p["lam"])
        s = stats(step, tr, na, yrs)
        curves[name] = s["eq"] / na    # per-unit-gross equity in bps
        # cost sensitivity
        r40 = book(resid, z, p["z_exit"], p["z_stop"], 40.0, p["lam"])[0].sum() / na / 100 / yrs
        r80 = book(resid, z, p["z_exit"], p["z_stop"], 80.0, p["lam"])[0].sum() / na / 100 / yrs
        print(f"  {name:16s} {s['sharpe']:7.2f} {s['ret']:8.0f} {s['maxdd']:11.0f} "
              f"{s['worst']:9.0f} {s['win']:5.0f} {s['ntr']:5d} | {r40:7.0f} {r80:7.0f}")

    # plot equity + drawdown
    fig, axs = plt.subplots(1, 2, figsize=(16, 6))
    col = {"butterfly": "seagreen", "condor": "royalblue",
           "condor+shallow": "darkorange", "condor+overlay": "crimson"}
    for name, eq in curves.items():
        axs[0].plot(days, eq, lw=1.4, color=col[name], label=name)
        dd = eq - np.maximum.accumulate(eq)
        axs[1].plot(days, dd, lw=1.2, color=col[name], label=name)
    axs[0].set_title("Equity curve (per unit gross notional, bps)", fontsize=11)
    axs[0].set_xlabel("days"); axs[0].set_ylabel("cum bps"); axs[0].legend(fontsize=9); axs[0].grid(alpha=0.25)
    axs[1].set_title("Drawdown (bps) — lower wing = the tail we're trying to cap", fontsize=11)
    axs[1].set_xlabel("days"); axs[1].set_ylabel("drawdown bps"); axs[1].legend(fontsize=9); axs[1].grid(alpha=0.25)
    fig.suptitle("Reshaping the tent: butterfly vs condor vs shallow-wing vs valley-overlay", fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "condor_compare.png"
    fig.savefig(path, dpi=110)
    print(f"\nsaved {path}")
    print("Read: higher Sharpe + shallower maxDD + ret holding up at 40/80bps = the better shape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
