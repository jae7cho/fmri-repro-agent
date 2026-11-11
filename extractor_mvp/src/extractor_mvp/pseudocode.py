"""The reconstructed preprocessing as pseudo-code (the author's request of 2026-11-09), rendered from a
stored record with no model call.

One line per step in execution order: the record's step order, which is the paper's where it states
one (``step_order_source``), else template order with a comment saying so. Function-call syntax with
named arguments; every argument carries a tag:

* ``[E]`` quote-backed: the paper's value, extracted with a resolved quote;
* ``[D]`` the KB default of the resolved tool or pipeline, with its source;
* ``[M]`` a model inference, unconfirmed: the resolution call's model-only answers and values the
  checking pass supplied (``rechecks.checker_supplied``);
* ``[C]`` from a cited paper: a value the citation hop read in the cited paper, a prior-publication
  inference, or a deferral not yet resolved (``see("<ref>")``);
* ``[?]`` not reported (including values the extraction could not verify);
* ``[x]`` stated not performed: the whole step renders as one line.

Fields the extractor never examined (``not_targeted_by_mvp``) are left out rather than shown as
``[?]``, so a reader is not told the paper is silent where nothing looked. Each line's comment
carries a clipped quote (80 characters at most) or the KB source. The header gives the pipeline, the
tool versions and the data release; the footer the mandatory-row count of the COBIDAS section.
"""

from __future__ import annotations

import json
from typing import Any

from extractor_mvp.render import (
    DEFERRED_TO_CITATION,
    EXTRACTED,
    INFERRED_DEFAULT,
    FieldRow,
    _fmt_value,
    flatten,
    to_cobidas_coverage,
)

TAGS: dict[str, str] = {
    "E": "quote-backed",
    "D": "KB default of the resolved tool, with source; for the program, [D: how the KB verified it]",
    "M": "model inference, unconfirmed",
    "C": "from a cited paper",
    "?": "not reported",
    "x": "stated not performed",
}
COMMENT_MAX = 80
#: Reasons that mean the extractor never looked: such a field is omitted, never shown as [?].
UNEXAMINED = ("not_targeted_by_mvp", "field_not_in_schema_version")
MOTION_SUB_ITEMS = (
    "reference_scan",
    "interpolation",
    "similarity_metric",
    "susceptibility_correction",
)


def _clean(text: str) -> str:
    """Drop GROBID's inline citation delimiters (span_resolver.CITATION_OPEN / CITATION_CLOSE)."""
    from extractor_mvp.span_resolver import CITATION_CLOSE, CITATION_OPEN

    return text.replace(CITATION_OPEN, "").replace(CITATION_CLOSE, "")


