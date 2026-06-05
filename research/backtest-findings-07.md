# Backtest Findings #7 — butterfly CORE MECHANIC works (first GO, with caveats)

_Run: `scripts/butterfly_core.py`. Synthetic long-gamma (Donchian breakout) on USDC/USDT
through the March-2023 USDC de-peg ($1.00 → $0.87 → $1.00) + 9.5 months of calm._

## The two fixes that turned the overlay from broken to working
1. **Donchian (fixed-reference) breakout instead of rolling-z.** Rolling-z whipsawed *through*
   the de-peg (captured −35 bps); Donchian **captured +603 bps** of the same move (biggest single
   trade +601). The reference must NOT chase the trend.
2. **Deadband = the "imaginary tip" zone.** No new entries within ~30 bps of the centroid → flat in
   calm, active only in the wings. This killed the calm whipsaw (130 trades → 7).

## Result (deadband=30bps, entry_n=72, cost=2bps — realistic for stablecoin pairs)
| metric | value |
|---|---|
| full-year net | **+525 bps (+5.25%)** |
| de-peg payoff | +546 bps |
| calm bleed (9.5 mo) | **−21 bps (≈0)** |
| trades / year | **7** |
| **payoff / bleed** | **26×** |

Robust across deadband 10–100 bps (all +469 to +533) — not a knife-edge. This is the reverse-iron-
butterfly behavior the design called for: **flat tip, profitable wings.** vs the carry book (mediocre
Sharpe ~0.5), this is the distinctive long-gamma idea **working as designed.**

## Honest caveats
- **ONE instrument, ONE event.** This proves the **mechanic captures a real dislocation cleanly with
  near-zero calm bleed** — necessary, and now demonstrated. It does NOT prove dislocations happen
  **often enough** across instruments to be steady income. USDC de-pegged once in 2023.
- Some choice in deadband/entry_n, but the sweep shows robustness. Cost (2 bps) needs live validation.
- "Calm" here is genuinely calm (USDC≈1.0); noisier instruments need per-axis deadband calibration.

## Verdict & next step
**GO on the butterfly core mechanic** — the first positive result of the POC, and it vindicates the
design (tip zone + go-with-the-move wings). The next question is **breadth/frequency**, not mechanism:
- Build the **multi-axis basket butterfly** — run this long-gamma rule across many dislocation-prone
  axes (stablecoin pairs, LST/ETH, wrapper pairs), netted delta-neutral, across **multiple real
  de-peg events** — and measure whether the basket produces **steady positive long-gamma flow** (not
  one lucky event) with bounded calm bleed.
- If yes → build the rotation/scalping engine + combine with the carry book (income + tail-hedge) and
  evaluate the combined book vs the Stage-3 gates.
