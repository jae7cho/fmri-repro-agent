"""The target_space tally: strips provenance headers, reads the 19-row CSV, names its vintage.

Four traps are pinned here, each one already recorded in TRACK_A_SCOPE.md or DEVLOG.md as
something that has gone wrong once:

1. **The `#` strip.** Both prediction CSVs carry emitted provenance headers. A bare DictReader
   parses those comment lines as data and returns ~32 rows with no error, which then tallies into
   clean-looking nonsense. `test_the_silent_garbage_mode_is_real` is the positive control: it
   shows the hazard firing, so the passing strip test is not vacuous.
2. **The 19-row CSV, never the workbook.** target_space_labels_v1.xlsx holds 22 data rows — 19
   real, two "(EXAMPLE)" duplicating oconnor and mueller, and a legend row.
3. **Vintage on the face of every rate.** Two vintages give different rates from identical labels
   under an identical map.
4. **Reachable-only stays out**, having been retired from the README as a post-hoc exclusion.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tally_target_space as tally

MODULE_SOURCE = Path(tally.__file__).read_text(encoding="utf-8")


def test_the_reader_strips_the_provenance_header() -> None:
    rows = tally.read_rows(tally.VINTAGES["v050"])
    assert len(rows) == 19
    assert all(not r["paper_id"].startswith("#") for r in rows)


def test_the_silent_garbage_mode_is_real() -> None:
    """The positive control for the strip. Without it nothing raises — you just get comment text
    parsed as papers. If this ever stops finding extra rows, the strip test above proves nothing
    and should be re-read rather than trusted."""
    path = tally.VINTAGES["v050"]
    with path.open(encoding="utf-8") as f:
        unstripped = list(csv.DictReader(f))
    assert len(unstripped) > 19, "the hazard this module guards against no longer exists"
    assert len(unstripped) == 32, (
        f"header shape changed: {len(unstripped)} rows unstripped. 32 is the number the forward "
        f"pointer at score_target_space.py:152 predicts; if it moves, that comment moves too."
    )


def test_no_unstripped_csv_reader_can_be_added_to_this_module() -> None:
    """A future edit that opens a CSV directly reintroduces the hazard silently. The strip lives
    in exactly one function; this asserts it stays that way.

    Parse, do not grep. The first version of this test counted `csv.DictReader` with a regex over
    the source and got TWO — the second hit was the module docstring's own warning about bare
    DictReaders. That warning is still there to be miscounted, and regex is what anyone reaches
    for first here, so the check walks the AST instead and prose cannot reach it.
    """
    tree = ast.parse(MODULE_SOURCE)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "DictReader"]
    assert len(calls) == 1, f"{len(calls)} DictReader uses in code; all reads go through read_rows"
    reader = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "read_rows"
    )
    assert reader.lineno < calls[0].lineno <= (reader.end_lineno or 0), (
        "the one DictReader is no longer inside read_rows"
    )


def test_labels_come_from_the_19_row_csv_not_the_workbook() -> None:
    labels = tally.load_labels()
    assert len(labels) == 19
    assert not [p for p in labels if "EXAMPLE" in p.upper()]
    assert tally.LABELS.suffix == ".csv"
    tree = ast.parse(MODULE_SOURCE)
    docstrings = {
        ast.get_docstring(n, clean=False)
        for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
    }
    literals = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value not in docstrings
    ]
    assert not [s for s in literals if ".xlsx" in s], "a workbook path reached the code"


def test_the_published_label_distribution_regenerates() -> None:
    """TRACK_A_SCOPE recorded this distribution as existing only as inline prose. It is the
    number on the poster, so it is pinned to the committed CSV."""
    from collections import Counter

    dist = Counter(tally.load_labels().values())
    assert dist == {
        "family_specified": 10,
        "deferred": 3,
        "native_volume": 2,
        "study_specific": 2,
        "canonical": 1,
        "absent": 1,
    }
    assert sum(dist.values()) == 19


@pytest.mark.parametrize(("vintage", "correct"), [("v040_frozen", 11), ("v050", 11)])
def test_per_label_counts_sum_to_what_the_scorers_report(vintage: str, correct: int) -> None:
    """Cross-check against the scorers, which reach the same totals by a different path. Both
    vintages total 11/8 — which is exactly why the per-label breakdown exists."""
    labels = tally.load_labels()
    matrix = tally.per_label_states(labels, tally.graded_predictions(vintage))
    assert sum(row.get(label, 0) for label, row in matrix.items()) == correct
    assert sum(sum(row.values()) for row in matrix.values()) == 19


def test_the_vintages_disagree_where_the_totals_do_not() -> None:
    """The finding the tally exists to surface: identical totals, different distributions."""
    labels = tally.load_labels()
    frozen = tally.per_label_states(labels, tally.graded_predictions("v040_frozen"))
    v050 = tally.per_label_states(labels, tally.graded_predictions("v050"))
    assert frozen["deferred"].get("deferred", 0) == 1
    assert v050["deferred"].get("deferred", 0) == 0, "braun's deferral detection held"
    assert frozen["study_specific"].get("study_specific", 0) == 0
    assert v050["study_specific"].get("study_specific", 0) == 1, "mueller's improvement vanished"


def test_every_emitted_rate_names_its_vintage() -> None:
    text = tally.render(list(tally.VINTAGES))
    for line in text.splitlines():
        if "correct-rate" in line:
            assert any(v in line for v in tally.VINTAGES), f"unlabelled rate: {line}"
    assert "10/17" in text and "11/17" in text, "both vintages' rates should appear"


def test_reachable_only_is_not_emitted_in_any_form() -> None:
    text = tally.render(list(tally.VINTAGES))
    assert "10/14" not in text and "11/14" not in text
    assert "71.4" not in text and "78.6" not in text
    assert text.lower().count("reachable-only") == 1, "only the line explaining its absence"


def test_out_writes_a_file_and_stdout_does_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "nested" / "tally.md"
    assert tally.main(["--out", str(dest)]) == 0
    assert dest.is_file(), "parent directories should be created"
    assert "# target_space corpus tally" in dest.read_text(encoding="utf-8")
    capsys.readouterr()
    assert tally.main(["--vintage", "v050"]) == 0
    assert capsys.readouterr().out.startswith("# target_space corpus tally")


def test_the_report_is_rendered_before_the_output_file_is_opened() -> None:
    """open("w") truncates on entry, so rendering inside the write would let a mid-render failure
    destroy the file it was regenerating. That bug cost the v050 CSV once
    (score_v050_reextraction.py:229); the ordering is asserted rather than remembered."""
    body = MODULE_SOURCE[MODULE_SOURCE.index("def main(") :]
    assert body.index("text = render(") < body.index("write_text("), "render must precede the open"
