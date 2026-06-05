"""Run the forward-collection recorder. Ctrl-C to stop (flushes on exit).

    python scripts/run_recorder.py [path/to/config.yaml]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from aquarius.config import load_config  # noqa: E402
from aquarius.recorder import Recorder  # noqa: E402

if __name__ == "__main__":
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else None
    Recorder(load_config(cfg_path)).run()
