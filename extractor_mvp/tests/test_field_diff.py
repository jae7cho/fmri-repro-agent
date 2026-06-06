"""Each FieldDiff classification, with synthetic per-acquisition extractions."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extractor_mvp.acquisition_discovery import AcquisitionDiscoveryResult
from extractor_mvp.field_diff import compute_field_diffs
from extractor_mvp.multi_acquisition_extractor import MultiAcquisitionResult


def _pf(extracted: bool, value: Any) -> Any:
    status = "EXTRACTED" if extracted else "MISSING_FROM_PAPER"
    return SimpleNamespace(extraction=SimpleNamespace(status=status, value=value))


def _prep(target_space_extracted: bool, target_space_value: Any) -> Any:
    """A stand-in Preprocessing exposing only the spatial_normalization.target_space
    field (the other diff fields resolve to Missing via the absent attr)."""
    spatial = SimpleNamespace(
        kind="spatial_normalization", target_space=_pf(target_space_extracted, target_space_value)
    )
    return SimpleNamespace(steps=[spatial])


def _result(extractions: dict[str, Any]) -> MultiAcquisitionResult:
    return MultiAcquisitionResult(
        discovery=AcquisitionDiscoveryResult(acquisitions=[]),
        extractions=extractions,
        diagnostics={},
    )


def _ts_class(extractions: dict[str, Any]) -> str:
    diffs = compute_field_diffs(_result(extractions))
    return next(d.classification for d in diffs if d.field_name == "target_space")


def test_fully_shared():
    r = _result({"a": _prep(True, "MNI152NLin6Asym"), "b": _prep(True, "MNI152NLin6Asym")})
    d = next(x for x in compute_field_diffs(r) if x.field_name == "target_space")
    assert d.classification == "fully_shared"
    assert d.shared_value == "MNI152NLin6Asym"
    assert d.extractable_count == 2


def test_acquisition_specific():
    assert _ts_class({"a": _prep(True, "MNI152NLin6Asym"), "b": _prep(True, "Talairach")}) == (
        "acquisition_specific"
    )


def test_partially_shared():
    assert _ts_class({"a": _prep(True, "Talairach"), "b": _prep(False, None)}) == "partially_shared"


def test_uniformly_missing():
    assert _ts_class({"a": _prep(False, None), "b": _prep(False, None)}) == "uniformly_missing"


def test_mixed_with_disagreement():
    extractions = {
        "a": _prep(True, "MNI152NLin6Asym"),
        "b": _prep(True, "MNI152NLin6Asym"),
        "c": _prep(True, "Talairach"),
    }
    assert _ts_class(extractions) == "mixed_with_disagreement"


def test_single_acquisition_fully_shared_trivially():
    d = next(
        x
        for x in compute_field_diffs(_result({"a": _prep(True, "Talairach")}))
        if x.field_name == "target_space"
    )
    assert d.classification == "fully_shared" and d.extractable_count == 1
