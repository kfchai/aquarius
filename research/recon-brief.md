# Recon Brief — POC Stage 0

**Purpose:** Pick the POC's target chain + instruments + data sources, and gather the real numbers needed to **ratify the go/no-go gates** in [../CLAUDE.md](../CLAUDE.md). This is the prerequisite for Stage 1 (cost/fill model).

**Constraints (from CLAUDE.md):** strictly delta-neutral; crypto-only (incl. tokenized RWAs); no listed options; cheap chains + maker rebates, avoid Ethereum L1; micro/steady; start <$10k. The core law: an edge exists only if realized edge > honestly-measured cost-hurdle.

## Questions the recon must answer

1. **Cost-calibration venue (Stage 1 linchpin).** Cheapest, most measurable execution for a small maker-focused trader on a *liquid* perp. Compare maker/taker fees, maker rebates, funding mechanics, min sizes, API/data quality across **Hyperliquid, Bybit, OKX, Binance, and a top Solana perp DEX (Drift / Jupiter)**. Which gives ~zero or negative maker fees + clean tick/L2 data?
2. **Wrapper-spread candidates (the edge).** Which "same-underlying, multiple-wrapper" pairs trade with real 24/7 liquidity on cheap chains?
   - Tokenized gold: **PAXG vs XAUT** — venues, depth, typical spread, historical dislocation range.
   - Tokenized equities (xStocks / Ondo / Dinari) — availability, liquidity, redemption.
   - Tokenized T-bills (BUIDL / USYC / USDY) — yields, redemption, on-chain rate vs SOFR.
   - → Which single pair has the best liquidity + data history for the *first* convergence trade?
3. **Cross-asset perps for cash-and-carry.** Any crypto venues listing gold/commodity/FX/equity perps usable for delta-neutral carry vs tokenized spot? Liquidity + funding behavior.
4. **Cheap-chain execution.** Solana vs Hyperliquid vs Base vs Arbitrum — current gas/fees, DEX maker-rebate availability, atomic multi-leg tooling.
5. **Data sources.** Historical + real-time availability (free vs paid) for L2 books, funding, oracle/mark, and tokenized-RWA prices — exchange APIs, Tardis.dev, Kaiko, Amberdata, CoinGlass, Dune. Flag where RWA history is thin (forward-collect).
6. **Redemption / de-peg risk.** For top wrapper candidates: redemption mechanics (who, fees, delays, custody/issuer) and any de-peg history. (The dominant tail.)

## Required output (synthesis)
A recommendation of: (a) Stage-1 cost-calibration instrument, (b) first wrapper-spread / carry leg, (c) chain/venue, (d) data stack, and (e) **realistic initial values to ratify the gates** — typical achievable maker cost, typical spread/edge size, typical dislocation frequency — so we can freeze the Stage-3 thresholds (Sharpe, cost-margin, DD, overlay bleed) against reality.

## Result
_(Recon report lands here / in `research/recon-report.md`.)_
