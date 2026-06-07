# Backtest Findings #20 — equal-weight pack mean beats market-cap-weighted (confirmed, keep equal-weight)

_Tested whether weighting the cross-sectional "pack mean" by market cap (proxied by trailing
$-volume) gives a cleaner residual than equal-weight. Both cross-sectional means (market level +
common factor) weighted; 5y 30-coin set, vol-scaled, screening model. `scripts/factor_weight_test.py`._

## Result — equal-weight wins clearly
| pack mean | Sharpe | ret%/yr | maxDD | Calmar | LUNA | FTX |
|---|---|---|---|---|---|---|
| **equal (current)** | **14.2** | 146 | **−4.3%** | **34** | +2265 | +4783 |
| cap-weighted | 9.8 | 155 | −13.1% | 12 | +3273 | +5075 |
| sqrt-cap | 12.5 | 143 | −5.8% | 25 | +911 | +5331 |

Cap-weighting: a hair more raw return but **3× the drawdown** (−13.1 vs −4.3%) and **−31% Sharpe** —
a clear risk-adjusted loss. sqrt-cap also worse than equal.

## Why cap-weighting fails
Cap-weighting makes the pack mean ≈ mostly BTC/ETH, which:
1. **Starves the majors of signal** — BTC can't deviate from a mean that *is* mostly BTC → residual
   signal concentrates into the small alts.
2. **Concentrates risk in the fat-tailed corner** — small alts have fatter idiosyncratic tails
   (gaps, near-delist moves), so the book tail blows out. And "small-alt vs BTC" is a more directional
   bet that reverts less cleanly than "small-alt vs its true peers."

## Verdict
Keep **equal-weight** pack mean. The sector-neutral step (findings-17) already captures the
legitimate "true peers" idea far more cleanly than cap-weighting a global mean. Another in-sample
signal tweak that confirms the current construction rather than improving it — reinforces that the
edge is on a robust plateau and the highest-value next step is live data, not more tuning.
