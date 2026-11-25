"""12-check verification suite for the version-stable core provenance types.

This suite IS the contract for ``src/fmri_repro/spec/provenance.py`` —
the module is "logic-frozen" insofar as these tests stay green.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fmri_repro.spec.provenance import (
    INFERRED_STATUSES,
    AlternativeInference,
    Deferral,
    DeferredToCitation,
    DerivedBasis,
    Extracted,
    FieldConventionBasis,
    InferredDefault,
    LabPriorBasis,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    PriorPublicationBasis,
    ProvenancedField,
    Span,
    VersionDefaultBasis,
)


def _span() -> Span:
    return Span(start=0, end=7, text="TR = 2s", section="Methods")


# ---------------------------------------------------------------------------
# 1. Legal: EXTRACTED + NOT_APPLICABLE
# ---------------------------------------------------------------------------
def test_legal_extracted_not_applicable_round_trip() -> None:
    pf = ProvenancedField[float](
        field_id="acquisition.tr",
        extraction=Extracted[float](value=2.0, spans=[_span()], confidence=0.9),
        inference=NotApplicable(),
    )
    assert pf.extraction.status == "EXTRACTED"
    assert pf.inference.status == "NOT_APPLICABLE"
    assert ProvenancedField[float].model_validate_json(pf.model_dump_json()) == pf


# ---------------------------------------------------------------------------
# 2. Legal: MISSING_FROM_PAPER + INFERRED_DEFAULT (under ceiling, w/ alt)
# ---------------------------------------------------------------------------
def test_legal_missing_inferred_default_with_alternative() -> None:
    pf = ProvenancedField[float](
        field_id="acquisition.te",
        extraction=MissingFromPaper(
            searched_terms=["TE", "echo time"],
            sections_searched=["Methods"],
        ),
        inference=InferredDefault[float](
            value=30.0,
            basis=VersionDefaultBasis(tool="fMRIPrep", version="23.2.1"),
            confidence=0.95,
            alternative_inferences=[
                AlternativeInference[float](
                    value=25.0,
                    basis=LabPriorBasis(lab_id="poldrack_lab_2023"),
                    confidence=0.5,
                ),
            ],
        ),
    )
    assert pf.inference.status == "INFERRED_DEFAULT"
    assert ProvenancedField[float].model_validate_json(pf.model_dump_json()) == pf


# ---------------------------------------------------------------------------
# 3. Legal: MISSING_FROM_PAPER + LEFT_MISSING
# ---------------------------------------------------------------------------
def test_legal_missing_left_missing_round_trip() -> None:
    pf = ProvenancedField[int](
        field_id="acquisition.n_volumes",
        extraction=MissingFromPaper(searched_terms=["TRs"], sections_searched=["Methods"]),
        inference=LeftMissing(reason="not reported"),
    )
    assert pf.inference.status == "LEFT_MISSING"
    assert ProvenancedField[int].model_validate_json(pf.model_dump_json()) == pf


# ---------------------------------------------------------------------------
# 4. Illegal coupling: EXTRACTED + INFERRED_DEFAULT
# ---------------------------------------------------------------------------
def test_illegal_extracted_plus_inferred_default() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProvenancedField[float](
            field_id="acquisition.tr",
            extraction=Extracted[float](value=2.0, spans=[_span()], confidence=0.9),
            inference=InferredDefault[float](
                value=2.0,
                basis=VersionDefaultBasis(tool="fMRIPrep", version="23.2.1"),
                confidence=0.5,
                alternative_inferences=[],
            ),
        )
    assert "Configurator must not touch" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. Illegal coupling: MISSING_FROM_PAPER + NOT_APPLICABLE
# ---------------------------------------------------------------------------
def test_illegal_missing_plus_not_applicable() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProvenancedField[float](
            field_id="acquisition.te",
            extraction=MissingFromPaper(searched_terms=["TE"], sections_searched=["Methods"]),
            inference=NotApplicable(),
        )
    # 0.8.0: the message names the three inferred statuses
    assert (
        "MISSING_FROM_PAPER requires an inferred value (INFERRED_DEFAULT, INFERRED_FROM_CITATION, "
        "INFERRED_FROM_TEXT) or LEFT_MISSING" in str(excinfo.value)
    )


# ---------------------------------------------------------------------------
# 6. Ceiling — main confidence (lab_prior at 0.60 exceeds 0.50)
# ---------------------------------------------------------------------------
def test_ceiling_main_confidence_exceeded() -> None:
    with pytest.raises(ValidationError) as excinfo:
        InferredDefault[float](
            value=30.0,
            basis=LabPriorBasis(lab_id="some_lab"),
            confidence=0.60,
            alternative_inferences=[],
        )
    msg = str(excinfo.value)
    assert "confidence 0.6" in msg
    assert "0.5" in msg
    assert "lab_prior" in msg


# ---------------------------------------------------------------------------
# 7. Ceiling — alternative_inference confidence
# ---------------------------------------------------------------------------
def test_ceiling_alternative_confidence_exceeded() -> None:
    with pytest.raises(ValidationError) as excinfo:
        InferredDefault[float](
            value=30.0,
            basis=VersionDefaultBasis(tool="fMRIPrep", version="23.2.1"),
            confidence=0.95,
            alternative_inferences=[
                AlternativeInference[float](
                    value=25.0,
                    basis=FieldConventionBasis(source="textbook"),
                    confidence=0.50,  # ceiling for field_convention is 0.40
                ),
            ],
        )
    msg = str(excinfo.value)
    assert "alt confidence" in msg
    assert "field_convention" in msg


# ---------------------------------------------------------------------------
# 8. Extraction requires at least one Span (empty list rejected)
# ---------------------------------------------------------------------------
def test_extracted_rejects_empty_spans() -> None:
    with pytest.raises(ValidationError):
        Extracted[float](value=2.0, spans=[], confidence=0.9)


# ---------------------------------------------------------------------------
# 9. Omitted alternative_inferences is rejected (required, no default)
# ---------------------------------------------------------------------------
def test_inferred_default_requires_alternative_inferences_field() -> None:
    with pytest.raises(ValidationError) as excinfo:
        InferredDefault[float].model_validate(
            {
                "value": 30.0,
                "basis": {
                    "basis_type": "version_default",
                    "tool": "fMRIPrep",
                    "version": "23.2.1",
                },
                "confidence": 0.95,
                # alternative_inferences intentionally omitted
            }
        )
    assert "alternative_inferences" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 10. Unknown discriminator on basis is rejected
# ---------------------------------------------------------------------------
def test_unknown_basis_discriminator_rejected() -> None:
    with pytest.raises(ValidationError):
        InferredDefault[float].model_validate(
            {
                "value": 30.0,
                "basis": {"basis_type": "bogus_basis", "blah": "x"},
                "confidence": 0.5,
                "alternative_inferences": [],
            }
        )


# ---------------------------------------------------------------------------
# 10b. Extracted.span_recovered: defaults False, explicit True round-trips (v0.4.0)
# ---------------------------------------------------------------------------
def test_extracted_span_recovered_default_and_round_trip() -> None:
    # Optional-with-default: an Extracted built without the flag reads False, so a v0.3.0
    # document (which never carried the field) parses unchanged.
    default = Extracted[float](value=2.0, spans=[_span()], confidence=0.9)
    assert default.span_recovered is False

    # An explicit True survives a JSON round-trip inside a ProvenancedField.
    pf = ProvenancedField[float](
        field_id="acquisition.tr",
        extraction=Extracted[float](
            value=2.0, spans=[_span()], confidence=0.9, span_recovered=True
        ),
        inference=NotApplicable(),
    )
    restored = ProvenancedField[float].model_validate_json(pf.model_dump_json())
    assert restored == pf
    assert restored.extraction.status == "EXTRACTED"
    assert restored.extraction.span_recovered is True


# ---------------------------------------------------------------------------
# 11. JSON Schema export for ProvenancedField[float|str|bool]
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload_type", [float, str, bool])
def test_json_schema_export(payload_type: type) -> None:
    # `payload_type` is a runtime fixture value, not a static type — mypy
    # cannot use it as a generic parameter. Logic is correct; suppress narrowly.
    schema = ProvenancedField[payload_type].model_json_schema()  # type: ignore[valid-type]
    assert "$defs" in schema
    defs = schema["$defs"]
    # All five basis arms must be reachable in $defs
    for basis_def in (
        "VersionDefaultBasis",
        "DateInferredVersionBasis",
        "PriorPublicationBasis",
        "LabPriorBasis",
        "FieldConventionBasis",
        "DerivedBasis",
    ):
        assert basis_def in defs, f"{basis_def} missing from $defs for {payload_type}"
    # Both extraction arms and all three inference arms must be reachable.
    # Names are pydantic-generated; check substrings.
    def_names = "\n".join(defs.keys())
    assert "MissingFromPaper" in def_names
    assert "DeferredToCitation" in def_names
    assert "LeftMissing" in def_names
    assert "NotApplicable" in def_names
    assert "Extracted" in def_names
    assert "InferredDefault" in def_names


# ---------------------------------------------------------------------------
# 12. Full ProvenancedField round-trip via JSON
# ---------------------------------------------------------------------------
def test_provenanced_field_json_round_trip() -> None:
    pf = ProvenancedField[float](
        field_id="acquisition.te",
        extraction=MissingFromPaper(
            searched_terms=["TE"],
            sections_searched=["Methods"],
        ),
        inference=InferredDefault[float](
            value=30.0,
            basis=VersionDefaultBasis(tool="fMRIPrep", version="23.2.1"),
            confidence=0.95,
            alternative_inferences=[],
        ),
    )
    js = pf.model_dump_json()
    restored = ProvenancedField[float].model_validate_json(js)
    assert restored == pf


# ---------------------------------------------------------------------------
# 13. DerivedBasis accepted under ceiling (boundary: 0.70 ≤ 0.70)
# ---------------------------------------------------------------------------
def test_derived_basis_at_ceiling_accepted() -> None:
    inf = InferredDefault[float](
        value=300.0,
        basis=DerivedBasis(source_field_ids=["acquisition.n_volumes", "acquisition.tr"]),
        confidence=0.70,
        alternative_inferences=[],
    )
    assert inf.basis.basis_type == "derived"


# ---------------------------------------------------------------------------
# 14. DerivedBasis ceiling — confidence > 0.70 rejected
# ---------------------------------------------------------------------------
def test_derived_basis_ceiling_exceeded() -> None:
    with pytest.raises(ValidationError) as excinfo:
        InferredDefault[float](
            value=300.0,
            basis=DerivedBasis(source_field_ids=["acquisition.tr"]),
            confidence=0.71,
            alternative_inferences=[],
        )
    msg = str(excinfo.value)
    assert "derived" in msg
    assert "0.7" in msg


# ---------------------------------------------------------------------------
# 15. DerivedBasis source_field_ids — empty or omitted rejected
# ---------------------------------------------------------------------------
def test_derived_basis_source_field_ids_required() -> None:
    with pytest.raises(ValidationError):
        DerivedBasis(source_field_ids=[])
    with pytest.raises(ValidationError):
        DerivedBasis.model_validate({})  # field omitted


# ---------------------------------------------------------------------------
# DEFERRED_TO_CITATION arm
# ---------------------------------------------------------------------------
def _deferral() -> Deferral:
    return Deferral(
        ref="Gordon 2017",
        span=Span(
            start=0,
            end=40,
            text="preprocessing as in Gordon et al. (2017)",
            section="Methods",
        ),
        target_kind="paper",
    )


# ---------------------------------------------------------------------------
# 16. DEFERRED_TO_CITATION + LEFT_MISSING — happy path, round-trips
# ---------------------------------------------------------------------------
def test_deferred_to_citation_accepts_with_one_deferral() -> None:
    pf = ProvenancedField[float](
        field_id="acquisition.partial_fourier",
        extraction=DeferredToCitation(
            deferrals=[_deferral()],
            searched_terms=["partial fourier"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="paper defers to cited methods"),
    )
    assert pf.extraction.status == "DEFERRED_TO_CITATION"
    assert ProvenancedField[float].model_validate_json(pf.model_dump_json()) == pf


# ---------------------------------------------------------------------------
# 17. DeferredToCitation rejects empty deferrals
# ---------------------------------------------------------------------------
def test_deferred_to_citation_rejects_empty_deferrals() -> None:
    with pytest.raises(ValidationError) as excinfo:
        DeferredToCitation(
            deferrals=[],
            searched_terms=[],
            sections_searched=["Methods"],
        )
    assert "deferrals" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 18. DEFERRED_TO_CITATION + NOT_APPLICABLE rejected
# ---------------------------------------------------------------------------
def test_deferred_plus_not_applicable_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProvenancedField[float](
            field_id="acquisition.partial_fourier",
            extraction=DeferredToCitation(
                deferrals=[_deferral()],
                searched_terms=[],
                sections_searched=["Methods"],
            ),
            inference=NotApplicable(),
        )
    msg = str(excinfo.value)
    assert "DEFERRED_TO_CITATION" in msg
    assert "INFERRED_DEFAULT, INFERRED_FROM_CITATION, INFERRED_FROM_TEXT) or LEFT_MISSING" in msg


# ---------------------------------------------------------------------------
# 19. DEFERRED_TO_CITATION + INFERRED_DEFAULT accepted (under ceiling)
# ---------------------------------------------------------------------------
def test_deferred_plus_inferred_default_accepted() -> None:
    pf = ProvenancedField[float](
        field_id="acquisition.partial_fourier",
        extraction=DeferredToCitation(
            deferrals=[_deferral()],
            searched_terms=["partial fourier"],
            sections_searched=["Methods"],
        ),
        inference=InferredDefault[float](
            value=0.75,
            basis=VersionDefaultBasis(tool="fMRIPrep", version="23.2.1"),
            confidence=0.9,
            alternative_inferences=[],
        ),
    )
    assert pf.inference.status == "INFERRED_DEFAULT"
    assert ProvenancedField[float].model_validate_json(pf.model_dump_json()) == pf


# --- 0.7.0: Varied (DESIGN_applies_to.md Stage 1, fork A1, 2026-11-11) ---------------------------


def _vspan() -> Span:
    return Span(start=0, end=4, text="text")


def test_varied_holds_parts_and_no_single_value() -> None:
    from fmri_repro.spec.provenance import STATED_STATUSES, Variant, Varied

    v = Varied[float](
        variants=[
            Variant[float](value=6.0, spans=[_vspan()], applies_to="ALFF", confidence=0.8),
            Variant[float](value=4.0, spans=[_vspan()], applies_to="ReHo", confidence=0.8),
        ]
    )
    pf = ProvenancedField[float](field_id="fwhm_mm", extraction=v, inference=NotApplicable())
    assert pf.extraction.status == "VARIED" and not hasattr(pf.extraction, "value")
    assert ProvenancedField[float].model_validate_json(pf.model_dump_json()) == pf
    assert STATED_STATUSES == {"EXTRACTED", "VARIED"}


def test_varied_rejects_all_repeats_and_a_stray_valueless_entry() -> None:
    from fmri_repro.spec.provenance import COMPARED_MODELS, Variant, Varied

    def var(value: float | None, applies_to: str) -> Variant[float]:
        return Variant[float](value=value, spans=[_vspan()], applies_to=applies_to, confidence=0.8)

    for bad in (
        [var(6.0, "all")],
        [var(6.0, "Part III"), var(4.0, "part III")],
        [var(None, "ReHo")],
        [var(None, COMPARED_MODELS), var(6.0, "ALFF")],
    ):
        with pytest.raises(ValidationError):
            Varied[float](variants=bad)
    with pytest.raises(ValidationError):
        Varied[float](variants=[])
    assert Varied[float](variants=[var(None, COMPARED_MODELS)]).variants[0].value is None


def test_varied_couples_like_extracted() -> None:
    from fmri_repro.spec.provenance import Variant, Varied

    v = Varied[float](
        variants=[Variant[float](value=6.0, spans=[_vspan()], applies_to="ALFF", confidence=0.8)]
    )
    with pytest.raises(ValidationError, match="VARIED requires inference=NOT_APPLICABLE"):
        ProvenancedField[float](field_id="fwhm_mm", extraction=v, inference=LeftMissing(reason="x"))


def test_normalize_applies_to() -> None:
    from fmri_repro.spec.provenance import normalize_applies_to

    assert normalize_applies_to("The Parts I\u2013II") == "parts i-ii"
    assert normalize_applies_to("ALFF & fALFF.") == "alff and falff"
    assert normalize_applies_to("  task - fMRI ") == "task-fmri"


# ---------------------------------------------------------------------------
# 0.8.0: two more inference statuses (DESIGN_prompt_schema_2026-11 B6; rulings 8 and 13)
# ---------------------------------------------------------------------------
_FROM_TEXT = DerivedBasis(source_field_ids=["step_order"], note="slice timing listed first")
_FROM_CITATION = PriorPublicationBasis(citation="Behzadi et al. 2007", note="the CompCor paper")


def _missing_arm() -> MissingFromPaper:
    return MissingFromPaper(searched_terms=[], sections_searched=["Methods"])


def _deferred_arm() -> DeferredToCitation:
    return DeferredToCitation(
        deferrals=[_deferral()], searched_terms=[], sections_searched=["Methods"]
    )


def test_the_inference_statuses_are_these_three() -> None:
    import typing

    field = InferredDefault.model_fields["status"]
    assert set(typing.get_args(field.annotation)) == INFERRED_STATUSES
    assert INFERRED_STATUSES == {
        "INFERRED_DEFAULT",
        "INFERRED_FROM_TEXT",
        "INFERRED_FROM_CITATION",
    }
    assert field.default == "INFERRED_DEFAULT"  # a 0.7.4 writer's value, unchanged


@pytest.mark.parametrize(
    ("status", "basis", "ceiling"),
    [
        ("INFERRED_FROM_TEXT", _FROM_TEXT, 0.70),
        ("INFERRED_FROM_CITATION", _FROM_CITATION, 0.60),
    ],
)
def test_a_new_status_is_accepted_with_its_basis_on_a_missing_or_deferred_field(
    status: str, basis: object, ceiling: float
) -> None:
    for extraction in (_missing_arm(), _deferred_arm()):
        pf = ProvenancedField[str](
            field_id="relative_to_motion_correction",
            extraction=extraction,
            inference=InferredDefault[str](
                status=status,
                value="before",
                basis=basis,
                confidence=ceiling,
                alternative_inferences=[],
            ),
        )
        assert pf.inference.status == status
        again = ProvenancedField[str].model_validate_json(pf.model_dump_json())
        assert again == pf and again.inference.status == status
    # the ceiling of the basis holds for the new status as for a default
    with pytest.raises(ValidationError, match="ceiling"):
        InferredDefault[str](
            status=status,
            value="before",
            basis=basis,
            confidence=ceiling + 0.01,
            alternative_inferences=[],
        )


def test_each_new_status_requires_its_own_basis() -> None:
    with pytest.raises(ValidationError, match="INFERRED_FROM_TEXT requires a derived basis"):
        InferredDefault[str](
            status="INFERRED_FROM_TEXT",
            value="before",
            basis=_FROM_CITATION,
            confidence=0.5,
            alternative_inferences=[],
        )
    with pytest.raises(
        ValidationError, match="INFERRED_FROM_CITATION requires a prior_publication basis"
    ):
        InferredDefault[str](
            status="INFERRED_FROM_CITATION",
            value="a",
            basis=_FROM_TEXT,
            confidence=0.5,
            alternative_inferences=[],
        )
    # a default keeps every basis it could have before 0.8.0, these two included
    for basis in (_FROM_TEXT, _FROM_CITATION, VersionDefaultBasis(tool="fMRIPrep", version="23")):
        inferred = InferredDefault[str](
            value="x", basis=basis, confidence=0.4, alternative_inferences=[]
        )
        assert inferred.status == "INFERRED_DEFAULT"


def test_an_alternative_of_a_new_status_rests_on_the_same_kind_of_basis() -> None:
    """The two statuses pass the gates that refuse a default (``inference_applicable``, the KB
    source), so an alternative may not bring a default in beside them."""
    a_default = AlternativeInference[str](
        value="after", basis=VersionDefaultBasis(tool="fMRIPrep", version="23"), confidence=0.9
    )
    with pytest.raises(ValidationError, match="an alternative requires a derived basis too"):
        InferredDefault[str](
            status="INFERRED_FROM_TEXT",
            value="before",
            basis=_FROM_TEXT,
            confidence=0.5,
            alternative_inferences=[a_default],
        )
    from_text = AlternativeInference[str](value="after", basis=_FROM_TEXT, confidence=0.4)
    with pytest.raises(
        ValidationError, match="an alternative requires a prior_publication basis too"
    ):
        InferredDefault[str](
            status="INFERRED_FROM_CITATION",
            value="a",
            basis=_FROM_CITATION,
            confidence=0.5,
            alternative_inferences=[from_text],
        )
    # an alternative on the same kind of basis is kept
    kept = InferredDefault[str](
        status="INFERRED_FROM_TEXT",
        value="before",
        basis=_FROM_TEXT,
        confidence=0.5,
        alternative_inferences=[from_text],
    )
    assert kept.alternative_inferences == [from_text]
    # control: a default takes alternatives on any basis, as before 0.8.0
    default = InferredDefault[str](
        value="x", basis=_FROM_TEXT, confidence=0.4, alternative_inferences=[a_default]
    )
    assert default.status == "INFERRED_DEFAULT" and default.alternative_inferences == [a_default]


def test_a_stated_value_takes_no_inference_of_any_status() -> None:
    for status, basis in (
        ("INFERRED_FROM_TEXT", _FROM_TEXT),
        ("INFERRED_FROM_CITATION", _FROM_CITATION),
    ):
        with pytest.raises(ValidationError, match="requires inference=NOT_APPLICABLE"):
            ProvenancedField[str](
                field_id="f",
                extraction=Extracted[str](value="after", spans=[_span()], confidence=0.9),
                inference=InferredDefault[str](
                    status=status,
                    value="before",
                    basis=basis,
                    confidence=0.5,
                    alternative_inferences=[],
                ),
            )


def test_an_unknown_inference_status_is_refused() -> None:
    payload = {
        "field_id": "f",
        "extraction": _missing_arm().model_dump(),
        "inference": {
            "status": "INFERRED_FROM_MODEL",
            "value": "before",
            "basis": _FROM_TEXT.model_dump(),
            "confidence": 0.5,
            "alternative_inferences": [],
        },
    }
    with pytest.raises(ValidationError, match="INFERRED_FROM_MODEL"):
        ProvenancedField[str].model_validate(payload)
