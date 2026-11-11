"""The derived label csvs must not carry prose from a held-out paper.

WHY THIS EXISTS. Three papers are held out by pre-registration C11/C26 (liu_2005, tang_2025,
wheaton_2004): reading their text destroys the only uncontaminated cells left in the motion
corpus. The hold-out was enforced by habit and by refusals in code, but their verbatim methods
prose was sitting in ``ground_truth/*_labels_v1.csv`` under ``supporting_quote`` and ``notes`` --
tracked, in a PUBLIC repository, in files that get grepped. On 2026-10-22 two ordinary searches
put held-out prose on screen (logged in ``docs/design/DELTA_glyph_leak_span_recovery.md`` section
0). ``.rgignore`` cannot prevent that: it matches PATHS, and this text lived inside files named
for the label set, not for the papers.

The derivers now withhold those columns for held-out rows. This test is what keeps it that way,
since the csvs are regenerated from the workbooks and a future deriver edit could quietly
reintroduce the text.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_GROUND_TRUTH = _REPO / "ground_truth"

#: Canonical held-out set. Every copy of it in the tree is compared against this one.
_HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})

#: Exactly what a deriver writes in place of a held-out paper's prose. Asserting EQUALITY with
#: this -- rather than a length bound -- is what makes the guard total: tang_2025's target_space
#: quote was only 78 chars, so any length threshold loose enough to admit the marker would also
#: have admitted that quote straight back in.
_REDACTED = "[withheld: held-out paper, prereg C11/C26 — quote retained in the workbook]"

#: Columns a deriver withholds for a held-out row.
_WITHHELD_COLUMNS = ("supporting_quote", "notes")

#: Columns that are the LABEL rather than prose, and so are expected to survive redaction.
_LABEL_COLUMNS = {"paper_id", "status", "target_space_state", "value", "specificity", "labeler"}

#: Backstop for any OTHER column: no held-out cell should ever reach prose length.
_MAX_HELD_OUT_CELL = 120

_CSVS = ("base_pipeline_labels_v1.csv", "target_space_labels_v1.csv")

#: Every file that keeps its own copy of the held-out set is discovered, not listed, so a new
#: copy is covered the day it is written rather than the day someone remembers this test.
_HELD_OUT_LITERAL = re.compile(r"_HELD_OUT = frozenset\(\{([^}]*)\}\)")

#: Fewer copies than this means the scan below silently stopped finding them.
_MIN_HELD_OUT_COPIES = 6


def _rows(name: str) -> list[dict[str, str]]:
    path = _GROUND_TRUTH / name
    if not path.is_file():
        pytest.skip(f"{name} absent")
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("name", _CSVS)
def test_held_out_rows_carry_no_prose(name: str) -> None:
    """No held-out row may carry prose in a tracked csv.

    A withheld column must be EMPTY or EXACTLY the marker. Nothing in between is tolerated,
    because a short quote is still the paper's text.
    """
    offenders: list[str] = []
    for row in _rows(name):
        if (row.get("paper_id") or "").strip() not in _HELD_OUT:
            continue
        for column, value in row.items():
            if column in _LABEL_COLUMNS:
                continue
            value = value or ""
            # Report the LENGTH, never the text: this message is printed on failure, and
            # printing the prose would commit the very leak being guarded.
            if column in _WITHHELD_COLUMNS:
                if value not in ("", _REDACTED):
                    offenders.append(
                        f"{name}:{row['paper_id']}.{column} = {len(value)} chars, not the marker"
                    )
            elif len(value) > _MAX_HELD_OUT_CELL:
                offenders.append(f"{name}:{row['paper_id']}.{column} = {len(value)} chars")
    assert not offenders, "held-out prose in a tracked csv: " + "; ".join(offenders)


@pytest.mark.parametrize("name", _CSVS)
def test_non_held_out_rows_still_carry_their_evidence(name: str) -> None:
    """Positive control, without which the test above is worthless.

    If redaction were applied to every row -- or if the quote column were simply dropped -- the
    guard above would pass while the label set lost the evidence for every label it carries.
    Over-redaction is detected EXACTLY, by the marker appearing on a row that is not held out,
    so stripping even one wrong row fails here instead of hiding under a count threshold.
    """
    rows = _rows(name)
    assert len(rows) == 19, f"{name}: expected the 19-paper label set, got {len(rows)}"

    over_redacted = [
        f"{row['paper_id']}.{column}"
        for row in rows
        if (row.get("paper_id") or "").strip() not in _HELD_OUT
        for column in _WITHHELD_COLUMNS
        if (row.get(column) or "") == _REDACTED
    ]
    assert not over_redacted, (
        f"{name}: redaction over-reached onto rows that are not held out: {over_redacted}"
    )

    kept = [
        row
        for row in rows
        if (row.get("paper_id") or "").strip() not in _HELD_OUT
        and len(row.get("supporting_quote") or "") > _MAX_HELD_OUT_CELL
    ]
    assert len(kept) >= 10, (
        f"{name}: only {len(kept)} non-held-out rows still carry a supporting quote -- "
        "redaction has over-reached and is destroying the label set's evidence"
    )


def test_every_copy_of_the_held_out_set_agrees() -> None:
    """Each file keeping its own copy of the held-out ids must not drift from the canonical one.

    Six copies exist (the two derivers plus motion_probe, step_field_support_replay,
    value_support_survey and apply_motion_inference). A copy that drifts is worse than no copy,
    because redaction would silently stop covering a paper. The copies are DISCOVERED rather
    than listed, so this keeps holding as more are written.
    """
    checked: list[str] = []
    for path in sorted(_REPO.rglob("*.py")):
        if any(
            part in {".venv", "venv", ".git", "node_modules", "__pycache__"} for part in path.parts
        ):
            continue
        match = _HELD_OUT_LITERAL.search(path.read_text(encoding="utf-8", errors="ignore"))
        if not match:
            continue
        found = {part.strip().strip('"').strip("'") for part in match.group(1).split(",")}
        found.discard("")
        rel = path.relative_to(_REPO)
        assert found == set(_HELD_OUT), f"{rel}: _HELD_OUT drifted to {sorted(found)}"
        checked.append(str(rel))

    assert len(checked) >= _MIN_HELD_OUT_COPIES, (
        f"only found {len(checked)} copies of _HELD_OUT ({checked}); expected at least "
        f"{_MIN_HELD_OUT_COPIES} -- the scan has stopped finding them and this test is vacuous"
    )
