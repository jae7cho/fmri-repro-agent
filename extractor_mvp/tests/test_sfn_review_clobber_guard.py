"""generate_sfn_review must refuse to overwrite a workbook a human has annotated.

The generator writes ``review``/``correction``/``notes`` empty and ``pd.ExcelWriter`` opens with
``mode="w"``, which truncates on entry. So pointing ``--output`` at an annotated workbook destroys
adjudication nothing can regenerate. That was live: ``sfn_review_first_pass_review.xlsx`` held 69
such cells and the only thing preventing the overwrite was this module failing to import openpyxl.
A packaging bug is not a safeguard.

**The positive control is the point of this file.** A guard tested only against clean workbooks
proves nothing: it would pass identically if the detector never detected anything. Every negative
result here is paired with a positive one, and the parser is exercised on both the sharedStrings
and the inline-string encodings because a detector that silently handles one and not the other
reports "no annotations" for a file full of them.

Fixtures are built here rather than committed, so the tests do not depend on an untracked file.
The guard was additionally run against the real workbook out of band and reported
``review=27, correction=21, notes=21``, matching a hand count of the same file.
"""

from __future__ import annotations

import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path

import pytest

# generate_sfn_review.py sits at the extractor_mvp root, not under src/, and pyproject's
# pythonpath only carries src. Tests reach it the same way a person running it from
# extractor_mvp/ would.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_sfn_review as gen

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
HEADER = ("paper_id", "step_kind", "field", "status", "review", "correction", "notes")


def _sheet_xml(rows: Sequence[tuple[str, ...]], *, shared: list[str] | None) -> str:
    """One worksheet. With `shared`, cells reference the shared-string table (what pandas emits);
    without it, cells carry inline strings. Both encodings appear in real workbooks."""
    out = [f"<worksheet {NS}><sheetData>"]
    for r, row in enumerate(rows, start=1):
        out.append(f'<row r="{r}">')
        for c, val in enumerate(row):
            ref = f"{chr(ord('A') + c)}{r}"
            if not val:
                out.append(f'<c r="{ref}"/>')
            elif shared is not None:
                out.append(f'<c r="{ref}" t="s"><v>{shared.index(val)}</v></c>')
            else:
                out.append(f'<c r="{ref}" t="inlineStr"><is><t>{val}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def _workbook(path: Path, rows: Sequence[tuple[str, ...]], *, use_shared: bool = True) -> Path:
    """Write the parts _hand_annotated_columns actually reads."""
    shared = sorted({v for row in rows for v in row if v}) if use_shared else None
    with zipfile.ZipFile(path, "w") as z:
        if shared is not None:
            items = "".join(f"<si><t>{s}</t></si>" for s in shared)
            z.writestr(
                "xl/sharedStrings.xml",
                f'<sst {NS} count="{len(shared)}" uniqueCount="{len(shared)}">{items}</sst>',
            )
        z.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows, shared=shared))
    return path


CLEAN = [HEADER, ("braun_2015", "normalization", "target_space", "Extracted", "", "", "")]
ANNOTATED = [
    HEADER,
    (
        "braun_2015",
        "normalization",
        "resolution_mm",
        "Extracted",
        "n",
        "defer to citation 47 or 48",
        "",
    ),
    (
        "chen_2015",
        "surface",
        "surface_registration",
        "Extracted",
        "n",
        "whatever CCS default is",
        "",
    ),
    ("liu_2005", "normalization", "resolution_mm", "Extracted", "n", "", "wrong quote"),
]


def test_refuses_an_annotated_workbook_and_names_what_is_in_it(tmp_path: Path) -> None:
    """THE positive control. If this test ever passes for the wrong reason, everything else here
    is vacuous — so it asserts the counts, not merely that something was raised."""
    out = _workbook(tmp_path / "annotated.xlsx", ANNOTATED)
    with pytest.raises(SystemExit) as exc:
        gen.refuse_to_clobber_hand_review(out)
    message = str(exc.value)
    assert "REFUSING to overwrite" in message
    assert str(out) in message, "the message must name the file, not just the failure"
    assert "review=3" in message and "correction=2" in message and "notes=1" in message


def test_the_detector_finds_annotations_in_both_string_encodings(tmp_path: Path) -> None:
    """A detector that handles only one encoding reports a full workbook as empty."""
    expected = {"review": 3, "correction": 2, "notes": 1}
    shared_wb = _workbook(tmp_path / "shared.xlsx", ANNOTATED, use_shared=True)
    inline_wb = _workbook(tmp_path / "inline.xlsx", ANNOTATED, use_shared=False)
    assert gen._hand_annotated_columns(shared_wb) == expected
    assert gen._hand_annotated_columns(inline_wb) == expected


def test_allows_a_generator_shaped_workbook_with_the_columns_empty(tmp_path: Path) -> None:
    """The negative control, which is only meaningful because the positive one above passes."""
    out = _workbook(tmp_path / "clean.xlsx", CLEAN)
    assert gen._hand_annotated_columns(out) == {}
    gen.refuse_to_clobber_hand_review(out)  # must not raise


def test_allows_writing_a_file_that_does_not_exist_yet(tmp_path: Path) -> None:
    gen.refuse_to_clobber_hand_review(tmp_path / "new.xlsx")  # must not raise


def test_fails_closed_when_the_workbook_cannot_be_read(tmp_path: Path) -> None:
    """A broken detector and an empty workbook must not give the same answer.

    Returning {} here would let the guard wave through a file it could not inspect — the
    absence-shaped check this repository keeps finding, in the one place where the cost of
    getting it wrong is the data itself.
    """
    corrupt = tmp_path / "corrupt.xlsx"
    corrupt.write_bytes(b"not a zip at all")
    with pytest.raises(Exception) as exc:
        gen._hand_annotated_columns(corrupt)
    assert not isinstance(exc.value, SystemExit), (
        "should surface the read failure, not refuse politely"
    )


def test_the_guard_runs_before_anything_opens_the_output_file() -> None:
    """Ordering is the whole protection: pd.ExcelWriter truncates on entry, so a check performed
    after the open would destroy what it was checking. Same shape as the provenance-header
    truncation bug (score_v050_reextraction.py:229)."""
    source = Path(gen.__file__).read_text(encoding="utf-8")
    body = source[source.index("def write_excel(") :]
    guard_at = body.index("refuse_to_clobber_hand_review(output)")
    writer_at = body.index("pd.ExcelWriter(")
    assert guard_at < writer_at, "the guard must precede the truncating open"
