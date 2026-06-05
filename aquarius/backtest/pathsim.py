"""Intra-candle path simulation.

We only have candle CLOSES, but the strategy's entries/exits happen *within* bars.
So between consecutive closes we synthesize a plausible sub-bar path with a
**Brownian bridge** (pinned at both closes, with intra-bar noise). Running the
strategy over many such random paths (Monte Carlo) tests whether the edge is
robust to the intra-bar dynamics we can't observe — not an artifact of lucky ticks.
"""

from __future__ import annotations

import numpy as np


def estimate_sigma_per_step(closes: np.ndarray, substeps: int, mult: float = 1.0) -> float:
    """Per-substep noise amplitude, scaled from the series' own bar-to-bar moves."""
    closes = np.asarray(closes, float)
    diffs = np.abs(np.diff(closes))
    typical = float(np.nanmedian(diffs)) if len(diffs) else 0.0
    # spread a bar's typical move across its substeps (random-walk scaling)
    return mult * typical / np.sqrt(max(substeps, 1))


def brownian_bridge_path(
    closes: np.ndarray, substeps: int, sigma_per_step: float, rng: np.random.Generator
) -> np.ndarray:
    """Fine path of length (N-1)*substeps + 1, pinned to every close."""
    closes = np.asarray(closes, float)
    n = len(closes)
    if n < 2 or substeps <= 1:
        return closes.copy()
    t = np.linspace(0.0, 1.0, substeps + 1)
    segments = []
    for i in range(n - 1):
        a, b = closes[i], closes[i + 1]
        dW = rng.normal(0.0, sigma_per_step, substeps)
        W = np.concatenate([[0.0], np.cumsum(dW)])
        bridge = W - t * W[-1]            # both ends pinned to 0
        seg = a + (b - a) * t + bridge    # linear drift + bridge noise
        segments.append(seg[:-1])         # drop endpoint (== next segment start)
    segments.append(np.array([closes[-1]]))
    return np.concatenate(segments)
