"""The realignment tool's precedence (the author's rule, 2026-11-09 night 3). Synthetic records; no
model call."""

from __future__ import annotations

from typing import Any

import pytest

from extractor_mvp.reresolve import answer_from_stored, reresolve_record
from extractor_mvp.resolution_call import ResolutionAnswer, SubItem, interpret

TEXT = "Synthetic text."


def _answer(tool: str = "none", pipeline: str = "none") -> ResolutionAnswer:
    u = SubItem(status="unknown")
    return ResolutionAnswer(
        resolved_pipeline=pipeline,
        realignment_tool=tool,
        basis="synthetic",
        reference_scan=u,
        interpolation=u,
        similarity_metric=u,
        susceptibility_correction=u,
    )


def _record(
    phrase: str | None = None,
    mentions: list[dict[str, Any]] | None = None,
    hop_tool: str | None = None,
    status: str = "EXTRACTED",
) -> dict[str, Any]:
    if phrase is not None:
        ext: dict[str, Any] = {
            "status": "EXTRACTED",
            "value": {"verbatim": phrase},
            "spans": [{"text": f"Volumes were realigned with {phrase}."}],
        }
    else:
        ext = {"status": status}
    rec: dict[str, Any] = {
        "software_mentions": mentions or [],
        "preprocessing": {
            "steps": [
                {
                    "kind": "motion_correction",
                    "method": {"extraction": ext, "inference": {"status": "LEFT_MISSING"}},
                }
            ]
        },
    }
    if hop_tool:
        rec["second_hop"] = [
            {
                "status": "ok",
                "ref": "[9]",
                "fields": {},
                "tools": {
                    "motion_correction.method": [
                        {
                            "tool": hop_tool,
                            "verbatim_quote": "a cited sentence",
                            "quote_resolved": True,
                            "tool_in_quote": True,
                            "tool_shaped": True,
                        }
                    ]
                },
            }
        ]
    return rec


def _m(tool_id: str, use: str, fmri: str = "yes") -> dict[str, Any]:
    return {"tool_id": tool_id, "display_name": tool_id.upper(), "use": use, "fmri": fmri}


def _tool(rec: dict[str, Any], **kw: str) -> dict[str, Any]:
    return interpret(_answer(**kw), rec, TEXT)["realignment_tool"]


def test_a_program_the_paper_names_is_extracted_and_outranks_everything() -> None:
    t = _tool(_record("MCFLIRT", [_m("spm", "preprocessing")]), pipeline="conn", tool="spm")
    assert (t["provenance"], t["basis"], t["value"], t["program"]) == (
        "EXTRACTED",
        "program_named",
        "fsl",
        "MCFLIRT",
    )
    assert t["quote"] == "Volumes were realigned with MCFLIRT."
    assert t["conflicts"] == [
        "conflict: paper names MCFLIRT, package default spm Realign",
        "conflict: paper names MCFLIRT, pipeline default spm Realign",
    ]
    assert "kb_confirmation" not in t


def test_a_cited_program_outranks_a_package_and_a_pipeline() -> None:
    t = _tool(
        _record(
            None,
            [_m("spm", "preprocessing")],
            hop_tool="AFNI's 3dvolreg",
            status="DEFERRED_TO_CITATION",
        )
    )
    assert (t["provenance"], t["basis"], t["value"], t["program"]) == (
        "EXTRACTED",
        "cited_program",
        "afni",
        "3dvolreg",
    )
    assert t["conflicts"] == [
        "conflict: cited paper ([9]) names AFNI's 3dvolreg, package default spm Realign"
    ]


def test_a_package_named_for_the_step_outranks_the_pipeline_and_records_the_conflict() -> None:
    t = _tool(_record("SPM12"), pipeline="HCP Pipelines")
    assert (t["provenance"], t["basis"], t["value"], t["program"]) == (
        "INFERRED_DEFAULT",
        "package_named",
        "spm",
        "Realign",
    )
    assert t["conflicts"] == ["conflict: paper names SPM12, pipeline default FLIRT or MCFLIRT"]
    assert t["kb_confirmation"]["basis"] == "package_named"


