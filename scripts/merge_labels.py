#!/usr/bin/env python3
"""Append labels exported by tools/labeler/labeler.html to the label workbooks.

Reads every ``*.labels.json`` in a folder and appends one row per labelled card to
``ground_truth/motion_correction_labels_v1.xlsx`` (sheet ``Labels``),
``ground_truth/smoothing_filtering_labels_v1.xlsx`` (sheets ``Smoothing`` and ``Filtering``) and,
from 2026-11-11, ``ground_truth/preproc_rows_labels_v1.xlsx`` (one sheet per remaining COBIDAS card
and sub-card, :data:`ROW_SHEETS`). A workbook is saved only when a row was appended to it.

After a merge that wrote rows to the preproc-rows workbook, ``ground_truth/preproc_rows_progress_v1.csv``
is updated: per paper, the number of rows merged into each of those sheets and the adjudication
string of the last merge. The papers to walk are ``ground_truth/preproc_rows_walk_v1.csv`` (ids only).

New rows only. A paper whose paper_id already has a row in any sheet the file would write to is
refused as a whole, and the refusal is printed; nothing of that paper is written anywhere. A file
that fails validation (unknown schema, bad paper_id, a state outside the workbook vocabulary, a
filled card without a state, a repeated applies_to) is refused the same way. Every appended row
gets ``adjudication`` = "author alone, <date>", or "<rater>, <date>" with ``--rater``. The motion
workbook had no adjudication column; one is added after its last column the first time a row is
appended to it. Bullets 2-7 of the motion row are left blank (the labeler covers bullet 1 only).

Held-out papers (2026-11-11, the author's ruling): for liu_2005, tang_2025 and wheaton_2004 the
cells outside the known label columns (:data:`LABEL_COLUMNS`: ids, states, values, adjudication; so
``quote``, ``notes``, ``method_quote`` and any column added later) are written as :data:`REDACTED`
(fail closed, Stage 2b), and the text itself is appended to ``ground_truth/heldout_label_prose.local.jsonl``,
which is gitignored. States and values are written as for any paper: they are the label. The
workbooks are untracked from the same day, so this keeps a held-out paper's text out of any
workbook that is published later.

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
ROWS_XLSX = REPO / "ground_truth" / "preproc_rows_labels_v1.xlsx"
WALK_CSV = REPO / "ground_truth" / "preproc_rows_walk_v1.csv"
PROGRESS_CSV = REPO / "ground_truth" / "preproc_rows_progress_v1.csv"
HELDOUT_SIDECAR = REPO / "ground_truth" / "heldout_label_prose.local.jsonl"

#: Held out by pre-registration C11/C26: their prose never goes into a workbook.
_HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
REDACTED = (
    "[withheld: held-out paper, prereg C11/C26 — kept in ground_truth/"
    "heldout_label_prose.local.jsonl, untracked]"
)
#: The workbook columns that are the label (ids, states, values, adjudication). Stage 2b item 5
#: (2026-11-11): for a held-out paper every OTHER column is withheld, so a prose column added later
#: is withheld without anyone remembering to list it (fail closed). Filled in below, after the
#: sheets' fields are defined.
LABEL_COLUMNS: frozenset[str] = frozenset()

SCHEMA = "aespa-labels/1"
#: The workbooks' dropdown lists, exactly (Labels!B, Smoothing!C, Filtering!C, Labels!R).
MOTION_STATES = ("named_tool", "described_only", "deferred", "absent", "stated_not_performed")
SF_STATES = ("reported", "partially_reported", "not_reported", "stated_not_performed", "deferred")
ATTRIBUTION = ("step", "package")

#: The remaining COBIDAS rows (2026-11-11). Same vocabulary as smoothing and filtering.
ROW_STATES = SF_STATES

#: sheet (= the step kind, = the labeler card key) -> the step's fields, named exactly as in the
#: schema's ``<KIND>_FIELD_META`` (src/fmri_repro/spec/preprocessing.py) in its order, without
#: ``performed``: the state carries it (stated_not_performed vs the rest). Every field is labelled
#: as the paper states it: no unit conversion, no enum coercion. tests/test_merge_labels.py holds
#: these to the schema, the labeler and the workbook. Sub-cards are their own sheets.
ROW_STEP_FIELDS: dict[str, tuple[str, ...]] = {
    "slice_time_correction": (
        "method",
        "interpolation_order",
        "reference",
        "relative_to_motion_correction",
        "interpolation",
    ),
    "nuisance_regression": (
        "regressor_list",
        "tissue_definition",
        "tissue_signal_definition",
        "motion_expansion",
        "tissue_regressors",
        "physio_regressors",
        "physio_n_regressors",
        "detrend",
        "method",
        "filtering_integrated",
    ),
    "compcor": ("variant", "n_components", "variance_threshold", "mask_source"),
    "ica_denoise": ("method", "training_set", "threshold", "aggressive"),
    "scrub": ("method", "criterion", "threshold", "remediation", "interpolation_method"),
    "despike": ("method", "threshold"),
    "nonsteadystate_removal": ("n_nonsteadystate_discarded",),
    "coregistration": (
        "nonlinear_transform_type",
        "transform",
        "method",
        "cost_function",
        "interpolation",
    ),
    "distortion_correction": ("source", "method", "tool"),
    "brain_extraction": ("parameters", "method", "manual_edits"),
    "segmentation": ("method", "tissue_classes"),
    "intensity_correction": ("target", "method"),
}
#: Four more rows (the author's request of 2026-11-11, second set). These are not one schema step
#: each, so their fields are the label's own, named by the author: gradient distortion correction
#: (the distortion_correction step's method and tool; its source is the sheet), intersubject
#: registration (spatial_normalization and surface_projection together), the resting-state fMRI
#: feature (a D.3 row the extractor does not assess) and software (one row per package). Values as
#: stated, like the rest.
ROW_LABEL_FIELDS: dict[str, tuple[str, ...]] = {
    "gradient_distortion_correction": ("method", "tool"),
    "intersubject_registration": (
        "method",
        "volume_or_surface",
        "template",
        "resolution",
        "warp_type",
        "interpolation",
        "cost_function",
    ),
    "resting_state_feature": ("measure", "band_hz", "reho_neighbourhood", "reho_measure"),
    "software": ("version_as_stated", "used_for"),
}
#: The column that names a row within a paper: applies_to, except software, one row per package.
ROW_KEY: dict[str, str] = {"software": "name"}


def row_key(sheet: str) -> str:
    return ROW_KEY.get(sheet, "applies_to")


#: sheet -> every labeler field of a row, in workbook column order (after paper_id)
ROW_SHEETS: dict[str, tuple[str, ...]] = {
    sheet: (row_key(sheet), "state", *fields, "quote", "notes")
    for sheet, fields in {**ROW_STEP_FIELDS, **ROW_LABEL_FIELDS}.items()
}

#: The standing rulings for these rows, as the labeler's help panel and the workbook's README state
#: them (the author's list of 2026-11-11).
ROW_RULINGS: tuple[str, ...] = (
    "A confound that is computed or made available (framewise displacement, DVARS, motion "
    "parameters, CompCor components) is not applied unless the paper says it was regressed out.",
    '"Annotated as outliers" is not censoring unless the frames were removed or interpolated.',
    "A step the data provider applied to a released dataset is labelled as applied; name the "
    "release in notes.",
    '"Co-registered to correct for head motion" is motion correction, not coregistration.',
    "Dummy volumes discarded by the scanner and dummy volumes discarded in preprocessing both count "
    "for T1 stabilization (nonsteadystate_removal); say which in notes.",
)

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
LABEL_COLUMNS = frozenset(
    {
        "paper_id",
        "applies_to",
        "state",
        "adjudication",
        "method_state",
        "method_value",
        "attribution",
    }
    | {f for f in SMOOTHING_FIELDS + FILTERING_FIELDS if f not in ("quote", "notes")}
    | {f for fields in ROW_STEP_FIELDS.values() for f in fields}
    | {f for fields in ROW_LABEL_FIELDS.values() for f in fields}
    | set(ROW_KEY.values())
)
PAPER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
NUMBER = re.compile(r"^\d+(\.\d+)?$")


@dataclass
class Paper:
    source: Path
    paper_id: str
    motion: dict[str, str] | None
    smoothing: list[dict[str, str]]
    filtering: list[dict[str, str]]
    rows: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def sheets(self) -> list[str]:
        return [
            s
            for s, rows in (
                ("Labels", [self.motion] if self.motion else []),
                ("Smoothing", self.smoothing),
                ("Filtering", self.filtering),
                *self.rows.items(),
            )
            if rows
        ]


@dataclass
class Outcome:
    files: int = 0
    appended: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    rows: dict[str, int] = field(
        default_factory=lambda: {
            "Labels": 0,
            "Smoothing": 0,
            "Filtering": 0,
            **dict.fromkeys(ROW_SHEETS, 0),
        }
    )
    empty_cards: int = 0
    withheld: int = 0  # held-out prose cells moved to the sidecar


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
    """Anything entered besides the default applies_to "all"."""
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
    cards = (("smoothing", SMOOTHING_FIELDS), ("filtering", FILTERING_FIELDS), *ROW_SHEETS.items())
    for key, fields in cards:
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
            if row["state"] not in (SF_STATES if key in ("smoothing", "filtering") else ROW_STATES):
                raise InvalidExportError(
                    f"{key} row {i} state {row['state']!r} is not in the workbook vocabulary"
                )
            col = row_key(key) if key in ROW_SHEETS else "applies_to"
            # software: a row naming no package is allowed only as the paper's "none named"
            # (not_reported), once
            if not row[col] and not (col == "name" and row["state"] == "not_reported"):
                raise InvalidExportError(f"{key} row {i} has an empty {col}")
            if row[col] in seen:
                raise InvalidExportError(f"{key} {col} {row[col]!r} appears twice")
            seen.add(row[col])
            kept.append(row)
        streams[key] = kept
    return Paper(
        path,
        pid,
        motion if motion["state"] else None,
        streams["smoothing"],
        streams["filtering"],
        {k: streams[k] for k in ROW_SHEETS if streams[k]},
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


PROGRESS_HEAD = ("paper_id", *ROW_SHEETS, "last_merged")


def read_progress(path: Path) -> list[dict[str, str]]:
    import csv

    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def update_progress(path: Path, written: dict[str, dict[str, int]], adjudication: str) -> None:
    """Per paper merged into the preproc-rows workbook: the rows it added to each sheet (added to
    any count already there) and ``last_merged``. A paper not on the walk list gets a row of its
    own at the end. Written atomically; the header is :data:`PROGRESS_HEAD`."""
    import csv

    rows = read_progress(path) if path.exists() else []
    by_id = {r["paper_id"]: r for r in rows}
    for pid, counts in written.items():
        row = by_id.get(pid)
        if row is None:
            row = dict.fromkeys(PROGRESS_HEAD, "")
            row["paper_id"] = pid
            rows.append(row)
            by_id[pid] = row
        for sheet, n in counts.items():
            row[sheet] = str(int(row.get(sheet) or 0) + n)
        row["last_merged"] = adjudication
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".csv", dir=path.parent)
    os.close(fd)
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(PROGRESS_HEAD), lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in PROGRESS_HEAD})
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _withhold(
    pid: str, sheet: str, values: dict[str, Any], sink: list[dict[str, Any]]
) -> dict[str, Any]:
    """A held-out paper's row with every non-empty cell outside :data:`LABEL_COLUMNS` replaced by
    :data:`REDACTED` (fail closed), the text moved to ``sink``; any other paper's row unchanged."""
    if pid not in _HELD_OUT:
        return values
    out = dict(values)
    for col in sorted(set(values) - LABEL_COLUMNS):
        if values[col] not in (None, ""):
            sink.append(
                {
                    "paper_id": pid,
                    "sheet": sheet,
                    "applies_to": values.get("applies_to", values.get("name")),
                    "column": col,
                    "text": values[col],
                }
            )
            out[col] = REDACTED
    return out


