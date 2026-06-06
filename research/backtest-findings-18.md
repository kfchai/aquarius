# Backtest Findings #18 — long-gamma overlay NOT worth it (the tail is already capped)

_Tested the last unused tail lever (direction #3): a per-coin long-gamma breakout sleeve
(`run_gamma_additive`) netted onto the core reversal book as a tail hedge. Sweep λ (overlay
fraction) on the 5y 30-coin set, sector-neutral + vol-scaled. `scripts/overlay_test.py`._

## Result — overlay only costs return, barely touches the tail
| λ (overlay) | Sharpe | ret%/yr | maxDD | worst bar | LUNA | FTX |
|---|---|---|---|---|---|---|
| **0.00** | **15.23** | 134 | −3.4% | −1466 | +3260 | +5710 |
| 0.10 | 14.84 | 127 | −3.2% | −1424 | 2767 | 5203 |
| 0.20 | 14.33 | 119 | −3.1% | −1381 | 2275 | 4696 |
| 0.35 | 13.31 | 108 | −3.1% | −1317 | 1537 | 3936 |
| 0.50 | 12.00 | 97 | −3.2% | −1253 | 798 | 3177 |

Overlay-alone return = **−75%/yr** (the insurance premium).

## Why it fails (and why that's good news)
1. **Bleeds −75%/yr standalone** — huge premium.
2. **Cuts Sharpe monotonically** (15.2 → 12.0) — pure drag.
3. **maxDD barely improves** (−3.4 → −3.1%, 0.3pp) — because the tail is **already tiny**:
   diversification + vol-scaling + tail guards already capped it. Nothing left to hedge.
4. **Crises get WORSE** (LUNA 3260→798, FTX 5710→3177) — the core already PROFITS in cascades
   (liquidity provider paid in stress); the overlay bleeds through the crisis chop and drags it down.

## Verdict — do NOT add the overlay
The overlay is built to hedge a fat-tailed book; this book isn't fat-tailed anymore. The cheap tail
tools (diversification = free Sharpe, vol-scaling = same Sharpe, guards = unmeasured-tail insurance)
already do the job, so the expensive long-gamma insurance is redundant — it only sacrifices return
and crisis P&L. **Closes the butterfly / long-gamma chapter:** a sound original instinct, but a
properly diversified + vol-scaled short-gamma core leaves no room for a long-gamma hedge to pay.

## Remaining directions
Robustness sweep (confirm the stack sits on a plateau), maker execution (live, net-return), or
multi-horizon + funding co-signal (more alpha, more overfit risk). Meta: highest-value step is now
LIVE forward data, not more in-sample tweaks.
