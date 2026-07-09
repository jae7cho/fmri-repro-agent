"""MVP output layer for a single :class:`~fmri_repro.spec.preprocessing.Preprocessing`.

One flattener, three thin formatters (COBIDAS reporting is per-pipeline, so the
unit here is exactly one ``Preprocessing``):

- :func:`flatten` — ``Preprocessing -> list[FieldRow]``. The single source of
  truth. Walks ``base_pipeline`` (incl. the nested ``PipelineRef.version``) then
  ``steps`` in list order (list position *is* pipeline order — never reordered).
- :func:`to_json` — ``preprocessing.model_dump_json(indent=2)``. Carries the version
  stamp (``schema_version``); round-trips via ``model_validate_json`` for a document of
  the CURRENT schema. A document written under an older schema must be read through
  ``fmri_repro.spec.migrations.parse_any_version`` (migrate-then-parse), not this path.
- :func:`to_text` — deterministic, no-LLM human report with per-state counts.
- :func:`to_bullets` — condensed markdown, one line per field.

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

from dataclasses import dataclass
from typing import Any

from fmri_repro.spec.preprocessing import PipelineRef, Preprocessing
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    Basis,
    NotApplicable,
    ProvenancedField,
)

# Display-state tokens. ``BASE_NOT_APPLICABLE`` is the from-scratch base_pipeline
# sentinel (one row, no version recursion); the rest mirror the five raw states.
EXTRACTED = "EXTRACTED"
INFERRED_DEFAULT = "INFERRED_DEFAULT"
DEFERRED_TO_CITATION = "DEFERRED_TO_CITATION"
MISSING_FROM_PAPER = "MISSING_FROM_PAPER"
LEFT_MISSING = "LEFT_MISSING"
BASE_NOT_APPLICABLE = "BASE_NOT_APPLICABLE"

#: Display-state order used for the to_text header counts (stable, exhaustive).
_STATE_ORDER: tuple[str, ...] = (
    EXTRACTED,
    INFERRED_DEFAULT,
    DEFERRED_TO_CITATION,
    MISSING_FROM_PAPER,
    LEFT_MISSING,
    BASE_NOT_APPLICABLE,
)

#: Condensed labels for to_bullets.
_SHORT_LABEL: dict[str, str] = {
    EXTRACTED: "extracted",
    INFERRED_DEFAULT: "inferred",
    DEFERRED_TO_CITATION: "deferred",
    MISSING_FROM_PAPER: "not reported",
    LEFT_MISSING: "not inferred",
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


def _fmt_value(value: Any) -> str:
    if isinstance(value, PipelineRef):
        return str(value.name)
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
    if row.state == MISSING_FROM_PAPER:
        return "not reported"
    if row.state == LEFT_MISSING:
        return "not inferred (no basis)"
    if row.state == BASE_NOT_APPLICABLE:
        return "not applicable (from-scratch)"
    return ""


def to_text(preprocessing: Preprocessing) -> str:
    """Deterministic, no-LLM human report of one ``Preprocessing``."""
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


def to_bullets(preprocessing: Preprocessing) -> str:
    """Condensed markdown: one bullet per field, grouped under a bold step header."""
    rows = flatten(preprocessing)
    lines: list[str] = []
    current_group: str | None = None
    for r in rows:
        if r.group != current_group:
            current_group = r.group
            lines.append(f"**{current_group}**")
        label = _SHORT_LABEL.get(r.state, r.state)
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
}

#: Per-field callout wording by base reason (source-absence vs extractor limitation).
_REASON_LINE: dict[str, str] = {
    "not_stated_in_text": "not reported in source — you must specify",
    "no_base_pipeline_named": "no base pipeline named in source — you must specify",
    "version_deferred_to_kb": "version not reported in source — you must specify",
    "value_not_in_literal": (
        "reported in source but not resolvable to a controlled value — map manually"
    ),
    "not_targeted_by_mvp": "not assessed by current extractor",
    "extraction_quote_unresolved": "value present in source but span unresolved (extractor limitation)",
    "field_not_in_schema_version": (
        "field did not exist in the schema version this document was written under "
        "(added by a later version; forward-migrated)"
    ),
}

#: Completeness-header gap buckets: (bucket key, display label), fixed order, non-zero only.
_BUCKET_HEADER: tuple[tuple[str, str], ...] = (
    ("not_reported", "not reported in source"),
    ("unmappable", "reported but unmappable to controlled vocabulary"),
    ("not_covered", "not covered by extractor"),
    ("unclassified", "unclassified"),
)


def _gap_bucket(row: FieldRow) -> str:
    """Bucket a MISSING/LEFT_MISSING row by its base LeftMissing.reason."""
    base = (row.left_missing_reason or "").split(":", 1)[0]
    return _REASON_BUCKET.get(base, "unclassified")


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
        base = (row.left_missing_reason or "").split(":", 1)[0]
        detail = _REASON_LINE.get(base, f"unspecified (reason: {base})")
        return f"{label}: {detail}"
    if st == BASE_NOT_APPLICABLE:
        return f"{label}: built from scratch (no named base pipeline)"
    return label


def _protocol_note_lines(row: FieldRow) -> list[str]:
    """The indented basis-note line(s) that follow an INFERRED bullet (else none)."""
    if row.state == INFERRED_DEFAULT:
        return [_fmt_basis_note(row)]
    return []


def to_protocol(preprocessing: Preprocessing, source: str | None = None) -> str:
    """Tool-agnostic Markdown replication protocol over ``flatten()``.

    Deterministic, no-LLM. Renders the base pipeline (name + a version sub-line), a
    four-way completeness header (specified · inferred · deferred · require-your-input,
    counted over the full ``flatten()`` tally), then each preprocessing step in
    pipeline (list) order with its COBIDAS tag. Holes become explicit "REQUIRED — you
    must specify" callouts; inferred values are marked and annotated with their basis.
    """
    rows = flatten(preprocessing)
    lines: list[str] = []
    lines.append(f"# Replication Protocol — {source}" if source else "# Replication Protocol")
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

    return "\n".join(lines).rstrip() + "\n"
