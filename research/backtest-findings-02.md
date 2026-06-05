# Backtest Findings #2 — funding-credited carry (PARTIAL advance, not a clean GO)

_Run: `scripts/backtest_carry.py` + risk calc. Long XAUT spot / short xyz:GOLD perp
(delta-neutral), funding credited from real `xyz:GOLD` history. Modeled round-trip cost 23 bps._

## The funding pivot flipped the sign — the carry now clears cost.

**Always-on carry (hold the delta-neutral position, harvest funding):**

| window | net | %/yr | **Sharpe** | maxDD | funding APR | neg-funding bars |
|---|---|---|---|---|---|---|
| XAUT/Binance (~70d) | +20 bps | **+1.0%** | **0.26** | −1.0% | 5.0% | 11% |
| XAUT/Bitfinex (~5.5mo) | +300 bps | **+6.7%** | **0.66** | −1.7% | 8.8% | 15% |

Decomposition (Bitfinex): funding **+385** − basis-drift **−62** − cost **−23** = **+300 bps**.

## Verdict: the carry concept is validated, but it FAILS the Stage-3 gate.
- ✅ **Net-of-cost positive** (+1 to +6.7%/yr) — the first structure to clear the cost-hurdle at all.
- ✅ **Low drawdown** (−1.0% / −1.7%) — well inside the ≤10% gate.
- ❌ **Sharpe 0.26–0.66** — far below the **≥1.5** GO bar. Not a GO. Not ready to paper-trade.
- **Funding is the entire edge** — convergence *timing* added nothing (the timed variant still lost; see below), and intra-bar trading still whipsaws to 0% profitable seeds.

## Why Sharpe is low
Basis (spread) **volatility** dominates the variance while funding accrues as a slow drip; funding also goes **negative 11–15%** of bars (you pay). The MtM swings from basis moves swamp the steady carry → mediocre return/risk. Drawdown is small but the curve is noisy. Also window-dependent (1.0% vs 6.7%) on short history.

## Timed/convergence variant — still fails
z-entry=1.5, min_hold=48h, carry-direction only: funding cut the loss (Bitfinex −225→−69 bps; break-even ~23 bps) but stayed negative at modeled cost, and MC intrabar = 0% profitable. **Timing harvests less funding than holding; the naive z-score is the wrong tool here.**

## Pivot (ladder — to lift Sharpe toward 1.5)
1. **Re-parameterize → gate on FUNDING, not basis.** Hold when funding is positive/high; flatten when it turns negative (avoid the 11–15% you-pay bars). Directly harvests the real edge. *Cheapest next step.*
2. **Restructure → add the convexity overlay.** The carry is short the basis-widening tail; the long-gamma "manifold butterfly" exists precisely to cap that — cutting the bad-tail variance is the most direct Sharpe lift. (This is where deeper-tip / steer / hard-cut applies.)
3. **Diversify → multiple uncorrelated funding-carry legs** (the manifold book) → smoother aggregate Sharpe.

**Status: carry book concept proven net-of-cost & low-DD, but Sharpe < gate. Not GO. Next: funding-gated carry.**
