#!/usr/bin/env python3
"""Create the label workbook for the remaining COBIDAS rows, the list of papers to walk, and the
progress file the merge updates (2026-11-11, the author's request). Run once; refuses to overwrite.

- ``ground_truth/preproc_rows_labels_v1.xlsx``: a README sheet (the state vocabulary, the columns
  and the standing rulings), then one sheet per labeler card and sub-card (``merge_labels.ROW_SHEETS``),
  each headed ``paper_id, applies_to, state, <the step's fields>, quote, notes, adjudication``, with
  the state vocabulary as a dropdown on column C.
- ``ground_truth/preproc_rows_walk_v1.csv``: the 19 corpus papers, ids only (the ids of the
  smoothing/filtering workbook, which labels exactly the corpus), sorted.
- ``ground_truth/preproc_rows_progress_v1.csv``: one row per paper on the walk list, a column per
  sheet and ``last_merged``, all blank; ``merge_labels.py`` fills it.

Usage (openpyxl is a dev dependency of the repository root):
    uv run python scripts/make_preproc_rows_workbook.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from merge_labels import (
    PROGRESS_CSV,
    PROGRESS_HEAD,
    ROW_RULINGS,
    ROW_SHEETS,
    ROW_STATES,
    ROWS_XLSX,
    SF_XLSX,
    WALK_CSV,
)

#: The state definitions, the smoothing/filtering workbook's wording.
STATE_DEFINITIONS: dict[str, str] = {
    "reported": "The step is stated with its parameters.",
    "partially_reported": "Some of the step is stated, some not.",
    "not_reported": "Nothing about the step.",
    "stated_not_performed": "The paper says the step was not done; a stated negative is a report.",
    "deferred": "Attributed to a citation or a pipeline.",
}

#: The general rules every row is labelled under (README, after the vocabulary).
GENERAL_RULES: tuple[str, ...] = (
    "Values as stated: each field is the paper's own words, in its own unit. No unit conversion and "
    "no mapping to a controlled vocabulary; both are inferences, not labels.",
    "The step's fields are named as in the schema's *_FIELD_META. performed is not a column: the "
    "state carries it (stated_not_performed, or one of the others).",
    "One row per paper x applies_to. applies_to is the paper's own words for what the value applies "
    'to (a derived measure, an analysis, a data type, a scanner or site, a named variant); "all" is '
    "the ordinary case. Use the same words for the same part on every sheet.",
    "Quotes come from the PDF text layer; if a glyph or a page header broke the text, clean the "
    "quote and say what changed in notes.",
    "Sub-cards are their own sheets: compcor and ica_denoise under nuisance regression; scrub and "
    "despike under volume censoring.",
)


def corpus_ids(sf_xlsx: Path = SF_XLSX) -> list[str]:
    import openpyxl

    wb = openpyxl.load_workbook(sf_xlsx, read_only=True)
    ids = {
        str(r[0]).strip()
        for r in wb["Smoothing"].iter_rows(min_row=2, values_only=True)
        if r and r[0] not in (None, "")
    }
    return sorted(ids)


def readme_rows() -> list[list[str]]:
    rows: list[list[str]] = [
        ["AESPA labels: the remaining COBIDAS D.3 preprocessing rows (v1, created 2026-11-11)"],
        [],
        ["State vocabulary (column C of every sheet)"],
        *[[s, STATE_DEFINITIONS[s]] for s in ROW_STATES],
        [],
        ["General rules"],
        *[[f"{i}.", r] for i, r in enumerate(GENERAL_RULES, 1)],
        [],
        ["Standing rulings for these rows"],
        *[[f"{i}.", r] for i, r in enumerate(ROW_RULINGS, 1)],
        [],
        ["Sheets and their columns"],
        *[
            [sheet, ", ".join(("paper_id", *cols, "adjudication"))]
            for sheet, cols in ROW_SHEETS.items()
        ],
        [],
        [
            "adjudication",
            'Written by scripts/merge_labels.py: "author alone, <date>" or "<rater>, <date>".',
        ],
    ]
    return rows


def build_workbook(path: Path) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation

    if path.exists():
        raise FileExistsError(f"{path} exists; existing workbooks are never overwritten")
    wb = openpyxl.Workbook()
    readme = wb.active
    readme.title = "README"
    for r in readme_rows():
        readme.append(r)
    readme.column_dimensions["A"].width = 26
    readme.column_dimensions["B"].width = 120
    for row in readme.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    readme["A1"].font = Font(bold=True)
    for sheet, cols in ROW_SHEETS.items():
        ws = wb.create_sheet(sheet)
        ws.append(["paper_id", *cols, "adjudication"])
        for c in ws[1]:
            c.font = Font(bold=True)
        dv = DataValidation(
            type="list", formula1='"' + ",".join(ROW_STATES) + '"', allow_blank=True
        )
        dv.add("C2:C1000")
        ws.add_data_validation(dv)
        ws.freeze_panes = "B2"
    wb.save(path)


def write_csv(path: Path, head: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"{path} exists; refusing to overwrite it")
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(head), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv: list[str] | None = None) -> int:
    ids = corpus_ids()
    try:
        build_workbook(ROWS_XLSX)
        write_csv(WALK_CSV, ("paper_id",), [{"paper_id": i} for i in ids])
        write_csv(
            PROGRESS_CSV,
            PROGRESS_HEAD,
            [{**dict.fromkeys(PROGRESS_HEAD, ""), "paper_id": i} for i in ids],
        )
    except FileExistsError as e:
        print(e, file=sys.stderr)
        return 1
    print(
        f"wrote {ROWS_XLSX.name} ({len(ROW_SHEETS)} sheets), {WALK_CSV.name} and "
        f"{PROGRESS_CSV.name} ({len(ids)} papers)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
