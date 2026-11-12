"""Pre-rerun item 1 (2026-11-11): a value's evidence as 1-3 verbatim spans. Each span is resolved;
the value is supported only if every span resolves, and the support check reads their texts together.
The methods text is written for these tests and quotes no paper."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from extractor_mvp.extraction_result import StepFieldResult, VariantResult
from extractor_mvp.extractor import _process_field
from extractor_mvp.rechecks import _spec_for

TEXT = (
    "Functional images were spatially smoothed. "
    "Data from various steps will be shown in the figures. "
    "The Gaussian kernel had a full width at half maximum of 6 mm. "
    "Resting-state data were smoothed with a 4 mm kernel."
)
S1 = "Functional images were spatially smoothed."
S2 = "The Gaussian kernel had a full width at half maximum of 6 mm."
S3 = "Resting-state data were smoothed with a 4 mm kernel."
DOTTED = "spatial_smoothing.fwhm_mm"


def _run(fe: StepFieldResult) -> tuple[Any, Any]:
    spec = _spec_for(DOTTED)
    assert spec is not None
    kwargs = {k: spec[k] for k in ("value_kind", "synonyms", "use_synonym_table") if k in spec}
    pf, diag, _ = _process_field(
        spec["field_id"], DOTTED, fe, spec["literal_type"], spec["t"], TEXT, None, **kwargs
    )
    return pf, diag


def test_two_quotes_both_resolve_and_the_value_is_read_across_them() -> None:
    pf, diag = _run(
        StepFieldResult(status="extracted", value="6", verbatim_quote=S1, additional_quotes=[S2])
    )
    assert diag is None and pf.extraction.status == "EXTRACTED"
    assert [s.text for s in pf.extraction.spans] == [S1, S2]
    assert pf.extraction.value == 6.0
    # control: the first sentence alone does not carry the number
    pf, diag = _run(StepFieldResult(status="extracted", value="6", verbatim_quote=S1))
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert diag.failure_reason == "value_unsupported_by_quote"


def test_one_unresolved_span_makes_the_value_unsupported() -> None:
    pf, diag = _run(
        StepFieldResult(
            status="extracted",
            value="6",
            verbatim_quote=S2,
            additional_quotes=["A sentence that is not in the text at all."],
        )
    )
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert diag.failure_reason.startswith("extraction_quote_unresolved:")
    assert diag.raw_more_quotes == ("A sentence that is not in the text at all.",)


def test_a_stitched_quote_does_not_resolve_and_two_spans_do() -> None:
    """power_2014's Stage 2b failure, in miniature: two sentences joined around the one between."""
    stitched = S1 + " " + S2
    pf, diag = _run(StepFieldResult(status="extracted", value="6", verbatim_quote=stitched))
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert diag.failure_reason.startswith("extraction_quote_unresolved")
    pf, _ = _run(
        StepFieldResult(status="extracted", value="6", verbatim_quote=S1, additional_quotes=[S2])
    )
    assert pf.extraction.status == "EXTRACTED"


def test_a_repeated_quote_is_one_span() -> None:
    pf, _ = _run(
        StepFieldResult(status="extracted", value="6", verbatim_quote=S2, additional_quotes=[S2])
    )
    assert len(pf.extraction.spans) == 1


def test_additional_quotes_are_at_most_two_and_only_on_an_extracted_value() -> None:
    with pytest.raises(ValidationError):
        StepFieldResult(
            status="extracted", value="6", verbatim_quote=S1, additional_quotes=[S2, S3, S1]
        )
    with pytest.raises(ValidationError, match="additional_quotes"):
        StepFieldResult(status="missing", additional_quotes=[S2])
    VariantResult(value="4", verbatim_quote=S3, applies_to="rest", additional_quotes=[S1])


def test_a_variant_keeps_its_spans() -> None:
    fe = StepFieldResult(
        status="varied",
        variants=[
            VariantResult(value="6", verbatim_quote=S1, additional_quotes=[S2], applies_to="task"),
            VariantResult(value="4", verbatim_quote=S3, applies_to="Resting-state data"),
        ],
    )
    pf, _ = _run(fe)
    assert pf.extraction.status == "VARIED"
    task, rest = pf.extraction.variants
    assert [s.text for s in task.spans] == [S1, S2] and len(rest.spans) == 1


def test_the_report_shows_a_values_spans_joined_and_one_span_as_before() -> None:
    from extractor_mvp.render import SPAN_JOIN, _row_from_field

    pf, _ = _run(
        StepFieldResult(status="extracted", value="6", verbatim_quote=S1, additional_quotes=[S2])
    )
    row = _row_from_field(pf, DOTTED, "spatial_smoothing", None)
    assert row.span_text == S1 + SPAN_JOIN + S2
    pf, _ = _run(StepFieldResult(status="extracted", value="6", verbatim_quote=S2))
    assert _row_from_field(pf, DOTTED, "spatial_smoothing", None).span_text == S2


def test_the_quote_rule_is_in_the_three_extraction_prompts_only() -> None:
    from extractor_mvp.coverage_extractor import SPATIAL_PROMPT, TEMPORAL_VOLUME_PROMPT
    from extractor_mvp.extractor import EXTRACTION_PROMPT
    from extractor_mvp.prompt_rules import QUOTE_RULES
    from extractor_mvp.verifier import VERIFIER_PROMPT

    for p in (EXTRACTION_PROMPT, TEMPORAL_VOLUME_PROMPT, SPATIAL_PROMPT):
        assert QUOTE_RULES in p
    assert "Never stitch" in QUOTE_RULES and "additional_quotes" in QUOTE_RULES
    assert QUOTE_RULES not in VERIFIER_PROMPT


def test_every_span_gets_full_paper_offsets() -> None:
    from extractor_mvp.batch import _translate_spans

    pf, _ = _run(
        StepFieldResult(status="extracted", value="6", verbatim_quote=S1, additional_quotes=[S2])
    )
    dump = {"steps": [{"kind": "spatial_smoothing", "fwhm_mm": pf.model_dump(mode="json")}]}
    _translate_spans(dump, 100)
    for sp in dump["steps"][0]["fwhm_mm"]["extraction"]["spans"]:
        assert sp["span_in_full_paper"] == {"start": sp["start"] + 100, "end": sp["end"] + 100}
