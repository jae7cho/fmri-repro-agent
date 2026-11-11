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

Per software mention, it also says whether the software was used for preprocessing (F1d).

2026-11-11 (DESIGN_applies_to.md Stage 1, fork F1): it judges ``applies_to`` as part of the value. A
field whose value differs by what it applies to is one draft line per part, ``<field>[<part>]``;
"wrong" when the value does not hold for the part named, "missed" when the paper ties a value to a
part the draft gives for all data. This replaces the record-level ``multiple_pipelines`` question,
which is no longer asked; a stored record keeps the answer it was given.

Caveat recorded with the design: the verifier is a second draw from the same model family as the
drafter; its verdicts are spot-checked against the author's reading before anyone trusts them.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from pydantic import BaseModel, Field, field_validator

from extractor_mvp.cobidas import COBIDAS_D3_ROWS
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.prompt_rules import CHECKING_RULES
from extractor_mvp.span_resolver import resolve_quote

VERDICTS: tuple[str, ...] = ("supported", "wrong", "missed")

VERIFIER_PROMPT = (
    """\
You are checking a DRAFTED report of the preprocessing an fMRI paper describes, against the paper's
methods text. Another reader drafted it; you check it. Read the methods text first, then go through
the draft line by line.

## What each draft line says
`<field> | <state> | <value> | quote: "<the sentence the drafter relied on>" | reason: <why it is a gap>`
State is one of: extracted (the drafter took a value from the paper), deferred (the drafter says
the paper sends the reader to a citation), not reported (the drafter found nothing), unverifiable
(the drafter found something it could not check).
A line whose field ends in `[<part>]` gives the value for that part of the paper's data only (a
derived measure, an analysis or part of the paper, a data type, a scanner or site, or a named
preprocessing variant, in the paper's words). A line without `[...]` gives a value for ALL of the
paper's data.

## Your verdict for EVERY line
- "supported": the value, or the gap, is right for THIS field (and, on a `[<part>]` line, for that
  part).
- "wrong": the value is not what the paper says for this field; on a `[<part>]` line, also when the
  value does not hold for the part named. Typical: the sentence is about the structural (T1/T2)
  image's own preprocessing but the field is about the functional (BOLD) data;
  the sentence describes covariates of a first-level statistical model (task regressors, motion or
  trend covariates in the GLM), which are analysis, not preprocessing; the sentence is about a
  different step; the value overstates the sentence (e.g. a specific variant the sentence does not
  name); a "not performed" the paper does not state.
- "missed": the draft has a gap (not reported / unverifiable) but the methods text states it; or the
  line has no `[...]` and the paper ties the value to a part of its data (it states a different
  value, or no value, for another part), in which case better_value = each part and its value, in
  the paper's words.
For "wrong" and "missed": better_value = what the field should say, in the paper's words (or
"not reported" when a value should not be there); relied_on = the sentence YOU relied on, copied
EXACTLY from the methods text. For "supported": relied_on may repeat the drafter's sentence.
reason = one sentence.

Scope (restated 2026-11-02): the preprocessing of the functional (BOLD) data, AND the structural
steps that feed the fMRI analysis -- brain extraction; segmentation used for masks or nuisance
regressors; bias-field (intensity inhomogeneity) correction; the structural image as the target of
the functional data's registration. Structural-only analyses (morphometry, diffusion, tractography)
and first-level model covariates are out. A structural sentence is wrong only for a field about the
functional series itself (its motion, slice timing, distortion, smoothing, filtering). Judge each
field independently. Do not judge a field by what a pipeline usually does; only by what the text
states.

## Software (one entry per software line in the draft)
software: for each `software_mentions.<name>` line, preprocessing_use = true if the paper used it
for a step in the scope above (functional preprocessing, or a structural step that feeds the fMRI
analysis: registration, segmentation, brain extraction, bias-field correction, motion correction,
denoising, ...), false if only for a structural-only analysis, statistics, visualization,
prediction or stimulus presentation.

## Preprocessing statements no draft line captures (added 2026-11-02)
unplaced: a list of the preprocessing statements in the methods text -- in the scope above -- that
NO draft line captures: a step, a parameter, a threshold, a filter, a branch of the pipeline that
the draft has nowhere to put or did not put anywhere. Do NOT list a statement a draft line already
captures, even with a gap or a verdict of yours; do NOT list analysis. For each: statement = what
is done, in a few words; relied_on = the sentence, copied EXACTLY from the methods text; row = the
COBIDAS D.3 row it would belong to, one of: {rows}; or "no row" when none fits. An empty list when
the draft captures everything. This list never changes a field.

Every quoted sentence (relied_on) must be copied EXACTLY from the methods text.

"""
    + CHECKING_RULES
    + """Methods text:
\"\"\"
{text}
\"\"\"

Drafted report (one line per field):
\"\"\"
{draft}
\"\"\"
"""
)


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


class UnplacedStatement(BaseModel):
    """A preprocessing statement no field captured (2026-11-02, the author's item 2). Plain strings,
    as the verdicts: a row outside the list is normalised to "no row" in code, never reasked."""

    statement: str
    relied_on: str | None = None
    row: str = "no row"


