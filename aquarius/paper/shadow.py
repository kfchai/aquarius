"""Shadow-live engine (Stage 5) — runs the validated cross-sectional reversal strategy on real
hourly data, simulates honest fills, tracks delta-neutrality and a $ equity curve, and SENDS NO
ORDERS. Deterministic given the data, so a live hourly loop just appends the newest bar and re-runs.

Mirrors the backtest exactly: residual = idiosyncratic deviation from the equal-weight log-basket
(EWMA-detrended, cross-sectionally demeaned, bps), z-scored; enter side=-sign(z) at |z|>=z_entry,
exit at |z|<=z_exit or stop at |z|>=z_stop; decisions use the PRIOR bar's z (1-bar lag, no same-bar
look-ahead). Cost per side = (base + k_vol*bar_range_bps)/2 + K*sqrt(order/$vol); carry charged while
held. P&L is residual-based (= long coin vs equal-weight basket), identical to honest_fill.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PPY = 24 * 365


@dataclass
class ShadowConfig:
    ema: int = 168
    zwin: int = 168
    z_entry: float = 1.5
    z_exit: float = 0.3
    z_stop: float = 5.0
    base_bps: float = 10.0
    k_vol: float = 0.10
    k_impact: float = 100.0      # impact bps = K*sqrt(participation)
    carry_annual: float = 20.0   # %/yr holding drag (funding/borrow), pessimistic
    gross: float = 100_000.0     # total gross $ across legs (equal-weight)
    # --- tail guards (findings-13: thin-coin idiosyncratic risk the z-stop alone misses) ---
    max_leg_loss_bps: float = 400.0    # hard per-leg MtM stop on adverse residual move from entry
    min_dollar_vol: float = 250_000.0  # liquidity floor: trailing-median hourly $vol to trade a coin
    liq_window: int = 168              # bars for the trailing liquidity median
    stale_bars: int = 12               # identical-close bars -> treat as halted/delisted, force-exit
    rebalance_bps_per_bar: float = 0.05  # hedge-rebalance drag while held (deferred cost, now charged)


@dataclass
class Position:
    side: int
    entry_resid: float
    entry_ts: int
    entry_z: float
    entry_cost_bps: float = 0.0   # slippage+fees+impact paid on the way in (for net P&L)


@dataclass
class ShadowResult:
    equity: np.ndarray            # cumulative net $ per bar
    net_delta: np.ndarray         # signed $ exposure per bar (neutrality monitor)
    index: np.ndarray             # ts (ms)
    trades: list                  # closed trades
    positions: dict               # final open positions {coin: Position}
    resid_last: dict              # latest residual per coin (bps)
    z_last: dict                  # latest z per coin


def residualize(close: pd.DataFrame, cfg: ShadowConfig):
    close = close.dropna()
    lp = np.log(close)
    ratio = lp.sub(lp.mean(axis=1), axis=0)
    dev = (ratio - ratio.ewm(span=cfg.ema, min_periods=24).mean()) * 1e4
    resid = dev.sub(dev.mean(axis=1), axis=0).dropna()
    z = (resid / resid.rolling(cfg.zwin, min_periods=24).std()).reindex(resid.index)
    return resid, z


def run_shadow(close: pd.DataFrame, tr: pd.DataFrame, dvol: pd.DataFrame,
               cfg: ShadowConfig) -> ShadowResult:
    resid, z = residualize(close, cfg)
    coins = list(resid.columns)
    n = len(resid)
    notional = cfg.gross / len(coins)               # equal-weight $/leg
    carry_bar = cfg.carry_annual / 100 * 1e4 / PPY  # bps per bar
    idx = resid.index.to_numpy()

    R = {c: resid[c].to_numpy() for c in coins}
    Z = {c: z[c].to_numpy() for c in coins}
    TR = {c: np.nan_to_num(tr.reindex(resid.index)[c].to_numpy()) for c in coins}
    DV = {c: dvol.reindex(resid.index)[c].fillna(dvol[c].median()).to_numpy() for c in coins}
    # liquidity floor: trailing-median hourly $vol must clear min_dollar_vol to be tradeable
    LIQ = {c: (dvol.reindex(resid.index)[c].rolling(cfg.liq_window, min_periods=24).median()
               .to_numpy() >= cfg.min_dollar_vol) for c in coins}
    # staleness: consecutive identical-close bars -> halted/delisted
    cl = close.reindex(resid.index)
    STALE = {c: (cl[c].diff() == 0).astype(int).groupby((cl[c].diff() != 0).cumsum()).cumcount()
             .to_numpy() for c in coins}

    pos: dict[str, Position] = {}
    equity = np.zeros(n)
    netd = np.zeros(n)
    trades: list = []
    cum = 0.0

    def side_cost_bps(c, i):
        part = min(notional / DV[c][i], 1.0) if DV[c][i] > 0 else 1.0
        return (cfg.base_bps + cfg.k_vol * TR[c][i]) / 2 + cfg.k_impact * np.sqrt(part)  # bps/side

    def side_cost(c, i):
        return side_cost_bps(c, i) / 1e4 * notional   # $ per side

    def close_leg(c, i, p, ri, zdec, reason):
        nonlocal_pnl = -side_cost(c, i)
        hold_bars = int((idx[i] - p.entry_ts) / 3_600_000)
        # realized round-trip cost in bps: entry + exit slippage/fees/impact + holding carry+rebalance
        cost_bps = (p.entry_cost_bps + side_cost_bps(c, i)
                    + (carry_bar + cfg.rebalance_bps_per_bar) * hold_bars)
        gross_bps = p.side * (ri - p.entry_resid)
        trades.append({
            "coin": c, "side": p.side, "entry_ts": p.entry_ts, "exit_ts": int(idx[i]),
            "entry_z": p.entry_z, "exit_z": float(zdec) if not np.isnan(zdec) else 0.0,
            "gross_bps": gross_bps, "cost_bps": cost_bps, "net_bps": gross_bps - cost_bps,
            "reason": reason, "hold_bars": hold_bars,
        })
        del pos[c]
        return nonlocal_pnl

    for i in range(n):
        bar_pnl = 0.0
        for c in coins:
            ri, rp = R[c][i], R[c][i - 1] if i > 0 else R[c][i]
            zi = Z[c][i]
            zdec = Z[c][i - 1] if i > 0 else np.nan   # 1-bar lag decision
            tradeable = LIQ[c][i] and STALE[c][i] < cfg.stale_bars
            p = pos.get(c)
            if p is not None:
                bar_pnl += (p.side * (ri - rp) - carry_bar - cfg.rebalance_bps_per_bar) / 1e4 * notional
                loss_bps = p.side * (p.entry_resid - ri)        # >0 = losing
                if not LIQ[c][i]:
                    reason = "liquidity"
                elif STALE[c][i] >= cfg.stale_bars:
                    reason = "delist"
                elif loss_bps >= cfg.max_leg_loss_bps:
                    reason = "leg_stop"
                elif not np.isnan(zdec) and abs(zdec) >= cfg.z_stop:
                    reason = "z_stop"
                elif not np.isnan(zdec) and abs(zdec) <= cfg.z_exit:
                    reason = "converge"
                else:
                    reason = None
                if reason:
                    bar_pnl += close_leg(c, i, p, ri, zdec, reason)
            elif not np.isnan(zdec) and not np.isnan(zi) and tradeable and abs(zdec) >= cfg.z_entry:
                side = -1 if zdec > 0 else 1
                bar_pnl -= side_cost(c, i)
                pos[c] = Position(side, ri, int(idx[i]), float(zdec), side_cost_bps(c, i))
        cum += bar_pnl
        equity[i] = cum
        netd[i] = sum(pp.side for pp in pos.values()) * notional

    return ShadowResult(equity, netd, idx, trades, dict(pos),
                        {c: float(R[c][-1]) for c in coins},
                        {c: float(Z[c][-1]) for c in coins})
