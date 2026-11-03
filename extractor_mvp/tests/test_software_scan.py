"""The software list by deterministic KB scan and one scoped question per mention (the author's
ruling, 2026-11-03). Offline: a fixed tool table and a stub client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extractor_mvp.software_scan import MentionUse, ask_uses, scan, tool_list

TOOLS: dict[str, dict[str, Any]] = {
    "fsl": {
        "display_name": "FSL",
        "aliases": ["FSL", "FSL suite", "FMRIB Software Library"],
        "version_token": False,
    },
    "afni": {"display_name": "AFNI", "aliases": ["AFNI", "afni"], "version_token": False},
    "spm": {"display_name": "SPM", "aliases": ["SPM"], "version_token": True},
    "mmps": {"display_name": "MMPS", "aliases": ["MMPS"], "version_token": False},
}


def test_a_mention_is_matched_whole_with_the_longest_alias_and_once_per_sentence() -> None:
    text = (
        "Methods. We used the FMRIB Software Library (FSL) and FSL again. "
        "Ventricles were masked; SPMs were thresholded. Data were preprocessed in SPM12. "
        "AFNI48 was cited."
    )
    ms = scan(text, TOOLS)
    assert [(m.tool_id, m.alias) for m in ms] == [
        ("fsl", "FMRIB Software Library"),  # one mention for the sentence, the longest alias first
        ("spm", "SPM"),
        ("afni", "AFNI"),
    ]
    assert ms[1].version == "12"  # SPM's version is part of its name token
    assert ms[2].version is None  # a citation number glued to AFNI is not a version


def test_a_version_written_after_the_name_is_read_and_the_reference_list_is_skipped() -> None:
    text = (
        "Methods. Surfaces used FSL version 6.0.4 throughout. Masks used MMPS.\n"
        "References\nSmith, S., 2004. Advances in FSL. NeuroImage 23, 1.\n"
    )
    ms = scan(text, TOOLS)
    assert [(m.tool_id, m.version) for m in ms] == [("fsl", "6.0.4"), ("mmps", None)]
    assert all(m.start < text.index("References") for m in ms)
    assert ms[0].sentence == "Surfaces used FSL version 6.0.4 throughout."


def test_case_matters_so_a_lower_case_word_is_not_a_package() -> None:
    assert scan("Methods. The fsl flag and mmps were unrelated words.", TOOLS) == []


def _client(answers: list[MentionUse], prompts: list[str]) -> Any:
    def create(*, messages: Any = None, **_kw: Any) -> Any:
        prompts.append(messages[0]["content"])
        return answers[len(prompts) - 1]

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_one_question_per_mention_and_a_tool_counts_only_on_a_found_quote_and_a_yes() -> None:
    text = (
        "Methods. Head motion was corrected with AFNI. Regressors were masked with FSL. "
        "Statistics used FSL as well, later. Tracts were labelled with MMPS."
    )
    ms = scan(text, TOOLS)
    assert [m.tool_id for m in ms] == ["afni", "fsl", "fsl", "mmps"]
    prompts: list[str] = []
    answers = [
        MentionUse(use="motion", use_quote="Head motion was corrected with AFNI.", fmri="yes"),
        MentionUse(use="masks", use_quote="A sentence not in the passage.", fmri="yes"),
        MentionUse(use="statistics", use_quote="Statistics used FSL as well, later.", fmri="no"),
        MentionUse(use="tracts", use_quote="Tracts were labelled with MMPS.", fmri="unclear"),
    ]
    uses = ask_uses(ms, "m", client=_client(answers, prompts))
    assert len(prompts) == 4 and "package AFNI" in prompts[0]
    assert [u["counts"] for u in uses] == [True, False, False, False]
    tools = {t["tool_id"]: t for t in tool_list(uses)}
    assert tools["afni"]["kept"] and tools["afni"]["use_quote"].startswith("Head motion")
    assert not tools["fsl"]["kept"] and tools["fsl"]["mentions"] == 2
    assert not tools["mmps"]["kept"]


def test_a_failed_question_is_recorded_never_raised() -> None:
    def create(**_kw: Any) -> Any:
        raise RuntimeError("down")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    [u] = ask_uses(scan("Methods. Frames were realigned with AFNI.", TOOLS), "m", client=client)
    assert u["status"] == "call_failed" and "counts" not in u
    assert tool_list([u])[0]["kept"] is False


def test_two_aliases_from_one_start_keep_the_longer() -> None:
    [m] = scan("Methods. Frames were masked with the FSL suite tools.", TOOLS)
    assert m.alias == "FSL suite"


def test_each_mention_has_its_own_meter_label_so_attempts_count_retries() -> None:
    text = "Methods. Frames were realigned with AFNI. Masks were also made with AFNI."
    meter = SimpleNamespace(label="")
    labels: list[str] = []

    def create(**_kw: Any) -> Any:
        labels.append(meter.label)
        return MentionUse(use="x")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    ask_uses(scan(text, TOOLS), "m", client=client, meter=meter)
    assert len(labels) == 2 and len(set(labels)) == 2
