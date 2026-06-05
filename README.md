# Aquarius

Delta-neutral, crypto-only market-neutral edge engine. See **[CLAUDE.md](CLAUDE.md)** for the
full charter and go/no-go gates, **[GLOSSARY.md](GLOSSARY.md)** for terms, and
**[research/recon-report.md](research/recon-report.md)** for the Stage-0 decisions.

## What this code is (Stage 1 + 2)
The recon found that the tokenized-gold edge has **no usable price history** — it must be
**forward-collected**. This package does that and lays the cost-model foundation:

- **Recorder** — polls live public APIs and logs, every ~10s:
  - Hyperliquid HIP-3 gold perp **`xyz:GOLD`** (mark/oracle/funding/OI + L2 top-of-book)
  - **XAUT** and **PAXG** spot (Binance, Bybit, Kraken) via ccxt
  - derived **wrapper-spread** (PAXG vs XAUT), **cash-and-carry basis** (spot vs perp), **funding APR**
- **Cost model** — turns fees + observed book spreads into a round-trip cost (bps), so any
  measured edge is judged against the cost-hurdle (the core law).

## Setup
```bash
pip install -r requirements.txt
```

## Use
```bash
python scripts/smoke_test.py             # one live poll + cost-model sanity (no keys)
python scripts/run_recorder.py           # forward-collect (Ctrl-C to stop; flushes on exit)
python scripts/compact_to_parquet.py     # JSONL -> parquet for analysis
python tests/test_metrics.py             # offline unit tests
python tests/test_costmodel.py
```

Data lands in `data/snapshots/snapshots-YYYY-MM-DD.jsonl` (git-ignored).

## Layout
```
aquarius/            package: adapters/, recorder, metrics, costmodel, storage, config
config/instruments.yaml   venues, symbols, fees (Stage-0 decisions)
scripts/             run_recorder, smoke_test, compact_to_parquet
tests/               offline unit tests (no pytest needed)
research/            recon brief + report
```

## Status
Stage-0 recon complete. **Next:** run the recorder to accumulate the spread/basis/funding
distribution (the data the go/no-go gates depend on), and calibrate the cost model on Hyperliquid.
Edge-side thresholds stay provisional until this data exists.
