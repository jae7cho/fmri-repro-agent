#!/usr/bin/env python3
"""Score stored records against the author's spatial smoothing and temporal filtering labels
(``ground_truth/smoothing_filtering_labels_v1.xlsx``). The PROCESSED layer, one draw per paper, no
model calls. Counts only; no rates.

A label row is one paper x ``applies_to``. It is matched to the record by paper and applies_to:
- one label row for the paper whose applies_to is "all" (or begins "all ") matches the record's one
  stream;
- otherwise (more than one row on a sheet, or one row not for "all"), the paper's rows are scored as
  one field by ``extractor_mvp.applies_to_scoring`` (DESIGN_applies_to.md §5, Stage 1, 2026-11-11):
  a record holding one "all" value equal to one row's is **collapsed**; a record holding parts
  where the label says "all" is **split**; otherwise each row is matched to the record's part whose
  sentence overlaps the row's quote (fork E2: no alias list), and is scored against it, or is
  **missed**. A record part that matches no row is spurious. "Equal" is the row's state and every
  labelled value agreeing.

Per row: the state, label vs record (the record's state is the report's own: ``cobidas.row_state``
for the Spatial smoothing row, ``cobidas.kind_state`` for temporal filtering), and the values as
stated. FWHM 6 agrees with 6.0. A width given as sigma, or a cutoff in seconds or cycles against the
record's Hz, is a measure or unit mismatch: reported, never converted.

Rows for liu_2005, tang_2025 and wheaton_2004 print states and agree/disagree only, never a value
(liu_2005 and wheaton_2004 are held out; tang_2025 is co-adjudicated but its values are withheld here
under the standing held-out rule).

Usage (openpyxl reads the workbook; it is not a dependency of this package):
    uv run --with openpyxl python scripts/score_smoothing_filtering.py \\
        --results-dir results/batch_coverage_v4
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor_mvp.applies_to_scoring import (
    FieldScore,
    LabelVariant,
    PredictedVariant,
    score_field,
)

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / "ground_truth" / "smoothing_filtering_labels_v1.xlsx"

#: The workbook's state vocabulary (its README sheet, line 4).
LABEL_STATES = (
    "reported",
    "partially_reported",
    "not_reported",
    "stated_not_performed",
    "deferred",
)

#: The report's row states (cobidas.ROW_STATES) in the labels' words.
RECORD_TO_LABEL_STATE = {
    "reported": "reported",
    "partially_reported": "partially_reported",
    "not_reported": "not_reported",
    "performed_no": "stated_not_performed",
    "deferred": "deferred",
    "unverifiable": "unverifiable",
    "not_assessed": "not_assessed",
}

#: Contamination classes (the author's list of 2026-11-05; the workbook's README, line 8).
CO_ADJUDICATED = "co-adjudicated"
AUTHOR_RULED_EXPOSED = "author-ruled, assistant exposure"
AUTHOR_ALONE = "author alone"
CLASS_ORDER = (CO_ADJUDICATED, AUTHOR_RULED_EXPOSED, AUTHOR_ALONE)
_SPECIAL_CLASS = {"liu_2005": AUTHOR_RULED_EXPOSED, "wheaton_2004": AUTHOR_ALONE}

#: Papers whose label and record values are never printed.
VALUES_WITHHELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})

SHEETS = ("Smoothing", "Filtering")
_VALUE_COLS = {
    "Smoothing": ("kernel", "width", "width_measure", "space"),
    "Filtering": ("pass_type", "band_or_cutoff_as_stated", "filter_type", "order"),
}
_STEP = {"Smoothing": "spatial_smoothing", "Filtering": "temporal_filtering"}


def contamination_class(paper_id: str) -> str:
    return _SPECIAL_CLASS.get(paper_id, CO_ADJUDICATED)


# --- labels -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LabelRow:
    sheet: str
    paper_id: str
    applies_to: str
    state: str
    values: dict[str, Any]
    quote: str
    adjudication: str


def load_labels(path: Path = LABELS) -> list[LabelRow]:
    """Every non-empty row of the two sheets. openpyxl is imported here only."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    out: list[LabelRow] = []
    for sheet in SHEETS:
        rows = list(wb[sheet].iter_rows(values_only=True))
        head = [str(h) for h in rows[0]]
        for r in rows[1:]:
            if not any(c not in (None, "") for c in r):
                continue
            d = dict(zip(head, r, strict=False))
            out.append(label_row(sheet, d))
    return out


