"""Scoring the four rows added on 2026-11-11 (second set) against the author's labels
(``ground_truth/preproc_rows_labels_v1.xlsx``): gradient_distortion_correction,
intersubject_registration, resting_state_feature and software. PRE-REGISTERED 2026-11-11, written
before any label on these sheets exists; ``tests/test_preproc_rows_scoring.py`` pins this file's
sha256 and each per-sheet script's, like the first twelve (``preproc_rows_scoring.py``, whose rules
and file this module reuses and does not change). No model calls; counts only, no rates.

These rows are not one schema step each, so each sheet says where its record values come from:

- **gradient_distortion_correction.** State: the report's own row state for the D.3 row
  "Gradient distortion correction" (``cobidas.row_state``). That row reads the whole
  distortion_correction step, so a paper with susceptibility correction only shows there as
  reported; the label decides whether that is right. Values: ``method`` and ``tool`` against the
  distortion_correction step's, only when the record's ``source`` is gradient_nonlinearity;
  otherwise "record has no value".
- **intersubject_registration.** State: the report's row state for "Intersubject registration"
  (spatial_normalization and surface_projection). Values: ``method`` against
  spatial_normalization.method or surface_projection.surface_registration; ``volume_or_surface``
  against the kinds the record states anything for (volume, surface, or both); ``template`` against
  spatial_normalization.target_space or surface_projection.target_surface; ``resolution`` against
  resolution_mm; ``warp_type`` against warp or transform_type; ``interpolation`` against
  interpolation; ``cost_function``: not asked in the schema. A value agrees when it agrees with any
  of its record fields. applies_to: parts from spatial_normalization's varied fields.
- **resting_state_feature.** A D.3 row the extractor does not assess (``cobidas.EXCLUDED_D3_ROWS``):
  every row (whatever its applies_to) is scored directly, record state not_assessed and every value
  "not asked in this record's schema", never through the parts matcher. The sheet's report is the
  labels' own counts.
- **software.** One row per package, keyed by name. The record's packages are
  ``cobidas.software_mentions_for_row`` (the Software row's own list: named software, and the base
  pipeline). A label package matches the record package whose name is the same (case, spaces, "_"
  and "-" ignored) or has the same content words (``part_names.content_words``); one to one, label
  order. A matched package: state reported when the record holds a version, partially_reported when
  not; ``version_as_stated`` digit-exact against the record's version; ``used_for`` against the
  record's words. An unmatched label package is missed; an unmatched record package is spurious. A
  label row with no name (not_reported, "none named") agrees when the record names no software.
  Per paper, the label's Software state (every package reported: reported; none named:
  not_reported; else partially_reported; deferred kept when every package is deferred) is shown
  beside the report's row state.

Values are compared as stated, by ``preproc_rows_scoring.compare_value``. Rows of liu_2005,
tang_2025 and wheaton_2004 print states and match / no match only, never a value, an applies_to or
a package name. With no label rows on a sheet yet, the run prints the expected schema and exits 0.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import preproc_rows_scoring as base
from score_smoothing_filtering import (
    CLASS_ORDER,
    LABEL_STATES,
    RECORD_TO_LABEL_STATE,
    VALUES_WITHHELD,
    StepView,
    _carries_applies_to,
    _streams,
    contamination_class,
)

#: sheet -> its value columns, as merge_labels.ROW_LABEL_FIELDS (a test holds the two equal)
FIELDS: dict[str, tuple[str, ...]] = {
    "gradient_distortion_correction": ("method", "tool"),
    "intersubject_registration": (
        "method",
        "volume_or_surface",
        "template",
        "resolution",
        "warp_type",
        "interpolation",
        "cost_function",
    ),
    "resting_state_feature": ("measure", "band_hz", "reho_neighbourhood", "reho_measure"),
    "software": ("version_as_stated", "used_for"),
}
SHEETS: tuple[str, ...] = tuple(FIELDS)
KEY: dict[str, str] = {"software": "name"}

#: intersubject_registration: label field -> the record fields it is compared against
INTERSUBJECT_MAP: dict[str, tuple[str, ...]] = {
    "method": ("spatial_normalization.method", "surface_projection.surface_registration"),
    "template": ("spatial_normalization.target_space", "surface_projection.target_surface"),
    "resolution": ("spatial_normalization.resolution_mm",),
    "warp_type": ("spatial_normalization.warp", "spatial_normalization.transform_type"),
    "interpolation": ("spatial_normalization.interpolation",),
    "cost_function": (),
}
GRADIENT_SOURCE = "gradient_nonlinearity"


def key(sheet: str) -> str:
    return KEY.get(sheet, "applies_to")


def columns(sheet: str) -> tuple[str, ...]:
    return ("paper_id", key(sheet), "state", *FIELDS[sheet], "quote", "notes", "adjudication")


# --- labels -------------------------------------------------------------------------------------


def load_labels(sheet: str, path: Path = base.LABELS) -> list[base.RowLabel]:
    """Every non-empty row of the sheet; an absent workbook or sheet is no labels. A software row's
    package name is carried in ``applies_to``."""
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
            base.RowLabel(
                sheet=sheet,
                paper_id=str(d.get("paper_id") or "").strip(),
                applies_to=str(d.get(key(sheet)) or "").strip(),
                state=str(d.get("state") or "").strip(),
                values={f: d.get(f) for f in FIELDS[sheet]},
                quote=str(d.get("quote") or "").strip(),
                adjudication=str(d.get("adjudication") or "").strip(),
            )
        )
    return out


def validate_labels(sheet: str, rows: list[base.RowLabel]) -> list[tuple[str, str]]:
    """The first twelve's checks; software's key may be blank only on a not_reported row, and its
    reported rows need a version."""
    fails = []
    for r in rows:
        if r.state not in LABEL_STATES:
            fails.append((r.paper_id, "state not in vocabulary"))
        if not r.applies_to and not (sheet == "software" and r.state == "not_reported"):
            fails.append((r.paper_id, f"{key(sheet)} empty"))
        if r.state == "reported":
            if not any(str(v or "").strip() for v in r.values.values()):
                fails.append((r.paper_id, "reported, no value"))
            if not r.quote:
                fails.append((r.paper_id, "reported, no quote"))
        if "pending" in r.adjudication.lower():
            fails.append((r.paper_id, "adjudication says pending"))
    return fails


# --- records ------------------------------------------------------------------------------------


def _parsed(record: dict[str, Any]) -> tuple[Any, list[Any], dict[str, Any]]:
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp.render import flatten

    raw = record.get("extraction_json", record)["preprocessing"]
    prep = parse_any_version(raw)
    return prep, flatten(prep), raw


def report_row_state(prep: Any, rows: list[Any], row_id: str) -> str:
    """The report's own state for one D.3 row, in the labels' words."""
    from extractor_mvp.cobidas import assess_coverage, row_state

    version = next((r.extraction_status for r in rows if r.path == "base_pipeline.version"), None)
    rc = next(
        c for c in assess_coverage(rows, version, prep.software_mentions) if c.row.row_id == row_id
    )
    return RECORD_TO_LABEL_STATE[row_state(rc, rows)]


def _value(r: Any) -> Any:
    return base._plain_keep(r.value)


def _source_is_gradient(value: Any) -> bool:
    """The record's source (a list of terms, or one) names gradient_nonlinearity."""
    items = value if isinstance(value, list | tuple) else [value]
    return any(base._norm(GRADIENT_SOURCE) in base._forms(v) for v in items if v is not None)


