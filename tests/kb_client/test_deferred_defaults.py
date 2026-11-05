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


def test_every_filled_record_revalidates_as_a_whole() -> None:
    # fix 3 follow-up (2026-11-05): the committed fill set arms the step's FieldMeta forbade, and
    # setattr never ran the step validator; a live run then crashed on re-validation
    from fmri_repro.spec.preprocessing import Segmentation

    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep", compcor=True)
    prep.steps.append(_step(Segmentation, {"method": "fMRIPrep", "tissue_classes": "fMRIPrep"}))
    paths = [
        *_COREG,
        ("compcor.variance_threshold", "fMRIPrep"),
        ("compcor.mask_source", "fMRIPrep"),
        ("segmentation.method", "fMRIPrep"),
        ("segmentation.tissue_classes", "fMRIPrep"),
    ]
    prep, recs = fill_deferred_defaults(prep, paths)
    assert all(r["filled"] for r in recs)
    Preprocessing.model_validate(prep.model_dump())  # raises if any arm breaks a step invariant


def test_a_field_whose_meta_forbids_inference_is_never_filled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = bp.get_param_defaults

    def with_extra(pid: str, version: str, fields: list[str], **kw: Any) -> Any:
        out = real(pid, version, [*fields, "coregistration.method"], **kw)
        r = out["coregistration.method"]
        out["coregistration.nonlinear_transform_type"] = type(r)(
            value="SyN",
            basis_type=r.basis_type,
            proposed_confidence=r.proposed_confidence,
            source=r.source,
            alternative_candidates=[],
        )
        return out

    monkeypatch.setattr(bp, "get_param_defaults", with_extra)
    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep")
    c = _coreg(prep)
    c.nonlinear_transform_type = _deferred(Coregistration, "nonlinear_transform_type", "fMRIPrep")
    prep, recs = fill_deferred_defaults(
        prep, [("coregistration.nonlinear_transform_type", "fMRIPrep")]
    )
    assert recs[0]["reason"] == "inference_not_applicable"
    assert _coreg(prep).nonlinear_transform_type.inference.status == "LEFT_MISSING"


def test_a_step_that_rejects_the_filled_arm_is_left_as_it_was(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = Coregistration.model_validate

    def rejects(data: Any, *a: Any, **k: Any) -> Any:
        return real({})  # any other step invariant failing raises the same way

    monkeypatch.setattr(Coregistration, "model_validate", rejects)
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep"), _COREG
    )
    assert all(r["reason"] == "step_rejects_inference" for r in recs)
    assert _coreg(prep).method.inference.status == "LEFT_MISSING"


# --- the author's ruling 1 (2026-11-05): an inferred value only from a sourced KB entry -----------


def test_a_kb_entry_without_a_source_fills_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    real = bp.get_param_defaults

    def unsourced(pid: str, version: str, fields: list[str], **kw: Any) -> Any:
        out = real(pid, version, fields, **kw)
        r = out["coregistration.method"]
        out["coregistration.method"] = type(r)(
            value=r.value,
            basis_type=r.basis_type,
            proposed_confidence=r.proposed_confidence,
            source="  ",
            alternative_candidates=[],
        )
        return out

    monkeypatch.setattr(bp, "get_param_defaults", unsourced)
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep"), _COREG
    )
    assert recs[0]["reason"] == "kb_entry_unsourced"
    assert _coreg(prep).method.inference.status == "LEFT_MISSING"


def test_a_flipped_field_with_no_kb_entry_stays_left_missing() -> None:
    # fMRIPrep 20.1.0 is on the timeline with no boilerplate entries: nothing to fill from
    prep, recs = fill_deferred_defaults(
        _prep("fMRIPrep", _version_extracted("20.1.0"), "fMRIPrep"), _COREG
    )
    assert all(r["reason"] == "not_in_kb" for r in recs)
    assert _coreg(prep).method.inference.status == "LEFT_MISSING"


def test_the_schema_refuses_an_inference_on_these_fields_from_anything_but_a_sourced_kb_entry() -> (
    None
):
    from fmri_repro.spec.preprocessing import SpecifiedTerm
    from fmri_repro.spec.provenance import DerivedBasis, PriorPublicationBasis

    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep")
    c = _coreg(prep)
    term = SpecifiedTerm(verbatim=None, resolved="bbregister", resolution="resolved")
    for basis in (
        PriorPublicationBasis(citation="Esteban 2019"),
        DerivedBasis(source_field_ids=["base_pipeline"], note="x"),
        VersionDefaultBasis(tool="fmriprep", version="20.2.0", note=None),
    ):
        payload = c.model_dump()
        payload["method"]["inference"] = InferredDefault(
            value=term, basis=basis, confidence=0.5, alternative_inferences=[]
        ).model_dump()
        with pytest.raises(ValueError, match="sourced KB entry"):
            Coregistration.model_validate(payload)
    payload = c.model_dump()
    payload["method"]["inference"] = InferredDefault(
        value=term,
        basis=VersionDefaultBasis(tool="fmriprep", version="20.2.0", note="a source"),
        confidence=0.9,
        alternative_inferences=[],
    ).model_dump()
    Coregistration.model_validate(payload)  # a sourced KB basis is accepted


def test_a_value_the_paper_states_is_never_replaced_by_the_kb() -> None:
    # the author's list of 2026-11-05, third round, item 3: extraction always wins. A field the
    # paper states keeps its extracted value and gets no inference, even when the record's
    # deferral list names it (a paper can state a value and also cite the pipeline for it).
    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "fMRIPrep")
    c = _coreg(prep)
    stated = _inner(Coregistration, "cost_function").model_validate(
        {
            "field_id": "cost_function",
            "extraction": {
                "status": "EXTRACTED",
                "value": {"verbatim": "mutual information", "resolved": "mutual_information"},
                "spans": [_span().model_dump()],
                "confidence": 0.9,
            },
            "inference": {"status": "NOT_APPLICABLE"},
        }
    )
    c.cost_function = stated
    before = stated.model_dump()
    prep, recs = fill_deferred_defaults(prep, _COREG)
    by_field = {r["field"]: r for r in recs}
    assert by_field["coregistration.cost_function"] == {
        "field": "coregistration.cost_function",
        "filled": False,
        "reason": "not_deferred",
    }
    assert _coreg(prep).cost_function.model_dump() == before
    assert by_field["coregistration.method"]["filled"]  # the deferred ones beside it still fill
