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

#: Base gap reasons meaning "the extractor LOOKED, found something, and could not verify it" — as
#: opposed to "looked and found nothing". Ruled 2026-10-01
#: (docs/design/DELTA_base_pipeline_diagnostic.md §4a): these make the Software row NOT covered, on
#: the same reasoning :func:`_software_coverage` already applies to ``NotApplicable`` below — the
#: tool cannot say what the paper reported, so silence is the honest output rather than an
#: unconditional accusation produced by a span resolver.
#:
#: Compared on the BASE (prefix before the first ``:``), so a suffixed reason carrying the
#: resolver's own failure_reason matches. Deliberately NOT a check on the condition: the reason is
#: read, never re-derived, which is the whole payoff of the diagnostic landing.
_UNVERIFIABLE_GAP_BASES = frozenset(
    {
        "extraction_quote_unresolved",
        "base_pipeline_value_unsupported",
        "deferral_quote_unresolved",
    }
)


def _gap_base(reason: str | None) -> str:
    """The base of a LeftMissing reason — the prefix before the first ``:``.

    Mirrors ``render._reason_base`` but takes the string, not a FieldRow: this module must not
    import render (render imports it), and the suffix convention is shared.
    """
    return (reason or "").split(":", 1)[0]


# ---------------------------------------------------------------------------
# Predicate
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RowCoverage:
    row: CobidasRow
    addressed: bool  # >=1 field on a mapped kind is EXTRACTED or DEFERRED_TO_CITATION
    covered_by_extractor: bool  # the extractor targets >=1 field on a mapped kind
    #: NOT covered because the extractor looked and could not VERIFY what it found — as distinct
    #: from never having targeted the row. Two different facts, and the coverage header must not
    #: collapse them (DELTA_base_pipeline_diagnostic.md §4a). Defaulted so the only construction
    #: site stays the only thing that has to know about it.
    unverifiable: bool = False


def _row_covered_by_extractor(field_rows: list[Any]) -> bool:  # list[render.FieldRow]
    """True iff the extractor targets any of these fields (a field is untargeted iff its
    LeftMissing reason is ``not_targeted_by_mvp``; extracted/deferred fields are targeted)."""
    return any(r.left_missing_reason != _UNTARGETED_REASON for r in field_rows)


def _software_coverage(
    base_row: Any, version_extraction_status: str | None
) -> tuple[bool, bool, bool]:
    """``(addressed, covered_by_extractor, unverifiable)`` for the unconditional Software row.

    The Software row maps to ``base_pipeline`` rather than a step kind, so it cannot use
    :func:`_row_covered_by_extractor`. It must still obey the SAME rule as the other 15 rows:
    a field the extractor targeted and found nothing for is COVERED, and renders as a claim
    about the paper; a field it never targeted is not.

    **addressed — did the PAPER answer the software question?**
    When a ``base_pipeline.version`` row exists (the outer arm resolved a ``PipelineRef``),
    the version's own extraction status answers it. When no version row exists, only an
    ``EXTRACTED`` base_pipeline answers it. These are two genuinely different questions; do
    NOT collapse them.

    ``DEFERRED_TO_CITATION`` does NOT address this row, and that SUPERSEDES the repair made
    in ``c9c2951`` without disturbing its diagnosis. That commit correctly found the report
    accusing a citing paper of an unconditional COBIDAS violation, and repaired it by making
    the row addressed. The false part was the accusation's wording, not the finding: COBIDAS
    §4.3 attaches no deferral clause to the version requirement, and the only citation-like
    mechanism it raises there (the RRID) is additive. This row's mandatory content is version
    and revision number; a deferring paper answers pipeline identity, not version. The row is
    unaddressed and the line beneath the heading says identity was deferred to the citation.
    See ``docs/design/DELTA_software_row_deferral.md``.

    Scoped to THIS branch. :data:`_ADDRESSING_STATUSES` is also read by the per-row rule in
    :func:`assess_coverage`, where a deferral remains a report per CALL 1, and must not be
    narrowed there.

    **covered — did the EXTRACTOR look?**
    True whenever a ``base_pipeline`` row exists with a targeted reason. ``base_pipeline`` is
    always targeted (``_build_base_pipeline`` runs on every paper), so the untargeted case is
    UNREACHABLE today; its branch below exists only so the rule reads completely, and it is
    pinned as row E in ``test_software_coverage_over_every_base_pipeline_state``.

    The one False case is ``NotApplicable``, and it is deliberate, not an oversight: do not
    "fix" it into a violation. ``NotApplicable`` has TWO producers meaning opposite things —
    a genuine from-scratch pipeline (render.flatten's reading) and
    ``fmri_repro.kb_client.base_pipeline`` (a pipeline the paper DID name that ``recognize()``
    did not know, with an uncertain outer extraction). The value cannot distinguish them, so
    the tool cannot tell what the paper said, and silence is the honest output. Deciding
    otherwise would encode a coin-flip into an accusation against an author. Disambiguating
    the two producers is filed as deferred work.
    """
    if base_row is None or base_row.extraction_status is None:
        return False, False, False  # NotApplicable (or no base_pipeline row at all)
    if base_row.left_missing_reason == _UNTARGETED_REASON:
        return False, False, False  # unreachable today; kept so the rule reads completely
    if version_extraction_status is not None:
        # The VERSION arm. Untouched by the 2026-10-01 ruling: a version row exists only when the
        # outer arm resolved a PipelineRef, so base_pipeline is EXTRACTED and carries no gap reason.
        # _build_version_pf collapses four conditions of its own onto version_deferred_to_kb and is
        # the LARGER half of this defect — DELTA_base_pipeline_diagnostic.md §10, its own commit.
        return version_extraction_status == "EXTRACTED", True, False
    if _gap_base(base_row.left_missing_reason) in _UNVERIFIABLE_GAP_BASES:
        # The extractor looked, found something, and could not verify it. Not addressed, and NOT
        # covered: claiming an unconditional COBIDAS violation here would accuse an author on the
        # strength of a span resolver failing. Silence, for the same reason NotApplicable is silent.
        return False, False, True
    return base_row.extraction_status == "EXTRACTED", True, False


def assess_coverage(rows: list[Any], version_extraction_status: str | None) -> list[RowCoverage]:
    """Assess every D.3 row from flattened ``FieldRow`` rows + the base_pipeline.version
    extraction status. Extraction arm ONLY — an INFERRED_DEFAULT value is not a *report*.

    ``rows`` is the output of ``render.flatten(preprocessing)``. ``version_extraction_status``
    is the extraction status of the ``base_pipeline.version`` row (None if no version row).
    """
    by_kind: dict[str, list[Any]] = {}
    for r in rows:
        by_kind.setdefault(r.group, []).append(r)

    base_row = next(
        (r for r in by_kind.get("base_pipeline", []) if r.path == "base_pipeline"), None
    )

    out: list[RowCoverage] = []
    for cr in COBIDAS_D3_ROWS:
        if cr.row_id == "software":
            addressed, covered, unverifiable = _software_coverage(
                base_row, version_extraction_status
            )
        else:
            mapped = [r for k in cr.spec_kinds for r in by_kind.get(k, [])]
            addressed = any(r.extraction_status in _ADDRESSING_STATUSES for r in mapped)
            covered = _row_covered_by_extractor(mapped)
            # Only the Software row can be unverifiable today: every other row's coverage is pure
            # targeting (_row_covered_by_extractor), which is a code property, not a per-paper one.
            unverifiable = False
        out.append(
            RowCoverage(
                row=cr,
                addressed=addressed,
                covered_by_extractor=covered,
                unverifiable=unverifiable,
            )
        )
    return out
