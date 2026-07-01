"""CitationResolver: cycle detection + coupling integrity (offline) and a live
one-hop Cho 2021 -> Glasser 2013 resolution (marked ``live``)."""

from __future__ import annotations

import logging
import os
from datetime import date
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fmri_repro.spec.provenance import InferredDefault, PriorPublicationBasis

from extractor_mvp.citation_resolver import (
    CITATION_CONFIDENCE_PENALTY,
    CitationResolver,
    _iter_fields,
)
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    DeferralRecord,
    PreprocessingExtraction,
    _apply_resolved_citations,
    extract,
    extract_preprocessing,
)
from extractor_mvp.paper_fetcher import PaperFetcher
from extractor_mvp.parsed_paper import ParsedPaper

_INDEX = """\
glasser_2013:
  canonical_id: glasser_2013
  aliases:
    - "glasser et al. 2013"
    - "glasser 2013"
  local_pdf: citation_cache/glasser_2013.pdf
  source: local
  verified: true
"""

CACHE_DIR = Path(__file__).resolve().parents[1] / "citation_cache"


def _tmp_cache(tmp_path: Path) -> Path:
    cache = tmp_path / "citation_cache"
    cache.mkdir()
    (cache / "index.yaml").write_text(_INDEX, encoding="utf-8")
    (cache / "glasser_2013.pdf").write_bytes(b"%PDF-1.4 dummy")
    return cache


def _rec(field: str, ref: str = "Glasser et al. 2013") -> DeferralRecord:
    return DeferralRecord(
        field=field,
        ref_string=ref,
        target_kind="paper",
        deferral_sentence="Preprocessing followed Glasser et al. (2013).",
    )


def _fake_client(payload: PreprocessingExtraction) -> Any:
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: payload))
    )


# --- 6d: cycle detection -------------------------------------------------------
def test_cycle_detection_skips_and_returns_empty(tmp_path: Path, caplog):
    calls = {"n": 0}

    def mock_extractor(_pp: ParsedPaper) -> tuple:
        calls["n"] += 1
        raise AssertionError("extractor must not be called when the cite is a cycle")

    resolver = CitationResolver(mock_extractor, PaperFetcher(_tmp_cache(tmp_path)))
    with caplog.at_level(logging.WARNING):
        out = resolver.resolve_all(
            [_rec("spatial_normalization.target_space")],
            seen_canonical_ids={"glasser_2013"},
        )
    assert out == {}
    assert calls["n"] == 0
    assert "cycle detected" in caplog.text


def test_max_depth_reached_returns_empty(tmp_path: Path, caplog):
    resolver = CitationResolver(
        lambda _pp: (_ for _ in ()).throw(AssertionError("not called")),
        PaperFetcher(_tmp_cache(tmp_path)),
        max_depth=1,
    )
    with caplog.at_level(logging.WARNING):
        out = resolver.resolve_all([_rec("spatial_normalization.target_space")], depth=1)
    assert out == {}
    assert "max_depth" in caplog.text


def test_unknown_ref_skipped(tmp_path: Path, caplog):
    resolver = CitationResolver(
        lambda _pp: (_ for _ in ()).throw(AssertionError("not called")),
        PaperFetcher(_tmp_cache(tmp_path)),
    )
    with caplog.at_level(logging.WARNING):
        out = resolver.resolve_all([_rec("x.y", ref="Nobody et al. 1999")])
    assert out == {}


# --- 6e: _apply_resolved_citations coupling integrity --------------------------
def _deferred_prep() -> Any:
    """A real Preprocessing whose spatial_normalization.target_space is DEFERRED."""
    text = "Preprocessing followed Glasser et al. (2013). Normalized to MNI152NLin6Asym."
    missing = FieldExtractionResult(status="missing")
    payload = PreprocessingExtraction(
        target_space=FieldExtractionResult(
            status="deferred",
            deferral_sentence="Preprocessing followed Glasser et al. (2013).",
            ref_string="Glasser et al. 2013",
        ),
        resolution_mm=missing,
        surface_registration=missing,
        target_surface=missing,
        intensity_convention=missing,
        intensity_value=missing,
    )
    prep, _diags, _defs = extract_preprocessing(
        ParsedPaper(text=text, source="t", parser="manual"), "m", client=_fake_client(payload)
    )
    return prep


