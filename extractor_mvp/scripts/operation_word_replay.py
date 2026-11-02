"""Replay the 2026-11-02 post-check "an operation word is not a convention value" (the author's queued
fix) over stored records. No model calls.

Every EXTRACTED ``intensity_normalization.convention`` is re-checked with
quote_support.is_operation_word_only; a hit is a cell that MOVES from extracted to unverifiable
(``operation_word_not_value``). **Prints the returned value only, never quote text**, and only for
contaminated papers; the three held-out papers are counts only.

Usage:
    python scripts/operation_word_replay.py results/batch_coverage_v3 [more result dirs ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.quote_support import is_operation_word_only  # noqa: E402

_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
_DOTTED = "intensity_normalization.convention"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    for results in map(Path, args):
        n = held_n = held_moved = 0
        moves: list[tuple[str, str]] = []
        for f in sorted((results / "papers").glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            pid = d["paper_id"]
            for step in (d.get("preprocessing") or {}).get("steps", []):
                if step.get("kind") != "intensity_normalization":
                    continue
                pf = step.get("convention")
                if not isinstance(pf, dict) or pf["extraction"]["status"] != "EXTRACTED":
                    continue
                value = pf["extraction"]["value"]
                verbatim = value.get("verbatim") if isinstance(value, dict) else str(value)
                hit = is_operation_word_only(_DOTTED, str(verbatim))
                if pid in _HELD:
                    held_n += 1
                    held_moved += hit
                else:
                    n += 1
                    if hit:
                        moves.append((pid, str(verbatim)))
        print(f"== {results.name}: extracted conventions, contaminated {n}; MOVE {len(moves)}")
        for pid, v in moves:
            print(f"    {pid:<22} {v!r}")
        print(f"   held-out three, counts only: {held_n} extracted, {held_moved} move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
