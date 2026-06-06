# Backtest Findings #19 — robustness sweep: trading rules are a PLATEAU (not overfit); windows left conservative on purpose

_Pre-live gate. One-at-a-time sweep of every hyperparameter on the honest engine, 5y 30-coin set
(`scripts/robustness_sweep.py`). Goal: confirm the edge sits on a broad plateau, not a fragile peak._

## Trading rules — ROBUST (the question that mattered)
| param | swept | Sharpe range | reading |
|---|---|---|---|
| z_entry | 1.25–2.5 | 8.8–9.5 | flat plateau ✓ |
| z_exit | 0.3–0.75 | 8.2–9.3 | flat plateau ✓ (only degenerate 0.0 breaks) |
| z_stop | 5–8 | 9.3–10.3 | plateau on the loose side ✓ (breaks only if set too tight, 3–4 — the known whipsaw) |

The decision logic is **not overfit** — it works across a wide band on every trading knob.

## Signal-construction windows — monotonic, NO plateau → deliberately NOT tuned
| ema (@zwin 336) | 24 | 36 | 48 | 72 | 96 | 120 | 168 |
|---|---|---|---|---|---|---|---|
| Sharpe | 21.0 | 19.0 | 17.3 | 15.2 | 13.8 | 12.6 | 10.7 |

ema Sharpe rises **monotonically as the window shortens**, optimum pinned at the edge of the grid,
**no plateau.** zwin similarly rises with length (84→3.9, 168→9.3, 336→10.7). These are NOT adopted:
1. **No plateau = fragile / edge-of-grid optimum** — the opposite of robust.
2. **Shorter ema → microstructure regime** — the residual increasingly captures bid-ask bounce, the
   noise we already showed isn't cleanly tradeable (the lag/cost reality-check); the honest engine
   under-models the fill-quality decay at those timescales, so the rising Sharpe is largely
   un-realizable. Chasing it = fitting noise on survivor data.

Decision: **keep ema=zwin=168.** A 1-week detrend sits comfortably longer than the ~2-day reversion
half-life, so it doesn't chase the signal — the conservative, principled choice.

## Verdict
Robustness sweep PASSED in the way that matters: the trading rules are a broad plateau (not overfit),
and we consciously leave the signal windows conservative rather than over-optimize toward
microstructure. **This effectively closes the in-sample research track.** Highest-value next step is
now LIVE forward data (the shadow paper run → $50 micro-test), not more backtest tuning.
