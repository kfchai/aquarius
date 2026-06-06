# Backtest Findings #17 — sector-neutral residuals beat single-factor (cleaner idiosyncratic = better reversion)

_Signal-quality test (direction #1). Compared three residual constructions on the 5y 30-coin set,
vol-scaled, screening model (`scripts/factor_test.py`). Demeaning against more common structure
isolates the truly idiosyncratic dislocation — the part that actually reverts._

## Result
| residual | Sharpe | ret%/yr | maxDD | Calmar | LUNA | FTX |
|---|---|---|---|---|---|---|
| single (current — one common factor) | 14.2 | 146 | −4.3% | 34.0 | +$2,265 | +$4,783 |
| **sector-neutral (causal)** | **15.2** | 134 | **−3.4%** | **39.4** | **+$3,260** | **+$5,710** |
| pca-2 (full-sample hindsight ceiling) | 15.7 | 140 | −4.3% | 32.6 | +$4,369 | +$3,817 |

## Reading
- **Sector-neutral: +7% Sharpe, −21% maxDD, +16% Calmar, better through BOTH crises** — and it's
  CAUSAL (uses only the time-t cross-section), so directly tradeable. The lower raw return (134 vs
  146) is just the lower risk point; at equal risk it returns ~169%/yr (>146).
- **Why:** demeaning *within* sectors removes sector ROTATIONS (which trend, don't revert) →
  isolates the idiosyncratic move that snaps back. Stops betting "SOL vs BTC" (cross-sector, can
  diverge for real reasons); only bets "SOL vs its true peers."
- **PCA-2 hindsight (Sharpe 15.7)** confirms genuine multi-factor signal; sector captures +7 of the
  +10% ceiling, causally and simply.

## Caveats
- Screening model (flat 20bps) — confirm it holds in the honest shadow engine before default.
- Hand-labeled sectors are a judgment call (mild overfitting surface).
- 5y survivor data.

## Sectors used (30-coin set)
SoV/pay: BTC LTC XRP XLM ETC DOGE · L1: ETH SOL BNB AVAX NEAR ADA DOT ATOM ALGO ICP HBAR EGLD FLOW ·
DeFi: UNI AAVE CRV INJ RUNE · Infra: LINK GRT FIL · Gaming: SAND MANA AXS.

## HONEST-ENGINE confirmation (more modest than screening)
On the shadow engine (full cost stack), 5y 30-coin, vol-scaled lev-1.0:
| | Sharpe | ret%/yr | maxDD |
|---|---|---|---|
| single | 8.91 | 74 | −5.0% |
| sector | **9.28** | 66 | **−4.5%** |
Real benefit = **+4% Sharpe, −10% maxDD, ~FLAT Calmar** (14.7 vs 14.8) — smaller because the
sector residuals are lower-amplitude (more variance removed), so fixed costs eat proportionally
more. A smoother ride with a smaller tail, but not a dramatic win; adds a hand-labeled-sector
overfitting surface. Kept as default (`sector_neutral` toggle) since higher Sharpe + smaller tail
fits the steady/capped-tail objective.

## Verdict
Adopt sector-neutral residuals (honest-engine confirmed: mild +4% Sharpe / smaller tail). A causal rolling-PCA could chase
the extra ~3% to the hindsight ceiling, but adds complexity + overfitting risk — sector gets most of
it simply. Next signal idea after this: multi-horizon blend + funding co-signal.
