# Aquarius — Delta-Neutral Crypto Edge Engine

> Status: **OOS PASS — the reversal basket survives 5y incl. LUNA/3AC/FTX/Aug-24; first genuine GO on the research track; gated now only by CAPACITY** ([findings-12](research/backtest-findings-12.md)). The make-or-break out-of-sample test passed emphatically: pulled 5y hourly OHLCV for the older 11-alt subset and ran the honest-fill book full-window — **Sharpe 7.5, +121%/yr at realistic fills, EVERY calendar year positive (incl. 2022's LUNA+3AC+FTX at Sharpe 7.1), and POSITIVE P&L inside every cascade** (LUNA +407bps, 3AC +433, FTX +356, Aug-24 +87). The feared failure (correlations→1, the −1145 tail firing across all legs) did NOT happen — in a cascade laggards & leaders both move, gaps still close; the book is a **cross-sectional liquidity provider paid more in stress.** POC's core falsifier ("edge < cost / one benign regime") failed to falsify it. **Remaining binding constraint = CAPACITY (real but small-capital edge): ~$1.4M/hr/coin → ~$14k/leg (~$150k gross) before impact bites — fits "<$10k start, micro-compound", will NOT scale to large AUM.** Caveats: Sharpe 7 is NOT live-achievable net (no hourly hedge-rebalance cost charged; slippage is a bar-range proxy not true size-impact; it's the known/competed short-term reversal factor). **Capacity & breadth now measured** ([findings-13](research/backtest-findings-13.md)): true sqrt-impact (K=100) → capacity is BIGGER than the earlier ~$150k guess. A **Sharpe-vs-capacity frontier**: small capital (<$1M) = **wide basket + EQUAL-weight** → Sharpe 8–12, maxDD ~5% (breadth is the biggest Sharpe lever found — top-35 legs); large capital ($3–30M) = **wide + LIQUIDITY-weight** → Sharpe 1.3–4.5, $3–8M/yr (depth-proportional sizing so thin legs don't choke; equal-weighting thin small-caps collapses at scale). "Multiple baskets" = deep-major sleeve (capacity) + wide small-cap sleeve (Sharpe). **For the <$10k start, wide equal-weight is the best box (Sharpe ~11, ~5% DD, ~1000× below any impact ceiling).** New caveat: small-caps have fatter idiosyncratic tails (delist/rug) the continuous-reversion model misses → wide-equal-weight Sharpe somewhat overstated; needs a per-leg hard stop + liquidity/listing filter. **Stage-5 shadow trader BUILT** ([findings-14](research/backtest-findings-14.md)): `aquarius/paper/shadow.py` + `scripts/shadow_run.py` run the strategy on real hourly data, simulate honest fills, verify neutrality (coin-leg tilt zeroed by basket hedge → net delta $0/bar), SEND NO ORDERS; deterministic so `--live` hourly accumulates a forward record. Tail guards wired (per-leg 400bps MtM stop, $250k/hr liquidity floor, delist/staleness cut, hedge-rebalance drag). **Honest guard finding:** in-sample they cost ~17%/yr return and barely move the tail (gaps dominate — stops can't prevent 1-bar gaps; diversification already caps the BOOK tail at ~5% maxDD) — BUT the data is **survivorship-biased (all 35 coins survived; no delisting/rug can appear)**, so the liquidity/delist guards protect an UNMEASURABLE permanent-loss tail (keep tight on small-caps, loosen on majors). **Next: schedule `shadow_run.py --live` hourly 4–6wk (Stage-5 window, incl. weekend+event), compare realized-vs-modeled; then higher-fidelity fills (live L2 / Binance testnet).** Earlier pivot/butterfly/PARK detail follows.

> Status (prior): **PIVOT THAT WORKED — short-gamma reversal clears Stage 4 (honest fills); gated only by capacity + a single regime** ([findings-11](research/backtest-findings-11.md)). The universe search flipped the thesis: **every** crypto residual basket MEAN-REVERTS (ext/rev < 0), so the long-gamma butterfly was the wrong side all along — the winning side is its mirror, **short-gamma cross-sectional mean-reversion on a broad 15-alt residual basket** (the standard butterfly *tent*, not the reverse/valley). It survives the falsification gauntlet: not a bid-ask-bounce mirage (holds at 3-bar lag + 80 bps); plain tent beats every reshape (synthetic gamma pays premium PER round-trip → condor/tight-stop lose; tight stop = whipsaw death); and it **clears Stage 4's ≥60% retention bar** under honest state-dependent slippage + carry (Sharpe ~9.3, ~80% retained). FIRST clean stage-pass in the POC. **Two binding blockers remain (not in formal gates): capacity is tiny (~$1.4M/hr/coin → low-hundreds-$k deployable) and it's ONE benign 6-month regime (zero crises tested — a deleveraging cascade fires the −1145bps tail across all 15 legs at once).** Absolute Sharpe 7–12 is NOT a forward number. **Next make-or-break: extend history back through a crash (DefiLlama multi-year) and re-run OOS.** Do NOT scale or paper-trade until OOS + a modeled crisis pass. (Conditionally supersedes the earlier PARK below.) Earlier butterfly/PARK detail follows.

> Status (prior): **POC essentially COMPLETE — thesis does not clear the gate; PARK recommended** ([findings-09](research/backtest-findings-09.md)). The GENUINE multi-leg manifold butterfly was finally built (centroid+residuals+netting+additive long-gamma) and tested: on stablecoins it **bleeds −6.7%/yr and netting adds nothing** (de-pegs are idiosyncratic, not common-factor); on LSTs it's blocked by data + a structurally shrinking opportunity (post-Shanghai redemption closed the de-pegs). Combined with carry (~0.5 Sharpe) and single-axis long-gamma (bleeds across breadth), **both books fail the pre-registered Sharpe ≥1.5 gate.** The convergence/dislocation edge is rare/idiosyncratic/costly/shrinking. POC succeeded at its job (cheap falsification before capital). Earlier Stage-3 detail below.

> Status (prior): **Stage-3 backtests.** #1 NO-GO on naive convergence ([findings-01](research/backtest-findings-01.md)); #2 funding-credited carry is **net-positive (+1 to +6.7%/yr) & low-DD (~1–2%) but Sharpe 0.26–0.66 — FAILS the ≥1.5 gate** ([findings-02](research/backtest-findings-02.md)). Carry concept proven; funding IS the edge. #3 funding-gating REJECTED ([findings-03](research/backtest-findings-03.md)) — at 23 bps round-trip, trading loses; **buy-and-hold dominates** (best = always-on carry, Sharpe 0.41–0.68). Sharpe is ~cost-independent for buy-and-hold → its ceiling is **basis volatility**, so the ONLY lever left is **cut basis-MtM variance**: (a) convexity overlay [necessary next step], (b) diversify legs. Both timing variants falsified. #4 overlay does NOT lift Sharpe ([findings-04](research/backtest-findings-04.md)) — basis mean-reverts so long-gamma bleeds, and with no de-peg in-sample the overlay only shows premium, not payoff (it's tail INSURANCE vs its own stress gate, not a Sharpe-lifter). Sharpe ceiling (~0.5) = basis volatility. Timing + overlay falsified → **only untested Sharpe lever is DIVERSIFICATION** (N uncorrelated carries → Sharpe ≈0.5·√N). #5 diversification WORKS but qualified ([findings-05](research/backtest-findings-05.md)): 4 carries (GOLD/BTC/ETH/SOL), avg corr 0.14, **equal-weight basket Sharpe 1.02 (honest) / inverse-vol 1.65 (clears gate but hindsight)**. GOLD genuinely diversifies; SOL funding went negative (funding-flip risk real). Single benign ~5.5mo regime flatters it; corr→1 in a deleveraging crisis. **Right structure, touches the gate, NOT a clean GO.** #6 robustness suite FAILS ([findings-06](research/backtest-findings-06.md)): 13-leg basket **equal-weight Sharpe 0.47 (no hindsight)**, IS-inverse-vol 1.11, walk-forward ~0 — the earlier 1.65 was hindsight; 4/13 legs had negative funding. Overlay made the synthetic crisis WORSE at every size (rolling-z whipsaws on trends) → fails its own gate. **Branch does NOT clear Sharpe ≥1.5 OOS** (real ~0.5 edge). Deep in the ladder (re-param ✗, reselect ✗, restructure ✗). Carry timing/diversification levers ≈ exhausted (carry book = real but ~0.5-Sharpe; park-ish). **#7 BUTTERFLY CORE = first GO** ([findings-07](research/backtest-findings-07.md)): the distinctive long-gamma idea, tested right (Donchian breakout + **deadband = the "imaginary tip" zone**) on the March-2023 USDC de-peg, **captured +546 bps with ~0 calm bleed over 9.5mo, 7 trades, payoff/bleed 26×** — flat tip, profitable wings, as designed. **#8 corrects #7** ([findings-08](research/backtest-findings-08.md)): multi-axis basket (5 stablecoin axes, ≤4.4y) **BLEEDS −2761 bps (−6.2%/yr), skew −1.6, payoff/bleed 0.3×** — only USDC (clean slow de-peg) was net-positive. Failure modes: noisy pegs bleed through a fixed deadband; **fast wicks MISSED (synthetic option-free gamma can't catch instantaneous jumps — structural cost of no-options); clean slow de-pegs are rare.** Butterfly captures only rare clean dislocations; not a standalone strategy; can't cleanly combine with carry (different instruments/windows). **STATE: both books individually fail Sharpe ≥1.5 (carry ~0.5; butterfly bleeds). At the PARK-AND-RETHINK rung.** Options: (1) park branch; (2) pivot to LSTs (carry + de-peg tail on SAME asset, needs on-chain data); (3) descope to opportunistic de-peg sniper. Do NOT paper-trade. (Recon: [research/recon-report.md](research/recon-report.md).)
> **Gate status:** cost-side numbers are pinned from recon; **edge-side thresholds (Sharpe, edge size) stay provisional** — they CANNOT be frozen until Stage-2 forward-collects the actual spread distribution. Do not move thresholds mid-stream to rescue a result.

## Stage-0 decisions (ratified from recon)
- **Cost-calibration venue:** Hyperliquid (best L2/funding data via Tardis from 2024-10-29; also the gold-perp venue). Benchmark: Drift/Solana (−0.25 bps flat maker rebate) as the cheap home for pure crypto-perp legs.
- **First edge/carry leg:** tokenized-gold **cash-and-carry** — long XAUT (tighter tracking) or PAXG spot vs short a crypto-rail gold perp (Hyperliquid HIP-3 gold or Kraken GLDx). Wrapper-spread (PAXG↔XAUT) is secondary, pending a shortable venue. Trade the spot leg on a **CEX** (no gas), since PAXG/XAUT are Ethereum ERC-20s.
- **Data stack:** Tardis.dev (L2 + funding/mark/OI) + CoinGlass API V4 (funding OHLC); **forward-collect tokenized-gold prices ourselves**.
- **Measured cost reality:** maker ≈ −0.25 bps (Drift) to +1.5 bps (Hyperliquid) per side, pre-slippage; spot leg adds CEX fees.
- **⚠️ Yellow flags:** recon **refuted** "tokenized gold trades at a 0.5–2.5% discount" and "dislocations cluster on weekends." Do not presume a fat or weekend-clustered gold spread — **measure it.**

## What this is
A market-neutral crypto trading engine built from two complementary books:
1. **Carry / manifold book** — a delta-neutral, multi-leg structural + statistical arbitrage over the linked native + tokenized-RWA universe ("same underlying, multiple wrappers" convergence; trade deviations off a no-arbitrage manifold). *Short-gamma, steady micro-income.*
2. **Convexity overlay** — an **option-free synthetic long-gamma "manifold butterfly":** a multi-crypto basket running per-spread synthetic-gamma (breakout / reverse-grid) rules, netted delta-neutral. The **"imaginary tip"** sits at the manifold centroid (computed, steerable). Because the legs are **no-expiry perps/spot (not options)**, the tip is a **contingent mark-to-market drawdown, never force-realized by a clock** → we do **NOT** finance it to zero; we run a **deeper tip to maximize the wings**, with depth treated as a **bounded risk-budget** (capped by margin headroom, a carry-bleed ceiling, a hard max-MtM / max-time-in-tip stop, and de-peg-survivable sizing). Steerable via signal, but with a **hard cut rule** — if MtM keeps deepening toward the margin/de-peg line and can't be steered out, cut (unrealized is one move from forced). Redundant legs make it **scalpable** (bank profitable legs while a rotation engine keeps net delta ≈ 0, gamma > 0). *Long-gamma, caps the carry book's de-peg tail.*

## North-star objective
A high-Sharpe, **steady micro-compounding** equity curve that scales slowly on proof, with **bounded, positive-skew tails** — not home-runs. Success = the combined book clears its honestly-measured cost-hurdle with margin, live, across regimes.

## The core law (everything is measured against this)
> **edge only exists when realized edge > honestly-measured cost-hurdle (fees + slippage + funding + gas).**
Signal cleverness is secondary. Every claim is judged net of pessimistic costs.

## Hard constraints (non-negotiable design rules)
- **Strictly delta-neutral** at all times — neutrality is an invariant to verify each cycle, never assumed.
- **Crypto-only execution** — CEX + DeFi + tokenized RWAs on crypto rails. **No** TradFi brokerage / FX / futures / equities accounts.
- **No listed options** — convexity is manufactured via synthetic gamma (perps) or nonlinear legs. *(Hard law: a static linear basket has zero gamma.)*
- **Cheap chains / maker rebates** (Solana, L2s, Hyperliquid). **Avoid Ethereum L1** — the cost floor kills micro edges.
- **Cap tails** even though all risk types are nominally acceptable; the overlay must cover the carry book's worst modeled de-peg.
- **Start < $10k; scale only on live metrics**, never on conviction.

---

## POC stages & GO / NO-GO gates
Advance only on GO. The POC's job is to **falsify cheaply.**

**A NO-GO is a pivot trigger, not a hard wall.** It halts *advancing on the current path* and opens a structured pivot review — it does **not** mean "kill the project," and it never means "push through anyway." When a gate fails, walk the pivot ladder (cheapest first):
1. **Re-parameterize** — band width, leg-count, rebalance cadence, cost/venue choice (maker vs taker, cheaper chain).
2. **Reselect inputs** — different instrument / wrapper-spread / chain / basket with better liquidity or data.
3. **Restructure** — change the leg geometry, the convexity source (rule vs nonlinear legs), or how the two books combine.
4. **Descope** — ship the part that *does* clear its gate (e.g., carry book alone) and defer the rest.
5. **Park** — shelve the branch with a written reason and revisit if conditions (liquidity, fees, new venues) change.

Only after the ladder is genuinely exhausted is a branch killed — and that decision is logged with the evidence. Record every NO-GO + chosen pivot so we don't loop on the same dead end.

### Stage 0 — Pre-register
- **Objective:** lock hypotheses, thresholds, and target instruments (via recon).
- **Deliverable:** ratified gates (this doc) + chosen chain/instruments.
- **GO:** hypotheses are falsifiable; thresholds written; target instruments have plausible liquidity + data.
- **NO-GO:** can't state a falsifiable test → idea isn't ready.

### Stage 1 — Cost/fill model (the linchpin)
- **Objective:** measure true cost on one liquid perp with tiny real orders.
- **Deliverable:** calibrated model — fees, slippage vs size, maker-fill probability, queue behavior, funding, gas.
- **GO:** model predicts realized cost within **±20%** on out-of-sample live micro-orders.
- **NO-GO:** costs unpredictable, or structurally larger than the smallest plausible edge → pivot (cheaper venue/chain, maker-only, or reselect instrument).

### Stage 2 — Data layer
- **Objective:** recorder running; sufficient, clean history.
- **Deliverable:** L2 books + funding + oracle/mark + tokenized-RWA prices, timezone-correct (incl. weekends/holidays). Forward-collect (RWA history is thin).
- **GO:** gap-free data for target instruments over **≥ 6 weeks** and accumulating.
- **NO-GO:** instruments lack liquidity/data to ever measure the edge → reselect.

### Stage 3 — Vectorized backtest (pessimistic costs)
- **Objective:** does the edge exist net of conservative costs?
- **Deliverable:** OOS PnL; **cost-sensitivity curve**; regime-conditional PnL; **carry and convexity validated separately**, then combined.
- **GO (all must hold):**
  - Carry book OOS net-of-cost annualized **Sharpe ≥ 1.5**.
  - Edge survives to **≥ 1.5× measured cost** (robustness margin).
  - **Max drawdown ≤ 10%.**
  - Overlay: calm-regime bleed **≤ 1% / month** AND cuts de-peg-stress drawdown by **≥ 50%**.
- **NO-GO:** edge < cost; only works at unrealistic costs; Sharpe < 1; or DD > 20%.

### Stage 4 — Event-driven fill simulation (honest fills)
- **Objective:** survive realistic fills; rotation engine holds neutrality.
- **Deliverable:** tick-level PnL with queue/partials/latency/maker-non-fills; Greek-tracking report.
- **GO:** retains **≥ 60%** of Stage-3 Sharpe under realistic fills; net delta within tolerance of 0 and gamma > 0 throughout scalping/rotation.
- **NO-GO:** fills cut Sharpe > 50%, or rotation can't maintain neutrality.

### Stage 5 — Paper / shadow-live
- **Objective:** measure the backtest-vs-reality gap across regimes + tail.
- **Deliverable:** **≥ 4–6 weeks** on live data (orders generated, micro/zero sent), incl. a weekend, an event, and a de-peg stress test.
- **GO:** realized (paper) edge **≥ 70%** of Stage-4 modeled edge; no regime yields an un-modeled blowup; ops stable (uptime, reconnection, kill-switch fire-drill passes).
- **NO-GO:** large unexplained gap, or any un-modeled tail appears.

### Stage 6 — Tiny live ($100–500)
- **Objective:** confirm real-money fills match paper; exercise full ops. *(Profit is NOT the goal.)*
- **Deliverable:** **≥ 4 weeks** tiny-live track record.
- **GO:** live net edge within tolerance of paper; ≥ breakeven after ALL costs; DD within budget; zero risk-limit/ops incidents.
- **NO-GO:** live underperforms paper beyond tolerance, or any risk-limit breach / ops failure.

---

## Capital scaling ladder (only after Stage 6 GO)
- **Phase 1 ($1–10k):** compound; the standard scorecard must hold for **≥ 8–12 weeks live** before any step up.
- **Phase 2 (10× steps):** each step gated on the live scorecard clearing the bar over a sustained window. **Never scale on a single good week.**
- Diversify into new manifold axes as capacity nears on existing ones.

## Standard scorecard (used at every gate)
- Net edge per trade after **all** costs
- Annualized net-of-cost Sharpe
- Max drawdown + longest drawdown duration
- Fill rate / realized-vs-modeled edge ratio
- Regime-conditional PnL (trend / chop / weekend / event)
- Greek tracking-error (net delta, net gamma)
- De-peg / tail-stress coverage (does the overlay cover the carry book's tail?)
- Capacity headroom

## Hard risk rules (always on once live)
- Per-position and per-book max loss; **daily-loss kill-switch.**
- Max leg-count / complexity budget (fees overtake edge past the optimum).
- No naked directional exposure; re-verify neutrality each cycle.
- Overlay sized to cover the carry book's worst modeled de-peg.
- Convexity-overlay **tip depth is a bounded risk-budget**: cap max unrealized MtM drawdown and time-in-tip; size depth to survive a wrapper de-peg; enforce a **hard cut** if steering cannot arrest a deepening tip (unrealized → forced via liquidation/de-peg).
- Per-venue counterparty caps.

## Out of scope / rejected
Oracle-staleness arb (commoditized); pure 2-leg pairs; cross-*underlying* correlation pairs (not truly neutral); any TradFi leg; listed options; Ethereum L1 for execution; home-run / high-variance bets.

## Stack & working principles (binding for anyone working in this repo)
- **Stack:** Python (polars/numpy/pandas) for research; CCXT / venue SDKs for connectivity; a **custom event-driven fill simulator we own** (no black-box backtest frameworks for fills); faster live engine later only if measured latency demands it.
- **Build to falsify** — surface what kills the idea, fast and cheap.
- **Pre-register thresholds; never move goalposts** to rescue a result.
- Every strategy claim needs an **OOS, cost-inclusive** number. **Never present a backtest without its cost-sensitivity curve.**
- Default to **pessimistic** cost/fill assumptions.
- **Validate carry and convexity books separately** before combining.
- Treat **delta-neutrality as an invariant** — verify it in code, don't assume it.
