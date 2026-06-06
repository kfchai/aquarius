# The Aquarius Strategy — in Plain Language

A no-jargon explanation of what this trading strategy does, why it works, what can go
wrong, and where it stands. If you only read one thing, read the next paragraph.

> **The one-sentence version:** When one crypto coin drifts out of line with the rest of
> the pack, we bet it drifts back into line — doing this across many coins at once, sized
> so the overall bet on "will crypto go up or down?" cancels out to zero.

---

## 1. The core idea: betting on the pack

Picture the major crypto coins — Bitcoin, Ethereum, Solana, and a few dozen others — as a
**pack of runners**. Most of the time they move together: when the whole market is up, they're
all roughly up; when it's down, they're all down. That shared movement is just "the market."

But at any given moment, one runner is usually a little **ahead of the pack** (it ran up more
than its peers) or a little **behind** (it lagged). Our entire strategy is built on one
observation, which we verified across years of data:

> **A coin that has pulled away from the pack tends to drift back toward it.**

It's a rubber-band effect. Stretch one coin away from its peers and, on average, it snaps
back. We're not predicting where the *whole pack* is running — we're betting that the
**gap between one runner and the pack closes**.

---

## 2. Why we don't care which way the market goes

This is the part that makes it safe-ish and unusual. We are **not** betting that Bitcoin goes
up, or that crypto crashes. We bet only on the **gap** between a coin and its peers — and we
do it with equal-and-opposite positions, so the market's direction washes out.

Here's the trick. Say Solana lags the pack — everyone's up 10% but Solana's only up 4%. Solana
is now "cheap relative to its peers." We **buy Solana and sell the basket of its peers** in
equal dollar amounts. Now two things can happen, and **we win either way**:

- Solana catches up (rises from +4% toward +10%), **or**
- The pack falls back toward Solana (drops from +10% toward +4%).

Either way the *gap* closes, and our buy-vs-sell pair profits. If the entire market suddenly
crashes 20%, our long (Solana) and our short (the basket) both fall together and **cancel** —
we barely notice. That's what "market-neutral" means: we've stripped out the up/down question
entirely and kept only the "is this coin in line with its peers?" question.

We verify this neutrality every single cycle. It's the one rule we never break.

---

## 3. How a single trade plays out, start to finish

Every coin gets a score each hour — call it its **stretch**. A stretch of 0 means "perfectly
in line with the pack." A large positive stretch means "unusually rich vs peers"; a large
negative one means "unusually cheap." (In the code this score is a *z-score*; we measure it in
"σ" — standard deviations from normal.)

1. **Enter** when a coin is clearly stretched — a stretch of **1.5σ or more.** If it's rich,
   we short it (and buy the basket); if it's cheap, we buy it (and short the basket).
2. **Wait** while the rubber band pulls it back. The coin's stretch shrinks toward 0 as it
   rejoins the pack. (On average this takes a couple of days — it's a gentle pull, not a
   violent snap.)
3. **Take profit** when the stretch falls back to nearly 0 (**0.3σ or less**) — the gap has
   closed, so we close the trade and bank it.
4. **Cut the loss** if instead the coin keeps stretching *away* (to 5σ, or a set dollar loss).
   That means the rubber band "broke" — usually the coin is genuinely re-rating (news, a hack,
   a delisting), not just wobbling. We get out before it gets worse.

We run this on ~20–35 coins simultaneously, opening and closing legs independently as each
one stretches and snaps back.

**A picture helps.** If you plot "how good is our position?" against "how stretched is the
coin?", you get a **tent shape**: we're happiest (most profit) when the coin is back near the
pack at the peak, and we lose out on the sloping sides if it stretches far. Each open trade is
a dot trying to **climb to the top of the tent** (the gap closing). Reach the top → bank it.
Slide off the side → stop-loss.

---

## 4. Why this actually makes money (the honest reason)

We're not smarter than the market. We're getting paid for a **service**: providing liquidity
to impatient traders.

