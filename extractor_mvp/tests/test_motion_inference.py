"""The inference arm of motion_correction.method (DESIGN_motion_inference_arm.md; 2026-10-28).

Synthetic preprocessing objects only; the knowledge base is the real one (editable install). Every
case of §1's scope, F1's two paths, F2's precedence, F3's stability condition and F4's basis; the
report line's wording for both paths and its identity with and without the record.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fmri_repro.spec.preprocessing import (
    MotionCorrection,
    MotionCorrectionMethod,
    PipelineRef,
    Preprocessing,
    SpecifiedTerm,
)
from fmri_repro.spec.provenance import (
    AlternativeInference,
    DateInferredVersionBasis,
    Deferral,
    DeferredToCitation,
    Extracted,
    InferredDefault,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef

from extractor_mvp.extractor import _missing_pf
from extractor_mvp.motion_inference import (
    MotionInferenceCandidate,
    _choose,
    infer_motion_method,
)
from extractor_mvp.render import to_report


def _span() -> Span:
    return Span(start=10, end=20, text="a sentence", section="Methods")


def _applies_to() -> list[AcquisitionRef]:
    return [AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))]


def _method(kind: str, **kw: Any) -> ProvenancedField:
    t = SpecifiedTerm[MotionCorrectionMethod]
    if kind == "described_only":
        return ProvenancedField[t](
            field_id="method",
            extraction=Extracted[t](
                value=t(
                    verbatim=kw.get("phrase", "image coregistration"),
                    resolved=None,
                    resolution="unrecognized",
                ),
                spans=[_span()],
                confidence=0.9,
            ),
            inference=NotApplicable(),
        )
    if kind == "named_tool":
        return ProvenancedField[t](
            field_id="method",
            extraction=Extracted[t](
                value=t(verbatim="MCFLIRT", resolved="mcflirt", resolution="resolved"),
                spans=[_span()],
                confidence=0.9,
            ),
            inference=NotApplicable(),
        )
    if kind == "deferred":
        return ProvenancedField[t](
            field_id="method",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(
                        ref=kw.get("ref", "C-PAC"),
                        span=_span(),
                        target_kind=kw.get("target_kind", "pipeline"),
                    )
                ],
                searched_terms=[],
                sections_searched=[],
            ),
            inference=LeftMissing(reason="deferred_to_citation"),
        )
    if kind == "missing":
        return _missing_pf(
            "method", t, kw.get("reason", "extraction_quote_unresolved:quote_not_found")
        )
    raise ValueError(kind)


def _version(
    kind: str, value: str = "1.8.6", alternatives: tuple[str, ...] = ()
) -> ProvenancedField:
    if kind == "extracted":
        return ProvenancedField[str](
            field_id="version",
            extraction=Extracted[str](value=value, spans=[_span()], confidence=0.9),
            inference=NotApplicable(),
        )
    if kind == "date_inferred":
        basis = DateInferredVersionBasis(
            tool="x", inferred_version=value, paper_date=date(2024, 1, 1)
        )
        return ProvenancedField[str](
            field_id="version",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
            inference=InferredDefault[str](
                value=value,
                basis=basis,
                confidence=0.75,
                alternative_inferences=[
                    AlternativeInference[str](value=a, basis=basis, confidence=0.7)
                    for a in alternatives
                ],
            ),
        )
    return _missing_pf("version", str, "version_deferred_to_kb")


def _prep(
    method: ProvenancedField, base_name: str | None, version: ProvenancedField | None = None
) -> Preprocessing:
    others = {
        n: _missing_pf(n, Any, "not_targeted_by_mvp")
        for n in MotionCorrection.model_fields
        if n not in ("kind", "method")
    }
    step = MotionCorrection(method=method, **others)
    if base_name is None:
        base: Any = NotApplicable()
    else:
        base = ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=Extracted[PipelineRef](
                value=PipelineRef(name=base_name, version=version or _version("missing")),
                spans=[_span()],
                confidence=0.9,
            ),
            inference=NotApplicable(),
        )
    return Preprocessing(applies_to=_applies_to(), base_pipeline=base, steps=[step])


def _method_pf(prep: Preprocessing) -> ProvenancedField:
    return next(s for s in prep.steps if s.kind == "motion_correction").method


# --- the paths -------------------------------------------------------------------------------


def test_deferred_to_a_recognized_pipeline_with_a_certain_version_fills_the_arm_at_0_95() -> None:
    prep = _prep(_method("deferred", ref="C-PAC"), "C-PAC", _version("extracted", "1.8.6"))
    prep, rec = infer_motion_method(prep)
    pf = _method_pf(prep)
    assert (
        rec.path == "arm" and rec.basis_name == "pipeline" and rec.basis_type == "version_default"
    )
    assert rec.program == "3dvolreg" and rec.confidence == 0.95 and rec.source
    assert pf.inference.status == "INFERRED_DEFAULT"
    assert (
        pf.inference.value.verbatim == "3dvolreg" and pf.inference.value.resolved == "afni_3dvolreg"
    )
    assert pf.inference.basis.note == rec.source  # the note IS the source, for identical wording
    assert pf.extraction.status == "DEFERRED_TO_CITATION"  # the extraction arm is untouched
    assert rec.alternatives == []


def test_missing_with_a_package_name_fills_the_arm_from_the_package_at_0_70() -> None:
    prep = _prep(_method("missing"), "SPM12")
    prep, rec = infer_motion_method(prep)
    pf = _method_pf(prep)
    assert rec.path == "arm" and rec.basis_name == "package" and rec.basis_type == "derived"
    assert rec.program == "Realign" and rec.confidence == 0.70
    assert pf.inference.status == "INFERRED_DEFAULT"
    assert pf.inference.basis.source_field_ids == ["base_pipeline.name"]
    assert pf.inference.value.resolved == "spm_realign"


def test_described_only_gets_the_same_inference_as_a_diagnostic_and_the_field_is_untouched() -> (
    None
):
    prep = _prep(
        _method("described_only"),
        "Connectome Computation System",
        _version("date_inferred", "2e413113d3a981e3201cf81f5189c83e35483c60", ("2015",)),
    )
    before = _method_pf(prep).model_dump()
    prep, rec = infer_motion_method(prep)
    assert rec.path == "diagnostic" and rec.basis_name == "pipeline"
    assert rec.basis_type == "date_inferred_version" and rec.confidence == 0.75
    assert rec.program == "3dvolreg"
    assert _method_pf(prep).model_dump() == before  # F1: the contract holds; nothing on the field


def test_a_date_inferred_version_across_an_unstable_range_gives_no_pipeline_basis() -> None:
    prep = _prep(_method("missing"), "C-PAC", _version("date_inferred", "1.0.0", ("0.3.9.1",)))
    prep, rec = infer_motion_method(prep)
    assert rec.path == "none" and "no recognized pipeline with a usable version" in rec.reason
    assert _method_pf(prep).inference.status == "LEFT_MISSING"


def test_named_tool_is_never_filled() -> None:
    prep = _prep(_method("named_tool"), "FSL suite")
    before = _method_pf(prep).model_dump()
    prep, rec = infer_motion_method(prep)
    assert rec.path == "never" and _method_pf(prep).model_dump() == before


@pytest.mark.parametrize(
    ("method", "base", "reason_part"),
    [
        (
            _method("deferred", ref="Smith et al.", target_kind="paper"),
            "C-PAC",
            "deferred to a paper",
        ),
        (_method("missing", reason="not_targeted_by_mvp"), "C-PAC", "not targeted"),
        (_method("missing"), None, "no recognized pipeline"),
        (_method("described_only"), "XCP Engine", "no recognized pipeline"),
    ],
)
def test_nothing_to_infer_from(
    method: ProvenancedField, base: str | None, reason_part: str
) -> None:
    prep = _prep(method, base, _version("extracted", "1.8.6") if base == "C-PAC" else None)
    prep, rec = infer_motion_method(prep)
    assert rec.path == "none" and reason_part in rec.reason


def test_deferral_to_a_recognized_pipeline_without_a_base_pipeline_uses_its_default_version() -> (
    None
):
    """The motion sentence defers to the FCP scripts; nothing is on base_pipeline. The document
    has one version, so resolve_version would be certain -- but no version field exists here, so
    no basis: reported as none, not guessed."""
    prep = _prep(_method("deferred", ref="FCP analysis scripts"), None)
    prep, rec = infer_motion_method(prep)
    assert rec.path == "none"


# --- F2 precedence --------------------------------------------------------------------------


def _cand(name: str, certain: bool) -> MotionInferenceCandidate:
    from fmri_repro.spec.provenance import DerivedBasis

    return MotionInferenceCandidate(
        name, "x", DerivedBasis(source_field_ids=["f"], note="n"), 0.5, "s", certain
    )  # type: ignore[arg-type]


def test_choose_prefers_a_certain_pipeline_else_the_package_and_always_lists_the_loser() -> None:
    p_certain, p_uncertain, t = (
        _cand("pipeline", True),
        _cand("pipeline", False),
        _cand("package", False),
    )
    assert _choose(p_certain, t) == (p_certain, [t])
    assert _choose(p_uncertain, t) == (t, [p_uncertain])
    assert _choose(None, t) == (t, [])
    assert _choose(p_uncertain, None) == (p_uncertain, [])
    assert _choose(None, None) == (None, [])


# --- the report line (§4): the paper's words, then the inference; identical on both paths --------


def _method_line(report: str) -> str:
    return next(line for line in report.splitlines() if line.startswith("- method"))


def test_the_arm_renders_the_paper_words_then_the_inference_with_basis_and_source() -> None:
    prep = _prep(_method("deferred", ref="C-PAC"), "C-PAC", _version("extracted", "1.8.6"))
    prep, rec = infer_motion_method(prep)
    with_record = _method_line(to_report(prep, source="t", motion_inference=rec))
    without = _method_line(to_report(prep, source="t"))
    assert with_record.startswith(
        "- method = deferred to C-PAC   — tool not stated; AESPA infers 3dvolreg (version_default, "
    )
    assert rec.source in with_record
    assert with_record == without  # the stored result re-renders identically without the record
    assert "INFERRED — not stated in source" not in with_record


def test_the_diagnostic_renders_the_phrase_then_the_same_clause() -> None:
    prep = _prep(_method("described_only", phrase="image coregistration"), "SPM12")
    prep, rec = infer_motion_method(prep)
    assert rec.path == "diagnostic"
    line = _method_line(to_report(prep, source="t", motion_inference=rec))
    assert "image coregistration" in line
    assert "   — tool not stated; AESPA infers Realign (derived, " in line and rec.source in line
    plain = _method_line(to_report(prep, source="t"))
    assert "AESPA infers" not in plain  # without the record, the described_only line is as before


def test_a_named_tool_line_never_carries_the_clause() -> None:
    prep = _prep(_method("named_tool"), "FSL suite")
    prep, rec = infer_motion_method(prep)
    assert "AESPA infers" not in _method_line(to_report(prep, source="t", motion_inference=rec))


# --- the frozen copies (C21) ---------------------------------------------------------------------


def test_the_copied_tool_shape_rules_equal_the_frozen_heuristic() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import motion_value_kind as mvk

    from extractor_mvp import motion_guard as g

    assert g._TOOL_TOKENS_FROZEN == mvk._TOOL_TOKENS
    assert g._NOT_TOOL_INITIALISMS_FROZEN == mvk._NOT_TOOL_INITIALISMS
    assert g._INITIALISM_FROZEN.pattern == mvk._INITIALISM.pattern
    assert g._VERSIONED_FROZEN.pattern == mvk._VERSIONED.pattern
    for v in (
        "MCFLIRT",
        "SPM12",
        "AFNI",
        "image coregistration",
        "rigid body realignment",
        "EPI images",
    ):
        assert g.is_tool_shaped_frozen(v) == mvk.is_tool_shaped(v), v