def clip(text: str | None, limit: int = COMMENT_MAX) -> str:
    flat = " ".join(_clean(text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def _literal(value: Any) -> str:
    if value is None or (hasattr(value, "verbatim") and value.verbatim in (None, "None")):
        return "none"  # an empty value (a KB default that is "no method"), never the string "None"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:g}" if isinstance(value, float) else str(value)
    if (
        isinstance(value, (list, tuple))
        and value
        and all(isinstance(v, (int, float)) for v in value)
    ):
        return "[" + ", ".join(_literal(v) for v in value) + "]"
    if isinstance(value, (list, tuple)):
        text = ", ".join(str(getattr(v, "verbatim", v)) for v in value)
    elif hasattr(value, "verbatim"):
        text = str(value.verbatim)
    elif isinstance(value, str):
        text = value
    else:
        text = _fmt_value(value)
    return '"' + _clean(text).replace('"', "'") + '"'


def _hop_values(record: dict[str, Any]) -> dict[str, tuple[Any, str, str | None]]:
    """``dotted path -> (value, cited ref, quote)`` for every field a citation hop read in a cited
    paper with a quote."""
    out: dict[str, tuple[Any, str, str | None]] = {}
    for hop in record.get("second_hop") or []:
        if hop.get("status") != "ok":
            continue
        for path, pf in (hop.get("fields") or {}).items():
            ext = (pf or {}).get("extraction") or {}
            if ext.get("status") == "EXTRACTED" and path not in out:
                spans = ext.get("spans") or [{}]
                value = ext.get("value")
                if isinstance(value, dict) and "verbatim" in value:
                    value = value["verbatim"]
                out[path] = (value, str(hop.get("ref") or ""), spans[0].get("text"))
    return out


class _Arg:
    def __init__(
        self,
        name: str,
        value: str,
        tag: str,
        comment: str | None = None,
        detail: str | None = None,
    ) -> None:
        self.name, self.value, self.tag, self.comment = name, value, tag, comment
        self.detail = detail  # 2026-11-11: printed inside the bracket, e.g. [D: script_at_tag]

    def text(self) -> str:
        inner = f"{self.tag}: {self.detail}" if self.detail else self.tag
        return f"{self.name}={self.value} [{inner}]"


def _kb_verification(resolution: dict[str, Any] | None) -> str | None:
    """How the KB verified the realignment program the resolution confirmed (2026-11-11), read
    from the KB at render time: the pipeline range's ``verification`` when a pipeline gave the
    program (every range naming that program when the version is not known, joined when they
    differ), else the package's own entry. None when nothing is confirmed or the KB has no entry."""
    from fmri_defaults_kb import realignment_program, realignment_tool_at
    from fmri_defaults_kb.errors import KbError
    from fmri_defaults_kb.io import load_pipeline_documents

    tool = (resolution or {}).get("realignment_tool") or {}
    conf = tool.get("kb_confirmation") or None
    if not conf:
        return None
    try:
        pid = conf.get("pipeline")
        if pid:
            version = ((resolution or {}).get("resolved_pipeline") or {}).get("pipeline_version")
            if version:
                found = realignment_tool_at(pid, str(version))
                return found.verification if found is not None else None
            doc = load_pipeline_documents().get(pid) or {}
            kinds = sorted(
                {
                    str(r.get("verification") or "unverified")
                    for r in (doc.get("realignment_tool") or {}).get("ranges") or []
                    if r.get("program") == conf.get("program")
                }
            )
            return " / ".join(kinds) or None
        return realignment_program(str(conf["package"])).verification
    except (KbError, KeyError):
        return None


def _row_arg(
    row: FieldRow,
    name: str,
    supplied: dict[str, dict[str, Any]],
    hops: dict[str, tuple[Any, str, str | None]],
) -> _Arg | None:
    if row.path in supplied:
        entry = supplied[row.path]
        return _Arg(
            name,
            _literal(entry["value"]),
            "M",
            f"checker-supplied «{clip(entry.get('quote'), 60)}»",
        )
    if row.state == EXTRACTED:
        return _Arg(name, _literal(row.value), "E", f"«{clip(row.span_text)}»")
    if row.state == INFERRED_DEFAULT:
        note = getattr(row.basis, "note", None) or getattr(row.basis, "citation", None)
        if row.basis_type == "prior_publication":
            return _Arg(name, _literal(row.value), "C", clip(note))
        return _Arg(name, _literal(row.value), "D", f"KB: {clip(note)}" if note else "KB default")
    if row.path in hops:
        value, ref, quote = hops[row.path]
        return _Arg(name, _literal(value), "C", f"{clip(ref, 30)} «{clip(quote, 45)}»")
    if row.state == DEFERRED_TO_CITATION:
        refs = _clean(", ".join(row.deferral_refs or []) or "unspecified").replace('"', "'")
        return _Arg(name, f'see("{refs}")', "C", None)
    if (row.left_missing_reason or "").split(":", 1)[0] in UNEXAMINED:
        return None
    return _Arg(name, "?", "?", None)


def _motion_args(resolution: dict[str, Any] | None) -> tuple[list[_Arg], set[str]]:
    """The resolution call's realignment tool and sub-items as arguments, and the sub-item names it
    covers (which then replace the never-examined motion fields)."""
    if not resolution or resolution.get("status") != "ok":
        return [], set()
    args: list[_Arg] = []
    tool = resolution.get("realignment_tool") or {}
    conf = tool.get("kb_confirmation")
    conflicts = "; ".join(tool.get("conflicts") or [])
    tail = f"; {conflicts}" if conflicts else ""
    if tool.get("basis") == "program_named":
        q = f"«{clip(tool.get('quote'), 60)}»" if tool.get("quote") else "named in the paper"
        args.append(_Arg("tool", f"{tool['value']}.{tool['program']}", "E", q + tail))
    elif tool.get("from_citation"):
        hop = tool["from_citation"]
        val = (
            f"{tool['value']}.{tool['program']}" if tool.get("program") else _literal(tool["value"])
        )
        args.append(
            _Arg(
                "tool",
                val,
                "C",
                f"{clip(str(hop.get('ref')), 30)} «{clip(hop.get('quote'), 45)}»" + tail,
            )
        )
    elif conf:
        args.append(
            _Arg(
                "tool",
                f"{conf['package']}.{conf['program']}",
                "D",
                f"KB: {clip(conf.get('source'))}" + tail,
                detail=_kb_verification(resolution),
            )
        )
    elif tool.get("model_reason"):
        prog = (
            f"{tool['value']}.{tool['program']}" if tool.get("program") else _literal(tool["value"])
        )
        args.append(_Arg("tool", prog, "M", clip(str(tool["model_reason"])) + tail))
    elif tool.get("value"):
        args.append(_Arg("tool", _literal(tool["value"]), "M", "resolution call" + tail))
    else:
        args.append(_Arg("tool", "?", "?"))
    for name in MOTION_SUB_ITEMS:
        item = (resolution.get("sub_items") or {}).get(name) or {}
        prov = item.get("provenance")
        if prov == "EXTRACTED":
            args.append(
                _Arg(name, _literal(item.get("value")), "E", f"«{clip(item.get('quote'))}»")
            )
        elif prov == "INFERRED_DEFAULT":
            # 2026-11-09: the tool's documented default from the KB, with its source
            args.append(
                _Arg(name, _literal(item.get("value")), "D", f"KB: {clip(item.get('source'))}")
            )
        elif prov == "INFERRED_MODEL":
            args.append(_Arg(name, _literal(item.get("value")), "M", "resolution call"))
        else:
            args.append(_Arg(name, "?", "?"))
    return args, set(MOTION_SUB_ITEMS)


def _step_line(
    step: Any,
    rows: list[FieldRow],
    supplied: dict[str, dict[str, Any]],
    hops: dict[str, tuple[Any, str, str | None]],
    resolution: dict[str, Any] | None,
    applied: dict[str, dict[str, str]] | None = None,
) -> str:
    kind = step.kind
    mine = [r for r in rows if r.group == kind]
    performed = next((r for r in mine if r.path == f"{kind}.performed"), None)
    if performed is not None and performed.state == EXTRACTED and performed.value is False:
        return f"{kind}()  [x]  # «{clip(performed.span_text)}»"
    args: list[_Arg] = []
    covered: set[str] = set()
    if kind == "motion_correction":
        extra, covered = _motion_args(resolution)
    else:
        extra = []
    for r in mine:
        name = r.path.split(".", 1)[1] if "." in r.path else r.path
        if r.path == f"{kind}.performed" and r.state == EXTRACTED and r.value is True:
            continue  # the call itself says the step was performed
        if name in covered:
            continue  # the resolution call's answer replaces the field
        arg = _row_arg(r, name, supplied, hops)
        if (
            arg is not None
            and arg.tag == "D"
            and r.path == "motion_correction.method"
            and getattr(r.basis, "source_field_ids", None) == ["resolution_call"]
        ):
            arg.detail = _kb_verification(resolution)  # the same KB program as the tool's [D]
        if arg is not None:
            args.append(arg)
        if r.path == "motion_correction.method":
            args.extend(extra)
            extra = []
    args.extend(extra)
    provider = next((v for k, v in (applied or {}).items() if k.split(".", 1)[0] == kind), None)
    if provider is not None:
        # 2026-11-09 (item 3): the data provider applied this step to the release
        q = next((a.comment for a in args if a.tag == "E" and a.comment), None)
        args.insert(0, _Arg("applied_by", '"data_provider"', "E", q))
        args.insert(1, _Arg("release", _literal(provider["release"]), "E", None))
    stated = performed is not None and performed.state == EXTRACTED and performed.value is True
    if args and all(a.tag == "?" for a in args) and not stated:
        return f"{kind}(...)  [?]  # nothing reported for this step"
    comment = next(
        (a.comment for tag in ("E", "D", "C", "M") for a in args if a.tag == tag and a.comment),
        f"performed: «{clip(performed.span_text)}»" if stated and performed is not None else None,
    )
    call = f"{kind}(" + ", ".join(a.text() for a in args) + ")"
    return call + (f"  # {comment}" if comment else "")


def _header(record: dict[str, Any], prep: Any) -> list[str]:
    bp = getattr(prep.base_pipeline, "extraction", None)
    if bp is not None and bp.status == "EXTRACTED":
        ver = getattr(getattr(bp.value, "version", None), "extraction", None)
        version = str(ver.value) if ver is not None and ver.status == "EXTRACTED" else "not stated"
        pipeline = f"{bp.value.name} (version {version})"
    elif bp is not None and bp.status == "DEFERRED_TO_CITATION":
        pipeline = "deferred to " + ", ".join(d.ref for d in bp.deferrals)
    else:
        pipeline = "not stated"
    resolution = record.get("resolution") or {}
    rp = (resolution.get("resolved_pipeline") or {}).get("value")
    if rp:
        pipeline += f"; resolved: {rp}"
    tools = "; ".join(
        f"{t.get('display_name')} {t.get('version') or '(version not stated)'}"
        for t in record.get("citing_software") or []
        if t.get("kept", True)
    )
    releases = "; ".join(
        f"{r.get('dataset')} {r.get('release') or ''}".strip()
        for r in (record.get("data_release") or {}).get("releases") or []
    )
    order = getattr(prep, "step_order_source", None)
    order_words = {
        "paper": "as stated in the paper",
        "partial": "the paper's order for the steps it orders; the rest in template order",
    }.get(order or "", "template order (the paper does not state one; do not assume it)")
    return [
        f"# Reconstructed preprocessing — {record.get('paper_id')}",
        f"# pipeline: {pipeline}",
        f"# tools: {tools or 'none recorded'}",
        f"# data release: {releases or 'not stated'}",
        f"# order: {order_words}",
        "# tags: " + " · ".join(f"[{k}] {v}" for k, v in TAGS.items()),
    ]


def _variants(record: dict[str, Any]) -> int | None:
    mp = record.get("multiple_pipelines") or {}
    for call in mp.values() if isinstance(mp, dict) else []:
        count = ((call or {}).get("pipeline_variant_count") or {}).get("extraction") or {}
        if count.get("status") == "EXTRACTED":
            try:
                return int(float(count["value"]))
            except (TypeError, ValueError):
                return None
    return None


def _streams(record: dict[str, Any]) -> dict[str, list[int]]:
    """Step indices by ``applies_to``, when the record's steps carry one (no schema version does
    yet; the grouping is here so such a record renders one block per stream)."""
    out: dict[str, list[int]] = {}
    for i, step in enumerate((record.get("preprocessing") or {}).get("steps") or []):
        label = step.get("applies_to")
        if isinstance(label, str) and label.strip():
            out.setdefault(label.strip(), []).append(i)
    return out


#: 2026-11-11: the steps the release-defaults block lists, in order
RELEASE_STEPS: tuple[str, ...] = (
    "slice_timing",
    "distortion_correction",
    "coregistration",
    "normalization",
    "smoothing",
    "temporal_filtering",
    "nuisance_regression",
    "scrubbing",
)
_PER_STEP = 4  # options and fixed values shown per step; the rest are in the KB
#: 2026-11-11 (the author's wording): the block's header when the paper does not state its release
NOT_STATED = "not stated by the paper; pipeline defaults at candidate releases"


def _paper_date(record: dict[str, Any]) -> tuple[Any, str] | None:
    """The date the candidate releases are read at, and what it is (``paper_dates``: a stored
    date, CrossRef's issued date, the printed accepted or received date, the PDF's creation
    date, in that order)."""
    from extractor_mvp.paper_dates import paper_date

    return paper_date(record)


def _stated_release(record: dict[str, Any], pipeline_id: str) -> str | None:
    """A release of the pipeline the paper itself states (its cited software, or a data
    release's pipeline version)."""
    names = {"fmriprep": ("fmriprep",), "cpac": ("c-pac", "cpac")}[pipeline_id]
    for c in record.get("citing_software") or []:
        name = str(c.get("display_name") or c.get("tool_id") or "").lower()
        if c.get("version") and any(n in name for n in names):
            return str(c["version"]).lstrip("vV")
    pv = ((record.get("resolution") or {}).get("resolved_pipeline") or {}).get("pipeline_version")
    return str(pv).lstrip("vV") if pv else None


def _fmt(value: Any) -> str:
    return clip(
        " ".join(json.dumps(value, default=str).split()) if not isinstance(value, str) else value,
        60,
    )


def _release_defaults(record: dict[str, Any]) -> list[str]:
    """2026-11-11 (the author's request): for a paper resolved to fMRIPrep or C-PAC, what the
    pipeline's releases would have run, step by step, from the KB's option inventories. The
    release the paper states, else the releases out by its date (the latest, and the last release
    of each of the two minor versions before it). Values are the latest candidate's; an earlier
    candidate that differs is named beside it. Comments only: none of this is the paper's."""
    pipeline_id = ((record.get("resolution") or {}).get("resolved_pipeline") or {}).get("value")
    if pipeline_id not in ("fmriprep", "cpac"):
        return []
    from fmri_defaults_kb import options_at_date, release_timeline, step_defaults
    from fmri_defaults_kb.errors import KbError

    label = {"fmriprep": "fMRIPrep", "cpac": "C-PAC"}[pipeline_id]
    try:
        releases = {str(t["version"]): t for t in release_timeline(pipeline_id)}
        stated = _stated_release(record, pipeline_id)
        if stated and stated in releases:
            cands = [(stated, step_defaults(pipeline_id, stated))]
            head = f"# --- {label} {stated} defaults (the release the paper states) [D: KB option inventory]"
        else:
            when = _paper_date(record)
            if when is None:
                return ["", f"# --- {label}: {NOT_STATED}: none (no date is known for the paper)"]
            out = options_at_date(pipeline_id, when[0])
            if not out["candidates"]:
                return [
                    "",
                    f"# --- {label}: {NOT_STATED}: none out by {when[0].isoformat()} ({when[1]})",
                ]
            cands = [(c["version"], c["step_defaults"]) for c in out["candidates"]]
            listed = ", ".join(
                f"{c['version']} ({c['released']}{', latest' if c['latest'] else ''})"
                for c in out["candidates"]
            )
            head = (
                f"# --- {label}: {NOT_STATED}, out by {when[0].isoformat()} "
                f"({when[1]}): {listed} [D: KB option inventory]"
            )
    except KbError:
        return []
    lines = ["", head]
    latest_v, latest = cands[0]
    for step in RELEASE_STEPS:
        entry = latest.get(step) or {"options": {}, "fixed": []}
        parts: list[str] = []
        # every option any candidate offers for the step (a renamed option exists under one name
        # in one release and another name in the next); the latest's value first, then each
        # earlier candidate whose value differs, or that has the option when the latest does not
        ids: list[str] = []
        for _v, sd in cands:
            for oid in (sd.get(step) or {}).get("options", {}):
                if oid not in ids:
                    ids.append(oid)
        for oid in ids:
            opt = entry["options"].get(oid)
            shown_value = (
                None
                if opt is None
                else (
                    opt.get("default") if opt.get("default") is not None else opt.get("gui_default")
                )
            )
            others = []
            for v, sd in cands[1:]:
                o2 = (sd.get(step) or {}).get("options", {}).get(oid)
                if o2 is None or o2.get("default") is None:
                    continue
                if opt is None or o2.get("default") != opt.get("default"):
                    others.append(f"{v}: {_fmt(o2.get('default'))}")
            if shown_value is None and not others:
                continue
            if opt is None:
                text = f"{oid} absent in {latest_v}"
            else:
                text = f"{oid}={_fmt(opt.get('default'))}"
                if "gui_default" in opt and opt["gui_default"] != opt.get("default"):
                    text += f" (GUI: {_fmt(opt['gui_default'])})"
            parts.append(text + (f" [{'; '.join(others)}]" if others else ""))
        for p in entry["fixed"]:
            parts.append(
                f"{p['parameter']}: {_fmt(p['value'])}"
                + (" (uncertain)" if p.get("uncertain") else "")
            )
        if not parts:
            continue
        more = len(parts) - _PER_STEP
        shown = "; ".join(parts[:_PER_STEP]) + (f"; +{more} more in the KB" if more > 0 else "")
        lines.append(f"#   {step}: {shown}")
    example = any(
        o.get("config_role") == "example" for e in latest.values() for o in e["options"].values()
    )
    if example:
        lines.append(
            f"#   note: {label} {latest_v}'s configuration file is a shipped example, not a loaded "
            "default; the GUI values are shown beside it"
        )
    return lines


def render_pseudocode(record: dict[str, Any]) -> str | None:
    """The pseudo-code for one stored record, or None for a record with no extraction."""
    if "preprocessing" not in record:
        return None
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp.rechecks import checker_supplied

    prep = parse_any_version(record["preprocessing"])
    rows = flatten(prep)
    supplied = {c["field"]: c for c in checker_supplied(record)}
    hops = _hop_values(record)
    resolution = record.get("resolution")
    lines = _header(record, prep)
    streams = _streams(record)
    n = _variants(record)
    if streams:
        blocks = [(f"stream: {label}", idx) for label, idx in streams.items()]
    else:
        if n and n > 1:
            lines.append(
                f"# note: the paper describes {n} preprocessing variants; the record does not separate "
                "them by stream (no applies_to), so one block is shown"
            )
        blocks = [("", list(range(len(prep.steps))))]
    for label, idx in blocks:
        lines.append("")
        if label:
            lines.append(f"# --- {label}")
        for i in idx:
            lines.append(
                _step_line(
                    prep.steps[i], rows, supplied, hops, resolution, record.get("applied_by")
                )
            )
    lines.extend(_release_defaults(record))
    lines.append("")
    from extractor_mvp.verifier import drop_same_order_verdict

    # the same call the report's own COBIDAS section makes (render.to_protocol), so the counts agree
    verifier = drop_same_order_verdict(record.get("verifier"), prep)
    coverage = to_cobidas_coverage(
        prep, verifier=verifier, supplement=record.get("supplement")
    ).splitlines()
    start = next((i for i, ln in enumerate(coverage) if ln.startswith("Mandatory rows:")), None)
    if start is not None:
        lines.append(f"# {coverage[start]}")
        for ln in coverage[start + 1 :]:
            if not ln.startswith("  "):
                break
            lines.append(f"#   {ln.strip()}")
    return "\n".join(lines) + "\n"


def report_block(record: dict[str, Any]) -> str:
    """The ``## Reconstructed preprocessing`` section appended to the report ("" when none)."""
    code = render_pseudocode(record)
    if code is None:
        return ""
    return "\n## Reconstructed preprocessing\n\n```text\n" + code + "```\n"
