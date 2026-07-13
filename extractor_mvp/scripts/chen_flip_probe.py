"""Per-draw evidence for chen_2015's flipping fields (K=20, temp 0, fixed input).

DIAGNOSTIC ONLY. Changes no extraction logic, prompt, schema, temperature, or max_retries.
Answers WHY chen · temporal_standardization.method flips EXTRACTED/MISSING on byte-identical
input, by capturing the model's own words per draw.

The schema (extractor_mvp.extraction_result.FieldExtractionResult) has NO reasoning field:
status + value + verbatim_quote on EXTRACTED, searched_terms + sections_searched on MISSING.
So "reasoning" here = exactly those, captured from the ONE existing extraction call via a
read-only instructor `completion:response` hook — no rationale field, no second LLM call.

Capturing the RAW LLM response (not the post-processed Preprocessing) is deliberate: it is the
model's answer before Python span-resolution, so it separates "the LLM flipped status" from
"the LLM said EXTRACTED but the span didn't resolve -> final MISSING". Both are reported.

Off by default. Run by path:
    python scripts/chen_flip_probe.py --k 20 --out results/CHEN_FLIP_RAW.md
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from extractor_mvp.extractor import build_client, extract
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date

_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # the v6-pinned model
_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
_PDF = "Chen_2015.pdf"

# The response-model field names to capture per draw (attrs on PreprocessingExtraction).
_TARGET = "temporal_standardization_method"  # the state flip under investigation
_CONTRAST = "base_pipeline_name"  # the "CCS (CCS)" / "CCS" value wobble
_ADJACENT = ["intensity_convention", "intensity_value"]  # bleed hypothesis (grand-mean 10000)
_CAPTURE = [_TARGET, _CONTRAST, *_ADJACENT]


def _norm(s: str | None) -> str:
    return " ".join(s.split()) if s else ""


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


def _raw_field(raw: dict[str, Any] | None, name: str) -> dict[str, Any]:
    """The model's raw FieldExtractionResult for one field, defensively normalized."""
    fv = (raw or {}).get(name)
    if not isinstance(fv, dict):
        return {"status": "?", "value": None, "quote": "", "searched": [], "sections": []}
    return {
        "status": fv.get("status"),
        "value": fv.get("value"),
        "quote": _norm(fv.get("verbatim_quote")),
        "searched": fv.get("searched_terms") or [],
        "sections": fv.get("sections_searched") or [],
    }


def _final_temporal_state(prep: Any) -> str:
    """The post-processed four-state of temporal_standardization.method (for the raw-vs-final check)."""
    for s in prep.steps:
        if s.kind == "temporal_standardization":
            f = getattr(s, "method", None)
            if f is not None:
                ext = f.extraction
                return f"{ext.status}:{ext.value if ext.status == 'EXTRACTED' else None}"
    return "ABSENT"


def run(k: int) -> tuple[list[dict[str, Any]], str]:
    client = build_client()
    captured: list[Any] = []
    client.on("completion:response", lambda response: captured.append(response))

    text, _ = load_pdf_text(_CORPUS / _PDF)
    slice_text = find_methods_section(text).text  # canonical input, reused every run
    canon_hash = hashlib.sha256(slice_text.encode()).hexdigest()[:16]
    paper = ParsedPaper(
        text=slice_text,
        source="chen_2015",
        parser="pypdf",
        pdf_date=pdf_creation_date(_CORPUS / _PDF),
    )

    rows: list[dict[str, Any]] = []
    for i in range(k):
        # Recompute the slice each run and assert byte-identity: catch any nondeterminism
        # UPSTREAM of the LLM (pypdf / find_methods_section). If it differs, STOP.
        rerun_hash = hashlib.sha256(
            find_methods_section(load_pdf_text(_CORPUS / _PDF)[0]).text.encode()
        ).hexdigest()[:16]
        if rerun_hash != canon_hash:
            raise SystemExit(
                f"STOP: methods slice not byte-identical across runs "
                f"({rerun_hash} != {canon_hash} at run {i + 1}). Upstream nondeterminism — "
                f"report, do not average over it."
            )
        captured.clear()
        prep, _d, _f = extract(paper, _MODEL, client=client, paper_date=paper.pdf_date)
        # extract() makes exactly one completion call; take the last captured response (the
        # accepted one, were a reask ever to fire).
        raw = _parse_json(captured[-1].choices[0].message.content) if captured else None
        row: dict[str, Any] = {"run": i + 1, "attempts": len(captured)}
        for name in _CAPTURE:
            row[name] = _raw_field(raw, name)
        row["final_temporal"] = _final_temporal_state(prep)
        rows.append(row)
        tf = row[_TARGET]
        print(
            f"  run {i + 1}/{k}: temporal={tf['status']} final={row['final_temporal']}",
            file=sys.stderr,
        )
    return rows, canon_hash


