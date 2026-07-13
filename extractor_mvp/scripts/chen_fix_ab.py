"""A/B capture for the temporal_standardization firewall test (temp 0, pinned model).

DIAGNOSTIC harness for a scoped prompt A/B. This script itself changes nothing — it runs the
UNCHANGED extract() path K times on one paper's methods slice and appends per-draw rows (the raw
temporal_standardization_method FieldExtractionResult + intensity_convention for a bleed re-check)
to a JSONL sidecar. The PROMPT change under test is made out-of-band by editing the field's scope
stanza in extractor.py between invocations; separate `python` processes pick up the edited file, so
Run 1 (baseline) and Run 2 (fixed) differ only by that stanza.

Capture pattern reused from scripts/chen_flip_probe.py (read-only completion:response hook).
Off by default. Usage:
    python scripts/chen_fix_ab.py --paper chen_2015 --pdf Chen_2015.pdf --k 20 \
        --tag "RUN1_baseline" --expect-hash 1a6d8afbec64e926 --jsonl results/chen_fix_ab.jsonl
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

_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
_TARGET = "temporal_standardization_method"


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


def _field(raw: dict[str, Any] | None, name: str) -> dict[str, Any]:
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--paper", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--tag", required=True, help="RUN1_baseline / RUN2_fixed / RUN3_regression")
    ap.add_argument(
        "--field",
        default="temporal_standardization_method",
        choices=["temporal_standardization_method", "base_pipeline_name"],
        help="which field's status is the primary tally",
    )
    ap.add_argument(
        "--expect-hash", default=None, help="assert slice hash matches (void run if not)"
    )
    ap.add_argument("--jsonl", type=Path, required=True)
    args = ap.parse_args(argv)

    client = build_client()
    captured: list[Any] = []
    client.on("completion:response", lambda response: captured.append(response))

    text, _ = load_pdf_text(_CORPUS / args.pdf)
    slice_text = find_methods_section(text).text
    canon_hash = hashlib.sha256(slice_text.encode()).hexdigest()[:16]
    if args.expect_hash and canon_hash != args.expect_hash:
        raise SystemExit(
            f"STOP: {args.paper} slice hash {canon_hash} != expected {args.expect_hash}. "
            "Comparison void — report, do not proceed."
        )
    paper = ParsedPaper(
        text=slice_text,
        source=args.paper,
        parser="pypdf",
        pdf_date=pdf_creation_date(_CORPUS / args.pdf),
    )

    statuses: collections.Counter[str] = collections.Counter()
    with args.jsonl.open("a") as fh:
        for i in range(args.k):
            captured.clear()
            extract(paper, _MODEL, client=client, paper_date=paper.pdf_date)
            raw = _parse_json(captured[-1].choices[0].message.content) if captured else None
            t = _field(raw, _TARGET)
            ic = _field(raw, "intensity_convention")
            bp = _field(raw, "base_pipeline_name")
            primary = bp if args.field == "base_pipeline_name" else t
            statuses[str(primary["status"])] += 1
            fh.write(
                json.dumps(
                    {
                        "tag": args.tag,
                        "paper": args.paper,
                        "field": args.field,
                        "hash": canon_hash,
                        "run": i + 1,
                        "t_status": t["status"],
                        "t_value": t["value"],
                        "t_quote": t["quote"],
                        "t_searched": t["searched"],
                        "t_sections": t["sections"],
                        "ic_status": ic["status"],
                        "ic_value": ic["value"],
                        "bp_status": bp["status"],
                        "bp_value": bp["value"],
                        "bp_quote": bp["quote"],
                        "bp_searched": bp["searched"],
                    }
                )
                + "\n"
            )
            print(
                f"  [{args.tag}] {args.paper} {i + 1}/{args.k}: {args.field}={primary['status']}",
                file=sys.stderr,
            )
    print(f"{args.tag} {args.paper} (hash {canon_hash}): {dict(statuses)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