def label_row(sheet: str, d: dict[str, Any]) -> LabelRow:
    return LabelRow(
        sheet=sheet,
        paper_id=str(d.get("paper_id") or "").strip(),
        applies_to=str(d.get("applies_to") or "").strip(),
        state=str(d.get("state") or "").strip(),
        values={c: d.get(c) for c in _VALUE_COLS[sheet]},
        quote=str(d.get("quote") or "").strip(),
        adjudication=str(d.get("adjudication") or "").strip(),
    )


def validate_labels(rows: list[LabelRow]) -> list[tuple[str, str, str]]:
    """The checks the labels passed before they were committed: (sheet, paper, failure)."""
    fails: list[tuple[str, str, str]] = []
    for r in rows:
        if r.state not in LABEL_STATES:
            fails.append((r.sheet, r.paper_id, "state not in vocabulary"))
        if not r.applies_to:
            fails.append((r.sheet, r.paper_id, "applies_to empty"))
        if r.state == "reported":
            if not any(str(v or "").strip() for v in r.values.values()):
                fails.append((r.sheet, r.paper_id, "reported, no value"))
            if not r.quote:
                fails.append((r.sheet, r.paper_id, "reported, no quote"))
        if "pending" in r.adjudication.lower():
            fails.append((r.sheet, r.paper_id, "adjudication says pending"))
    return fails


def is_all(applies_to: str) -> bool:
    from extractor_mvp.applies_to_scoring import is_all as _is_all

    return _is_all(applies_to)


# --- records ------------------------------------------------------------------------------------


@dataclass
class StepView:
    """One step of one stored record, as the report reads it."""

    state: str  # in the labels' words (RECORD_TO_LABEL_STATE)
    values: dict[str, Any] = field(default_factory=dict)  # field -> EXTRACTED value
    asked: frozenset[str] = frozenset()  # fields the record's schema has on this step
    streams: dict[str, StepView] | None = None  # by applies_to, when the record carries it
    applies_to: str = "all"  # a stream's part, in the record's words
    quotes: tuple[str, ...] = ()  # the stream's sentences (value and applies_to quotes)


def _carries_applies_to(step_json: dict[str, Any] | None) -> bool:
    """A record written before DESIGN_applies_to.md carries none: a field whose extraction is
    VARIED (0.7.0) counts."""
    if not step_json:
        return False
    return any(
        isinstance(v, dict) and (v.get("extraction") or {}).get("status") == "VARIED"
        for v in step_json.values()
    )


def _streams(kind: str, rows: list[Any], base: StepView) -> dict[str, StepView]:
    """A step's parts (0.7.0): one view per part under the same-string rule. A VARIED field gives
    each part its own value; a field stated for all data gives every part its value. A part whose
    ``performed`` is no is stated_not_performed; one with any value, reported."""
    from fmri_repro.spec.provenance import normalize_applies_to

    streams: dict[str, StepView] = {}
    shared = {k: v for k, v in base.values.items()}
    for r in rows:
        if r.group != kind or r.state != "VARIED":
            continue
        param = r.path.split(".", 1)[1]
        for v in r.variants or []:
            key = normalize_applies_to(v.applies_to)
            view = streams.setdefault(
                key, StepView(base.state, dict(shared), base.asked, None, v.applies_to)
            )
            view.quotes = (*view.quotes, v.span_text) + (
                (v.applies_to_span_text,) if v.applies_to_span_text else ()
            )
            if v.value is None:
                view.state = "not_reported"  # fork C2: no value for any one compared model
                continue
            view.values[param] = _plain(v.value)
            if param == "performed":
                view.state = "stated_not_performed" if v.value is False else "reported"
    for view in streams.values():
        view.values.pop("performed", None)
    return streams


