"""Stage 4 — honest fills for the alt-residual mean-reversion butterfly (the Stage-3 winner).

Strips the idealizations that inflate mean-reversion backtests:
  1. STATE-DEPENDENT slippage: cost at entry/exit = base + k_vol * (that bar's true-range in bps).
     We enter when |z| spikes -> a violent bar -> cost lands hardest exactly where we trade.
     k_vol = the fraction of the bar's range you concede to slippage/adverse selection.
  2. EXECUTION LAG: act on the PREVIOUS bar's z (no same-bar look-ahead / no trading the print).
  3. CARRY DRAG: a funding/borrow cost charged every bar we hold (annualized %).
  4. CAPACITY: separately, how big an order before volume-impact eats the edge.

Sweeps k_vol and carry to see how much of the Stage-3 edge survives realism.

    python scripts/honest_fill.py
"""

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

HIST = pathlib.Path("data/history")
EMA, ZWIN = 168, 168
ZE, ZX, ZS = 1.5, 0.3, 5.0
PPY = 24 * 365
BASE = 10.0   # base round-trip bps (fees + half-spread on the liquid basket hedge)
ALTS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK",
        "LTC", "ADA", "SUI", "NEAR", "APT", "ARB", "OP"]


def load():
    close, tr, dvol = {}, {}, {}
    for n in ALTS:
        f = HIST / f"spot_{n}.parquet"
        if not f.exists():
            continue
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
    DV = pd.DataFrame(dvol).reindex(resid.index)
    return resid, z, TR, DV


def run_axis(resid, z, half_cost, carry_bar, lag):
    """Honest per-axis run. half_cost[i] = state-dependent one-side cost at bar i (bps)."""
    n = len(resid)
    step = np.zeros(n)
    zc = pd.Series(z).shift(lag).to_numpy()
    pos = 0
    entry_i = 0
    entry_s = 0.0
    trades = []
    for i in range(n):
        if pos != 0:
            step[i] += pos * (resid[i] - resid[i - 1]) - carry_bar  # MtM minus holding carry
        zi = zc[i]
        if np.isnan(zi):
            continue
        if pos == 0:
            want = -1 if zi >= ZE else (1 if zi <= -ZE else 0)
            if want:
                pos = want
                entry_i = i
                entry_s = resid[i]
                step[i] -= half_cost[i]
        else:
            if abs(zi) >= ZS or abs(zi) <= ZX:
                step[i] -= half_cost[i]
                gross = pos * (resid[i] - entry_s)
                hold = i - entry_i
                trades.append(gross - half_cost[entry_i] - half_cost[i] - carry_bar * hold)
                pos = 0
    return step, trades


def book(resid, z, TR, k_vol, carry_annual, lag=1):
    n = len(resid)
    carry_bar = carry_annual / 100 * 1e4 / PPY   # %/yr -> bps/bar
    step = np.zeros(n)
    trades = []
    for a in resid.columns:
        hc = (BASE + k_vol * np.nan_to_num(TR[a].to_numpy(), nan=0.0)) / 2.0
        sp, tr = run_axis(resid[a].to_numpy(), z[a].to_numpy(), hc, carry_bar, lag)
        step += sp
        trades += tr
    return step, np.array(trades)


def stats(step, trades, na, yrs):
    mu, sd = step.mean(), step.std()
    sharpe = mu / sd * np.sqrt(PPY) if sd > 0 else 0.0
    eq = np.cumsum(step)
    maxdd = (eq - np.maximum.accumulate(eq)).min() / na
    return (sharpe, step.sum() / na / 100 / yrs, maxdd,
            (trades > 0).mean() * 100, trades.mean(), len(trades))


def main():
    resid, z, TR, DV = load()
    na = resid.shape[1]
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    medtr = float(np.nanmedian(TR.to_numpy()))
    print(f"{na} alts, {yrs:.1f}y, hourly. base={BASE:.0f}bps, lag=1 bar, median bar true-range="
          f"{medtr:.0f}bps.")
    print("k_vol = fraction of the entry/exit bar's range conceded to slippage.\n")
    print(f"  {'k_vol':>6s} {'carry%/yr':>9s} {'+slip(bps)':>11s} | {'Sharpe':>7s} "
          f"{'ret%/yr':>8s} {'maxDD':>7s} {'win%':>5s} {'bps/tr':>7s} {'ntr':>5s}")
    for k_vol in [0.0, 0.05, 0.10, 0.20]:
        for carry in [0.0, 20.0]:
            step, tr = book(resid, z, TR, k_vol, carry)
            sh, ret, dd, win, bpstr, ntr = stats(step, tr, na, yrs)
            slip = k_vol * medtr
            print(f"  {k_vol:6.2f} {carry:9.0f} {slip:11.0f} | {sh:7.2f} {ret:8.0f} "
                  f"{dd:7.0f} {win:5.0f} {bpstr:7.1f} {ntr:5d}")

    # crude capacity: per-trade order notional vs median per-bar dollar-volume of the traded coin.
    # impact ~ 10bps * sqrt(participation); find size where impact ~ matches a typical edge bite.
    meddv = float(np.nanmedian(DV.to_numpy()))
    print(f"\ncapacity sketch: median coin hourly $-volume ~ ${meddv/1e6:.1f}M.")
    for part in [0.01, 0.05, 0.10]:
        notional = part * meddv
        impact = 10 * np.sqrt(part / 0.01)   # 10bps at 1% participation, sqrt-impact
        print(f"  order = {part*100:.0f}% of bar volume (~${notional/1e3:.0f}k/leg) -> "
              f"~{impact:.0f}bps impact/side")
    print("\nRead: watch where Sharpe/ret cross the floor as slippage rises. If it stays >1.5 "
          "Sharpe and ret>0 at k_vol~0.1 + carry, the edge survives honest fills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
