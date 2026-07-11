"""Stage-partition diagnostic for base_pipeline MISSING_FROM_PAPER misses.

DIAGNOSTIC ONLY. Changes no extraction logic, no prompt, no schema. It answers ONE
sizing question: of the base_pipeline misses in batch_v6_full, how many are
prompt-tractable (STAGE-3: token is clean & present in the slice the model receives,
model still returned MISSING) versus not (STAGE-1: token is corrupted/absent in the
slice — a pypdf-frontend problem no prompt can fix).

Method (per paper):
  1. Recompute the exact methods slice the extractor sees: find_methods_section(pypdf text).
  2. Search that slice for pipeline NAMES — KB aliases (built from fmri_defaults_kb, not
     hardcoded) plus common non-KB toolboxes — in two forms:
        CLEAN  : the alias appears as normal text.
        FUSED  : only a whitespace-shattered variant appears ("C-P A C") — a pypdf artifact.
  3. Search for a VERSION token (vN.N[.N]) near a name hit, same 3-way split, reported
     SEPARATELY from the name.
  4. Classify each miss:
        name CLEAN in slice          -> STAGE-3  (prompt-addressable)
        name FUSED in slice          -> STAGE-1  (pypdf; prompt cannot help)
        name absent from slice but
          present in full pypdf text -> SLICE-BOUNDARY (methods_finder cut it out)
        name absent from full text   -> NOT-A-MISS (paper names no pipeline)

Then, to SIZE stage-3 variance (not fix it), re-run the UNCHANGED extractor K times at
temp 0 on ONLY the STAGE-3-clean papers and report the base_pipeline flip-rate per paper.

Run by path:
    python scripts/stage_partition.py --k 15 --out results/STAGE_PARTITION.md
"""

from __future__ import annotations

import argparse
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

# The 9 non-cabral papers whose base_pipeline NAME is MISSING_FROM_PAPER in batch_v6_full
# (braun_2015 is DEFERRED_TO_CITATION, not MISSING -> correctly excluded). PDF names from
# each result JSON's `path`.
_MISS_PAPERS: dict[str, str] = {
    "binder_1999": "Binder_1999.pdf",
    "derosa_2025": "DeRosa_2025.pdf",
    "liu_2005": "Liu_2005.pdf",
    "liu_2013": "Liu_2013.pdf",
    "oconnor_2017": "OConnor_2017.pdf",
    "poldrack_2015": "Poldrack_2015.pdf",
    "power_2014": "Power_2014.pdf",
    "viduarre_2017": "Viduarre_2017.pdf",
    "weber_2024": "Weber_2024.pdf",
}

# Non-KB toolboxes a paper might name as its base. NOT pipeline-KB members, but a named
# toolbox is still a real base_pipeline candidate the model could have surfaced.
_TOOLBOXES = [
    # SPM99/SPM8/SPM12/SPM — but NOT "SPMs" (statistical parametric maps, a stats term, not
    # the software): a trailing letter forbids the match. binder_1999's "(SPMs)" is thereby
    # rejected, and its real tool token "MCW-AFNI" is picked up instead.
    r"SPM(?:99|\d{1,2})?(?![A-Za-z])",
    r"AFNI",
    r"FSL",
    r"FreeSurfer",
    r"XCP[\s\-]?(?:Engine|D)?",
    r"Nipype",
    r"DPARSF",
    r"CONN(?:\s+toolbox)?",
]

_VERSION_RE = re.compile(r"v(?:ersion)?\.?\s*\d+(?:\.\d+){1,2}", re.IGNORECASE)


def _kb_aliases() -> list[str]:
    """All KB pipeline names/display-names/aliases, longest-first (build, don't hardcode)."""
    from fmri_repro.kb_client.base_pipeline import recognize

    from extractor_mvp.extractor import build_client as _bc  # noqa: F401  (keeps import local)

    loader = recognize.__globals__["load_pipeline_documents"]
    docs = loader()
    seen: set[str] = set()
    for pid, doc in docs.items():
        for c in (pid, doc.get("display_name", ""), *doc.get("aliases", [])):
            if c:
                seen.add(c)
    return sorted(seen, key=len, reverse=True)


def _clean_re(alias: str) -> re.Pattern[str]:
    """Alias as normal text: internal runs of space collapse, word-ish boundaries."""
    body = re.escape(alias).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.IGNORECASE)


