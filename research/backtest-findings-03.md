# Backtest Findings #3 — funding-gating REJECTED (trading cost dominates)

_Run: `scripts/backtest_funding_gated.py`. Hold long-spot/short-perp only while
smoothed funding pays; sweep entry/exit thresholds (APR). Cost 23 bps round-trip._

## Result: every gated config is WORSE than just holding.

| config | Binance net (Sharpe) | Bitfinex net (Sharpe) | trades |
|---|---|---|---|
| **always-on (hold)** | **+31 (0.41)** | **+311 (0.68)** | 0 |
| gate >0% / <0% | −299 (−4.02) | −899 (−2.12) | 16 / 54 |
| gate >5% / <0% | −224 (−3.14) | −278 (−0.66) | 10 / 30 |
| gate >10% / <3% | −83 (−1.35) | −153 (−0.39) | 8 / 26 |

## Why: the cure costs more than the disease.
Negative funding is small (~5–9% APR × 11–15% of bars ≈ tens of bps avoided over the window).
But getting in/out to dodge it costs **23 bps per round trip × many trades** (54 trades ≈ 1242 bps).
**At 23 bps round-trip, you cannot afford to trade — buy-and-hold dominates any timing.** The same
cost wall that killed convergence-timing (#1) kills funding-timing (#3).

## What this nails down
1. **Best carry = always-on buy-and-hold**, Sharpe **0.41–0.68** — still **below the ≥1.5 gate.**
2. For buy-and-hold the entry cost is one-off, so **Sharpe is ~cost-independent** → cheaper execution
   will NOT lift it. The Sharpe ceiling is **basis (spread) volatility while held**, nothing else.
3. Therefore the only levers that can clear the Sharpe gate are ones that **cut basis-MtM variance**:
   - **Convexity overlay** — cap the basis-widening tail (long-gamma "manifold butterfly"). *Now the
     necessary next step, not optional.*
   - **Diversification** — many uncorrelated carry legs → smoother aggregate.

## Pivot decision
Funding-timing and convergence-timing are both **rejected** (cost-dominated). The backtests have
empirically driven us to the two-book design: **always-on carry + convexity overlay.** Next build:
backtest the carry **with a synthetic long-gamma overlay** that caps the basis-widening drawdown, and
measure whether carry+overlay reaches Sharpe ≥ 1.5.
