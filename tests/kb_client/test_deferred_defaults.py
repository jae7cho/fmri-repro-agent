"""fill_deferred_defaults (fix 3, the author's list of 2026-11-05; DESIGN_kb_deferred_defaults.md).
Synthetic preprocessing objects; the knowledge base is the real one (editable install)."""

from __future__ import annotations

import typing
from datetime import date
from typing import Any

import pytest

from fmri_repro.kb_client import base_pipeline as bp
from fmri_repro.kb_client.base_pipeline import fill_deferred_defaults
from fmri_repro.spec.preprocessing import (
    CompCor,
    Coregistration,
    PipelineRef,
    Preprocessing,
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
    VersionDefaultBasis,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef


def _span() -> Span:
    return Span(start=0, end=5, text="a sentence", section="Methods")


def _inner(cls: type, name: str) -> Any:
    ann = cls.model_fields[name].annotation
    pf = next(a for a in (typing.get_args(ann) or (ann,)) if a is not type(None))
    return pf


def _missing(cls: type, name: str) -> ProvenancedField:
    return _inner(cls, name)(
        field_id=name,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
        inference=LeftMissing(reason="not_stated_in_text"),
    )


def _deferred(cls: type, name: str, ref: str) -> ProvenancedField:
    return _inner(cls, name)(
        field_id=name,
        extraction=DeferredToCitation(
            deferrals=[Deferral(ref=ref, span=_span(), target_kind="pipeline")],
            searched_terms=[],
            sections_searched=[],
        ),
        inference=LeftMissing(reason="deferred_to_citation"),
    )


def _step(cls: type, deferred: dict[str, str]) -> Any:
    fields = {
        n: (_deferred(cls, n, deferred[n]) if n in deferred else _missing(cls, n))
        for n in cls.model_fields
        if n != "kind"
    }
    return cls(**fields)


def _version_extracted(v: str) -> ProvenancedField:
    return ProvenancedField[str](
        field_id="version",
        extraction=Extracted[str](value=v, spans=[_span()], confidence=0.9),
        inference=NotApplicable(),
    )


def _version_date_inferred(v: str, alts: tuple[str, ...]) -> ProvenancedField:
    basis = DateInferredVersionBasis(tool="x", inferred_version=v, paper_date=date(2021, 1, 1))
    return ProvenancedField[str](
        field_id="version",
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
        inference=InferredDefault[str](
            value=v,
            basis=basis,
            confidence=0.75,
            alternative_inferences=[
                AlternativeInference[str](value=a, basis=basis, confidence=0.7) for a in alts
            ],
        ),
    )


def _prep(
    name: str, version: ProvenancedField, ref: str, *, compcor: bool = False
) -> Preprocessing:
    base = ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(name=name, version=version), spans=[_span()], confidence=0.9
        ),
        inference=NotApplicable(),
    )
    steps: list[Any] = [
        _step(Coregistration, {"method": ref, "transform": ref, "cost_function": ref}),
    ]
    if compcor:
        steps.append(_step(CompCor, {"variance_threshold": ref, "mask_source": ref}))
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=base,
        steps=steps,
    )


_COREG = [
    ("coregistration.method", "fMRIPrep"),
    ("coregistration.transform", "fMRIPrep"),
    ("coregistration.cost_function", "fMRIPrep"),
]


def _coreg(prep: Preprocessing) -> Any:
    return next(s for s in prep.steps if s.kind == "coregistration")


def test_a_deferred_field_gets_the_kb_default_on_its_inference_arm_only() -> None:
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep"), _COREG
    )
    m = _coreg(prep).method
    assert m.extraction.status == "DEFERRED_TO_CITATION"  # untouched
    assert m.inference.status == "INFERRED_DEFAULT"
    assert m.inference.value.resolved == "bbregister" and m.inference.value.verbatim is None
    assert isinstance(m.inference.basis, VersionDefaultBasis)
    assert m.inference.basis.version == "20.2.0" and m.inference.confidence <= 0.95
    assert "fMRIPrep 20.2.0 methods boilerplate" in (m.inference.basis.note or "")
    assert _coreg(prep).transform.inference.value.resolved == "rigid"
    assert [r["filled"] for r in recs] == [True, True, True]


def test_a_version_written_with_a_leading_v_is_found() -> None:
    prep, _ = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("v1.5.3"), "fMRIPrep"), _COREG
    )
    assert _coreg(prep).method.inference.basis.version == "1.5.3"


