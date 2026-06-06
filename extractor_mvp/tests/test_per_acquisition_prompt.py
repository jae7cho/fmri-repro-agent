"""The per-acquisition prompt substitutes scope fields and stays self-contained."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extractor_mvp.extractor import (
    EXTRACTION_PROMPT,
    PER_ACQUISITION_EXTRACTION_PROMPT,
    extract_preprocessing_for_acquisition,
)
from extractor_mvp.parsed_paper import ParsedPaper


def test_prompt_substitutes_scope_fields():
    prompt = PER_ACQUISITION_EXTRACTION_PROMPT.format(
        paper_name="HCP-TRT", characterizing_quote="the HCP test-retest data", text="BODY TEXT"
    )
    assert 'named: "HCP-TRT"' in prompt
    assert "the HCP test-retest data" in prompt
    assert "BODY TEXT" in prompt
    # still contains the base v3 instructions
    assert "verbatim_quote" in prompt
    assert "Output status for each field" in prompt
    assert "Do not infer values from the named pipeline" in prompt
    # the base prompt is appended after the scope prefix
    assert prompt.index('named: "HCP-TRT"') < prompt.index("Do not infer values")


def test_base_prompt_has_no_scope_prefix():
    assert "ONE specific acquisition" not in EXTRACTION_PROMPT
    assert "ONE specific acquisition" in PER_ACQUISITION_EXTRACTION_PROMPT


def test_scope_directive_does_not_leak_other_acquisition_names():
    # the directive line names only the acquisition passed in
    captured: dict[str, str] = {}

    def fake_create(*, messages: Any, **_: Any) -> Any:
        captured["prompt"] = messages[0]["content"]
        from extractor_mvp.extraction_result import FieldExtractionResult
        from extractor_mvp.extractor import PreprocessingExtraction

        none = FieldExtractionResult(status="missing")
        return PreprocessingExtraction(
            target_space=none,
            resolution_mm=none,
            surface_registration=none,
            target_surface=none,
            intensity_convention=none,
            intensity_value=none,
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    paper = ParsedPaper(text="HCP and ABCD were both used.", source="t", parser="manual")
    extract_preprocessing_for_acquisition(paper, "HCP", "HCP", "m", client=client)
    assert 'named: "HCP"' in captured["prompt"]
    assert 'named: "ABCD"' not in captured["prompt"]
