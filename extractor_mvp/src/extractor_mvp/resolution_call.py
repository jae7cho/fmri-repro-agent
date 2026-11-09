"""The resolution call (the author's item 1, 2026-11-09): one tool-calling model call after the
extraction that resolves the paper's pipeline and its realignment tool, replacing the lookup-based
motion inference (``motion_inference.infer_motion_method``, which matched whole KB names only).

Input: the base pipeline phrase, every software mention with its version, the motion method phrase
and quote, the data release if stated, and the KB index (one line per pipeline and tool id). Output:
``resolved_pipeline`` and ``realignment_tool`` (a KB id, free text, or none), a one-sentence basis,
and four motion sub-items (reference scan, interpolation, similarity metric, susceptibility
correction), each stated-with-quote, inferred-from-default, or unknown.

Provenance, decided by code after the call, never by the model:

* ``INFERRED_DEFAULT`` (KB-confirmed): the tool is a KB tool with a documented realignment program,
  and either the paper names that tool (a software mention with its tool id) or the resolved
  pipeline is a KB pipeline whose documented realignment program is that tool's at every listed
  version. The KB program and its source are recorded.
* ``INFERRED_MODEL``: anything the model said that the KB does not confirm. Rendered "inferred by the
  model, unconfirmed".
* ``EXTRACTED``: a sub-item stated in the paper whose quote resolves in the text.
* ``UNKNOWN``: nothing said.

The paper's own phrase stays the EXTRACTED value of ``motion_correction.method``; the resolution
travels beside it in the record (``resolution``). Only a method field that is MISSING or DEFERRED
gets its inference arm filled, and only when KB-confirmed (the provenance contract's
INFERRED_DEFAULT, basis ``derived``).
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from extractor_mvp.span_resolver import resolve_quote

PROMPT = """You resolve which preprocessing software and pipeline an fMRI paper used, from what the
extraction already found. Use the KB index below where an entry fits, answering with the id alone
(e.g. "spm"); otherwise answer in free text; answer "none" when nothing supports an answer.