def test_a_version_the_kb_does_not_list_fills_nothing() -> None:
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.1.0"), "fMRIPrep"), _COREG
    )
    assert _coreg(prep).method.inference.status == "LEFT_MISSING"
    assert all(r["reason"] == "not_in_kb" for r in recs)


def test_only_a_deferral_to_the_same_pipeline_is_filled() -> None:
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.2.0"), "C-PAC"),
        [("coregistration.method", "C-PAC")],
    )
    assert _coreg(prep).method.inference.status == "LEFT_MISSING"
    assert recs[0]["reason"] == "reference_names_another_pipeline"


def test_a_field_that_is_not_deferred_or_already_inferred_is_left() -> None:
    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep")
    c = _coreg(prep)
    c.interpolation = _missing(Coregistration, "interpolation")
    prep, recs = fill_deferred_defaults(prep, [("coregistration.interpolation", "fMRIPrep")])
    assert recs[0]["reason"] == "not_deferred"
    prep, _ = fill_deferred_defaults(prep, _COREG)
    prep, recs = fill_deferred_defaults(prep, _COREG)  # a second pass finds them filled
    assert all(r["reason"] == "inference_already_set" for r in recs)


def test_a_date_inferred_version_fills_only_values_stable_across_its_alternatives() -> None:
    paths = [
        ("compcor.variance_threshold", "fMRIPrep"),
        ("compcor.mask_source", "fMRIPrep"),
    ]
    prep = _prep("fMRIPrep", _version_date_inferred("20.2.0", ("1.5.3",)), "fMRIPrep", compcor=True)
    prep, recs = fill_deferred_defaults(prep, paths)
    cc = next(s for s in prep.steps if s.kind == "compcor")
    assert cc.variance_threshold.inference.status == "INFERRED_DEFAULT"
    assert isinstance(cc.variance_threshold.inference.basis, DateInferredVersionBasis)
    assert cc.variance_threshold.inference.confidence <= 0.75
    assert cc.mask_source.inference.status == "LEFT_MISSING"  # the masks differ by version
    assert {r["field"]: r["filled"] for r in recs} == {
        "compcor.variance_threshold": True,
        "compcor.mask_source": False,
    }


def test_hcp_from_glasser_on_a_date_inferred_version() -> None:
    prep, _recs = fill_deferred_defaults(
        _prep(
            "HCP minimal preprocessing pipeline",
            _version_date_inferred("v4.1.3", ("v3.4.0",)),
            "HCP minimal preprocessing pipeline",
        ),
        [
            ("coregistration.transform", "HCP minimal preprocessing pipeline"),
            ("coregistration.cost_function", "HCP minimal preprocessing pipeline"),
            ("coregistration.method", "HCP minimal preprocessing pipeline"),
        ],
    )
    c = _coreg(prep)
    assert c.transform.inference.value.resolved == "rigid"
    assert c.cost_function.inference.value.resolved == "boundary_based"
    assert c.method.inference.status == "LEFT_MISSING"  # two programs; not entered
    assert "Glasser" in (c.transform.inference.basis.note or "")


def test_a_kb_value_the_field_does_not_accept_fills_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = bp.get_param_defaults

    def bogus(pid: str, version: str, fields: list[str], **kw: Any) -> Any:
        out = real(pid, version, fields, **kw)
        r = out["coregistration.method"]
        out["coregistration.method"] = type(r)(
            value="not_a_member",
            basis_type=r.basis_type,
            proposed_confidence=r.proposed_confidence,
            source=r.source,
            alternative_candidates=[],
        )
        return out

    monkeypatch.setattr(bp, "get_param_defaults", bogus)
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep"), _COREG
    )
    assert _coreg(prep).method.inference.status == "LEFT_MISSING"
    assert recs[0]["reason"] == "value_does_not_validate"
    assert _coreg(prep).transform.inference.status == "INFERRED_DEFAULT"  # the others still fill


def test_a_list_valued_field_is_filled_as_a_list_of_terms() -> None:
    from fmri_repro.spec.preprocessing import Segmentation

    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep")
    prep.steps.append(_step(Segmentation, {"tissue_classes": "fMRIPrep"}))
    prep, _ = fill_deferred_defaults(prep, [("segmentation.tissue_classes", "fMRIPrep")])
    seg = next(s for s in prep.steps if s.kind == "segmentation")
    assert [t.resolved for t in seg.tissue_classes.inference.value] == [
        "csf",
        "white_matter",
        "gray_matter",
    ]
