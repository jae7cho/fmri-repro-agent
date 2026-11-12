"""Pre-rerun item 4 (2026-11-11): a deferral whose cited source the hop could not open (no local PDF,
no Europe PMC full text) is marked on the field, rendered as such and counted as deferred. Offline;
every reference below is invented."""

from __future__ import annotations

import copy
import inspect
from typing import Any

from conftest import FULL_TEXT, _canned_payload, stub_client
from extractor_mvp.citation_hop import mark_unopened_deferrals, unopened_refs
from extractor_mvp.extractor import extract
from extractor_mvp.parsed_paper import ParsedPaper

_DUMP: dict[str, Any] | None = None


def _dump() -> dict[str, Any]:
    global _DUMP
    if _DUMP is None:
        prep, _, _ = extract(
            ParsedPaper(text=FULL_TEXT, source="p"), "m", client=stub_client(_canned_payload())
        )
        _DUMP = prep.model_dump(mode="json")
    return copy.deepcopy(_DUMP)


def _deferred(field_id: str, ref: str) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "extraction": {
            "status": "DEFERRED_TO_CITATION",
            "deferrals": [
                {"ref": ref, "span": {"start": 0, "end": 4, "text": "text"}, "target_kind": "paper"}
            ],
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {"status": "LEFT_MISSING", "reason": "deferred_to_citation"},
    }


def _record() -> dict[str, Any]:
    """Deferrals from the extraction call (slice timing), call T (scrub) and call S (distortion
    correction), two to an unopened source and one to an opened one."""
    dump = _dump()
    steps = {s["kind"]: s for s in dump["steps"]}
    steps["slice_time_correction"]["method"] = _deferred("method", "Smith 2020")
    steps["scrub"]["method"] = _deferred("method", "Smith 2020")
    steps["distortion_correction"]["method"] = _deferred("method", "Jones 2019")
    return {
        "paper_id": "t",
        "preprocessing": dump,
        "second_hop": [
            {"ref": "Smith 2020", "status": "not_retrievable"},
            {"ref": "Jones 2019", "status": "ok"},
        ],
    }


def test_unopened_refs_are_those_whose_every_target_failed_to_open() -> None:
    hops = [
        {"ref": "A", "status": "not_retrievable"},
        {"ref": "B", "status": "not_retrievable"},
        {"ref": "B", "status": "ok"},
        {"ref": "C", "status": "reference_not_found"},  # never looked for: not "could not open"
        {"ref": "D", "status": "not_retrievable"},
        {"ref": "D", "status": "not_retrievable"},
    ]
    assert unopened_refs(hops) == ["A", "D"]


def test_deferrals_from_every_call_are_marked_and_an_opened_one_is_not() -> None:
    rec = _record()
    marked = mark_unopened_deferrals(rec)
    assert marked == ["slice_time_correction.method", "scrub.method"]
    steps = {s["kind"]: s for s in rec["preprocessing"]["steps"]}
    assert steps["scrub"]["method"]["extraction"]["deferrals"][0]["source_could_not_be_opened"]
    assert (
        "source_could_not_be_opened"
        not in (steps["distortion_correction"]["method"]["extraction"]["deferrals"][0])
    )


def test_the_base_pipelines_deferral_is_marked_too() -> None:
    rec = _record()
    rec["preprocessing"]["base_pipeline"] = _deferred("base_pipeline", "Smith 2020")
    assert "base_pipeline" in mark_unopened_deferrals(rec)


def test_rendered_as_such_and_counted_as_deferred() -> None:
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp import render
    from extractor_mvp.cobidas import assess_coverage, row_state

    rec = _record()
    mark_unopened_deferrals(rec)
    prep = parse_any_version(rec["preprocessing"])
    report = render.to_report(prep, source="t")
    assert (
        "method: deferred to Smith 2020 (source could not be opened: no local PDF, no Europe PMC "
        "full text)" in report
    )
    assert "deferred to Jones 2019 —" in report  # control: an opened source reads as before
    rows = render.flatten(prep)
    rc = next(c for c in assess_coverage(rows, None, None) if c.row.row_id == "volume_censoring")
    assert row_state(rc, rows) == "deferred"


def test_the_pseudocode_says_so() -> None:
    from extractor_mvp.pseudocode import render_pseudocode

    rec = _record()
    mark_unopened_deferrals(rec)
    code = render_pseudocode(rec)
    assert code is not None
    line = next(ln for ln in code.splitlines() if ln.startswith("scrub("))
    assert 'method=see("Smith 2020") [C]' in line and "source could not be opened" in line


def test_run_paper_marks_before_it_renders() -> None:
    from extractor_mvp import full_report

    src = inspect.getsource(full_report.run_paper)
    assert src.index("mark_unopened_deferrals(record)") < src.index("render_record(record)")
