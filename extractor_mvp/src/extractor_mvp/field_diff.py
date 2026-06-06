"""F2 diff: classify each preprocessing field as shared vs acquisition-specific.

Pure Python — no LLM calls. Informational only: it does NOT modify the
extraction result; the per-acquisition redundant extractions stay intact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from extractor_mvp.multi_acquisition_extractor import MultiAcquisitionResult

DiffClass = Literal[
    "fully_shared",  # all acquisitions Extracted, identical values
    "partially_shared",  # some Extracted (same), others MissingFromPaper
    "acquisition_specific",  # all Extracted, differing values
    "uniformly_missing",  # all MissingFromPaper
    "mixed_with_disagreement",  # some Extracted agree, some Extracted differ (+ maybe missing)
]

# (step kind, bare field attr, display name) for the 6 targeted preprocessing fields.
_DIFF_FIELDS: list[tuple[str, str, str]] = [
    ("spatial_normalization", "target_space", "target_space"),
    ("spatial_normalization", "resolution_mm", "resolution_mm"),
    ("surface_projection", "surface_registration", "surface_registration"),
    ("surface_projection", "target_surface", "target_surface"),
    ("intensity_normalization", "convention", "intensity_convention"),
    ("intensity_normalization", "value", "intensity_value"),
]


@dataclass(frozen=True)
class FieldDiff:
    field_name: str
    values_per_acquisition: dict[str, str]  # acq_id -> serialized value summary
    classification: DiffClass
    shared_value: object | None  # populated iff classification == "fully_shared"
    extractable_count: int  # how many acquisitions Extracted this field


def _field_value(preprocessing: Any, kind: str, attr: str) -> tuple[bool, Any]:
    """Return (is_extracted, value). value is the Extracted value or None."""
    for step in preprocessing.steps:
        if getattr(step, "kind", None) == kind:
            pf = getattr(step, attr, None)
            extraction = getattr(pf, "extraction", None)
            if extraction is not None and extraction.status == "EXTRACTED":
                return True, extraction.value
            return False, None
    return False, None


def _classify(extracted: dict[str, Any], n_acq: int) -> tuple[DiffClass, object | None]:
    if not extracted:
        return "uniformly_missing", None
    values = list(extracted.values())
    distinct = {repr(v) for v in values}
    missing = n_acq - len(extracted)
    if len(distinct) == 1:  # extracted values all agree
        return ("fully_shared", values[0]) if missing == 0 else ("partially_shared", None)
    # extracted values disagree (>1 distinct)
    has_repeat = len(values) != len(distinct)  # some agree AND some differ
    return ("mixed_with_disagreement", None) if has_repeat else ("acquisition_specific", None)


def compute_field_diffs(result: MultiAcquisitionResult) -> list[FieldDiff]:
    """Classify each preprocessing field across the acquisitions that extracted."""
    acq_ids = list(result.extractions.keys())
    n_acq = len(acq_ids)
    diffs: list[FieldDiff] = []
    for kind, attr, name in _DIFF_FIELDS:
        extracted: dict[str, Any] = {}
        summary: dict[str, str] = {}
        for acq_id in acq_ids:
            is_ext, value = _field_value(result.extractions[acq_id], kind, attr)
            if is_ext:
                extracted[acq_id] = value
                summary[acq_id] = f"Extracted={value!r}"
            else:
                summary[acq_id] = "Missing"
        classification, shared = _classify(extracted, n_acq)
        diffs.append(
            FieldDiff(
                field_name=name,
                values_per_acquisition=summary,
                classification=classification,
                shared_value=shared,
                extractable_count=len(extracted),
            )
        )
    return diffs
