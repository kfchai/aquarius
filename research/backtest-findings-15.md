# Backtest Findings #15 — volatility-scaled sizing caps the tail WITHOUT compromising the edge

_Tested risk-management lever (B) from the stop-loss discussion: size each leg ∝ 1/(trailing
residual vol) instead of equal $ notional, so jumpy/gap-prone coins get less capital and contribute
~equal risk. `scripts/volscale_test.py`, 5y 11-coin set (incl. LUNA/3AC/FTX), causal vol (trailing,
capped [1/3×, 3×]), $100k gross, 20bps cost._

## Result — same Sharpe, smaller tail
| scheme | Sharpe | ret%/yr | maxDD | worst trade | LUNA | FTX |
|---|---|---|---|---|---|---|
| equal-weight | 8.88 | 144 | −8.8% | −$2,958 | +$6,112 | +$4,345 |
| **vol-scaled** | **8.88** | 124 | **−5.6%** | **−$2,138** | +$2,175 | +$1,909 |

vol-scaled vs equal: **Sharpe −0%**, return −13%, **worst-trade −28%**, **maxDD −36%**, **Calmar +36%**.

## Reading
- **Sharpe is identical** → the edge *per unit risk* is fully preserved; vol-scaling doesn't touch the
  signal or exit, only the dollar size of each leg.
- **Tail shrinks materially**: maxDD −36%, worst single trade −28%, and the per-trade P&L left tail
  visibly pulls in (research/figures/volscale_compare.png panel C).
- The 13% return give-up is just *running less risk* — and since Sharpe held, **return-per-drawdown
  (Calmar) improves ~36%.** Sized to the same drawdown budget, vol-scaling delivers MORE return with
  the same tail. This is the textbook risk-parity outcome.
- Crises stay positive (LUNA/FTX) but smaller — correct, because the coins gapping hardest during a
  cascade are exactly the ones vol-scaling down-sizes.

## Verdict
Confirmed: vol-scaled (inverse-residual-vol) sizing is a clean, gap-resistant way to cap the loss
tail with **zero edge compromise** (Sharpe unchanged). Highest-confidence of the stop-loss-handling
levers. Recommended as the default sizing for the live book (alongside breadth + a small long-gamma
overlay for the residual tail). Caveat: tested in-sample on survivor coins; the real permanent-loss
tail (delist/rug) is still handled by the liquidity/delist guards, not by sizing.