def merge(
    folder: Path,
    adjudication: str,
    motion_xlsx: Path = MOTION_XLSX,
    sf_xlsx: Path = SF_XLSX,
    dry_run: bool = False,
    say: Any = print,
    rows_xlsx: Path = ROWS_XLSX,
    progress_csv: Path = PROGRESS_CSV,
    sidecar: Path = HELDOUT_SIDECAR,
) -> Outcome:
    import openpyxl

    out = Outcome()
    mwb, swb = openpyxl.load_workbook(motion_xlsx), openpyxl.load_workbook(sf_xlsx)
    rwb = openpyxl.load_workbook(rows_xlsx)
    sheets = {"Labels": mwb["Labels"], "Smoothing": swb["Smoothing"], "Filtering": swb["Filtering"]}
    sheets.update({name: rwb[name] for name in ROW_SHEETS if name in rwb.sheetnames})
    taken = {name: existing_ids(ws) for name, ws in sheets.items()}
    missing = [name for name in ROW_SHEETS if name not in rwb.sheetnames]
    written: dict[str, dict[str, int]] = {}
    withheld: list[dict[str, Any]] = []

    for path in sorted(folder.glob("*.labels.json")):
        out.files += 1
        try:
            paper = parse(path, out)
        except InvalidExportError as e:
            out.refused.append(path.name)
            say(f"refused {path.name}: {e}; nothing written for it")
            continue
        absent = [s for s in paper.sheets() if s in missing]
        if absent:
            out.refused.append(paper.paper_id)
            say(
                f"refused {paper.paper_id}: the rows workbook has no sheet {', '.join(absent)}; "
                "add it with scripts/make_preproc_rows_workbook.py --add-sheets, nothing written "
                "for it"
            )
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
            row = _withhold(paper.paper_id, "Labels", row, withheld)
            append_row(
                sheets["Labels"], {"paper_id": paper.paper_id, **row, "adjudication": adjudication}
            )
            out.rows["Labels"] += 1
        for name, rows in (
            ("Smoothing", paper.smoothing),
            ("Filtering", paper.filtering),
            *paper.rows.items(),
        ):
            for r in rows:
                values = {k: _cell_value(k, v) for k, v in r.items()}
                values = _withhold(paper.paper_id, name, values, withheld)
                append_row(
                    sheets[name],
                    {"paper_id": paper.paper_id, **values, "adjudication": adjudication},
                )
                out.rows[name] += 1
        for s in paper.sheets():
            taken[s].add(paper.paper_id)
        if paper.rows:
            written[paper.paper_id] = {k: len(v) for k, v in paper.rows.items()}
        out.appended.append(paper.paper_id)

    if not dry_run:
        if out.rows["Labels"]:
            save_atomically(mwb, motion_xlsx)
        if out.rows["Smoothing"] or out.rows["Filtering"]:
            save_atomically(swb, sf_xlsx)
        if written:
            save_atomically(rwb, rows_xlsx)
            update_progress(progress_csv, written, adjudication)
        if withheld:
            with sidecar.open("a", encoding="utf-8") as fh:
                for item in withheld:
                    fh.write(json.dumps({**item, "adjudication": adjudication}) + "\n")
    out.withheld = len(withheld)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path, help="folder of <paper_id>.labels.json files")
    ap.add_argument("--rater", help='rater name for adjudication (default "author alone")')
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="adjudication date")
    ap.add_argument("--motion-workbook", type=Path, default=MOTION_XLSX)
    ap.add_argument("--sf-workbook", type=Path, default=SF_XLSX)
    ap.add_argument("--rows-workbook", type=Path, default=ROWS_XLSX)
    ap.add_argument("--progress", type=Path, default=PROGRESS_CSV)
    ap.add_argument("--heldout-sidecar", type=Path, default=HELDOUT_SIDECAR)
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
        args.folder,
        f"{rater}, {args.date}",
        args.motion_workbook,
        args.sf_workbook,
        args.dry_run,
        rows_xlsx=args.rows_workbook,
        progress_csv=args.progress,
        sidecar=args.heldout_sidecar,
    )
    verb = "would append" if args.dry_run else "appended"
    row_counts = ", ".join(f"{s} {out.rows[s]}" for s in ROW_SHEETS if out.rows[s])
    print(
        f"{out.files} files read; {len(out.appended)} papers {verb}, {len(out.refused)} refused; "
        f"rows {verb}: Labels {out.rows['Labels']}, Smoothing {out.rows['Smoothing']}, "
        f"Filtering {out.rows['Filtering']}"
        + (f", {row_counts}" if row_counts else "")
        + f"; empty cards skipped: {out.empty_cards}"
        + (f"; held-out prose cells withheld: {out.withheld}" if out.withheld else "")
    )
    return 1 if out.refused else 0


if __name__ == "__main__":
    sys.exit(main())
