"""Scoring the remaining COBIDAS rows against the author's labels
(``ground_truth/preproc_rows_labels_v1.xlsx``), one sheet at a time. PRE-REGISTERED 2026-11-11,
written before any label exists; ``tests/test_preproc_rows_scoring.py`` pins this file's sha256 and
each per-sheet script's, so a change after labels exist is a dated, visible event. No model calls;
counts only, no rates.

The smoothing/filtering pattern (``score_smoothing_filtering.py``), per sheet:

- **State agreement.** The record's state is ``cobidas.kind_state`` over the step's fields (the
  report's own precedence: performed=no, reported, deferred, unverifiable, not reported, not
  assessed), in the labels' words.
- **Value agreement, as stated.** Each labelled field against the record's EXTRACTED value of the
  field of the same name. Nothing is converted: a number agrees when the label's numbers are the
  record's (digit-exact, units ignored, never converted); a yes/no field when the label says yes or
  no to match; a term when the label equals the paper's verbatim words or the resolved member
  (case, spaces, "_" and "-" ignored); a list when every item matches one record item and no item is
  left over. Otherwise one of: "not labelled", "not asked in this record's schema", "record has no
  value", "disagree".
- **applies_to classes** (``extractor_mvp.applies_to_scoring``, DESIGN_applies_to.md §5): a paper
  with one "all" row is scored against the record directly; any other paper's rows are one field:
  collapsed, split, or per row matched (by quote overlap, fork E2) and scored, or missed; a record
  part matching no row is spurious.

Records: the newest ``results/*/papers`` directory holding a record for every paper on
``ground_truth/preproc_rows_walk_v1.csv`` (``--results-dir`` overrides); the report names it.
Rows of liu_2005, tang_2025 and wheaton_2004 print states and match / no match only, never a value
or an applies_to (the standing held-out rule).

With no label rows on the sheet yet, the run prints the schema it expects and exits 0.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_smoothing_filtering import (
    CLASS_ORDER,
    LABEL_STATES,
    RECORD_TO_LABEL_STATE,
    VALUES_WITHHELD,
    StepView,
    _carries_applies_to,
    _plain,
    _streams,
    contamination_class,
)

from extractor_mvp.applies_to_scoring import (
    FieldScore,
    LabelVariant,
    PredictedVariant,
    is_all,
    score_field,
)

EXTRACTOR = Path(__file__).resolve().parents[1]
REPO = EXTRACTOR.parent
LABELS = REPO / "ground_truth" / "preproc_rows_labels_v1.xlsx"
WALK = REPO / "ground_truth" / "preproc_rows_walk_v1.csv"
RESULTS = EXTRACTOR / "results"

#: The sheets, in the workbook's order: each is the step kind of its name.
SHEETS: tuple[str, ...] = (
    "slice_time_correction",
    "nuisance_regression",
    "compcor",
    "ica_denoise",
    "scrub",
    "despike",
    "nonsteadystate_removal",
    "coregistration",
    "distortion_correction",
    "brain_extraction",
    "segmentation",
    "intensity_correction",
)


def _read_step_fields() -> dict[str, tuple[str, ...]]:
    from fmri_repro.spec import preprocessing as spec

    return {
        s: tuple(k for k in getattr(spec, f"{s.upper()}_FIELD_META") if k != "performed")
        for s in SHEETS
    }


#: Read once, at import, in the schema's source order (a dict reordered later in the process, e.g.
#: by a test's monkeypatch, does not move the columns).
_STEP_FIELDS = _read_step_fields()


def step_fields(sheet: str) -> tuple[str, ...]:
    """The sheet's value columns: the schema's ``<KIND>_FIELD_META`` names without ``performed``."""
    return _STEP_FIELDS[sheet]


def columns(sheet: str) -> tuple[str, ...]:
    return (
        "paper_id",
        "applies_to",
        "state",
        *step_fields(sheet),
        "quote",
        "notes",
        "adjudication",
    )


# --- labels -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RowLabel:
    sheet: str
    paper_id: str
    applies_to: str
    state: str
    values: dict[str, Any]
    quote: str
    adjudication: str


def load_labels(sheet: str, path: Path = LABELS) -> list[RowLabel]:
    """Every non-empty row of the sheet; an absent workbook or sheet is no labels."""
    if not path.exists():
        return []
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    if sheet not in wb.sheetnames:
        return []
    rows = list(wb[sheet].iter_rows(values_only=True))
    if not rows:
        return []
    head = [str(h) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(c not in (None, "") for c in r):
            continue
        d = dict(zip(head, r, strict=False))
        out.append(
            RowLabel(
                sheet=sheet,
                paper_id=str(d.get("paper_id") or "").strip(),
                applies_to=str(d.get("applies_to") or "").strip(),
                state=str(d.get("state") or "").strip(),
                values={f: d.get(f) for f in step_fields(sheet)},
                quote=str(d.get("quote") or "").strip(),
                adjudication=str(d.get("adjudication") or "").strip(),
            )
        )
    return out


def validate_labels(rows: list[RowLabel]) -> list[tuple[str, str]]:
    """The smoothing/filtering checks: (paper, failure)."""
    fails = []
    for r in rows:
        if r.state not in LABEL_STATES:
            fails.append((r.paper_id, "state not in vocabulary"))
        if not r.applies_to:
            fails.append((r.paper_id, "applies_to empty"))
        if r.state == "reported":
            if not any(str(v or "").strip() for v in r.values.values()):
                fails.append((r.paper_id, "reported, no value"))
            if not r.quote:
                fails.append((r.paper_id, "reported, no quote"))
        if "pending" in r.adjudication.lower():
            fails.append((r.paper_id, "adjudication says pending"))
    return fails


# --- records ------------------------------------------------------------------------------------


def walk_ids(path: Path = WALK) -> list[str]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [r["paper_id"] for r in csv.DictReader(fh)]


def latest_results_dir(results: Path = RESULTS, ids: list[str] | None = None) -> Path | None:
    """The newest ``results/*/papers`` directory (by modification time) holding every walk paper."""
    want = set(ids if ids is not None else walk_ids())
    best: tuple[float, Path] | None = None
    for papers in results.glob("*/papers"):
        have = {p.stem for p in papers.glob("*.json")}
        if want <= have:
            t = papers.stat().st_mtime
            if best is None or t > best[0]:
                best = (t, papers.parent)
    return best[1] if best else None


