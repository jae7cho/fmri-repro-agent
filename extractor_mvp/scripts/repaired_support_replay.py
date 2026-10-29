"""Replay the 2026-10-29 change -- the value-support check reads the REPAIRED text when a span
carries tier-6 repairs -- over every stored batch result. No model calls.

Two directions:

* **cells that move to EXTRACTED**: every diagnostic ``value_unsupported_by_quote`` is re-run
  through the production ``_process_field`` on its stored raw value and raw quote against the
  paper's methods slice, re-sliced from the PDF as the run did. A cell that now comes back EXTRACTED
  moved (it can only move if its quote resolves through tier 6);
* **cells that resolved before**: every EXTRACTED cell whose stored span carries repairs (only
  coverage_v2 records have them) is re-checked on the repaired text. The raw quote of a passing cell
  is not stored, so the repaired text is reconstructed from the span by undoing each named
  substitution once, left to right -- an approximation, labelled as one.

**Prints no quote text.** Contaminated papers are listed by vintage, paper and field; the three
held-out papers are counts only.

Usage:
    python scripts/repaired_support_replay.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.batch_config import load_batch_config  # noqa: E402
from extractor_mvp.coverage_fields import COVERAGE_SPECS  # noqa: E402
from extractor_mvp.extraction_result import FieldExtractionResult  # noqa: E402
from extractor_mvp.extractor import _FIELD_SPECS, _process_field  # noqa: E402
from extractor_mvp.methods_finder import find_methods_section  # noqa: E402
from extractor_mvp.pdf_loader import load_pdf_text  # noqa: E402
from extractor_mvp.quote_support import coverage_value_supported, step_value_supported  # noqa: E402

_RESULTS = _HERE.parent / "results"
_CONFIG = _HERE.parent / "configs" / "batch_coverage_v2_config.yaml"
_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
_VINTAGES = (
    "batch_a1_acceptance",
    "batch_motion_corpus_v1",
    "batch_motion_corpus_v1_inferred",
    "batch_coverage_v1",
    "batch_coverage_v2",
)
_COV = {s.dotted: s for s in COVERAGE_SPECS}
_SHARED = {dotted: (fid, lit, t) for _a, fid, dotted, lit, t in _FIELD_SPECS}


def _rerun(dotted: str, raw_value: str, raw_quote: str, text: str):
    fe = FieldExtractionResult(status="extracted", value=raw_value, verbatim_quote=raw_quote)
    if dotted in _COV:
        spec = _COV[dotted]
        return _process_field(
            spec.field_id,
            dotted,
            fe,
            spec.literal_type,
            spec.t,
            text,
            None,
            use_synonym_table=False,
            value_kind=spec.value_kind,
            synonyms=(spec.synonyms, spec.underspecified) if spec.synonyms is not None else None,
        )[0]
    if dotted in _SHARED:
        fid, lit, t = _SHARED[dotted]
        return _process_field(fid, dotted, fe, lit, t, text, None)[0]
    return None


def _undo(span_text: str, repairs: list[str]) -> str:
    out = span_text
    for event in repairs:
        quote_chars, source_chars = event.split("→", 1)
        out = out.replace(source_chars, quote_chars, 1)
    return out


def _value_for_check(value):
    if isinstance(value, dict):
        return SimpleNamespace(**value)
    if isinstance(value, list):
        return [SimpleNamespace(**v) if isinstance(v, dict) else v for v in value]
    return value


def main() -> int:
    cfg = load_batch_config(_CONFIG)
    paths = {p.paper_id: p.path for p in cfg.papers}
    cache: dict[str, str] = {}

    def text_of(pid: str) -> str:
        if pid not in cache:
            cache[pid] = find_methods_section(load_pdf_text(paths[pid])[0]).text
        return cache[pid]

    moved: list[tuple[str, str, str]] = []
    held_moved = collections.Counter()
    still = collections.Counter()
    kept = 0
    flipped: list[tuple[str, str, str]] = []
    held_flipped = 0
    for vint in _VINTAGES:
        papers = _RESULTS / vint / "papers"
        if not papers.is_dir():
            continue
        for f in sorted(papers.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            pid = d["paper_id"]
            for diag in d.get("diagnostics", []):
                if diag.get("failure_reason") != "value_unsupported_by_quote":
                    continue
                pf = _rerun(diag["field"], diag["raw_value"], diag["raw_quote"], text_of(pid))
                if pf is not None and pf.extraction.status == "EXTRACTED":
                    if pid in _HELD:
                        held_moved[vint] += 1
                    else:
                        repairs = ", ".join(pf.extraction.spans[0].repairs)
                        moved.append((vint, pid, f"{diag['field']}  [{repairs}]"))
                else:
                    still[vint] += 1
            for step in d["preprocessing"].get("steps", []):
                for name, value in step.items():
                    if not isinstance(value, dict):
                        continue
                    ext = value.get("extraction")
                    if not isinstance(ext, dict) or ext.get("status") != "EXTRACTED":
                        continue
                    span = ext["spans"][0]
                    if not span.get("repairs"):
                        continue
                    dotted = f"{step['kind']}.{name}"
                    repaired = _undo(span["text"], span["repairs"])
                    val = _value_for_check(ext["value"])
                    ok = (
                        coverage_value_supported(dotted, val, repaired)
                        if dotted in _COV
                        else step_value_supported(dotted, val, repaired)
                    )
                    if ok is False:
                        if pid in _HELD:
                            held_flipped += 1
                        else:
                            flipped.append((vint, pid, dotted))
                    else:
                        kept += 1
    print("== unsupported before, still unsupported, per vintage")
    for k, v in sorted(still.items()):
        print(f"  {k:<36} {v}")
    print(f"== unsupported before, MOVED to EXTRACTED (contaminated, listed): {len(moved)}")
    for row in moved:
        print("  ", *row)
    print("== the same on the held-out three, counts only:", dict(held_moved) or 0)
    print(
        f"== repaired-span cells that resolved before, still supported on the repaired text: {kept}"
    )
    print(f"== ... and now UNSUPPORTED (contaminated, listed): {len(flipped)}")
    for row in flipped:
        print("  ", *row)
    print("== the same on the held-out three, count only:", held_flipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
