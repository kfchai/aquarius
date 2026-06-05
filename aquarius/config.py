"""Load the recorder/cost-model config (config/instruments.yaml)."""

from __future__ import annotations

import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "instruments.yaml"


def load_config(path: str | pathlib.Path | None = None) -> dict:
    path = pathlib.Path(path) if path else DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
