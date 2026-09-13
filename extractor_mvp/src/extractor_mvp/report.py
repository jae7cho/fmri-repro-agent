#!/usr/bin/env python3
"""One PDF in, one COBIDAS completeness report out — Track A item A4.

    aespa-report paper.pdf
    python -m extractor_mvp.report paper.pdf --output paper.md

A thin shell over :func:`extractor_mvp.batch.process_paper`, which already runs the whole
chain: ``load_pdf_text`` → ``find_methods_section`` → ``ParsedPaper`` → ``extract`` →
``to_report``. A1 (``214b55c``) assembled that; this module only supplies the argv surface,
a paper id, a model, the write, and an exit code.

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
import sys
from pathlib import Path

from extractor_mvp.batch import process_paper

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
        "--paper-id",
        help="identifier used as the report's title and span source (default: the PDF filename stem)",
    )
    args = ap.parse_args(argv)

    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    paper_id = args.paper_id or pdf.stem
    result = process_paper(paper_id, pdf, args.model)

    if result.report is None:
        detail = result.render_error or result.error_message or "no report was produced"
        print(f"FAILED {paper_id} [{result.status}]: {detail}", file=sys.stderr)
        return 1

    if args.output is None:
        sys.stdout.write(result.report)
    else:
        out = args.output.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.report, encoding="utf-8")
        print(f"wrote {out}")

    if result.status != "success":
        # methods_not_found is the live case: extraction ran on the full document and the
        # report carries its own slice warning, so the report stands and this is a note.
        print(f"note: status={result.status}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
