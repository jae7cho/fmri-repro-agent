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
    kb_id,
    kb_index,
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
    return {
        "software_mentions": [
            {"tool_id": t, "display_name": t.upper(), "use": "preprocessing"} for t in tool_ids
        ]
    }


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
    assert out["resolved_pipeline"] == {"value": "conn", "kb": True, "provenance": "pipeline name"}


@pytest.mark.parametrize(
    ("tool", "pipeline", "named"),
    [
        ("spm", "none", ()),  # a KB tool neither named nor any pipeline's default
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
        _record(),  # the tool is not named in the paper: no KB defaults, the model's answers stand
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
    assert "- conn (pipeline): CONN" in p and "- spm (tool):" in p
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
    # SPM is named and no pipeline wraps it: its KB default replaces the model's guess
    assert "reference_scan = register to mean" in out and "[KB default of the tool:" in out
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


@pytest.mark.parametrize(
    ("answer", "kind", "expected"),
    [
        ("tool spm", "tool", "spm"),  # the index line echoed back (the 2026-11-09 metered run)
        ("pipeline conn", "pipeline", "conn"),
        ("spm", "tool", "spm"),
        ("SPM12", "tool", "spm"),  # a name the KB's tool recogniser knows
        ("Conn toolbox", "pipeline", "conn"),
        ("an in-house realigner", "tool", None),
        (None, "tool", None),
    ],
)
def test_an_answer_is_mapped_to_its_kb_id(
    answer: str | None, kind: str, expected: str | None
) -> None:
    pipes, tools = kb_index()
    assert kb_id(answer, pipes if kind == "pipeline" else tools, kind) == expected


def test_an_echoed_index_prefix_is_still_confirmed() -> None:
    out = interpret(_answer("tool spm", pipeline="pipeline conn"), _record("conn", "spm"), TEXT)
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_DEFAULT" and tool["value"] == "spm"
    assert tool["as_answered"] == "tool spm"
    assert out["resolved_pipeline"]["value"] == "conn" and out["resolved_pipeline"]["kb"] is True


def test_a_stored_lookup_inference_is_not_rendered_beside_a_resolution() -> None:
    from extractor_mvp.full_report import render_record

    prep = _prep(_method("described_only", phrase="realigned"), None)
    lookup = {
        "field": "motion_correction.method",
        "path": "diagnostic",
        "reason": "r",
        "program": "LookupProgram",
        "basis_name": "package",
        "basis_type": "derived",
        "confidence": 0.7,
        "source": "a lookup source",
        "note": None,
        "alternatives": [],
    }
    record = {
        "paper_id": "synthetic",
        "status": "success",
        "preprocessing": prep.model_dump(mode="json"),
        "methods": {
            "found_via": "header_match",
            "matched_header": "Methods",
            "start_offset": 0,
            "end_offset": 10,
            "slice_ratio": 0.1,
            "ended_at": None,
            "suspicious": False,
            "fallback_reason": None,
        },
        "motion_inference": lookup,
    }
    assert "LookupProgram" in render_record(record)
    record["resolution"] = interpret(_answer("spm"), _record("spm"), TEXT)
    out = render_record(record)
    assert "LookupProgram" not in out and "realignment tool: spm → Realign" in out


def test_kb_defaults_fill_sub_items_only_for_a_named_unwrapped_tool_of_a_documented_version() -> (
    None
):
    def run(tool: str, pipeline: str, *mentions: dict[str, Any]) -> dict[str, Any]:
        record = {"software_mentions": list(mentions)}
        return interpret(_answer(tool, pipeline=pipeline), record, TEXT)

    spm = {
        "tool_id": "spm",
        "display_name": "SPM",
        "use": "preprocessing",
        "sentence": "Data were processed in SPM12.",
    }
    out = run("spm", "none", spm)
    items = out["sub_items"]
    assert items["reference_scan"]["provenance"] == "INFERRED_DEFAULT"
    assert items["reference_scan"]["value"].startswith("register to mean")
    assert items["interpolation"]["value"] == (
        "estimate: 2nd degree B-spline; reslice: 4th degree B-spline"
    )
    assert items["similarity_metric"]["value"] == "least squares"
    assert "spm_defaults.m line 105" in items["reference_scan"]["source"]
    assert items["susceptibility_correction"]["provenance"] == "UNKNOWN"  # no KB default
    assert out["tool_defaults"]["applied"] is True
    # a stated version the defaults are not documented for
    old = {
        "tool_id": "spm",
        "display_name": "SPM",
        "version": "99",
        "use": "preprocessing",
        "sentence": "SPM99 was used.",
    }
    out = run("spm", "none", old)
    assert out["tool_defaults"]["applied"] is False and "99" in out["tool_defaults"]["reason"]
    assert out["sub_items"]["reference_scan"]["provenance"] == "UNKNOWN"
    # wrapped by a KB pipeline whose settings the KB does not record: the pipeline may override,
    # so no tool defaults (2026-11-10: a pipeline that records them is tested below)
    # (2026-11-11: fMRIPrep's settings are now recorded; DPARSF's are not)
    out = run("spm", "dparsf", spm, {"tool_id": "spm", "display_name": "DPARSF"})
    assert out["tool_defaults"]["applied"] is False
    assert "dparsf, whose own settings" in out["tool_defaults"]["reason"]
    # FSL: no reslice default is sourced, so interpolation is the estimate default alone
    fsl = {
        "tool_id": "fsl",
        "display_name": "FSL",
        "use": "preprocessing",
        "sentence": "FSL was used.",
    }
    # FSL: the reslice default is sourced since 2026-11-11 (FSL mcflirt 2111.0)
    assert run("fsl", "none", fsl)["sub_items"]["interpolation"]["value"] == (
        "estimate: trilinear; reslice: trilinear"
    )


def test_a_data_release_resolves_the_pipeline_and_its_tool() -> None:
    record = {
        "software_mentions": [],
        "data_release": {"releases": [{"dataset": "ABCD Study", "release": "4.0"}]},
    }
    out = interpret(_answer("none", pipeline="none"), record, TEXT)
    pipe = out["resolved_pipeline"]
    assert (pipe["value"], pipe["provenance"], pipe["dataset_ids"]) == (
        "abcd_daic",
        "via data release",
        ["abcd_4_0"],
    )
    tool = out["realignment_tool"]
    assert tool["value"] == "afni" and tool["kb_confirmation"]["basis"] == "pipeline_default"
    assert tool["kb_confirmation"]["program"] == "3dvolreg"
    # a release-specific alias the model gives as the pipeline
    out = interpret(_answer("none", pipeline="HCP S1200"), {"software_mentions": []}, TEXT)
    assert out["resolved_pipeline"]["value"] == "hcp_minimal"
    assert out["resolved_pipeline"]["provenance"] == "via data release"
    # an unlisted release resolves to nothing
    record["data_release"]["releases"][0]["release"] = "2.0"
    assert (
        interpret(_answer("none", pipeline="none"), record, TEXT)["resolved_pipeline"]["kb"]
        is False
    )


def test_a_kb_pipeline_governs_a_tool_the_model_names_against_it() -> None:
    """2026-11-09: CONN documents SPM at every version and offers no choice; a model answer of "fsl"
    is kept as as_answered and the KB's program stands."""
    out = interpret(_answer("fsl", pipeline="conn"), _record(), TEXT)
    tool = out["realignment_tool"]
    assert (tool["value"], tool["provenance"], tool["as_answered"]) == (
        "spm",
        "INFERRED_DEFAULT",
        "fsl",
    )


def _cpac_record(stated: str | None = None, inferred: tuple[str, ...] = ()) -> dict[str, Any]:
    version: dict[str, Any] = {
        "extraction": {"status": "EXTRACTED", "value": stated}
        if stated
        else {"status": "MISSING_FROM_PAPER"},
        "inference": {"status": "NOT_APPLICABLE"}
        if stated
        else (
            {
                "status": "INFERRED_DEFAULT",
                "value": inferred[0],
                "alternative_inferences": [{"value": v} for v in inferred[1:]],
            }
            if inferred
            else {"status": "LEFT_MISSING"}
        ),
    }
    return {
        "software_mentions": [],
        "preprocessing": {
            "base_pipeline": {
                "extraction": {
                    "status": "EXTRACTED",
                    "value": {"name": "C-PAC", "version": version},
                }
            }
        },
    }


def test_a_configurable_pipelines_default_is_the_models_never_the_kbs() -> None:
    out = interpret(
        _answer("none", pipeline="C-PAC"), _cpac_record(inferred=("1.8.7", "1.8.6")), TEXT
    )
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_MODEL"
    assert tool["model_reason"] == "pipeline default; the pipeline lets the user choose"
    assert (tool["value"], tool["program"], tool["options"]) == (
        "afni",
        "3dvolreg",
        ["3dvolreg", "mcflirt"],
    )
    assert "kb_confirmation" not in tool
    # the method arm is never filled from it
    pf = _method_pf(fill_method_arm(_prep(_method("missing"), None), out))
    assert pf.inference.status == "LEFT_MISSING"
    rendered = render.to_report(_prep(_method("missing"), None), resolution=out)
    assert (
        "afni → 3dvolreg   [pipeline default; the pipeline lets the user choose; options: 3dvolreg, mcflirt]"
        in rendered
    )


@pytest.mark.parametrize(
    ("record", "versions"),
    [
        (_cpac_record(inferred=("0.3.9.1", "0.3.9")), ["0.3.9.1", "0.3.9"]),
        (_cpac_record(stated="0.4.0"), ["0.4.0"]),  # never released: placed in its range by the KB
        (_cpac_record(stated="1.0.0"), ["1.0.0"]),
    ],
)
def test_a_version_that_offers_no_choice_is_kb_confirmed(
    record: dict[str, Any], versions: list[str]
) -> None:
    out = interpret(_answer("none", pipeline="C-PAC"), record, TEXT)
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_DEFAULT" and tool["versions"] == versions
    assert tool["kb_confirmation"]["program"] == "3dvolreg"


def test_programs_that_differ_across_the_versions_are_the_models() -> None:
    out = interpret(_answer("none", pipeline="HCP Pipelines"), {"software_mentions": []}, TEXT)
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_MODEL" and tool["model_reason"].startswith(
        "version-dependent"
    )


def test_a_hop_resolved_citation_that_states_the_tool_is_extracted_from_it() -> None:
    record = _cpac_record(inferred=("1.8.7",))
    record["second_hop"] = [
        {
            "status": "ok",
            "ref": "[49]",
            "fields": {
                "motion_correction.method": {
                    "extraction": {
                        "status": "EXTRACTED",
                        "value": {"verbatim": "3dvolreg"},
                        "spans": [{"text": "a synthetic cited sentence"}],
                    }
                }
            },
        }
    ]
    out = interpret(_answer("none", pipeline="C-PAC"), record, TEXT)
    tool = out["realignment_tool"]
    assert (tool["provenance"], tool["value"], tool["program"]) == ("EXTRACTED", "afni", "3dvolreg")
    assert tool["from_citation"]["ref"] == "[49]"
    assert "afni → 3dvolreg   [from a cited paper: [49]]" in render.to_report(
        _prep(_method("missing"), None), resolution=out
    )


def test_a_default_not_verified_across_the_versions_is_the_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fmri_defaults_kb

    from extractor_mvp import resolution_call

    def fake(pid: str, version: str, **_: Any) -> Any:
        return SimpleNamespace(
            program="3dvolreg",
            package="afni",
            stable_across_range=False,
            configurable=False,
            options=(),
            source="synthetic",
            choice_source="synthetic",
        )

    monkeypatch.setattr(fmri_defaults_kb, "realignment_tool_at", fake)
    pr = resolution_call.pipeline_realignment("cpac", ["0.3.9", "0.3.9.1"])
    assert pr is not None and pr["verified"] is False
    assert (
        resolution_call.pipeline_realignment("cpac", ["0.3.9.1"])["verified"] is True
    )  # one version
    out = interpret(
        _answer("none", pipeline="C-PAC"), _cpac_record(inferred=("0.3.9.1", "0.3.9")), TEXT
    )
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_MODEL" and "not verified" in tool["model_reason"]


@pytest.mark.parametrize("release", ["S900", "S1200"])
def test_an_hcp_release_resolves_into_the_flirt_range_as_kb_confirmed(release: str) -> None:
    """2026-11-09: the S900/S1200 manuals state Functional Pipeline v3.1, which the KB places in the
    FLIRT-based range (no choice): INFERRED_DEFAULT, not version-dependent. The release's version is
    the provider's, so it outranks a date-inferred version of the base pipeline."""
    record = {
        "software_mentions": [],
        "data_release": {"releases": [{"dataset": "Human Connectome Project", "release": release}]},
        "preprocessing": {
            "base_pipeline": {
                "extraction": {
                    "status": "EXTRACTED",
                    "value": {
                        "name": "HCP minimal preprocessing pipeline",
                        "version": {
                            "extraction": {"status": "MISSING_FROM_PAPER"},
                            "inference": {
                                "status": "INFERRED_DEFAULT",
                                "value": "v4.1.3",
                                "alternative_inferences": [],
                            },
                        },
                    },
                }
            }
        },
    }
    out = interpret(_answer("none", pipeline="HCP minimal preprocessing pipeline"), record, TEXT)
    tool = out["realignment_tool"]
    assert tool["provenance"] == "INFERRED_DEFAULT" and tool["versions"] == ["v3.1"]
    assert (tool["kb_confirmation"]["program"], tool["kb_confirmation"]["package"]) == (
        "FLIRT",
        "fsl",
    )
    # without the release, the date-inferred v4.1.3 is configurable: the model's
    del record["data_release"]
    out = interpret(_answer("none", pipeline="HCP minimal preprocessing pipeline"), record, TEXT)
    assert out["realignment_tool"]["provenance"] == "INFERRED_MODEL"


def test_a_hop_tools_answer_with_a_resolved_quote_is_extracted_from_the_cited_paper() -> None:
    """2026-11-09: the hop asks a deferred method as the step's tool; its answer lives in
    hop["tools"], and one whose quote resolved and holds the tool-shaped name is EXTRACTED [C]."""
    record = _cpac_record(inferred=("1.8.7",))
    answer = {
        "tool": "AFNI's 3dvolreg",
        "verbatim_quote": "a synthetic cited sentence",
        "quote_resolved": True,
        "tool_in_quote": True,
        "tool_shaped": True,
    }
    record["second_hop"] = [
        {"status": "ok", "ref": "34", "fields": {}, "tools": {"motion_correction.method": [answer]}}
    ]
    tool = interpret(_answer("none", pipeline="C-PAC"), record, TEXT)["realignment_tool"]
    assert (tool["provenance"], tool["value"], tool["program"], tool["from_citation"]["ref"]) == (
        "EXTRACTED",
        "afni",
        "3dvolreg",
        "34",
    )
    for key in ("quote_resolved", "tool_in_quote", "tool_shaped"):
        record["second_hop"][0]["tools"]["motion_correction.method"] = [{**answer, key: False}]
        tool = interpret(_answer("none", pipeline="C-PAC"), record, TEXT)["realignment_tool"]
        assert tool["provenance"] == "INFERRED_MODEL", key


# --- 2026-11-10: a wrapping pipeline's own realignment settings fill the sub-items -------------

_SPM12 = {
    "tool_id": "spm",
    "display_name": "SPM",
    "use": "preprocessing",
    "sentence": "Data were preprocessed in SPM12.",
}
_CONN = {"tool_id": "conn", "display_name": "CONN", "use": "preprocessing"}


def _run(tool: str, pipeline: str, *mentions: dict[str, Any], **items: SubItem) -> dict[str, Any]:
    return interpret(
        _answer(tool, pipeline=pipeline, **items), {"software_mentions": list(mentions)}, TEXT
    )


@pytest.mark.parametrize(
    "mentions",
    [(_CONN,), (_SPM12, _CONN)],
    ids=["conn_default_tool", "spm12_named_inside_conn"],
)
def test_conns_settings_fill_the_sub_items_set_or_inherited(
    mentions: tuple[dict[str, Any], ...],
) -> None:
    out = _run("spm", "conn", *mentions)
    assert out["tool_defaults"]["applied"] is True and out["tool_defaults"]["pipeline"] == "conn"
    items = out["sub_items"]
    ref = items["reference_scan"]
    # CONN sets rtm=0 itself: register to first, not SPM Realign's register to mean
    assert (ref["value"], ref["provenance"], ref["set_by"]) == (
        "register to first",
        "INFERRED_DEFAULT",
        "pipeline",
    )
    assert "conn_setup_preproc.m" in ref["source"] and "rtm=0" in ref["source"]
    interp = items["interpolation"]
    assert interp["value"] == "estimate: 2nd degree B-spline; reslice: 4th degree B-spline"
    assert interp["set_by"] == "inherited"
    # the CONN line that leaves the option unset, and the SPM line the default is read from
    assert "leaves eoptions.einterp unset" in interp["source"]
    assert "spm_defaults.m line 101" in interp["source"]
    assert "spm_defaults.m line 107" in interp["source"]
    assert items["similarity_metric"]["value"] == "least squares"
    assert "spm_cfg_realignunwarp.m line 507" in items["similarity_metric"]["source"]
    assert items["susceptibility_correction"]["provenance"] == "UNKNOWN"  # no setting for it


def test_conns_settings_do_not_apply_to_a_tool_conn_does_not_wrap() -> None:
    fsl = {"tool_id": "fsl", "display_name": "FSL", "use": "preprocessing"}
    out = _run("fsl", "conn", fsl, _CONN)
    assert out["tool_defaults"]["applied"] is False
    assert "is not the one conn wraps (spm)" in out["tool_defaults"]["reason"]
    assert out["sub_items"]["reference_scan"]["provenance"] == "UNKNOWN"


def test_a_stated_spm_version_the_defaults_are_not_documented_for_stops_the_inherited_fill() -> (
    None
):
    spm8 = {**_SPM12, "version": "8", "sentence": "Data were preprocessed in SPM8."}
    out = _run("spm", "conn", spm8, _CONN)
    assert out["tool_defaults"]["applied"] is False and "8" in out["tool_defaults"]["reason"]


def test_the_papers_own_quote_still_outranks_the_pipelines_setting() -> None:
    stated = SubItem(
        status="stated",
        value="first volume",
        quote="Volumes were realigned to the first volume with a synthetic tool.",
    )
    out = _run("spm", "conn", _CONN, reference_scan=stated)
    assert out["sub_items"]["reference_scan"]["provenance"] == "EXTRACTED"
    assert "set_by" not in out["sub_items"]["reference_scan"]


def test_a_setting_that_differs_across_versions_fills_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fmri_defaults_kb

    real = fmri_defaults_kb.realignment_settings

    def ranged(pipeline_id: str, version: str | None = None) -> dict[str, Any] | None:
        out = real(pipeline_id, version)
        assert out is not None
        out["reference_scan"] = {**out["reference_scan"], "value": None, "range": "synthetic"}
        return out

    monkeypatch.setattr(fmri_defaults_kb, "realignment_settings", ranged)
    out = _run("spm", "conn", _CONN)
    assert out["tool_defaults"]["applied"] is True
    assert out["sub_items"]["reference_scan"]["provenance"] == "UNKNOWN"
    assert out["sub_items"]["interpolation"]["provenance"] == "INFERRED_DEFAULT"


def test_fmriprep_wraps_fsl_and_its_settings_fill_what_holds_across_versions() -> None:
    fsl = {"tool_id": "fsl", "display_name": "FSL", "use": "preprocessing"}
    out = _run("fsl", "fmriprep", fsl, {"tool_id": "fmriprep", "display_name": "fMRIPrep"})
    assert (
        out["tool_defaults"]["applied"] is True and out["tool_defaults"]["pipeline"] == "fmriprep"
    )
    items = out["sub_items"]
    # the reference differs across fMRIPrep versions and no version is known: not filled
    assert items["reference_scan"]["provenance"] == "UNKNOWN"
    assert items["similarity_metric"]["value"].startswith("normalised correlation")
    assert items["similarity_metric"]["set_by"] == "inherited"
    assert items["interpolation"]["value"].startswith(
        "estimate: trilinear; reslice: not from MCFLIRT"
    )
