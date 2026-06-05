# Backtest Findings #12 — OUT-OF-SAMPLE PASS: the reversal basket survives 5 years incl. LUNA/3AC/FTX/Aug-24, every regime, crisis-resilient

_The make-or-break test from findings-11. Pulled 5y hourly OHLCV for the older 11-coin alt subset
(`scripts/backfill_long.py`) and ran the honest-fill book across the full window with per-year and
crisis isolation (`scripts/oos_crisis.py`). The single benign 6-month window was just the calm tail;
this is genuinely out-of-sample through the worst crypto crises on record. **It passed.**_

## Headline — full 5y, honest fills (state-dependent slippage + carry + 1-bar lag)
| k_vol | carry%/yr | Sharpe | ret%/yr | maxDD(bps, /gross) | win% | ntr |
|---|---|---|---|---|---|---|
| 0.00 | 0 | 9.44 | 152 | −812 | 75 | 6720 |
| 0.10 | 20 | **7.49** | **121** | −865 | 70 | 6720 |
| 0.20 | 20 | 6.24 | 101 | −970 | 66 | 6720 |

6720 trades over 5y ≈ 3.7/day across 11 legs — not HFT, executable.

## Every calendar year positive — including 2022 (LUNA + 3AC + FTX)
| year | Sharpe | ret%/yr | regime |
|---|---|---|---|
| 2021 | 8.02 | 172 | bull top |
| **2022** | **7.08** | 125 | **LUNA, 3AC, FTX** |
| 2023 | 7.48 | 109 | recovery |
| 2024 | 7.38 | 126 | bull + Aug unwind |
| 2025 | 8.62 | 113 | — |
| 2026 | 7.25 | 72 | partial |

## Crisis isolation — the tail did NOT fire; the book made money in cascades
| crisis | days | P&L (bps/gross) | worst bar | intra maxDD | ann.Sharpe |
|---|---|---|---|---|---|
| LUNA/UST | 9 | **+407** | −467 | −845 | 3.19 |
| 3AC/Celsius | 7 | **+433** | −81 | −125 | 10.75 |
| FTX | 14 | **+356** | −151 | −470 | 3.10 |
| Aug-24 unwind | 3 | **+87** | −59 | −208 | 5.26 |

The feared failure mode (correlations → 1, the −1145bps tail fires across all legs at once) **did not
happen**. In a cascade the laggards and leaders both move, the cross-sectional gaps still close, and
the book is effectively a **cross-sectional liquidity provider paid more in stress** — a coherent
economic story for why it earns through crises. Equity climbs straight through every crisis band;
rolling 30d Sharpe sits above the 1.5 gate almost the entire 5y (research/figures/oos_crisis.png).

## Formal gates — now passes cleanly (research track)
- Sharpe ≥ 1.5 OOS: **7.5** ✓  · survives ≥1.5× cost (holds at k_vol 0.2 + carry): ✓ · positive every
  regime ✓ · crisis-resilient ✓. The POC's core falsifier ("edge < cost / one benign regime")
  **failed to falsify it.** First genuine GO on the research track.

## The discipline — why this is NOT "Sharpe-7 real"
Sharpe 7 every year for 5y is not a live-achievable net number. What still flatters it:
1. **Capacity = the hard ceiling.** Per-unit-gross; Sharpe is scale-free but dollars aren't. ~$1.4M/hr
   median volume → ~$14k/leg (~$150k gross) before impact bites. A REAL but SMALL-capital edge (fits
   "<$10k start, micro-compound"; will NOT scale to large AUM).
2. **Modeling still optimistic:** no hourly hedge-rebalance cost charged; slippage uses bar-range as a
   proxy, not true size-dependent impact. Live will be lower, maybe materially.
3. **It's the known crypto short-term reversal factor** — real, documented, COMPETED. Survives honest
   fills + crises (many naive versions don't), but crowding compresses it over time.

## State / next
Conditional PARK (findings-09) is now firmly overturned for this branch. The reversal basket is a
validated, regime-robust, crisis-resilient edge — capacity-limited and modeling-optimistic, but real.
**Next: capacity-realistic sizing study** — re-run with true size-dependent impact at target book
sizes ($10k/$50k/$150k) to find deployable AUM and Sharpe-at-size (the dollar value) BEFORE any paper
infra. Only then Stage 5 (paper/shadow-live). Do not skip the sizing study — capacity is the binding
real-world constraint, not the signal.