class VerifierExtraction(BaseModel):
    fields: list[FieldVerdict] = Field(default_factory=list)
    unplaced: list[UnplacedStatement] = Field(default_factory=list)
    software: list[SoftwareVerdict] = Field(default_factory=list)

    @field_validator("fields", "unplaced", "software", mode="before")
    @classmethod
    def _a_list_sent_as_a_json_string(cls, v: Any) -> Any:
        """2026-11-05, after Ladouceur_2023's checking pass came back unavailable twice in stress_v1:
        every rejected attempt was complete (finish_reason tool_calls, 6,727-10,110 output tokens)
        and sent ``fields`` as a JSON-encoded string of the array instead of the array. A string
        that parses to a list is read as that list; anything else is left for validation to reject.
        The JSON schema the model sees is unchanged (a before-validator adds nothing to it)."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except ValueError:
                return v
            if isinstance(parsed, list):
                return parsed
        return v


def _fmt(value: Any) -> str:
    from extractor_mvp.render import _fmt_value

    return _fmt_value(value)


def compact_draft(preprocessing: Any) -> str:
    """One line per TARGETED field (untargeted fillers omitted), full quotes, plus the software
    mentions and the stated step order -- the draft the verifier checks (§3: full, untruncated
    quotes, which avoids the misreading the author caught on chen)."""
    from extractor_mvp.citation_hop import json_safe
    from extractor_mvp.render import flatten

    lines: list[str] = []
    for r in flatten(preprocessing):
        if r.left_missing_reason == "not_targeted_by_mvp":
            continue
        if r.state == "VARIED":
            # fork F1 (2026-11-11): one line per part, so each is judged as part of the value
            lines.extend(_variant_draft_lines(r))
            continue
        if r.state == "EXTRACTED":
            state, value = "extracted", _fmt(r.value)
        elif r.state == "DEFERRED_TO_CITATION":
            state, value = "deferred", "deferred to " + ", ".join(r.deferral_refs or [])
        elif r.state == "INFERRED_DEFAULT" and r.extraction_status == "DEFERRED_TO_CITATION":
            # fix 1d (2026-11-05): the checking pass sees what the paper said, never AESPA's
            # inference; the extraction arm is shown, the inferred value is not
            state, value = "deferred", "deferred to " + ", ".join(r.deferral_refs or [])
        elif r.state == "INFERRED_DEFAULT":
            state, value = "not reported", "-"
        else:
            from extractor_mvp.cobidas import _UNVERIFIABLE_GAP_BASES, _gap_base

            base = _gap_base(r.left_missing_reason)
            state = "unverifiable" if base in _UNVERIFIABLE_GAP_BASES else "not reported"
            value = "-"
        quote = json_safe(" ".join((r.span_text or "").split()))  # no double quote to copy back
        reason = r.left_missing_reason or ""
        lines.append(f'{r.path} | {state} | {value} | quote: "{quote}" | reason: {reason}')
    for pf in getattr(preprocessing, "software_mentions", None) or []:
        if pf.extraction.status == "EXTRACTED":
            v = pf.extraction.value
            quote = json_safe(" ".join(pf.extraction.spans[0].text.split()))
            lines.append(
                f"software_mentions.{v.name} | extracted | version {v.version or 'not stated'}; "
                f'used for {v.used_for or "not stated"} | quote: "{quote}" | reason: '
            )
    source = getattr(preprocessing, "step_order_source", None)
    if source is not None:
        order = ", ".join(s.kind for s in preprocessing.steps)
        quotes = json_safe(
            " ".join(" ".join(sp.text.split()) for sp in preprocessing.step_order_spans or [])
        )
        if source != "by_part":
            lines.append(f'step_order | {source} | {order} | quote: "{quotes}" | reason: ')
    for part in getattr(preprocessing, "step_order_parts", None) or []:
        quotes = json_safe(" ".join(" ".join(sp.text.split()) for sp in part.spans))
        lines.append(
            f"step_order[{part.applies_to}] | extracted | {', '.join(part.kinds)} | "
            f'quote: "{quotes}" | reason: '
        )
    return "\n".join(lines)


def _variant_draft_lines(r: Any) -> list[str]:
    """A VARIED row's draft lines: ``<field>[<part>]``, its value and its own quote."""
    from extractor_mvp.citation_hop import json_safe
    from extractor_mvp.render import _variant_value, variant_key

    out = []
    for v in r.variants or []:
        quote = json_safe(" ".join(v.span_text.split()))
        reason = "" if v.verified else "the words for the part are not in the quote"
        out.append(
            f"{variant_key(r.path, v.applies_to)} | extracted | {_variant_value(r, v)} | "
            f'quote: "{quote}" | reason: {reason}'
        )
    return out


#: The rows an unplaced statement may name: every D.3 preprocessing row id, then "no row".
_ROW_IDS: tuple[str, ...] = tuple(r.row_id for r in COBIDAS_D3_ROWS)
_ROW_CHOICES = ", ".join(_ROW_IDS)


