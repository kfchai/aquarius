"""Phase-0 falsifier for a momentum book: does the residual show CONTINUATION at any horizon?

Your reversal book trades the residual LEVEL (mean-reverting at the hourly horizon). Momentum is
the same question at a longer horizon: does trailing residual MOVEMENT predict forward residual
movement (same sign = momentum, opposite sign = reversal)?

Because the residual is cross-sectionally demeaned each bar (resid = dev − mean(dev), rows sum ≈ 0),
the market component is already stripped — so the pooled autocorrelation of residual returns IS the
cross-sectional momentum/reversal signature (no directional/market trend leaking in).

For each horizon L (hours) it reports, on the 5y 30-coin set:
  autocorr  : pooled corr(past-L residual return, next-L residual return).  <0 reversal, >0 momentum.
  IC t-stat : significance of that relationship (non-overlapping samples).
  LS Sharpe : tradeable proxy — long top-third / short bottom-third by trailing residual return,
              hold L (non-overlapping), annualized Sharpe of the dollar-neutral spread.
  LS bps    : mean residual P&L per period (bps), sign-aware.

READ: where autocorr / LS-Sharpe is NEGATIVE = your reversal book's turf. Where it crosses POSITIVE
= a momentum horizon worth building. If it never turns positive, residual momentum has no edge here
— stop before writing a backtest. (Screening diagnostic: gross residual moves, no fills/costs yet.)

    python scripts/momentum_horizon.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

HIST = pathlib.Path("data/history")
EMA = 168
PPY = 24 * 365
# horizons in hours: 1h .. 30d
HORIZONS = [1, 2, 4, 8, 12, 24, 48, 72, 120, 168, 336, 504, 720]


def load_logprice():
    coins = sorted(p.stem[len("long_"):] for p in HIST.glob("long_*.parquet"))
    s = {}
    for n in coins:
        df = pd.read_parquet(HIST / f"long_{n}.parquet").sort_values("ts")
        s[n] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    return np.log(pd.DataFrame(s).dropna())


def signals(lp, kind, L):
    """Return (past, fwd) panels of L-horizon momentum signals, both delta-neutral (per-bar demeaned).

      residual : EWMA-detrended deviation (your reversal book's object) — pulled to 0 by the EMA.
      relative : trailing RAW return minus the cross-sectional mean — classic XS relative-strength
                 momentum, NOT mechanically mean-reverting. This is the real momentum test.
    """
    if kind == "residual":
        ratio = lp.sub(lp.mean(axis=1), axis=0)
        dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
        r = dev.sub(dev.mean(axis=1), axis=0).dropna()
        past = (r - r.shift(L))
        fwd = (r.shift(-L) - r)
    else:  # relative — raw L-return, cross-sectionally demeaned each bar (bps)
        ret_past = (lp - lp.shift(L)) * 1e4
        ret_fwd = (lp.shift(-L) - lp) * 1e4
        past = ret_past.sub(ret_past.mean(axis=1), axis=0)
        fwd = ret_fwd.sub(ret_fwd.mean(axis=1), axis=0)
    common = past.dropna(how="all").index
    return past.reindex(common), fwd.reindex(common)


def horizon_stats(past_df, fwd_df, L):
    """Returns (autocorr, ic_t, ls_sharpe, ls_bps, n_periods)."""
    past = past_df.to_numpy()
    fwd = fwd_df.to_numpy()
    n, ncoins = past.shape

    # pooled autocorrelation (≈ cross-sectional IC, since rows are demeaned)
    P, F = past.ravel(), fwd.ravel()
    m = np.isfinite(P) & np.isfinite(F)
    ac = float(np.corrcoef(P[m], F[m])[0, 1]) if m.sum() > 2 else np.nan

    # tradeable, NON-OVERLAPPING long-short spread (long top-third trailing, short bottom-third)
    sp = []
    for t in range(L, n - L, L):
        pr, fr = past[t], fwd[t]
        valid = np.where(np.isfinite(pr) & np.isfinite(fr))[0]
        if valid.size < 6:
            continue
        o = valid[np.argsort(pr[valid])]                          # ascending trailing return
        k = max(1, o.size // 3)
        short, long = o[:k], o[-k:]                               # bottom third / top third
        sp.append(fr[long].mean() - fr[short].mean())             # momentum spread, bps over L
    sp = np.array(sp)
    if sp.size < 3 or sp.std() == 0:
        return ac, np.nan, np.nan, np.nan, sp.size
    ls_sharpe = sp.mean() / sp.std() * np.sqrt(PPY / L)           # annualized
    ic_t = ac * np.sqrt(max(m.sum() / ncoins / L, 1.0))           # crude non-overlap t (informational)
    return ac, ic_t, ls_sharpe, float(sp.mean()), sp.size


def main():
    lp = load_logprice()
    yrs = (lp.index[-1] - lp.index[0]) / 1000 / 86400 / 365
    print(f"{lp.shape[1]} coins, {yrs:.1f}y hourly. Two delta-neutral momentum constructions:\n"
          f"  residual = EWMA-detrended (your reversal object) | relative = raw XS relative-strength\n")

    series = {}
    for kind in ["residual", "relative"]:
        print(f"[{kind}]  {'horizon':>7s} {'autocorr':>9s} {'IC_t':>6s} {'LS_Sharpe':>10s} "
              f"{'LS_bps':>8s} {'periods':>8s}")
        rows = []
        for L in HORIZONS:
            past_df, fwd_df = signals(lp, kind, L)
            ac, ict, sh, bps, npd = horizon_stats(past_df, fwd_df, L)
            lbl = f"{L}h" if L < 24 else f"{L // 24}d"
            rows.append((L, lbl, ac, sh))
            print(f"          {lbl:>7s} {ac:9.3f} {ict:6.1f} {sh:10.2f} {bps:8.1f} {npd:8d}")
        series[kind] = rows
        print()

    # --- figure: autocorr signature + tradeable LS-Sharpe vs horizon, both constructions ---
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5))
    col = {"residual": "#6b7280", "relative": "#2563eb"}
    labels = [r[1] for r in series["relative"]]
    for kind, rows in series.items():
        Ls = [r[0] for r in rows]
        a1.plot(Ls, [r[2] for r in rows], "o-", color=col[kind], lw=1.6, label=kind)
        a2.plot(Ls, [r[3] for r in rows], "o-", color=col[kind], lw=1.6, label=kind)
    for ax in (a1, a2):
        ax.axhline(0, color="#9ca3af", lw=1)
        ax.set_xscale("log")
        ax.set_xticks([r[0] for r in series["relative"]]); ax.set_xticklabels(labels, rotation=45)
        ax.set_xlabel("horizon"); ax.legend(); ax.grid(alpha=0.25)
    a1.set_title("Autocorrelation vs horizon  (<0 = reversal, >0 = momentum)", fontsize=11)
    a1.set_ylabel("pooled autocorr")
    a2.set_title("XS long-short spread annualized Sharpe (gross, no costs)", fontsize=11)
    a2.set_ylabel("Sharpe")
    fig.tight_layout()
    out = pathlib.Path("research/figures") / "momentum_horizon.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"saved {out}")
    print("READ: 'relative' is the real momentum test (not EMA-pulled). A horizon where its autocorr "
          "and LS-Sharpe turn clearly positive (a band, not one spike) is where to build the book; "
          "negative everywhere -> no XS-momentum edge on this universe, stop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