When someone *needs* to buy or sell a coin right now — a big order, a forced liquidation, a
panic — they push its price away from where its peers say it "should" be. They pay for that
immediacy. By taking the other side (buying what they're dumping, selling what they're
grabbing) and waiting for the price to settle back, we **collect that premium.** We're the
calm counterparty who steps in and gets paid for patience.

This is a real, decades-old phenomenon — finance professors call it "short-term reversal,"
and stat-arb desks have traded it in stocks since the 1990s. **It's not a secret and not a
trick.** Our advantage isn't that we discovered something new; it's that crypto lets a small
player actually capture it (see §9).

---

## 5. What drives the pattern

The rubber band only works because two forces are out of balance: something **pushes** a coin
out of line quickly, and something else **pulls** it back more slowly.

**What pushes a coin out of line (the stretch)** — all temporary, non-fundamental pressure:

- **Someone needs to trade now.** A whale, a fund rebalancing, an OTC desk unwinding — a big
  order in a thin market shoves one coin's price away from its peers. This is the main driver.
- **Forced liquidations.** Crypto runs on heavy leverage; when a coin dips, leveraged bets get
  auto-closed, dumping at any price and *overshooting*. (This is exactly why the strategy earns
  *more* in panics — more forced flow to lean against.)
- **Retail overreaction.** A tweet, a listing, a fear headline — people pile into or bail out
  of one coin and overshoot before the news is digested.
- **Thin, fragmented liquidity.** Shallow order books mean a given order moves the price more —
  a bigger stretch per dollar traded.

**What pulls it back (the snap)** — because the cause was *flow, not fundamentals*, nothing
holds the coin out of line:

- **Patient capital steps in.** Market makers and arbitrageurs (and us) buy what's being dumped
  and sell what's being grabbed; as that demand for immediacy is satisfied, the price settles
  back in line. *We get paid for being that patient counterparty.*
- **The overreaction fades** and the leverage flush finishes, so the overshoot bounces back.

**Why we measure it *relative to the pack*.** A coin's move has two parts: the **market-wide**
part (which can genuinely trend, and does *not* reliably revert) and the **coin-specific** part
(driven by the flow above, which *does* revert). Subtracting the pack throws away the trending
part and keeps only the revertible part — which is why this is far more reliable than betting
on a lone coin reverting.

**The flip side.** Sometimes a coin moves for a *real, lasting* reason — a hack, a delisting, a
genuine re-rating. Those don't revert, and they're the source of our occasional large losses.
The bet is that flow-driven dislocations dominate *on average*; the stops (§7) handle the ones
that don't.

*(Crypto supercharges every one of these forces — see §9.)*

---

## 6. Why many coins instead of one

Three reasons, all important:

- **The pull is gentle.** On any single coin the effect is small and noisy. But run it across
  35 coins at once and the small edges add up into something steady. Breadth is the biggest
  driver of how smooth the returns are.
- **Safety in numbers.** If one coin's rubber band breaks (it gets delisted, say), that's one
  bad leg out of 35 — a scratch, not a wound, *as long as each leg is sized small.*
- **More room to grow.** Each coin can only absorb so much money before our own trading moves
  its price. Spreading across many coins lets the whole strategy hold more capital.

---

## 7. What can go wrong — and how we handle it

This strategy has a specific risk personality: **lots of small wins, with occasional larger
losses.** (The opposite of a lottery ticket.) The dangerous moment is when a coin we're
holding *doesn't* revert — it keeps stretching away. Our defenses, in order of importance:

1. **Diversification** — many small legs, so no single blow-up can sink the book.
2. **A hard stop on each leg** — if a coin stretches to 5σ or loses a set amount, we cut it
   and admit "this one isn't reverting."
3. **Small, survivable sizing** — every position is sized so that even a total wipeout of one
   leg is bearable.
4. **A liquidity / delisting filter** — we stop trading a coin if its trading volume dries up
   or it looks halted (the early-warning sign of a coin going to zero).
5. **Neutrality checks every cycle** — we confirm the book has no accidental bet on market
   direction.