Rules:
- realignment_tool is the program family that ESTIMATED between-volume head motion. A package the
  paper names for its preprocessing as a whole counts; so does the documented default of a named
  pipeline or toolbox (e.g. a toolbox that runs SPM's realignment). Motion parameters used as
  regressors, framewise displacement and censoring are not the realignment tool.
- "Co-registered" or "registered" volumes TO CORRECT FOR HEAD MOTION (to a reference volume of the
  same run) is motion correction, not coregistration. Coregistration aligns functional to anatomical.
- resolved_pipeline is the named pipeline or toolbox whose preprocessing the paper used, if any.
- basis: one sentence saying what in the inputs supports the two answers.
- Each motion sub-item is one of:
  - "stated": the paper says it; give the value and copy the sentence VERBATIM from the method quote
    or the software sentences below as the quote;
  - "inferred_from_default": the paper does not say it, but it follows from the documented default of
    the realignment tool or pipeline you resolved; give the value;
  - "unknown": neither.
  Sub-items: reference_scan (the volume realigned to), interpolation (the resampling interpolation),
  similarity_metric (the cost function of the estimation), susceptibility_correction (correction of
  susceptibility distortion or its interaction with motion, e.g. unwarping, field maps).

KB index (id: name):
{kb_index}

Base pipeline phrase: {base_pipeline}
Software mentions (name, version, use, sentence):
{software}
Motion method phrase: {motion_phrase}
Motion method quote: {motion_quote}
Data release: {data_release}
"""

SUB_ITEMS: tuple[str, ...] = (
    "reference_scan",
    "interpolation",
    "similarity_metric",
    "susceptibility_correction",
)


class SubItem(BaseModel):
    status: Literal["stated", "inferred_from_default", "unknown"]
    value: str | None = None
    quote: str | None = Field(default=None, description="verbatim, only when stated")


class ResolutionAnswer(BaseModel):
    resolved_pipeline: str = Field(description='a KB id, free text, or "none"')
    realignment_tool: str = Field(description='a KB id, free text, or "none"')
    basis: str
    reference_scan: SubItem
    interpolation: SubItem
    similarity_metric: SubItem
    susceptibility_correction: SubItem


def kb_index() -> tuple[dict[str, str], dict[str, str]]:
    """``(pipelines, tools)``: KB id -> display name."""
    from fmri_defaults_kb.io import load_pipeline_documents
    from fmri_defaults_kb.tools import load_tool_documents

    pipes = {pid: str(d.get("display_name") or pid) for pid, d in load_pipeline_documents().items()}
    tools = {tid: str(d.get("display_name") or tid) for tid, d in load_tool_documents().items()}
    return pipes, tools


def kb_id(value: str | None, ids: dict[str, str], kind: str) -> str | None:
    """The KB id an answer names, or None. The model may write the id as the index line wrote it
    ("tool spm"), the id alone, or a name ("SPM12", "Conn toolbox"): the index prefix is dropped,
    then the id is matched, then the KB's own recogniser (``recognize`` for a pipeline,
    ``recognize_tool`` for a tool) is asked. Never fuzzy beyond what those recognisers accept."""
    from fmri_defaults_kb import recognize, recognize_tool

    if value is None:
        return None
    v = re.sub(r"^(?:tool|pipeline)\s*[:\-]?\s*", "", value.strip(), flags=re.IGNORECASE).strip()
    if v in ids:
        return v
    if v.lower() in ids:
        return v.lower()
    try:
        found = recognize(v) if kind == "pipeline" else recognize_tool(v)
    except Exception:  # an unreadable name is no id
        found = None
    return found if found in ids else None


def _none(s: str | None) -> str | None:
    t = (s or "").strip()
    return None if not t or t.lower() in ("none", "null", "unknown", "n/a") else t


def _motion_inputs(prep: Any) -> tuple[str, str, str | None]:
    """The motion method's phrase and quote as the extraction left them, and its status."""
    step = next((s for s in prep.steps if getattr(s, "kind", None) == "motion_correction"), None)
    if step is None:
        return "none", "none", None
    ext = step.method.extraction
    if ext.status == "EXTRACTED":
        phrase = getattr(ext.value, "verbatim", None) or str(ext.value)
        return str(phrase), ext.spans[0].text, ext.status
    if ext.status == "DEFERRED_TO_CITATION":
        d = ext.deferrals[0]
        return f"deferred to {d.ref}", d.span.text, ext.status
    return "none", "none", ext.status


def build_prompt(record: dict[str, Any], prep: Any) -> str:
    pipes, tools = kb_index()
    index = "\n".join(
        [f"- {k} (pipeline): {v}" for k, v in sorted(pipes.items())]
        + [f"- {k} (tool): {v}" for k, v in sorted(tools.items())]
    )
    bp = getattr(prep.base_pipeline, "extraction", None)  # NotApplicable carries no extraction
    base = (
        getattr(getattr(bp, "value", None), "name", None)
        if bp is not None and bp.status == "EXTRACTED"
        else None
    )
    software = (
        "\n".join(
            f"- {m.get('display_name')} | version {m.get('version') or 'not stated'} | "
            f"{m.get('use') or ''} | {m.get('sentence') or m.get('use_quote') or ''}"
            for m in record.get("software_mentions") or []
        )
        or "none"
    )
    phrase, quote, _status = _motion_inputs(prep)
    releases = (record.get("data_release") or {}).get("releases") or []
    release = "; ".join(f"{r.get('dataset')} {r.get('release') or ''}".strip() for r in releases)
    return PROMPT.format(
        kb_index=index,
        base_pipeline=base or "none",
        software=software,
        motion_phrase=phrase,
        motion_quote=quote,
        data_release=release or "none",
    )


