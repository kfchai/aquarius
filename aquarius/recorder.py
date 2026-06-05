"""Recorder loop: poll all venues, compute edge metrics, persist crash-safely.

Built to run unattended for weeks. A single failing fetch must never kill the loop
(per-quote try/except); data is buffered and flushed on an interval and on shutdown.
"""

from __future__ import annotations

import datetime as dt
import time

from .adapters import CexSpotAdapter, HyperliquidAdapter
from .metrics import compute_metrics
from .storage import JsonlWriter


class Recorder:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.poll_interval = float(cfg.get("poll_interval_sec", 10))
        self.flush_interval = float(cfg.get("flush_interval_sec", 60))
        self.writer = JsonlWriter(cfg.get("data_dir", "data/snapshots"))

        hl = cfg["hyperliquid"]
        self.hl = HyperliquidAdapter(hl["api_url"], hl.get("timeout_sec", 15))
        self.perp_specs = hl.get("perps", [])

        # one ccxt client per exchange, plus the flat (exchange, symbol, label) list
        self.cex_adapters: dict[str, CexSpotAdapter] = {}
        self.cex_specs: list[tuple[str, str, str]] = []
        for entry in cfg.get("cex_spot", []):
            exid = entry["exchange"]
            self.cex_adapters[exid] = CexSpotAdapter(exid)
            for s in entry["symbols"]:
                self.cex_specs.append((exid, s["symbol"], s["label"]))

        self.metrics_cfg = cfg.get("metrics", {})

    def poll_once(self) -> dict:
        quotes: dict = {}
        errors: list[str] = []

        for spec in self.perp_specs:
            try:
                q = self.hl.fetch_perp(spec["coin"], spec["dex"], spec["label"])
                quotes[spec["label"]] = q
            except Exception as e:  # noqa: BLE001 - never let one venue kill the loop
                errors.append(f"{spec['label']}:{type(e).__name__}")

        for exid, symbol, label in self.cex_specs:
            try:
                q = self.cex_adapters[exid].fetch(symbol, label)
                quotes[label] = q
            except Exception as e:  # noqa: BLE001
                errors.append(f"{label}:{type(e).__name__}")

        ts_ms = int(time.time() * 1000)
        row = {
            "ts_ms": ts_ms,
            "iso": dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc).isoformat(),
            "n_ok": len(quotes),
            "n_err": len(errors),
        }
        if errors:
            row["errors"] = ",".join(errors)
        for q in quotes.values():
            row.update(q.to_flat())
        row.update(compute_metrics(quotes, self.metrics_cfg))
        return row

    def run(self) -> None:
        print(
            f"[recorder] poll={self.poll_interval}s flush={self.flush_interval}s "
            f"perps={len(self.perp_specs)} cex={len(self.cex_specs)} "
            f"-> {self.writer.data_dir}"
        )
        last_flush = time.monotonic()
        n_polls = 0
        try:
            while True:
                t0 = time.monotonic()
                row = self.poll_once()
                self.writer.write(row)
                n_polls += 1
                if time.monotonic() - last_flush >= self.flush_interval:
                    n = self.writer.flush()
                    last_flush = time.monotonic()
                    self._heartbeat(n_polls, n, row)
                # keep cadence steady regardless of fetch latency
                time.sleep(max(0.0, self.poll_interval - (time.monotonic() - t0)))
        except KeyboardInterrupt:
            print("\n[recorder] shutting down — flushing buffer...")
        finally:
            n = self.writer.flush()
            self.hl.close()
            print(f"[recorder] flushed {n} buffered rows. bye.")

    @staticmethod
    def _heartbeat(n_polls: int, n_flushed: int, row: dict) -> None:
        bits = [f"polls={n_polls}", f"flushed+={n_flushed}", f"ok={row.get('n_ok')}"]
        for k, v in row.items():
            if k.startswith("wspread_") or k.startswith("basis_") or k.endswith("_funding_apr"):
                if isinstance(v, (int, float)):
                    bits.append(f"{k}={v:.2f}")
        print(f"[recorder] {row['iso']} " + " ".join(bits))
