# Backtest Findings #14 — Stage-5 shadow trader built; tail guards wired; the survivorship caveat

_Built the paper/shadow-live rig (`aquarius/paper/shadow.py` + `scripts/shadow_run.py`): runs the
validated cross-sectional reversal strategy on real hourly data, simulates honest fills, tracks
delta-neutrality, SENDS NO ORDERS. Deterministic, so an hourly `--live` loop just appends the newest
bar and continues a forward track record. Then added the tail guards from findings-13._

## The rig
- Engine mirrors the backtest exactly (residual = coin vs equal-wt basket, 1-bar-lag decisions,
  honest state-dependent slippage + impact + carry). Persists snapshots (`data/shadow/snapshots.jsonl`)
  and trades (`data/shadow/trades.parquet`) each run.
- 45-day replay on real Apr–Jun 2026 data, top-20, $100k gross, guards on: net +$6,968 (+57%/yr),
  Sharpe 6.7, maxDD −2.0%, 249 trades, neutrality verified (coin-leg tilt zeroed by basket hedge →
  net delta $0 every bar).

## Neutrality (a correctness fix)
The residual book is delta-neutral BY CONSTRUCTION: each leg is long-coin-vs-equal-wt-basket, so the
coin-leg tilt (wanders ±40% of gross) is exactly offset by the basket hedge → true net delta = 0.
The monitor now reports both and confirms the invariant each cycle (the hedge is an execution task).

## Tail guards (findings-13 thin-coin risk)
Added: per-leg hard MtM stop (400 bps), liquidity floor (trailing-median $vol ≥ $250k/hr),
delist/staleness cut (12 identical-close bars), hedge-rebalance drag (0.05 bps/bar).

A/B, wide-35, full 3y, $100k:
| | net/yr | Sharpe | maxDD | worst leg | trades |
|---|---|---|---|---|---|
| guards OFF | 120% | 11.65 | −$5,058 | −4052 bps | 12914 |
| guards ON | 100% | 10.95 | −$4,968 | −3555 bps | 10356 |

## The honest reading — guards are insurance against an UNMEASURABLE tail
In-sample the guards cost ~17% of return and barely move the tail, for two reasons:
1. **Gaps dominate; stops can't prevent gaps** — worst legs are one-bar residual jumps; the stop fires
   instantly but exits at the gapped price (−4052 → −3555 only).
2. **Diversification already caps the BOOK tail** — one blown leg at 1/35 weight ≈ $1.1k on $100k;
   maxDD ≈ 5% with or without the per-leg stop. The stop mostly realizes would-have-reverted losses
   (whipsaw) → that's the 17% cost.

BUT: **all 35 coins survived to today — the data is survivorship-biased and CANNOT contain a
delisting/rug.** A live forward book will eventually hold a coin that halts/→0; the liquidity & delist
guards are exactly what prevent that becoming a −100% leg. Their value is invisible in any survivor
backtest by construction. So:
- **Liquid majors:** delisting risk tiny → run looser guards, recover most of the 17%.
- **Wide small-cap book:** permanent-loss tail real & unmeasured → keep guards tight (cheap insurance).

## State / next
Stage-5 rig is live-ready (paper). To accumulate the real forward track record: schedule
`python scripts/shadow_run.py --live` hourly for 4–6 weeks (charter Stage-5 window), incl. a weekend
+ an event, then compare realized paper edge vs modeled. Higher-fidelity fills (live L2 book / Binance
testnet placement) are the next rung after a clean paper run.
