"""Replay the span resolver over every stored result and every recorded motion draw. No model calls.

Acceptance for DESIGN_coverage_expansion.md B14 item 1 (the author's order of 2026-10-28): list each
cell that moves from unresolved to resolved under the repair tier, by paper and field (or draw), and
confirm that nothing resolved before changes -- every cell that resolved under the committed resolver
re-resolves to the SAME span (start, end) with the SAME recovered flag.

Two record shapes are replayed:

* batch records (``results/<vintage>/papers/*.json``): the unresolved cells are the diagnostics whose
  ``failure_reason`` starts with ``extraction_quote_unresolved`` / ``deferral_quote_unresolved`` (the
  model's raw quote is stored there); the resolved cells are every EXTRACTED span, re-resolved from
  its located text and compared on ``span_in_slice``;
* motion probe draws (``results/motion_probe_*/motion_probe/*.jsonl``): the raw quote
  (``raw_verbatim_quote`` or ``raw_deferral_sentence``) re-resolved; unresolved draws
  (``span_start`` None with a raw quote) may move; resolved draws must keep ``span_start``/``span_end``
  and ``span_recovered``.

The paper text is re-sliced from the PDF exactly as the runs did (``load_pdf_text`` then
``find_methods_section``); the de-interleaved liu_2005 run uses the slice file its manifest names.

**Prints no quote text and no value text.** The three held-out papers (liu_2005, tang_2025,
wheaton_2004) appear as COUNTS only, never by field, offset or substitution; contaminated papers'
moves are listed by paper, field and the named substitutions.

Usage:
    python scripts/span_repair_replay.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.batch_config import load_batch_config  # noqa: E402
from extractor_mvp.methods_finder import find_methods_section  # noqa: E402
from extractor_mvp.pdf_loader import load_pdf_text  # noqa: E402
from extractor_mvp.span_resolver import resolve_quote  # noqa: E402

_RESULTS = _HERE.parent / "results"
_CONFIG = _HERE.parent / "configs" / "batch_coverage_v1_config.yaml"
_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
_BATCH_VINTAGES = (
    "batch_a1_acceptance",
    "batch_motion_corpus_v1",
    "batch_motion_corpus_v1_inferred",
    "batch_coverage_v1",
)


def _probe_runs() -> list[tuple[str, Path]]:
    runs: list[tuple[str, Path]] = []
    for d in sorted(_RESULTS.glob("motion_probe*")):
        if (d / "motion_probe").is_dir():
            runs.append((d.name, d / "motion_probe"))
        elif d.name == "motion_probe" and any(d.glob("*.jsonl")):
            runs.append((d.name, d))
        for sub in sorted(d.glob("*/motion_probe")):  # the A/B runs: <dir>/<arm>/motion_probe
            runs.append((f"{d.name}/{sub.parent.name}", sub))
    return runs


class _Texts:
    def __init__(self) -> None:
        cfg = load_batch_config(_CONFIG)
        self._paths = {p.paper_id: p.path for p in cfg.papers}
        self._cache: dict[str, str] = {}

    def slice(self, paper_id: str) -> str:
        if paper_id not in self._cache:
            text, _ = load_pdf_text(self._paths[paper_id])
            self._cache[paper_id] = find_methods_section(text).text
        return self._cache[paper_id]


def _label(paper_id: str) -> str:
    return "held-out" if paper_id in _HELD else paper_id


def main() -> int:
    texts = _Texts()
    moved: list[tuple[str, str, str, str]] = []  # (vintage, paper-or-held-out, field, repairs)
    held_moved: collections.Counter = collections.Counter()
    stable = collections.Counter()
    changed: list[tuple[str, str, str]] = []
    still = collections.Counter()

    # --- batch records --------------------------------------------------------------------------
    for vint in _BATCH_VINTAGES:
        papers = _RESULTS / vint / "papers"
        if not papers.is_dir():
            print(f"(skipping {vint}: not present)")
            continue
        for f in sorted(papers.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            pid = d["paper_id"]
            text = texts.slice(pid)
            for diag in d.get("diagnostics", []):
                reason = diag.get("failure_reason", "")
                if not reason.startswith(
                    ("extraction_quote_unresolved", "deferral_quote_unresolved")
                ):
                    continue
                r = resolve_quote(diag.get("raw_quote") or "", text)
                if r.span is None:
                    still[vint] += 1
                elif pid in _HELD:
                    held_moved[vint] += 1
                else:
                    moved.append((vint, pid, diag["field"], ", ".join(r.repairs) or "(tier 5)"))
            for step in d["preprocessing"].get("steps", []):
                for name, value in step.items():
                    if not isinstance(value, dict):
                        continue
                    ext = value.get("extraction")
                    if not isinstance(ext, dict) or ext.get("status") != "EXTRACTED":
                        continue
                    span = ext["spans"][0]
                    r = resolve_quote(span["text"], text)
                    want = span.get("span_in_slice") or {"start": span["start"], "end": span["end"]}
                    ok = (
                        r.span is not None
                        and (r.span.start, r.span.end) == (want["start"], want["end"])
                        and r.recovered is False
                    )
                    if ok:
                        stable[vint] += 1
                    else:
                        changed.append((vint, _label(pid), f"{step['kind']}.{name}"))

    # --- motion probe draws ---------------------------------------------------------------------
    for run, path in _probe_runs():
        manifest = path / "manifest.json"
        slice_file = None
        if manifest.is_file():
            slice_file = json.loads(manifest.read_text(encoding="utf-8")).get("slice_file")
        for f in sorted(path.glob("*.jsonl")):
            for line in f.open(encoding="utf-8"):
                if not line.strip():
                    continue
                rec = json.loads(line)
                pid = rec["paper_id"]
                quote = rec.get("raw_verbatim_quote") or rec.get("raw_deferral_sentence")
                if not quote:
                    continue
                text = (
                    Path(slice_file).read_text(encoding="utf-8") if slice_file else texts.slice(pid)
                )
                r = resolve_quote(quote, text)
                reason = rec.get("left_missing_reason") or ""
                unresolved_before = reason.startswith(
                    ("extraction_quote_unresolved", "deferral_quote_unresolved")
                )
                draw = f"draw {rec['draw']}"
                if unresolved_before:
                    if r.span is None:
                        still[run] += 1
                    elif pid in _HELD:
                        held_moved[run] += 1
                    else:
                        moved.append((run, pid, draw, ", ".join(r.repairs) or "(tier 5)"))
                elif rec.get("span_start") is None:
                    # a deferred draw whose deferral sentence resolved at run time: the record keeps
                    # no span for it, so stability is "still resolves"; offsets are uncomparable
                    if r.span is not None:
                        stable[run] += 1
                    else:
                        changed.append((run, _label(pid), f"{draw} (deferral sentence)"))
                else:
                    ok = (
                        r.span is not None
                        and (r.span.start, r.span.end) == (rec["span_start"], rec["span_end"])
                        and bool(r.recovered) == bool(rec.get("span_recovered"))
                    )
                    if ok:
                        stable[run] += 1
                    else:
                        changed.append((run, _label(pid), draw))

    print("== resolved before: re-resolved identical (span and recovered flag), per vintage/run")
    for k, v in sorted(stable.items()):
        print(f"  {k:<48} {v}")
    print(f"== resolved before and CHANGED: {len(changed)}")
    for row in changed:
        print("  ", row)
    print("== unresolved before, still unresolved, per vintage/run")
    for k, v in sorted(still.items()):
        print(f"  {k:<48} {v}")
    print(f"== unresolved before, MOVED to resolved (contaminated papers, listed): {len(moved)}")
    for vint, pid, field, repairs in moved:
        print(f"  {vint:<40} {pid:<15} {field:<48} {repairs}")
    print("== unresolved before, MOVED to resolved on the held-out three: counts only")
    for k, v in sorted(held_moved.items()):
        print(f"  {k:<48} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
