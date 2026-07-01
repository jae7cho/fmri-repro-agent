"""CLI: text-in, JSON-out. Runs the MVP extractor and prints a per-field summary.

    python -m extractor_mvp.demo --text examples/schwartz_2018_methods.txt \\
        --model bedrock/us.anthropic.claude-sonnet-4-6 \\
        --output results/schwartz_2018.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from extractor_mvp.extractor import extract_preprocessing
from extractor_mvp.parsed_paper import ParsedPaper


def _iter_provenanced_fields(preprocessing: Any) -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    for step in preprocessing.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            if hasattr(pf, "extraction"):
                out.append((f"{step.kind}.{pf.field_id}", pf))
    return out


def summarize(preprocessing: Any) -> dict[str, Any]:
    fields = _iter_provenanced_fields(preprocessing)
    extracted = [fid for fid, pf in fields if pf.extraction.status == "EXTRACTED"]
    deferred = [fid for fid, pf in fields if pf.extraction.status == "DEFERRED_TO_CITATION"]
    missing_reasons: Counter[str] = Counter()
    for _, pf in fields:
        if pf.extraction.status == "MISSING_FROM_PAPER":
            missing_reasons[getattr(pf.inference, "reason", None) or "unspecified"] += 1
    return {
        "extracted_fields": extracted,
        "n_extracted": len(extracted),
        "deferred_fields": deferred,
        "n_deferred": len(deferred),
        "n_missing": sum(missing_reasons.values()),
        "missing_by_reason": dict(missing_reasons),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--text", required=True, type=Path, help="path to a methods-text file")
    parser.add_argument("--model", required=True, help="LiteLLM model id")
    parser.add_argument("--output", type=Path, help="write JSON here (else stdout)")
    parser.add_argument("--parser", default="manual", choices=["pdftotext", "marker", "manual"])
    args = parser.parse_args(argv)

    if not args.text.is_file():
        print(f"ERROR: text file not found: {args.text}", file=sys.stderr)
        return 1

    paper = ParsedPaper(
        text=args.text.read_text(encoding="utf-8"),
        source=args.text.name,
        parser=args.parser,
    )
    preprocessing, diagnostics, deferrals = extract_preprocessing(paper, args.model)

    payload = {
        "source": paper.source,
        "model": args.model,
        "preprocessing": preprocessing.model_dump(mode="json"),
        "diagnostics": [dataclasses.asdict(d) for d in diagnostics],
        "deferred_fields": [dataclasses.asdict(d) for d in deferrals],
        "summary": summarize(preprocessing),
    }
    text = json.dumps(payload, indent=2, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")

    s = payload["summary"]
    print(f"=== MVP extraction: {paper.source} ({args.model}) ===")
    print(
        f"Extracted {s['n_extracted']} fields with spans: {', '.join(s['extracted_fields']) or '(none)'}"
    )
    print(
        f"DeferredToCitation {s['n_deferred']} fields: {', '.join(s['deferred_fields']) or '(none)'}"
    )
    print(f"MissingFromPaper {s['n_missing']} fields, by reason:")
    for reason, n in sorted(s["missing_by_reason"].items()):
        print(f"    {reason}: {n}")
    if diagnostics:
        print(f"Diagnostics ({len(diagnostics)}):")
        for d in diagnostics:
            print(
                f"    {d.field}: {d.failure_reason} (value={d.raw_value!r}, quote={d.raw_quote!r})"
            )
    if args.output:
        print(f"\nJSON -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
