"""The checking pass (DESIGN_report_v2.md §3, ratified 2026-10-29). Offline: the stub serves the
VerifierExtraction. Every assertion is about the record and the rendered report."""

from __future__ import annotations

from typing import Any

from conftest import stub_client
from extractor_mvp import render
from extractor_mvp.coverage_extractor import SpatialExtraction, TemporalVolumeExtraction
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.verifier import (
    VERIFIER_PROMPT,
    FieldVerdict,
    SoftwareVerdict,
    VerifierExtraction,
    compact_draft,
)

TEXT = (
    "Structural images were registered and resampled to an isotropic standard space. "
    "Images were smoothed with a 6 mm FWHM Gaussian kernel. "
    "No slice-timing correction was applied. "
    "Statistics were computed in R version 4.1.0. "
    "Two preprocessing variants were compared: with and without global signal regression (n = 2). "
    "Task and rest data were preprocessed separately in two branches."
)
_SMOOTH = "Images were smoothed with a 6 mm FWHM Gaussian kernel."


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _ex(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _prep_payload(**kw: Any) -> PreprocessingExtraction:
    base = dict(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    base.update(kw)
    return PreprocessingExtraction(**base)


def _run(verifier: Any = None, counter: dict | None = None, **kw: Any) -> tuple[Any, dict, str]:
    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    out: list[Any] = []
    prep, _, _ = extract(
        paper,
        "m",
        client=stub_client(
            _prep_payload(**kw.pop("shared", {})),
            spatial=SpatialExtraction(**kw.pop("spatial", {})),
            temporal=TemporalVolumeExtraction(**kw.pop("temporal", {})),
            verifier=verifier,
            counter=counter,
        ),
        verifier_out=out,
    )
    record = out[0]
    report = render.to_report(
        prep, source="t", verifier=record, multiple_pipelines=record.get("multiple_pipelines")
    )
    return prep, record, report


def test_one_more_call_and_never_without_a_caller_asking() -> None:
    counter: dict[str, int] = {}
    _run(counter=counter)
    assert counter["VerifierExtraction"] == 1
    counter2: dict[str, int] = {}
    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    extract(paper, "m", client=stub_client(_prep_payload(), counter=counter2))
    assert "VerifierExtraction" not in counter2


def test_the_draft_carries_full_quotes_and_omits_untargeted_fields() -> None:
    prep, _, _ = _run(
        spatial={"smoothing_performed": _ex("yes", _SMOOTH), "smoothing_fwhm_mm": _ex("6", _SMOOTH)}
    )
    draft = compact_draft(prep)
    assert f'spatial_smoothing.fwhm_mm | extracted | 6.0 | quote: "{_SMOOTH}"' in draft
    assert "not_targeted_by_mvp" not in draft
    assert "{text}" in VERIFIER_PROMPT and "{draft}" in VERIFIER_PROMPT


def test_wrong_demotes_the_value_to_a_flag_and_never_replaces_it() -> None:
    struct = "Structural images were registered and resampled to an isotropic standard space."
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_normalization.target_space",
                verdict="wrong",
                reason="the sentence is about the structural image",
                relied_on=struct,
                better_value="not reported",
            ),
            FieldVerdict(field="spatial_smoothing.fwhm_mm", verdict="supported", relied_on=_SMOOTH),
        ]
    )
    prep, _record, report = _run(
        verifier=verdict,
        shared={"target_space": _ex("isotropic standard space", struct)},
        spatial={
            "smoothing_performed": _ex("yes", _SMOOTH),
            "smoothing_fwhm_mm": _ex("6", _SMOOTH),
        },
    )
    # the extraction arm is untouched
    ts = next(s for s in prep.steps if s.kind == "spatial_normalization").target_space
    assert ts.extraction.status == "EXTRACTED"
    assert ts.extraction.value.verbatim == "isotropic standard space"
    line = next(ln for ln in report.splitlines() if ln.startswith("- ⚑ target_space"))
    assert '"isotropic standard space"' in line
    assert (
        "checking pass: WRONG — the sentence is about the structural image; should be: not reported"
        in line
    )
    assert "- fwhm_mm = 6.0   [from paper]" in report and "[check: supported]" in report
    assert (
        "Intersubject registration [validated against labels] — flagged by the checking pass"
        in report
    )
    assert "Checking pass (unvalidated" in report and "wrong 1" in report