def _shatter_re(alias: str) -> re.Pattern[str]:
    """Alias tolerant of whitespace/hyphen inserted BETWEEN characters (pypdf shattering)."""
    chars = [re.escape(c) for c in alias if not c.isspace()]
    return re.compile(r"[\s\-]*".join(chars), re.IGNORECASE)


def _ctx(text: str, start: int, end: int, width: int = 160) -> str:
    pad = (width - (end - start)) // 2
    seg = text[max(0, start - pad) : end + pad]
    return " ".join(seg.split())[:width]


def _find_name(slice_text: str, full_text: str, aliases: list[str]) -> dict[str, Any]:
    """Classify the NAME miss for one paper. Returns class + matched token + context."""
    patterns = [(a, _clean_re(a), _shatter_re(a)) for a in aliases]
    patterns += [
        (tb, re.compile(tb, re.IGNORECASE), re.compile(tb, re.IGNORECASE)) for tb in _TOOLBOXES
    ]

    # CLEAN in slice wins outright.
    for _lbl, clean, _ in patterns:
        m = clean.search(slice_text)
        if m:
            return {
                "cls": "STAGE-3",
                "token": m.group(0),
                "ctx": _ctx(slice_text, m.start(), m.end()),
            }
    # FUSED in slice (shattered variant present, clean absent).
    for _lbl, clean, shatter in patterns:
        m = shatter.search(slice_text)
        if m and not clean.search(slice_text):
            raw = m.group(0)
            # only "fused" if whitespace/hyphen was actually inserted between chars
            if re.sub(r"[\s\-]", "", raw).lower() != raw.lower():
                return {"cls": "STAGE-1", "token": raw, "ctx": _ctx(slice_text, m.start(), m.end())}
    # Absent from slice: present in full text -> slice cut it; else genuinely absent.
    for _lbl, clean, shatter in patterns:
        m = clean.search(full_text) or shatter.search(full_text)
        if m:
            return {
                "cls": "SLICE-BOUNDARY",
                "token": m.group(0),
                "ctx": _ctx(full_text, m.start(), m.end()),
            }
    return {"cls": "NOT-A-MISS", "token": "", "ctx": ""}


def _find_version(slice_text: str, full_text: str) -> dict[str, Any]:
    """Classify a VERSION token independently of the name."""
    m = _VERSION_RE.search(slice_text)
    if m:
        raw = m.group(0)
        fused = bool(re.search(r"\d\s+\.\s*\d|\d\s+\d", raw))
        return {
            "cls": "STAGE-1" if fused else "STAGE-3",
            "token": raw,
            "ctx": _ctx(slice_text, m.start(), m.end()),
        }
    mf = _VERSION_RE.search(full_text)
    if mf:
        return {
            "cls": "SLICE-BOUNDARY",
            "token": mf.group(0),
            "ctx": _ctx(full_text, mf.start(), mf.end()),
        }
    return {"cls": "NOT-A-MISS", "token": "", "ctx": ""}


def _base_state(prep: Any) -> str:
    bp = prep.base_pipeline
    ext = getattr(bp, "extraction", None)
    if ext is None:
        return "NOT_APPLICABLE"
    if ext.status == "EXTRACTED":
        return f"EXTRACTED:{ext.value.name}"
    return str(ext.status)


