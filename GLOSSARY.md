# Aquarius — Glossary

Plain-language definitions of every term used in [CLAUDE.md](CLAUDE.md) and the design discussion. Terms marked **(coined)** are our own project vocabulary, not standard industry terms. Terms marked **(option Greek)** describe sensitivities that originate in options but apply to *any* position.

---

## 1. The core stance

- **Delta-neutral** — the position has **zero net exposure to price direction**. If the underlying goes up or down a little, your P&L doesn't change from *that* alone. "Delta" = sensitivity to price; neutral = it nets to zero. This is our hard invariant.
- **Market-neutral** — broader cousin of delta-neutral: no net bet on the market going up or down; profit comes from *relative* moves, carry, or convergence.
- **Edge** — a genuine, repeatable source of profit after costs. Not a hunch — something measurable.
- **Cost-hurdle (coined)** — the all-in cost of doing a trade (fees + slippage + funding + gas). Our core law: an edge only exists if the realized profit **beats the cost-hurdle**.

## 2. Options shapes & the Greeks (the language of the "butterfly")

- **Delta (option Greek)** — sensitivity to the underlying's *price*. Long 1 BTC = delta of 1. Delta-neutral = total delta 0.
- **Gamma (option Greek)** — sensitivity of *delta* to price; i.e. **how your directional exposure changes as price moves**. **Long gamma** = you automatically get longer as price rises and shorter as it falls (you profit from movement either way). **Short gamma** = the opposite (you profit from stillness, lose on big moves).
- **Theta (option Greek)** — time decay: what a long-options position *bleeds* per day just from time passing. The price you pay to be long gamma.
- **Vega (option Greek)** — sensitivity to *implied volatility* (the market's expected future movement).
- **Convexity** — a curved (non-straight-line) payoff. Long gamma = positive convexity = small steady cost, occasional big gains. The whole "butterfly" idea is a convexity structure.
- **Straddle** — buy a call *and* a put at the same strike. Profits from a big move in *either* direction. Long gamma.
- **Strangle** — like a straddle but the call and put are at *different* (out-of-the-money) strikes. Cheaper, needs a bigger move.
- **(Reverse / long) iron butterfly** — buy a straddle (the middle), sell a strangle (the wings). Net result: **profit if price moves far either way, small capped loss if it sits still.** The shape that started this thread.
- **Net debit / net credit** — debit = you *pay* to put the trade on (the butterfly costs money up front). Credit = you *receive* money up front.
- **The "tip" (coined)** — the downward point in the middle of the reverse-butterfly payoff: the **maximum loss, suffered when price doesn't move.** It is literally *the price of owning convexity* — paid as theta (options) or as whipsaw + fees (our option-free version). **Conservation of the tip:** you can't make it disappear for free; you only shrink it with a real edge (cheap volatility, cheap execution, or good timing).
- **Imaginary tip (coined)** — our tip isn't a real traded strike; it sits at a *computed* reference point (the manifold centroid), and we aim to **finance it toward ~zero** by continuously banking profitable legs (scalping). "Imaginary" = virtual location + nearly-free in the right regime.

## 3. Carry, rates & the dollar curve

- **Carry / carry trade** — earning a steady yield for holding a position (like interest). The "savings-account" layer of our book.
- **Basis** — the price gap between a derivative and its spot asset (e.g. futures price − spot price).
- **Cash-and-carry** — buy spot, sell the future (or perp) against it → delta-neutral, collect the basis/funding as it converges. A classic neutral carry trade.
- **Spot** — the plain asset itself, for immediate delivery (vs a derivative of it).
- **Perpetual future ("perp")** — a crypto futures contract with no expiry. Stays near spot via the funding mechanism.
- **Funding / funding rate** — periodic payment between perp longs and shorts that tethers the perp to spot. Positive funding → longs pay shorts. Capturing funding (while delta-neutral) is a core carry edge.
- **Term structure / forward curve** — the set of prices/rates for the *same* asset across different expiries or horizons. Has a "shape" (see below).
- **Level / slope / curvature** — three properties of a curve. **Level** = overall height, **slope** = tilt, **curvature** = bend. A *butterfly* spread isolates **curvature** while cancelling level and slope.
- **Calendar spread / (calendar) butterfly** — multi-leg trades across *expiries* that bet on the curve's shape, not the asset's direction.
- **SOFR** — the benchmark US overnight interest rate (the "risk-free" dollar rate in TradFi). Our reference for what an on-chain dollar *should* yield.
- **Dollar-funding membrane (coined)** — the boundary between **on-chain dollar rates** (USDC lending, funding-implied rates, tokenized T-bill yields) and **off-chain rates** (SOFR). The same dollar has different prices on each side; the gap is a neutral carry edge.

## 4. Relative value, spreads & "the manifold"

- **Spread** — the price difference between two related instruments. Trading the spread = betting they converge or diverge, not on their direction.
- **Spread-of-spreads** — a second-order spread: when one spread reliably co-moves with another, you trade the gap between *them*.
- **No-arbitrage manifold (coined framing)** — the idea that a set of linked instruments (e.g. gold and all its tokenized wrappers, perps, baskets) *should* sit at prices consistent with each other. That consistent set forms a low-dimensional surface — the **manifold**. Real prices wander **off** it; each deviation is a tradeable arbitrage.
- **Centroid** — the geometric center of a basket; in our design, the manifold's "fair" reference point — i.e. where the **imaginary tip** sits.
- **Cointegration** — a statistical property where two (or more) prices wander individually but their *spread* stays stable/mean-reverting. The basis for pairs and basket trades.
- **Statistical arbitrage ("stat-arb")** — many small, diversified, market-neutral bets on mean-reverting relationships. Profits on average across the portfolio, not trade-by-trade.
- **Factor / factor-neutral** — a *factor* is a common driver many assets share (e.g. "the crypto market," "the gold factor," "the rate factor"). **Factor-neutral** = a portfolio built so its exposure to every common factor is zero, leaving only the idiosyncratic mispricing.
- **PCA / eigen-portfolio** — Principal Component Analysis: a math technique that extracts the common factors from a group of assets. The leftover **residual** is the mean-reverting part we trade. An *eigen-portfolio* is a basket aligned to one factor.
- **Dispersion / dispersion trade** — how *spread out* a group of assets' moves are. A dispersion trade profits when components scatter apart (high dispersion) regardless of market direction — naturally long-gamma and delta-neutral.
- **Correlation trade** — betting on whether assets move *together* or apart, independent of which way they go.
- **Triangular / cyclic arbitrage** — a loop of trades (A→B→C→A) where the exchange rates multiply to ≠ 1, leaving a riskless profit.
- **Negative cycle / Bellman-Ford** — model every tradeable rate as an edge in a graph of log-prices; a **negative cycle** (found via the *Bellman-Ford* shortest-path algorithm) is exactly a profitable arbitrage loop.
- **Replication / basket arbitrage** — when an instrument can be rebuilt from a basket of others (e.g. an index vs its constituents), you trade the package vs the parts. On-chain, 24/7 version of **ETF AP arbitrage**.
- **ETF AP (Authorized Participant) arbitrage** — in TradFi, big players keep an ETF's price tied to its underlying basket by creating/redeeming shares. We mimic the logic with tokenized assets.
- **mNAV / premium-to-NAV** — how much a wrapper (e.g. a tokenized MicroStrategy share) trades *above or below* the value of what it holds (NAV = net asset value). The oscillating premium is itself a mean-reverting, hedge-able series.

## 5. Volatility & the convexity engines (option-free)

- **Implied volatility (IV)** — the market's *expected* future movement, priced into options.
- **Realized volatility (RV)** — how much the asset *actually* moved. Long-gamma profits when **RV > IV** (or, for us, when realized movement beats the cost-hurdle).
- **Variance risk premium** — the tendency for IV ≥ RV on average (option sellers get paid). It's *why* being structurally long-gamma usually bleeds — and why we need a real reason for the tip to be cheap.
- **Vol surface / skew** — the full map of implied vol across strikes and expiries. **Skew** = the asymmetry (e.g. puts pricier than calls). Dislocations here are tradeable.
- **Gamma scalping** — holding a long-gamma position and continuously re-hedging delta back to zero; each wiggle locks in a small profit. The "base-hit" way to monetize convexity.
- **Delta hedging / dynamic replication** — repeatedly trading the underlying to keep delta at a target. Done with a *rule*, it can **manufacture** an option-like (convex) payoff using only perps — no options needed.
- **Breakout rule / reverse-grid (coined usage)** — a rule that **adds to the direction of a move** (buy as price breaks up, sell as it breaks down). This synthesizes **long gamma**. Its mirror image:
- **Grid bot** — a rule that **fades** moves (buy dips, sell rips) within a range. This is **short gamma** — profits in chop, loses on breakouts.
- **Whipsaw** — repeated false breakouts in a choppy market that make a breakout/long-gamma rule flip back and forth and bleed. The synthetic version of the "tip."
- **Trend-following** — systematically riding sustained moves; mathematically ≈ long gamma / long straddle.
- **Leveraged tokens** — tokens (e.g. "3× long") that rebalance daily to keep constant leverage. Holding a long *and* short one together is convex to trends but **decays** in chop.
- **Volatility drag / decay** — the erosion a leveraged/rebalancing product suffers in choppy markets. For a long-gamma leveraged-token structure, this decay *is* the tip.
- **Rotation engine (coined)** — the logic that **scalps** a profitable leg and **tops up / substitutes** others so the basket keeps net delta ≈ 0 and net gamma > 0 within tolerance. What makes our butterfly "scalpable without destroying it."
- **Redundancy budget (coined)** — how many legs you can peel off (bank for profit) before the butterfly shape breaks. A designable number; bigger with more correlated legs.

## 6. Crypto instruments & venues

- **Tokenized RWA (Real-World Asset)** — a TradFi asset (gold, a stock, T-bills) represented as a token that trades 24/7 on crypto rails. Examples: **PAXG / XAUT** (gold), tokenized stocks, **BUIDL / USYC / USDY** (T-bills). In scope for us because they trade on crypto venues.
- **Wrapper / wrapper-spread (coined usage)** — a *wrapper* is one crypto representation of an underlying (PAXG is a wrapper for gold). A *wrapper-spread* is the price gap between two wrappers of the same thing (PAXG vs XAUT) — a pure, delta-neutral convergence trade.
- **Stablecoin** — a token pegged to $1 (USDT, USDC). Our cash leg. Backed largely by US T-bills — which is why stablecoins behave like a "shadow dollar" system.
- **LST (Liquid Staking Token)** — a token representing staked crypto plus its yield (e.g. stETH for staked ETH). Often priced ≈ its underlying, with tradeable deviations.
- **AMM / LP / concentrated liquidity** — an Automated Market Maker (e.g. Uniswap) is a DEX where **Liquidity Providers (LPs)** deposit assets to earn fees. *Concentrated liquidity* (Uniswap v3) lets LPs focus on a price range. LPs are structurally **short gamma**.
- **Impermanent loss (IL)** — the loss an LP takes when prices move away from where they deposited; the concrete form of an LP's short-gamma exposure.
- **Oracle** — an on-chain price feed that smart contracts read (they can't call exchanges directly).
- **Oracle staleness / heartbeat / deviation threshold** — oracles update only every so often (**heartbeat**) or when price moves past a band (**deviation threshold**), so the on-chain price can lag reality (**stale**).
- **Push vs pull oracle (Chainlink vs Pyth)** — *push* (Chainlink) updates get posted automatically; *pull* (Pyth) updates are submitted by whoever needs them, when they need them. **TWAP** = a time-averaged on-chain price (manipulation-resistant but laggy).
- **L1 / L2 / chain** — **L1** = a base blockchain (Ethereum, Solana). **L2** = a faster/cheaper network settling onto an L1 (Arbitrum, Base). **Hyperliquid** = an on-chain exchange with order-book perps. We favor cheap chains.
- **Gas** — the transaction fee paid to a blockchain. On Ethereum L1 it's high enough to kill micro-edges; on Solana/L2s it's sub-cent.

## 7. Execution & market microstructure

- **Maker vs taker** — a **maker** posts a resting order and *adds* liquidity (often earns a **rebate**); a **taker** crosses the spread and *removes* liquidity (pays a fee). Maker-first execution lowers our cost-hurdle.
- **Bid-ask spread** — the gap between the best buy and best sell price; a cost you pay every time you cross it.
- **Slippage** — the difference between the price you expected and the price you actually got, especially for larger orders.
- **Fill** — an executed order. **Partial fill** = only part of it executed. **Queue position** = where your resting order sits in line at a price level.
- **Adverse selection** — the tendency for your resting (maker) orders to fill exactly when the market is about to move against you. A hidden cost the honest simulator must model.
- **Event-driven simulation** — a backtest that replays the market tick-by-tick and models real fills (queue, partials, latency), rather than assuming you always trade at the mid-price. We **own** ours — no black-box fill models.

## 8. On-chain mechanical edges (context, mostly out of scope for us)

- **Liquidation / liquidation bonus** — when a borrower's collateral falls too low, anyone can repay their loan and seize the collateral at a discount (the **bonus**).
- **Flash loan** — borrow a large sum with no collateral, *as long as you repay it in the same transaction* — decouples a trade's size from your capital.
- **MEV (Maximal Extractable Value)** — profit a block producer/searcher can extract by ordering transactions (arbitrage, liquidations). A **searcher** hunts it; a **bundle** is their packaged transactions; the **mempool** is the pool of pending public transactions. **Backrun** = trade right after a target tx; **JIT** = just-in-time liquidity; **sandwich** = a predatory front-and-back trade (off-limits for us).

## 9. Risk, validation & metrics

- **Sharpe ratio** — return divided by volatility of returns; a measure of *consistency*. Higher = smoother, more reliable. Our whole pitch is **high-Sharpe base-hits**.
- **Positive / negative skew** — *positive* skew = many small losses, occasional big wins (long-gamma; good). *Negative* skew = many small wins, occasional big loss (short-vol; the tail we must cap).
- **Tail / tail risk** — rare, large, outsized outcomes. We want positive tails and capped negative tails.
- **Max drawdown** — the largest peak-to-trough loss. Killer of compounding (a −50% needs +100% to recover), so we bound it.
- **Out-of-sample (OOS) / walk-forward** — testing a strategy on data it was *not* tuned on (OOS), rolling forward through time (walk-forward). The only honest way to backtest.
- **Lookahead bias / survivorship bias / overfitting** — the three classic backtest lies: using future info you wouldn't have had (lookahead); only testing assets that survived (survivorship); fitting noise so it looks great on history but fails live (overfitting).
- **Regime / regime-switching** — markets behave in modes (trending, choppy, risk-on, risk-off) and switch between them. Many strategies only work in some regimes; we measure performance per regime.
- **Cost-sensitivity curve (coined usage)** — a plot of profitability vs assumed cost level, showing **at what cost the edge dies.** We require the edge to survive to ≥ 1.5× our *measured* cost.
- **Kelly criterion / fractional Kelly** — the math for optimal bet sizing to grow capital; *fractional* Kelly bets a safe fraction of it. Many uncorrelated edges let you size each small while running healthy total exposure.
- **Cross-margin** — using one shared collateral pool to back many positions at once → capital efficiency.
- **Notional** — the total face value of a position (vs the margin posted for it).
- **Counterparty risk** — the risk that an exchange or issuer fails and you lose funds held there (FTX, Celsius). Per-venue caps mitigate it.
- **De-peg** — when a token that's *supposed* to track something (a stablecoin, an LST, a wrapper) breaks away from its peg and **doesn't reconverge**. The dominant tail in our convergence trades; the convexity overlay exists to cover it.
- **Capacity / capacity headroom** — how much capital a strategy can absorb before its edge compresses. At <$10k we have huge headroom (not a near-term constraint).
- **Kill-switch** — an automated hard stop that flattens positions / halts trading when a loss limit or anomaly is hit.

## 10. Project-coined strategy vocabulary (quick recap)

- **The tip / imaginary tip** — see §2. The cost of convexity; ours is virtual and self-financed toward zero.
- **Manifold / no-arbitrage manifold** — see §4. The "fair" surface our linked instruments should sit on.
- **Manifold butterfly** — our option-free, multi-crypto, delta-neutral synthetic long-gamma structure.
- **Rotation engine / redundancy budget** — see §5. What makes it scalpable without breaking.
- **Carry / manifold book vs convexity overlay** — the two halves of the engine: steady short-gamma income, and the long-gamma tail-hedge that rides on top.
- **Dollar-funding membrane** — see §3. The on-chain vs off-chain dollar-rate seam.
- **Frontier rotation** — being early on new chains where searcher/arbitrage competition is still thin, then moving on.
- **World-Clock** — a time/timezone/holiday/funding-settlement-aware signal layer (markets have a predictable "circadian" rhythm of liquidity and volatility).

## 11. Tooling

- **CCXT** — a popular open-source library that gives one common interface to many crypto exchanges' APIs.
- **polars / pandas / numpy** — Python data libraries for fast analysis and backtesting (polars is the faster, modern one).
