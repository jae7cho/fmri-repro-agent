#!/usr/bin/env python3
"""Append labels exported by tools/labeler/labeler.html to the two label workbooks.

Reads every ``*.labels.json`` in a folder and appends one row per labelled card to
``ground_truth/motion_correction_labels_v1.xlsx`` (sheet ``Labels``) and
``ground_truth/smoothing_filtering_labels_v1.xlsx`` (sheets ``Smoothing`` and ``Filtering``).

New rows only. A paper whose paper_id already has a row in any sheet the file would write to is
refused as a whole, and the refusal is printed; nothing of that paper is written anywhere. A file
that fails validation (unknown schema, bad paper_id, a state outside the workbook vocabulary, a
filled card without a state, a repeated applies_to) is refused the same way. Every appended row
gets ``adjudication`` = "author alone, <date>", or "<rater>, <date>" with ``--rater``. The motion
workbook had no adjudication column; one is added after its last column the first time a row is
appended to it. Bullets 2-7 of the motion row are left blank (the labeler covers bullet 1 only).

Exit status: 0 when every file was appended, 1 when anything was refused (the rest is still
written), 2 on a usage error. ``--dry-run`` reports the same counts and writes nothing.

Usage (openpyxl is a dev dependency of the repository root):
    uv run python scripts/merge_labels.py LABELS_DIR [--rater NAME] [--date YYYY-MM-DD] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from copy import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
MOTION_XLSX = REPO / "ground_truth" / "motion_correction_labels_v1.xlsx"
SF_XLSX = REPO / "ground_truth" / "smoothing_filtering_labels_v1.xlsx"

SCHEMA = "aespa-labels/1"
#: The workbooks' dropdown lists, exactly (Labels!B, Smoothing!C, Filtering!C, Labels!R).
MOTION_STATES = ("named_tool", "described_only", "deferred", "absent", "stated_not_performed")
SF_STATES = ("reported", "partially_reported", "not_reported", "stated_not_performed", "deferred")
ATTRIBUTION = ("step", "package")

MOTION_FIELDS = ("state", "named_tool", "attribution", "quote", "notes")
SMOOTHING_FIELDS = (
    "applies_to",
    "state",
    "kernel",
    "width",
    "width_measure",
    "space",
    "quote",
    "notes",
)
FILTERING_FIELDS = (
    "applies_to",
    "state",
    "pass_type",
    "band_or_cutoff_as_stated",
    "filter_type",
    "order",
    "quote",
    "notes",
)
#: labeler field -> Labels column
MOTION_COLUMNS = {
    "state": "method_state",
    "named_tool": "method_value",
    "quote": "method_quote",
    "notes": "notes",
    "attribution": "attribution",
}
PAPER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
NUMBER = re.compile(r"^\d+(\.\d+)?$")


@dataclass
class Paper:
    source: Path
    paper_id: str
    motion: dict[str, str] | None
    smoothing: list[dict[str, str]]
    filtering: list[dict[str, str]]

    def sheets(self) -> list[str]:
        return [
            s
            for s, rows in (
                ("Labels", [self.motion] if self.motion else []),
                ("Smoothing", self.smoothing),
                ("Filtering", self.filtering),
            )
            if rows
        ]


@dataclass
class Outcome:
    files: int = 0
    appended: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    rows: dict[str, int] = field(
        default_factory=lambda: {"Labels": 0, "Smoothing": 0, "Filtering": 0}
    )
    empty_cards: int = 0


class InvalidExportError(ValueError):
    pass


def _strings(row: Any, fields: tuple[str, ...], where: str) -> dict[str, str]:
    if not isinstance(row, dict):
        raise InvalidExportError(f"{where} is not an object")
    unknown = sorted(set(row) - set(fields))
    if unknown:
        raise InvalidExportError(f"{where} has unknown fields {unknown}")
    out = {}
    for f in fields:
        v = row.get(f, "")
        if v is None:
            v = ""
        if not isinstance(v, str):
            raise InvalidExportError(f"{where}.{f} is not a string")
        out[f] = v.strip()
    return out


def _filled(row: dict[str, str]) -> bool:
    return any(v and not (k == "applies_to" and v == "all") for k, v in row.items())


def parse(path: Path, outcome: Outcome) -> Paper:
    """One exported file, validated against the workbook vocabularies. Raises InvalidExportError."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise InvalidExportError(f"not readable as JSON ({type(e).__name__})") from e
    if not isinstance(d, dict) or d.get("schema") != SCHEMA:
        raise InvalidExportError(f"schema is not {SCHEMA!r}")
    pid = d.get("paper_id")
    if not isinstance(pid, str) or not PAPER_ID.match(pid):
        raise InvalidExportError("paper_id is missing or malformed")
    if path.name != f"{pid}.labels.json":
        raise InvalidExportError(f"file name does not match paper_id {pid!r}")

    motion = _strings(d.get("motion") or {}, MOTION_FIELDS, "motion")
    if motion["state"]:
        if motion["state"] not in MOTION_STATES:
            raise InvalidExportError(
                f"motion state {motion['state']!r} is not in the workbook vocabulary"
            )
        if motion["attribution"] and motion["attribution"] not in ATTRIBUTION:
            raise InvalidExportError(
                f"motion attribution {motion['attribution']!r} is not step or package"
            )
    elif _filled(motion):
        raise InvalidExportError("motion card is filled but has no state")
    else:
        outcome.empty_cards += 1

    streams: dict[str, list[dict[str, str]]] = {}
    for key, fields in (("smoothing", SMOOTHING_FIELDS), ("filtering", FILTERING_FIELDS)):
        raw = d.get(key) or []
        if not isinstance(raw, list):
            raise InvalidExportError(f"{key} is not a list")
        kept, seen = [], set()
        for i, r in enumerate(raw, 1):
            row = _strings(r, fields, f"{key} row {i}")
            if not row["state"]:
                if _filled(row):
                    raise InvalidExportError(f"{key} row {i} is filled but has no state")
                outcome.empty_cards += 1
                continue
            if row["state"] not in SF_STATES:
                raise InvalidExportError(
                    f"{key} row {i} state {row['state']!r} is not in the workbook vocabulary"
                )
            if not row["applies_to"]:
                raise InvalidExportError(f"{key} row {i} has an empty applies_to")
            if row["applies_to"] in seen:
                raise InvalidExportError(f"{key} applies_to {row['applies_to']!r} appears twice")
            seen.add(row["applies_to"])
            kept.append(row)
        streams[key] = kept
    return Paper(
        path, pid, motion if motion["state"] else None, streams["smoothing"], streams["filtering"]
    )


