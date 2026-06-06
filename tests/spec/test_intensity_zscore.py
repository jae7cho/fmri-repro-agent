"""The voxel_temporal_zscore convention must carry no target magnitude."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from fmri_repro.spec.preprocessing import IntensityNormalization
from fmri_repro.spec.provenance import (
    Extracted,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
)


def _span() -> Span:
    return Span(start=0, end=5, text="dummy", section="Methods")


def _missing(field_id: str, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[field_id], sections_searched=["Methods"]),
        inference=LeftMissing(reason="not_applicable_to_convention"),
    )


def _extracted(field_id: str, t: Any, value: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](value=value, spans=[_span()], confidence=0.9),
        inference=NotApplicable(),
    )


def _intensity(convention_value: str, value_pf: ProvenancedField) -> IntensityNormalization:
    return IntensityNormalization(
        scope=_missing("scope", str),
        convention=_extracted("convention", str, convention_value),
        value=value_pf,
    )


def test_zscore_with_no_magnitude_is_accepted():
    # value carries no concrete number -> consistent
    inten = _intensity("voxel_temporal_zscore", _missing("value", float))
    assert inten.convention.extraction.value == "voxel_temporal_zscore"


def test_zscore_with_concrete_value_is_rejected():
    with pytest.raises(ValidationError, match="no target magnitude"):
        _intensity("voxel_temporal_zscore", _extracted("value", float, 1000.0))


def test_magnitude_conventions_still_accept_a_value():
    # the new global_* conventions DO have a magnitude — must not be rejected
    inten = _intensity("global_median_1000", _extracted("value", float, 1000.0))
    assert inten.value.extraction.value == 1000.0