def record_steps(record: dict[str, Any]) -> dict[str, StepView]:
    """The Spatial smoothing row's and temporal filtering's state and values, read with the current
    code (the stored preprocessing parsed to the current schema)."""
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp.cobidas import assess_coverage, kind_state, row_state
    from extractor_mvp.render import flatten

    raw = record.get("extraction_json", record)["preprocessing"]
    prep = parse_any_version(raw)
    rows = flatten(prep)
    version = next((r.extraction_status for r in rows if r.path == "base_pipeline.version"), None)
    coverage = assess_coverage(rows, version, prep.software_mentions)
    sm = next(rc for rc in coverage if rc.row.row_id == "spatial_smoothing")
    states = {
        "spatial_smoothing": row_state(sm, rows),
        "temporal_filtering": kind_state([r for r in rows if r.group == "temporal_filtering"]),
    }
    out: dict[str, StepView] = {}
    raw_steps = {s["kind"]: s for s in raw.get("steps", [])}
    for kind, st in states.items():
        values: dict[str, Any] = {}
        for r in rows:
            if r.group == kind and r.extraction_status == "EXTRACTED":
                values[r.path.split(".", 1)[1]] = _plain(r.value)
        asked = frozenset(r.path.split(".", 1)[1] for r in rows if r.group == kind)
        quotes = tuple(r.span_text for r in rows if r.group == kind and r.span_text)
        view = StepView(RECORD_TO_LABEL_STATE[st], values, asked, quotes=quotes)
        if _carries_applies_to(raw_steps.get(kind)):
            view.streams = _streams(kind, rows, view)
        out[kind] = view
    return out


def _plain(v: Any) -> Any:
    """A SpecifiedTerm (or a list of them) as its resolved member, else its verbatim words."""
    if isinstance(v, list | tuple):
        return [_plain(x) for x in v]
    resolved = getattr(v, "resolved", None)
    if resolved is not None:
        return resolved
    verbatim = getattr(v, "verbatim", None)
    return verbatim if verbatim is not None else v


# --- values -------------------------------------------------------------------------------------

_NUM = re.compile(r"\d+(?:\.\d+)?")


def _num(x: Any) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        m = _NUM.search(str(x or ""))
        return float(m.group(0)) if m else None


def compare_smoothing(
    label: dict[str, Any], rec: dict[str, Any], asked: frozenset[str] | None = None
) -> dict[str, str]:
    out: dict[str, str] = {}
    width, measure = label.get("width"), str(label.get("width_measure") or "").strip()
    if width in (None, ""):
        out["width"] = "not labelled"
    elif "fwhm_mm" not in rec:
        note = "" if measure.upper() == "FWHM" else f" (label {measure or 'unstated'})"
        out["width"] = f"record has no value{note}"
    elif measure.upper() != "FWHM":
        out["width"] = f"measure mismatch (label {measure or 'unstated'}, record FWHM)"
    else:
        out["width"] = "agree" if _num(width) == _num(rec["fwhm_mm"]) else "disagree"
    kernel = str(label.get("kernel") or "").strip()
    if not kernel:
        out["kernel"] = "not labelled"
    elif "kernel_type" not in rec:
        out["kernel"] = "record has no value"
    else:
        out["kernel"] = "agree" if kernel.lower() == str(rec["kernel_type"]).lower() else "disagree"
    return out


_PASS = {"band-pass": "band_pass", "high-pass": "high_pass", "low-pass": "low_pass"}


def label_band(stated: Any) -> tuple[str, tuple[float, ...]]:
    """(unit, numbers) of a band or cutoff as stated: unit "Hz", "s", "cycles", "none" (nothing
    numeric, e.g. "not stated") or "unknown"."""
    s = str(stated or "").strip()
    nums = tuple(float(n) for n in _NUM.findall(s))
    low = s.lower()
    if "cycle" in low:  # "three cycles per scan" has no digits and is still a stated edge
        return "cycles", nums
    if not nums:
        return "none", ()
    if "hz" in low:
        return "Hz", nums
    if re.search(r"\d\s*(s|sec|secs|seconds)\b", low):
        return "s", nums
    return "unknown", nums


def record_hz(rec: dict[str, Any]) -> tuple[float, ...]:
    nums: list[float] = []
    for f in ("effective_band_hz", "nominal_band_hz", "low_hz", "high_hz", "cutoff"):
        v = rec.get(f)
        for x in v if isinstance(v, list | tuple) else [v]:
            if isinstance(x, int | float) and float(x) not in nums:
                nums.append(float(x))
    return tuple(sorted(nums))


