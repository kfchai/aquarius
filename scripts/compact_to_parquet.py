"""Compact recorded JSONL snapshots into a single parquet for analysis.

    python scripts/compact_to_parquet.py [data/snapshots] [out.parquet]
"""

import pathlib
import sys

import pandas as pd


def main() -> int:
    data_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/snapshots")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else data_dir / "snapshots.parquet")
    files = sorted(data_dir.glob("snapshots-*.jsonl"))
    if not files:
        print(f"no JSONL files in {data_dir}")
        return 1
    frames = [pd.read_json(f, lines=True) for f in files]
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.sort_values("ts_ms").reset_index(drop=True)
    df.to_parquet(out, index=False)
    print(f"compacted {len(files)} files -> {out}  ({len(df):,} rows, {df.shape[1]} cols)")
    print(f"range: {df['ts'].min()} .. {df['ts'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
