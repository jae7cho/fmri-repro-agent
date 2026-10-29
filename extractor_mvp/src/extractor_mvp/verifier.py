"""The checking pass: one more call reads the methods text and the drafted report, field by field.

``docs/design/DESIGN_report_v2.md`` §3, ratified by the author on 2026-10-29. Per targeted field the
verifier returns ``supported``, ``wrong`` (the value is not what the paper says for this field) or
``missed`` (the draft has a gap the paper fills), with the reason and the sentence it relied on.
That sentence is quote-checked through the one span path like every other quote; a verdict whose
sentence does not resolve is shown as an unverified verdict and has no effect.

**The verifier never writes a value and can never fail a paper.** It has no validator (the
2026-10-29 ruling); any exception leaves the record ``unavailable`` and the report renders without
a checking column, saying so. A ``wrong`` verdict demotes the drafted value to a flag in the report
(the renderer's job); the extraction arm in the JSON is untouched.

It also carries the record-level ``multiple_pipelines`` question, re-worded (F3a): does this paper
preprocess its own data in more than one way -- a benchmark of denoising strategies run on the
same data excluded -- and, per software mention, whether it was used for preprocessing (F1d).

Caveat recorded with the design: the verifier is a second draw from the same model family as the
drafter; its verdicts are spot-checked against the author's reading before anyone trusts them.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from extractor_mvp.coverage_fields import RECORD_SPECS
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.span_resolver import resolve_quote

VERDICTS: tuple[str, ...] = ("supported", "wrong", "missed")

VERIFIER_PROMPT = """\
You are checking a DRAFTED report of the preprocessing an fMRI paper describes, against the paper's
methods text. Another reader drafted it; you check it. Read the methods text first, then go through
the draft line by line.

## What each draft line says
`<field> | <state> | <value> | quote: "<the sentence the drafter relied on>" | reason: <why it is a gap>`
State is one of: extracted (the drafter took a value from the paper), deferred (the drafter says
the paper sends the reader to a citation), not reported (the drafter found nothing), unverifiable
(the drafter found something it could not check).

## Your verdict for EVERY line
- "supported": the value, or the gap, is right for THIS field.
- "wrong": the value is not what the paper says for this field. Typical: the sentence is about the
  structural (T1/T2) image's own preprocessing but the field is about the functional (BOLD) data;
  the sentence describes covariates of a first-level statistical model (task regressors, motion or
  trend covariates in the GLM), which are analysis, not preprocessing; the sentence is about a
  different step; the value overstates the sentence (e.g. a specific variant the sentence does not
  name); a "not performed" the paper does not state.
- "missed": the draft has a gap (not reported / unverifiable) but the methods text states it.
For "wrong" and "missed": better_value = what the field should say, in the paper's words (or
"not reported" when a value should not be there); relied_on = the sentence YOU relied on, copied
EXACTLY from the methods text. For "supported": relied_on may repeat the drafter's sentence.
reason = one sentence.

Scope: only the preprocessing of the functional (BOLD) data is in scope, except where a field is
about the structural image (brain extraction, segmentation, intensity correction of the structural
image). Judge each field independently. Do not judge a field by what a pipeline usually does; only
by what the text states.

## Software (one entry per software line in the draft)
software: for each `software_mentions.<name>` line, preprocessing_use = true if the paper used it
for preprocessing the data (registration, segmentation, motion correction, denoising, ...), false
if only for statistics, analysis, visualization or stimulus presentation.

## More than one preprocessing variant (a record-level question)
multiple_pipelines: "yes" only if the paper PREPROCESSES ITS OWN DATA IN MORE THAN ONE WAY -- for
  example separate task and rest preprocessing branches, or a main pipeline and an alternative
  whose results are reported. A comparison or benchmark of several denoising or preprocessing
  strategies applied to the same data, as the object of study, is NOT this (answer missing).
  verbatim_quote = the sentence that shows it. "missing" otherwise. Never "no", never "deferred".
pipeline_variant_count: when multiple_pipelines is "yes", the number of variants as an integer
  string, with the sentence that lets it be counted; "missing" otherwise.

Every quoted sentence (relied_on, verbatim_quote) must be copied EXACTLY from the methods text.

Methods text:
\"\"\"
{text}
\"\"\"

