"""12-check verification suite for the version-stable core provenance types.

This suite IS the contract for ``src/fmri_repro/spec/provenance.py`` —
the module is "logic-frozen" insofar as these tests stay green.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fmri_repro.spec.provenance import (
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
    assert "MISSING_FROM_PAPER requires INFERRED_DEFAULT or LEFT_MISSING" in str(excinfo.value)


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
    assert "INFERRED_DEFAULT or LEFT_MISSING" in msg


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
