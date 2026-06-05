"""Mean-reversion convergence strategy on a spread series (in bps).

Hypothesis under test: a delta-neutral spread (wrapper-spread or cash-and-carry
basis) mean-reverts enough to clear the cost-hurdle. Enter when the z-score is
extreme, exit on reversion; a wide z-stop guards the divergence/de-peg tail.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MRParams:
    lookback: int = 168     # bars for rolling mean/std (1 week of hourly)
    z_entry: float = 2.0
    z_exit: float = 0.5
    z_stop: float = 4.0     # divergence stop — the de-peg / "tip deepens" guard
    max_hold: int = 0       # 0 = no time cap (steps)
    min_hold: int = 0       # don't exit before this many bars (unless stopped) — hold the carry
    side_filter: int = 0    # 0=both; +1=long-spread only; -1=short-spread only


def rolling_z(spread: np.ndarray, lookback: int) -> np.ndarray:
    s = pd.Series(np.asarray(spread, float))
    mean = s.rolling(lookback).mean()
    std = s.rolling(lookback).std(ddof=0)
    return ((s - mean) / std.replace(0.0, np.nan)).to_numpy()


def run_convergence(spread: np.ndarray, z: np.ndarray, params: MRParams,
                    cost_bps: float, funding=None):
    """Run the strategy. Returns (trades, step_pnl).

    side = -1: entered short (z high, bet spread falls); +1: long (z low, bet rises).
    For the basis structure, side=+1 means long-spot/short-perp → EARNS funding when the
    rate is positive; side=-1 (long perp) PAYS it. `funding` is the per-bar funding rate
    (hourly fraction) aligned to `spread`; while in position we accrue side*funding*1e4 bps.
    step_pnl[i] = mark-to-market bps that bar (drift + funding + entry/exit cost halves).
    """
    spread = np.asarray(spread, float)
    n = len(spread)
    step_pnl = np.zeros(n)
    has_funding = funding is not None
    if has_funding:
        funding = np.asarray(funding, float)
    trades: list[dict] = []
    pos = 0
    entry_i = 0
    entry_s = 0.0
    fund_acc = 0.0
    half_cost = cost_bps / 2.0

    for i in range(n):
        zi = z[i]
        if pos != 0:
            step_pnl[i] += pos * (spread[i] - spread[i - 1])  # mark-to-market vs prev bar
            if has_funding and not np.isnan(funding[i]):
                f = pos * funding[i] * 1e4  # short perp (pos=+1) earns positive funding
                step_pnl[i] += f
                fund_acc += f

        if np.isnan(zi):
            continue

        if pos == 0:
            want = -1 if zi >= params.z_entry else (1 if zi <= -params.z_entry else 0)
            if want != 0 and (params.side_filter == 0 or params.side_filter == want):
                pos = want
                entry_i = i
                entry_s = spread[i]
                fund_acc = 0.0
                step_pnl[i] -= half_cost  # entry cost
        else:
            hold = i - entry_i
            stopped = abs(zi) >= params.z_stop
            converged = abs(zi) <= params.z_exit
            timecap = bool(params.max_hold) and hold >= params.max_hold
            exit_now = stopped or ((converged or timecap) and hold >= params.min_hold)
            if exit_now:
                step_pnl[i] -= half_cost  # exit cost
                gross = pos * (spread[i] - entry_s)
                trades.append({
                    "entry_i": entry_i, "exit_i": i, "side": pos,
                    "entry_spread": entry_s, "exit_spread": spread[i],
                    "gross_bps": gross, "funding_bps": fund_acc,
                    "net_bps": gross + fund_acc - cost_bps,
                    "hold": hold, "stopped": stopped,
                })
                pos = 0
    return trades, step_pnl


@dataclass
class FundingGateParams:
    f_entry: float = 0.0   # enter when smoothed funding (per-hr fraction) > f_entry
    f_exit: float = 0.0    # exit when smoothed funding < f_exit
    smooth: int = 8        # rolling-mean bars to denoise funding
    min_hold: int = 0
    side: int = 1          # +1 = long-spot/short-perp (harvest positive funding)


def run_funding_gated(spread: np.ndarray, funding: np.ndarray,
                      params: FundingGateParams, cost_bps: float):
    """Harvest funding: hold the carry only while (smoothed) funding pays, flatten
    when it fades. The gate reads the funding LEVEL (slow), not the noisy spread —
    so it does not whipsaw intra-bar. Returns (trades, step_pnl, in_market_bars).
    """
    spread = np.asarray(spread, float)
    funding = np.asarray(funding, float)
    n = len(spread)
    step_pnl = np.zeros(n)
    fsm = pd.Series(funding).rolling(params.smooth, min_periods=1).mean().to_numpy()
    trades: list[dict] = []
    pos = 0
    entry_i = 0
    entry_s = 0.0
    fund_acc = 0.0
    in_mkt = 0
    half = cost_bps / 2.0

    for i in range(n):
        if pos != 0:
            step_pnl[i] += pos * (spread[i] - spread[i - 1])
            fb = pos * funding[i] * 1e4
            step_pnl[i] += fb
            fund_acc += fb
            in_mkt += 1
        if pos == 0:
            if fsm[i] > params.f_entry:
                pos = params.side
                entry_i = i
                entry_s = spread[i]
                fund_acc = 0.0
                step_pnl[i] -= half
        else:
            hold = i - entry_i
            if fsm[i] < params.f_exit and hold >= params.min_hold:
                step_pnl[i] -= half
                gross = pos * (spread[i] - entry_s)
                trades.append({
                    "entry_i": entry_i, "exit_i": i, "side": pos,
                    "gross_bps": gross, "funding_bps": fund_acc,
                    "net_bps": gross + fund_acc - cost_bps,
                    "hold": hold, "stopped": False,
                })
                pos = 0
    return trades, step_pnl, in_mkt


@dataclass
class OverlayParams:
    lookback: int = 168
    z_band: float = 2.5    # enter momentum when |z| > z_band (wide → rare → affordable)
    z_exit: float = 0.5    # flatten when |z| < z_exit


def run_breakout_overlay(spread: np.ndarray, params: OverlayParams, cost_bps: float):
    """Option-free synthetic LONG-GAMMA overlay on the spread (unit size).

    Momentum / reverse-grid: go WITH the move (long when z high, short when z low),
    flat in the tip zone. Profits when the spread TRENDS (de-peg / basis blow-out) —
    exactly the carry's bad tail — and bleeds (the 'tip') when it chops. Wide z_band
    keeps trades rare so the 23 bps round-trip doesn't eat it. Returns (step_pnl, flips).
    """
    z = rolling_z(spread, params.lookback)
    spread = np.asarray(spread, float)
    n = len(spread)
    pnl = np.zeros(n)
    pos = 0
    flips = 0
    half = cost_bps / 2.0
    for i in range(n):
        if pos != 0:
            pnl[i] += pos * (spread[i] - spread[i - 1])  # hold WITH the move
        zi = z[i]
        if np.isnan(zi):
            continue
        target = pos
        if pos == 0:
            if zi >= params.z_band:
                target = +1
            elif zi <= -params.z_band:
                target = -1
        else:
            if abs(zi) <= params.z_exit:
                target = 0
            elif zi >= params.z_band and pos < 0:
                target = +1
            elif zi <= -params.z_band and pos > 0:
                target = -1
        if target != pos:
            pnl[i] -= half * abs(target - pos)  # cost scales with size of the change
            pos = target
            flips += 1
    return pnl, flips


@dataclass
class DonchianParams:
    entry_n: int = 48        # breakout lookback (bars) — go WITH a move past the N-bar high/low
    exit_n: int = 12         # shorter exit channel — lock in trend profit when it stalls
    deadband_bps: float = 0  # "tip zone": no NEW entries within this distance of the centroid
    ref_n: int = 720         # long-run reference (the centroid / imaginary tip)


def run_donchian_gamma(price: np.ndarray, params: DonchianParams, cost_bps: float):
    """Fixed-reference breakout = proper synthetic LONG-GAMMA (the overlay done right).

    Go long when price breaks above the trailing N-bar high, short below the N-bar low;
    exit via a shorter channel. Unlike rolling-z, the reference does NOT chase the trend,
    so a sustained dislocation keeps you positioned (it RIDES de-pegs instead of whipsawing).
    Returns (trades, step_pnl). PnL in bps of price.
    """
    price = np.asarray(price, float)
    n = len(price)
    s = pd.Series(price)
    upper = s.rolling(params.entry_n).max().shift(1).to_numpy()
    lower = s.rolling(params.entry_n).min().shift(1).to_numpy()
    ex_lo = s.rolling(params.exit_n).min().shift(1).to_numpy()
    ex_up = s.rolling(params.exit_n).max().shift(1).to_numpy()
    longref = s.rolling(params.ref_n, min_periods=1).mean().to_numpy()  # centroid
    step_pnl = np.zeros(n)
    trades: list[dict] = []
    pos = 0
    entry_px = 0.0
    entry_i = 0
    half = cost_bps / 2.0
    for i in range(n):
        if pos != 0:
            step_pnl[i] += pos * (price[i] - price[i - 1]) / price[i - 1] * 1e4
        if np.isnan(upper[i]):
            continue
        target = pos
        if pos == 0:
            outside_tip = (params.deadband_bps <= 0 or
                           abs(price[i] - longref[i]) / longref[i] * 1e4 > params.deadband_bps)
            if outside_tip and price[i] > upper[i]:
                target = +1
            elif outside_tip and price[i] < lower[i]:
                target = -1
        elif pos > 0:
            if price[i] < ex_lo[i]:
                target = 0
        else:
            if price[i] > ex_up[i]:
                target = 0
        if target != pos:
            step_pnl[i] -= half * abs(target - pos)
            if pos != 0:
                gross = pos * (price[i] - entry_px) / entry_px * 1e4
                trades.append({"entry_i": entry_i, "exit_i": i, "side": pos,
                               "gross_bps": gross, "net_bps": gross - cost_bps,
                               "hold": i - entry_i})
            if target != 0:
                entry_px = price[i]
                entry_i = i
            pos = target
    return trades, step_pnl


def run_gamma_additive(series: np.ndarray, params: DonchianParams, cost_bps: float):
    """Long-gamma on an ADDITIVE series already in bps (e.g. a manifold residual that
    oscillates around ~0). Same tip-zone Donchian logic, but P&L = pos*delta(series)
    (no division — the series crosses zero). Deadband is distance from the rolling
    centroid. Returns (trades, step_pnl)."""
    series = np.asarray(series, float)
    n = len(series)
    s = pd.Series(series)
    upper = s.rolling(params.entry_n).max().shift(1).to_numpy()
    lower = s.rolling(params.entry_n).min().shift(1).to_numpy()
    ex_lo = s.rolling(params.exit_n).min().shift(1).to_numpy()
    ex_up = s.rolling(params.exit_n).max().shift(1).to_numpy()
    centroid = s.rolling(params.ref_n, min_periods=1).mean().to_numpy()
    step_pnl = np.zeros(n)
    trades: list[dict] = []
    pos = 0
    entry = 0.0
    entry_i = 0
    half = cost_bps / 2.0
    for i in range(n):
        if pos != 0:
            step_pnl[i] += pos * (series[i] - series[i - 1])
        if np.isnan(upper[i]):
            continue
        target = pos
        if pos == 0:
            outside = (params.deadband_bps <= 0 or abs(series[i] - centroid[i]) > params.deadband_bps)
            if outside and series[i] > upper[i]:
                target = +1
            elif outside and series[i] < lower[i]:
                target = -1
        elif pos > 0:
            if series[i] < ex_lo[i]:
                target = 0
        else:
            if series[i] > ex_up[i]:
                target = 0
        if target != pos:
            step_pnl[i] -= half * abs(target - pos)
            if pos != 0:
                g = pos * (series[i] - entry)
                trades.append({"entry_i": entry_i, "exit_i": i, "side": pos,
                               "gross_bps": g, "net_bps": g - cost_bps, "hold": i - entry_i})
            if target != 0:
                entry = series[i]
                entry_i = i
            pos = target
    return trades, step_pnl
