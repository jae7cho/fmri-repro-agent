"""IntensityNormalization magnitude conventions still accept a target value.

Surviving test from the former ``test_intensity_zscore.py``. After the Build 1
migration, ``voxel_temporal_zscore`` is no longer an intensity convention (it
moved to the ``temporal_standardization`` step — see
``test_temporal_standardization.py``), so intensity normalization is
magnitude-scaling-only and the magnitude conventions must still carry a value.
"""

from __future__ import annotations

from typing import Any

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
        inference=LeftMissing(reason="left_missing"),
    )


def _extracted(field_id: str, t: Any, value: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](value=value, spans=[_span()], confidence=0.9),
        inference=NotApplicable(),
    )


def test_magnitude_conventions_still_accept_a_value() -> None:
    # the global_* conventions DO have a magnitude — must not be rejected
    inten = IntensityNormalization(
        scope=_missing("scope", str),
        convention=_extracted("convention", str, "global_median_1000"),
        value=_extracted("value", float, 1000.0),
    )
    assert inten.value.extraction.value == 1000.0
    assert inten.convention.extraction.value == "global_median_1000"