def record_view(record: dict[str, Any], sheet: str) -> StepView:
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp.cobidas import kind_state
    from extractor_mvp.render import flatten

    raw = record.get("extraction_json", record)["preprocessing"]
    prep = parse_any_version(raw)
    rows = [r for r in flatten(prep) if r.group == sheet]
    values = {
        r.path.split(".", 1)[1]: _plain_keep(r.value)
        for r in rows
        if r.extraction_status == "EXTRACTED"
    }
    values.pop("performed", None)
    asked = frozenset(r.path.split(".", 1)[1] for r in rows)
    quotes = tuple(r.span_text for r in rows if r.span_text)
    view = StepView(RECORD_TO_LABEL_STATE[kind_state(rows)], values, asked, quotes=quotes)
    step_json = next((s for s in raw.get("steps", []) if s.get("kind") == sheet), None)
    if _carries_applies_to(step_json):
        view.streams = _streams(sheet, rows, view)
    return view


def _plain_keep(v: Any) -> Any:
    """The record's value with a term's verbatim words kept beside its resolved member."""
    if isinstance(v, list | tuple) and v and hasattr(v[0], "verbatim"):
        return [_term(x) for x in v]
    if hasattr(v, "verbatim"):
        return _term(v)
    return v


def _term(v: Any) -> dict[str, Any]:
    return {"verbatim": getattr(v, "verbatim", None), "resolved": getattr(v, "resolved", None)}


def load_records(results_dir: Path, sheet: str) -> dict[str, StepView]:
    return {
        f.stem: record_view(json.loads(f.read_text()), sheet)
        for f in sorted((results_dir / "papers").glob("*.json"))
    }


# --- values as stated ---------------------------------------------------------------------------

_NUM = re.compile(r"\d+(?:\.\d+)?")
_YES = frozenset({"yes", "true", "performed", "applied", "y"})
_NO = frozenset({"no", "false", "not performed", "not applied", "n"})


def _norm(x: Any) -> str:
    return " ".join(re.sub(r"[_\-]", " ", str(x).lower()).split())


def _forms(item: Any) -> set[str]:
    """The ways a record item may be written: a term's verbatim words and its resolved member."""
    if isinstance(item, dict):
        return {
            _norm(v) for v in (item.get("verbatim"), item.get("resolved")) if v not in (None, "")
        }
    return {_norm(_plain(item))}