Drafted report (one line per field):
\"\"\"
{draft}
\"\"\"
"""


def _missing_field() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


class FieldVerdict(BaseModel):
    """One verdict. Plain strings, not Literals, so a malformed verdict is normalised in code
    instead of triggering a reask."""

    field: str
    verdict: str
    reason: str = ""
    relied_on: str | None = None
    better_value: str | None = None


class SoftwareVerdict(BaseModel):
    name: str
    preprocessing_use: bool | None = None


class VerifierExtraction(BaseModel):
    fields: list[FieldVerdict] = Field(default_factory=list)
    software: list[SoftwareVerdict] = Field(default_factory=list)
    multiple_pipelines: FieldExtractionResult = Field(default_factory=_missing_field)
    pipeline_variant_count: FieldExtractionResult = Field(default_factory=_missing_field)


def _fmt(value: Any) -> str:
    from extractor_mvp.render import _fmt_value

    return _fmt_value(value)


def compact_draft(preprocessing: Any) -> str:
    """One line per TARGETED field (untargeted fillers omitted), full quotes, plus the software
    mentions and the stated step order -- the draft the verifier checks (§3: full, untruncated
    quotes, which avoids the misreading the author caught on chen)."""
    from extractor_mvp.render import flatten

    lines: list[str] = []
    for r in flatten(preprocessing):
        if r.left_missing_reason == "not_targeted_by_mvp":
            continue
        if r.state == "EXTRACTED":
            state, value = "extracted", _fmt(r.value)
        elif r.state == "DEFERRED_TO_CITATION":
            state, value = "deferred", "deferred to " + ", ".join(r.deferral_refs or [])
        elif r.state == "INFERRED_DEFAULT":
            state, value = "not reported (a default was inferred, not stated)", _fmt(r.value)
        else:
            from extractor_mvp.cobidas import _UNVERIFIABLE_GAP_BASES, _gap_base

            base = _gap_base(r.left_missing_reason)
            state = "unverifiable" if base in _UNVERIFIABLE_GAP_BASES else "not reported"
            value = "-"
        quote = " ".join((r.span_text or "").split())
        reason = r.left_missing_reason or ""
        lines.append(f'{r.path} | {state} | {value} | quote: "{quote}" | reason: {reason}')
    for pf in getattr(preprocessing, "software_mentions", None) or []:
        if pf.extraction.status == "EXTRACTED":
            v = pf.extraction.value
            quote = " ".join(pf.extraction.spans[0].text.split())
            lines.append(
                f"software_mentions.{v.name} | extracted | version {v.version or 'not stated'}; "
                f'used for {v.used_for or "not stated"} | quote: "{quote}" | reason: '
            )
    source = getattr(preprocessing, "step_order_source", None)
    if source is not None:
        order = ", ".join(s.kind for s in preprocessing.steps)
        quotes = " ".join(" ".join(sp.text.split()) for sp in preprocessing.step_order_spans or [])
        lines.append(f'step_order | {source} | {order} | quote: "{quotes}" | reason: ')
    return "\n".join(lines)


def _normalise(verdict: str) -> str | None:
    v = verdict.strip().lower()
    for known in VERDICTS:
        if v.startswith(known):
            return known
    return None


def _record_field(fe: FieldExtractionResult, spec: Any, text: str) -> dict[str, Any]:
    from extractor_mvp.extractor import _process_field

    pf, _diag, _deferral = _process_field(
        spec.field_id,
        f"record.{spec.field_id}",
        fe,
        None,
        spec.t,
        text,
        None,
        use_synonym_table=False,
        value_kind=spec.value_kind,
    )
    dumped: dict[str, Any] = pf.model_dump(mode="json")
    return dumped


def run_verifier(
    parsed_paper: ParsedPaper,
    preprocessing: Any,
    model: str,
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    """One ``create()`` after the draft exists. Returns the verifier record (a plain dict, stored
    beside the record as ``verifier``); never raises."""
    from extractor_mvp.extractor import build_client

    t0 = time.perf_counter()
    draft = compact_draft(preprocessing)
    known_fields = {line.split(" | ", 1)[0] for line in draft.splitlines()}
    try:
        client = client or build_client()
        raw: VerifierExtraction = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": VERIFIER_PROMPT.format(text=parsed_paper.text, draft=draft),
                }
            ],
            response_model=VerifierExtraction,
            temperature=0.0,
            max_retries=2,
        )
    except Exception as exc:  # the checking pass can never fail a paper
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}"[:500],
            "wall_time_s": round(time.perf_counter() - t0, 3),
            "fields": {},
            "software": {},
            "multiple_pipelines": None,
            "n_draft_lines": len(known_fields),
        }
    fields: dict[str, dict[str, Any]] = {}
    for fv in raw.fields:
        verdict = _normalise(fv.verdict)
        if verdict is None or fv.field not in known_fields or fv.field in fields:
            continue
        resolved = None
        if fv.relied_on:
            res = resolve_quote(fv.relied_on, parsed_paper.text)
            resolved = res.span is not None
        fields[fv.field] = {
            "verdict": verdict,
            "reason": fv.reason,
            "relied_on": fv.relied_on,
            "relied_on_resolved": resolved,
            "better_value": fv.better_value,
        }
    software = {
        sv.name: sv.preprocessing_use for sv in raw.software if sv.preprocessing_use is not None
    }
    specs = {s.field_id: s for s in RECORD_SPECS}
    multiple = {
        "V": {
            "multiple_pipelines": _record_field(
                raw.multiple_pipelines, specs["multiple_pipelines"], parsed_paper.text
            ),
            "pipeline_variant_count": _record_field(
                raw.pipeline_variant_count, specs["pipeline_variant_count"], parsed_paper.text
            ),
        }
    }
    return {
        "status": "ok",
        "error": None,
        "wall_time_s": round(time.perf_counter() - t0, 3),
        "fields": fields,
        "software": software,
        "multiple_pipelines": multiple,
        "n_draft_lines": len(known_fields),
    }


def effective(verdict: dict[str, Any] | None) -> str | None:
    """The verdict that acts on the report: ``None`` when absent or when its sentence did not
    resolve (an unverified verdict has no effect)."""
    if not verdict:
        return None
    if (
        verdict.get("verdict") in ("wrong", "missed")
        and verdict.get("relied_on_resolved") is not True
    ):
        return None
    return str(verdict.get("verdict"))
