"""Retry/reask audit — does instructor's max_retries=2 silently alter the four-state result?

DIAGNOSTIC ONLY. Touches no extraction logic, prompt, schema, or temperature. It attaches
READ-ONLY instructor hooks (completion:response, parse:error) to a client and runs the
UNCHANGED extract() over the corpus, recording, per extraction call:
  - attempts actually made (1 = clean first parse; >1 = a reask fired)
  - each reask's triggering ValidationError (field + offending value)
  - the first-draft field value vs the final accepted value

Structural fact this measures against (from source, extractor_mvp.extraction_result):
PreprocessingExtraction fields are FieldExtractionResult, whose `value` is a free `str | None`
— NOT a Literal enum. The Literal -> value_not_in_literal resolution is Python-side, AFTER
instructor returns, so an out-of-enum VALUE cannot raise a pydantic error and cannot trigger a
reask. The only reask triggers are: bad `status`/`target_kind` Literal, the model_validator
cross-field constraints (extracted-without-quote, missing-with-value, deferred-without-ref),
malformed JSON, or a missing required field. This audit checks whether any of those, when they
fire, flip a field we report as EXTRACTED / MISSING.

Hooks are attached only inside this standalone script; the extractor is never modified. Off by
default — nothing imports this. Run by path:
    python scripts/retry_audit.py --n 5 --out results/RETRY_AUDIT.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from extractor_mvp.batch_config import load_batch_config
from extractor_mvp.corpus import is_excluded
from extractor_mvp.extractor import build_client, extract
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date

_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # the v6-pinned model
_V6_CONFIG = Path(__file__).resolve().parent.parent / "results" / "batch_v6_full_config.yaml"


def _corpus_papers() -> list[tuple[str, Path]]:
    """The exact v6 corpus (paper_id, path), honoring the exclusion registry (drops cabral)."""
    cfg = load_batch_config(_V6_CONFIG)
    return [(p.paper_id, p.path) for p in cfg.papers if not is_excluded(p.paper_id)]


# The 7 targeted response-model fields whose first->final we care about.
_FIELDS = [
    "target_space",
    "resolution_mm",
    "surface_registration",
    "target_surface",
    "intensity_convention",
    "intensity_value",
    "base_pipeline_name",
    "temporal_standardization_method",
]


@dataclass
class _CallLog:
    """Per-extraction-call capture, reset before each extract()."""

    responses: list[Any] = field(default_factory=list)  # raw litellm response per attempt
    errors: list[Exception] = field(default_factory=list)  # parse:error exceptions per failure

    def reset(self) -> None:
        self.responses = []
        self.errors = []


def _raw_content(resp: Any) -> str | None:
    try:
        content = resp.choices[0].message.content
    except Exception:
        return None
    return content if isinstance(content, str) else None


def _parse_json(content: str | None) -> dict[str, Any] | None:
    if not content:
        return None
    try:
        return dict(json.loads(content))
    except (json.JSONDecodeError, TypeError, ValueError):
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return dict(json.loads(m.group(0)))
            except (json.JSONDecodeError, TypeError, ValueError):
                return None
        return None


def _field_class(fieldval: Any) -> str:
    """Collapse a raw response-model field dict to status:value for diffing."""
    if not isinstance(fieldval, dict):
        return "ABSENT"
    st = fieldval.get("status")
    if st == "extracted":
        return f"extracted:{fieldval.get('value')}"
    if st == "deferred":
        return f"deferred:{fieldval.get('ref_string')}"
    return str(st)


def _error_fields(exc: Exception) -> list[dict[str, Any]]:
    """Pull (field, error-type, offending input) out of a pydantic ValidationError."""
    out: list[dict[str, Any]] = []
    errs = getattr(exc, "errors", None)
    if callable(errs):
        try:
            for e in exc.errors():  # type: ignore[attr-defined]
                loc = e.get("loc", ())
                out.append(
                    {
                        "field": ".".join(str(x) for x in loc) or "(root)",
                        "type": e.get("type", "?"),
                        "input": e.get("input"),
                        "msg": e.get("msg", ""),
                    }
                )
        except Exception:
            pass
    if not out:
        out.append(
            {
                "field": "(unparsed)",
                "type": type(exc).__name__,
                "input": None,
                "msg": str(exc)[:200],
            }
        )
    return out


@dataclass
class Reask:
    paper: str
    run: int
    attempts: int
    trigger_field: str
    trigger_type: str
    offending: Any
    is_enum: bool
    is_parse: bool
    classification: str  # COERCED / DROPPED / UNCHANGED / PARSE
    first_final: str  # "first_class -> final_class" for the triggering field


def _classify(exc: Exception, first: dict[str, Any] | None, final: Any) -> list[Reask]:
    """Build a Reask record per validation error the exception carries."""
    records = []
    for ef in _error_fields(exc):
        fld = ef["field"].split(".")[0]
        etype = str(ef["type"])
        is_parse = "json" in etype.lower() or (ef["field"] == "(unparsed)" and "JSON" in etype)
        is_enum = "literal" in etype.lower() or "enum" in etype.lower()
        first_cls = _field_class((first or {}).get(fld)) if first else "N/A"
        final_cls = "N/A"
        if final is not None and hasattr(final, "__dict__"):
            fv = getattr(final, fld, None)
            if fv is not None and hasattr(fv, "model_dump"):
                final_cls = _field_class(fv.model_dump())
            else:
                final_cls = _field_class(fv)
        if is_parse:
            cls = "PARSE"
        elif first_cls.startswith(("extracted", "deferred")) and final_cls in ("missing", "None"):
            cls = "DROPPED"
        elif is_enum and final_cls.startswith("extracted"):
            cls = "COERCED"
        elif first_cls == final_cls:
            cls = "UNCHANGED"
        else:
            cls = f"CHANGED({first_cls}->{final_cls})"
        records.append(
            Reask(
                paper="",
                run=0,
                attempts=0,
                trigger_field=fld,
                trigger_type=etype,
                offending=ef["input"],
                is_enum=is_enum,
                is_parse=is_parse,
                classification=cls,
                first_final=f"{first_cls} -> {final_cls}",
            )
        )
    return records


def run(n: int) -> tuple[list[Reask], int, int, list[str]]:
    client = build_client()
    log = _CallLog()
    client.on("completion:response", lambda response: log.responses.append(response))
    client.on("parse:error", lambda error: log.errors.append(error))

    papers = _corpus_papers()  # [(paper_id, path), ...] excluding registry entries
    reasks: list[Reask] = []
    total_calls = 0
    reask_calls = 0
    for pid, path in papers:
        full, _ = load_pdf_text(path)
        sl = find_methods_section(full)
        parsed = ParsedPaper(
            text=sl.text, source=pid, parser="pypdf", pdf_date=pdf_creation_date(path)
        )
        for run_i in range(n):
            log.reset()
            prep, _d, _f = extract(parsed, _MODEL, client=client, paper_date=parsed.pdf_date)
            total_calls += 1
            attempts = len(log.responses)
            if log.errors:  # at least one reask fired
                reask_calls += 1
                first = _parse_json(_raw_content(log.responses[0])) if log.responses else None
                for exc in log.errors:
                    for rec in _classify(exc, first, prep):
                        rec.paper, rec.run, rec.attempts = pid, run_i + 1, attempts
                        reasks.append(rec)
            print(f"  {pid} run {run_i + 1}/{n}: attempts={attempts}", file=sys.stderr)
    return reasks, total_calls, reask_calls, [p for p, _ in papers]


def render(reasks: list[Reask], total: int, reask_calls: int, papers: list[str], n: int) -> str:
    enum_triggered = [r for r in reasks if r.is_enum]
    parse_triggered = [r for r in reasks if r.is_parse]
    struct = [r for r in reasks if not r.is_enum and not r.is_parse]
    coerced = [r for r in reasks if r.classification == "COERCED"]
    dropped = [r for r in reasks if r.classification == "DROPPED"]
    lines = [
        "# Retry / reask audit — does max_retries=2 alter the four-state result?",
        "",
        f"Corpus: {len(papers)} papers x N={n} = {total} extraction calls. Model pinned to the "
        "v6 string; temperature 0; prompt/schema UNCHANGED. Read-only instructor hooks "
        "(completion:response, parse:error) attached to the client — the extractor is not "
        "modified.",
        "",
        "## Headline",
        "",
        f"- Extraction calls that fired ≥1 reask: **{reask_calls} / {total}**.",
        f"- Reask events captured: {len(reasks)} "
        f"(enum-triggered {len(enum_triggered)} · structural {len(struct)} · parse {len(parse_triggered)}).",
        f"- **COERCED** (out-of-enum → valid member; signal silently upgraded): **{len(coerced)}**.",
        f"- **DROPPED** (value → MISSING on retry; signal silently erased): **{len(dropped)}**.",
        "",
    ]
    if reask_calls == 0:
        lines += [
            "**No reask fired anywhere in the corpus.** Every extraction call parsed cleanly on "
            "the first attempt. max_retries=2 is inert on this corpus at temp 0: no reported "
            "EXTRACTED or MISSING state owes itself to a reask. The concern is discharged "
            "empirically (though the reask path remains a latent risk if the schema tightened).",
        ]
        return "\n".join(lines) + "\n"

    lines += [
        "## Every reask (first-draft → final for the triggering field)",
        "",
        "| paper | run | attempts | field | error type | enum? | offending value | class | first → final |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reasks:
        off = str(r.offending)[:40].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r.paper} | {r.run} | {r.attempts} | {r.trigger_field} | {r.trigger_type} | "
            f"{'YES' if r.is_enum else 'no'} | `{off}` | {r.classification} | {r.first_final} |"
        )
    lines += [
        "",
        "## Part-3 verdict — enum reasks killing value_not_in_literal",
        "",
        f"Enum/Literal-triggered reasks: **{len(enum_triggered)}**.",
    ]
    if not enum_triggered:
        lines.append(
            "Zero enum-triggered reasks. On this corpus the thesis-critical worry (an enum reask "
            "silently converting a value_not_in_literal signal into a valid member) does NOT "
            "occur — consistent with the structural finding that response-model VALUE fields are "
            "free strings, not Literals. It remains a latent design risk only."
        )
    else:
        lines.append(
            "Enum-triggered reasks DID occur — original out-of-enum strings being discarded:"
        )
        for r in enum_triggered:
            lines.append(f"- {r.paper} run {r.run}: `{r.offending}` → {r.first_final}")
    if coerced or dropped:
        lines += [
            "",
            "**A reported four-state outcome owes its state to a reask** (STOP — this is a "
            "design decision, reported not fixed):",
        ]
        for r in coerced + dropped:
            lines.append(
                f"- {r.paper} run {r.run} · {r.trigger_field}: {r.classification} · {r.first_final}"
            )
    else:
        lines += [
            "",
            "No reask changed a field from EXTRACTED/DEFERRED to MISSING or coerced an out-of-enum "
            "value into a member. Reasks, where they fired, were structural and left the reported "
            "four-state outcome unchanged.",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--n", type=int, default=5, help="passes over the corpus")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    reasks, total, reask_calls, papers = run(args.n)
    md = render(reasks, total, reask_calls, papers, args.n)
    if args.out is not None:
        args.out.write_text(md)
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