def _find(prep: Any, dotted: str) -> Any:
    for step in prep.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            if f"{step.kind}.{pf.field_id}" == dotted:
                return pf
    raise AssertionError(f"no field {dotted}")


def test_apply_resolved_citations_upgrades_inference_only():
    prep = _deferred_prep()
    before = _find(prep, "spatial_normalization.target_space")
    assert before.extraction.status == "DEFERRED_TO_CITATION"
    assert before.inference.status == "LEFT_MISSING"

    resolved = {
        "spatial_normalization.target_space": InferredDefault(
            value="MNI152NLin6Asym",
            basis=PriorPublicationBasis(citation="Glasser et al. 2013", note="one-hop"),
            confidence=0.5,
            alternative_inferences=[],
        )
    }
    new_prep = _apply_resolved_citations(prep, resolved)  # must not raise (coupling valid)
    after = _find(new_prep, "spatial_normalization.target_space")
    # extraction arm unchanged; inference arm upgraded
    assert after.extraction.status == "DEFERRED_TO_CITATION"
    assert after.inference.status == "INFERRED_DEFAULT"
    assert after.inference.basis.basis_type == "prior_publication"
    assert after.inference.value == "MNI152NLin6Asym"
    # original object not mutated
    assert before.inference.status == "LEFT_MISSING"


def test_apply_resolved_citations_noop_on_empty():
    prep = _deferred_prep()
    assert _apply_resolved_citations(prep, {}) is prep


# --- 7d: live Cho 2021 base-pipeline citation fallback (via extract() routing) --
MODEL = os.environ.get("EXTRACTOR_MODEL", "bedrock/us.anthropic.claude-sonnet-4-6")
# The repo's purpose-built Cho-2021 HCP methods section. We use this (not the raw
# Cho_2021.pdf) because the full-PDF auto-slice (~22 KB) dilutes deferral detection:
# the LLM extracts/misses fields on the large slice instead of deferring, even though
# the deferral sentence IS present. On this focused section the LLM reliably defers
# preprocessing to "Marcus et al., 2013; Glasser et al., 2013". The full-PDF
# deferral-recall gap is a Pass-2/methods-finder limitation, outside Part B's scope.
CHO_SECTION = Path(__file__).resolve().parents[1] / "examples" / "cho_2021_hcp_section.txt"


@pytest.mark.live
def test_cho_2021_base_pipeline_citation_fallback():
    """Cho defers its base pipeline (HCP) to Glasser/Marcus. Via extract() routing
    with paper_date set: the KB path runs first, but HCP is multi-version (no
    default_version) -> resolves date_inferred -> fill_dependent_defaults no-ops; the
    citation fallback then fetches Glasser and fills the step fields at
    PriorPublicationBasis (confidence <= 0.60).

    Reframed from the Part B per-field resolver test (was xfail because Cho's deferral
    is base-pipeline-level, not per-field; now routed through
    CitationResolver.resolve_base_pipeline_deferral via extract()).
    """
    assert CHO_SECTION.is_file(), f"missing fixture: {CHO_SECTION}"
    assert CACHE_DIR.is_dir(), f"missing citation cache: {CACHE_DIR}"

    paper = ParsedPaper(
        text=CHO_SECTION.read_text(encoding="utf-8"), source="cho_2021", parser="manual"
    )
    fetcher = PaperFetcher(CACHE_DIR)
    resolver = CitationResolver(partial(extract_preprocessing, model=MODEL), fetcher)
    prep, _diags, _deferrals = extract(
        paper, MODEL, citation_resolver=resolver, paper_date=date(2021, 1, 1)
    )

    pp_fields = [
        (dotted, pf)
        for dotted, pf in _iter_fields(prep)
        if pf.inference.status == "INFERRED_DEFAULT"
        and pf.inference.basis.basis_type == "prior_publication"
    ]
    assert pp_fields, "expected >=1 step field filled via base-pipeline citation fallback"
    for _dotted, pf in pp_fields:
        assert pf.inference.confidence <= 0.60
    # penalty applied (source 0.8 * 0.70 = 0.56)
    assert any(
        pf.inference.confidence <= 0.8 * CITATION_CONFIDENCE_PENALTY + 1e-9 for _, pf in pp_fields
    )