def gradient_view(record: dict[str, Any]) -> StepView:
    prep, rows, _ = _parsed(record)
    state = report_row_state(prep, rows, "gradient_distortion_correction")
    mine = [r for r in rows if r.group == "distortion_correction"]
    source = next((r for r in mine if r.path == "distortion_correction.source"), None)
    gradient = (
        source is not None
        and source.extraction_status == "EXTRACTED"
        and _source_is_gradient(_value(source))
    )
    values: dict[str, Any] = {}
    if gradient:
        for r in mine:
            name = r.path.split(".", 1)[1]
            if name in FIELDS["gradient_distortion_correction"] and r.extraction_status == (
                "EXTRACTED"
            ):
                values[name] = _value(r)
    quotes = tuple(r.span_text for r in mine if r.span_text) if gradient else ()
    return StepView(
        state, values, frozenset(FIELDS["gradient_distortion_correction"]), None, "all", quotes
    )


def intersubject_view(record: dict[str, Any]) -> StepView:
    prep, rows, raw = _parsed(record)
    state = report_row_state(prep, rows, "intersubject_registration")
    kinds = ("spatial_normalization", "surface_projection")
    mine = [r for r in rows if r.group in kinds]
    by_path = {r.path: r for r in mine}
    values: dict[str, Any] = {}
    asked = set()
    for label_field, paths in INTERSUBJECT_MAP.items():
        here = [by_path[p] for p in paths if p in by_path]
        if here:
            asked.add(label_field)
        got = [_value(r) for r in here if r.extraction_status == "EXTRACTED"]
        if got:
            values[label_field] = got[0] if len(got) == 1 else ("any of", got)
    stated = [
        k for k in kinds if any(r.extraction_status == "EXTRACTED" for r in mine if r.group == k)
    ]
    asked.add("volume_or_surface")
    if stated:
        values["volume_or_surface"] = [
            "volume" if k == "spatial_normalization" else "surface" for k in stated
        ]
    quotes = tuple(r.span_text for r in mine if r.span_text)
    view = StepView(state, values, frozenset(asked), None, "all", quotes)
    step_json = next(
        (s for s in raw.get("steps", []) if s.get("kind") == "spatial_normalization"), None
    )
    if _carries_applies_to(step_json):
        sn_rows = [r for r in rows if r.group == "spatial_normalization"]
        parts = _streams("spatial_normalization", sn_rows, StepView(state, {}, frozenset()))
        for part in parts.values():
            part.values = _intersubject_part_values(part.values)
            part.asked = view.asked
        view.streams = parts
    return view


