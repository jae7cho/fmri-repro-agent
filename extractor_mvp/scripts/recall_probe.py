"""Standalone false-absence SCREEN for base_pipeline extraction (no LLM, no network).

A SCREEN, not ground truth. A hit means "the alias token appears in the text the extractor
was actually given (its methods slice)" — NOT that the paper reported a pipeline. Every
suspected case MUST be adjudicated by a human reading the printed context window; this script
never labels a confirmed false negative. The headline (N of the MISSING_FROM_PAPER base
pipelines that have alias hits) is a LOWER BOUND on the false-absence rate: it can only find
pipelines whose names are in the alias list.

Not wired into batch.py / extractor.py. Run by path (scripts/ is not a package):
    python scripts/recall_probe.py <corpus_pdf_dir> <results_papers_dir>
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any

from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.pdf_loader import load_pdf_text

# --- regexes (report, don't judge) ------------------------------------------
_FUSED_RUN = re.compile(r"[A-Za-z]{26,}")
_SHATTERED_ACRONYM = re.compile(r"\b[A-Z](?:\s[A-Z]){2,}\b")
_VERSION_TOKEN = re.compile(r"v(?:ersion)?\.?\s*\d+(?:\.\d+){1,2}", re.IGNORECASE)
_WS = re.compile(r"\s+")

# Toolbox names not modeled in the KB (KB aliases are loaded separately, not hardcoded).
_NON_KB_TOOLBOXES = (
    "SPM99",
    "SPM2",
    "SPM5",
    "SPM8",
    "SPM12",
    "SPM",
    "AFNI",
    "FSL",
    "FreeSurfer",
    "XCP-D",
    "XCP",
    "Nipype",
    "DPARSF",
    "CONN",
)

_VERSION_PROXIMITY = 120  # chars between an alias hit and a version token
_CONTEXT = 160  # verbatim context window for human adjudication
_FUSED_MIN_ALIAS = 5  # only run the fused search for distinctive aliases (avoid SPM/FSL noise)


# --- alias list -------------------------------------------------------------


def kb_aliases(kb_root: str | None = None) -> list[str]:
    """pipeline_id + display_name + aliases for every KB pipeline doc (NOT hardcoded),
    plus the non-KB toolbox names. Deduped, longest-first (so the longest alias reports)."""
    from fmri_defaults_kb.io import load_pipeline_documents

    seen: set[str] = set()
    for pid, doc in load_pipeline_documents(kb_root).items():
        seen.add(pid)
        seen.add(str(doc.get("display_name", "")))
        seen.update(str(a) for a in doc.get("aliases", []))
    seen.update(_NON_KB_TOOLBOXES)
    return sorted((a for a in seen if a.strip()), key=lambda a: (-len(a), a.lower()))


def _alias_re(alias: str) -> re.Pattern[str]:
    # Token boundaries that tolerate internal hyphens (C-PAC) but reject substring matches
    # (CONN inside "Connectome").
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", re.IGNORECASE)


# --- records ----------------------------------------------------------------


@dataclasses.dataclass
class Suspected:
    paper_id: str
    kind: str  # "name" | "version" | "fused-name" | "fused-version"
    alias: str
    offset: int  # absolute char offset in full paper text (or -1 for fused, ws-collapsed)
    context: str


@dataclasses.dataclass
class PaperReport:
    paper_id: str
    full_chars: int
    fused_per_1k: float
    fused_n: int
    shattered_n: int
    slice_len: int
    slice_ratio: float
    slice_after: str
    slice_flag: bool
    base_status: str
    version_status: str | None
    n_name_hits: int
    n_fused_hits: int
    suspected: list[Suspected] = dataclasses.field(default_factory=list)


# --- helpers ----------------------------------------------------------------


def _fused_stats(text: str) -> tuple[int, float]:
    n = len(_FUSED_RUN.findall(text))
    words = max(1, len(text.split()))
    return n, round(n / words * 1000, 2)


def _context(text: str, start: int, end: int) -> str:
    lo = max(0, start - _CONTEXT // 2)
    hi = min(len(text), end + _CONTEXT // 2)
    return _WS.sub(" ", text[lo:hi]).strip()


def _version_near(text: str, lo: int, hi: int) -> bool:
    window = text[max(0, lo - _VERSION_PROXIMITY) : hi + _VERSION_PROXIMITY]
    return _VERSION_TOKEN.search(window) is not None


def _base_pipeline(result: dict[str, Any]) -> dict[str, Any]:
    bp = result.get("preprocessing", {}).get("base_pipeline")
    return bp if isinstance(bp, dict) else {}


def _version_status(bp: dict[str, Any]) -> str | None:
    ext = bp.get("extraction", {})
    if ext.get("status") != "EXTRACTED":
        return None
    version = (ext.get("value") or {}).get("version") or {}
    status = (version.get("extraction") or {}).get("status")
    return str(status) if status is not None else None


# --- per-paper probe --------------------------------------------------------


def probe_paper(
    paper_id: str, full_text: str, result: dict[str, Any], aliases: list[str]
) -> PaperReport:
    fused_n, fused_per_1k = _fused_stats(full_text)
    shattered_n = len(_SHATTERED_ACRONYM.findall(full_text))

    sl = find_methods_section(full_text)
    end = sl.start_offset + len(sl.text)
    after = _WS.sub(" ", full_text[end : end + 120]).strip()
    ratio = round(len(sl.text) / max(1, len(full_text)), 3)
    slice_flag = ratio > 0.5 or "reference" in after[:60].lower()

    bp = _base_pipeline(result)
    base_status = str(bp.get("extraction", {}).get("status", "UNKNOWN"))
    version_status = _version_status(bp)

    suspected: list[Suspected] = []

    # (a) clean alias hits within the methods slice
    name_hits: list[tuple[str, int, int]] = []  # (alias, slice_start, slice_end)
    for alias in aliases:
        m = _alias_re(alias).search(sl.text)
        if m is not None:
            name_hits.append((alias, m.start(), m.end()))
    if base_status == "MISSING_FROM_PAPER":
        for alias, s, e in name_hits:
            abs_off = sl.start_offset + s
            suspected.append(
                Suspected(
                    paper_id,
                    "name",
                    alias,
                    abs_off,
                    _context(full_text, abs_off, sl.start_offset + e),
                )
            )
    # (b) version false-absence: base extracted but version missing, version token near a name hit
    if version_status == "MISSING_FROM_PAPER":
        for alias, s, e in name_hits:
            if _version_near(sl.text, s, e):
                abs_off = sl.start_offset + s
                suspected.append(
                    Suspected(
                        paper_id,
                        "version",
                        alias,
                        abs_off,
                        _context(full_text, abs_off, sl.start_offset + e),
                    )
                )

    # (c) fused/shattered case: the extractor could not reasonably have matched these.
    stripped = _WS.sub("", sl.text)
    fused_hits: list[tuple[str, int]] = []  # (alias, stripped_offset)
    for alias in aliases:
        stripped_alias = _WS.sub("", alias)
        if len(stripped_alias) < _FUSED_MIN_ALIAS:
            continue
        idx = stripped.lower().find(stripped_alias.lower())
        if idx != -1:
            fused_hits.append((alias, idx))
    for alias, idx in fused_hits:
        ctx = stripped[max(0, idx - _CONTEXT // 2) : idx + len(_WS.sub("", alias)) + _CONTEXT // 2]
        if base_status == "MISSING_FROM_PAPER":
            suspected.append(Suspected(paper_id, "fused-name", alias, -1, ctx))
        # a version token in the collapsed neighborhood -> fused version evidence
        vwin = stripped[max(0, idx - _VERSION_PROXIMITY) : idx + _VERSION_PROXIMITY]
        if _VERSION_TOKEN.search(vwin):
            suspected.append(Suspected(paper_id, "fused-version", alias, -1, ctx))

    return PaperReport(
        paper_id=paper_id,
        full_chars=len(full_text),
        fused_per_1k=fused_per_1k,
        fused_n=fused_n,
        shattered_n=shattered_n,
        slice_len=len(sl.text),
        slice_ratio=ratio,
        slice_after=after,
        slice_flag=slice_flag,
        base_status=base_status,
        version_status=version_status,
        n_name_hits=len(name_hits),
        n_fused_hits=len(fused_hits),
        suspected=suspected,
    )


# --- driver + rendering -----------------------------------------------------


def run(
    corpus_dir: Path, results_dir: Path, kb_root: str | None
) -> tuple[list[PaperReport], list[str]]:
    """Returns (reports, excluded_paper_ids). Excluded papers are skipped, not probed."""
    from extractor_mvp.corpus import is_excluded

    aliases = kb_aliases(kb_root)
    reports: list[PaperReport] = []
    excluded: list[str] = []
    for pdf in sorted(corpus_dir.glob("*.pdf")):
        paper_id = pdf.stem.lower()
        if is_excluded(paper_id):  # exclusion takes precedence over result presence
            excluded.append(paper_id)
            continue
        result_path = results_dir / f"{paper_id}.json"
        if not result_path.exists():
            continue
        text, _status = load_pdf_text(pdf)
        result = json.loads(result_path.read_text())
        reports.append(probe_paper(paper_id, text, result, aliases))
    return reports, excluded


def render(reports: list[PaperReport], excluded: list[str] | None = None) -> str:
    excluded = excluded or []
    lines: list[str] = ["# base_pipeline false-absence screen", ""]
    lines.append(
        "SCREEN only — a hit means the alias appears in the methods slice the extractor was "
        "given; a human must read the context window to confirm. The suspected count is a "
        "LOWER BOUND (only names in the alias list can be found)."
    )
    if excluded:
        lines.append("")
        lines.append(
            f"Excluded from this screen (corpus registry): {', '.join(sorted(excluded))}. "
            "cabral_2017 was one of the two MISSING_FROM_PAPER papers with no alias hit, so "
            "the MISSING set drops 10 -> 9 and the headline becomes 8/9."
        )
    lines.append("")

    # headline: MISSING_FROM_PAPER base pipelines with any (clean) name hit
    missing = [r for r in reports if r.base_status == "MISSING_FROM_PAPER"]
    with_hits = [r for r in missing if any(s.kind in ("name", "fused-name") for s in r.suspected)]
    lines.append(
        f"**Headline: {len(with_hits)} of {len(missing)} MISSING_FROM_PAPER base pipelines "
        f"have alias hits in their methods slice (suspected false absence).**"
    )
    lines.append("")

    lines.append("## Per-paper")
    lines.append("")
    lines.append(
        "| paper | full chars | fused/1k | shattered | slice len | slice/full | slice flag "
        "| base_status | version_status | name hits | fused hits |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(reports, key=lambda r: (not r.suspected, r.paper_id)):
        flag = "⚠ bloat/refs" if r.slice_flag else ""
        lines.append(
            f"| {r.paper_id} | {r.full_chars} | {r.fused_per_1k} | {r.shattered_n} | "
            f"{r.slice_len} | {r.slice_ratio} | {flag} | {r.base_status} | "
            f"{r.version_status or '-'} | {r.n_name_hits} | {r.n_fused_hits} |"
        )
    lines.append("")

    all_suspected = [s for r in reports for s in r.suspected]
    lines.append(f"## SUSPECTED FALSE ABSENCE ({len(all_suspected)}) — adjudicate each by reading")
    lines.append("")
    order = {"name": 0, "version": 1, "fused-name": 2, "fused-version": 3}
    for s in sorted(all_suspected, key=lambda s: (s.paper_id, order.get(s.kind, 9))):
        loc = f"@{s.offset}" if s.offset >= 0 else "@(ws-collapsed)"
        lines.append(f"- **{s.paper_id}** [{s.kind}] alias `{s.alias}` {loc}")
        lines.append(f"  > …{s.context}…")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("corpus_dir", type=Path, help="folder of corpus *.pdf")
    ap.add_argument("results_dir", type=Path, help="results papers/ folder (<paper_id>.json)")
    ap.add_argument("--kb-root", default=None, help="KB root (default: installed fmri_defaults_kb)")
    ap.add_argument("--out", type=Path, default=None, help="write markdown here (else stdout)")
    args = ap.parse_args(argv)

    if not args.corpus_dir.is_dir() or not args.results_dir.is_dir():
        print("ERROR: corpus_dir and results_dir must be folders", file=sys.stderr)
        return 1
    reports, excluded = run(args.corpus_dir, args.results_dir, args.kb_root)
    md = render(reports, excluded)
    if args.out is not None:
        args.out.write_text(md)
        print(f"Wrote {args.out} ({len(reports)} papers).")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
