# Backtest Findings #10 — butterfly shape-integrity metric (built; verdict: not scalpable here)

_Built `aquarius/backtest/butterfly.py::shape_health()` + `scripts/shape_metric.py` (rotation
sim). Exercised on the cross-sectional stablecoin residuals (5 axes, 4.4y). This is the metric
the user asked for: does banking a profitable leg keep the butterfly's shape?_

## The metric
For the live leg set: `net_delta` (Σ side·size → neutral?), `net_gamma` (with-the-move posture →
long wings?), `wings_ok` (a +side and a −side leg → two-winged?), `shape_holds` (all three), and
`redundancy` (legs droppable one-at-a-time while shape_holds stays true).

## Readout (while a basket is held; basket exists only 5% of the time)
| metric | value | reading |
|---|---|---|
| shape_holds | **40.8%** | a *valid* butterfly < half the time |
| wings_ok (2-sided) | **40.8%** | **the binding constraint** |
| \|net_delta\|≤tol | 99.5% | neutrality fine |
| net_gamma>0 | 99.9% | gamma posture fine |
| **redundancy** | **0.57** | **< 1 leg droppable — essentially none** |
| avg legs held | 1.76 | runs on the bare minimum |
| banked / banks / reopens / cuts | −5716 bps / 41 / 38 / 76 | — |
| **reopen rate** | **93%** | almost every bank forces a reopen |

## Verdict (computed): banking profit does NOT keep the shape here.
The *construction is sound* (delta-neutral 99.5%, gamma>0 99.9%) — the limit is the **data**:
- **Dislocations are one-sided** → both wings present only 40.8% of the time.
- **Sparse** (a basket exists just 5% of the time, ~1.76 legs) → **no redundancy** (0.57), so you
  can't drop a leg without breaking the shape → **93% of banks force a reopen.**

## The constructive part (a reusable design criterion)
A *scalpable* butterfly needs **frequent, simultaneous, TWO-SIDED dislocations across MANY axes** —
that's what creates the redundancy that lets you bank legs and keep the shape. Stablecoins fail this
(sparse, one-directional down-pegs). The metric now lets us *measure* any candidate universe for this
property before committing: target **shape_holds high + redundancy ≥ 1–2 + reopen rate low.**

A universe that might pass: a large basket of cointegrated assets that dislocate **both ways often**
(many small relative moves), not a handful of rarely-de-pegging stablecoins. The metric is the test.
