# Backtest Findings #1 — convergence structure (NO-GO as tested)

_Run: `scripts/backtest.py` on backfilled 1h history. Mean-reversion z-score convergence
(lookback=168, z_entry=2, z_exit=0.5, z_stop=4), cost from `config/instruments.yaml`
(Binance spot maker 10 bps/side, perp maker 1.5 bps). Causal rolling z (no lookahead)._

## Verdict: **NO-GO** — gross edge is real, but it does not clear the modeled cost-hurdle.

| structure | span | gross (bps) | **net @ modeled cost** | break-even cost | MC intrabar |
|---|---|---|---|---|---|
| BASIS: XAUT spot vs xyz:GOLD perp | 0.19y | +213 | **−293** (cost 23) | ~10 bps | −1837, 0% seeds + |
| WRAPPER same-venue: PAXG vs XAUT (Binance) | 0.19y | +163 | **−837** (cost 40) | ~10 bps | −4141, 0% + |
| WRAPPER cross-venue: PAXG(bnc) vs XAUT(bfx) | 1.42y | +7499 | **−3061** (cost 40) | ~30 bps | −18679, 0% + |

## Diagnosis
1. **The killer is the CEX spot fee**, not the signal. Mean-reversion makes money *gross* in all three; the 10 bps/side spot fee (→ 23–40 bps round-trip) is 2–4× the captured edge. Average gross/trade ≈ 10–30 bps vs cost 23–40.
2. **Intra-bar simulation makes it worse** (MC ≫ negative): acting intra-bar → many more threshold crossings → cost compounds. The strategy overtrades and whipsaws.
3. **The clean spreads are too small; the big spread is an artifact.** Same-venue wrapper |dev|>cost only 0.4% of the time. The large cross-venue gross is inflated by Binance↔Bitfinex + USDT/USD basis that isn't cleanly capturable.

## Caveats (cut both ways)
- **Understates basis:** the backtest EXCLUDES the perp funding tailwind of **~8.69% APR** — large. A *held* cash-and-carry earning funding while it waits to converge is a different, likely better trade than high-frequency flipping. (8.69% APR ≈ 33 bps per ~2-week hold — alone exceeds the 23 bps round-trip.)
- **Overstates whipsaw:** MC `sigma_mult=1.0` likely injects more intra-bar variance than reality → inflated trade count. Truth is between RAW and MC; both are negative at modeled cost, so the verdict is robust.
- Candle closes ≠ executable mids; single param set (overfit risk); short windows (basis/same-venue ~70d).

## Pivot (per CLAUDE.md ladder — cheapest first)
1. **Restructure → funding-credited hold-style basis.** Credit the 8.69% APR funding; hold the delta-neutral cash-and-carry and exit on convergence rather than churning. This is the most promising, evidence-backed lever (funding alone may clear cost).
2. **Re-parameterize → fewer, bigger trades.** Higher z_entry + hysteresis/min-hold to trade only large dislocations and stop the whipsaw.
3. **Reselect → cheaper execution.** Edge only lives below ~10–30 bps round-trip; need maker rebates / lower-fee tier / cheaper spot venue. The 10 bps Binance spot maker is the wall.

**Do NOT proceed to paper trade** — hypothesis did not hold as tested. Next: re-run BASIS as a funding-credited, low-frequency cash-and-carry at realistic low cost.
