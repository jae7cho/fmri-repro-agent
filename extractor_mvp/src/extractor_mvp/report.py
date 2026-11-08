#!/usr/bin/env python3
"""One PDF in, one COBIDAS completeness report out — Track A item A4.

    aespa-report paper.pdf
    python -m extractor_mvp.report paper.pdf --output paper.md

A thin shell over :func:`extractor_mvp.full_report.run_paper` (2026-11-05, fix 2): the fMRI gate,
``process_paper`` (``load_pdf_text`` → ``find_methods_section`` → ``extract`` with the checking pass
and the KB inference arm), the citation hop for every paper or supplement a field defers to, call R
(the paper's data release) and the KB software scan, then the report with the hop section. Every
model call is metered. Before fix 2 this ran ``process_paper`` alone, with no hop and no cost record.

**The run record.** Beside the report (``--output x.md`` → ``x.record.json``, or ``--record``): the
paper JSON as ``run_batch`` writes it, the hop's inputs, and ``run``: one entry per attempt of every
call (label, attempt, wall time, tokens, cost, finish reason, parse error) with the totals. A retry
is an attempt above 1. The totals are also printed to stderr.

``demo.py`` is not the host. It calls ``extract_preprocessing`` (demo.py:71) while the batch
path calls ``extract`` (batch.py:30), so it sits on the older entry point and was skipped by
the migration that moved every other runner.

**Exit code.** 0 when a report was produced, 1 when none was. A paper whose methods section
could not be located still produces a report — the slice warning is rendered into it — so
that is a note on stderr, not a failure. ``process_paper`` never raises for a bad paper; it
returns the failure on the result, which is right for a batch and wrong for one paper, so the
inspection happens here.

**Cost.** This command makes a billed model call. Rendering an EXISTING result costs nothing
and needs no network: see ``scripts/rerender_reports.py``, which replays stored per-paper
JSON through the current renderer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from extractor_mvp.full_report import run_paper

#: All 21 tracked batch configs name this model, so a single-paper run defaults to it and the
#: printed command stays short. Override with --model.
DEFAULT_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="aespa-report",
        description="Extract preprocessing from a paper PDF and write a COBIDAS "
        "completeness report.",
    )
    ap.add_argument("pdf", type=Path, help="path to the paper PDF")
    ap.add_argument(
        "--output",
        type=Path,
        help="write the report here (default: stdout). Parent directories are created.",
    )
    ap.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"LiteLLM model id (default: {DEFAULT_MODEL})"
    )
    ap.add_argument(
        "--corpus",
        type=Path,
        action="append",
        help="a folder of local PDFs the citation hop searches for a cited paper (repeatable; "
        "default: the PDF's own folder)",
    )
    ap.add_argument(
        "--record",
        type=Path,
        help="write the run record (paper JSON, hop inputs, per-call log) here (default: beside "
        "--output as <stem>.record.json; none when writing the report to stdout)",
    )
    ap.add_argument(
        "--paper-id",
        help="identifier used as the report's title and span source (default: the PDF filename stem)",
    )
    ap.add_argument(
        "--text-source",
        choices=("pypdf", "grobid"),
        default=None,
        help="the text layer: GROBID's TEI body from a running server (default; "
        "AESPA_GROBID_URL, default http://localhost:8070), falling back to pypdf when it is "
        "unreachable, or pypdf. Same as AESPA_TEXT_SOURCE.",
    )
    args = ap.parse_args(argv)
    if args.text_source is not None:
        import os

        from extractor_mvp.grobid_source import TEXT_SOURCE_ENV

        os.environ[TEXT_SOURCE_ENV] = args.text_source

    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    paper_id = args.paper_id or pdf.stem
    corpus = [p.expanduser().resolve() for p in (args.corpus or [pdf.parent])]
    full = run_paper(paper_id, pdf, args.model, corpus)
    result = full.first
    assert result is not None

    record_path = args.record or (
        args.output.with_suffix(".record.json") if args.output is not None else None
    )
    if record_path is not None and full.record is not None:
        rp = record_path.expanduser().resolve()
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(full.record, indent=1, default=str), encoding="utf-8")
        print(f"wrote {rp}", file=sys.stderr)
    cost = f"${full.cost_usd:.4f}" if full.cost_usd is not None else "cost unknown"
    print(
        f"{paper_id}: {full.status} · {len(full.calls)} calls · {full.retries} retries · "
        f"{sum(1 for c in full.calls if c.get('parse_error'))} parse errors · {cost} · "
        f"{full.wall_s} s",
        file=sys.stderr,
    )

    if full.report is None:
        detail = result.render_error or result.error_message or "no report was produced"
        print(f"FAILED {paper_id} [{result.status}]: {detail}", file=sys.stderr)
        return 1

    if args.output is None:
        sys.stdout.write(full.report)
    else:
        out = args.output.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(full.report, encoding="utf-8")
        print(f"wrote {out}")

    if full.status not in ("success", "not_fmri"):
        # methods_not_found is the live case: extraction ran on the full document and the
        # report carries its own slice warning, so the report stands and this is a note.
        print(f"note: status={result.status}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