def _intersubject_part_values(step_values: dict[str, Any]) -> dict[str, Any]:
    """A spatial_normalization part's values under the label's field names."""
    out: dict[str, Any] = {}
    for label_field, paths in INTERSUBJECT_MAP.items():
        for p in paths:
            kind, name = p.split(".", 1)
            if kind == "spatial_normalization" and name in step_values:
                out.setdefault(label_field, step_values[name])
    out["volume_or_surface"] = ["volume"]
    return out


def not_assessed_view(record: dict[str, Any]) -> StepView:
    return StepView("not_assessed", {}, frozenset())


VIEWS = {
    "gradient_distortion_correction": gradient_view,
    "intersubject_registration": intersubject_view,
    "resting_state_feature": not_assessed_view,
}


def load_records(results_dir: Path, sheet: str) -> dict[str, Any]:
    reader = software_record if sheet == "software" else VIEWS[sheet]
    return {
        f.stem: reader(json.loads(f.read_text()))
        for f in sorted((results_dir / "papers").glob("*.json"))
    }


# --- values -------------------------------------------------------------------------------------


def compare_value(label: str, rec: Any) -> str:
    """``preproc_rows_scoring.compare_value``, with two shapes of this module: ("any of", values)
    agrees when any one agrees, and volume_or_surface's kinds compare as a set of words ("both"
    is volume and surface)."""
    if isinstance(rec, tuple) and len(rec) == 2 and rec[0] == "any of":
        return "agree" if any(compare_value(label, v) == "agree" for v in rec[1]) else "disagree"
    if (
        isinstance(rec, list)
        and rec
        and all(isinstance(x, str) for x in rec)
        and set(rec) <= {"volume", "surface"}
    ):
        said = set(re.findall(r"volume|surface", label.lower()))
        if "both" in label.lower():
            said = {"volume", "surface"}
        return "agree" if said == set(rec) else "disagree"
    return base.compare_value(label, rec)


def compare_version(label: str, rec: str) -> str:
    """A software version, digit-exact: the label's numbers are the record's, in order ("v6.0.4"
    and "6.0.4" agree; "6.0" and "6.0.4" do not). No digits on either side: the words, as stated."""
    a, b = base._NUM.findall(label), base._NUM.findall(str(rec))
    if not a and not b:
        return "agree" if base._norm(label) == base._norm(rec) else "disagree"
    return "agree" if [float(x) for x in a] == [float(x) for x in b] else "disagree"


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
        elif f == "version_as_stated":
            out[f] = compare_version(text, view.values[f])
        else:
            out[f] = compare_value(text, view.values[f])
    return out


def _equal(view: StepView, row: base.RowLabel) -> bool:
    return view.state == row.state and all(
        o in base._NEUTRAL for o in compare(row.values, view).values()
    )