def test_missed_names_what_the_paper_states_and_fills_nothing() -> None:
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.fwhm_mm",
                verdict="missed",
                reason="the kernel is stated",
                relied_on=_SMOOTH,
                better_value="6",
            )
        ]
    )
    prep, _, report = _run(verifier=verdict)
    fwhm = next(s for s in prep.steps if s.kind == "spatial_smoothing").fwhm_mm
    assert fwhm.extraction.status == "MISSING_FROM_PAPER"
    assert "checking pass: MISSED — the paper states: 6 «Images were smoothed" in report
    assert "[missed per the checking pass: fwhm_mm]" in report


def test_a_verdict_whose_sentence_does_not_resolve_has_no_effect() -> None:
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.fwhm_mm",
                verdict="wrong",
                reason="x",
                relied_on="a sentence nowhere in the text",
            )
        ]
    )
    _, _, report = _run(
        verifier=verdict,
        spatial={
            "smoothing_performed": _ex("yes", _SMOOTH),
            "smoothing_fwhm_mm": _ex("6", _SMOOTH),
        },
    )
    assert "- ⚑ fwhm_mm" not in report
    assert "[check: unverified verdict — its sentence did not resolve]" in report
    assert "flagged by the checking pass" not in report


def test_a_failing_verifier_never_fails_the_paper() -> None:
    class Boom:
        def __init__(self) -> None:
            from types import SimpleNamespace

            self.inner = stub_client(_prep_payload())
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, *, response_model: Any = None, **kw: Any) -> Any:
            if response_model is VerifierExtraction:
                raise RuntimeError("transport down")
            return self.inner.chat.completions.create(response_model=response_model, **kw)

    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    out: list[Any] = []
    prep, _, _ = extract(paper, "m", client=Boom(), verifier_out=out)
    assert out[0]["status"] == "unavailable" and "transport down" in out[0]["error"]
    report = render.to_report(prep, source="t", verifier=out[0])
    assert "Checking pass: unavailable — no field was checked" in report


def test_multiple_pipelines_is_asked_here_and_a_benchmark_wording_is_in_the_prompt() -> None:
    quote = "Task and rest data were preprocessed separately in two branches."
    _, record, report = _run(
        verifier=VerifierExtraction(
            multiple_pipelines=_ex("yes", quote),
            pipeline_variant_count=_ex(
                "2",
                "Two preprocessing variants were compared: with and without global signal "
                "regression (n = 2).",
            ),
        )
    )
    assert record["multiple_pipelines"]["V"]["multiple_pipelines"]["extraction"]["value"] is True
    assert (
        "> ⚠ More than one preprocessing variant is described — checking pass: yes, count 2"
        in report
    )
    assert "PREPROCESSES ITS OWN DATA IN MORE THAN ONE WAY" in VERIFIER_PROMPT
    assert "benchmark of several denoising or preprocessing" in VERIFIER_PROMPT
    # the coverage calls no longer ask it (F3a)
    assert "multiple_pipelines" not in SpatialExtraction.model_fields
    assert "multiple_pipelines" not in TemporalVolumeExtraction.model_fields


def test_software_the_checking_pass_marks_not_preprocessing_is_shown_not_counted() -> None:
    from extractor_mvp.coverage_extractor import SoftwareMentionResult

    r = SoftwareMentionResult(
        name="R", version="4.1.0", verbatim_quote="Statistics were computed in R version 4.1.0."
    )
    _, _, report = _run(
        verifier=VerifierExtraction(software=[SoftwareVerdict(name="R", preprocessing_use=False)]),
        spatial={"software_mentions": [r]},
    )
    assert "not counted, not preprocessing per the checking pass: r" in report
