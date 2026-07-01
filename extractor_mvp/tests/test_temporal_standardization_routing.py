"""Build 2: temporal_standardization routing (OFFLINE — simulated LLM extractions).

Tests that GIVEN an LLM FieldExtractionResult, the temporal_standardization_method
field routes through _process_field (direct Literal validation — no synonym table,
since field_id "method" is not a SYNONYMS_BY_FIELD key) and lands in the assembled
Preprocessing as a temporal_standardization step. The step is ALWAYS emitted (like
the other MVP steps); whether its method carries a value is what varies.

The OBJECT discrimination (signal vs regressor/component/connectivity/feature) is an
LLM prompt judgment and is validated live in Build 3, NOT here — these tests take the
LLM's extraction as given.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract_preprocessing
from extractor_mvp.parsed_paper import ParsedPaper

# Liu 2013 phrasing — the verbatim quotes below are substrings of this text so span
# resolution succeeds.
TEXT = (
    "For each voxel, the fMRI signal was temporally normalized by subtracting its mean "
    "and then dividing by its temporal standard deviation. "
    "Functional intensity used grand-mean scaling to 10000."
)


def _fake_client(payload: PreprocessingExtraction) -> Any:
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: payload))
    )


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _ex(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _payload(**overrides: FieldExtractionResult) -> PreprocessingExtraction:
    base: dict[str, FieldExtractionResult] = {
        "target_space": _missing(),
        "resolution_mm": _missing(),
        "surface_registration": _missing(),
        "target_surface": _missing(),
        "intensity_convention": _missing(),
        "intensity_value": _missing(),
    }
    base.update(overrides)
    return PreprocessingExtraction(**base)


def _prep(payload: PreprocessingExtraction):
    prep, _diags, _defs = extract_preprocessing(
        ParsedPaper(text=TEXT, source="t", parser="manual"), "m", client=_fake_client(payload)
    )
    return prep


def _ts_step(prep: Any) -> Any:
    steps = [s for s in prep.steps if s.kind == "temporal_standardization"]
    assert len(steps) == 1, f"expected exactly one temporal_standardization step, got {len(steps)}"
    return steps[0]


_ZSCORE_QUOTE = (
    "the fMRI signal was temporally normalized by subtracting its mean and then "
    "dividing by its temporal standard deviation"
)


def test_zscore_signal_routes_to_temporal_standardization() -> None:
    prep = _prep(
        _payload(temporal_standardization_method=_ex("voxel_temporal_zscore", _ZSCORE_QUOTE))
    )
    ts = _ts_step(prep)
    assert ts.method.extraction.status == "EXTRACTED"
    assert ts.method.extraction.value == "voxel_temporal_zscore"


def test_other_method_accepted() -> None:
    prep = _prep(_payload(temporal_standardization_method=_ex("other", _ZSCORE_QUOTE)))
    ts = _ts_step(prep)
    assert ts.method.extraction.status == "EXTRACTED"
    assert ts.method.extraction.value == "other"


def test_step_always_emitted_with_missing_method_when_absent() -> None:
    # The step is present even when the field is missing; its method is MISSING.
    prep = _prep(_payload())  # temporal_standardization_method defaults to missing
    ts = _ts_step(prep)
    assert ts.method.extraction.status == "MISSING_FROM_PAPER"


def test_non_literal_method_value_demoted_to_missing() -> None:
    # Direct Literal validation (no synonym table): a value outside the Literal is
    # demoted to MISSING with a value_not_in_literal diagnostic.
    prep, diags, _ = extract_preprocessing(
        ParsedPaper(text=TEXT, source="t", parser="manual"),
        "m",
        client=_fake_client(
            _payload(temporal_standardization_method=_ex("min_max_scaled", _ZSCORE_QUOTE))
        ),
    )
    ts = _ts_step(prep)
    assert ts.method.extraction.status == "MISSING_FROM_PAPER"
    assert any(
        d.field == "temporal_standardization.method" and "value_not_in_literal" in d.failure_reason
        for d in diags
    )


def test_intensity_convention_no_longer_accepts_zscore() -> None:
    # End-to-end for §3b: z-score routed into the intensity convention is rejected
    # (voxel_temporal_zscore left IntensityNormalizationConvention in Build 1).
    prep = _prep(_payload(intensity_convention=_ex("voxel_temporal_zscore", _ZSCORE_QUOTE)))
    intensity = next(s for s in prep.steps if s.kind == "intensity_normalization")
    assert intensity.convention.extraction.status == "MISSING_FROM_PAPER"