def score(labels: list[base.RowLabel], records: dict[str, StepView]) -> list[base.Scored]:
    """The first twelve's ``score`` (same classes, same order of tests), with this module's value
    comparison."""
    from extractor_mvp.applies_to_scoring import (
        LabelVariant,
        PredictedVariant,
        is_all,
        score_field,
    )

    groups: dict[str, list[base.RowLabel]] = {}
    for r in labels:
        groups.setdefault(r.paper_id, []).append(r)
    scored: dict[int, base.Scored] = {}
    for paper, rows in groups.items():
        view = records.get(paper)
        if view is None:
            for r in rows:
                scored[id(r)] = base.Scored(r, "no record")
            continue
        if len(rows) == 1 and is_all(rows[0].applies_to) and not view.streams:
            r = rows[0]
            scored[id(r)] = base.Scored(r, "scored", view.state, compare(r.values, view))
            continue
        parts = list((view.streams or {}).values()) or [view]
        fs = score_field(
            [LabelVariant(r.applies_to, r, r.quote) for r in rows],
            [PredictedVariant(p.applies_to, p, p.quotes) for p in parts],
            equal=lambda pv, lr: _equal(pv, lr),
        )
        if fs.outcome in ("collapsed", "split"):
            for r in rows:
                scored[id(r)] = base.Scored(r, fs.outcome, view.state, scope=fs)
            continue
        for r, hit in zip(rows, fs.matches, strict=True):
            if hit is None:
                scored[id(r)] = base.Scored(r, "missed", scope=fs)
                continue
            part = parts[hit]
            scored[id(r)] = base.Scored(r, "scored", part.state, compare(r.values, part), scope=fs)
    return [scored[id(r)] for r in labels]


def score_not_assessed(
    labels: list[base.RowLabel], records: dict[str, StepView]
) -> list[base.Scored]:
    """resting_state_feature: each row against its paper's not-assessed view; no parts."""
    out = []
    for r in labels:
        view = records.get(r.paper_id)
        if view is None:
            out.append(base.Scored(r, "no record"))
        else:
            out.append(base.Scored(r, "scored", view.state, compare(r.values, view)))
    return out


# --- software -----------------------------------------------------------------------------------


@dataclass
class SoftwareRecord:
    packages: list[Any]  # cobidas.Mention: name, version, used_for
    row_state: str  # the report's Software row state, in the labels' words


def software_record(record: dict[str, Any]) -> SoftwareRecord:
    from extractor_mvp.cobidas import software_mentions_for_row

    prep, rows, _ = _parsed(record)
    verified, _n = software_mentions_for_row(rows, prep.software_mentions)
    return SoftwareRecord(list(verified), report_row_state(prep, rows, "software"))


def same_package(a: str, b: str) -> bool:
    from extractor_mvp.part_names import content_words

    if base._norm(a) == base._norm(b):
        return True
    ca, cb = content_words(a), content_words(b)
    return bool(ca) and ca == cb


@dataclass
class SoftwareScored:
    row: base.RowLabel
    outcome: str  # "scored" | "missed" | "none named" | "no record"
    record_state: str | None = None
    values: dict[str, str] = field(default_factory=dict)

    @property
    def state_agrees(self) -> bool | None:
        return None if self.record_state is None else self.record_state == self.row.state


@dataclass
class SoftwarePaper:
    paper_id: str
    label_state: str
    report_state: str | None
    spurious: int


def label_paper_state(rows: list[base.RowLabel]) -> str:
    """The label's Software state for a paper, from its package rows."""
    named = [r.state for r in rows if r.applies_to]
    if not named:
        return "not_reported"
    if all(s == "reported" for s in named):
        return "reported"
    if all(s == "deferred" for s in named):
        return "deferred"
    return "partially_reported"


def score_software(
    labels: list[base.RowLabel], records: dict[str, SoftwareRecord]
) -> tuple[list[SoftwareScored], list[SoftwarePaper]]:
    groups: dict[str, list[base.RowLabel]] = {}
    for r in labels:
        groups.setdefault(r.paper_id, []).append(r)
    scored: dict[int, SoftwareScored] = {}
    papers: list[SoftwarePaper] = []
    for pid, rows in groups.items():
        rec = records.get(pid)
        if rec is None:
            for r in rows:
                scored[id(r)] = SoftwareScored(r, "no record")
            papers.append(SoftwarePaper(pid, label_paper_state(rows), None, 0))
            continue
        taken: set[int] = set()
        for r in rows:
            if not r.applies_to:
                state = "not_reported" if not rec.packages else "partially_reported"
                scored[id(r)] = SoftwareScored(r, "none named", state)
                continue
            hit = next(
                (
                    i
                    for i, m in enumerate(rec.packages)
                    if i not in taken and same_package(r.applies_to, m.name)
                ),
                None,
            )
            if hit is None:
                scored[id(r)] = SoftwareScored(r, "missed")
                continue
            taken.add(hit)
            m = rec.packages[hit]
            view = StepView(
                "reported" if m.version else "partially_reported",
                {"version_as_stated": m.version, "used_for": m.used_for},
                frozenset(FIELDS["software"]),
            )
            scored[id(r)] = SoftwareScored(r, "scored", view.state, compare(r.values, view))
        papers.append(
            SoftwarePaper(
                pid, label_paper_state(rows), rec.row_state, len(rec.packages) - len(taken)
            )
        )
    return [scored[id(r)] for r in labels], papers