def compare_filtering(
    label: dict[str, Any], rec: dict[str, Any], asked: frozenset[str] | None = None
) -> dict[str, str]:
    out: dict[str, str] = {}
    unit, nums = label_band(label.get("band_or_cutoff_as_stated"))
    rec_nums = record_hz(rec)
    if unit == "none":
        out["band"] = "not labelled"
    elif not rec_nums:
        out["band"] = "record has no value" + ("" if unit == "Hz" else f" (label in {unit})")
    elif unit != "Hz":
        out["band"] = f"unit mismatch (label {unit}, record Hz)"
    else:
        out["band"] = "agree" if tuple(sorted(set(nums))) == rec_nums else "disagree"
    lp = str(label.get("pass_type") or "").strip().lower()
    if not lp:
        out["pass_type"] = "not labelled"
    elif lp not in _PASS:
        out["pass_type"] = "label not comparable as stated"
    elif asked is not None and "pass_type" not in asked:
        out["pass_type"] = "not asked in this record's schema"
    elif "pass_type" not in rec:
        out["pass_type"] = "record has no value"
    else:
        out["pass_type"] = "agree" if _PASS[lp] == rec["pass_type"] else "disagree"
    return out


# --- scoring ------------------------------------------------------------------------------------


@dataclass
class Scored:
    row: LabelRow
    outcome: str  # "scored" | "collapsed" | "split" | "missed" | "no record"
    record_state: str | None = None
    values: dict[str, str] = field(default_factory=dict)
    #: the paper's field outcome on this sheet when it was scored as variants (applies_to_scoring)
    scope: FieldScore | None = None

    @property
    def state_agrees(self) -> bool | None:
        return None if self.record_state is None else self.record_state == self.row.state


def _equal(view: StepView, row: LabelRow) -> bool:
    """A record view equals a label row: the state agrees and every labelled value agrees. A value
    the record's schema did not have (``pass_type`` before 0.6.3) is no evidence either way and is
    skipped; a value the record lacks, or one in another unit or measure, is not equal."""
    if view.state != row.state:
        return False
    compare = compare_smoothing if row.sheet == "Smoothing" else compare_filtering
    outcomes = compare(row.values, view.values, view.asked)
    return all(o in _NEUTRAL_FOR_EQUALITY for o in outcomes.values())


_NEUTRAL_FOR_EQUALITY = frozenset({"agree", "not labelled", "not asked in this record's schema"})


def score(labels: list[LabelRow], records: dict[str, dict[str, StepView]]) -> list[Scored]:
    groups: dict[tuple[str, str], list[LabelRow]] = {}
    for r in labels:
        groups.setdefault((r.paper_id, r.sheet), []).append(r)
    scored: dict[int, Scored] = {}
    for (paper, sheet), rows in groups.items():
        steps = records.get(paper)
        if steps is None:
            for r in rows:
                scored[id(r)] = Scored(r, "no record")
            continue
        view = steps[_STEP[sheet]]
        compare = compare_smoothing if sheet == "Smoothing" else compare_filtering
        if len(rows) == 1 and is_all(rows[0].applies_to) and not view.streams:
            r = rows[0]
            scored[id(r)] = Scored(
                r, "scored", view.state, compare(r.values, view.values, view.asked)
            )
            continue
        parts = list((view.streams or {}).values()) or [view]
        preds = [PredictedVariant(p.applies_to, p, p.quotes) for p in parts]
        fs = score_field(
            [LabelVariant(r.applies_to, r, r.quote) for r in rows],
            preds,
            equal=lambda pv, lr: _equal(pv, lr),
        )
        if fs.outcome in ("collapsed", "split"):
            for r in rows:
                scored[id(r)] = Scored(r, fs.outcome, view.state, scope=fs)
            continue
        for r, hit in zip(rows, fs.matches, strict=True):
            if hit is None:
                scored[id(r)] = Scored(r, "missed", scope=fs)
                continue
            part = parts[hit]
            scored[id(r)] = Scored(
                r, "scored", part.state, compare(r.values, part.values, part.asked), scope=fs
            )
    return [scored[id(r)] for r in labels]


def papers_scored(results: list[Scored], sheet: str) -> list[str]:
    return sorted(
        {s.row.paper_id for s in results if s.row.sheet == sheet and s.outcome == "scored"}
    )


def load_records(results_dir: Path) -> dict[str, dict[str, StepView]]:
    out: dict[str, dict[str, StepView]] = {}
    for f in sorted((results_dir / "papers").glob("*.json")):
        out[f.stem] = record_steps(json.loads(f.read_text()))
    return out


# --- report -------------------------------------------------------------------------------------


def _shown(paper_id: str, v: Any) -> str:
    if paper_id in VALUES_WITHHELD:
        return "(withheld)"
    return "" if v in (None, "") else str(v)


