"""Replay item 2 (the author's order of 2026-10-28) over the stored coverage_v1 records. No model calls.

For every ``performed`` cell of the thirteen kinds: an EXTRACTED cell's located quote is checked
against the step's frozen phrase list (quote_support.performed_phrase_supported) -- a miss is a cell
that MOVES to unverifiable under the new rule; a DEFERRED cell is one the never-deferred validator
would now refuse (a reask at run time). **Prints no quote text.** Contaminated papers are listed by
paper and kind; the three held-out papers are counts only.

Usage:
    python scripts/performed_phrase_replay.py [results/batch_coverage_v1]
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.coverage_fields import COVERAGE_KINDS  # noqa: E402
from extractor_mvp.quote_support import performed_phrase_supported  # noqa: E402

_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    results = Path(args[0]) if args else _HERE.parent / "results" / "batch_coverage_v1"
    extracted = collections.Counter()
    moves: list[tuple[str, str]] = []
    held_moves = 0
    deferred: list[tuple[str, str]] = []
    held_deferred = 0
    for f in sorted((results / "papers").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d["paper_id"]
        for step in d["preprocessing"].get("steps", []):
            kind = step.get("kind")
            if kind not in COVERAGE_KINDS:
                continue
            pf = step.get("performed")
            if not isinstance(pf, dict):
                continue
            status = pf["extraction"]["status"]
            if status == "EXTRACTED":
                extracted[pid in _HELD] += 1
                quote = pf["extraction"]["spans"][0]["text"]
                if not performed_phrase_supported(kind, quote):
                    if pid in _HELD:
                        held_moves += 1
                    else:
                        moves.append((pid, kind))
            elif status == "DEFERRED_TO_CITATION":
                if pid in _HELD:
                    held_deferred += 1
                else:
                    deferred.append((pid, kind))
    print(f"performed EXTRACTED cells: contaminated {extracted[False]}, held-out {extracted[True]}")
    print(
        f"== MOVE to unverifiable (quote carries no phrase of its step), contaminated: {len(moves)}"
    )
    for pid, kind in moves:
        print(f"  {pid:<15} {kind}")
    print(f"== the same on the held-out three, count only: {held_moves}")
    print(
        f"== DEFERRED performed cells the validator now refuses (a reask), contaminated: {len(deferred)}"
    )
    for pid, kind in deferred:
        print(f"  {pid:<15} {kind}")
    print(f"== the same on the held-out three, count only: {held_deferred}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
