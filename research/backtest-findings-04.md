# Backtest Findings #4 — overlay doesn't lift Sharpe (and that was the wrong test)

_Run: `scripts/backtest_overlay.py`. Always-on carry + option-free long-gamma momentum
overlay on the same basis; swept overlay size × z_band. Cost 23 bps/flip._

## Result: every carry+overlay combination is WORSE than carry alone.

| | carry alone | best combined (z_band=3, size=0.25) |
|---|---|---|
| Binance ~70d | Sharpe **0.26**, net +20 | Sharpe −0.32, net −24 |
| Bitfinex ~5.5mo | Sharpe **0.66**, net +300 | Sharpe 0.09, net +38 |

Overlay *standalone* bleeds hard (Sharpe −5.7 to −11.5; net −178 to −2958) at every band.

## Why — and the reframe
1. **The basis mean-reverts; it doesn't trend.** Long-gamma momentum is the losing side of a mean-reverting series (confirmed by finding-01, where *reversion* was the gross-positive direction). So the overlay bleeds, and each flip pays 23 bps.
2. **No de-peg occurred in-sample.** The overlay is **tail insurance** against a basis blow-out / de-peg — and ~70d / 5.5mo contained no such event. A benign sample can only show the *premium* (bleed), never the *payoff*. **A backtest with no tail event is structurally biased against tail insurance.**
3. **I conflated two jobs.** The overlay's charter gate is *"calm-regime bleed ≤1%/month AND cuts de-peg-stress drawdown ≥50%"* — NOT "lift the carry's Sharpe." Asking it to raise Sharpe was the wrong test. (At small size / wide band its calm bleed ≈0.6%/mo — within budget; its protection is just unmeasurable here.)

## What this means for the Sharpe gate
The carry's Sharpe ceiling (~0.5) is set by **basis volatility while held**, and the overlay does not (and should not) fix that. Of the three levers to lift Sharpe, two are now falsified (funding-timing, convergence-timing) and the overlay is revealed as insurance, not alpha. **The one untested, mathematically-sound lever remains: DIVERSIFICATION.**
- A single carry at Sharpe ~0.5, replicated across **N uncorrelated** funding-carry legs, gives aggregate Sharpe ≈ 0.5·√N (≈1.5 at N≈9). This is the manifold/multi-leg book and the fractional-Kelly thesis.

## Pivot decision — two separate next steps
1. **Diversification (for the Sharpe gate):** build a basket of uncorrelated delta-neutral funding carries (gold + liquid crypto perps — easy to backfill with existing tools) and measure whether the **aggregate** Sharpe clears ≥1.5. This is the live question.
2. **De-peg stress test (for the overlay's own gate):** inject a synthetic basis blow-out and verify the overlay cuts the carry's stress-drawdown ≥50% at ≤1%/month calm bleed. Validates the overlay against the right gate.

Priority: **#1 diversification** — it's the actual path to the Sharpe gate.
