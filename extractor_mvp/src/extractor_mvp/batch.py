"""Batch MVP runner over a folder of PDFs (PDFs only; no DOI fetching).

Per-paper status taxonomy:
    success            — extraction completed; n_extracted may be 0 (e.g. a paper
                         that defers preprocessing to a citation)
    pdf_parse_failed   — pypdf returned empty / errored
    methods_not_found  — methods heuristic fell back to full text; extraction STILL
                         ran (non-fatal). Manually review high-n_missing papers
                         with this flag — the wrong section may have been processed.
    extraction_failed  — the LLM call errored or returned malformed JSON

Per-paper errors are caught and logged; the batch continues. Spans in the JSON
output are given in BOTH forms: ``span_in_slice`` (offsets into the methods
slice the model saw) and ``span_in_full_paper`` (offsets into the full PDF text).
"""

from __future__ import annotations

import csv
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any

from extractor_mvp.batch_config import BatchConfig, load_batch_config
from extractor_mvp.extractor import extract_preprocessing
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text

# Multi-acquisition heuristic: ≥2 distinct DATASET mentions flags likely-multi.
# Pipeline tools alone don't flag (most papers cite several tools).
_DATASET_NAMES = ("HCP", "HNU", "MSC", "ABIDE", "UKBB")
_IGNORE_REASON = "not_targeted_by_mvp"  # the untargeted filler fields

SUMMARY_COLUMNS = [
    "paper_id",
    "path",
    "status",
    "parser",
    "methods_found_via",
    "methods_header_matched",
    "likely_multi_acquisition",
    "n_extracted",
    "n_deferred",
    "n_deferral_quote_unresolved",
    "n_missing_not_stated",
    "n_missing_quote_unresolved",
    "n_value_not_in_literal",
    "error_message",
]


@dataclasses.dataclass(frozen=True)
class PaperResult:
    paper_id: str
    path: str
    status: str
    parser: str | None
    methods_found_via: str | None
    methods_header_matched: str | None
    likely_multi_acquisition: bool
    n_extracted: int
    n_deferred: int
    n_deferral_quote_unresolved: int
    n_missing_not_stated: int
    n_missing_quote_unresolved: int
    n_value_not_in_literal: int
    extraction_json: dict[str, Any] | None
    error_message: str | None


def _count_distinct_datasets(text: str) -> int:
    return sum(1 for name in _DATASET_NAMES if re.search(rf"\b{name}\b", text))


def _tally(preprocessing: Any) -> dict[str, int]:
    """Bucket the targeted fields by outcome (untargeted fillers ignored)."""
    counts = {
        "n_extracted": 0,
        "n_deferred": 0,
        "n_deferral_quote_unresolved": 0,
        "n_missing_not_stated": 0,
        "n_missing_quote_unresolved": 0,
        "n_value_not_in_literal": 0,
    }
    for step in preprocessing.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            if pf.extraction.status == "EXTRACTED":
                counts["n_extracted"] += 1
                continue
            if pf.extraction.status == "DEFERRED_TO_CITATION":
                counts["n_deferred"] += 1
                continue
            reason = getattr(pf.inference, "reason", None) or ""
            if reason == _IGNORE_REASON:
                continue
            if reason.startswith("deferral_quote_unresolved"):
                counts["n_deferral_quote_unresolved"] += 1
            elif reason == "not_stated_in_text":
                counts["n_missing_not_stated"] += 1
            elif reason.startswith("extraction_quote_unresolved"):
                counts["n_missing_quote_unresolved"] += 1
            elif reason == "value_not_in_literal":
                counts["n_value_not_in_literal"] += 1
    return counts


def _translate_spans(prep_dump: dict[str, Any], start_offset: int) -> None:
    """Add ``span_in_slice`` / ``span_in_full_paper`` to every extracted span.

    The model's spans are offsets into the methods slice; add the slice's
    ``start_offset`` to recover full-paper offsets. Mutates in place.
    """
    for step in prep_dump.get("steps", []):
        for value in step.values():
            if not isinstance(value, dict):
                continue
            extraction = value.get("extraction")
            if not isinstance(extraction, dict) or extraction.get("status") != "EXTRACTED":
                continue
            for span in extraction.get("spans", []):
                s, e = span["start"], span["end"]
                span["span_in_slice"] = {"start": s, "end": e}
                span["span_in_full_paper"] = {"start": s + start_offset, "end": e + start_offset}