def _quote_groups(rows: list[dict[str, Any]], field: str, status: str) -> list[tuple[str, int]]:
    c = collections.Counter(r[field]["quote"] for r in rows if r[field]["status"] == status)
    return c.most_common()


def render_raw(rows: list[dict[str, Any]], canon_hash: str, k: int) -> str:
    lines = [
        f"# chen_2015 flip probe — raw per-draw dump (K={k}, temp 0, fixed input)",
        "",
        f"Model {_MODEL}; methods-slice sha256[:16] = `{canon_hash}` (byte-identical every run). "
        "Fields are the RAW model FieldExtractionResult (verbatim_quote / searched_terms), captured "
        "from the single extraction call via a read-only hook, before span resolution.",
        "",
    ]
    for r in rows:
        lines.append(
            f"## run {r['run']} (attempts={r['attempts']}, final_temporal={r['final_temporal']})"
        )
        for name in _CAPTURE:
            f = r[name]
            lines.append(f"- **{name}**: `{f['status']}` value={f['value']!r}")
            if f["status"] == "extracted":
                lines.append(f"    - quote: {f['quote']!r}")
            else:
                lines.append(
                    f"    - searched_terms={f['searched']} sections_searched={f['sections']}"
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_finding(rows: list[dict[str, Any]], canon_hash: str, k: int) -> str:
    ext = [r for r in rows if r[_TARGET]["status"] == "extracted"]
    miss = [r for r in rows if r[_TARGET]["status"] == "missing"]
    other = [r for r in rows if r[_TARGET]["status"] not in ("extracted", "missing")]
    tgroups = _quote_groups(rows, _TARGET, "extracted")

    # diagnosis heuristic from the quote content
    def _bucket(q: str) -> str:
        ql = q.lower()
        if "10,000" in ql or "10000" in ql or "global mean intensity" in ql:
            return "BLEED (intensity grand-mean sentence)"
        if "reho" in ql or ("mean" in ql and "variance" in ql):
            return "REFERENT-BINDING (ReHo/connectivity z-scoring)"
        return "OTHER"

    buckets = collections.Counter(_bucket(q) for q, _ in tgroups for _ in range(1))
    distinct_quotes = len(tgroups)
    if distinct_quotes == 0:
        diagnosis = "No EXTRACTED draws — cannot diagnose from quotes; field simply not extracted."
    elif distinct_quotes > 1 and not buckets:
        diagnosis = "UNDER-CONSTRAINED: different EXTRACTED draws cite DIFFERENT sentences."
    elif "BLEED" in " ".join(buckets):
        diagnosis = "FIELD BLEED: intensity_normalization grand-mean sentence leaking into temporal_standardization."
    elif "REFERENT" in " ".join(buckets):
        diagnosis = (
            "REFERENT-BINDING error: connectivity/ReHo z-scoring mis-bound to the BOLD signal."
        )
    elif distinct_quotes == 1:
        diagnosis = (
            f"SINGLE DRIVER: every EXTRACTED draw cites one quote ({_bucket(tgroups[0][0])})."
        )
    else:
        diagnosis = "MIXED — inspect the quote table."

    lines = [
        "# Finding: why chen · temporal_standardization.method flips",
        "",
        f"**Harness:** `extractor_mvp/scripts/chen_flip_probe.py` · **Model (pinned):** {_MODEL}, "
        f"temperature 0 · **K={k}** on byte-identical input (methods-slice sha256[:16] `{canon_hash}`).",
        "Raw per-draw dump: `extractor_mvp/results/CHEN_FLIP_RAW.md` (gitignored).",
        "",
        "## temporal_standardization.method across the draws",
        "",
        f"- EXTRACTED: **{len(ext)}/{k}** ({100 * len(ext) / k:.0f}%) · MISSING: **{len(miss)}/{k}** "
        f"({100 * len(miss) / k:.0f}%)" + (f" · other: {len(other)}" if other else ""),
        "",
        "### EXTRACTED draws grouped by verbatim_quote (the key output)",
        "",
    ]
    if tgroups:
        lines.append("| count | bucket | verbatim_quote |")
        lines.append("|---|---|---|")
        for q, n in tgroups:
            lines.append(f"| {n} | {_bucket(q)} | {q!r} |".replace("\n", " "))
    else:
        lines.append("_(no EXTRACTED draws)_")
    lines += [
        "",
        "### MISSING draws — searched_terms / sections_searched",
        "",
    ]
    if miss:
        sterms = collections.Counter(t for r in miss for t in r[_TARGET]["searched"])
        ssec = collections.Counter(s for r in miss for s in r[_TARGET]["sections"])
        distinct_searched = {tuple(sorted(r[_TARGET]["searched"])) for r in miss}
        lines.append(f"- searched_terms union (count): {dict(sterms)}")
        lines.append(f"- sections_searched union (count): {dict(ssec)}")
        lines.append(
            f"- distinct searched_terms sets across MISSING runs: {len(distinct_searched)}"
        )
    else:
        lines.append("_(no MISSING draws)_")
    lines += [
        "",
        "### Cross-check: intensity fields on EXTRACTED-temporal runs (bleed test)",
        "",
        "| run | temporal quote | intensity_convention | intensity_value | int_value quote |",
        "|---|---|---|---|---|",
    ]
    for r in ext:
        ic, iv = r["intensity_convention"], r["intensity_value"]
        lines.append(
            f"| {r['run']} | {r[_TARGET]['quote'][:50]!r} | {ic['status']}:{ic['value']} | "
            f"{iv['status']}:{iv['value']} | {iv['quote'][:50]!r} |".replace("\n", " ")
        )
    # base_pipeline_name value wobble
    bp_ext = [r for r in rows if r[_CONTRAST]["status"] == "extracted"]
    bp_valgroups = collections.Counter(
        (r[_CONTRAST]["value"], r[_CONTRAST]["quote"]) for r in bp_ext
    )
    lines += [
        "",
        "## base_pipeline_name value wobble (phrasing vs source ambiguity)",
        "",
        "| count | value | verbatim_quote |",
        "|---|---|---|",
    ]
    for (val, q), n in bp_valgroups.most_common():
        lines.append(f"| {n} | {val!r} | {q!r} |".replace("\n", " "))
    distinct_bp_quotes = len({q for (_, q) in bp_valgroups})
    lines += [
        "",
        f"base_pipeline distinct values={len({v for (v, _) in bp_valgroups})}, "
        f"distinct quotes={distinct_bp_quotes} → "
        + (
            "SAME sentence, different rendering (phrasing-only wobble)."
            if distinct_bp_quotes <= 1
            else "DIFFERENT sentences cited (source ambiguity, not just phrasing)."
        ),
        "",
        "## Diagnosis",
        "",
        diagnosis,
        "",
        "Caveat: K=20, one paper; the split is a point estimate (see [variance finding](variance.md)). "
        "The diagnosis is driven by the quote grouping above, quoted verbatim.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--out", type=Path, default=None, help="raw per-draw dump path")
    ap.add_argument("--finding", type=Path, default=None, help="finding summary path")
    args = ap.parse_args(argv)

    rows, canon_hash = run(args.k)
    raw_md = render_raw(rows, canon_hash, args.k)
    finding_md = render_finding(rows, canon_hash, args.k)

    if args.out is not None:
        args.out.write_text(raw_md)
        print(f"Wrote {args.out}")
    if args.finding is not None:
        args.finding.write_text(finding_md)
        print(f"Wrote {args.finding}")
    # Always print the finding (the quote table is the point).
    print("\n" + finding_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
