# Backtest Findings #9 — the GENUINE manifold butterfly, built & tested. It bleeds.

_Built the real thing at last: computed centroid + per-instrument residuals + netting +
additive long-gamma (`run_gamma_additive`, `butterfly_manifold*.py`). Tested on LSTs and stablecoins._

## LST basket — blocked by data + structurally shrinking opportunity
- **Data wall:** free DefiLlama daily USD prices don't align across tokens — only **24 of 1,610 days** survive a synchronous join; rETH gets **zero**. A clean LST/ETH market ratio needs **on-chain Curve pool data** (Dune/subgraph) — a real further lift.
- **Structural:** post-Shanghai (Apr 2023, withdrawals enabled) stETH is ~1:1 redeemable → std fell to **19 bps, no de-pegs since.** The big 2022 de-peg was a *pre-Merge* artifact the protocol has since closed. The butterfly's food source is shrinking.

## Stablecoin basket — clean data, recurring de-pegs, GENUINE netting
| | net | %/yr | maxDD | skew |
|---|---|---|---|---|
| **NETTED manifold (the real design)** | −2945 bps | **−6.7%** | −3910 | −3.8 |
| un-netted single-axis sum | −2933 bps | −6.6% | −4050 | −1.6 |

**Netting buys essentially nothing** (−6.7% vs −6.6%). Why: deviation std ≈ residual std (5–19 vs 6–14 bps) — the dislocations are **idiosyncratic** (each coin wiggles on its own), not a common factor. Removing the centroid doesn't remove the noise the long-gamma bleeds on. Captures are real (USDC +220 @ Mar-2023, BUSD +160, TUSD events) but **far below the everyday bleed.**

## Verdict
The genuine multi-leg manifold butterfly — finally built correctly and tested on the best available
data — **does not produce positive flow.** Its distinctive element (cross-sectional netting) adds nothing
because real de-pegs are idiosyncratic, not common-factor. Captures < bleed; negative skew.

## State of the entire POC (9 tests)
- **Carry book:** real but Sharpe ~0.5 — fails ≥1.5 gate. Diversification fails out-of-sample.
- **Synthetic long-gamma (single-axis):** captures one clean slow de-peg; bleeds across breadth.
- **Genuine manifold butterfly (netted):** bleeds −6.7%/yr; netting adds nothing.

The convergence/dislocation thesis keeps hitting the same wall: **dislocations are rare, idiosyncratic,
costly to capture, and structurally diminishing.** Both books fail the pre-registered gate.

## Decision
**PARK the thesis** with this full evidence (the disciplined default). The POC did its job: falsified the
idea cheaply, before any capital. Only remaining long-shot: **restaking-token de-pegs** (e.g. ezETH, which
did de-peg in 2024) via on-chain data — low probability, real data lift. Recommend stepping back to rethink
the edge class rather than chase it.
