"""Robustness sweep (pre-live gate): vary each hyperparameter one-at-a-time and confirm the edge
sits on a BROAD PLATEAU, not a fragile peak. Honest shadow engine, 5y 30-coin set.

A healthy strategy keeps a high Sharpe across ±a wide range on every knob. If Sharpe only spikes at
the exact baseline value, that's overfitting — find it here, before risking money.

    python scripts/robustness_sweep.py
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.paper.shadow import ShadowConfig, run_shadow, PPY  # noqa: E402

HIST = pathlib.Path("data/history")
BASE = dict(z_entry=1.5, z_exit=0.3, z_stop=5.0, ema=168, zwin=168)
SWEEPS = {
    "z_entry": [1.25, 1.5, 1.75, 2.0, 2.5],
    "z_exit": [0.0, 0.3, 0.5, 0.75],
    "z_stop": [3.0, 4.0, 5.0, 6.0, 8.0],
    "ema": [84, 168, 336],
    "zwin": [84, 168, 336],
}


def load():
    close, tr, dv = {}, {}, {}
    for p in sorted(HIST.glob("long_*.parquet")):
        c = p.stem[len("long_"):]
        df = pd.read_parquet(p).sort_values("ts"); ts = df["ts"].to_numpy()
        close[c] = pd.Series(df["close"].to_numpy(), index=ts)
        tr[c] = pd.Series(((df["high"] - df["low"]) / df["close"] * 1e4).to_numpy(), index=ts)
        dv[c] = pd.Series((df["close"] * df["volume"]).to_numpy(), index=ts)
    return pd.DataFrame(close), pd.DataFrame(tr), pd.DataFrame(dv)


def run(close, tr, dv, **over):
    cfg = ShadowConfig(gross=1e5, leverage=1.0, vol_scaled=True, sector_neutral=True,
                       **{**BASE, **over})
    r = run_shadow(close, tr, dv, cfg)
    step = np.diff(np.concatenate([[0.0], r.equity]))
    sh = step.mean() / step.std() * np.sqrt(PPY) if step.std() > 0 else 0.0
    dd = (r.equity - np.maximum.accumulate(r.equity)).min()
    yrs = (r.index[-1] - r.index[0]) / 1000 / 86400 / 365
    return sh, r.equity[-1] / 1e5 * 100 / yrs, dd / 1e5 * 100


def main():
    close, tr, dv = load()
    base_sh, base_ret, base_dd = run(close, tr, dv)
    print(f"baseline (sector-neutral, vol-scaled, lev 1.0): Sharpe {base_sh:.2f}  "
          f"ret {base_ret:.0f}%/yr  maxDD {base_dd:.1f}%\n")

    results = {}
    fig, axs = plt.subplots(2, 3, figsize=(16, 9))
    for ax, (param, vals) in zip(axs.flat, SWEEPS.items()):
        print(f"=== {param} (baseline {BASE[param]}) ===")
        shs, rets, dds = [], [], []
        for v in vals:
            sh, ret, dd = run(close, tr, dv, **{param: v})
            shs.append(sh); rets.append(ret); dds.append(dd)
            tag = "  <- baseline" if v == BASE[param] else ""
            print(f"   {param}={v:<6} Sharpe {sh:5.2f}  ret {ret:4.0f}%/yr  maxDD {dd:5.1f}%{tag}")
        results[param] = (vals, shs)
        lo = min(shs) / base_sh
        print(f"   -> Sharpe range {min(shs):.1f}-{max(shs):.1f} "
              f"({'PLATEAU ok' if lo >= 0.6 else 'FRAGILE — dips <60% of baseline'})\n")
        ax.plot(vals, shs, "o-", color="#2563eb")
        ax.axhline(base_sh, color="#9ca3af", ls=":", lw=1)
        ax.axhline(base_sh * 0.6, color="#dc2626", ls=":", lw=1, label="60% of baseline")
        ax.axvline(BASE[param], color="#16a34a", ls="--", lw=1, label="baseline")
        ax.set_title(f"Sharpe vs {param}", fontsize=11)
        ax.set_xlabel(param); ax.set_ylabel("Sharpe"); ax.set_ylim(0, None)
        ax.legend(fontsize=7); ax.grid(alpha=0.3)
    axs.flat[-1].axis("off")
    fig.suptitle(f"Robustness sweep — baseline Sharpe {base_sh:.1f} (honest engine, 5y 30-coin)",
                 fontsize=13)
    fig.tight_layout()
    out = pathlib.Path("research/figures") / "robustness_sweep.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=108)
    print(f"saved {out}")
    worst = min(min(s) / base_sh for _, s in results.values())
    print(f"\nVERDICT: worst-case Sharpe across all sweeps = {worst:.0%} of baseline — "
          f"{'PLATEAU (robust, not overfit)' if worst >= 0.6 else 'check the fragile knob'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