def _outcome(paper_id: str, outcome: str) -> str:
    """A withheld paper's value outcome as match or no match only: "measure mismatch (label sigma,
    ...)" or "(label in s)" would say what its label holds."""
    if paper_id not in VALUES_WITHHELD:
        return outcome
    return "match" if outcome == "agree" else "no match"


def render(results: list[Scored], results_dir: str) -> str:
    lines = [
        "# Smoothing and filtering: stored records vs the author's labels (diagnostic)",
        "",
        f"Records: `{results_dir}`, read with the current code. Labels: "
        "`ground_truth/smoothing_filtering_labels_v1.xlsx`. Counts only; no rates.",
        "",
    ]
    for sheet in SHEETS:
        lines += [f"## {sheet}", ""]
        lines.append("| class | paper | applies_to | label state | record state | state | values |")
        lines.append("|---|---|---|---|---|---|---|")
        rows = [s for s in results if s.row.sheet == sheet]
        rows.sort(
            key=lambda s: (CLASS_ORDER.index(contamination_class(s.row.paper_id)), s.row.paper_id)
        )
        for s in rows:
            pid = s.row.paper_id
            applies = _shown(pid, s.row.applies_to)
            if s.outcome != "scored":
                lines.append(
                    f"| {contamination_class(pid)} | {pid} | {applies} | {s.row.state} | "
                    f"{s.outcome} | | |"
                )
                continue
            agree = "agree" if s.state_agrees else "disagree"
            vals = "; ".join(f"{k}: {_outcome(pid, v)}" for k, v in s.values.items())
            lines.append(
                f"| {contamination_class(pid)} | {pid} | {applies} | {s.row.state} | "
                f"{s.record_state} | {agree} | {vals} |"
            )
        lines.append("")
        lines.append(f"Papers scored on {sheet}: {len(papers_scored(results, sheet))}")
        lines.append("")
        lines += _counts(rows)
        lines += _scope_section(rows)
    return "\n".join(lines).rstrip() + "\n"


def _scope_section(rows: list[Scored]) -> list[str]:
    """Per paper scored as variants: its field outcome and the variant counts (DESIGN_applies_to.md
    §5: reported beside the field-level outcome, never instead of it). Counts and classes only."""
    seen: dict[str, Scored] = {}
    for s in rows:
        if s.scope is not None:
            seen.setdefault(s.row.paper_id, s)
    if not seen:
        return []
    out = [
        "Scope (papers whose labels carry parts, or whose record does; DESIGN_applies_to.md §5):",
        "",
        "| paper | field outcome | label variants | matched correct | matched wrong | missed "
        "| spurious |",
        "|---|---|---|---|---|---|---|",
    ]
    for pid in sorted(seen):
        fs = seen[pid].scope
        assert fs is not None
        n_labels = sum(1 for s in rows if s.row.paper_id == pid)
        c = Counter(cls for _, cls in fs.label_classes)
        out.append(
            f"| {pid} | {fs.outcome} | {n_labels} | {c['matched_correct']} | "
            f"{c['matched_wrong']} | {c['missed']} | {len(fs.spurious)} |"
        )
    out.append("")
    return out


def _counts(rows: list[Scored]) -> list[str]:
    out = ["Counts by class and label state (rows):", ""]
    out.append(
        "| class | label state | state agrees | state disagrees | collapsed | split | missed "
        "| no record |"
    )
    out.append("|---|---|---|---|---|---|---|---|")
    for cls in CLASS_ORDER:
        mine = [s for s in rows if contamination_class(s.row.paper_id) == cls]
        for st in LABEL_STATES:
            here = [s for s in mine if s.row.state == st]
            if not here:
                continue
            c = Counter(
                ("agree" if s.state_agrees else "disagree") if s.outcome == "scored" else s.outcome
                for s in here
            )
            out.append(
                f"| {cls} | {st} | {c['agree']} | {c['disagree']} | {c['collapsed']} | "
                f"{c['split']} | {c['missed']} | {c['no record']} |"
            )
    out.append("")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "results/batch_coverage_v4",
    )
    ap.add_argument("--out", type=Path, help="write the report here (default: stdout)")
    args = ap.parse_args(argv)
    labels = load_labels(args.labels)
    fails = validate_labels(labels)
    if fails:
        for f in fails:
            print(f"label check failed: {f}", file=sys.stderr)
        return 1
    text = render(score(labels, load_records(args.results_dir)), str(args.results_dir))
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
