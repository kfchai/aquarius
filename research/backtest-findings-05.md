# Backtest Findings #5 — diversification works (basket touches the gate, but qualified)

_Run: `scripts/diversify.py`. 4 always-on delta-neutral funding carries (GOLD, BTC, ETH, SOL),
common ~0.45y window, per-bar carry = d(spread_bps) + funding. Cost one-off (buy-and-hold)._

## Per-leg
| leg | Sharpe | %/yr | funding APR | ret vol (bps) |
|---|---|---|---|---|
| GOLD | 0.71 | 7.2 | 8.8% | 11.1 |
| BTC | **2.23** | 3.0 | 3.0% | 1.5 |
| ETH | **2.53** | 4.0 | 4.2% | 1.7 |
| SOL | **−1.52** | −3.1 | **−3.6%** | 2.2 |

## Correlation (per-bar carry) — the crux
avg pairwise corr = **0.14**. GOLD ~uncorrelated with crypto (0.02–0.05, genuine diversifier);
BTC/ETH/SOL 0.20–0.28 (shared leverage factor, but modest).

## Basket
- equal-weight Sharpe = **1.02** (2.8%/yr) — *fails* gate
- **inverse-vol Sharpe = 1.65** — *clears* gate
- avg single-leg 0.99; ideal-if-uncorrelated 1.98; crypto-only (no GOLD) EW = 1.13

## Verdict: diversification is real, but this is NOT a clean GO.
✅ **The mechanism works** — low correlation (0.14), basket Sharpe (1.02–1.65) well above the single gold leg (0.71). GOLD genuinely diversifies crypto.
⚠️ **But the gate-clearing 1.65 is fragile:**
1. **Hindsight in the weighting.** Inverse-vol down-weights SOL *because SOL lost in-sample*. Out-of-sample you don't know the loser. The no-hindsight number is **equal-weight = 1.02, which fails.**
2. **SOL funding went NEGATIVE (−3.6% APR).** Funding-carry is not free yield — 1 of 4 legs had negative carry. In a deleveraging event, fundings flip negative *together* → the 0.14 correlation spikes toward 1 exactly when it matters ("correlations → 1 in a crisis"). The benign 0.14 is regime-dependent.
3. **Single ~5.5mo, mostly-positive-funding regime.** BTC/ETH Sharpe 2.2–2.5 is almost certainly flattered; funding-carry Sharpe is the most regime-sensitive metric there is. The tail (correlated funding-flip + basis blow-out + short-leg liquidation) is absent from this window.

## Pivot — confirm robustly (3 things)
1. **More legs (N≈10–15 liquid perps).** Makes *equal-weight* (no hindsight) clear the gate if correlations stay low — the honest robustness test.
2. **Walk-forward weighting** (inverse-vol from *past* data only) — removes hindsight.
3. **Funding-flip stress test** — force fundings negative / correlations to 1, size the drawdown. (This is also where the convexity overlay finally earns its keep.)

**Status: diversified carry basket is the right structure and reaches the gate under favorable (hindsight/benign) assumptions; equal-weight honest Sharpe ~1.0. Not GO yet — needs more legs + OOS weighting + stress.**
