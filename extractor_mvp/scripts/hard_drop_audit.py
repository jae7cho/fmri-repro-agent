"""PHASE 1 (measurement only): the span-resolution hard-drop blast radius.

DIAGNOSTIC. Changes no extraction logic. For every field of every corpus paper it captures, at
four-state assignment time:
  - RAW model output (status, value, verbatim_quote) via a read-only completion:response hook
  - whether resolve_quote(verbatim_quote, slice) returns a span or None (production's own function)
  - the FINAL four-state from the returned Preprocessing
and flags SILENT DROPS: RAW status=extracted AND span=None AND FINAL=MISSING_FROM_PAPER — a value the
model extracted, relabeled "not reported" by post-processing.

For each drop it classifies WHY resolve_quote failed, to separate pypdf-mangle (recoverable, safe to
flag) from genuine-mismatch (quote content truly absent -> the span check is correctly catching a
possible hallucination; must keep failing). N=1 is enough: these are deterministic post-processing
failures given the model's quote, not sampling.

Off by default. Run: python scripts/hard_drop_audit.py --out results/HARD_DROP_AUDIT.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from extractor_mvp.batch_config import load_batch_config
from extractor_mvp.corpus import is_excluded
from extractor_mvp.extractor import build_client, extract
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date
from extractor_mvp.span_resolver import resolve_quote

_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
_V6_CONFIG = Path(__file__).resolve().parent.parent / "results" / "batch_v6_full_config.yaml"

# raw response-model field -> (step kind, step attr) for reading the FINAL state. base_pipeline_name
# is special (prep.base_pipeline). base_pipeline_ref is excluded (it is attribution, not a value).
_STEP_MAP: dict[str, tuple[str, str]] = {
    "target_space": ("spatial_normalization", "target_space"),
    "resolution_mm": ("spatial_normalization", "resolution_mm"),
    "surface_registration": ("surface_projection", "surface_registration"),
    "target_surface": ("surface_projection", "target_surface"),
    "intensity_convention": ("intensity_normalization", "convention"),
    "intensity_value": ("intensity_normalization", "value"),
    "temporal_standardization_method": ("temporal_standardization", "method"),
}
_FIELDS = ["base_pipeline_name", *_STEP_MAP.keys()]


def _parse_json(content: str | None) -> dict[str, Any]:
    if not content:
        return {}
    try:
        return dict(json.loads(content))
    except (json.JSONDecodeError, TypeError, ValueError):
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return dict(json.loads(m.group(0)))
            except (json.JSONDecodeError, TypeError, ValueError):
                return {}
        return {}


def _final_status(prep: Any, field: str) -> str:
    if field == "base_pipeline_name":
        bp = prep.base_pipeline
        ext = getattr(bp, "extraction", None)
        if ext is None:
            return type(bp).__name__.replace("MissingFromPaper", "MISSING_FROM_PAPER")
        return str(ext.status)
    kind, attr = _STEP_MAP[field]
    for s in prep.steps:
        if s.kind == kind:
            f = getattr(s, attr, None)
            if f is not None:
                return str(f.extraction.status)
    return "ABSENT"


def _dehyphen(s: str) -> str:
    return re.sub(r"-\s*\n\s*", "", s)  # remove line-break hyphenation ("us-\ning" -> "using")


def _strip_markers(s: str) -> str:
    return re.sub(r"\[\s*\d+(?:[-\u2013]\d+)?\s*\]", "", s)  # "[ 62]" / "[1-3]"


def _hard(s: str) -> str:
    """Strip EVERY non-alphanumeric (whitespace, punctuation, unicode multiplication-sign / apostrophes, URL slashes).

    The robust "is this text present at all" test: a quote whose content survives here as a
    substring of the source is a pypdf-mangle, not a hallucination. Weaker normalizers miss
    real mangles (agtzidis's multiplication-sign renders as '/C2', derosa's "subject's" as "subject ' s")."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _classify_failure(quote: str, text: str, failure_reason: str | None) -> tuple[str, list[str]]:
    """Return (bucket, artifact_tags). bucket in {mangle, genuine-mismatch, ambiguous}."""
    if failure_reason == "quote_ambiguous":
        return "ambiguous", []
    if _hard(quote) and _hard(quote) in _hard(text):
        # present modulo ALL non-alphanumerics -> pypdf mangle. Tag the artifact(s).
        tags: list[str] = []
        if re.sub(r"\s+", "", quote.lower()) in re.sub(r"\s+", "", text.lower()):
            tags.append("whitespace/shattered")
        if re.search(r"\[\s*\d", text):
            tags.append("injected-marker")
        if re.search(r"-\s*\n", text):
            tags.append("hyphenation")
        if "/c" in text.lower() or "\u00d7" in quote:
            tags.append("unicode-mangle")
        return "mangle", tags or ["combined"]
    return "genuine-mismatch", []


def _value_in_quote(value: Any, quote: str) -> bool:
    """Does the model's own quote actually contain its claimed value? (mislocalization guard)."""
    v = _hard(str(value)) if value is not None else ""
    return bool(v) and v in _hard(quote)