def classify_all(aliases: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for pid, pdf in _MISS_PAPERS.items():
        full, _ = load_pdf_text(_CORPUS / pdf)
        sl = find_methods_section(full)
        out[pid] = {
            "name": _find_name(sl.text, full, aliases),
            "version": _find_version(sl.text, full),
            "slice_ratio": sl.slice_ratio,
        }
        print(f"  classified {pid}: name={out[pid]['name']['cls']}", file=sys.stderr)
    return out


def flip_rate(paper_ids: list[str], k: int, client: Any) -> dict[str, list[str]]:
    obs: dict[str, list[str]] = {}
    for pid in paper_ids:
        pdf = _MISS_PAPERS[pid]
        full, _ = load_pdf_text(_CORPUS / pdf)
        sl = find_methods_section(full)  # fixed input, computed once
        paper = ParsedPaper(
            text=sl.text, source=pid, parser="pypdf", pdf_date=pdf_creation_date(_CORPUS / pdf)
        )
        states = []
        for i in range(k):
            prep, _d, _f = extract(paper, _MODEL, client=client, paper_date=paper.pdf_date)
            states.append(_base_state(prep))
            print(f"  {pid} run {i + 1}/{k}: {states[-1]}", file=sys.stderr)
        obs[pid] = states
    return obs


def render(classes: dict[str, dict[str, Any]], flips: dict[str, list[str]], k: int) -> str:
    s3 = [p for p, c in classes.items() if c["name"]["cls"] == "STAGE-3"]
    s1 = [p for p, c in classes.items() if c["name"]["cls"] == "STAGE-1"]
    sb = [p for p, c in classes.items() if c["name"]["cls"] == "SLICE-BOUNDARY"]
    na = [p for p, c in classes.items() if c["name"]["cls"] == "NOT-A-MISS"]

    lines = [
        "# base_pipeline miss — stage partition (name vs version SEPARATED)",
        "",
        "Diagnostic only. Population: the 9 non-cabral papers with base_pipeline = "
        "MISSING_FROM_PAPER in batch_v6_full. Slice = find_methods_section(pypdf text), the "
        "exact input the extractor receives. Model pinned to the v6 string; temp 0; prompt "
        "UNCHANGED.",
        "",
        "- **STAGE-3** = name is CLEAN & present in the slice, model still returned MISSING "
        "→ prompt-addressable.",
        "- **STAGE-1** = name is whitespace-shattered in the slice → pypdf frontend, a "
        "prompt cannot help.",
        "- **SLICE-BOUNDARY** = name absent from slice but present in full text → "
        "methods_finder cut it.",
        "- **NOT-A-MISS** = name absent from the full paper text → paper names no pipeline; "
        "MISSING is correct.",
        "",
        "## Name / version classification",
        "",
        "| paper | name class | version class | clean token | context (160c) |",
        "|---|---|---|---|---|",
    ]
    for pid, c in classes.items():
        n, v = c["name"], c["version"]
        tok = " ".join((n["token"] or v["token"] or "—").split())
        ctx = " ".join((n["ctx"] or v["ctx"] or "").split()).replace("|", "\\|")
        lines.append(f"| {pid} | {n['cls']} | {v['cls']} | `{tok}` | {ctx} |")
    lines += [
        "",
        "## Population sizes (the numbers that decide the experiment)",
        "",
        f"- **STAGE-3-clean name misses (prompt-addressable): {len(s3)}** — {s3 or '(none)'}",
        f"- STAGE-1 name misses (pypdf frontend, different fix): {len(s1)} — {s1 or '(none)'}",
        f"- SLICE-BOUNDARY name misses (methods_finder cut it): {len(sb)} — {sb or '(none)'}",
        f"- NOT-A-MISS (paper names no pipeline; MISSING correct): {len(na)} — {na or '(none)'}",
        "",
        f"## Stage-3 variance — base_pipeline flip-rate, K={k}, temp 0, fixed input",
        "",
    ]
    if flips:
        lines += ["| paper | distinct states | deterministic? | outcomes |", "|---|---|---|---|"]
        for pid, states in flips.items():
            import collections

            cc = collections.Counter(states)
            det = "yes (stable)" if len(cc) == 1 else "**NO (flips)**"
            outs = " / ".join(f"{v} x{n}" for v, n in cc.most_common())
            lines.append(f"| {pid} | {len(cc)} | {det} | {outs} |")
        lines += [
            "",
            "A stable 0/K MISSING on a STAGE-3-clean paper = a DETERMINISTIC model false "
            "negative: reproducible, so a prompt change can be scored against a fixed "
            "baseline (any recovery is signal). A flipping rate = the miss is partly a draw.",
        ]
    else:
        lines.append("(no STAGE-3-clean papers — K-run skipped)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--k", type=int, default=15, help="repeat runs on stage-3-clean papers")
    ap.add_argument("--no-rerun", action="store_true", help="classification only, skip K-run")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    aliases = _kb_aliases()
    print(f"KB aliases: {len(aliases)}", file=sys.stderr)
    classes = classify_all(aliases)
    s3 = [p for p, c in classes.items() if c["name"]["cls"] == "STAGE-3"]

    flips: dict[str, list[str]] = {}
    if s3 and not args.no_rerun:
        print(f"K={args.k} re-run on stage-3-clean: {s3}", file=sys.stderr)
        flips = flip_rate(s3, args.k, build_client())

    md = render(classes, flips, args.k)
    if args.out is not None:
        args.out.write_text(md)
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
