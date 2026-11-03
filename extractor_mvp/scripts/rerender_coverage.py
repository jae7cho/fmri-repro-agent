"""Re-render a coverage vintage's stored records with the CURRENT renderer, the way the batch renders
them (the checking pass, its multiple_pipelines answer, the motion inference), into a NEW directory.
No model calls. Never writes into ``<results-dir>/papers``: the stored reports are the only copy.

Prints, per paper, identical or changed against the stored report; the held-out three as counts.

Usage:
    python scripts/rerender_coverage.py results/batch_coverage_v4 results/batch_coverage_v4_rerender
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))
sys.path.insert(0, str(_HERE.parent.parent / "src"))

from fmri_repro.spec.migrations import parse_any_version  # noqa: E402

from extractor_mvp.methods_finder import MethodsSlice  # noqa: E402
from extractor_mvp.render import to_report  # noqa: E402

_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def main(argv: list[str] | None = None) -> int:
    src, out = (Path(a).resolve() for a in (argv if argv is not None else sys.argv[1:]))
    if out == src or out == src / "papers" or (src / "papers") in out.parents:
        raise SystemExit("refusing to write into the source results directory")
    (out / "papers").mkdir(parents=True, exist_ok=True)
    same: list[str] = []
    changed: list[str] = []
    held_same = held_changed = 0
    for f in sorted((src / "papers").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        pid = data["paper_id"]
        stored = src / "papers" / f"{pid}.md"
        if data.get("preprocessing") is None or not stored.exists():
            continue
        verifier = data.get("verifier")
        extra: dict[str, Any] = {
            "verifier": verifier,
            "multiple_pipelines": (verifier or {}).get("multiple_pipelines"),
        }
        rec = data.get("motion_inference")
        if isinstance(rec, dict):
            extra["motion_inference"] = SimpleNamespace(**rec)
        new = to_report(
            parse_any_version(data["preprocessing"]),
            source=pid,
            methods_slice=MethodsSlice(text="", **data["methods"]),
            **extra,
        )
        (out / "papers" / f"{pid}.md").write_text(new, encoding="utf-8")
        identical = new == stored.read_text(encoding="utf-8")
        if pid in _HELD:
            held_same += identical
            held_changed += not identical
        else:
            (same if identical else changed).append(pid)
    print(f"identical {len(same)}: {', '.join(same) or '-'}")
    print(f"changed {len(changed)}: {', '.join(changed) or '-'}")
    print(f"held-out: identical {held_same}, changed {held_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
