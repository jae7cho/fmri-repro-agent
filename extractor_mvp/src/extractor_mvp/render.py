"""MVP output layer for a single :class:`~fmri_repro.spec.preprocessing.Preprocessing`.

COBIDAS reporting is per-pipeline, so the unit here is exactly one ``Preprocessing``.

REPORT surfaces — safe to show a paper's author
-----------------------------------------------
A report accounts for EVERY COBIDAS D.3 row, including rows the extractor never examined,
because its denominator comes from the standard rather than from the steps present (see
:mod:`extractor_mvp.cobidas`). Only these may be presented as "the report":

- :func:`to_report` — THE supported report surface; listed in :data:`REPORT_SURFACES`,
  which the guard test parametrizes over. Delegates to :func:`to_protocol`.
- :func:`to_protocol` — the implementation behind :func:`to_report`: a tool-agnostic
  Markdown replication protocol that appends :func:`to_cobidas_coverage`. Also listed in
  :data:`REPORT_SURFACES` in its own right, since it is public and holds every current
  caller.
- :func:`to_cobidas_coverage` — the D.3 coverage section on its own.

PARTIAL views — NOT reports
---------------------------
These walk ``flatten()`` rows only, so a D.3 row for which the extractor produces no field
rows (``motion_correction`` today) is ABSENT from their output entirely. Showing one to an
author would report a paper as complete where the tool simply never looked:

- :func:`to_field_table` — per-field text view with per-state counts.
- :func:`to_field_bullets` — condensed markdown, one line per field.

Neither is a completeness report. Use :func:`to_report` for anything author-facing.

Structural
----------
- :func:`flatten` — ``Preprocessing -> list[FieldRow]``. The single source of
  truth. Walks ``base_pipeline`` (incl. the nested ``PipelineRef.version``) then
  ``steps`` in list order (list position *is* pipeline order — never reordered).
- :func:`to_json` — ``preprocessing.model_dump_json(indent=2)``. Carries the version
  stamp (``schema_version``); round-trips via ``model_validate_json`` for a document of
  the CURRENT schema. A document written under an older schema must be read through
  ``fmri_repro.spec.migrations.parse_any_version`` (migrate-then-parse), not this path.

``fmri_repro`` is contract-frozen; rendering lives here on the consumer side.

State model
-----------
A :class:`~fmri_repro.spec.provenance.ProvenancedField` couples an *extraction*
stage (``EXTRACTED`` / ``MISSING_FROM_PAPER`` / ``DEFERRED_TO_CITATION``) with an
*inference* stage (``NOT_APPLICABLE`` / ``INFERRED_DEFAULT`` / ``LEFT_MISSING``).
``FieldRow`` keeps both raw statuses; :func:`_display_state` projects the pair to
one of five display states for the formatters, by this precedence:

1. extraction ``EXTRACTED``                      -> ``EXTRACTED``
2. inference  ``INFERRED_DEFAULT``               -> ``INFERRED_DEFAULT``
3. extraction ``DEFERRED_TO_CITATION``           -> ``DEFERRED_TO_CITATION``
4. extraction ``MISSING_FROM_PAPER``             -> ``MISSING_FROM_PAPER``
5. (otherwise) inference ``LEFT_MISSING``        -> ``LEFT_MISSING``

The spec's coupling validator forbids a ``MISSING``/``DEFERRED`` extraction from
pairing with ``NOT_APPLICABLE`` inference, so the only ``LEFT_MISSING``-inference
tuples are ``(MISSING, LEFT_MISSING)`` and ``(DEFERRED, LEFT_MISSING)`` — both
captured at steps 3-4 above. The ``LEFT_MISSING`` *display* state (step 5) is
therefore a defensive branch under the frozen coupling: all five raw status
values still surface in ``FieldRow.extraction_status`` / ``.inference_status``
(that is what "covers all five states" means), but a single field's collapsed
display label takes one of the four reachable values.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fmri_repro.spec.preprocessing import PipelineRef, Preprocessing, SpecifiedTerm
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    Basis,
    NotApplicable,
    ProvenancedField,
)

from extractor_mvp.cobidas import (
    DIVERGENCE_KINDS,
    RowCoverage,
    assess_coverage,
)
from extractor_mvp.methods_finder import MethodsSlice

# Display-state tokens. ``BASE_NOT_APPLICABLE`` is the from-scratch base_pipeline
# sentinel (one row, no version recursion); the rest mirror the five raw states.
EXTRACTED = "EXTRACTED"
INFERRED_DEFAULT = "INFERRED_DEFAULT"
DEFERRED_TO_CITATION = "DEFERRED_TO_CITATION"
MISSING_FROM_PAPER = "MISSING_FROM_PAPER"
LEFT_MISSING = "LEFT_MISSING"
BASE_NOT_APPLICABLE = "BASE_NOT_APPLICABLE"

#: Display-state order used for the to_field_table header counts (stable, exhaustive).
_STATE_ORDER: tuple[str, ...] = (
    EXTRACTED,
    INFERRED_DEFAULT,
    DEFERRED_TO_CITATION,
    MISSING_FROM_PAPER,
    LEFT_MISSING,
    BASE_NOT_APPLICABLE,
)

#: Condensed labels for to_field_bullets, for the states that carry a value or a
#: citation. The two GAP states are deliberately ABSENT: a gap row's label is its
#: :data:`_REASON_LINE` callout (via :func:`_short_label`), because a fixed label
#: cannot distinguish "the paper omitted this" from "the extractor never looked".
#: Re-adding a MISSING_FROM_PAPER / LEFT_MISSING key here reintroduces that conflation.
_SHORT_LABEL: dict[str, str] = {
    EXTRACTED: "extracted",
    INFERRED_DEFAULT: "inferred",
    DEFERRED_TO_CITATION: "deferred",
    BASE_NOT_APPLICABLE: "not applicable (from-scratch)",
}

_SPAN_QUOTE_MAX = 80


@dataclass
class FieldRow:
    """One flattened provenanced field (or the from-scratch base_pipeline sentinel).

    ``group`` is the section header ("base_pipeline" or ``step.kind``); ``state``
    is the collapsed display state (see :func:`_display_state`). Raw
    ``extraction_status`` / ``inference_status`` are retained so all five
    underlying states remain inspectable.
    """

    path: str
    group: str
    state: str
    cobidas_row: str | None = None
    extraction_status: str | None = None
    inference_status: str | None = None
    value: Any = None
    span_text: str | None = None
    basis_type: str | None = None
    confidence: float | None = None
    basis: Basis | None = None  # full basis object, for protocol note rendering
    left_missing_reason: str | None = None  # LeftMissing.reason, for protocol hole callouts
    searched_terms: list[str] | None = None
    deferral_refs: list[str] | None = None


# ---------------------------------------------------------------------------
# Detection + projection helpers
# ---------------------------------------------------------------------------


def is_provenanced_field(v: Any) -> bool:
    """True iff ``v`` is a :class:`ProvenancedField` (any ``T``).

    ``isinstance`` works here: in pydantic v2 a parametrized generic such as
    ``ProvenancedField[str]`` is a subclass of the generic origin, so
    ``isinstance(field, ProvenancedField)`` returns ``True`` (verified in
    ``test_render`` against a real field from the example spec). The structural
    duck-type (``.extraction.status`` + ``.inference``) is kept as a fallback for
    any object that walks like a provenanced field without subclassing it.
    """
    if isinstance(v, ProvenancedField):
        return True
    extraction = getattr(v, "extraction", None)
    inference = getattr(v, "inference", None)
    return (
        extraction is not None
        and inference is not None
        and hasattr(extraction, "status")
        and hasattr(inference, "status")
    )


def _display_state(extraction_status: str, inference_status: str) -> str:
    """Collapse the coupled (extraction, inference) pair to one display state."""
    if extraction_status == "EXTRACTED":
        return EXTRACTED
    if inference_status == "INFERRED_DEFAULT":
        return INFERRED_DEFAULT
    if extraction_status == "DEFERRED_TO_CITATION":
        return DEFERRED_TO_CITATION
    if extraction_status == "MISSING_FROM_PAPER":
        return MISSING_FROM_PAPER
    return LEFT_MISSING  # defensive — unreachable under the frozen coupling


def _resolved_value(pf: ProvenancedField) -> Any:
    """Extracted value if EXTRACTED, else inferred value if INFERRED_DEFAULT, else None."""
    if pf.extraction.status == "EXTRACTED":
        return pf.extraction.value
    if pf.inference.status == "INFERRED_DEFAULT":
        return pf.inference.value
    return None


def _row_from_field(
    pf: ProvenancedField, path: str, group: str, cobidas_row: str | None
) -> FieldRow:
    ext = pf.extraction
    inf = pf.inference
    row = FieldRow(
        path=path,
        group=group,
        state=_display_state(ext.status, inf.status),
        cobidas_row=cobidas_row,
        extraction_status=ext.status,
        inference_status=inf.status,
        value=_resolved_value(pf),
    )
    if ext.status == "EXTRACTED":
        row.span_text = ext.spans[0].text
    if ext.status in ("MISSING_FROM_PAPER", "DEFERRED_TO_CITATION"):
        row.searched_terms = list(ext.searched_terms)
    if ext.status == "DEFERRED_TO_CITATION":
        row.deferral_refs = [d.ref for d in ext.deferrals]
    if inf.status == "INFERRED_DEFAULT":
        row.basis_type = inf.basis.basis_type
        row.confidence = inf.confidence
        row.basis = inf.basis
    if inf.status == "LEFT_MISSING":
        row.left_missing_reason = inf.reason
    return row


def _resolved_pipeline_ref(pf: ProvenancedField) -> PipelineRef | None:
    """The PipelineRef carried by a ``base_pipeline`` field, if one is resolved.

    Present when the outer arm is EXTRACTED (paper named it) or INFERRED_DEFAULT
    (Configurator supplied it); absent when the pipeline identity itself is
    deferred or missing (no inner ``version`` to recurse into).
    """
    val = _resolved_value(pf)
    return val if isinstance(val, PipelineRef) else None


# ---------------------------------------------------------------------------
# Core flattener
# ---------------------------------------------------------------------------


def flatten(preprocessing: Preprocessing) -> list[FieldRow]:
    """Flatten one :class:`Preprocessing` to ordered :class:`FieldRow` rows.

    Order: ``base_pipeline`` (and its nested ``PipelineRef.version``), then each
    step in ``steps`` list order. Structural fields — ``applies_to``,
    ``intended_fieldmap``, ``PipelineRef.name``, every ``kind`` literal — emit no
    rows (the step classes declare them in ``STRUCTURAL_FIELDS``; ``kind`` and
    ``name`` are never provenanced).
    """
    rows: list[FieldRow] = []

    base = preprocessing.base_pipeline
    if isinstance(base, NotApplicable):
        # From-scratch (Bassett-style): one sentinel row, no version recursion.
        rows.append(
            FieldRow(
                path="base_pipeline",
                group="base_pipeline",
                state=BASE_NOT_APPLICABLE,
                value="not applicable (from-scratch)",
            )
        )
    else:
        rows.append(_row_from_field(base, "base_pipeline", "base_pipeline", None))
        pref = _resolved_pipeline_ref(base)
        if pref is not None:
            # PipelineRef.version is itself a ProvenancedField[str] — a SEPARATE
            # row that can carry a different state than the outer pipeline arm.
            rows.append(
                _row_from_field(pref.version, "base_pipeline.version", "base_pipeline", None)
            )

    for step in preprocessing.steps:
        cls = type(step)
        structural: frozenset[str] = getattr(cls, "STRUCTURAL_FIELDS", frozenset())
        cobidas_row = getattr(cls, "cobidas_row", None)
        for name in cls.model_fields:
            if name in structural:
                continue
            attr = getattr(step, name)
            if not is_provenanced_field(attr):
                continue  # defensive: non-provenanced, non-structural field
            rows.append(_row_from_field(attr, f"{step.kind}.{name}", step.kind, cobidas_row))

    return rows


# ---------------------------------------------------------------------------
# View 1: JSON (canonical round-trip)
# ---------------------------------------------------------------------------


def to_json(preprocessing: Preprocessing) -> str:
    """Canonical JSON serialization; carries the ``schema_version`` stamp.

    Round-trips via ``model_validate_json`` for a CURRENT-schema document. Read
    older-schema artifacts through ``fmri_repro.spec.migrations.parse_any_version``.
    """
    return str(preprocessing.model_dump_json(indent=2))


# ---------------------------------------------------------------------------
# View 2: human text
# ---------------------------------------------------------------------------


def _fmt_specified_term(v: SpecifiedTerm) -> str:
    """Render a 0.5.0 ``SpecifiedTerm``: the resolved member when there is one, always
    showing the paper's verbatim words when they differ; the verbatim term alone when
    unresolved (0.5.0 records it rather than discarding it to a false-missing)."""
    if v.resolved is not None:
        if v.verbatim and str(v.verbatim) != str(v.resolved):
            return f'{v.resolved} (paper: "{v.verbatim}")'
        return str(v.resolved)
    return f'"{v.verbatim}"' if v.verbatim else "(term not recorded)"


def _fmt_value(value: Any) -> str:
    if isinstance(value, PipelineRef):
        return str(value.name)
    if isinstance(value, SpecifiedTerm):
        return _fmt_specified_term(value)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _truncate_quote(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) > _SPAN_QUOTE_MAX:
        return flat[: _SPAN_QUOTE_MAX - 1].rstrip() + "…"
    return flat


def _fmt_field_text(row: FieldRow) -> str:
    """The right-hand value/explanation per the five display states."""
    if row.state == EXTRACTED:
        return f"from paper: {_fmt_value(row.value)}   «{_truncate_quote(row.span_text or '')}»"
    if row.state == INFERRED_DEFAULT:
        return f"inferred: {_fmt_value(row.value)}   ({row.basis_type}, conf {row.confidence})"
    if row.state == DEFERRED_TO_CITATION:
        refs = ", ".join(row.deferral_refs or []) or "(unspecified)"
        return f"deferred to {refs}"
    if row.state in (MISSING_FROM_PAPER, LEFT_MISSING):
        # CHARACTERISE the absence, never label it. A bare "not reported" is a claim about
        # the AUTHOR'S MANUSCRIPT, and is false for every field the extractor never targeted
        # (>=19 of 27 rows on any paper — _assemble hardcodes ``not_targeted_by_mvp`` for
        # those). Same table, same wording as :func:`_protocol_main`, so the surfaces cannot
        # contradict each other about the same field. (LEFT_MISSING display is defensive —
        # unreachable via flatten() — but treated identically, as in the protocol view.)
        return _reason_detail(row)
    if row.state == BASE_NOT_APPLICABLE:
        return "not applicable (from-scratch)"
    return ""


def to_field_table(preprocessing: Preprocessing) -> str:
    """Per-field text view with per-state counts. **NOT a completeness report.**

    Deterministic, no-LLM. Walks ``flatten()`` rows only, so a COBIDAS D.3 row for which
    the extractor produces no field rows (``motion_correction`` today) does not appear at
    all. Presenting this to an author would report their paper as complete where the tool
    never looked. Use :func:`to_report` for author-facing output; this view is for
    inspecting extraction.
    """
    rows = flatten(preprocessing)
    counts = {state: 0 for state in _STATE_ORDER}
    for r in rows:
        counts[r.state] = counts.get(r.state, 0) + 1

    lines: list[str] = []
    lines.append(f"Preprocessing — {len(rows)} field(s)")
    summary = "  ".join(f"{state}={counts[state]}" for state in _STATE_ORDER if counts.get(state))
    lines.append(f"  states: {summary}")
    lines.append("")

    # base_pipeline section (rows whose group is base_pipeline)
    base_rows = [r for r in rows if r.group == "base_pipeline"]
    lines.append("base_pipeline:")
    for r in base_rows:
        if r.state == BASE_NOT_APPLICABLE:
            lines.append("  not applicable (from-scratch)")
        else:
            lines.append(f"  {r.path}: {_fmt_field_text(r)}")
    lines.append("")

    # steps in list order
    for step in preprocessing.steps:
        cobidas_row = getattr(type(step), "cobidas_row", None)
        lines.append(f"[{step.kind}]  (cobidas: {cobidas_row})")
        for r in (row for row in rows if row.group == step.kind):
            field_name = r.path.split(".", 1)[1] if "." in r.path else r.path
            lines.append(f"  {field_name}: {_fmt_field_text(r)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# View 3: condensed markdown bullets
# ---------------------------------------------------------------------------


def _fmt_value_suffix(row: FieldRow) -> str:
    if row.state in (EXTRACTED, INFERRED_DEFAULT) and row.value is not None:
        return f" {_fmt_value(row.value)}"
    if row.state == DEFERRED_TO_CITATION and row.deferral_refs:
        return f" ({', '.join(row.deferral_refs)})"
    return ""


def to_field_bullets(preprocessing: Preprocessing) -> str:
    """Condensed markdown, one bullet per field under a bold step header. **NOT a report.**

    Same limitation as :func:`to_field_table`: ``flatten()`` rows only, so a D.3 row with no
    extractor field rows is absent entirely. Use :func:`to_report` for author-facing output.
    """
    rows = flatten(preprocessing)
    lines: list[str] = []
    current_group: str | None = None
    for r in rows:
        if r.group != current_group:
            current_group = r.group
            lines.append(f"**{current_group}**")
        label = _short_label(r)
        lines.append(f"- {r.path}: {label}{_fmt_value_suffix(r)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# View 4: tool-agnostic replication protocol (Markdown)
# ---------------------------------------------------------------------------
#
# Answers "how would I reproduce this, and what can't the paper tell me?" rather
# than "did we extract correctly?". Holes are rendered as explicit actionable
# callouts (COBIDAS: flag the unreported against a controlled vocabulary rather
# than silently dropping it, Nichols et al. 2017), and inferred values are marked
# distinctly from extracted ones with their basis + confidence-vs-ceiling.
#
# NOTE on the LEFT_MISSING display state: :func:`_display_state` collapses a
# ``(MISSING extraction, LEFT_MISSING inference)`` field to the ``MISSING_FROM_PAPER``
# *display* state, so the distinct ``LEFT_MISSING`` protocol line below is a
# DEFENSIVE branch, unreachable via :func:`flatten` for a valid ``Preprocessing``
# (same status as the ``LEFT_MISSING`` branch in :func:`_fmt_field_text`). Real
# missing-and-not-inferred fields render with the ``MISSING_FROM_PAPER`` wording.


# Reason partition for MISSING/LEFT_MISSING gap fields — separates source-absence
# from extractor-coverage so the completeness count is not a conflation. Keyed on the
# BASE reason (``reason.split(":",1)[0]``, to absorb suffixes like
# ``extraction_quote_unresolved:quote_not_found``). An unknown base reason falls to
# ``unclassified`` and is NEVER folded into a source-completeness bucket.
_REASON_BUCKET: dict[str, str] = {
    "not_stated_in_text": "not_reported",
    "no_base_pipeline_named": "not_reported",
    "version_deferred_to_kb": "not_reported",
    "value_not_in_literal": "unmappable",
    "not_targeted_by_mvp": "not_covered",  # mirrors batch.py _IGNORE_REASON
    "extraction_quote_unresolved": "not_covered",
    "field_not_in_schema_version": "not_covered",  # field absent when the source doc was written
    # Previously unmapped, so they fell to ``unclassified`` and leaked their raw internal
    # token into author-facing output. All three are live producers in extractor.py.
    "value_not_numeric": "unmappable",  # same shape as value_not_in_literal: uncoercible to type
    "extraction_quote_missing": "not_covered",
    "deferral_quote_unresolved": "not_covered",
}

#: Per-field callout wording by base reason (source-absence vs extractor limitation).
_REASON_LINE: dict[str, str] = {
    "not_stated_in_text": "not reported in source — you must specify",
    "no_base_pipeline_named": "no base pipeline named in source — you must specify",
    "version_deferred_to_kb": "version not reported in source — you must specify",
    "value_not_in_literal": (
        "reported in source but not resolvable to a controlled value — map manually"
    ),
    "not_targeted_by_mvp": "not examined by the extractor — check the source yourself",
    "extraction_quote_unresolved": "value present in source but span unresolved (extractor limitation)",
    "field_not_in_schema_version": (
        "field did not exist in the schema version this document was written under "
        "(added by a later version; forward-migrated)"
    ),
    # These three fire BEFORE (or instead of) quote validation, so nothing has confirmed the
    # value is grounded in the source. They therefore describe what the EXTRACTOR did, and
    # assert nothing about what the manuscript reports. See the semantics note in
    # tests/test_render.py::test_every_producible_reason_base_is_mapped.
    "value_not_numeric": "extractor returned a non-numeric value for this field — enter manually",
    "extraction_quote_missing": (
        "extractor returned a value with no supporting quote — unverifiable, "
        "check the source yourself"
    ),
    "deferral_quote_unresolved": (
        "extractor reported a deferral to another source but could not locate the "
        "deferring sentence — check the source yourself"
    ),
}

#: Completeness-header gap buckets: (bucket key, display label), fixed order, non-zero only.
_BUCKET_HEADER: tuple[tuple[str, str], ...] = (
    ("not_reported", "not reported in source"),
    ("unmappable", "reported but unmappable to controlled vocabulary"),
    ("not_covered", "not covered by extractor"),
    ("unclassified", "unclassified"),
)


def _reason_base(row: FieldRow) -> str:
    """The BASE LeftMissing.reason for a gap row (suffix after ``:`` dropped)."""
    return (row.left_missing_reason or "").split(":", 1)[0]


def _gap_bucket(row: FieldRow) -> str:
    """Bucket a MISSING/LEFT_MISSING row by its base LeftMissing.reason."""
    return _REASON_BUCKET.get(_reason_base(row), "unclassified")


def _reason_detail(row: FieldRow) -> str:
    """The per-field callout for a gap row — THE single source of gap wording.

    Every surface that renders an absence routes through here, so no two surfaces can
    describe the same field differently. An unmapped base reason falls back to a literal
    ``unspecified (reason: ...)`` rather than being silently absorbed into a source-absence
    claim; ``test_every_producible_reason_base_is_mapped`` keeps that fallback unreachable
    for reasons this codebase actually produces.
    """
    base = _reason_base(row)
    return _REASON_LINE.get(base, f"unspecified (reason: {base})")


def _short_label(row: FieldRow) -> str:
    """Condensed bullet label for :func:`to_field_bullets`.

    Gap rows characterise their reason (same wording as every other surface); all other
    states use their fixed :data:`_SHORT_LABEL`.
    """
    if row.state in (MISSING_FROM_PAPER, LEFT_MISSING):
        return _reason_detail(row)
    return _SHORT_LABEL.get(row.state, row.state)


def _fmt_basis_note(row: FieldRow) -> str:
    """Human basis note for an INFERRED_DEFAULT row: the basis specifics, the
    Configurator-authored ``note`` (rendered verbatim, never authored here), and
    ``confidence X / ceiling Y``. Dispatch is exhaustive over the ``Basis`` union."""
    b = row.basis
    if b is None:
        return ""
    if b.basis_type == "date_inferred_version":
        core = (
            f"{b.tool} {b.inferred_version} — latest release on or before paper date {b.paper_date}"
        )
    elif b.basis_type == "version_default":
        core = f"{b.tool} {b.version} (version stated/confirmed)"
    elif b.basis_type == "prior_publication":
        core = f"from cited work {b.citation}"
    elif b.basis_type == "lab_prior":
        core = f"lab default ({b.lab_id})"
    elif b.basis_type == "field_convention":
        core = f"field convention ({b.source})"
    elif b.basis_type == "derived":
        core = f"derived from {', '.join(b.source_field_ids)}"
    else:  # defensive; the union is closed
        core = ""
    if b.note:
        core += f" — {b.note}"
    ceiling = BASIS_CEILINGS[b.basis_type]
    core += f" (confidence {row.confidence} / ceiling {ceiling})"
    return core


def _protocol_main(row: FieldRow, label: str, *, equals_for_extracted: bool) -> str:
    """One protocol line for ``row`` under ``label``, per display state.

    ``equals_for_extracted`` picks ``label = value`` (step fields) vs ``label: value``
    (the base_pipeline header line). Non-extracted states always use ``label: ...``.
    """
    st = row.state
    sep = " = " if equals_for_extracted else ": "
    if st == EXTRACTED:
        line = f"{label}{sep}{_fmt_value(row.value)}   [from paper]"
        if row.span_text:
            line += f"  «{_truncate_quote(row.span_text)}»"
        return line
    if st == INFERRED_DEFAULT:
        return f"{label}{sep}{_fmt_value(row.value)}   [INFERRED — not stated in source]"
    if st == DEFERRED_TO_CITATION:
        refs = ", ".join(row.deferral_refs or []) or "(unspecified)"
        return f"{label}: deferred to {refs} — resolve by consulting the cited source"
    if st in (MISSING_FROM_PAPER, LEFT_MISSING):
        # Reason-partitioned callout: source-absence vs extractor-coverage. (LEFT_MISSING
        # display is defensive — unreachable via flatten() — but treated identically.)
        return f"{label}: {_reason_detail(row)}"
    if st == BASE_NOT_APPLICABLE:
        return f"{label}: built from scratch (no named base pipeline)"
    return label


def _protocol_note_lines(row: FieldRow) -> list[str]:
    """The indented basis-note line(s) that follow an INFERRED bullet (else none)."""
    if row.state == INFERRED_DEFAULT:
        return [_fmt_basis_note(row)]
    return []


def to_protocol(
    preprocessing: Preprocessing,
    source: str | None = None,
    *,
    methods_slice: MethodsSlice | None = None,
) -> str:
    """Tool-agnostic Markdown replication protocol over ``flatten()``.

    A REPORT surface, listed in :data:`REPORT_SURFACES` in its own right: appends
    :func:`to_cobidas_coverage`, so every D.3 row is accounted for including rows the
    extractor never examined. Remains public and unchanged; :func:`to_report` is the name
    new callers should reach for and delegates here.

    Deterministic, no-LLM. Renders the base pipeline (name + a version sub-line), a
    four-way completeness header (specified · inferred · deferred · require-your-input,
    counted over the full ``flatten()`` tally), then each preprocessing step in
    pipeline (list) order with its COBIDAS tag. Holes become explicit "REQUIRED — you
    must specify" callouts; inferred values are marked and annotated with their basis.

    When ``methods_slice`` is supplied and flagged ``suspicious``, a single warning line
    is rendered under the title: a spec extracted from a whole-document fallback or a
    bloated slice has different provenance semantics and must say so on its face.
    """
    rows = flatten(preprocessing)
    lines: list[str] = []
    lines.append(f"# Replication Protocol — {source}" if source else "# Replication Protocol")
    lines.append("")

    if methods_slice is not None and methods_slice.suspicious:
        if methods_slice.found_via == "fallback_full_text":
            lines.append(
                "> ⚠ Methods section not identified — extracted from the FULL document; "
                "spans may resolve against Introduction / Discussion / References."
            )
        else:
            lines.append(
                "> ⚠ Methods slice may include Results / Discussion "
                f"(slice/full = {methods_slice.slice_ratio:.0%}, ended at "
                f"{methods_slice.ended_at!r})."
            )
        lines.append("")

    # --- Base pipeline (header line + optional version sub-line) ---
    base_rows = [r for r in rows if r.group == "base_pipeline"]
    base_main = next((r for r in base_rows if r.path == "base_pipeline"), None)
    version_row = next((r for r in base_rows if r.path == "base_pipeline.version"), None)
    if base_main is not None:
        lines.append(_protocol_main(base_main, "Base pipeline", equals_for_extracted=False))
        lines.extend(f"    {n}" for n in _protocol_note_lines(base_main))
        if version_row is not None:
            lines.append("  " + _protocol_main(version_row, "version", equals_for_extracted=True))
            lines.extend(f"      {n}" for n in _protocol_note_lines(version_row))
    lines.append("")

    # --- Completeness header: reason-partitioned, non-zero segments only ---
    # Source-completeness states (extracted/inferred/deferred), then the gap fields
    # partitioned by reason so extractor-coverage is not conflated with source-absence.
    counts = {state: 0 for state in _STATE_ORDER}
    bucket_counts = {bucket: 0 for bucket, _ in _BUCKET_HEADER}
    for r in rows:
        counts[r.state] = counts.get(r.state, 0) + 1
        if r.state in (MISSING_FROM_PAPER, LEFT_MISSING):
            bucket_counts[_gap_bucket(r)] += 1
    segments: list[str] = []
    if counts[EXTRACTED]:
        segments.append(f"{counts[EXTRACTED]} specified in source")
    if counts[INFERRED_DEFAULT]:
        segments.append(f"{counts[INFERRED_DEFAULT]} inferred")
    if counts[DEFERRED_TO_CITATION]:
        segments.append(f"{counts[DEFERRED_TO_CITATION]} deferred")
    for bucket, label in _BUCKET_HEADER:
        if bucket_counts[bucket]:
            segments.append(f"{bucket_counts[bucket]} {label}")
    lines.append("Completeness: " + " · ".join(segments))
    lines.append("")

    # --- Steps in pipeline (list) order ---
    lines.append("## Preprocessing steps (pipeline order)")
    lines.append("")
    for n, step in enumerate(preprocessing.steps, start=1):
        cobidas_row = getattr(type(step), "cobidas_row", None)
        lines.append(f"### {n}. {step.kind}   (COBIDAS: {cobidas_row})")
        for r in (row for row in rows if row.group == step.kind):
            param = r.path.split(".", 1)[1] if "." in r.path else r.path
            lines.append(f"- {_protocol_main(r, param, equals_for_extracted=True)}")
            lines.extend(f"    {note}" for note in _protocol_note_lines(r))
        lines.append("")

    # --- COBIDAS D.3 coverage (grounds the gap figure in the standard) ---
    lines.append(to_cobidas_coverage(preprocessing).rstrip())

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# The report surface
# ---------------------------------------------------------------------------


def to_report(
    preprocessing: Preprocessing,
    source: str | None = None,
    *,
    methods_slice: MethodsSlice | None = None,
) -> str:
    """THE supported report surface — the only output safe to present as "the report".

    Delegates to :func:`to_protocol`, which appends :func:`to_cobidas_coverage` so every
    COBIDAS D.3 row is accounted for, including rows the extractor never examined. The
    partial views (:func:`to_field_table`, :func:`to_field_bullets`) walk ``flatten()``
    rows only and silently omit such rows; they are not reports.
    """
    return to_protocol(preprocessing, source, methods_slice=methods_slice)


#: Surfaces a caller may present as "the report". The guard test parametrizes over this
#: tuple: a surface listed here without a coverage section fails, and a surface NOT listed
#: here is not a sanctioned report. :func:`to_protocol` is listed in its own right, not
#: merely reached through :func:`to_report` — it is documented as a report and holds every
#: current caller, so covering it only while delegation happens to hold would leave the
#: guard resting on an implementation detail.
REPORT_SURFACES: tuple[Callable[..., str], ...] = (to_report, to_protocol)


def to_cobidas_coverage(preprocessing: Preprocessing) -> str:
    """A COBIDAS D.3 (preprocessing) coverage section over ``flatten()``.

    Deterministic, pure, no LLM/IO. Grounds the ``not covered by extractor`` figure in the
    standard: a D.3 row is ADDRESSED iff the paper reports (EXTRACTED / DEFERRED_TO_CITATION)
    a value on any mapped step kind — extraction arm only, so an AESPA-inferred value never
    counts as a report. Non-compliance is claimed ONLY for the one unconditional row
    (Software: version + revision number); every other unaddressed mandatory row is an
    honest "not reported whether performed", since D.3 requires reporting only if the step
    was performed and presence cannot be read from text.
    """
    rows = flatten(preprocessing)
    version_row = next((r for r in rows if r.path == "base_pipeline.version"), None)
    coverage = assess_coverage(rows, version_row.extraction_status if version_row else None)
    by_id = {rc.row.row_id: rc for rc in coverage}

    lines: list[str] = ["## COBIDAS D.3 coverage (preprocessing)", ""]

    # Partition, do NOT aggregate: an "addressed / 16" fraction is dominated by tool coverage
    # (the extractor targets fields on only a few rows), not by the paper's compliance. Report
    # what AESPA can assess separately from what it can't, and keep mandatory / non-mandatory
    # numerators apart. The denominator that means anything is rows-AESPA-assesses.
    mandatory = [rc for rc in coverage if rc.row.mandatory]
    mand_assessed = [rc for rc in mandatory if rc.covered_by_extractor]
    mand_addressed = [rc for rc in mand_assessed if rc.addressed]
    mand_not_reported = [rc for rc in mand_assessed if not rc.addressed]
    mand_not_assessed = [rc for rc in mandatory if not rc.covered_by_extractor]
    non_mandatory = [rc for rc in coverage if not rc.row.mandatory]
    non_mand_addressed = [rc for rc in non_mandatory if rc.addressed]
    divergence_present = [s.kind for s in preprocessing.steps if s.kind in DIVERGENCE_KINDS]

    violation = (
        " (incl. Software — unconditional violation)"
        if any(rc.row.row_id == "software" for rc in mand_not_reported)
        else ""
    )
    lines.append(f"Mandatory rows: {len(mandatory)}")
    lines.append(
        f"  Assessed by AESPA: {len(mand_assessed)}  →  "
        f"addressed {len(mand_addressed)} · not reported {len(mand_not_reported)}{violation}"
    )
    lines.append(f"  Not assessed by AESPA: {len(mand_not_assessed)}")
    lines.append(
        f"Non-mandatory rows: {len(non_mandatory)} ({len(non_mand_addressed)} addressed)  ·  "
        f"Beyond COBIDAS: {len(divergence_present)} steps"
    )
    lines.append(
        "  (The 'not assessed' count is a TOOL gap — the extractor targets fields on only a "
        "few rows — not a statement about the paper. Silence on the rest is not measurable "
        "from text. The one unconditional, citable COBIDAS claim here is the Software row.)"
    )
    lines.append("")

    def _tag(rc: RowCoverage) -> str:
        # Distinct wording from the field-level "not assessed by current extractor" callout:
        # this is the ROW-level statement (no field on any mapping kind is targeted).
        return "" if rc.covered_by_extractor else "  (no fields assessed by current extractor)"

    # 1. Unconditional violation: only the Software row can appear here.
    # The coverage condition is the SAME one the header requires at the `violation` line
    # above (mand_not_reported is a subset of mand_assessed, i.e. covered_by_extractor).
    # Without it this branch asserts non-compliance from a row the tool could not assess —
    # which is inference from absence of evidence, and it fired on real papers: see
    # cobidas._software_coverage for the NotApplicable two-producer case.
    software = by_id["software"]
    if software.covered_by_extractor and not software.addressed:
        # One heading, four lines: the finding is the same (the version is not reported) but
        # the action differs. See DELTA_software_row_deferral.md §8. A deferring paper must
        # NOT receive the bare "No version reported" line written for the unnamed case —
        # _base_pipeline_name returns None when no PipelineRef resolves, so without this
        # branch it would read exactly as a paper that named nothing at all.
        base_row = next((r for r in rows if r.path == "base_pipeline"), None)
        deferred_refs = (
            base_row.deferral_refs
            if base_row is not None and base_row.extraction_status == "DEFERRED_TO_CITATION"
            else None
        )
        if deferred_refs:
            # rstrip the terminator: refs are author-shaped strings and some already end
            # in a period ("Glasser et al."), which would render as "et al..".
            joined = ", ".join(deferred_refs).rstrip(".")
            detail = f"Version not reported; pipeline identity deferred to {joined}."
        else:
            name = _base_pipeline_name(preprocessing)
            named = f"Pipeline named: {name}. " if name else ""
            if version_row is not None and version_row.inference_status == "INFERRED_DEFAULT":
                ver = "Version inferred by AESPA, not reported by the paper."
            else:
                ver = "No version reported by the paper."
            detail = f"{named}{ver}"
        lines.append("### Not reported (mandatory, unconditional)")
        lines.append(
            "- Software: version and revision number NOT REPORTED — COBIDAS D.3 requires "
            f"this for each software used. ({detail})"
        )
        lines.append("")

    # 2. Conditional mandatory rows, unaddressed: honest gaps, not violations.
    conditional = [
        rc for rc in coverage if rc.row.mandatory and not rc.row.unconditional and not rc.addressed
    ]
    if conditional:
        lines.append("### Not reported whether performed (mandatory if performed)")
        for rc in conditional:
            lines.append(f"- {rc.row.d3_aspect}{_tag(rc)}")
        lines.append(
            "  (Silence is not a COBIDAS violation for these rows; the standard requires "
            "reporting only if the step was performed. Presence cannot be determined from "
            "the text.)"
        )
        lines.append("")

    # 3. Non-mandatory rows, unaddressed.
    optional = [rc for rc in coverage if not rc.row.mandatory and not rc.addressed]
    if optional:
        lines.append("### Optional per COBIDAS")
        for rc in optional:
            lines.append(f"- {rc.row.d3_aspect} (N){_tag(rc)}")
        lines.append("")

    # 4. AESPA extensions with no D.3 row (never in the denominator).
    if divergence_present:
        lines.append("### Beyond COBIDAS (AESPA extensions)")
        for kind in divergence_present:
            lines.append(f"- {kind}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _base_pipeline_name(preprocessing: Preprocessing) -> str | None:
    """The base pipeline's name if one is resolved (paper-named or inferred), else None."""
    base = preprocessing.base_pipeline
    if isinstance(base, NotApplicable):
        return None
    pref = _resolved_pipeline_ref(base)
    return pref.name if pref is not None else None
