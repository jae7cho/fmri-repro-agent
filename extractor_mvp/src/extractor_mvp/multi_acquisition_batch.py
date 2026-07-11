"""Fork C batch: two-pass multi-acquisition extraction over a folder of PDFs.

Mirrors ``batch.py`` but uses :func:`extract_multi_acquisition`. Status taxonomy
adds ``no_acquisitions_found`` (Pass 1 returned zero). Output -> the config's
``output_dir`` (e.g. results/batch_multi_acq/).
"""

from __future__ import annotations

import csv
import dataclasses
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from extractor_mvp.batch import _tally, _translate_spans
from extractor_mvp.batch_config import BatchConfig, load_batch_config
from extractor_mvp.batch_utils import build_citation_resolver
from extractor_mvp.field_diff import compute_field_diffs
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.multi_acquisition_extractor import extract_multi_acquisition
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date

if TYPE_CHECKING:
    from extractor_mvp.citation_resolver import CitationResolver

SUMMARY_COLUMNS = [
    "paper_id",
    "path",
    "status",
    "parser",
    "methods_found_via",
    "methods_header_matched",
    "n_acquisitions",
    "acquisition_ids",
    "n_extracted_total",
    "n_missing_total",
    "n_quote_unresolved_total",
    "n_value_not_in_literal_total",
    "n_fully_shared_fields",
    "n_acquisition_specific_fields",
    "n_partially_shared_fields",
    "error_message",
]


@dataclasses.dataclass(frozen=True)
class MultiAcquisitionPaperResult:
    paper_id: str
    path: str
    status: str
    parser: str | None
    methods_found_via: str | None
    methods_header_matched: str | None
    n_acquisitions: int
    acquisition_ids: list[str]
    n_extracted_total: int
    n_missing_total: int
    n_quote_unresolved_total: int
    n_value_not_in_literal_total: int
    n_fully_shared_fields: int
    n_acquisition_specific_fields: int
    n_partially_shared_fields: int
    result_json: dict[str, Any] | None
    error_message: str | None


def _empty(
    paper_id: str, path: Path, status: str, parser: str | None, msg: str
) -> MultiAcquisitionPaperResult:
    return MultiAcquisitionPaperResult(
        paper_id,
        str(path),
        status,
        parser,
        None,
        None,
        0,
        [],
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        None,
        msg,
    )