def run(out_path: Path | None) -> int:
    cfg = load_batch_config(_V6_CONFIG)
    papers = [(p.paper_id, p.path) for p in cfg.papers if not is_excluded(p.paper_id)]
    client = build_client()
    cap: list[Any] = []
    client.on("completion:response", lambda response: cap.append(response))

    rows: list[dict[str, Any]] = []
    for pid, path in papers:
        text, _ = load_pdf_text(path)
        sl = find_methods_section(text).text
        paper = ParsedPaper(text=sl, source=pid, parser="pypdf", pdf_date=pdf_creation_date(path))
        cap.clear()
        prep, _d, _f = extract(paper, _MODEL, client=client, paper_date=paper.pdf_date)
        raw = _parse_json(cap[-1].choices[0].message.content) if cap else {}
        for field in _FIELDS:
            fv = raw.get(field)
            if not isinstance(fv, dict) or fv.get("status") != "extracted":
                continue
            quote = fv.get("verbatim_quote") or ""
            res = resolve_quote(quote, sl)
            final = _final_status(prep, field)
            resolved = res.span is not None
            row: dict[str, Any] = {
                "paper": pid,
                "field": field,
                "raw_value": fv.get("value"),
                "raw_quote": quote,
                "span_resolved": resolved,
                "failure_reason": res.failure_reason,
                "final": final,
            }
            if not resolved and final == "MISSING_FROM_PAPER":
                row["silent_drop"] = True
                bucket, tags = _classify_failure(quote, sl, res.failure_reason)
                row["why"], row["artifacts"] = bucket, tags
                row["value_in_quote"] = _value_in_quote(fv.get("value"), quote)
            else:
                row["silent_drop"] = False
            rows.append(row)
        print(f"  {pid}: captured", file=sys.stderr)

    if out_path is not None:
        out_path.write_text(render(rows))
        # auditable per-drop dump (full quotes) for reclassification + Phase 2, gitignored.
        jl = out_path.with_suffix(".jsonl")
        with jl.open("w") as fh:
            for r in rows:
                if r.get("silent_drop"):
                    fh.write(json.dumps(r) + "\n")
        print(f"Wrote {out_path} and {jl}")
    print("\n" + _summary(rows))
    return 0


def _summary(rows: list[dict[str, Any]]) -> str:
    drops = [r for r in rows if r.get("silent_drop")]
    by_field: dict[str, int] = {}
    for r in drops:
        by_field[r["field"]] = by_field.get(r["field"], 0) + 1
    genuine = [r for r in drops if r.get("why") == "genuine-mismatch"]
    ambig = [r for r in drops if r.get("why") == "ambiguous"]
    mangle = [r for r in drops if r.get("why") == "mangle"]
    recoverable = [r for r in mangle if r.get("value_in_quote")]
    value_mismatch = [r for r in mangle if not r.get("value_in_quote")]
    lines = [
        f"HEADLINE: {len(drops)} silent drops (raw=extracted, span=None, final=MISSING) "
        f"across {len({r['paper'] for r in drops})} papers.",
        f"By field: {by_field}",
        f"RECOVERABLE mangle (quote present + value in quote): {len(recoverable)} · "
        f"VALUE-MISMATCH mangle (quote present but value NOT in its own quote — do NOT recover): "
        f"{len(value_mismatch)} · genuine-mismatch (quote absent, hallucination-guard): "
        f"{len(genuine)} · ambiguous: {len(ambig)}",
    ]
    if genuine:
        lines.append("GENUINE-MISMATCH (quote content absent from source — must keep failing):")
        for r in genuine:
            lines.append(
                f"  - {r['paper']}.{r['field']}: {r['raw_value']!r} quote={r['raw_quote'][:70]!r}"
            )
    if value_mismatch:
        lines.append("VALUE-MISMATCH (quote present but does not contain its claimed value):")
        for r in value_mismatch:
            lines.append(
                f"  - {r['paper']}.{r['field']}: value={r['raw_value']!r} quote={r['raw_quote'][:70]!r}"
            )
    return "\n".join(lines)


def render(rows: list[dict[str, Any]]) -> str:
    drops = [r for r in rows if r.get("silent_drop")]
    lines = [
        "# Phase 1 — span-resolution hard-drop audit (measurement only)",
        "",
        f"Model {_MODEL}, temp 0, N=1 over the 19-paper corpus. For each field: RAW model output, "
        "whether production's resolve_quote() grounds the quote, and the FINAL four-state. A SILENT "
        "DROP = raw extracted + span None + final MISSING_FROM_PAPER.",
        "",
        _summary(rows).replace("HEADLINE", "## Headline\n\nHEADLINE"),
        "",
        "## Every silent drop",
        "",
        "| paper | field | raw_value | raw_quote (truncated) | why | value_in_quote | artifacts |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in drops:
        q = (r["raw_quote"][:80]).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r['paper']} | {r['field']} | {str(r['raw_value'])[:24]!r} | {q!r} | "
            f"{r.get('why')} ({r.get('failure_reason')}) | {r.get('value_in_quote')} | "
            f"{', '.join(r.get('artifacts', []))} |"
        )
    lines += [
        "",
        "## All extracted fields (drop or not) — the denominator",
        "",
        "| paper | field | span_resolved | final |",
        "|---|---|---|---|",
    ]
    for r in rows:
        flag = "**DROP**" if r.get("silent_drop") else ("ok" if r["span_resolved"] else "no-span")
        lines.append(
            f"| {r['paper']} | {r['field']} | {r['span_resolved']} | {r['final']} ({flag}) |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    return run(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