def existing_ids(ws: Any) -> set[str]:
    head = [c.value for c in ws[1]]
    col = head.index("paper_id")
    return {
        str(r[col]).strip()
        for r in ws.iter_rows(min_row=2, values_only=True)
        if r[col] not in (None, "")
    }


def _cell_value(column: str, v: str) -> Any:
    if v == "":
        return None
    if column == "width" and NUMBER.match(v):
        return float(v) if "." in v else int(v)
    return v


def append_row(ws: Any, values: dict[str, Any]) -> None:
    """Append under the header by column name, styled like the sheet's first data row."""
    head = [c.value for c in ws[1]]
    unknown = set(values) - set(head)
    if unknown:
        raise KeyError(f"{ws.title} has no column {sorted(unknown)}")
    r = ws.max_row + 1
    for j, name in enumerate(head, 1):
        cell = ws.cell(row=r, column=j, value=values.get(name))
        model = ws.cell(row=2, column=j)
        if model.has_style:
            cell.font, cell.alignment = copy(model.font), copy(model.alignment)
            cell.border, cell.fill = copy(model.border), copy(model.fill)


def ensure_column(ws: Any, name: str) -> None:
    head = [c.value for c in ws[1]]
    if name not in head:
        last = len(head)
        new = ws.cell(row=1, column=last + 1, value=name)
        model = ws.cell(row=1, column=last)
        if model.has_style:
            new.font, new.alignment = copy(model.font), copy(model.alignment)
            new.border, new.fill = copy(model.border), copy(model.fill)