def _process_paper(
    paper_id: str, path: Path, model: str, citation_resolver: CitationResolver | None = None
) -> MultiAcquisitionPaperResult:
    text, parser = load_pdf_text(path)
    if parser == "failed":
        return _empty(paper_id, path, "pdf_parse_failed", None, "pypdf returned no text")

    methods = find_methods_section(text)
    paper = ParsedPaper(
        text=methods.text, source=paper_id, parser="pypdf", pdf_date=pdf_creation_date(path)
    )
    try:
        result = extract_multi_acquisition(
            paper, model, citation_resolver=citation_resolver, paper_date=paper.pdf_date
        )
    except Exception as exc:  # Pass 1/2 transport or validation error
        return MultiAcquisitionPaperResult(
            paper_id,
            str(path),
            "extraction_failed",
            parser,
            methods.found_via,
            methods.matched_header,
            0,
            [],
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            f"{type(exc).__name__}: {exc}",
        )

    acq_ids = [a.acquisition_id for a in result.discovery.acquisitions]
    if not acq_ids:
        return _empty(
            paper_id, path, "no_acquisitions_found", parser, "Pass 1 found 0 acquisitions"
        )

    # per-acquisition tallies (summed) + field diffs
    totals = {
        "n_extracted": 0,
        "n_missing_not_stated": 0,
        "n_missing_quote_unresolved": 0,
        "n_value_not_in_literal": 0,
    }
    for prep in result.extractions.values():
        for k, v in _tally(prep).items():
            totals[k] += v
    diffs = compute_field_diffs(result)
    by_class = {
        c: sum(1 for d in diffs if d.classification == c)
        for c in ("fully_shared", "acquisition_specific", "partially_shared")
    }

    # serialize: per-acquisition Preprocessing (spans translated to full-paper offsets)
    acquisitions_json: dict[str, Any] = {}
    for acq_id, prep in result.extractions.items():
        dump = prep.model_dump(mode="json")
        _translate_spans(dump, methods.start_offset)
        acquisitions_json[acq_id] = {
            "preprocessing": dump,
            "diagnostics": [dataclasses.asdict(d) for d in result.diagnostics.get(acq_id, [])],
        }
    # acquisitions that failed Pass 2 (in diagnostics but not extractions)
    for acq_id, diags in result.diagnostics.items():
        if acq_id not in acquisitions_json:
            acquisitions_json[acq_id] = {
                "preprocessing": None,
                "diagnostics": [dataclasses.asdict(d) for d in diags],
            }

    result_json = {
        "methods": {
            "found_via": methods.found_via,
            "matched_header": methods.matched_header,
            "start_offset": methods.start_offset,
            "end_offset": methods.end_offset,
            "slice_ratio": methods.slice_ratio,
            "ended_at": methods.ended_at,
            "suspicious": methods.suspicious,
        },
        "discovery": result.discovery.model_dump(mode="json"),
        "acquisitions": acquisitions_json,
        "field_diffs": [dataclasses.asdict(d) for d in diffs],
    }
    status = "methods_not_found" if methods.found_via == "fallback_full_text" else "success"
    return MultiAcquisitionPaperResult(
        paper_id,
        str(path),
        status,
        parser,
        methods.found_via,
        methods.matched_header,
        len(acq_ids),
        acq_ids,
        totals["n_extracted"],
        totals["n_missing_not_stated"],
        totals["n_missing_quote_unresolved"],
        totals["n_value_not_in_literal"],
        by_class["fully_shared"],
        by_class["acquisition_specific"],
        by_class["partially_shared"],
        result_json,
        None,
    )


def run_multi_acquisition_batch(config: BatchConfig) -> list[MultiAcquisitionPaperResult]:
    papers_dir = config.output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    citation_resolver = build_citation_resolver(config)
    results: list[MultiAcquisitionPaperResult] = []
    for paper in config.papers:
        r = _process_paper(paper.paper_id, paper.path, config.model, citation_resolver)
        results.append(r)
        if r.result_json is not None:
            (papers_dir / f"{paper.paper_id}.json").write_text(
                json.dumps(
                    {"paper_id": r.paper_id, "path": r.path, "status": r.status, **r.result_json},
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        if r.status in ("pdf_parse_failed", "extraction_failed", "no_acquisitions_found"):
            print(f"  FAIL {paper.paper_id}: {r.status} — {r.error_message}", file=sys.stderr)
        else:
            flag = " [methods_not_found]" if r.status == "methods_not_found" else ""
            print(
                f"  ok   {paper.paper_id}: {r.n_acquisitions} acq {r.acquisition_ids} | "
                f"{r.n_extracted_total} extracted, {r.n_fully_shared_fields} shared, "
                f"{r.n_acquisition_specific_fields} acq-specific{flag}"
            )

    _write_summary(config.output_dir, results)
    print(f"\nProcessed {len(results)} papers. Summary: {config.output_dir / 'summary.csv'}")
    return results


def _write_summary(output_dir: Path, results: list[MultiAcquisitionPaperResult]) -> None:
    def row(r: MultiAcquisitionPaperResult) -> dict[str, Any]:
        d = {k: getattr(r, k) for k in SUMMARY_COLUMNS if k != "acquisition_ids"}
        d["acquisition_ids"] = ";".join(r.acquisition_ids)
        return d

    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        w.writeheader()
        for r in results:
            w.writerow(row(r))
    lines = [
        "| " + " | ".join(SUMMARY_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in SUMMARY_COLUMNS) + " |",
    ]
    for r in sorted(results, key=lambda x: (x.status, x.paper_id)):
        rd = row(r)
        lines.append("| " + " | ".join(str(rd[c]) for c in SUMMARY_COLUMNS) + " |")
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.config.is_file():
        print(f"ERROR: config not found: {args.config}", file=sys.stderr)
        return 1
    run_multi_acquisition_batch(load_batch_config(args.config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
