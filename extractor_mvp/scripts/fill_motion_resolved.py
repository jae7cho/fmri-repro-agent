"""Fill resolved_tool and resolved_basis in the motion labels (2026-11-09), by code only.

Only a named_tool row whose own method_value names a realignment program
(fmri_defaults_kb.recognize_program: "MCFLIRT" -> "fsl MCFLIRT", basis program_named) or a package
with a documented realignment program (recognize_tool + realignment_program: "SPM12" -> "spm
Realign", basis package_named) is filled. Every other row is left blank for the author. A cell
that already holds a value is never overwritten. The columns are added after the last column
when absent. Prints counts and paper ids only.

    uv run --with openpyxl python scripts/fill_motion_resolved.py [--workbook PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from copy import copy
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / "ground_truth" / "motion_correction_labels_v1.xlsx"
COLUMNS = ("resolved_tool", "resolved_basis")


def resolve_label(method_state: str | None, method_value: str | None) -> tuple[str, str] | None:
    """``(resolved_tool, resolved_basis)`` for a label, or None when code may not fill it."""
    from fmri_defaults_kb import realignment_program, recognize_program, recognize_tool
    from fmri_defaults_kb.errors import KbError

    if method_state != "named_tool" or not method_value:
        return None
    prog = recognize_program(str(method_value))
    if prog is not None:
        return f"{prog[1]} {prog[0]}", "program_named"
    tool = recognize_tool(str(method_value))
    if tool is None:
        return None
    try:
        rp = realignment_program(tool)
    except KbError:
        return None
    return f"{tool} {rp.program}", "package_named"


def main(argv: list[str] | None = None) -> int:
    import openpyxl

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workbook", type=Path, default=LABELS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    wb = openpyxl.load_workbook(args.workbook)
    ws = wb["Labels"]
    head = [c.value for c in ws[1]]
    for name in COLUMNS:
        if name not in head:
            cell = ws.cell(row=1, column=len(head) + 1, value=name)
            model = ws.cell(row=1, column=len(head))
            if model.has_style:
                cell.font, cell.alignment = copy(model.font), copy(model.alignment)
                cell.border, cell.fill = copy(model.border), copy(model.fill)
            head.append(name)
    col = {name: head.index(name) + 1 for name in head}
    filled, blank, kept = [], [], []
    for r in range(2, ws.max_row + 1):
        pid = ws.cell(row=r, column=col["paper_id"]).value
        if not pid or " " in str(pid):
            continue
        got = resolve_label(
            ws.cell(row=r, column=col["method_state"]).value,
            ws.cell(row=r, column=col["method_value"]).value,
        )
        if got is None:
            blank.append(str(pid))
            continue
        if any(ws.cell(row=r, column=col[n]).value not in (None, "") for n in COLUMNS):
            kept.append(str(pid))
            continue
        ws.cell(row=r, column=col["resolved_tool"], value=got[0])
        ws.cell(row=r, column=col["resolved_basis"], value=got[1])
        filled.append(str(pid))
    if not args.dry_run:
        wb.save(args.workbook)
    print(f"filled {len(filled)}: {', '.join(filled)}")
    print(f"left blank for the author {len(blank)}: {', '.join(blank)}")
    if kept:
        print(f"already set, not overwritten {len(kept)}: {', '.join(kept)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
