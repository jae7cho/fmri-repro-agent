"""temporal_filtering.pass_type (schema 0.6.3, fix 5 of the author's list of 2026-11-05). The six
stress papers the checking pass said filter_type missed all named a pass type, which filter_type
(the filter's design) has no member for. Offline: the stub client answers call T."""

from __future__ import annotations

from typing import Any

from conftest import stub_client
from extractor_mvp.coverage_extractor import TEMPORAL_VOLUME_PROMPT, TemporalVolumeExtraction
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.render import to_report

TEXT = (
    "The data were band-pass filtered between 0.01 and 0.1 Hz with a Butterworth filter. "
    "Nothing else was done to the time series."
)
SENT = "The data were band-pass filtered between 0.01 and 0.1 Hz with a Butterworth filter."


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _run(**temporal: Any) -> Any:
    shared = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    prep, _, _ = extract(
        ParsedPaper(text=TEXT, source="t", parser="manual"),
        "m",
        client=stub_client(shared, temporal=TemporalVolumeExtraction(**temporal)),
    )
    return next(s for s in prep.steps if s.kind == "temporal_filtering")


def test_call_t_asks_the_pass_type_apart_from_the_filter_design() -> None:
    assert "filter_pass_type: the band's shape: canonical high_pass, low_pass, band_pass" in (
        TEMPORAL_VOLUME_PROMPT
    )
    assert "filter_type: the filter's design, not its band's shape" in TEMPORAL_VOLUME_PROMPT
    assert "filter_pass_type" in TemporalVolumeExtraction.model_fields


def test_the_paper_s_words_resolve_to_the_pass_type_and_the_design_stays_apart() -> None:
    tf = _run(
        filter_pass_type=FieldExtractionResult(
            status="extracted", value="band-pass", verbatim_quote=SENT
        ),
        filter_type=FieldExtractionResult(
            status="extracted", value="Butterworth", verbatim_quote=SENT
        ),
    )
    assert tf.pass_type.extraction.status == "EXTRACTED"
    assert tf.pass_type.extraction.value.resolved == "band_pass"
    assert tf.filter_type.extraction.value.resolved == "butterworth"


def test_the_report_shows_the_pass_type() -> None:
    shared = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    temporal = TemporalVolumeExtraction(
        filter_pass_type=FieldExtractionResult(
            status="extracted", value="band-pass", verbatim_quote=SENT
        )
    )
    prep, _, _ = extract(
        ParsedPaper(text=TEXT, source="t", parser="manual"),
        "m",
        client=stub_client(shared, temporal=temporal),
    )
    out = to_report(prep, source="t")
    assert '- pass_type = band_pass (paper: "band-pass")   [from paper]' in out
