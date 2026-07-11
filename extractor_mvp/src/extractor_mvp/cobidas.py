"""COBIDAS D.3 (Preprocessing) coverage registry + predicate — emitter-side, pure.

Grounds the ``not covered by extractor`` figure in the actual standard: COBIDAS Report
v1.0 (2016-05-19), Table D.3 "Preprocessing Reporting" (pp. 53-58), transcribed verbatim.

Two facts from the source drive the design:

1. ``Mandatory = Y`` means "reporting is mandatory *if the step was performed*." Almost
   every row is phrased conditionally ("If performed, report:", "if not already performed
   by scanner", "Use of any ...") or with a bare "Report:". Silence on a conditional row is
   therefore NOT a COBIDAS violation — the standard cannot distinguish "didn't do it" from
   "did it, didn't say." So we claim non-compliance ONLY where the language is unconditional.
2. Exactly one row is unconditional: **Software** — "For each software used, be sure to
   include version and revision number." (Software *citation* / URL / RRID is ``N``.)

This module never touches ``_assemble`` or the schema. Step *presence* in ``_assemble`` is a
hardcoded 7-step list carrying no information; coverage is computed here, over the standard,
from extraction-arm state only.
"""

from __future__ import annotations

import dataclasses
from typing import Any

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CobidasRow:
    """One COBIDAS D.3 preprocessing row.

    ``spec_kinds`` are the ReplicationSpec ``PreprocStep`` *kind* values (NOT the
    ``cobidas_row`` ClassVars, which are not 1:1 with D.3) whose extraction-arm state
    determines whether this row is addressed. The ``software`` row is special: it maps to
    ``base_pipeline.version`` rather than a step kind, so its ``spec_kinds`` is empty.
    """

    row_id: str
    d3_aspect: str  # verbatim D.3 aspect title
    mandatory: bool
    unconditional: bool  # True only when D.3's language is an unconditional obligation
    spec_kinds: tuple[str, ...]


#: The 16 D.3 rows in scope for an fMRI-preprocessing protocol, in D.3 order.
#: 14 mandatory; ``software`` is the only unconditional row.
COBIDAS_D3_ROWS: tuple[CobidasRow, ...] = (
    CobidasRow("software", "Software", True, True, ()),
    CobidasRow("software_citation", "Software citation", False, False, ()),
    CobidasRow("t1_stabilization", "T1 stabilization", True, False, ("nonsteadystate_removal",)),
    CobidasRow("brain_extraction", "Brain extraction", True, False, ("brain_extraction",)),
    CobidasRow("segmentation", "Segmentation", True, False, ("segmentation",)),
    CobidasRow(
        "slice_time_correction", "Slice time correction", True, False, ("slice_time_correction",)
    ),
    CobidasRow("motion_correction", "Motion correction", True, False, ("motion_correction",)),
    CobidasRow(
        "gradient_distortion_correction",
        "Gradient distortion correction",
        True,
        False,
        ("distortion_correction",),
    ),
    CobidasRow(
        "distortion_correction", "Distortion correction", True, False, ("distortion_correction",)
    ),
    CobidasRow(
        "coregistration",
        "Function-structure (intra-subject) coregistration",
        True,
        False,
        ("coregistration",),
    ),
    CobidasRow(
        "intersubject_registration",
        "Intersubject registration",
        True,
        False,
        ("spatial_normalization", "surface_projection"),
    ),
    CobidasRow(
        "intensity_correction", "Intensity correction", True, False, ("intensity_correction",)
    ),
    CobidasRow(
        "intensity_normalization",
        "Intensity normalization",
        False,
        False,
        ("intensity_normalization",),
    ),
    CobidasRow(
        "artifact_structured_noise_removal",
        "Artifact and structured noise removal",
        True,
        False,
        ("ica_denoise", "compcor", "nuisance_regression"),
    ),
    CobidasRow("volume_censoring", "Volume censoring", True, False, ("despike", "scrub")),
    CobidasRow("spatial_smoothing", "Spatial smoothing", True, False, ("spatial_smoothing",)),
)

#: AESPA step kinds with no D.3 row; never counted in the coverage denominator.
DIVERGENCE_KINDS: tuple[str, ...] = ("temporal_filtering", "temporal_standardization")

#: D.3 rows deliberately out of scope for a *preprocessing* protocol. Recorded, not hidden.
EXCLUDED_D3_ROWS: tuple[str, ...] = (
    "Diffusion: Distortion correction",
    "Diffusion: Eddy current correction",
    "Diffusion: Motion correction",
    "Diffusion: Gradient direction reorientation",
    "Perfusion: Motion correction",
    "Perfusion: Label/control subtraction",
    "Resting state fMRI feature",
    "Quality control reports",
)

_ADDRESSING_STATUSES = frozenset({"EXTRACTED", "DEFERRED_TO_CITATION"})
_UNTARGETED_REASON = "not_targeted_by_mvp"


# ---------------------------------------------------------------------------
# Predicate
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RowCoverage:
    row: CobidasRow
    addressed: bool  # >=1 field on a mapped kind is EXTRACTED or DEFERRED_TO_CITATION
    covered_by_extractor: bool  # the extractor targets >=1 field on a mapped kind


def _row_covered_by_extractor(field_rows: list[Any]) -> bool:  # list[render.FieldRow]
    """True iff the extractor targets any of these fields (a field is untargeted iff its
    LeftMissing reason is ``not_targeted_by_mvp``; extracted/deferred fields are targeted)."""
    return any(r.left_missing_reason != _UNTARGETED_REASON for r in field_rows)


def assess_coverage(rows: list[Any], version_extraction_status: str | None) -> list[RowCoverage]:
    """Assess every D.3 row from flattened ``FieldRow`` rows + the base_pipeline.version
    extraction status. Extraction arm ONLY — an INFERRED_DEFAULT value is not a *report*.

    ``rows`` is the output of ``render.flatten(preprocessing)``. ``version_extraction_status``
    is the extraction status of the ``base_pipeline.version`` row (None if no version row).
    """
    by_kind: dict[str, list[Any]] = {}
    for r in rows:
        by_kind.setdefault(r.group, []).append(r)

    out: list[RowCoverage] = []
    for cr in COBIDAS_D3_ROWS:
        if cr.row_id == "software":
            addressed = version_extraction_status == "EXTRACTED"
            covered = version_extraction_status is not None  # the extractor targets version
        else:
            mapped = [r for k in cr.spec_kinds for r in by_kind.get(k, [])]
            addressed = any(r.extraction_status in _ADDRESSING_STATUSES for r in mapped)
            covered = _row_covered_by_extractor(mapped)
        out.append(RowCoverage(row=cr, addressed=addressed, covered_by_extractor=covered))
    return out
