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


CONFIGURABLE_WORDS = "pipeline default; the pipeline lets the user choose"


def _confirm(
    tool: str | None, pipeline: str | None, mentions: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """KB confirmation of a tool the paper names for its preprocessing (no KB pipeline), or None."""
    from fmri_defaults_kb import realignment_program
    from fmri_defaults_kb.errors import KbError

    if tool is None or pipeline is not None:
        return None
    try:
        rp = realignment_program(tool)
    except KbError:
        return None
    if tool in {m.get("tool_id") for m in mentions}:
        return {
            "program": rp.program,
            "package": tool,
            "basis": "package_named",
            "source": rp.source,
        }
    return None


def _release_version(record: dict[str, Any], pid: str) -> str | None:
    """The pipeline version a data release the paper uses states for ``pid`` (kb/datasets), if any:
    the provider applied that version to the release."""
    from fmri_defaults_kb import recognize_dataset

    for rel in (record.get("data_release") or {}).get("releases") or []:
        dataset = str(rel.get("dataset") or "").strip()
        m = recognize_dataset(dataset, rel.get("release")) if dataset else None
        if m is not None and m.pipeline_id == pid and m.pipeline_version:
            return m.pipeline_version
    return None


def pipeline_versions(record: dict[str, Any], pid: str, stated: str | None = None) -> list[str]:
    """The pipeline versions the paper's realignment could have run at, in order of evidence: the
    version the paper states for this pipeline; the version a data release it uses states (the
    provider applied it); the base pipeline's date-inferred version and its alternatives; else every
    listed version. A stated version the KB does not list is kept as written (the KB places it in
    its range: ``realignment_tool_at``)."""
    from fmri_defaults_kb import recognize
    from fmri_defaults_kb.io import load_pipeline_documents

    listed = [str(v["version"]) for v in load_pipeline_documents()[pid]["versions"]]
    bp = (record.get("preprocessing") or {}).get("base_pipeline") or {}
    ext = bp.get("extraction") or {}
    value: dict[str, Any] = ext["value"] if isinstance(ext.get("value"), dict) else {}
    same = bool(value) and recognize(str(value.get("name") or "")) == pid
    vf = value.get("version") or {}
    vext, vinf = vf.get("extraction") or {}, vf.get("inference") or {}
    if same and vext.get("status") == "EXTRACTED":
        stated = str(vext.get("value"))
    stated = stated or _release_version(record, pid)
    if stated:
        for v in listed:
            if v.lstrip("vV") == stated.strip().lstrip("vV"):
                return [v]
        return [stated.strip()]
    if same and vinf.get("status") == "INFERRED_DEFAULT":
        inferred = [str(vinf.get("value"))] + [
            str(a.get("value")) for a in vinf.get("alternative_inferences") or []
        ]
        return [v for v in inferred if v in listed] or listed
    return listed


def pipeline_realignment(pid: str, versions: list[str]) -> dict[str, Any] | None:
    """What the KB records for ``pid`` at ``versions``: the programs, whether any is configurable,
    the options, and whether the ranges are verified; None when the KB records nothing."""
    from fmri_defaults_kb import realignment_tool_at
    from fmri_defaults_kb.errors import KbError

    found = []
    for v in versions:
        try:
            rt = realignment_tool_at(pid, v)
        except KbError:
            rt = None
        if rt is not None:
            found.append(rt)
    if not found:
        return None
    return {
        "programs": sorted({(r.program, r.package) for r in found}),
        "configurable": any(r.configurable for r in found),
        "options": sorted({o for r in found for o in r.options}),
        "verified": all(r.stable_across_range for r in found) or len(versions) == 1,
        "source": found[0].source,
        "choice_source": next((r.choice_source for r in found if r.configurable), None),
        "versions": versions,
    }


def _hop_tool(record: dict[str, Any]) -> dict[str, Any] | None:
    """A realignment tool a citation hop read in a cited paper (motion_correction.method EXTRACTED
    there with a tool-shaped value): EXTRACTED [C] from that source."""
    from extractor_mvp.motion_guard import is_tool_shaped_frozen

    for hop in record.get("second_hop") or []:
        if hop.get("status") != "ok":
            continue
        pf = (hop.get("fields") or {}).get("motion_correction.method") or {}
        ext = pf.get("extraction") or {}
        if ext.get("status") != "EXTRACTED":
            continue
        value = ext.get("value")
        verbatim = value.get("verbatim") if isinstance(value, dict) else value
        if verbatim and is_tool_shaped_frozen(str(verbatim)):
            spans = ext.get("spans") or [{}]
            return {"value": str(verbatim), "ref": hop.get("ref"), "quote": spans[0].get("text")}
    return None


def _resolve_pipeline(
    pipeline: str | None, pipes: dict[str, str], record: dict[str, Any]
) -> tuple[str | None, str | None, dict[str, Any]]:
    """``(KB pipeline id, provenance, detail)``. The model's answer first: a KB pipeline name
    (provenance "pipeline name") or a release-specific dataset alias ("via data release"); then the
    paper's own data release (call R's dataset and release) through ``recognize_dataset``."""
    from fmri_defaults_kb import recognize_dataset, recognize_with_provenance

    pid = kb_id(pipeline, pipes, "pipeline")
    if pid is not None:
        found = recognize_with_provenance(pipeline or "")
        prov = found[1] if found is not None and found[0] == pid else "pipeline name"
        return pid, prov, {}
    for rel in (record.get("data_release") or {}).get("releases") or []:
        dataset = str(rel.get("dataset") or "").strip()
        if not dataset:
            continue
        m = recognize_dataset(dataset, rel.get("release"))
        if m is not None and m.pipeline_id in pipes:
            detail = {
                "dataset_ids": list(m.dataset_ids),
                "pipeline_version": m.pipeline_version,
                "source": m.source,
                "from": "data release",
            }
            return m.pipeline_id, m.provenance, detail
    return None, None, {}


def _stated_versions(
    tool_id: str, mentions: list[dict[str, Any]], tools: dict[str, str]
) -> set[str]:
    """The versions the paper states for ``tool_id``: a software mention's version, or the digits
    written after the package's name in a mention sentence ("SPM12", "SPM 8")."""
    out: set[str] = set()
    name = re.escape(tools.get(tool_id, tool_id))
    for m in mentions:
        if m.get("tool_id") != tool_id:
            continue
        if m.get("version"):
            out.add(str(m["version"]).strip().lstrip("vV"))
        for hit in re.finditer(rf"\b{name}\s?(\d+)\b", str(m.get("sentence") or ""), re.IGNORECASE):
            out.add(hit.group(1))
    return out


#: Sub-item -> the KB default keys that fill it.
_DEFAULT_KEYS: dict[str, tuple[str, ...]] = {
    "reference_scan": ("reference_scan",),
    "interpolation": ("interpolation_estimate", "interpolation_reslice"),
    "similarity_metric": ("cost_function",),
}


def _tool_defaults(
    confirmed: dict[str, Any] | None,
    pipe_id: str | None,
    mentions: list[dict[str, Any]],
    tools: dict[str, str],
) -> tuple[dict[str, Any] | None, str | None]:
    """The KB defaults that may fill sub-items, or ``(None, why not)``. Only for a tool the paper
    names with no KB pipeline wrapping it (a pipeline may override its tool's defaults), and not when
    the paper states a version the defaults are not documented for."""
    from fmri_defaults_kb import realignment_defaults

    if confirmed is None:
        return None, "no KB-confirmed realignment tool"
    if pipe_id is not None:
        return None, f"the tool runs inside {pipe_id}, whose own settings the KB does not record"
    if confirmed.get("basis") != "package_named":
        return None, "the tool is not named in the paper"
    defaults = realignment_defaults(confirmed["package"])
    if not defaults:
        return None, f"the KB records no defaults for {confirmed['package']}"
    documented = [str(v) for v in defaults.get("version_tokens") or []]
    stated = _stated_versions(confirmed["package"], mentions, tools)
    if documented and stated and not stated & set(documented):
        return None, (
            f"the paper states version {', '.join(sorted(stated))}; the defaults are documented for "
            f"{defaults.get('documented_for')}"
        )
    return defaults, None


def interpret(answer: ResolutionAnswer, record: dict[str, Any], text: str) -> dict[str, Any]:
    """The stored record of one resolution call: the model's answers with code-assigned provenance."""
    pipes, tools = kb_index()
    pipeline = _none(answer.resolved_pipeline)
    tool = _none(answer.realignment_tool)
    mentions = record.get("software_mentions") or []
    pipe_id, pipe_prov, pipe_detail = _resolve_pipeline(pipeline, pipes, record)
    tool_id = kb_id(tool, tools, "tool")
    confirmed = _confirm(tool_id, pipe_id, mentions)
    tool_entry: dict[str, Any] = {
        "value": tool_id or tool,
        "kb": tool_id is not None,
        **({"as_answered": tool} if tool_id and tool_id != tool else {}),
        "provenance": "INFERRED_DEFAULT"
        if confirmed
        else ("INFERRED_MODEL" if tool else "UNKNOWN"),
        **({"kb_confirmation": confirmed} if confirmed else {}),
    }
    hop = _hop_tool(record)
    if hop is not None:
        # a hop-resolved citation states the tool: the cited paper's words, [C]
        tool_entry = {
            "value": hop["value"],
            "kb": False,
            "provenance": "EXTRACTED",
            "from_citation": hop,
        }
        confirmed = None
    elif pipe_id is not None:
        pr = pipeline_realignment(
            pipe_id, pipeline_versions(record, pipe_id, pipe_detail.get("pipeline_version"))
        )
        if pr is not None:
            (program, package), n = pr["programs"][0], len(pr["programs"])
            base = {"kb": True, "pipeline": pipe_id, "versions": pr["versions"]}
            if n > 1:
                tool_entry = {
                    **base,
                    "value": ", ".join(f"{pk}.{pg}" for pg, pk in pr["programs"]),
                    "provenance": "INFERRED_MODEL",
                    "model_reason": "version-dependent: the pipeline's program differs across the versions that apply",
                }
            elif pr["configurable"]:
                # 2026-11-09 (the author's rule): a configurable pipeline's default is never INFERRED_DEFAULT
                tool_entry = {
                    **base,
                    "value": package,
                    "program": program,
                    "provenance": "INFERRED_MODEL",
                    "model_reason": CONFIGURABLE_WORDS,
                    "options": pr["options"],
                    "choice_source": pr["choice_source"],
                }
            elif not pr["verified"]:
                tool_entry = {
                    **base,
                    "value": package,
                    "program": program,
                    "provenance": "INFERRED_MODEL",
                    "model_reason": "pipeline default, not verified across the versions that apply",
                }
            else:
                confirmed = {
                    "program": program,
                    "package": package,
                    "basis": "pipeline_default",
                    "pipeline": pipe_id,
                    "source": pr["source"],
                }
                tool_entry = {
                    **base,
                    "value": package,
                    **({"as_answered": tool} if tool and tool != package else {}),
                    "provenance": "INFERRED_DEFAULT",
                    "kb_confirmation": confirmed,
                }
    out: dict[str, Any] = {
        "status": "ok",
        "resolved_pipeline": {
            "value": pipe_id or pipeline,
            "kb": pipe_id is not None,
            **({"provenance": pipe_prov} if pipe_id else {}),
            **({"as_answered": pipeline} if pipe_id and pipe_id != pipeline else {}),
            **pipe_detail,
        },
        "realignment_tool": tool_entry,
        "basis": answer.basis,
        "sub_items": {},
    }
    defaults, why_not = _tool_defaults(confirmed, pipe_id, mentions, tools)
    if why_not is not None:
        out["tool_defaults"] = {"applied": False, "reason": why_not}
    else:
        assert defaults is not None
        out["tool_defaults"] = {"applied": True, "documented_for": defaults.get("documented_for")}
    for name in SUB_ITEMS:
        item: SubItem = getattr(answer, name)
        entry: dict[str, Any] = {"status": item.status, "value": item.value}
        kb_parts = [defaults[k] for k in _DEFAULT_KEYS.get(name, ()) if defaults and k in defaults]
        if item.status == "stated" and item.quote and resolve_quote(item.quote, text).span:
            entry.update(provenance="EXTRACTED", quote=item.quote)
        elif kb_parts:
            # 2026-11-09 (the author's item 3): the tool's documented default, with its source
            keys = [k for k in _DEFAULT_KEYS[name] if defaults and k in defaults]
            value = (
                kb_parts[0]["value"]
                if len(kb_parts) == 1
                else "; ".join(
                    f"{k.split('_')[-1]}: {defaults[k]['value']}" for k in keys if defaults
                )
            )
            entry.update(
                provenance="INFERRED_DEFAULT",
                value=value,
                source=" | ".join(str(part["source"]) for part in kb_parts),
                **({"model_said": item.value} if item.value else {}),
            )
        elif item.status == "stated":
            # a "stated" sub-item whose quote is not in the text is the model's, not the paper's
            entry.update(provenance="INFERRED_MODEL", quote_unresolved=item.quote)
        elif item.status == "inferred_from_default" and item.value:
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
