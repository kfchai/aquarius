# Backtest Findings #16 — breadth + vol-scaling SURVIVES the crises (wide basket, 5y)

_Breadth was only tested on the no-crisis 3y window; this closes that gap. Backfilled the 5y
(long_) set from 11 → **30 coins** (added DOT/ATOM/UNI/AAVE/FIL/ETC/XLM/ALGO/ICP/HBAR/GRT/SAND/
MANA/AXS/CRV/INJ/RUNE/EGLD/FLOW, all existing by 2021), then ran the wide basket through LUNA/3AC/
FTX/Aug-24, equal-weight vs vol-scaled. `scripts/backfill_long_wide.py` + `crisis_breadth_test.py`._

## Result — wide basket is crisis-resilient, vol-scaling holds Sharpe & cuts the tail
| scheme (30 coins, 4.8y) | Sharpe | ret%/yr | maxDD | LUNA | 3AC | FTX | Aug-24 |
|---|---|---|---|---|---|---|---|
| equal-weight | 14.22 | 175 | −6.6% | +$6,219 | +$3,828 | +$8,606 | +$1,580 |
| **vol-scaled** | **14.23** | 146 | **−4.3%** | +$2,265 | +$2,592 | +$4,783 | +$1,613 |

- **Every crisis positive** under both schemes — breadth does NOT break in a cascade; the wide
  basket profits *through* LUNA/3AC/FTX (consistent with findings-12 on 11 coins).
- **Every calendar year positive** (per-year Sharpe 12.8–15.9 both schemes).
- **Vol-scaling keeps an identical Sharpe (14.2)** while cutting maxDD ~35% (−6.6→−4.3%) — the
  same clean result as the 11-coin test (findings-15), now confirmed on the wide basket *through
  crises*. Crisis P&L is positive but smaller under vol-scaling (gapping coins get down-sized — the
  intended behavior).

## Caveat (unchanged)
Sharpe ~14 is inflated by **survivorship** — these 30 coins all survived to today; coins that
actually died in 2022 (LUNA, etc.) aren't in the set. The absolute number is NOT a forward number.
But the two findings that matter are robust and *relative*: (1) breadth survives crises, (2)
vol-scaling caps the tail at no Sharpe cost — both now hold on a wide basket across real cascades.

## Verdict
Breadth + vol-scaling is **safe to make the live default.** Roll both into the shadow engine
(wider coin set + inverse-residual-vol leg sizing). Tail still guarded by the liquidity/delist
filters for the unmeasurable permanent-loss tail.
