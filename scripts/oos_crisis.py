"""Stage 4/5 — OUT-OF-SAMPLE across regimes + crisis isolation for the reversal basket.

Runs the honest-fill book (state-dependent slippage + carry + 1-bar lag) on 5 years of the
11-coin older alt basket, then:
  - headline OOS stats over the full window (+ a k_vol/carry sweep),
  - per-CALENDAR-YEAR Sharpe/ret/maxDD (does it hold across regimes?),
  - CRISIS isolation: P&L, worst bar, intra-window drawdown during LUNA / 3AC / FTX / Aug-2024.

This is the make-or-break: a benign window is exactly where mean-reversion lies. If the edge holds
OOS and the cascades don't fire the tail across all legs at once, it's a genuine GO.

    python scripts/oos_crisis.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.honest_fill import book, stats, BASE, PPY  # noqa: E402

HIST = pathlib.Path("data/history")
EMA, ZWIN = 168, 168
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "LTC", "ADA", "NEAR"]

CRISES = [
    ("LUNA/UST",     "2022-05-07", "2022-05-16"),
    ("3AC/Celsius",  "2022-06-12", "2022-06-19"),
    ("FTX",          "2022-11-07", "2022-11-21"),
    ("Aug-24 unwind", "2024-08-04", "2024-08-07"),
]


def load_long():
    close, tr, dvol = {}, {}, {}
    for n in COINS:
        f = HIST / f"long_{n}.parquet"
        df = pd.read_parquet(f).sort_values("ts")
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
    return resid, z, TR


def seg_stats(step, na, idx, mask):
    s = step[mask]
    if s.size < 24 or s.std() == 0:
        return None
    eq = np.cumsum(s)
    dd = (eq - np.maximum.accumulate(eq)).min() / na
    yrs = mask.sum() / PPY
    return s.mean() / s.std() * np.sqrt(PPY), s.sum() / na / 100 / yrs, dd


def main():
    resid, z, TR = load_long()
    na = resid.shape[1]
    dti = pd.to_datetime(resid.index, unit="ms", utc=True)
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    print(f"OOS basket: {na} alts, {yrs:.1f}y ({dti[0].date()} .. {dti[-1].date()}), hourly. "
          f"base={BASE:.0f}bps, lag=1, k_vol=0.10, carry=20%/yr.\n")

    # headline + sweep
    print("=== full-window honest-fill sweep ===")
    print(f"  {'k_vol':>6s} {'carry':>6s} | {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD':>7s} "
          f"{'win%':>5s} {'bps/tr':>7s} {'ntr':>6s}")
    base_step = None
    for k_vol in [0.0, 0.10, 0.20]:
        for carry in [0.0, 20.0]:
            step, tr = book(resid, z, TR, k_vol, carry)
            sh, ret, dd, win, bpstr, ntr = stats(step, tr, na, yrs)
            if k_vol == 0.10 and carry == 20.0:
                base_step = step
            print(f"  {k_vol:6.2f} {carry:6.0f} | {sh:7.2f} {ret:8.0f} {dd:7.0f} "
                  f"{win:5.0f} {bpstr:7.1f} {ntr:6d}")

    step = base_step
    # per-year
    print("\n=== per calendar year (k_vol=0.10, carry=20%/yr) ===")
    print(f"  {'year':>6s} {'Sharpe':>7s} {'ret%/yr':>8s} {'maxDD':>7s} {'bars':>6s}")
    for yr in sorted(set(dti.year)):
        mask = np.asarray(dti.year == yr)
        r = seg_stats(step, na, dti, mask)
        if r:
            print(f"  {yr:6d} {r[0]:7.2f} {r[1]:8.0f} {r[2]:7.0f} {mask.sum():6d}")

    # crisis isolation
    print("\n=== crisis windows (book P&L per unit gross; does the tail fire?) ===")
    print(f"  {'event':>14s} {'days':>5s} {'P&L(bps)':>9s} {'worst-bar':>10s} {'maxDD':>7s} "
          f"{'ann.Sharpe':>10s}")
    for name, a, b in CRISES:
        mask = np.asarray((dti >= pd.Timestamp(a, tz='utc')) & (dti < pd.Timestamp(b, tz='utc')))
        if mask.sum() < 12:
            print(f"  {name:>14s}  (no data)"); continue
        s = step[mask]
        eq = np.cumsum(s)
        dd = (eq - np.maximum.accumulate(eq)).min() / na
        r = seg_stats(step, na, dti, mask)
        sh = r[0] if r else float('nan')
        print(f"  {name:>14s} {mask.sum()/24:5.0f} {s.sum()/na:9.0f} {s.min()/na:10.0f} "
              f"{dd:7.0f} {sh:10.2f}")

    # plot equity + rolling 30d Sharpe
    days = (resid.index.to_numpy() - resid.index[0]) / 1000 / 86400
    eq = np.cumsum(step) / na
    roll = pd.Series(step)
    rsh = (roll.rolling(720).mean() / roll.rolling(720).std() * np.sqrt(PPY)).to_numpy()
    fig, axs = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
    axs[0].plot(days, eq, lw=1.0, color="navy")
    axs[1].plot(days, rsh, lw=0.8, color="teal"); axs[1].axhline(0, color="k", lw=0.6)
    axs[1].axhline(1.5, color="green", ls=":", lw=0.9, label="Sharpe 1.5 gate")
    for name, a, b in CRISES:
        d0 = (pd.Timestamp(a, tz='utc').value // 1_000_000 - resid.index[0]) / 1000 / 86400
        d1 = (pd.Timestamp(b, tz='utc').value // 1_000_000 - resid.index[0]) / 1000 / 86400
        for ax in axs:
            ax.axvspan(d0, d1, color="red", alpha=0.18)
        axs[0].text((d0 + d1) / 2, eq.max() * 0.95, name, ha="center", fontsize=7, color="darkred")
    axs[0].set_title(f"OOS equity (per unit gross, bps) — {na} alts, {yrs:.1f}y, honest fills",
                     fontsize=11)
    axs[0].set_ylabel("cum bps"); axs[0].grid(alpha=0.25)
    axs[1].set_title("Rolling 30-day annualized Sharpe (red = crises)", fontsize=11)
    axs[1].set_xlabel("days from 2021-06"); axs[1].set_ylabel("Sharpe")
    axs[1].legend(fontsize=8); axs[1].grid(alpha=0.25)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "oos_crisis.png"
    fig.savefig(path, dpi=110)
    print(f"\nsaved {path}")
    print("GO if: full-window Sharpe stays high, EVERY year positive, and crises show small/positive "
          "P&L (market-neutral holds). NO-GO if a cascade craters the book (tail fires across legs).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
