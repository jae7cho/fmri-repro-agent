"""One-hop citation resolver for DeferredToCitation fields.

Takes a list of deferral records from Pass 2, fetches the cited paper via
PaperFetcher, runs the same extraction logic on its preprocessing section,
and returns InferredDefault objects for successfully resolved fields.

Depth is capped at max_depth (default 1 -- MVP). Cycle detection via
seen_canonical_ids set passed through the call chain.

Return contract:
  resolve_all() -> dict[field, InferredDefault] | {}
  Empty dict if no deferrals resolved; caller (Configurator) emits
  LeftMissing for any field not in the returned dict.

  NOTE: keys are the deferral record's ``field`` attribute -- a dotted path like
  "spatial_normalization.target_space" (Part A's DeferralRecord names it ``field``,
  not ``field_name``). That dotted path is also the lookup key into the
  Preprocessing tree (``f"{step.kind}.{pf.field_id}"``), so _apply_resolved_citations
  can match resolved fields back without any renaming.

Confidence: min(source_confidence * CITATION_CONFIDENCE_PENALTY,
               BASIS_CEILINGS["prior_publication"])
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any

from fmri_repro.spec.preprocessing import Preprocessing
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    InferredDefault,
    PriorPublicationBasis,
)

from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.paper_fetcher import PaperFetcher
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text

logger = logging.getLogger(__name__)

CITATION_CONFIDENCE_PENALTY = 0.70

# extractor callable: takes a ParsedPaper, returns (Preprocessing, diagnostics, deferrals).
ExtractorCallable = Callable[[ParsedPaper], tuple[Preprocessing, list, list]]


def _iter_fields(preprocessing: Preprocessing) -> Iterator[tuple[str, Any]]:
    """Yield (dotted_path, ProvenancedField) for every real field (skips ``kind``)."""
    for step in preprocessing.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            yield f"{step.kind}.{pf.field_id}", pf


class CitationResolver:
    """Resolve DeferredToCitation fields one hop into their cited papers."""

    def __init__(
        self,
        extractor: ExtractorCallable,  # the single-acquisition extractor callable
        fetcher: PaperFetcher,
        max_depth: int = 1,
    ) -> None:
        self.extractor = extractor
        self.fetcher = fetcher
        self.max_depth = max_depth

    def resolve_all(
        self,
        deferral_records: list,  # deferral_records from extractor output
        depth: int = 0,
        seen_canonical_ids: set[str] | None = None,
    ) -> dict[str, InferredDefault[Any]]:
        """Resolve all deferred fields. Returns {field: InferredDefault}."""
        seen = set(seen_canonical_ids or set())
        resolved: dict[str, InferredDefault[Any]] = {}

        # One fetch per cited paper, not per field.
        by_ref: dict[str, list] = {}
        for rec in deferral_records:
            by_ref.setdefault(rec.ref_string, []).append(rec)

        for ref_string, recs in by_ref.items():
            canonical_id = self.fetcher.canonical_id_for(ref_string)
            if canonical_id is None:
                logger.warning("no canonical_id for ref %r; skipping", ref_string)
                continue
            if canonical_id in seen:
                logger.warning("cycle detected for %s; skipping", canonical_id)
                continue
            if depth >= self.max_depth:
                logger.warning(
                    "max_depth %d reached at depth %d; skipping %s",
                    self.max_depth,
                    depth,
                    canonical_id,
                )
                continue

            pdf_path = self.fetcher.resolve(ref_string)
            if pdf_path is None:
                logger.warning(
                    "could not fetch PDF for %s (%r); skipping", canonical_id, ref_string
                )
                continue

            seen.add(canonical_id)
            try:
                cited_prep = self._extract_cited(pdf_path, canonical_id)
            except Exception as exc:  # a bad cited PDF must not abort the whole resolution
                logger.warning("extraction on cited paper %s failed: %s", canonical_id, exc)
                continue

            wanted = {rec.field for rec in recs}
            for dotted, pf in _iter_fields(cited_prep):
                if dotted not in wanted or pf.extraction.status != "EXTRACTED":
                    continue
                source_conf = pf.extraction.confidence
                confidence = min(
                    source_conf * CITATION_CONFIDENCE_PENALTY,
                    BASIS_CEILINGS["prior_publication"],
                )
                resolved[dotted] = InferredDefault(
                    value=pf.extraction.value,
                    basis=PriorPublicationBasis(
                        citation=ref_string,
                        note=f"one-hop from cited paper; source_confidence={source_conf:.2f}",
                    ),
                    confidence=confidence,
                    alternative_inferences=[],
                )

        return resolved

    def resolve_base_pipeline_deferral(
        self,
        deferral_records: list,  # only field=="base_pipeline" records
        current_preprocessing: Preprocessing,
    ) -> dict[str, InferredDefault[Any]]:
        """Fallback path for unrecognized pipelines or version-uncertain KB lookups.

        Fetches the cited pipeline paper, runs full Layer-2 extraction, and returns
        an ``InferredDefault`` at ``PriorPublicationBasis`` (ceiling 0.60) for each
        step field that is currently ``LEFT_MISSING`` in ``current_preprocessing``.

        Uses the same compound-ref splitting (via PaperFetcher), cycle detection,
        and depth guard as :meth:`resolve_all`. Keys are step-field dotted paths
        (e.g. ``"spatial_normalization.target_space"``) so the result drops
        straight into :func:`_apply_resolved_citations`.
        """
        resolved: dict[str, InferredDefault[Any]] = {}
        # Only fields the extractor/Configurator left open are eligible to fill.
        missing_now = {
            dotted
            for dotted, pf in _iter_fields(current_preprocessing)
            if pf.inference.status == "LEFT_MISSING"
        }
        if not missing_now:
            return resolved

        depth = 0  # base-pipeline expansion is one-hop
        seen: set[str] = set()
        by_ref: dict[str, list] = {}
        for rec in deferral_records:
            by_ref.setdefault(rec.ref_string, []).append(rec)

        for ref_string in by_ref:
            canonical_id = self.fetcher.canonical_id_for(ref_string)
            if canonical_id is None:
                logger.warning("no canonical_id for base-pipeline ref %r; skipping", ref_string)
                continue
            if canonical_id in seen:
                logger.warning("cycle detected for %s; skipping", canonical_id)
                continue
            if depth >= self.max_depth:
                logger.warning("max_depth %d reached; skipping %s", self.max_depth, canonical_id)
                continue
            pdf_path = self.fetcher.resolve(ref_string)
            if pdf_path is None:
                logger.warning(
                    "could not fetch pipeline PDF for %s (%r); skipping", canonical_id, ref_string
                )
                continue
            seen.add(canonical_id)
            try:
                cited_prep = self._extract_cited(pdf_path, canonical_id)
            except Exception as exc:  # a bad cited PDF must not abort the whole resolution
                logger.warning(
                    "extraction on cited pipeline paper %s failed: %s", canonical_id, exc
                )
                continue

            for dotted, pf in _iter_fields(cited_prep):
                if dotted not in missing_now or pf.extraction.status != "EXTRACTED":
                    continue
                if dotted in resolved:
                    continue  # first cited source wins
                source_conf = pf.extraction.confidence
                confidence = min(
                    source_conf * CITATION_CONFIDENCE_PENALTY,
                    BASIS_CEILINGS["prior_publication"],
                )
                resolved[dotted] = InferredDefault(
                    value=pf.extraction.value,
                    basis=PriorPublicationBasis(
                        citation=ref_string,
                        note=f"one-hop base-pipeline expansion; source_confidence={source_conf:.2f}",
                    ),
                    confidence=confidence,
                    alternative_inferences=[],
                )

        return resolved

    def _extract_cited(self, pdf_path: Any, canonical_id: str) -> Preprocessing:
        """Load the cited PDF, slice its methods, run the extractor; return its Preprocessing."""
        text, _parser = load_pdf_text(pdf_path)
        methods = find_methods_section(text)
        cited_paper = ParsedPaper(text=methods.text, source=canonical_id, parser="pypdf")
        cited_prep, _diags, _deferrals = self.extractor(cited_paper)
        return cited_prep
