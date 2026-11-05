"""Fix 3 in the extractor and the report (the author's list of 2026-11-05;
DESIGN_kb_deferred_defaults.md). The client's own rules are tested in
tests/kb_client/test_deferred_defaults.py; here: the wiring in _resolve_deferrals, the report line,
the COBIDAS row, and that the checking pass never sees the value."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests" / "kb_client"))

from test_deferred_defaults import _coreg, _prep, _version_extracted

from extractor_mvp.extractor import DeferralRecord, _resolve_deferrals
from extractor_mvp.render import to_report
from extractor_mvp.verifier import compact_draft


def _records(kind: str) -> list[DeferralRecord]:
    return [
        DeferralRecord(
            field=f"coregistration.{n}",
            ref_string="fMRIPrep",
            target_kind=kind,
            deferral_sentence="s",
        )
        for n in ("method", "transform", "cost_function")
    ]


def _resolved(kind: str):  # type: ignore[no-untyped-def]
    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep")
    return _resolve_deferrals(prep, _records(kind), paper_date=None, citation_resolver=None)


def test_a_deferral_to_the_pipeline_is_filled_in_resolve_deferrals() -> None:
    c = _coreg(_resolved("pipeline"))
    assert c.method.inference.status == "INFERRED_DEFAULT"
    assert c.method.extraction.status == "DEFERRED_TO_CITATION"


def test_a_deferral_to_a_paper_or_supplement_is_not() -> None:
    for kind in ("paper", "supplement"):
        assert _coreg(_resolved(kind)).method.inference.status == "LEFT_MISSING"


def test_the_report_says_the_paper_s_words_then_aespa_s_inference() -> None:
    out = to_report(_resolved("pipeline"), source="t")
    line = next(ln for ln in out.splitlines() if ln.startswith("- method = deferred to fMRIPrep"))
    assert "— not stated in this paper; AESPA infers bbregister (version_default, " in line
    assert "fMRIPrep 20.2.0 methods boilerplate" in line
    assert "[INFERRED — not stated in source]" not in line


def test_the_checking_pass_sees_the_deferral_never_the_value() -> None:
    draft = compact_draft(_resolved("pipeline"))
    line = next(ln for ln in draft.splitlines() if ln.startswith("coregistration.method |"))
    assert "| deferred | deferred to fMRIPrep |" in line and "bbregister" not in line


def _with_performed(prep):  # type: ignore[no-untyped-def]
    from fmri_repro.spec.provenance import Extracted, NotApplicable, ProvenancedField, Span

    c = _coreg(prep)
    c.performed = ProvenancedField[bool](
        field_id="performed",
        extraction=Extracted[bool](
            value=True, spans=[Span(start=0, end=5, text="a sentence", section="M")], confidence=0.9
        ),
        inference=NotApplicable(),
    )
    return prep


def _row(out: str) -> str:
    return next(ln for ln in out.splitlines() if ln.startswith("- Function-structure"))


def test_the_coverage_row_still_names_the_deferral_aespa_filled() -> None:
    out = to_report(_with_performed(_resolved("pipeline")), source="t")
    assert "method: deferred to fMRIPrep" in _row(out)


def test_a_filled_deferral_keeps_its_row_from_being_flagged() -> None:
    wrong = {"verdict": "wrong", "relied_on": "x", "relied_on_resolved": True, "reason": ""}
    verifier = {
        "status": "ok",
        "fields": {"coregistration.performed": wrong, "coregistration.method": wrong},
        "n_draft_lines": 2,
    }
    out = to_report(_with_performed(_resolved("pipeline")), source="t", verifier=verifier)
    assert "— flagged by the checking pass" not in _row(out)
