"""Crash-safe snapshot sink.

JSONL (append-only, one snapshot per line) is the primary sink — a recorder that
must run for weeks prioritizes never losing data and never crashing over query
ergonomics. Compact to parquet for analysis via scripts/compact_to_parquet.py.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib


class JsonlWriter:
    def __init__(self, data_dir: str | pathlib.Path):
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []

    @staticmethod
    def _date_str(ts_ms: int) -> str:
        return dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")

    def write(self, row: dict) -> None:
        """Buffer a snapshot (flushed on flush())."""
        self._buffer.append(row)

    def flush(self) -> int:
        """Append buffered rows to date-partitioned JSONL files. Returns rows written."""
        if not self._buffer:
            return 0
        # group by UTC date so a flush spanning midnight lands in the right files
        by_date: dict[str, list[dict]] = {}
        for row in self._buffer:
            by_date.setdefault(self._date_str(row["ts_ms"]), []).append(row)
        n = 0
        for date, rows in by_date.items():
            path = self.data_dir / f"snapshots-{date}.jsonl"
            with open(path, "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, separators=(",", ":")) + "\n")
                    n += 1
        self._buffer.clear()
        return n
