"""Visualize the mean-reversion TENDENCY of crypto cross-sectional residuals on historical data.

Four complementary views (pooled over all coins, broad 35-coin set):
  A Conditional next-move: mean Δz over the next H hours vs current z. Downward slope through 0 =
    rich coins fall back, cheap coins rise back -> reversion. (The core signature.)
  B Event-study decay: align every dislocation (|z| first crosses 1.5) at t=0, average |z| forward.
    A decay toward 0 = the gap closes; mark the take-profit band and the half-life.
  C Reversion payoff by entry z: average forward move in the convergence direction, by starting z.
    A 'smile' (positive both sides, bigger at extremes) = the further out, the bigger the snap-back.
  D Autocorrelation: lag-1..24 autocorr of RESIDUAL returns (negative = reversion) vs RAW returns
    (~0) — shows it's the cross-sectional residual that reverts, not price itself.

    python scripts/viz_reversion.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HIST = pathlib.Path("data/history")
EMA, ZWIN, H = 168, 168, 24    # detrend / z-window / reversion horizon (hours)
ZE, ZX = 1.5, 0.3


def load():
    coins = sorted(p.stem[len("broad_"):] for p in HIST.glob("broad_*.parquet"))
    close = {}
    for c in coins:
        df = pd.read_parquet(HIST / f"broad_{c}.parquet").sort_values("ts")
        close[c] = pd.Series(df["close"].to_numpy(), index=df["ts"].to_numpy())
    close = pd.DataFrame(close).dropna()
    lp = np.log(close)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=EMA, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(ZWIN, min_periods=24).std()).reindex(resid.index)
    return close.reindex(resid.index), resid, z


def main():
    close, resid, z = load()
    Z = z.to_numpy()
    Rz = resid.to_numpy()
    T, N = Z.shape
    yrs = (resid.index[-1] - resid.index[0]) / 1000 / 86400 / 365
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))

    # A — conditional next-move vs current z
    dzf = np.full_like(Z, np.nan); dzf[:-H] = Z[H:] - Z[:-H]
    x = Z[:-H].ravel(); y = dzf[:-H].ravel()
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    bins = np.linspace(-4, 4, 17)
    cen, mu = [], []
    for b in range(1, len(bins)):
        sel = (x >= bins[b - 1]) & (x < bins[b])
        if sel.sum() > 100:
            cen.append((bins[b - 1] + bins[b]) / 2); mu.append(y[sel].mean())
    cen, mu = np.array(cen), np.array(mu)
    slope = np.polyfit(cen, mu, 1)[0]
    ax = axs[0, 0]
    ax.axhline(0, color="#888", lw=0.7); ax.axvline(0, color="#888", lw=0.7)
    ax.plot(cen, mu, "o-", color="#b91c1c", lw=2)
    ax.plot(cen, -cen, color="#94a3b8", ls=":", lw=1, label="full reversion (slope −1)")
    ax.set_title(f"A · Next-{H}h mean Δz vs current z  (slope={slope:+.2f} → reversion)", fontsize=11)
    ax.set_xlabel("current z (σ from pack)"); ax.set_ylabel(f"mean Δz over next {H}h")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)

    # B — event-study decay after a dislocation, SIGN-FOLDED so it decays toward 0
    # (mean |z| can't reach 0 even for random data — E|N(0,1)|≈0.8 — so we fold by entry sign:
    #  sign(z0)·z(t+k) averages from ~+1.7 down toward 0 as the gap closes.)
    K = 72
    paths = []
    for j in range(N):
        zc = Z[:, j]
        cross = np.where((np.abs(zc[1:]) >= ZE) & (np.abs(zc[:-1]) < ZE))[0] + 1
        for t in cross:
            if t + K < T:
                seg = np.sign(zc[t]) * zc[t:t + K + 1]
                if np.isfinite(seg).all():
                    paths.append(seg)
    P = np.array(paths)
    mp = P.mean(axis=0)
    halflvl = mp[0] / 2
    half = int(np.argmax(mp <= halflvl)) if (mp <= halflvl).any() else K
    ax = axs[0, 1]
    ax.plot(range(K + 1), mp, color="#2563eb", lw=2)
    ax.fill_between(range(K + 1), mp, 0, color="#2563eb", alpha=0.08)
    ax.axhline(0, color="#16a34a", ls="--", lw=1, label="full reversion (z→0)")
    ax.axhline(halflvl, color="#9ca3af", ls=":", lw=1)
    ax.axvline(half, color="#dc2626", ls=":", lw=1, label=f"half-life ≈ {half}h")
    ax.set_title(f"B · Dislocation decays back to the pack ({len(P):,} events)", fontsize=11)
    ax.set_xlabel("hours after |z| crosses 1.5"); ax.set_ylabel("mean sign-folded z  (→0 = reverted)")
    ax.legend(fontsize=8); ax.grid(alpha=0.25); ax.set_ylim(0, mp[0] * 1.1)

    # C — reversion payoff by entry z
    fwd = np.full_like(Rz, np.nan); fwd[:-H] = Rz[H:] - Rz[:-H]
    side = -np.sign(Z)
    pnl = side * fwd
    xx = Z[:-H].ravel(); pp = pnl[:-H].ravel()
    m2 = np.isfinite(xx) & np.isfinite(pp); xx, pp = xx[m2], pp[m2]
    cen2, mu2 = [], []
    for b in range(1, len(bins)):
        sel = (xx >= bins[b - 1]) & (xx < bins[b])
        if sel.sum() > 100:
            cen2.append((bins[b - 1] + bins[b]) / 2); mu2.append(pp[sel].mean())
    ax = axs[1, 0]
    ax.axhline(0, color="#888", lw=0.7); ax.axvline(0, color="#888", lw=0.7)
    ax.bar(cen2, mu2, width=0.42, color=["#16a34a" if v >= 0 else "#dc2626" for v in mu2])
    ax.set_title(f"C · Mean reversion payoff over {H}h by entry z (bps, convergence-direction)", fontsize=11)
    ax.set_xlabel("entry z (σ)"); ax.set_ylabel("mean forward bps (good = positive)")
    ax.grid(alpha=0.25, axis="y")

    # D — autocorrelation: residual returns vs raw returns
    dr = np.diff(Rz, axis=0)
    lr = np.diff(np.log(close.to_numpy()), axis=0)
    lags = range(1, 25)

    def acf(M, L):
        a, b = M[:-L].ravel(), M[L:].ravel()
        mm = np.isfinite(a) & np.isfinite(b)
        return np.corrcoef(a[mm], b[mm])[0, 1]
    ac_r = [acf(dr, L) for L in lags]
    ac_p = [acf(lr, L) for L in lags]
    ax = axs[1, 1]
    ax.bar([l - 0.2 for l in lags], ac_r, width=0.4, color="#b91c1c", label="residual returns")
    ax.bar([l + 0.2 for l in lags], ac_p, width=0.4, color="#94a3b8", label="raw price returns")
    ax.axhline(0, color="#444", lw=0.7)
    ax.set_title(f"D · Return autocorrelation (lag-1 resid={ac_r[0]:+.2f} → reversion)", fontsize=11)
    ax.set_xlabel("lag (hours)"); ax.set_ylabel("autocorrelation"); ax.legend(fontsize=8); ax.grid(alpha=0.25)

    fig.suptitle(f"Crypto cross-sectional residuals MEAN-REVERT — {N} coins, {yrs:.1f}y historical",
                 fontsize=14)
    fig.tight_layout()
    out = pathlib.Path("research/figures"); out.mkdir(parents=True, exist_ok=True)
    path = out / "reversion_tendency.png"
    fig.savefig(path, dpi=110)
    print(f"saved {path}")
    print(f"A slope={slope:+.2f} (neg=reversion) · B half-life≈{half}h, {len(P):,} events · "
          f"D lag-1 resid acf={ac_r[0]:+.2f} vs raw {ac_p[0]:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
