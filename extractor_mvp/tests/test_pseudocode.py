"""The reconstructed-preprocessing renderer (2026-11-09). Synthetic records only: no paper text, no
model call."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

from extractor_mvp.coverage_extractor import SpatialExtraction, TemporalVolumeExtraction
from extractor_mvp.pseudocode import COMMENT_MAX, clip, render_pseudocode, report_block

_spec = importlib.util.spec_from_file_location(
    "_cov_for_pseudocode", Path(__file__).with_name("test_coverage_expansion.py")
)
assert _spec and _spec.loader
cov = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cov)

_METHODS = {
    "found_via": "header_match",
    "matched_header": "Methods",
    "start_offset": 0,
    "end_offset": 100,
    "slice_ratio": 0.1,
    "ended_at": None,
    "suspicious": False,
    "fallback_reason": None,
}


def _step(record: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(s for s in record["preprocessing"]["steps"] if s["kind"] == kind)


def _deferred(field_id: str, ref: str) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "extraction": {
            "status": "DEFERRED_TO_CITATION",
            "deferrals": [
                {
                    "ref": ref,
                    "span": {"start": 0, "end": 5, "text": "a synthetic deferral"},
                    "target_kind": "paper",
                }
            ],
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {"status": "LEFT_MISSING", "reason": "deferred_to_citation"},
    }


def _record() -> dict[str, Any]:
    """One synthetic record carrying every tag."""
    prep = cov._run(
        spatial=SpatialExtraction(
            smoothing_fwhm_mm=cov._ex("8", cov._S["smooth"]),  # unverifiable -> checker-supplied
            smoothing_kernel_type=cov._ex("gaussian", cov._S["smooth"]),  # [E]
        ),
        temporal=TemporalVolumeExtraction(
            despike_performed=cov._ex("no", cov._S["no_smooth"]),  # [x]
        ),
    )
    rec: dict[str, Any] = {
        "paper_id": "synthetic_2099",
        "status": "success",
        "methods": _METHODS,
        "preprocessing": prep.model_dump(mode="json"),
        "diagnostics": [
            {
                "field": "spatial_smoothing.fwhm_mm",
                "failure_reason": "value_unsupported_by_quote",
                "raw_value": "8",
                "raw_quote": cov._S["smooth"],
            }
        ],
        "verifier": {
            "status": "ok",
            "fields": {
                "spatial_smoothing.fwhm_mm": {
                    "verdict": "wrong",
                    "better_value": "6",
                    "relied_on": cov._S["smooth"],
                }
            },
        },
        "citing_software": [{"display_name": "SYNTHTOOL", "version": "1.2", "kept": True}],
        "data_release": {"releases": [{"dataset": "SYNTH", "release": "3.0"}]},
    }
    # [D]: the motion method missing, its arm filled from the KB through the resolution call
    _step(rec, "motion_correction")["method"] = {
        "field_id": "method",
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {
            "status": "INFERRED_DEFAULT",
            "value": {"verbatim": "Realign", "resolved": "spm_realign", "resolution": "resolved"},
            "basis": {
                "basis_type": "derived",
                "source_field_ids": ["resolution_call"],
                "note": "a synthetic KB source",
            },
            "confidence": 0.7,
            "alternative_inferences": [],
        },
    }
    rec["resolution"] = {
        "status": "ok",
        "resolved_pipeline": {"value": None, "kb": False},
        "realignment_tool": {
            "value": "spm",
            "kb": True,
            "provenance": "INFERRED_DEFAULT",
            "kb_confirmation": {
                "program": "Realign",
                "package": "spm",
                "basis": "package_named",
                "source": "a synthetic KB source",
            },
        },
        "basis": "synthetic",
        "sub_items": {
            "reference_scan": {
                "status": "stated",
                "value": "first",
                "provenance": "EXTRACTED",
                "quote": "realigned to the first volume",
            },
            "interpolation": {
                "status": "inferred_from_default",
                "value": "spline",
                "provenance": "INFERRED_MODEL",
            },
            "similarity_metric": {
                "status": "unknown",
                "value": "least squares",
                "provenance": "INFERRED_DEFAULT",
                "source": "a synthetic KB default source",
            },
            "susceptibility_correction": {
                "status": "unknown",
                "value": None,
                "provenance": "UNKNOWN",
            },
        },
    }
    # [C]: one deferral the citation hop read in the cited paper, one not resolved
    tf = _step(rec, "temporal_filtering")
    tf["filter_type"] = _deferred("filter_type", "Smith 2000")
    tf["order"] = _deferred("order", "Jones 2001")
    rec["second_hop"] = [
        {
            "status": "ok",
            "ref": "Smith 2000",
            "fields": {
                "temporal_filtering.filter_type": {
                    "field_id": "filter_type",
                    "extraction": {
                        "status": "EXTRACTED",
                        "value": {
                            "verbatim": "butterworth",
                            "resolved": None,
                            "resolution": "unrecognized",
                        },
                        "spans": [{"start": 0, "end": 10, "text": "a synthetic cited sentence"}],
                        "confidence": 0.8,
                    },
                    "inference": {"status": "NOT_APPLICABLE"},
                }
            },
        }
    ]
    return rec


def _line(code: str, kind: str) -> str:
    return next(ln for ln in code.splitlines() if ln.startswith(f"{kind}("))


def test_every_tag_appears_where_it_belongs() -> None:
    code = render_pseudocode(_record())
    assert code is not None
    motion = _line(code, "motion_correction")
    assert 'method="Realign" [D]' in motion and "tool=spm.Realign [D]" in motion
    assert 'reference_scan="first" [E]' in motion
    assert 'interpolation="spline" [M]' in motion
    assert 'similarity_metric="least squares" [D]' in motion
    assert "susceptibility_correction=? [?]" in motion
    smooth = _line(code, "spatial_smoothing")
    assert 'kernel_type="gaussian" [E]' in smooth
    assert 'fwhm_mm="6" [M]' in smooth  # checker-supplied
    tf = _line(code, "temporal_filtering")
    assert 'filter_type="butterworth" [C]' in tf
    assert 'order=see("Jones 2001") [C]' in tf
    assert _line(code, "despike") == f"despike()  [x]  # «{clip(cov._S['no_smooth'])}»"
    for tag in ("E", "D", "M", "C", "?", "x"):
        assert f"[{tag}]" in code, tag


def test_every_argument_is_tagged_and_comments_are_clipped() -> None:
    code = render_pseudocode(_record())
    assert code is not None
    for ln in code.splitlines():
        if not ln or ln.startswith("#"):
            continue
        call, _, comment = ln.partition("  # ")
        inner = call[call.index("(") + 1 : call.rindex(")")]
        if inner and inner != "...":
            for arg in re.split(r",\s(?=\w+=)", inner):
                assert re.search(r"\[(E|D|M|C|\?|x)\]$", arg.strip()), arg
        assert len(comment) <= COMMENT_MAX + 40  # a prefix ("KB: ", a ref) plus a clipped quote
    assert clip("x" * 200) == "x" * (COMMENT_MAX - 1) + "…"


def test_the_header_and_footer() -> None:
    code = render_pseudocode(_record())
    assert code is not None
    lines = code.splitlines()
    assert lines[0] == "# Reconstructed preprocessing — synthetic_2099"
    assert "# tools: SYNTHTOOL 1.2" in lines
    assert "# data release: SYNTH 3.0" in lines
    assert any(ln.startswith("# order: ") for ln in lines)
    assert any(ln.startswith("# Mandatory rows: 14") for ln in lines)


def test_unexamined_fields_are_left_out_not_shown_as_not_reported() -> None:
    code = render_pseudocode(_record())
    assert code is not None
    # motion_correction's never-examined fields (not_targeted_by_mvp) are absent
    assert "nonrigid=" not in _line(code, "motion_correction")


def test_a_step_with_nothing_reported_is_one_line() -> None:
    code = render_pseudocode(_record())
    assert code is not None
    assert _line(code, "ica_denoise") == "ica_denoise(...)  [?]  # nothing reported for this step"


def test_template_order_is_said_and_streams_or_variants_are_noted() -> None:
    rec = _record()
    rec["preprocessing"]["step_order_source"] = "template"
    code = render_pseudocode(rec)
    assert code is not None and "# order: template order (the paper does not state one" in code
    # the checking pass reports two variants and the record has no applies_to: one block, a note
    rec["multiple_pipelines"] = {
        "V": {
            "pipeline_variant_count": {
                "field_id": "pipeline_variant_count",
                "extraction": {"status": "EXTRACTED", "value": 2, "spans": [], "confidence": 0.8},
                "inference": {"status": "NOT_APPLICABLE"},
            }
        }
    }
    code = render_pseudocode(rec)
    assert code is not None and "# note: the paper describes 2 preprocessing variants" in code
    # a record whose steps carry applies_to renders one block per stream
    steps = rec["preprocessing"]["steps"]
    for i, step in enumerate(steps):
        step["applies_to"] = "stream A" if i % 2 == 0 else "stream B"
    code = render_pseudocode(rec)
    assert code is not None
    assert "# --- stream: stream A" in code and "# --- stream: stream B" in code


def test_the_report_block_is_appended_and_a_stop_report_has_none() -> None:
    rec = _record()
    block = report_block(rec)
    assert block.startswith("\n## Reconstructed preprocessing\n\n```text\n")
    assert report_block({"paper_id": "x", "status": "not_fmri"}) == ""
    json.dumps(rec)  # the synthetic record is a stored-record shape


def test_render_record_appends_the_block_after_every_existing_section() -> None:
    from extractor_mvp.full_report import render_record

    rec = _record()
    out = render_record(rec)
    assert out.endswith(report_block(rec))
    assert out.index("## COBIDAS D.3 coverage") < out.index("## Reconstructed preprocessing")


def test_an_empty_value_renders_as_none_not_as_a_string() -> None:
    from types import SimpleNamespace

    from extractor_mvp.pseudocode import _literal

    assert _literal(None) == "none"
    assert _literal(SimpleNamespace(verbatim="None")) == "none"
    assert _literal(SimpleNamespace(verbatim="fsl_fast")) == '"fsl_fast"'


def test_a_configurable_default_is_m_and_a_cited_tool_is_c() -> None:
    rec = _record()
    rec["resolution"]["realignment_tool"] = {
        "value": "afni",
        "program": "3dvolreg",
        "provenance": "INFERRED_MODEL",
        "model_reason": "pipeline default; the pipeline lets the user choose",
    }
    code = render_pseudocode(rec)
    assert code is not None and "tool=afni.3dvolreg [M]" in _line(code, "motion_correction")
    rec["resolution"]["realignment_tool"] = {
        "value": "3dvolreg",
        "provenance": "EXTRACTED",
        "from_citation": {"ref": "[49]", "quote": "a synthetic cited sentence"},
    }
    code = render_pseudocode(rec)
    assert code is not None and 'tool="3dvolreg" [C]' in _line(code, "motion_correction")
