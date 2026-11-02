"""The population the 2026-11-02 scope rule for software_mentions aims at (the author's queued fix).
No model calls: the prompt change cannot be replayed without a draw, so this counts, per paper, the
stored mentions and those the checking pass marked as not used for preprocessing -- the mentions the
new prompt line tells call S not to list. Names are field values; no quote text is printed. The three
held-out papers are counts only.

Usage:
    python scripts/software_scope_population.py results/batch_coverage_v3
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def main(argv: list[str] | None = None) -> int:
    results = Path((argv if argv is not None else sys.argv[1:])[0])
    tot = out = 0
    held = [0, 0]
    for f in sorted((results / "papers").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d["paper_id"]
        mentions = (d.get("preprocessing") or {}).get("software_mentions") or []
        names = [
            m["extraction"]["value"]["name"]
            for m in mentions
            if m["extraction"]["status"] == "EXTRACTED"
        ]
        sw = ((d.get("verifier") or {}).get("software")) or {}
        not_pre = [n for n in names if sw.get(n) is False]
        if pid in _HELD:
            held[0] += len(names)
            held[1] += len(not_pre)
            continue
        tot += len(names)
        out += len(not_pre)
        print(
            f"{pid:<22} mentions {len(names):>2}  not preprocessing per the checking pass {len(not_pre):>2}  {', '.join(not_pre)}"
        )
    print(f"TOTAL contaminated+unseen: mentions {tot}, not preprocessing {out}")
    print(f"held-out three, counts only: mentions {held[0]}, not preprocessing {held[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
