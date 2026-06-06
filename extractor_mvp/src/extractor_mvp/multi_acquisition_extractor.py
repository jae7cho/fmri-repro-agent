"""Fork C orchestration: two-pass multi-acquisition extraction.

Pass 1 (one LLM call) discovers acquisitions; Pass 2 (N LLM calls) extracts
preprocessing scoped to each. Output is ``Map[acquisition_id, Preprocessing]``;
shared-vs-specific fields are detected post-hoc by :mod:`field_diff` (F2 =
redundant extraction + Python diff — the LLM never makes partitioning calls).
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from fmri_repro.spec.preprocessing import Preprocessing

from extractor_mvp.acquisition_discovery import (
    AcquisitionDiscoveryResult,
    discover_acquisitions,
)
from extractor_mvp.extractor import (
    ExtractionDiagnostic,
    _apply_resolved_citations,
    build_client,
    extract_preprocessing_for_acquisition,
)
from extractor_mvp.parsed_paper import ParsedPaper

if TYPE_CHECKING:
    from extractor_mvp.citation_resolver import CitationResolver


@dataclasses.dataclass(frozen=True)
class MultiAcquisitionResult:
    discovery: AcquisitionDiscoveryResult
    extractions: dict[str, Preprocessing]  # keyed by acquisition_id
    diagnostics: dict[str, list[ExtractionDiagnostic]]  # keyed by acquisition_id


def extract_multi_acquisition(
    parsed_paper: ParsedPaper,
    model: str,
    *,
    client: Any | None = None,
    citation_resolver: CitationResolver | None = None,
) -> MultiAcquisitionResult:
    """Two-pass extraction. Single-acquisition papers naturally produce N=1.

    A Pass-2 failure for one acquisition is recorded as a diagnostic and the
    remaining acquisitions still run (the whole paper is not aborted).

    If a ``citation_resolver`` is supplied, each acquisition's DEFERRED_TO_CITATION
    fields are resolved one hop and their inference arm upgraded in place of the run
    (LeftMissing -> InferredDefault), mirroring the single-pass :func:`extract`.
    """
    client = client or build_client()
    discovery = discover_acquisitions(parsed_paper, model, client=client)

    extractions: dict[str, Preprocessing] = {}
    diagnostics: dict[str, list[ExtractionDiagnostic]] = {}
    for acq in discovery.acquisitions:
        try:
            prep, diags, deferrals = extract_preprocessing_for_acquisition(
                parsed_paper, acq.paper_name, acq.characterizing_quote, model, client=client
            )
            if citation_resolver is not None and deferrals:
                resolved = citation_resolver.resolve_all(deferrals)
                prep = _apply_resolved_citations(prep, resolved)
            extractions[acq.acquisition_id] = prep
            diagnostics[acq.acquisition_id] = diags
        except Exception as exc:  # one acquisition failing must not abort the paper
            diagnostics[acq.acquisition_id] = [
                ExtractionDiagnostic(
                    f"acquisition:{acq.acquisition_id}",
                    f"pass2_failed:{type(exc).__name__}",
                    None,
                    None,
                )
            ]

    return MultiAcquisitionResult(
        discovery=discovery, extractions=extractions, diagnostics=diagnostics
    )
