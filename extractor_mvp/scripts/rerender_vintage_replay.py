"""Re-render every stored record of a vintage with the CURRENT renderer and schema, through the
supported door (``parse_any_version``), and compare with the stored report byte for byte. No model
calls, no text printed: papers are listed as identical or changed (the held-out three as counts).

Used for report v2's schema steps (DESIGN_report_v2.md): a lift that changes a stored record's
rendering is a lift that changed what a reader sees.

Usage:
    python scripts/rerender_vintage_replay.py results/batch_coverage_v2 [more dirs]
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
    for d in argv if argv is not None else sys.argv[1:]:
        papers = Path(d) / "papers"
        same, changed, held_changed = 0, [], 0
        for f in sorted(papers.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            pid = data["paper_id"]
            md = papers / f"{pid}.md"
            if not md.exists():
                continue
            extra: dict[str, Any] = {}
            if data.get("multiple_pipelines") is not None:
                extra["multiple_pipelines"] = data["multiple_pipelines"]
            rec = data.get("motion_inference")
            if isinstance(rec, dict):
                extra["motion_inference"] = SimpleNamespace(**rec)
            new = to_report(
                parse_any_version(data["preprocessing"]),
                source=pid,
                methods_slice=MethodsSlice(text="", **data["methods"]),
                **extra,
            )
            if new == md.read_text(encoding="utf-8"):
                same += 1
            elif pid in _HELD:
                held_changed += 1
            else:
                changed.append(pid)
        print(
            f"{d}: identical {same}; changed (contaminated/other) {changed or 0}; changed held-out {held_changed}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
