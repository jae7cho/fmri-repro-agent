"""Pass 1 acquisition discovery: slugify + LLM parsing + collision/span handling."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extractor_mvp.acquisition_discovery import (
    _LLMAcquisition,
    _LLMAcquisitionList,
    discover_acquisitions,
    slugify_paper_name,
)
from extractor_mvp.parsed_paper import ParsedPaper


def test_slugify_edge_cases():
    assert slugify_paper_name("HCP-TRT") == "hcp_trt"
    assert slugify_paper_name("ABCD cohort") == "abcd_cohort"
    assert slugify_paper_name("Sample 1") == "sample_1"
    assert slugify_paper_name("") == "unnamed_acquisition"
    assert slugify_paper_name("!!!@@@") == "unnamed_acquisition"
    assert slugify_paper_name("  Discovery  Sample  ") == "discovery_sample"


def _fake_client(acq_list: _LLMAcquisitionList) -> Any:
    completions = SimpleNamespace(create=lambda **_: acq_list)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_discovery_resolves_spans_and_slugs():
    text = "We analyzed the HCP-TRT dataset and the eNKI cohort separately."
    payload = _LLMAcquisitionList(
        acquisitions=[
            _LLMAcquisition(paper_name="HCP-TRT", characterizing_quote="the HCP-TRT dataset"),
            _LLMAcquisition(paper_name="eNKI cohort", characterizing_quote="the eNKI cohort"),
        ]
    )
    res = discover_acquisitions(
        ParsedPaper(text=text, source="t", parser="manual"), "m", client=_fake_client(payload)
    )
    assert [a.acquisition_id for a in res.acquisitions] == ["hcp_trt", "enki_cohort"]
    assert res.note is None
    assert res.acquisitions[0].span is not None  # quote resolved
    assert res.acquisitions[0].span_failure_reason is None


def test_discovery_collision_appends_suffix():
    text = "Sample 1 was scanned. Later, a different Sample 1 was also scanned."
    payload = _LLMAcquisitionList(
        acquisitions=[
            _LLMAcquisition(paper_name="Sample 1", characterizing_quote="Sample 1 was scanned"),
            _LLMAcquisition(paper_name="Sample 1", characterizing_quote="a different Sample 1"),
        ]
    )
    res = discover_acquisitions(
        ParsedPaper(text=text, source="t", parser="manual"), "m", client=_fake_client(payload)
    )
    assert [a.acquisition_id for a in res.acquisitions] == ["sample_1", "sample_1_2"]


def test_discovery_unresolvable_quote_flagged():
    payload = _LLMAcquisitionList(
        acquisitions=[_LLMAcquisition(paper_name="HCP", characterizing_quote="not in the text")]
    )
    res = discover_acquisitions(
        ParsedPaper(text="some other text entirely", source="t", parser="manual"),
        "m",
        client=_fake_client(payload),
    )
    assert res.note == "single_acquisition_paper"
    assert res.acquisitions[0].span is None
    assert res.acquisitions[0].span_failure_reason == "quote_not_found"


def test_discovery_empty_noted():
    payload = _LLMAcquisitionList(acquisitions=[])
    res = discover_acquisitions(
        ParsedPaper(text="x", source="t", parser="manual"), "m", client=_fake_client(payload)
    )
    assert res.note == "no_acquisitions_found"
    assert res.acquisitions == []
