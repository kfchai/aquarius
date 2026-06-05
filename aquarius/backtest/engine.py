"""Backtest engine: score a convergence run net of cost, on raw closes and on
Monte-Carlo intra-bar paths.
"""

from __future__ import annotations

import numpy as np

from .pathsim import brownian_bridge_path, estimate_sigma_per_step
from .strategy import (
    FundingGateParams, MRParams, rolling_z, run_convergence, run_funding_gated,
)


def _metrics(trades: list[dict], step_pnl: np.ndarray, periods_per_year: float) -> dict:
    eq = np.cumsum(step_pnl)
    dd = eq - np.maximum.accumulate(np.maximum(eq, 0.0))
    nz = step_pnl[step_pnl != 0.0]
    sharpe = (
        float(step_pnl.mean() / step_pnl.std(ddof=1) * np.sqrt(periods_per_year))
        if step_pnl.std(ddof=1) > 0 else float("nan")
    )
    net = np.array([t["net_bps"] for t in trades]) if trades else np.array([])
    return {
        "n_trades": len(trades),
        "net_bps_total": float(net.sum()) if trades else 0.0,
        "gross_bps_total": float(sum(t["gross_bps"] for t in trades)),
        "avg_net_per_trade": float(net.mean()) if trades else float("nan"),
        "win_rate": float((net > 0).mean()) if trades else float("nan"),
        "avg_hold_bars": float(np.mean([t["hold"] for t in trades])) if trades else float("nan"),
        "n_stops": int(sum(t["stopped"] for t in trades)),
        "sharpe_ann": sharpe,
        "max_dd_bps": float(dd.min()) if len(dd) else 0.0,
        "equity_bps": float(eq[-1]) if len(eq) else 0.0,
    }


def run_raw(spread: np.ndarray, params: MRParams, cost_bps: float, ppy: float,
            funding=None) -> dict:
    z = rolling_z(spread, params.lookback)
    trades, step_pnl = run_convergence(spread, z, params, cost_bps, funding)
    m = _metrics(trades, step_pnl, ppy)
    m["funding_bps_total"] = float(sum(t.get("funding_bps", 0.0) for t in trades))
    return m


def run_montecarlo(
    spread_closes: np.ndarray, params: MRParams, cost_bps: float,
    bars_per_year: float, substeps: int = 12, n_seeds: int = 50,
    sigma_mult: float = 1.0, seed0: int = 0, funding=None,
) -> dict:
    """Run the strategy over n_seeds synthetic intra-bar paths; summarize the
    net-PnL distribution. Lookback is scaled to fine resolution. Funding (per real
    bar) is spread evenly across that bar's substeps so it accrues per wall-clock hour.
    """
    sigma = estimate_sigma_per_step(spread_closes, substeps, sigma_mult)
    fine_params = MRParams(
        lookback=params.lookback * substeps,
        z_entry=params.z_entry, z_exit=params.z_exit, z_stop=params.z_stop,
        max_hold=params.max_hold * substeps, min_hold=params.min_hold * substeps,
        side_filter=params.side_filter,
    )
    fine_funding = None
    if funding is not None:
        funding = np.asarray(funding, float)
        parts = [np.repeat(funding[i] / substeps, substeps) for i in range(len(spread_closes) - 1)]
        parts.append(np.array([0.0]))
        fine_funding = np.concatenate(parts)
    ppy = bars_per_year * substeps
    nets, sharpes, dds = [], [], []
    for s in range(n_seeds):
        rng = np.random.default_rng(seed0 + s)
        fine = brownian_bridge_path(spread_closes, substeps, sigma, rng)
        z = rolling_z(fine, fine_params.lookback)
        trades, step_pnl = run_convergence(fine, z, fine_params, cost_bps, fine_funding)
        m = _metrics(trades, step_pnl, ppy)
        nets.append(m["net_bps_total"])
        sharpes.append(m["sharpe_ann"])
        dds.append(m["max_dd_bps"])
    nets = np.array(nets)
    return {
        "n_seeds": n_seeds, "substeps": substeps, "sigma_per_step": sigma,
        "net_bps_median": float(np.median(nets)),
        "net_bps_p25": float(np.percentile(nets, 25)),
        "net_bps_p75": float(np.percentile(nets, 75)),
        "frac_seeds_profitable": float((nets > 0).mean()),
        "sharpe_ann_median": float(np.nanmedian(sharpes)),
        "max_dd_bps_median": float(np.median(dds)),
    }


def run_funding_gated_scored(spread, funding, params: FundingGateParams,
                             cost_bps: float, ppy: float) -> dict:
    trades, step_pnl, in_mkt = run_funding_gated(spread, funding, params, cost_bps)
    m = _metrics(trades, step_pnl, ppy)
    m["funding_bps_total"] = float(sum(t.get("funding_bps", 0.0) for t in trades))
    m["time_in_market"] = in_mkt / len(spread) if len(spread) else 0.0
    return m


def spread_distribution(spread: np.ndarray, cost_bps: float, lookback: int) -> dict:
    """How the deviation compares to the cost-hurdle — the core falsification check."""
    z = rolling_z(spread, lookback)
    s = np.asarray(spread, float)
    mean = np.nanmean(s)
    dev = np.abs(s - mean)
    valid = ~np.isnan(z)
    return {
        "spread_mean_bps": float(mean),
        "spread_std_bps": float(np.nanstd(s)),
        "abs_dev_p50_bps": float(np.nanpercentile(dev, 50)),
        "abs_dev_p95_bps": float(np.nanpercentile(dev, 95)),
        "frac_dev_gt_cost": float((dev[valid] > cost_bps).mean()) if valid.any() else float("nan"),
    }