def _items(text: str) -> list[str]:
    return [_norm(t) for t in re.split(r",|;|\band\b|&|/", text) if t.strip()]


def compare_value(label: str, rec: Any) -> str:
    """One labelled field against the record's value, as stated: "agree" or "disagree"."""
    if isinstance(rec, bool):
        said = _norm(label)
        ok = (rec and said in _YES) or (not rec and said in _NO)
        return "agree" if ok else "disagree"
    if isinstance(rec, int | float):
        return "agree" if [float(n) for n in _NUM.findall(label)] == [float(rec)] else "disagree"
    if (
        isinstance(rec, list | tuple)
        and rec
        and all(isinstance(x, int | float) or x is None for x in rec)
    ):
        want = sorted(float(x) for x in rec if x is not None)
        return "agree" if sorted(float(n) for n in _NUM.findall(label)) == want else "disagree"
    if isinstance(rec, list | tuple):
        left = [_forms(x) for x in rec]
        items = _items(label)
        if len(items) != len(left):
            return "disagree"
        for it in items:
            hit = next((i for i, forms in enumerate(left) if it in forms), None)
            if hit is None:
                return "disagree"
            left.pop(hit)
        return "agree"
    return "agree" if _norm(label) in _forms(rec) else "disagree"


def compare(label: dict[str, Any], view: StepView) -> dict[str, str]:
    out = {}
    for f, v in label.items():
        text = "" if v is None else str(v).strip()
        if not text:
            out[f] = "not labelled"
        elif f not in view.asked:
            out[f] = "not asked in this record's schema"
        elif f not in view.values or view.values[f] in (None, "", []):
            out[f] = "record has no value"
        else:
            out[f] = compare_value(text, view.values[f])
    return out


_NEUTRAL = frozenset({"agree", "not labelled", "not asked in this record's schema"})


def _equal(view: StepView, row: RowLabel) -> bool:
    return view.state == row.state and all(
        o in _NEUTRAL for o in compare(row.values, view).values()
    )


# --- scoring ------------------------------------------------------------------------------------


@dataclass
class Scored:
    row: RowLabel
    outcome: str  # "scored" | "collapsed" | "split" | "missed" | "no record"
    record_state: str | None = None
    values: dict[str, str] = field(default_factory=dict)
    scope: FieldScore | None = None

    @property
    def state_agrees(self) -> bool | None:
        return None if self.record_state is None else self.record_state == self.row.state


