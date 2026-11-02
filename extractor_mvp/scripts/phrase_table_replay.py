"""Replay the 2026-11-02 phrase-table change (the author's queued fix) over stored coverage records.
No model calls.

Every ``<kind>.performed`` diagnostic stored with ``value_unsupported_by_quote`` keeps the model's raw
quote. Each is re-checked against the step's phrase list as it now stands; a pass is a cell that
MOVES from unverifiable to checked under the new table (at run time the check reads the resolved
span, which equals the raw quote unless the span carried repairs -- an upper bound, said so). Adding
phrases cannot make a passing cell fail, so no reverse move exists. **Prints no quote text.**
Contaminated papers are listed by paper and kind; the three held-out papers are counts only.

Usage:
    python scripts/phrase_table_replay.py results/batch_coverage_v2 [results/batch_coverage_v3 ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.quote_support import performed_phrase_supported  # noqa: E402

_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    for results in map(Path, args):
        seen = moved = held_seen = held_moved = 0
        moves: list[tuple[str, str]] = []
        for f in sorted((results / "papers").glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            pid = d["paper_id"]
            for diag in d.get("diagnostics") or []:
                field = str(diag.get("field", ""))
                if not field.endswith(".performed"):
                    continue
                if diag.get("failure_reason") != "value_unsupported_by_quote":
                    continue
                kind = field.rsplit(".", 1)[0]
                ok = performed_phrase_supported(kind, str(diag.get("raw_quote") or ""))
                if pid in _HELD:
                    held_seen += 1
                    held_moved += ok
                else:
                    seen += 1
                    if ok:
                        moved += 1
                        moves.append((pid, kind))
        print(f"== {results.name}")
        print(
            f"  unverifiable performed cells, contaminated: {seen}; MOVE under the new table: {moved}"
        )
        for pid, kind in moves:
            print(f"    {pid:<22} {kind}")
        print(f"  held-out three, counts only: {held_seen} cells, {held_moved} move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