6. **A whole-book kill-switch** for the genuinely scary scenario: a market-wide panic where
   *every* coin stretches at once and the usual diversification temporarily fails. In that
   case we pull risk down rather than trusting the average.

Honest note: every one of these protections costs a little return (a stop sometimes cuts a
trade that *would* have reverted). That's the price of not blowing up, and we pay it on
purpose.

---

## 8. The shape of the returns

- **Wins often, wins small** (historically ~70–75% of trades profitable).
- **Loses rarely, but a bad leg can be large** — which is exactly why the stops and the
  diversification matter.
- **Steady, not explosive.** The goal is a smooth, slowly-compounding equity curve — small
  consistent gains — not home-run bets.

---

## 9. Why crypto, and not stocks?

The *same* effect exists in stocks, commodities, bonds, and currencies — it's universal. But
in those markets it's been competed down to razor-thin margins by giant funds with near-zero
costs, and a small account can't profitably trade it there.

Crypto is the sweet spot for a small player because:

- **Retail-driven overreaction** makes the rubber band stretch further (bigger edge).
- **Easy to short** any coin via perpetual futures, 24/7.
- **Less institutional competition** (for now) than equities.
- **Fragmented, less efficient** — exactly where these gaps live.

So our edge isn't the *signal* (everyone knows it) — it's the **access**: crypto lets us
harvest cheaply, at small size, what big markets reserve for giants. That advantage will
slowly shrink as crypto matures, which we accept.

---

## 10. How big can it get?

This is a **small-capital edge by nature.** Our own trading starts to move prices once the
book gets large, which eats the return. Roughly:

- Under ~$1 million: the edge is essentially untouched — ideal for a small, compounding account.
- A few million: still works, but returns thin out as our footprint grows.
- Tens of millions: only by concentrating in the most liquid coins, at much lower returns.

It will **never** be a giant-fund strategy. It's designed to start small (under $10k),
compound slowly, and scale only on proof — which suits its nature perfectly.

---

## 11. What we've actually proven

We built this to *try to kill it* cheaply before risking money. It survived every test:

- **It's real, not a data artifact** — it holds up even when we add a realistic trading delay
  and pessimistic costs.
- **It survived 5 years of history**, including the worst crypto disasters (the Terra/LUNA
  collapse, the 3AC and FTX blow-ups) — and was *profitable through each crisis*, because
  in a panic the laggards and leaders both move and the gaps still close.
- **Every single calendar year was positive.**
- **The reversion is visible in the raw data** — dislocated coins measurably drift back to
  the pack, with a roughly two-day half-life.

The big honest caveat: the *historical* numbers look very strong (a high Sharpe ratio), but
that's an idealized backtest. The real, live number will be lower — we just don't yet know by
how much. Which is why we're being careful.

---

## 12. Where it stands now, and what's next

- ✅ **Research & backtesting:** passed.
- ✅ **Paper trading (shadow mode):** built and running. The strategy runs on *live* market
  data, simulates realistic fills, tracks a real forward record — and **sends no real orders.**
  There's a live dashboard to watch it.
- ⏭️ **Next — a tiny live test (~$50 per leg):** not for profit (it'd make pennies), but to
  confirm that *real* fills, fees, and neutrality match what the paper model predicts. This
  needs an order-execution layer with a kill-switch, tested first on an exchange testnet.
- ⏭️ **Then — scale slowly on proof,** never on conviction.

We do not put real money at risk until the paper record matches the model and the tiny-live
test confirms the costs are what we think they are.

---

## The whole thing in five sentences

1. Crypto coins mostly move together; one usually drifts out of line.
2. A coin that's out of line tends to drift back — that's the bet.
3. We hold equal buys and sells so the market's direction cancels — we only bet on the gap.
4. We do it across many coins, with hard stops and small sizes, for steady small gains.
5. It's a known, modest, slow effect — but crypto lets a small account harvest it cheaply,
   and it has survived years of history including the big crashes.
