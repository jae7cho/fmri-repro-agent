"""Run-to-run VARIANCE harness for the extractor (temp 0, FIXED input, same model).

The measurement instrument that makes every downstream extraction experiment falsifiable.
The v6->v7 diff showed 8 targeted fields flipping when the input changed; this asks the prior
question: with the input held BYTE-IDENTICAL, does the same field flip across N runs?

  - Fields stable across N runs -> temp 0 is effectively deterministic; a v6-vs-v7 diff on
    fixed input is trustworthy, and chen's loss is a real context-sensitivity effect.
  - Fields flip across identical runs -> temp 0 is NOT deterministic in this stack; every
    reported extraction number needs error bars and the honest unit is a flip-rate.

CAUTION (per PI): if runs come back identical, that itself needs scrutiny — confirm nothing
(Bedrock prompt caching, a fixed seed) is manufacturing false stability before trusting it.
This script sends TRULY identical requests; interpret perfect stability with that caveat.

Not wired into batch. Run by path:
    python scripts/variance_probe.py --n 15 --papers chen_2015 oconnor_2017 weber_2024
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path
from typing import Any

from extractor_mvp.extractor import build_client, extract
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date

_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # the v6/v7-pinned model
_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
_PDF = {
    "chen_2015": "Chen_2015.pdf",
    "oconnor_2017": "OConnor_2017.pdf",
    "weber_2024": "Weber_2024.pdf",
}

# Targeted fields whose per-run extraction state we track (kind, attr). base_pipeline special.
_TARGETS = [
    ("spatial_normalization", "target_space"),
    ("spatial_normalization", "resolution_mm"),
    ("surface_projection", "target_surface"),
    ("surface_projection", "surface_registration"),
    ("intensity_normalization", "convention"),
    ("intensity_normalization", "value"),
    ("temporal_standardization", "method"),
]


def _field_state(prep: Any, kind: str, attr: str) -> str:
    for s in prep.steps:
        if s.kind == kind:
            f = getattr(s, attr, None)
            if f is not None:
                ext = f.extraction
                val = ext.value if ext.status == "EXTRACTED" else None
                return f"{ext.status}:{val}"
    return "ABSENT"


def _base_state(prep: Any) -> str:
    bp = prep.base_pipeline
    ext = getattr(bp, "extraction", None)
    if ext is None:
        return "NOT_APPLICABLE"
    if ext.status == "EXTRACTED":
        return f"EXTRACTED:{ext.value.name}"
    return str(ext.status)


def run_paper(paper_id: str, n: int, client: Any) -> dict[str, list[str]]:
    text, _ = load_pdf_text(_CORPUS / _PDF[paper_id])
    sl = find_methods_section(text)  # the input is fixed: computed once, reused every run
    paper = ParsedPaper(
        text=sl.text,
        source=paper_id,
        parser="pypdf",
        pdf_date=pdf_creation_date(_CORPUS / _PDF[paper_id]),
    )
    fields = ["base_pipeline"] + [f"{k}.{a}" for k, a in _TARGETS]
    observations: dict[str, list[str]] = {f: [] for f in fields}
    for i in range(n):
        prep, _diag, _def = extract(paper, _MODEL, client=client, paper_date=paper.pdf_date)
        observations["base_pipeline"].append(_base_state(prep))
        for k, a in _TARGETS:
            observations[f"{k}.{a}"].append(_field_state(prep, k, a))
        print(f"  {paper_id} run {i + 1}/{n} done", file=sys.stderr)
    return observations


def render(all_obs: dict[str, dict[str, list[str]]], n: int) -> str:
    lines = [f"# Extractor run-to-run variance (N={n}, temp 0, fixed input, model {_MODEL})", ""]
    lines.append(
        "A field is STABLE if all N runs returned the same state. A field that FLIPS across "
        "byte-identical inputs proves temp-0 nondeterminism in this stack — every extraction "
        "number then needs error bars."
    )
    lines.append("")
    any_flip = False
    for paper_id, obs in all_obs.items():
        lines.append(f"## {paper_id}")
        lines.append("")
        lines.append("| field | distinct | stable? | modal (count) | all outcomes |")
        lines.append("|---|---|---|---|---|")
        for field, runs in obs.items():
            counts = collections.Counter(runs)
            stable = len(counts) == 1
            any_flip = any_flip or not stable
            modal, mc = counts.most_common(1)[0]
            outcomes = " / ".join(f"{v} x{c}" for v, c in counts.most_common())
            flag = "yes" if stable else "**NO**"
            lines.append(
                f"| {field} | {len(counts)} | {flag} | `{modal[:40]}` ({mc}/{n}) | {outcomes[:120]} |"
            )
        lines.append("")
    verdict = (
        "AT LEAST ONE FIELD FLIPPED across identical runs -> temp 0 is NOT deterministic here; "
        "single-run extraction numbers need error bars (flip-rate, not state)."
        if any_flip
        else "Every field stable across all runs -> temp 0 is effectively deterministic on fixed "
        "input. SCRUTINISE before trusting: confirm no Bedrock prompt caching / fixed seed is "
        "manufacturing this stability."
    )
    lines.append("## Verdict")
    lines.append("")
    lines.append(verdict)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--n", type=int, default=15, help="runs per paper")
    ap.add_argument(
        "--papers", nargs="+", default=list(_PDF), help="paper_ids (default: chen + 2 C-PAC)"
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    client = build_client()
    all_obs = {pid: run_paper(pid, args.n, client) for pid in args.papers}
    md = render(all_obs, args.n)
    if args.out is not None:
        args.out.write_text(md)
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