def score(labels: list[RowLabel], records: dict[str, StepView]) -> list[Scored]:
    groups: dict[str, list[RowLabel]] = {}
    for r in labels:
        groups.setdefault(r.paper_id, []).append(r)
    scored: dict[int, Scored] = {}
    for paper, rows in groups.items():
        view = records.get(paper)
        if view is None:
            for r in rows:
                scored[id(r)] = Scored(r, "no record")
            continue
        if len(rows) == 1 and is_all(rows[0].applies_to) and not view.streams:
            r = rows[0]
            scored[id(r)] = Scored(r, "scored", view.state, compare(r.values, view))
            continue
        parts = list((view.streams or {}).values()) or [view]
        fs = score_field(
            [LabelVariant(r.applies_to, r, r.quote) for r in rows],
            [PredictedVariant(p.applies_to, p, p.quotes) for p in parts],
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
            scored[id(r)] = Scored(r, "scored", part.state, compare(r.values, part), scope=fs)
    return [scored[id(r)] for r in labels]


# --- report -------------------------------------------------------------------------------------


def _outcome(paper_id: str, outcome: str) -> str:
    if paper_id not in VALUES_WITHHELD:
        return outcome
    return "match" if outcome == "agree" else "no match"


def _shown_path(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(EXTRACTOR))
    except ValueError:
        return str(p)


def expected_schema(sheet: str, results_dir: Path | None) -> str:
    """What a "no labels yet" run prints: the sheet it reads and how it scores it."""
    return "\n".join(
        [
            f"# {sheet}: no labels yet",
            "",
            f"Workbook: `{LABELS.relative_to(REPO)}`, sheet `{sheet}`.",
            f"Columns: {', '.join(columns(sheet))}.",
            f"States: {', '.join(LABEL_STATES)}.",
            "Values are compared as stated (numbers digit-exact, units never converted; terms against "
            "the paper's words or the resolved member; lists item by item); applies_to classes per "
            "DESIGN_applies_to.md §5.",
            "Records that would be read: "
            + (f"`{_shown_path(results_dir)}`" if results_dir else "none hold every walk paper")
            + ".",
            "",
        ]
    )


def render(sheet: str, results: list[Scored], results_dir: Path) -> str:
    lines = [
        f"# {sheet}: stored records vs the author's labels",
        "",
        f"Records: `{_shown_path(results_dir)}`, read with the current code. Labels: "
        f"`{LABELS.relative_to(REPO)}`, sheet `{sheet}`. Pre-registered 2026-11-11. Counts only; "
        "no rates.",
        "",
        "| class | paper | applies_to | label state | record state | state | values |",
        "|---|---|---|---|---|---|---|",
    ]
    rows = sorted(
        results,
        key=lambda s: (CLASS_ORDER.index(contamination_class(s.row.paper_id)), s.row.paper_id),
    )
    for s in rows:
        pid = s.row.paper_id
        applies = "(withheld)" if pid in VALUES_WITHHELD else s.row.applies_to
        head = f"| {contamination_class(pid)} | {pid} | {applies} | {s.row.state} |"
        if s.outcome != "scored":
            lines.append(f"{head} {s.outcome} | | |")
            continue
        vals = "; ".join(f"{k}: {_outcome(pid, v)}" for k, v in s.values.items())
        agree = "agree" if s.state_agrees else "disagree"
        lines.append(f"{head} {s.record_state} | {agree} | {vals} |")
    lines += [
        "",
        f"Papers scored: {len({s.row.paper_id for s in results if s.outcome == 'scored'})}",
        "",
    ]
    lines += [
        "Counts by class and label state (rows):",
        "",
        "| class | label state | state agrees | state disagrees | collapsed | split | missed "
        "| no record |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cls in CLASS_ORDER:
        for st in LABEL_STATES:
            here = [
                s
                for s in results
                if contamination_class(s.row.paper_id) == cls and s.row.state == st
            ]
            if not here:
                continue
            c = Counter(
                ("agree" if s.state_agrees else "disagree") if s.outcome == "scored" else s.outcome
                for s in here
            )
            lines.append(
                f"| {cls} | {st} | {c['agree']} | {c['disagree']} | {c['collapsed']} | "
                f"{c['split']} | {c['missed']} | {c['no record']} |"
            )
    scopes: dict[str, Scored] = {}
    for s in results:
        if s.scope is not None:
            scopes.setdefault(s.row.paper_id, s)
    if scopes:
        lines += [
            "",
            "Scope (DESIGN_applies_to.md §5):",
            "",
            "| paper | field outcome | label variants | matched correct | matched wrong | missed "
            "| spurious |",
            "|---|---|---|---|---|---|---|",
        ]
        for pid in sorted(scopes):
            fs = scopes[pid].scope
            assert fs is not None
            c = Counter(cls for _, cls in fs.label_classes)
            n = sum(1 for s in results if s.row.paper_id == pid)
            lines.append(
                f"| {pid} | {fs.outcome} | {n} | {c['matched_correct']} | {c['matched_wrong']} | "
                f"{c['missed']} | {len(fs.spurious)} |"
            )
    return "\n".join(lines).rstrip() + "\n"


def main(sheet: str, argv: list[str] | None = None) -> int:
    if sheet not in SHEETS:
        raise ValueError(f"no sheet {sheet!r}")
    ap = argparse.ArgumentParser(
        description=f"Score the {sheet} labels (pre-registered 2026-11-11)."
    )
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument(
        "--results-dir", type=Path, help="default: the latest records (module docstring)"
    )
    ap.add_argument("--out", type=Path, help="write the report here (default: stdout)")
    args = ap.parse_args(argv)
    results_dir = args.results_dir or latest_results_dir()
    labels = load_labels(sheet, args.labels)
    if not labels:
        print(expected_schema(sheet, results_dir), end="")
        return 0
    fails = validate_labels(labels)
    if fails:
        for f in fails:
            print(f"label check failed: {sheet} {f}", file=sys.stderr)
        return 1
    if results_dir is None:
        print("no results directory holds every walk paper; pass --results-dir", file=sys.stderr)
        return 2
    text = render(sheet, score(labels, load_records(results_dir, sheet)), results_dir)
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0
