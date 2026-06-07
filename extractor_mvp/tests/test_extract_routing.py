"""extract() base-pipeline routing (offline): KB path, citation fallback, and the
_any_step_fields_left_missing gate. The KB helpers and CitationResolver are mocked,
so these test the *routing*, not real KB resolution or live extraction."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

import fmri_repro.kb_client.base_pipeline as kb_mod
from fmri_repro.spec.provenance import (
    InferredDefault,
    PriorPublicationBasis,
    VersionDefaultBasis,
)

from extractor_mvp.citation_resolver import CitationResolver, _iter_fields
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    _any_step_fields_left_missing,
    _apply_resolved_citations,
    extract,
    extract_preprocessing,
)
from extractor_mvp.parsed_paper import ParsedPaper

# Names the base-pipeline name + the deferral sentence both appear verbatim here.
TEXT = (
    "Data were processed with the HCP minimal preprocessing pipeline. "
    "Preprocessing followed Glasser et al. (2013)."
)
# Resolvable Layer-2 content (for the 7c extracted states).
TEXT_FULL = (
    "Data were normalized to MNI152NLin6Asym space at 2 mm isotropic resolution. "
    "Cortical surfaces were registered with MSMSulc onto the fsLR_32k atlas. "
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


def _base_pipeline_deferred_payload() -> PreprocessingExtraction:
    """Extracted pipeline name + deferred ref -> base_pipeline EXTRACTED + one
    base_pipeline DeferralRecord; all six step fields missing."""
    return PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
        base_pipeline_name=_ex(
            "HCP minimal preprocessing pipeline",
            "Data were processed with the HCP minimal preprocessing pipeline.",
        ),
        base_pipeline_ref=FieldExtractionResult(
            status="deferred",
            deferral_sentence="Preprocessing followed Glasser et al. (2013).",
            ref_string="Glasser et al. 2013",
        ),
    )


def _paper(text: str = TEXT) -> ParsedPaper:
    return ParsedPaper(text=text, source="t", parser="manual")


def _ts_inferred(prep: Any, basis: Any, conf: float) -> Any:
    """Upgrade spatial_normalization.target_space to InferredDefault(basis)."""
    return _apply_resolved_citations(
        prep,
        {
            "spatial_normalization.target_space": InferredDefault(
                value="MNI152NLin6Asym", basis=basis, confidence=conf, alternative_inferences=[]
            )
        },
    )


def _bases(prep: Any) -> list[str]:
    return [
        pf.inference.basis.basis_type
        for _, pf in _iter_fields(prep)
        if pf.inference.status == "INFERRED_DEFAULT"
    ]


class _StubResolver(CitationResolver):
    """CitationResolver subclass with the two resolve methods stubbed (no fetch)."""

    def __init__(self, base_pipeline_ret: dict) -> None:
        self._ret = base_pipeline_ret
        self.bp_calls = 0

    def resolve_all(self, deferral_records, depth=0, seen_canonical_ids=None):
        return {}

    def resolve_base_pipeline_deferral(self, deferral_records, current_preprocessing):
        self.bp_calls += 1
        return self._ret


# --- 7a: KB path fills version_default -----------------------------------------
def test_kb_path_fills_version_default(monkeypatch):
    calls = {"fill": 0}

    def mock_fill(prep, paper_date):
        calls["fill"] += 1
        return _ts_inferred(prep, VersionDefaultBasis(tool="hcp_minimal", version="v3.4.0"), 0.9)

    monkeypatch.setattr(kb_mod, "infer_base_pipeline_version", lambda prep, pd: prep)
    monkeypatch.setattr(kb_mod, "fill_dependent_defaults", mock_fill)

    prep, _d, _r = extract(
        _paper(),
        "m",
        client=_fake_client(_base_pipeline_deferred_payload()),
        paper_date=date(2021, 1, 1),
    )
    assert calls["fill"] == 1
    assert "version_default" in _bases(prep)


# --- 7b: citation fallback when KB returns nothing ------------------------------
def test_citation_fallback_when_kb_unchanged(monkeypatch):
    calls = {"fill": 0}

    def mock_fill(prep, paper_date):  # KB recognized nothing -> returns unchanged
        calls["fill"] += 1
        return prep

    monkeypatch.setattr(kb_mod, "infer_base_pipeline_version", lambda prep, pd: prep)
    monkeypatch.setattr(kb_mod, "fill_dependent_defaults", mock_fill)

    resolver = _StubResolver(
        {
            "spatial_normalization.target_space": InferredDefault(
                value="MNI152NLin6Asym",
                basis=PriorPublicationBasis(citation="Glasser et al. 2013", note="x"),
                confidence=0.56,
                alternative_inferences=[],
            )
        }
    )

    prep, _d, _r = extract(
        _paper(),
        "m",
        client=_fake_client(_base_pipeline_deferred_payload()),
        citation_resolver=resolver,
        paper_date=date(2021, 1, 1),
    )
    assert calls["fill"] == 1  # KB path tried first
    assert resolver.bp_calls == 1  # then citation fallback
    assert "prior_publication" in _bases(prep)


# --- 7c: _any_step_fields_left_missing -----------------------------------------
def _prep_from(payload: PreprocessingExtraction, text: str = TEXT_FULL) -> Any:
    prep, _d, _r = extract_preprocessing(_paper(text), "m", client=_fake_client(payload))
    return prep


def test_any_step_fields_left_missing_all_missing():
    payload = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    assert _any_step_fields_left_missing(_prep_from(payload)) is True


def test_any_step_fields_left_missing_one_extracted_still_true():
    payload = PreprocessingExtraction(
        target_space=_ex("MNI152NLin6Asym", "normalized to MNI152NLin6Asym"),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    assert _any_step_fields_left_missing(_prep_from(payload)) is True


def test_any_step_fields_left_missing_all_extracted_false():
    payload = PreprocessingExtraction(
        target_space=_ex("MNI152NLin6Asym", "normalized to MNI152NLin6Asym"),
        resolution_mm=_ex("2", "at 2 mm"),
        surface_registration=_ex("msm_sulc", "registered with MSMSulc"),
        target_surface=_ex("fsLR_32k", "fsLR_32k atlas"),
        intensity_convention=_ex("fsl_grand_mean_10000", "grand-mean scaling to 10000"),
        intensity_value=_ex("10000", "scaling to 10000"),
    )
    assert _any_step_fields_left_missing(_prep_from(payload)) is False
