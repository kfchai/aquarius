# Backtest Findings #6 — robustness suite FAILS (diversification was hindsight; overlay broken)

_Runs: `scripts/diversify.py` (13 legs, walk-forward weighting) + `scripts/stress.py`
(synthetic correlated crisis). The decisive, no-hindsight tests._

## Diversification (13 legs: GOLD + 12 crypto perps, ~0.45y)
| weighting | Sharpe | gate 1.5 |
|---|---|---|
| **equal-weight (no hindsight)** | **0.47** | ❌ |
| inverse-vol (in-sample / hindsight) | 1.11 | ❌ |
| **walk-forward inverse-vol (out-of-sample)** | **~0** (fragile) | ❌ |

- **4 of 13 legs had NEGATIVE Sharpe** (APT −1.6, SOL −1.5, OP −0.95, XRP −0.34) — i.e. negative funding. You can't know which in advance.
- Adding legs *lowered* the hindsight basket (4-leg IV 1.65 → 13-leg IV 1.11): naive diversification pulls in losers.
- avg corr 0.11 (low) — so the mechanism is present, but the per-leg base Sharpe (~0.46) is too low and the negative legs drag it. **The earlier 1.65 was pure hindsight (cherry-picking winners after the fact).**
- (Naive walk-forward inverse-vol collapsed to ~0 — return-agnostic weighting over-concentrates on whichever leg's trailing vol momentarily craters. Fragile scheme; the honest robust floor is equal-weight = 0.47.)

## Stress test — overlay fails its OWN gate
Synthetic correlated crisis (all funding → −40% APR, basis −200 bps): carry-only crisis loss 94 bps.
**The overlay made it WORSE at every size** (size 1.0 → 140 bps, −50% worse; size 3 → 225, −139% worse)
and bled −0.6 to −3.7%/mo in calm. **Reason:** rolling-z momentum is the wrong signal for a sustained
trend — the rolling mean tracks the de-peg, so z never stays extreme; the overlay whipsaws and pays cost
instead of riding the move. The overlay as built does not work; it needs a real trend signal (Donchian /
level-breakout), not a z-score.

## Verdict
After 6 backtests, the funding-carry / convergence branch **does not clear the pre-registered Sharpe ≥ 1.5
gate out-of-sample.** It is a real but ~0.5-Sharpe edge; naive diversification doesn't fix it (hindsight only),
and the convexity overlay as implemented is broken. We are deep into the pivot ladder
(re-parameterize ✗, reselect ✗, restructure ✗).

## Two untested levers remain (then park, per the ladder)
1. **Return-aware allocation** (how real funding-farms actually work): each period, hold only legs with
   positive *trailing* funding, weight by trailing carry quality — drops the negative-carry legs OOS. This
   is the one lever that directly targets the "4/13 losers drag it" failure. Cheap to test.
2. **Proper trend overlay** (Donchian/level breakout instead of rolling-z) so the de-peg hedge actually
   rides the trend — re-run the stress.

**If return-aware allocation does not clear ~1.5 OOS, PARK this branch** with this evidence and reconsider
the approach (different instrument class, or accept a lower-Sharpe product and descope). Do not keep adding
epicycles.
