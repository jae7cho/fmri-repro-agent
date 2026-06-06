"""End-to-end two-pass extraction with a mocked client (Pass 1 + Pass 2)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extractor_mvp.acquisition_discovery import _LLMAcquisition, _LLMAcquisitionList
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction
from extractor_mvp.field_diff import compute_field_diffs
from extractor_mvp.multi_acquisition_extractor import extract_multi_acquisition
from extractor_mvp.parsed_paper import ParsedPaper

TEXT = (
    "We used HCP data normalized to MNI152NLin6Asym space. "
    "We also used ABCD data normalized to Talairach space."
)


def _none() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _ts_only(value: str, quote: str) -> PreprocessingExtraction:
    return PreprocessingExtraction(
        target_space=FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote),
        resolution_mm=_none(),
        surface_registration=_none(),
        target_surface=_none(),
        intensity_convention=_none(),
        intensity_value=_none(),
    )


class _MultiPassClient:
    def __init__(self, acq_list: _LLMAcquisitionList, prep_payloads: list[Any]):
        self._acq = acq_list
        self._preps = list(prep_payloads)
        self.pass2_prompts: list[str] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *, response_model: Any, messages: Any, **_: Any) -> Any:
        if response_model is _LLMAcquisitionList:
            return self._acq
        self.pass2_prompts.append(messages[0]["content"])
        payload = self._preps.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload


def _acq_list() -> _LLMAcquisitionList:
    return _LLMAcquisitionList(
        acquisitions=[
            _LLMAcquisition(paper_name="HCP", characterizing_quote="HCP data"),
            _LLMAcquisition(paper_name="ABCD", characterizing_quote="ABCD data"),
        ]
    )


def _paper() -> ParsedPaper:
    return ParsedPaper(text=TEXT, source="t", parser="manual")


def test_two_pass_end_to_end_acquisition_specific():
    client = _MultiPassClient(
        _acq_list(),
        [
            _ts_only("MNI152NLin6Asym", "normalized to MNI152NLin6Asym"),
            _ts_only("Talairach", "normalized to Talairach"),
        ],
    )
    result = extract_multi_acquisition(_paper(), "m", client=client)
    assert set(result.extractions) == {"hcp", "abcd"}
    diff = next(d for d in compute_field_diffs(result) if d.field_name == "target_space")
    assert diff.classification == "acquisition_specific"
    # each Pass-2 prompt is scoped to its own acquisition (no cross-leak in the directive)
    assert any('named: "HCP"' in p for p in client.pass2_prompts)
    assert any('named: "ABCD"' in p for p in client.pass2_prompts)


def test_pass2_failure_recorded_not_aborting():
    client = _MultiPassClient(
        _acq_list(),
        [
            _ts_only("MNI152NLin6Asym", "normalized to MNI152NLin6Asym"),
            RuntimeError("bedrock 500"),  # ABCD Pass-2 fails
        ],
    )
    result = extract_multi_acquisition(_paper(), "m", client=client)
    assert "hcp" in result.extractions  # HCP still extracted
    assert "abcd" not in result.extractions  # ABCD failed -> no extraction
    assert any("pass2_failed" in d.failure_reason for d in result.diagnostics["abcd"])
