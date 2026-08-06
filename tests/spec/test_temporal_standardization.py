"""temporal_standardization step (Build 1 migration).

``voxel_temporal_zscore`` moved OUT of ``IntensityNormalizationConvention`` and
INTO the new terminal ``TemporalStandardization`` PreprocStep kind. Intensity
normalization is now magnitude-scaling-only; z-scoring is its own step. The
former ``_zscore_has_no_magnitude`` validator is replaced structurally: the step
has no ``value`` field, so a target magnitude is unrepresentable.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from fmri_repro.spec.preprocessing import (
    IntensityNormalization,
    IntensityNormalizationConvention,
    SpecifiedTerm,
    TemporalStandardization,
    TemporalStandardizationMethod,
)
from fmri_repro.spec.provenance import (
    Extracted,
    FieldConventionBasis,
    InferredDefault,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
)


def _span() -> Span:
    return Span(start=0, end=5, text="dummy", section="Methods")


def _extracted(field_id: str, t: Any, value: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](value=value, spans=[_span()], confidence=0.9),
        inference=NotApplicable(),
    )


def _missing(field_id: str, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[field_id], sections_searched=["Methods"]),
        inference=LeftMissing(reason="left_missing"),
    )


def _inferred(field_id: str, t: Any, value: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[field_id], sections_searched=["Methods"]),
        inference=InferredDefault[t](
            value=value,
            basis=FieldConventionBasis(source="test"),
            confidence=0.4,  # == field_convention ceiling
            alternative_inferences=[],
        ),
    )


def test_temporal_standardization_accepts_voxel_temporal_zscore() -> None:
    # 0.5.0: method is a SpecifiedTerm; a resolved member lands in .resolved.
    term = SpecifiedTerm[TemporalStandardizationMethod](
        verbatim="voxel_temporal_zscore",
        resolved="voxel_temporal_zscore",
        resolution="resolved",
    )
    step = TemporalStandardization(
        method=_extracted("method", SpecifiedTerm[TemporalStandardizationMethod], term)
    )
    assert step.kind == "temporal_standardization"
    assert step.method.extraction.value.resolved == "voxel_temporal_zscore"


def test_temporal_standardization_has_no_value_field() -> None:
    # Structural replacement for the former _zscore_has_no_magnitude validator:
    # a target magnitude is unrepresentable because there is no value field.
    assert "value" not in TemporalStandardization.model_fields
    assert set(TemporalStandardization.model_fields) == {"kind", "method"}


def test_intensity_no_longer_accepts_zscore() -> None:
    # voxel_temporal_zscore left the IntensityNormalizationConvention Literal -> rejected as a
    # resolved member of the retyped SpecifiedTerm convention field.
    with pytest.raises(ValidationError):
        IntensityNormalization(
            scope=_missing("scope", str),
            convention=_extracted(
                "convention",
                SpecifiedTerm[IntensityNormalizationConvention],
                SpecifiedTerm(resolved="voxel_temporal_zscore", resolution="resolved"),
            ),
            value=_missing("value", float),
        )


def test_temporal_standardization_method_not_inferrable() -> None:
    # method is inference_applicable=False (mirrors test_preprocessing.py
    # test_inferred_default_on_non_flagged_field_rejected): an INFERRED_DEFAULT
    # on method must be rejected.
    with pytest.raises(ValidationError):
        TemporalStandardization(
            method=_inferred(
                "method",
                SpecifiedTerm[TemporalStandardizationMethod],
                SpecifiedTerm(resolved="voxel_temporal_zscore", resolution="resolved"),
            )
        )