@pytest.mark.parametrize(
    ("mentions", "expected"),
    [
        ([_m("ants", "transformation into MNI space")], None),  # another step's package
        (
            [_m("fsl", "resampling data to atlas space with head motion transforms")],
            None,
        ),  # APPLY role
        ([_m("spm", "realignment, unwarping, and coregistration")], "spm"),  # bound to the step
        (
            [_m("afni", "preprocessing"), _m("fsl", "PPI analyses")],
            "afni",
        ),  # a specific analysis is not "as a whole"
        ([_m("afni", "preprocessing"), _m("fsl", "preprocessing")], None),  # two: not attributable
        ([_m("spm", "fMRI data analysis")], "spm"),  # analysis as a whole
        ([_m("spm", "motion correction", fmri="no")], None),
        ([_m("spm", "motion correction"), _m("fsl", "preprocessing")], "spm"),  # step-bound first
        # two packages bound to the step: not attributable, and no fall-through to the preprocessing
        (
            [_m("spm", "motion correction"), _m("afni", "head motion"), _m("fsl", "preprocessing")],
            None,
        ),
    ],
)
def test_the_package_tier_reads_the_mentions_use(
    mentions: list[dict[str, Any]], expected: str | None
) -> None:
    t = _tool(_record("motion correction", mentions))
    assert (t.get("basis") == "package_named" and t["value"]) == (expected or False)


def test_the_pipeline_is_the_fallback_and_the_model_is_last() -> None:
    t = _tool(_record("motion correction"), pipeline="conn")
    assert (t["provenance"], t["kb_confirmation"]["basis"], t["value"]) == (
        "INFERRED_DEFAULT",
        "pipeline_default",
        "spm",
    )
    t = _tool(_record("motion correction"), tool="an in-house realigner")
    assert (t["provenance"], t["value"]) == ("INFERRED_MODEL", "an in-house realigner")
    assert _tool(_record("motion correction"))["provenance"] == "UNKNOWN"


def test_agreeing_lower_tiers_are_no_conflict() -> None:
    t = _tool(_record("motion correction", [_m("spm", "image processing")]), pipeline="conn")
    assert t["basis"] == "package_named" and "conflicts" not in t


def test_the_raw_answer_is_stored_and_a_stored_record_re_resolves() -> None:
    rec = _record("MCFLIRT")
    res = interpret(_answer(tool="spm", pipeline="conn"), rec, TEXT)
    assert (
        res["answer"]["realignment_tool"] == "spm" and res["answer"]["resolved_pipeline"] == "conn"
    )
    assert answer_from_stored(res).realignment_tool == "spm"
    # an older resolution without the raw answer is rebuilt from what it kept
    old = {k: v for k, v in res.items() if k != "answer"}
    assert answer_from_stored(old).resolved_pipeline == "conn"


def test_reresolve_resets_a_fill_and_refills_from_the_new_resolution() -> None:
    from test_motion_inference import _method, _prep

    prep = _prep(_method("deferred", ref="[9]"), None)
    rec = {
        "paper_id": "synthetic",
        "software_mentions": [_m("spm", "preprocessing")],
        "preprocessing": prep.model_dump(mode="json"),
    }
    step = next(s for s in rec["preprocessing"]["steps"] if s["kind"] == "motion_correction")
    step["method"]["inference"] = {
        "status": "INFERRED_DEFAULT",
        "value": {"verbatim": "MCFLIRT", "resolved": "mcflirt", "resolution": "resolved"},
        "basis": {"basis_type": "derived", "source_field_ids": ["resolution_call"], "note": "old"},
        "confidence": 0.7,
        "alternative_inferences": [],
    }
    rec["resolution"] = interpret(_answer(tool="fsl"), {**rec, "software_mentions": []}, TEXT)
    new = reresolve_record(rec, TEXT)
    m = next(s for s in new["preprocessing"]["steps"] if s["kind"] == "motion_correction")["method"]
    assert m["inference"]["status"] == "INFERRED_DEFAULT"
    assert m["inference"]["value"]["verbatim"] == "Realign"  # SPM named for the preprocessing
    assert new["resolution"]["realignment_tool"]["basis"] == "package_named"


def test_reresolve_clears_an_old_fill_the_new_resolution_does_not_confirm() -> None:
    from test_motion_inference import _method, _prep

    rec = {
        "paper_id": "synthetic",
        "software_mentions": [],
        "preprocessing": _prep(_method("deferred", ref="[9]"), None).model_dump(mode="json"),
    }
    step = next(s for s in rec["preprocessing"]["steps"] if s["kind"] == "motion_correction")
    step["method"]["inference"] = {
        "status": "INFERRED_DEFAULT",
        "value": {"verbatim": "MCFLIRT", "resolved": "mcflirt", "resolution": "resolved"},
        "basis": {"basis_type": "derived", "source_field_ids": ["resolution_call"], "note": "old"},
        "confidence": 0.7,
        "alternative_inferences": [],
    }
    rec["resolution"] = interpret(_answer(tool="an in-house realigner"), rec, TEXT)
    new = reresolve_record(rec, TEXT)
    m = next(s for s in new["preprocessing"]["steps"] if s["kind"] == "motion_correction")["method"]
    assert m["inference"] == {"status": "LEFT_MISSING", "reason": "deferred_to_citation"}
