"""The resolution call (the author's item 1, 2026-11-09). A stubbed client only: no model call.
Synthetic inputs only: no paper text."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from extractor_mvp import render
from extractor_mvp.resolution_call import (
    PROMPT,
    ResolutionAnswer,
    SubItem,
    build_prompt,
    fill_method_arm,
    interpret,
    run_resolution,
)
from test_motion_inference import _method, _method_pf, _prep

TEXT = "Volumes were realigned to the first volume with a synthetic tool. More synthetic text."


def _answer(tool: str = "spm", pipeline: str = "none", **items: SubItem) -> ResolutionAnswer:
    unknown = SubItem(status="unknown")
    return ResolutionAnswer(
        resolved_pipeline=pipeline,
        realignment_tool=tool,
        basis="a synthetic basis",
        reference_scan=items.get("reference_scan", unknown),
        interpolation=items.get("interpolation", unknown),
        similarity_metric=items.get("similarity_metric", unknown),
        susceptibility_correction=items.get("susceptibility_correction", unknown),
    )


def _record(*tool_ids: str) -> dict[str, Any]:
    return {"software_mentions": [{"tool_id": t, "display_name": t.upper()} for t in tool_ids]}


def test_a_kb_tool_the_paper_names_is_confirmed_with_its_kb_program() -> None:
    out = interpret(_answer("spm"), _record("spm"), TEXT)
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_DEFAULT"
    conf = tool["kb_confirmation"]
    assert (conf["program"], conf["package"], conf["basis"]) == ("Realign", "spm", "package_named")
    assert conf["source"]


def test_a_kb_pipeline_whose_default_is_the_tool_confirms_it() -> None:
    out = interpret(_answer("spm", pipeline="conn"), _record("conn"), TEXT)
    conf = out["realignment_tool"]["kb_confirmation"]
    assert conf["basis"] == "pipeline_default" and conf["pipeline"] == "conn"
    assert out["resolved_pipeline"] == {"value": "conn", "kb": True}


@pytest.mark.parametrize(
    ("tool", "pipeline", "named"),
    [
        ("spm", "none", ()),  # a KB tool neither named nor any pipeline's default
        ("fsl", "conn", ()),  # a pipeline whose default is another tool
        ("an in-house realigner", "none", ()),  # free text
    ],
)
def test_anything_the_kb_does_not_confirm_is_the_models(
    tool: str, pipeline: str, named: tuple[str, ...]
) -> None:
    out = interpret(_answer(tool, pipeline=pipeline), _record(*named), TEXT)
    assert out["realignment_tool"]["provenance"] == "INFERRED_MODEL"
    assert "kb_confirmation" not in out["realignment_tool"]


def test_none_is_unknown() -> None:
    out = interpret(_answer("none"), _record(), TEXT)
    assert out["realignment_tool"] == {"value": None, "kb": False, "provenance": "UNKNOWN"}


def test_sub_items_take_their_provenance_from_the_text() -> None:
    out = interpret(
        _answer(
            reference_scan=SubItem(
                status="stated", value="first volume", quote="realigned to the first volume"
            ),
            interpolation=SubItem(status="stated", value="sinc", quote="not in the text at all"),
            similarity_metric=SubItem(status="inferred_from_default", value="least squares"),
        ),
        _record("spm"),
        TEXT,
    )
    items = out["sub_items"]
    assert items["reference_scan"]["provenance"] == "EXTRACTED"
    assert items["interpolation"]["provenance"] == "INFERRED_MODEL"
    assert items["similarity_metric"]["provenance"] == "INFERRED_MODEL"
    assert items["susceptibility_correction"] == {
        "status": "unknown",
        "value": None,
        "provenance": "UNKNOWN",
    }


def test_the_prompt_carries_the_inputs_the_kb_index_and_the_coregistration_rule() -> None:
    prep = _prep(_method("described_only", phrase="realigned"), "CONN toolbox")
    record = {
        "software_mentions": [
            {"tool_id": "spm", "display_name": "SPM", "version": "12", "use": "processing"}
        ],
        "data_release": {"releases": [{"dataset": "SYNTH", "release": "2.0"}]},
    }
    p = build_prompt(record, prep)
    assert "Base pipeline phrase: CONN toolbox" in p
    assert "- SPM | version 12 | processing" in p
    assert "Motion method phrase: realigned" in p
    assert "Data release: SYNTH 2.0" in p
    assert "pipeline conn: CONN" in p and "tool spm:" in p
    assert (
        "TO CORRECT FOR HEAD MOTION" in PROMPT
        and "is motion correction, not coregistration" in PROMPT
    )


class _Stub:
    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.calls = 0

    def _create(self, **kwargs: Any) -> Any:
        self.calls += 1
        assert kwargs["response_model"] is ResolutionAnswer
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_one_call_and_a_failed_call_is_a_state() -> None:
    prep = _prep(_method("missing"), None)
    stub = _Stub(_answer("spm"))
    out = run_resolution(_record("spm"), prep, TEXT, "m", client=stub)
    assert stub.calls == 1 and out["status"] == "ok"
    failed = run_resolution(_record(), prep, TEXT, "m", client=_Stub(RuntimeError("boom")))
    assert failed["status"] == "call_failed" and "boom" in failed["error"]


def test_only_a_kb_confirmed_program_fills_a_missing_or_deferred_method() -> None:
    confirmed = interpret(_answer("spm"), _record("spm"), TEXT)
    model_only = interpret(_answer("spm"), _record(), TEXT)
    for kind in ("missing", "deferred"):
        pf = _method_pf(fill_method_arm(_prep(_method(kind), None), confirmed))
        assert pf.inference.status == "INFERRED_DEFAULT"
        assert pf.inference.value.resolved == "spm_realign"
        assert pf.inference.basis.basis_type == "derived"
        assert pf.inference.basis.source_field_ids == ["resolution_call"]
        assert _method_pf(
            fill_method_arm(_prep(_method(kind), None), model_only)
        ).inference.status == ("LEFT_MISSING")
    extracted = _prep(_method("described_only"), None)
    assert _method_pf(fill_method_arm(extracted, confirmed)).inference.status == "NOT_APPLICABLE"


def test_the_report_keeps_the_papers_phrase_and_says_where_each_answer_came_from() -> None:
    prep = _prep(_method("described_only", phrase="realigned"), None)
    confirmed = interpret(
        _answer(
            "spm",
            reference_scan=SubItem(status="inferred_from_default", value="mean volume"),
        ),
        _record("spm"),
        TEXT,
    )
    out = render.to_report(prep, resolution=confirmed)
    assert 'method = "realigned"' in out
    assert "realignment tool: spm → Realign   [KB default, named in the paper:" in out
    assert "reference_scan = mean volume   [inferred by the model, unconfirmed]" in out
    model_only = interpret(_answer("an in-house realigner"), _record(), TEXT)
    assert (
        "realignment tool: an in-house realigner   [inferred by the model, unconfirmed]"
        in render.to_report(prep, resolution=model_only)
    )
    assert "resolution call: call_failed" in render.to_report(
        prep, resolution={"status": "call_failed", "error": "x"}
    )


def test_the_extraction_no_longer_runs_the_lookup_inference() -> None:
    import inspect

    from extractor_mvp import extractor

    src = inspect.getsource(extractor)
    assert "infer_motion_method(" not in src
