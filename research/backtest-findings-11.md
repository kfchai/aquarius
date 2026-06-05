# Backtest Findings #11 — the pivot that worked: short-gamma reversal on an alt-residual basket clears Stage 4 (honest fills), gated only by capacity + a single regime

_This session ran the universe search to its conclusion and it flipped the whole thesis.
Built `scripts/universe_search.py`, `reality_check.py`, `plot_revert_shape.py`, `condor_test.py`,
`honest_fill.py`. The headline: **the butterfly (long-gamma) was the wrong side the whole time;
the right side is short-gamma cross-sectional mean-reversion on a broad alt basket** — and it is
the first structure in the entire POC to survive honest fills._

## 1. Universe search → the sign flip
Built cross-sectional residuals (idiosyncratic deviation from the equal-weight log-basket,
EWMA-detrended, cross-sectionally demeaned, z-scored) for three universes and measured
extend-vs-revert, frequency, two-sidedness, and BOTH a long-gamma and a mean-revert P&L:

| universe | ext/rev | freq | 2-sided | LONG-gamma %/yr | MEAN-REVERT %/yr |
|---|---|---|---|---|---|
| stablecoins | −1.09 | 47% | 25% | −38 | +24 |
| **alts-15** | −0.60 | **98%** | **87%** | **−711** | **+1869** |
| L1-6 | −0.53 | 88% | 62% | −367 | +721 |

**Every** crypto universe mean-REVERTS (ext/rev < 0). The butterfly needs dislocations to EXTEND
to the wing; they don't — they snap back. So long-gamma is structurally on the wrong side, and
the winning side is its mirror: **short-gamma mean-reversion** (bet the gap closes). Alts give it
the frequency (98%) + two-sidedness (87%) that stablecoins never had.

## 2. Reality check — not a bid-ask-bounce mirage
`reality_check.py`: lag the signal (act on a prior bar, no same-bar look-ahead) × sweep cost.
It did NOT collapse — +1810%/yr at lag=1, still +215%/yr at a **3-bar lag + 80 bps** round-trip.
A same-bar microstructure artifact would have died. This is the real, documented **crypto
short-term cross-sectional reversal factor.** (Magnitude is inflated — see §5 — but the sign is real.)

## 3. The shape is the standard butterfly (user's correction)
`plot_revert_shape.py` (research/figures/revert_shape.png): the mean-reversion payoff is a
**tent / inverted-V** — peak profit when the gap is small, capped losses in the wings. This is the
**standard (long) butterfly = short gamma**; the "reverse iron butterfly" we'd been chasing (valley)
is its inverse. 989 trades, 74% win, +153 bps avg win, but a **−1,145 bps worst trade** (the
left-wing tail = a dislocation that trended instead of reverting). The risk is negative-skew in the
operational tail even though headline skew is dragged positive by a few deep reverters.

## 4. Reshaping the tent — plain butterfly wins; the synthetic-premium law
`condor_test.py` (research/figures/condor_compare.png), all on the same alt-residual basket @20bps:

| config | Sharpe | ret%/yr | maxDD | worst-tr | ret@80bps |
|---|---|---|---|---|---|
| **butterfly** (hold to z=0.3) | 11.4 | 109 | −280 | −1145 | **+30** |
| condor (exit z=1.0, flat top) | 10.0 | 88 | −289 | −1145 | −28 |
| condor+shallow (stop z=3) | 1.6 | 12 | **−1084** | −750 | −293 |
| condor+overlay (λ=0.35 valley) | 8.7 | 67 | **−224** | −1145 | −72 |

**Key structural law:** with real options you buy the shape ONCE (fixed premium); with SYNTHETIC
gamma you pay the premium PER ROUND-TRIP. So every reshape that trades more (condor's early exit,
the tight stop) pays MORE and loses. The plain tent held to centre is the most cost-efficient and
the **only config still positive at 80 bps.** Tight stop = whipsaw death (3851 trades, 43% win,
maxDD 4× worse). The valley overlay genuinely caps the book drawdown (−224, best) — confirming the
two-book thesis directionally — but the premium is expensive (ret 109→67, negative at 80 bps).
Verdict: keep the plain butterfly; tip-steering remains the only untested lever (deferred, highest
overfit risk, no added trades).

## 5. Stage 4 — honest fills: it SURVIVES (clears the ≥60% retention bar)
`honest_fill.py`: state-dependent slippage (cost at entry/exit = base + k_vol·that-bar's-true-range,
so cost lands hardest on the violent entry bars) + 1-bar execution lag + funding/borrow carry drag.

| k_vol | carry%/yr | Sharpe | ret%/yr | maxDD | win% | bps/tr |
|---|---|---|---|---|---|---|
| 0.00 | 0 | 12.4 | 118 | −280 | 78 | 90 |
| 0.10 | 20 | 9.3 | 89 | −299 | 72 | 67 |
| 0.20 | 20 | 7.4 | 71 | −311 | 67 | 54 |

Retains ~80% of the idealized Sharpe at a realistic setting → **clears Stage 4's ≥60% bar.** It
survives because reversion amplitude (~80 bps/trade) dwarfs realistic slippage (~10–40 bps). **First
structure in the POC to pass a stage GO cleanly.**

## 6. The two real blockers (not in the formal gates, but binding)
- **Capacity is tiny.** Median coin volume ~$1.4M/hr → ~10 bps impact at just 1% participation
  ($14k/leg). Deployable capital is low hundreds of $k gross before impact dominates. A small-capital
  edge (fits "<$10k start", won't scale).
- **One benign 6-month regime.** Sharpe 7–12 is NOT a forward number — it's the ceiling of a calm
  window. Mean-reversion looks best right before it blows up: in a deleveraging cascade all residuals
  diverge at once, correlations → 1, the −1,145 tail fires across all 15 legs simultaneously. **Zero
  crises tested.**

## State / next
The long arc finally found a structure on the RIGHT side of the market that survives honest cost —
a genuine reversal of the earlier PARK recommendation, *conditional* on the two blockers. The
make-or-break next test is **out-of-sample across regimes**: extend history back through a crash
(DefiLlama multi-year) and re-run §5 OOS. A benign window is exactly where this strategy lies. Do
NOT scale or paper-trade until OOS + a modeled crisis are passed; the capacity ceiling caps ambition
regardless.