def _confirm(
    tool: str | None, pipeline: str | None, mentions: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """KB confirmation of the realignment tool (module docstring), or None."""
    from fmri_defaults_kb import realignment_program
    from fmri_defaults_kb.errors import KbError
    from fmri_defaults_kb.io import load_pipeline_documents

    if tool is None:
        return None
    try:
        rp = realignment_program(tool)
    except KbError:
        return None
    named = {m.get("tool_id") for m in mentions}
    if tool in named:
        return {
            "program": rp.program,
            "package": tool,
            "basis": "package_named",
            "source": rp.source,
        }
    doc = load_pipeline_documents().get(pipeline or "")
    ranges = ((doc or {}).get("realignment_tool") or {}).get("ranges") or []
    if ranges and all(r.get("package") == tool and r.get("stable_across_range") for r in ranges):
        return {
            "program": ranges[0]["program"],
            "package": tool,
            "basis": "pipeline_default",
            "pipeline": pipeline,
            "source": ranges[0]["source"],
        }
    return None


def interpret(answer: ResolutionAnswer, record: dict[str, Any], text: str) -> dict[str, Any]:
    """The stored record of one resolution call: the model's answers with code-assigned provenance."""
    pipes, tools = kb_index()
    pipeline = _none(answer.resolved_pipeline)
    tool = _none(answer.realignment_tool)
    pipe_id, tool_id = kb_id(pipeline, pipes, "pipeline"), kb_id(tool, tools, "tool")
    mentions = record.get("software_mentions") or []
    confirmed = _confirm(tool_id, pipe_id, mentions)
    out: dict[str, Any] = {
        "status": "ok",
        "resolved_pipeline": {
            "value": pipe_id or pipeline,
            "kb": pipe_id is not None,
            **({"as_answered": pipeline} if pipe_id and pipe_id != pipeline else {}),
        },
        "realignment_tool": {
            "value": tool_id or tool,
            "kb": tool_id is not None,
            **({"as_answered": tool} if tool_id and tool_id != tool else {}),
            "provenance": "INFERRED_DEFAULT"
            if confirmed
            else ("INFERRED_MODEL" if tool else "UNKNOWN"),
            **({"kb_confirmation": confirmed} if confirmed else {}),
        },
        "basis": answer.basis,
        "sub_items": {},
    }
    for name in SUB_ITEMS:
        item: SubItem = getattr(answer, name)
        entry: dict[str, Any] = {"status": item.status, "value": item.value}
        if item.status == "stated" and item.quote and resolve_quote(item.quote, text).span:
            entry.update(provenance="EXTRACTED", quote=item.quote)
        elif item.status == "stated":
            # a "stated" sub-item whose quote is not in the text is the model's, not the paper's
            entry.update(provenance="INFERRED_MODEL", quote_unresolved=item.quote)
        elif item.status == "inferred_from_default" and item.value:
            # the KB documents no sub-item defaults: a default the model names is unconfirmed
            entry["provenance"] = "INFERRED_MODEL"
        else:
            entry.update(provenance="UNKNOWN", value=None)
        out["sub_items"][name] = entry
    return out


def run_resolution(
    record: dict[str, Any], prep: Any, text: str, model: str, *, client: Any, meter: Any = None
) -> dict[str, Any]:
    """One metered call; never raises (a failed call is a state)."""
    from extractor_mvp.citation_hop import _create

    if meter is not None:
        meter.label = "resolution"
    try:
        answer = _create(client, model, build_prompt(record, prep), ResolutionAnswer)
    except Exception as exc:
        return {"status": "call_failed", "error": f"{type(exc).__name__}: {exc}"[:500]}
    return interpret(answer, record, text)


def fill_method_arm(prep: Any, resolution: dict[str, Any]) -> Any:
    """A MISSING or DEFERRED motion method gets the KB-confirmed program on its inference arm
    (INFERRED_DEFAULT, basis ``derived`` from the resolution call). An EXTRACTED method is never
    touched; a model-only answer never reaches the arm."""
    from fmri_repro.spec.provenance import BASIS_CEILINGS, DerivedBasis, InferredDefault

    from extractor_mvp.motion_inference import _term

    conf = ((resolution.get("realignment_tool") or {}).get("kb_confirmation")) or None
    step = next((s for s in prep.steps if getattr(s, "kind", None) == "motion_correction"), None)
    if conf is None or step is None:
        return prep
    if step.method.extraction.status not in ("MISSING_FROM_PAPER", "DEFERRED_TO_CITATION"):
        return prep
    basis = DerivedBasis(source_field_ids=["resolution_call"], note=conf["source"])
    step.method = step.method.model_copy(
        update={
            "inference": InferredDefault(
                value=_term(conf["program"]),
                basis=basis,
                confidence=BASIS_CEILINGS["derived"],
                alternative_inferences=[],
            )
        }
    )
    return prep
