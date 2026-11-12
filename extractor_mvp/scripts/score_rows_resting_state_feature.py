#!/usr/bin/env python3
"""Score the `resting_state_feature` sheet of ground_truth/preproc_rows_labels_v1.xlsx against the latest stored
records. Pre-registered 2026-11-11, before any label on this sheet exists; the rules are
preproc_rows_scoring_v2.py's.

Usage (openpyxl reads the workbook; it is not a dependency of this package):
    uv run --with openpyxl python scripts/score_rows_resting_state_feature.py [--results-dir DIR] [--out FILE]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from preproc_rows_scoring_v2 import main

if __name__ == "__main__":
    raise SystemExit(main("resting_state_feature"))