# --- report -------------------------------------------------------------------------------------


def expected_schema(sheet: str, results_dir: Path | None) -> str:
    return "\n".join(
        [
            f"# {sheet}: no labels yet",
            "",
            f"Workbook: `{base.LABELS.relative_to(base.REPO)}`, sheet `{sheet}`.",
            f"Columns: {', '.join(columns(sheet))}.",
            f"States: {', '.join(LABEL_STATES)}.",
            "Rules: preproc_rows_scoring_v2.py's docstring (pre-registered 2026-11-11).",
            "Records that would be read: "
            + (
                f"`{base._shown_path(results_dir)}`"
                if results_dir
                else "none hold every walk paper"
            )
            + ".",
            "",
        ]
    )


def render_software(
    results: list[SoftwareScored], papers: list[SoftwarePaper], results_dir: Path
) -> str:
    lines = [
        "# software: stored records vs the author's labels",
        "",
        f"Records: `{base._shown_path(results_dir)}`, read with the current code. Labels: "
        f"`{base.LABELS.relative_to(base.REPO)}`, sheet `software`. Pre-registered 2026-11-11. "
        "Counts only; no rates.",
        "",
        "| class | paper | package | label state | record state | state | values |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in sorted(
        results,
        key=lambda s: (CLASS_ORDER.index(contamination_class(s.row.paper_id)), s.row.paper_id),
    ):
        pid = s.row.paper_id
        name = "(withheld)" if pid in VALUES_WITHHELD else (s.row.applies_to or "(none named)")
        head = f"| {contamination_class(pid)} | {pid} | {name} | {s.row.state} |"
        if s.outcome in ("missed", "no record"):
            lines.append(f"{head} {s.outcome} | | |")
            continue
        vals = "; ".join(f"{k}: {base._outcome(pid, v)}" for k, v in s.values.items())
        lines.append(
            f"{head} {s.record_state} | {'agree' if s.state_agrees else 'disagree'} | {vals} |"
        )
    lines += [
        "",
        "Per paper: the label's Software state beside the report's row state, and the record's "
        "packages no label row matched:",
        "",
        "| paper | label state | report state | state | record packages unmatched |",
        "|---|---|---|---|---|",
    ]
    for p in sorted(papers, key=lambda p: p.paper_id):
        agree = (
            ""
            if p.report_state is None
            else ("agree" if p.report_state == p.label_state else "disagree")
        )
        lines.append(
            f"| {p.paper_id} | {p.label_state} | {p.report_state or 'no record'} | {agree} | "
            f"{p.spurious} |"
        )
    c = Counter(s.outcome for s in results)
    lines += [
        "",
        f"Packages: {sum(1 for s in results if s.row.applies_to)}; scored {c['scored']}, missed "
        f"{c['missed']}, no record {c['no record']}; rows naming no software {c['none named']}.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run(sheet: str, labels_path: Path, results_dir: Path | None) -> tuple[int, str]:
    labels = load_labels(sheet, labels_path)
    if not labels:
        return 0, expected_schema(sheet, results_dir)
    fails = validate_labels(sheet, labels)
    if fails:
        return 1, "".join(f"label check failed: {sheet} {f}\n" for f in fails)
    if results_dir is None:
        return 2, "no results directory holds every walk paper; pass --results-dir\n"
    if sheet == "software":
        results, papers = score_software(labels, load_records(results_dir, sheet))
        return 0, render_software(results, papers, results_dir)
    scorer = score_not_assessed if sheet == "resting_state_feature" else score
    return 0, base.render(sheet, scorer(labels, load_records(results_dir, sheet)), results_dir)


def main(sheet: str, argv: list[str] | None = None) -> int:
    if sheet not in SHEETS:
        raise ValueError(f"no sheet {sheet!r}")
    ap = argparse.ArgumentParser(
        description=f"Score the {sheet} labels (pre-registered 2026-11-11)."
    )
    ap.add_argument("--labels", type=Path, default=base.LABELS)
    ap.add_argument(
        "--results-dir", type=Path, help="default: the latest records (module docstring)"
    )
    ap.add_argument("--out", type=Path, help="write the report here (default: stdout)")
    args = ap.parse_args(argv)
    code, text = run(sheet, args.labels, args.results_dir or base.latest_results_dir())
    if code:
        print(text, end="", file=sys.stderr)
        return code
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0
