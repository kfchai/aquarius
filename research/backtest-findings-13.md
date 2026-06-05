# Backtest Findings #13 — capacity & breadth: the dollar value, and the Sharpe-vs-capacity frontier

_Two studies on the validated reversal basket (findings-11/12): (1) capacity-realistic sizing with
true sqrt-impact per fill (`scripts/capacity_sizing.py`, 11 coins/5y), and (2) the "many tiny legs"
breadth test (`scripts/backfill_broad.py` + `breadth_capacity.py`, 35 coins/3y). Impact model:
impact_bps = K·√(order/bar-$vol), K=100 (1% participation → 10 bps/side), on top of honest fills._

## 1. Capacity is BIGGER than the earlier ~$150k guess
The earlier guess used median-coin volume × 1% participation. True impact at that size is negligible
(0.3% participation). Real picture (11 coins, 5y, equal-weight):
| gross $ | Sharpe | net $/yr | maxDD% |
|---|---|---|---|
| $100k | 6.8 | $109k | −8.7 |
| $1M | 5.2 | $842k | −9.7 |
| $3M | 3.6 | $1.74M | −14.8 |
| $10M | 0.8 | $1.3M | −44 |
Equal-weight peaks in dollars ~$3M; liquidity-weight (11 coins) pushes to ~$10M (Sharpe 2.2,
$4.6M/yr) by concentrating in BTC/ETH (lower Sharpe, deeper DD).

## 2. Breadth: more legs → much higher Sharpe; capacity needs depth-aware weighting
Top-N by volume from the 35-coin set (3y, 2023-06+, equal-weight):
| breadth | Sharpe @$100k | maxDD% | net$/yr ceiling | Sharpe @$10M |
|---|---|---|---|---|
| top-10 | 6.8 | −7.4 | $1.68M | 0.76 |
| top-20 | 9.95 | −7.2 | $1.92M | 1.42 |
| top-35 | **11.65** | **−5.1** | $1.45M (collapses) | 0.10 |

Breadth is the biggest **Sharpe** lever found (top-35 = 11.7 @ −5% DD at small size). But equal-
weighting THIN coins (MANA/EGLD/FLOW ~$0.1M/hr) **chokes at scale** — top-35 collapses at $10M.
The fix is depth-aware sizing, not fewer legs:
| top-35 @ $10M | Sharpe | net $/yr |
|---|---|---|
| equal-weight | 0.10 | $0.1M |
| **liquidity-weight** | **3.24** | **$6.87M** |
liq-weighted top-35 scales to $30M (Sharpe 1.3, $8.3M/yr).

## 3. The frontier (pick weighting by capital)
| capital | structure | Sharpe | maxDD | note |
|---|---|---|---|---|
| <$1M | wide + EQUAL-weight | 8–12 | ~5% | max diversification; impact irrelevant |
| $3–30M | wide + LIQUIDITY-weight | 1.3–4.5 | ~15–22% | dollars follow depth |
"Multiple baskets" = run two sleeves (deep-major liq-weighted for capacity + wide small-cap equal-
weight for Sharpe), allocate by capital. **For the <$10k start, wide equal-weight is the best box on
the board** (Sharpe ~11, ~5% DD, ~1000× below any impact ceiling).

## Caveats (sharper for the wide book)
- **3y window (no 2022 crisis)** in the 35-coin set → absolute Sharpe runs higher than the crisis-
  tested 5y number; trust the RELATIVE breadth comparison, not the level.
- **Small-caps have fatter idiosyncratic tails** (delist/rug = permanent loss) the continuous
  reversion model does NOT capture → wide-equal-weight Sharpe is somewhat overstated; a real book
  needs a hard per-leg stop + liquidity/listing filter.
- **K=100 impact is an estimate**; worse real impact lowers every ceiling.

## State / next
Edge is validated (findings-12) AND has real, quantified capacity: a high-Sharpe small-capital book
(<$1M, wide equal-weight) scaling to a lower-Sharpe multi-$M book (liq-weight). Matches the "<$10k
start, micro-compound, scale on proof" mandate. Remaining before live: (a) add per-leg hard stop +
liquidity/listing filter and re-measure the wide book's tail honestly; (b) charge hourly hedge-
rebalance cost; (c) then Stage 5 paper/shadow-live.