def _unplaced_record(u: UnplacedStatement, text: str) -> dict[str, Any]:
    """One unplaced statement, its sentence quote-checked through the one span path. A row not in
    the D.3 list is kept verbatim as ``row_raw`` and placed as "no row"."""
    resolved = None
    if u.relied_on:
        resolved = resolve_quote(u.relied_on, text).span is not None
    row = u.row.strip()
    return {
        "statement": u.statement.strip(),
        "relied_on": u.relied_on,
        "relied_on_resolved": resolved,
        "row": row if row in _ROW_IDS else "no row",
        "row_raw": row,
    }


def same_order(better_value: str | None, kinds: list[str]) -> bool:
    """True when an order proposal names only steps in ``kinds`` and keeps them in ``kinds``'s order.

    2026-11-02, the author's ruling: an order verdict whose proposal equals the current order is
    dropped in code. The draft lists every kind (performed or not), so a proposal that names only
    the performed ones in the same relative order (shen_2013's) is the same order, not an
    objection to it. A proposal with any token that is not a draft kind, a repeated kind, or no
    kinds at all is kept: it cannot be read as equal."""
    if not better_value:
        return False
    tokens = [
        "_".join(t.lower().replace("-", " ").split())
        for t in re.split(r",|;|->|\u2192|\bthen\b", better_value)
        if t.strip()
    ]
    known = set(kinds)
    if not tokens or any(t not in known for t in tokens) or len(set(tokens)) != len(tokens):
        return False
    return tokens == [k for k in kinds if k in set(tokens)]


def drop_same_order_verdict(
    verifier: dict[str, Any] | None, preprocessing: Any
) -> dict[str, Any] | None:
    """The verifier record without a ``step_order`` verdict whose proposal equals the current order
    (:func:`same_order`); otherwise the record unchanged. Applied when the record is written and
    again when it is rendered, so records stored before the ruling read the same way."""
    if not verifier or verifier.get("status") != "ok" or preprocessing is None:
        return verifier
    v = (verifier.get("fields") or {}).get("step_order")
    if v is None or v.get("verdict") != "wrong":
        return verifier
    if not same_order(v.get("better_value"), [s.kind for s in preprocessing.steps]):
        return verifier
    fields = {k: val for k, val in verifier["fields"].items() if k != "step_order"}
    return {**verifier, "fields": fields, "dropped_same_order": True}


def _normalise(verdict: str) -> str | None:
    v = verdict.strip().lower()
    for known in VERDICTS:
        if v.startswith(known):
            return known
    return None


def run_verifier(
    parsed_paper: ParsedPaper,
    preprocessing: Any,
    model: str,
    *,
    client: Any | None = None,
    draft: str | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    """One ``create()`` after the draft exists. Returns the verifier record (a plain dict, stored
    beside the record as ``verifier``); never raises. ``draft`` replaces :func:`compact_draft` for a
    draft that is not a whole ``Preprocessing`` (the citation hop's scoped fields).

    ``text`` (2026-11-05, fix 1a): the text the checking pass reads and resolves its sentences
    against, when it is not the methods slice -- the full paper when the slice is suspicious. The
    record says which (``read``)."""
    from extractor_mvp.extractor import build_client

    t0 = time.perf_counter()
    read = "full_text" if text is not None else "methods_slice"
    if text is None:
        text = parsed_paper.text
    # 2026-11-05 (Ladouceur_2023, stress_v1): the text the checking pass reads and resolves against
    # has every double quotation mark made an apostrophe, one character for one (citation_hop's
    # json_safe, case one's fix for the hop calls). A copied sentence opening with a quote was sent
    # unescaped, the reply did not parse, and the pass came back unavailable after two attempts.
    from extractor_mvp.citation_hop import json_safe

    text = json_safe(text)
    if draft is None:
        draft = compact_draft(preprocessing)
    known_fields = {line.split(" | ", 1)[0] for line in draft.splitlines()}
    try:
        client = client or build_client()
        raw: VerifierExtraction = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": VERIFIER_PROMPT.format(text=text, draft=draft, rows=_ROW_CHOICES),
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
            "unplaced": [],
            "n_draft_lines": len(known_fields),
            "read": read,
        }
    fields: dict[str, dict[str, Any]] = {}
    for fv in raw.fields:
        verdict = _normalise(fv.verdict)
        if verdict is None or fv.field not in known_fields or fv.field in fields:
            continue
        resolved = None
        if fv.relied_on:
            res = resolve_quote(fv.relied_on, text)
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
    unplaced = [_unplaced_record(u, text) for u in raw.unplaced if u.statement.strip()]
    return (
        drop_same_order_verdict(
            {
                "status": "ok",
                "error": None,
                "wall_time_s": round(time.perf_counter() - t0, 3),
                "fields": fields,
                "software": software,
                # fork F1 (2026-11-11): no longer asked; the key stays so stored and new records
                # share one shape, and the render derives the variants line from the values
                "multiple_pipelines": None,
                "unplaced": unplaced,
                "n_draft_lines": len(known_fields),
                "read": read,
            },
            preprocessing,
        )
        or {}
    )


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