def _process_paper(paper_id: str, path: Path, model: str) -> PaperResult:
    text, parser = load_pdf_text(path)
    if parser == "failed":
        return PaperResult(
            paper_id,
            str(path),
            "pdf_parse_failed",
            None,
            None,
            None,
            False,
            0,  # n_extracted
            0,  # n_deferred
            0,  # n_deferral_quote_unresolved
            0,  # n_missing_not_stated
            0,  # n_missing_quote_unresolved
            0,  # n_value_not_in_literal
            None,
            "pypdf returned no text",
        )

    methods = find_methods_section(text)
    multi = _count_distinct_datasets(methods.text) >= 2
    paper = ParsedPaper(text=methods.text, source=paper_id, parser="pypdf")

    try:
        preprocessing, diagnostics, deferrals = extract_preprocessing(paper, model)
    except Exception as exc:  # LLM/transport/validation error -> recorded, batch continues
        return PaperResult(
            paper_id,
            str(path),
            "extraction_failed",
            parser,
            methods.found_via,
            methods.matched_header,
            multi,
            0,  # n_extracted
            0,  # n_deferred
            0,  # n_deferral_quote_unresolved
            0,  # n_missing_not_stated
            0,  # n_missing_quote_unresolved
            0,  # n_value_not_in_literal
            None,
            f"{type(exc).__name__}: {exc}",
        )

    counts = _tally(preprocessing)
    prep_dump = preprocessing.model_dump(mode="json")
    _translate_spans(prep_dump, methods.start_offset)
    extraction_json = {
        "methods": {
            "found_via": methods.found_via,
            "matched_header": methods.matched_header,
            "start_offset": methods.start_offset,
        },
        "likely_multi_acquisition": multi,
        "counts": counts,
        "preprocessing": prep_dump,
        "diagnostics": [dataclasses.asdict(d) for d in diagnostics],
        # Fork B reads deferred_fields to drive citation resolution without parsing
        # the provenance coupling. target_kind is the ORIGINAL LLM value (incl
        # "supplement"); pending_resolution flags fields awaiting Fork B.
        "deferred_fields": [dataclasses.asdict(d) for d in deferrals],
    }
    status = "methods_not_found" if methods.found_via == "fallback_full_text" else "success"
    return PaperResult(
        paper_id,
        str(path),
        status,
        parser,
        methods.found_via,
        methods.matched_header,
        multi,
        counts["n_extracted"],
        counts["n_deferred"],
        counts["n_deferral_quote_unresolved"],
        counts["n_missing_not_stated"],
        counts["n_missing_quote_unresolved"],
        counts["n_value_not_in_literal"],
        extraction_json,
        None,
    )


def run_batch(config: BatchConfig) -> list[PaperResult]:
    """Process all papers; per-paper errors are caught so the batch continues."""
    papers_dir = config.output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    results: list[PaperResult] = []

    for paper in config.papers:
        result = _process_paper(paper.paper_id, paper.path, config.model)
        results.append(result)
        if result.extraction_json is not None:
            (papers_dir / f"{paper.paper_id}.json").write_text(
                json.dumps(
                    {
                        "paper_id": result.paper_id,
                        "path": result.path,
                        "status": result.status,
                        **result.extraction_json,
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        # loud on failure, quiet on success
        if result.status in ("pdf_parse_failed", "extraction_failed"):
            print(
                f"  FAIL {paper.paper_id}: {result.status} — {result.error_message}",
                file=sys.stderr,
            )
        else:
            flags = []
            if result.status == "methods_not_found":
                flags.append("methods_not_found")
            if result.likely_multi_acquisition:
                flags.append("likely_multi_acquisition")
            suffix = f" [{', '.join(flags)}]" if flags else ""
            print(f"  ok   {paper.paper_id}: {result.n_extracted} extracted{suffix}")

    _write_summary_csv(config.output_dir / "summary.csv", results)
    _write_summary_md(config.output_dir / "summary.md", results)
    _print_rollup(results, config.output_dir)
    return results


def _write_summary_csv(path: Path, results: list[PaperResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        w.writeheader()
        for r in results:
            w.writerow({k: getattr(r, k) for k in SUMMARY_COLUMNS})


def _write_summary_md(path: Path, results: list[PaperResult]) -> None:
    rows = sorted(results, key=lambda r: (r.status, r.paper_id))
    header = "| " + " | ".join(SUMMARY_COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in SUMMARY_COLUMNS) + " |"
    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(getattr(r, k)) for k in SUMMARY_COLUMNS) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_rollup(results: list[PaperResult], output_dir: Path) -> None:
    ok = [r for r in results if r.status in ("success", "methods_not_found")]
    failed = [r for r in results if r.status in ("pdf_parse_failed", "extraction_failed")]
    x = sum(r.n_extracted for r in ok)
    d = sum(r.n_deferred for r in ok)
    y = sum(r.n_missing_not_stated for r in ok)
    z = sum(r.n_missing_quote_unresolved for r in ok)
    w = sum(r.n_value_not_in_literal for r in ok)
    print(
        f"Processed {len(results)} papers ({len(ok)} successful, {len(failed)} failed). "
        f"Across successes: {x} fields extracted with spans, {d} deferred-to-citation, "
        f"{y} missing-not-stated, {z} quote-unresolved, {w} value-not-in-literal."
    )
    print(f"Summary: {output_dir / 'summary.csv'} , {output_dir / 'summary.md'}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", required=True, type=Path, help="batch config YAML")
    args = parser.parse_args(argv)
    if not args.config.is_file():
        print(f"ERROR: config not found: {args.config}", file=sys.stderr)
        return 1
    run_batch(load_batch_config(args.config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
