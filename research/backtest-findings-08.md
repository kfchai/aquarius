# Backtest Findings #8 — multi-axis butterfly does NOT produce steady flow (corrects #7)

_Run: `scripts/butterfly_basket.py`. Tip-zone Donchian long-gamma across 5 stablecoin axes
(USDC, TUSD, FDUSD, BUSD, USDP), up to 4.4y each, multiple real de-peg events. Cost 2 bps._

## Result: the basket bleeds. The single-USDC success was unrepresentative.
| axis | net bps | events>50bps | best | window |
|---|---|---|---|---|
| **USDC** | **+454** | 1 | +580 | Mar-2023 clean slow de-peg |
| TUSD | −1058 | 3 | +155 | noisy; small wins < bleed |
| FDUSD | −602 | 0 | **+18** | **missed its Apr-2025 →0.87 wick** |
| BUSD | −1 | 0 | +17 | flat, short window |
| USDP | −1555 | 0 | −15 | perpetual micro-noise, pure bleed |
| **BASKET** | **−2761 (−6.2%/yr)** | 4 total | — | **skew −1.6, payoff/bleed 0.3×** |

Only USDC was net-positive. Total event payoff +1257 vs bleed −4004 bps. **Negative skew** — the opposite of what a long-gamma book should show.

## Three failure modes (all honest, all important)
1. **Noisy pegs bleed through a fixed deadband.** USDP/TUSD wiggle around 1.0 enough to keep triggering and whipsawing. The 30-bps deadband tuned on (unusually calm) USDC doesn't generalize.
2. **Fast wicks are MISSED.** FDUSD fell to 0.87 in *hours* and snapped back — the breakout rule entered late and exited into the reversal (+18 bps on a 1300-bps move). **Synthetic (option-free) gamma can only capture *sustained* moves, not instantaneous jumps — that is the structural cost of going option-free, now measured.**
3. **Clean, slow, large de-pegs (USDC-type) are RARE.** The one case the rule loves happens maybe once every couple of years per instrument.

## Verdict
The butterfly **core mechanic captures a clean slow dislocation** (USDC, confirmed in #7) **but does NOT produce steady positive flow across instruments/events** — it bleeds on noisy pegs and misses fast wicks. As a *standalone* strategy it fails. As *insurance* (its charter role) the premium is steep (~−6%/yr), and we **cannot cleanly test the combined book** because the carry legs (perps, data from Dec-2025) and the de-pegging instruments (stablecoins, events in 2023/2025) **live on different instruments and windows — they don't overlap.**

## Where the whole POC stands (honest)
Both books individually fall short of the Sharpe ≥1.5 gate: carry ~0.5; butterfly bleeds standalone, captures only rare clean dislocations, and can't be combined with the carry on current data. We are at the **park-and-rethink** rung of the ladder.

## Options
1. **Park** the gold/funding-carry/stablecoin branch with this evidence (disciplined default).
2. **Pivot to LSTs (e.g. stETH/ETH)** — the one class where a *carry* (staking yield) and a real *de-peg tail* coexist on the SAME asset, which is what the two-book design actually needs. Requires on-chain data (bigger lift).
3. **Descope** to an opportunistic "clean-de-peg sniper" (USDC-type events only) — real but rare, not a steady business.