def save_atomically(wb: Any, path: Path) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".xlsx", dir=path.parent)
    os.close(fd)
    try:
        wb.save(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def merge(
    folder: Path,
    adjudication: str,
    motion_xlsx: Path = MOTION_XLSX,
    sf_xlsx: Path = SF_XLSX,
    dry_run: bool = False,
    say: Any = print,
) -> Outcome:
    import openpyxl

    out = Outcome()
    mwb, swb = openpyxl.load_workbook(motion_xlsx), openpyxl.load_workbook(sf_xlsx)
    sheets = {"Labels": mwb["Labels"], "Smoothing": swb["Smoothing"], "Filtering": swb["Filtering"]}
    taken = {name: existing_ids(ws) for name, ws in sheets.items()}

    for path in sorted(folder.glob("*.labels.json")):
        out.files += 1
        try:
            paper = parse(path, out)
        except InvalidExportError as e:
            out.refused.append(path.name)
            say(f"refused {path.name}: {e}; nothing written for it")
            continue
        clash = [s for s in paper.sheets() if paper.paper_id in taken[s]]
        if clash:
            out.refused.append(paper.paper_id)
            say(
                f"refused {paper.paper_id}: a row for this paper_id already exists in "
                f"{', '.join(clash)}; existing rows are never overwritten, nothing written for it"
            )
            continue
        if not paper.sheets():
            out.refused.append(paper.paper_id)
            say(f"refused {paper.paper_id}: no card has a state; nothing to write")
            continue
        if paper.motion:
            ensure_column(sheets["Labels"], "adjudication")
            row = {MOTION_COLUMNS[k]: _cell_value(k, v) for k, v in paper.motion.items()}
            append_row(
                sheets["Labels"], {"paper_id": paper.paper_id, **row, "adjudication": adjudication}
            )
            out.rows["Labels"] += 1
        for name, rows in (("Smoothing", paper.smoothing), ("Filtering", paper.filtering)):
            for r in rows:
                values = {k: _cell_value(k, v) for k, v in r.items()}
                append_row(
                    sheets[name],
                    {"paper_id": paper.paper_id, **values, "adjudication": adjudication},
                )
                out.rows[name] += 1
        for s in paper.sheets():
            taken[s].add(paper.paper_id)
        out.appended.append(paper.paper_id)

    if not dry_run:
        if out.rows["Labels"]:
            save_atomically(mwb, motion_xlsx)
        if out.rows["Smoothing"] or out.rows["Filtering"]:
            save_atomically(swb, sf_xlsx)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path, help="folder of <paper_id>.labels.json files")
    ap.add_argument("--rater", help='rater name for adjudication (default "author alone")')
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="adjudication date")
    ap.add_argument("--motion-workbook", type=Path, default=MOTION_XLSX)
    ap.add_argument("--sf-workbook", type=Path, default=SF_XLSX)
    ap.add_argument("--dry-run", action="store_true", help="report counts, write nothing")
    args = ap.parse_args(argv)
    if not args.folder.is_dir():
        print(f"not a folder: {args.folder}", file=sys.stderr)
        return 2
    try:
        dt.date.fromisoformat(args.date)
    except ValueError:
        print(f"--date is not YYYY-MM-DD: {args.date}", file=sys.stderr)
        return 2
    rater = (args.rater or "").strip() or "author alone"
    out = merge(
        args.folder, f"{rater}, {args.date}", args.motion_workbook, args.sf_workbook, args.dry_run
    )
    verb = "would append" if args.dry_run else "appended"
    print(
        f"{out.files} files read; {len(out.appended)} papers {verb}, {len(out.refused)} refused; "
        f"rows {verb}: Labels {out.rows['Labels']}, Smoothing {out.rows['Smoothing']}, "
        f"Filtering {out.rows['Filtering']}; empty cards skipped: {out.empty_cards}"
    )
    return 1 if out.refused else 0


if __name__ == "__main__":
    sys.exit(main())
