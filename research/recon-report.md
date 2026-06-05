# Recon Report — POC Stage 0

_Source: deep-research run wf_7b66bc10-bea (104 agents, 22 sources, 25 claims adversarially verified, 23 confirmed / 2 refuted). Figures are 2025–2026 and fast-moving._

## TL;DR decisions
- **Stage-1 cost-calibration venue:** **Hyperliquid** (best programmatic data + it's also the carry-leg venue) — with **Drift (Solana)** as the cheap-execution benchmark.
- **First edge/carry leg:** **tokenized-gold cash-and-carry** — long **XAUT** (or PAXG) spot vs short a **crypto-rail gold perp** (Hyperliquid HIP-3 gold or Kraken GLDx). The PAXG↔XAUT wrapper-spread is the related structure *if* shorting one token is executable.
- **Data stack:** **Tardis.dev** (L2 books + funding/mark/OI incl. Hyperliquid) + **CoinGlass API V4** (funding OHLC); **forward-collect tokenized-gold prices ourselves** — history is thin.
- **⚠️ Cannot ratify the edge-side gates yet.** The actual PAXG/XAUT spread size & dislocation frequency were **not verifiable** (two attempts refuted). They must be **forward-collected** before any Sharpe/edge threshold is frozen.

---

## 1. Cost-calibration venue
Real tension between cheapest execution and best data:

| Venue | Maker fee | Reachable at <$10k? | Data quality |
|---|---|---|---|
| **Drift (Solana)** | **−0.25 bps flat** (you get *paid* to make, non-BTC/ETH perps, any tier) | ✅ yes | good |
| **Hyperliquid** | +1.5 bps base (Tier 0); true negative rebate needs **0.5%+ of exchange-wide maker volume** | ❌ rebate unreachable | **best** (Tardis L2/funding from 2024-10-29, per-block snapshots, 100 ns ts) |

→ **Decision: calibrate on Hyperliquid** (cleanest data, and it's the gold-perp venue), **benchmark Drift** as the cheaper home for any pure crypto-perp legs. The ~1.75 bps/side swing between them is material for a micro-edge and goes straight into the cost model.
Sources: docs.drift.trade/market-makers/maker-rebate-fees, hyperliquid.gitbook.io/.../fees.

## 2. First edge instrument — tokenized gold (PAXG / XAUT)
- PAXG + XAUT = majority (**~$6.1B**) of the tokenized-gold market; each = 1 troy oz vaulted gold. Combined CEX spot volume **>$1.8B** (early Feb 2026). Real 24/7 trading **including weekends when COMEX is frozen** (1–3.5% weekend moves). **XAUT tracks spot tighter** than PAXG (0.25% vs 1% fee, deeper liquidity, ~$2.2B cap).
- **Two structures, different executability:**
  - **Cash-and-carry (recommended first):** long tokenized-gold spot vs short a gold *perp* → executable today (perp shortable on HIP-3/GLDx). Edge = basis + funding.
  - **Wrapper-spread (PAXG↔XAUT):** purest delta-neutral, but requires *shorting* one tokenized-gold token — borrow availability unconfirmed. Flagged as secondary pending a shortable venue.
- **Practical wrinkle:** PAXG/XAUT are Ethereum ERC-20s (XAUT also TRON/BNB). On-chain DEX trading of the spot leg = **Ethereum L1 gas (which we avoid)** → trade the spot leg on a **CEX** (no gas) or a cheap-chain version (XAUT on BNB).
Sources: coinmetrics.substack.com/p/state-of-the-network-issue-354, coingecko.com/learn/tokenized-gold-price-signal, mdpi.com/2674-1032/5/1/19.

## 3. Cross-asset gold perps (the carry leg)
- **Kraken GLDx Perps** — launched 24 Feb 2026, backed 1:1 by SPDR Gold Shares; part of 10-contract xStocks perps suite, 24/7, non-US.
- **Hyperliquid HIP-3** — on-chain order-book perps on gold/silver/oil/equities, USDC/USDH-margined; **>$95B cumulative volume, $1.2B+ OI** (→ ~$3B by mid-2026).
- **Gap:** actual **funding levels & depth** on these gold perps were **not quantified** — must measure before confirming a positive carry.
Sources: blog.kraken.com/.../tokenized-equity-perpetual-futures, coinmetrics.substack.com/p/state-of-the-network-issue-354.

## 4. Data stack
- **Tardis.dev** — L2 books + trades + derivative_ticker (funding/OI/mark) across 50+ venues incl. Hyperliquid (from 2024-10-29), Binance, Bybit, OKX, dYdX v4; per-block L2 snapshots, 100 ns timestamps.
- **CoinGlass API V4** — funding-rate OHLC at 1m→1w intervals.
- **Tokenized-RWA prices: forward-collect ourselves** via exchange APIs — history too thin to backtest from.
Sources: docs.tardis.dev/historical-data-details/{overview,hyperliquid}, docs.coinglass.com/reference/fr-ohlc-histroy.

## 5. Cash-leg yield (idle margin)
Tokenized T-bills give ~SOFR on parked collateral: **USYC** (Circle/Hashnote, ~$1.69B, integrating with USDC), **OUSG** (Ondo, ~3.49–3.75% APY Jan 2026), **BUIDL** (BlackRock). Redemption mechanics & de-peg history **not verified** — open risk item.
Sources: circle.com/pressroom/...usyc..., docs.ondo.finance/qualified-access-products/ousg/yield.

## 6. ⚠️ Critical gaps — must forward-collect before freezing gates
1. **Empirical PAXG/XAUT bid-ask, L2 depth, and the realized spread/dislocation distribution (bps) & frequency.** This is *the* number the go/no-go gates depend on, and it has **no usable history** — collect it live.
2. **Redemption mechanics + de-peg history** for PAXG, XAUT, USYC, OUSG, BUIDL (the tail).
3. **Funding/basis levels** on GLDx / HIP-3 gold perps vs cost of holding tokenized-gold spot (confirm carry is positive net of fees).
4. **Cheap-chain all-in per-leg cost + atomic multi-leg tooling** (Solana vs Hyperliquid vs Base vs Arbitrum) — not pinned.

## 7. Refuted claims (honesty — these temper the thesis)
- ❌ "Tokenized gold trades at a 0.5–2.5% discount to spot" — **refuted 0-3.**
- ❌ "Dislocations concentrate on weekends / off-hours when XAU is closed" — **refuted 1-2.**
→ Do **not** assume a fat, weekend-clustered gold spread. The edge must be *measured*, not presumed. This is a yellow flag on the gold-wrapper enthusiasm.

## 8. Impact on the go/no-go gates
- **Cost side — ratifiable now:** maker cost ≈ **−0.25 bps (Drift) to +1.5 bps (Hyperliquid) per side**, before slippage; the spot leg adds CEX fees. Stage 1 measures the real round-trip.
- **Edge side — DEFERRED:** spread size & frequency unknown → the central test (edge > cost) **cannot be evaluated until Stage-2 forward-collection.** Pre-registered Sharpe/edge thresholds stay provisional until then.

**Sequencing change:** because the edge data has no history, **start the Stage-2 recorder immediately** (forward-collect XAUT/PAXG spot + gold-perp funding/basis) and run **Stage-1 cost calibration on Hyperliquid in parallel.**
