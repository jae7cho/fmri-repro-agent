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
from pathlib import Path
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
    is_expanded,
    kind_state,
    mapped_rows,
    row_state,
    software_mentions_for_row,
    validation_tag,
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
    span_repairs: list[str] | None = None  # Span.repairs (0.5.3): the named substitutions, tier 6
    span_recovered: bool = False  # Extracted.span_recovered: the quote matched only after the
    # corrupted-source tolerant tier repaired mangled PDF text. Carried to the report because a
    # span located by repair is weaker evidence than a clean match, and a flag no surface reads
    # is not a disclosure (the field shipped in v0.4.0 with no consumer).


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
        row.span_recovered = bool(getattr(ext, "span_recovered", False))
        repairs = list(getattr(ext.spans[0], "repairs", None) or [])
        row.span_repairs = repairs or None
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
        return ", ".join(
            _fmt_specified_term(v) if isinstance(v, SpecifiedTerm) else str(v) for v in value
        )
    return str(value)


#: Shown on an EXTRACTED field whose span was located only by the corrupted-source tolerant
#: tier. One wording, used by both the protocol view and the field table, so the two surfaces
#: cannot disagree about the same field.
_REPAIRED_SPAN_NOTE = "[quote matched after source-text repair]"


def _repair_note(row: FieldRow) -> str:
    """The repaired-span note, naming tier 6's substitutions when the span carries them (2026-10-28,
    the author's item 1): ``quote matched after source-text repair: \u00d7→/C2, \u00d7→/C2``."""
    note = _REPAIRED_SPAN_NOTE[1:-1]
    if row.span_repairs:
        note += ": " + ", ".join(row.span_repairs)
    return note


def _from_paper_tag(row: FieldRow) -> str:
    """``[from paper]``, widened when the span was recovered rather than cleanly matched."""
    if row.span_recovered:
        return f"[from paper — {_repair_note(row)}]"
    return "[from paper]"


def _truncate_quote(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) > _SPAN_QUOTE_MAX:
        return flat[: _SPAN_QUOTE_MAX - 1].rstrip() + "…"
    return flat


def _fmt_field_text(row: FieldRow) -> str:
    """The right-hand value/explanation per the five display states."""
    if row.state == EXTRACTED:
        tag = "" if not row.span_recovered else f"   [{_repair_note(row)}]"
        return f"from paper: {_fmt_row_value(row)}   «{_truncate_quote(row.span_text or '')}»{tag}"
    if row.state == INFERRED_DEFAULT:
        return f"inferred: {_fmt_row_value(row)}   ({row.basis_type}, conf {row.confidence})"
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
        return f" {_fmt_row_value(row)}"
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
    # The one new base from DELTA_base_pipeline_diagnostic.md §5: a base_pipeline name whose quote
    # GROUNDED but does not state the value. Every other reason's sentence is false of it — the span
    # resolved — so it cannot reuse one. not_covered because the tool could not verify what the paper
    # said, which is the same judgement cobidas._software_coverage expresses as covered=False.
    "base_pipeline_value_unsupported": "not_covered",
    # The two KB bases, given stable prefixes by ruling 6 so _gap_base can match them and the
    # reason scan can see them. kb_ambiguous is a tool gap; kb_not_applicable is NEITHER a gap nor
    # a paper claim — the KB says the step does not apply — so it must not land in not_reported.
    "kb_ambiguous": "not_covered",
    "kb_not_applicable": "not_covered",
    # The motion post-check (motion_guard.py, 2026-10-26). Both are judgements about the
    # extractor's evidence, not about the manuscript: the quote grounded; the value is either not
    # in it or names a structured-noise tool. not_covered, like base_pipeline_value_unsupported.
    "motion_value_unsupported_by_quote": "not_covered",
    "motion_value_routed_structured_noise": "not_covered",
    # The step-field quote-support check (quote_support.py, 2026-10-26): the quote grounded; no alias
    # of the value (or the number) is in it. A statement about the extractor's evidence.
    "value_unsupported_by_quote": "not_covered",
    # The coverage calls (2026-10-28, DESIGN_coverage_expansion.md B2/B3). A parameter of a step the
    # paper STATES was not performed is neither a gap about the paper nor a tool limitation: its own
    # bucket, emitted only when non-zero. A non-yes/no for a boolean is the same shape as a
    # non-number for a number field.
    "step_not_performed": "not_applicable",
    "value_not_boolean": "unmappable",
    "performed_cannot_defer": "not_covered",  # 2026-10-29: the post-check; unverifiable, not absent
    "operation_word_not_value": "not_covered",  # 2026-11-02: names the operation, not a convention
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
    # The reasons below describe what the EXTRACTOR did and assert nothing about what the
    # manuscript reports. REWORDED 2026-10-19: this comment used to enumerate "these three",
    # which read as a second classification list competing with cobidas._UNVERIFIABLE_GAP_BASES.
    # There is ONE classification source and it is that frozenset — see its membership criterion,
    # and DELTA_conditional_row_unverifiable.md ruling 1. This table decides WORDING only; it
    # decides nothing about coverage.
    "value_not_numeric": "extractor returned a non-numeric value for this field — enter manually",
    "extraction_quote_missing": (
        "extractor returned a value with no supporting quote — unverifiable, "
        "check the source yourself"
    ),
    "deferral_quote_unresolved": (
        "extractor reported a deferral to another source but could not locate the "
        "deferring sentence — check the source yourself"
    ),
    # Must NOT say "not reported in source": the source WAS quoted and the quote grounded. The
    # paper named something; the sentence the model cited does not state it. That is a statement
    # about the extractor's evidence, not about the manuscript.
    "base_pipeline_value_unsupported": (
        "a pipeline was named but the quoted sentence does not state it — check the source yourself"
    ),
    "kb_ambiguous": (
        "AESPA's knowledge base could not determine which version applies — check the source "
        "yourself"
    ),
    # RULED 2026-10-19. Says where it came from and that the paper did not report it, in the same
    # form as the inferred-version line below. Names no internal token: the raw producer message
    # carried "couple_stages forbids ..." and leaked it into author-facing output, because the
    # un-prefixed free text matched neither table and fell to "unspecified (reason: ...)".
    "kb_not_applicable": (
        "AESPA's knowledge base records that this step does not apply to the named pipeline; "
        "the paper did not report it"
    ),
    # Must NOT say "not reported in source": the quoted sentence is real paper text about motion
    # correction. The first says the value was taken from elsewhere than the sentence cited; the
    # second says the tool named belongs to COBIDAS D.3's artifact/structured-noise row (CALL 4).
    "motion_value_unsupported_by_quote": (
        "a motion-correction value was returned but the quoted sentence does not state it — "
        "check the source yourself"
    ),
    "motion_value_routed_structured_noise": (
        "the method named for motion correction is a structured-noise tool (COBIDAS D.3 artifact "
        "row), not a realignment tool — check the source yourself"
    ),
    # Must NOT say "not reported in source": the quoted sentence is real paper text about this step.
    "value_unsupported_by_quote": (
        "a value was returned but the quoted sentence does not state it or a known form of it — "
        "check the source yourself"
    ),
    # Must NOT read as a gap: the paper said the step was not done (R2, 2026-10-28).
    "step_not_performed": "not applicable — the paper states this step was not performed",
    "value_not_boolean": "extractor returned a non-yes/no value for this field — enter manually",
    "performed_cannot_defer": (
        "the extractor was given a citation instead of whether this step was performed — "
        "check the source yourself"
    ),
    "operation_word_not_value": (
        "the quoted sentence names the operation but no convention — check the source yourself"
    ),
}

#: Completeness-header gap buckets: (bucket key, display label), fixed order, non-zero only.
_BUCKET_HEADER: tuple[tuple[str, str], ...] = (
    ("not_reported", "not reported in source"),
    ("unmappable", "reported but unmappable to controlled vocabulary"),
    ("not_covered", "not covered by extractor"),
    ("not_applicable", "not applicable (step stated as not performed)"),
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
        line = f"{label}{sep}{_fmt_row_value(row)}   {_from_paper_tag(row)}"
        if row.span_text:
            line += f"  «{_truncate_quote(row.span_text)}»"
        return line
    if st == INFERRED_DEFAULT:
        return f"{label}{sep}{_fmt_row_value(row)}   [INFERRED — not stated in source]"
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


#: The inference clause of the motion method's line (DESIGN_motion_inference_arm.md §4; the
#: author's wording, 2026-10-28): the paper's words first, then what AESPA infers, with basis and
#: source -- never presented as reported. Identical for the arm proper (the inferred default on the
#: field) and for the described_only diagnostic (the record beside the stored result).
_MOTION_INFERS = "   — tool not stated; AESPA infers {program} ({basis_type}, {source})"


def _motion_method_line(row: FieldRow, label: str, record: Any | None) -> str:
    """The ``motion_correction.method`` protocol line, with the inference clause when the arm is
    filled (state INFERRED) or a described_only diagnostic record travels with the result."""
    if row.state == INFERRED_DEFAULT:
        if row.extraction_status == DEFERRED_TO_CITATION:
            refs = ", ".join(row.deferral_refs or []) or "(unspecified)"
            words = f"deferred to {refs}"
        else:
            words = "not stated"
        source = (
            (
                getattr(record, "source", None)
                if record is not None and getattr(record, "path", None) == "arm"
                else None
            )
            or getattr(row.basis, "note", None)
            or "(source not recorded)"
        )
        return f"{label} = {words}" + _MOTION_INFERS.format(
            program=(getattr(row.value, "verbatim", None) or _fmt_value(row.value)),
            basis_type=row.basis_type,
            source=source,
        )
    line = _protocol_main(row, label, equals_for_extracted=True)
    if (
        row.state == EXTRACTED
        and record is not None
        and getattr(record, "path", None) == "diagnostic"
        and getattr(record, "program", None)
    ):
        line += _MOTION_INFERS.format(
            program=record.program, basis_type=record.basis_type, source=record.source
        )
    return line


#: A field the paper defers to its pipeline and AESPA fills from the KB (fix 3, 2026-11-05): the
#: paper's words first, then the inference, as the motion line words it.
_DEFERRED_INFERS = "   — not stated in this paper; AESPA infers {value} ({basis_type}, {source})"


def _supplement_line(supplement: dict[str, Any]) -> str:
    """Fix 4 (2026-11-05): one line under the title on the paper's own supplement."""
    name = Path(str(supplement.get("path") or "")).name or "the supplement"
    if supplement.get("read"):
        sl = supplement.get("slice")
        if sl is None:  # a record written before supplements were sliced
            return (
                f"Supplement: {name}, read with the paper "
                f"({supplement.get('n_chars', 0)} characters)."
            )
        n_read, n_all = supplement.get("n_chars_read", 0), supplement.get("n_chars", 0)
        # the author's list of 2026-11-05, third round, item 1: which part of it was read
        if sl.get("found_via") == "header_match":
            return (
                f"Supplement: {name}, its MRI sections read with the paper (from "
                f"{sl.get('matched_header')!r} to {sl.get('ended_at')!r}, {n_read} of {n_all} "
                "characters)."
            )
        return (
            f"Supplement: {name}, read whole with the paper ({n_read} characters; "
            f"{sl.get('fallback_reason')})."
        )
    if supplement.get("present"):
        return f"Supplement: {name} found beside the paper, not read ({supplement.get('reason')})."
    return "Supplement: none found beside the paper; a field the paper sends there is not read."


def _supplement_words(supplement: dict[str, Any] | None) -> str:
    """A field the paper sends to its own supplement (fix 4): "see Supplementary Material" is not a
    citation, so it is never looked up in the reference list."""
    if supplement and supplement.get("read"):
        return "in this paper's supplement, read with the paper; no value was taken from it"
    return "in this paper's supplement, not read"


def _deferred_inferred_line(row: FieldRow, label: str) -> str:
    refs = ", ".join(row.deferral_refs or []) or "(unspecified)"
    return f"{label} = deferred to {refs}" + _DEFERRED_INFERS.format(
        value=_fmt_row_value(row),
        basis_type=row.basis_type,
        source=getattr(row.basis, "note", None) or "(source not recorded)",
    )


def _multiple_pipelines_line(answers: dict[str, Any] | None) -> str | None:
    """Item 5 (2026-10-28): one header line on the steps section when either coverage call
    answered that the text describes more than one preprocessing variant. ``answers`` is the
    stored shape -- ``{call: {"multiple_pipelines": <dumped field>, "pipeline_variant_count": <dumped
    field>}}`` -- so the batch and the re-render script render the same line."""
    if not answers:
        return None
    parts: list[str] = []
    for call in sorted(answers):
        fields = answers[call] or {}
        flag = (fields.get("multiple_pipelines") or {}).get("extraction") or {}
        if flag.get("status") != "EXTRACTED" or flag.get("value") is not True:
            continue
        count = (fields.get("pipeline_variant_count") or {}).get("extraction") or {}
        n = f"count {count['value']}" if count.get("status") == "EXTRACTED" else "count not stated"
        spans = flag.get("spans") or []
        quote = f"  «{_truncate_quote(spans[0]['text'])}»" if spans else ""
        who = "checking pass" if call == "V" else f"call {call}"
        parts.append(f"{who}: yes, {n}{quote}")
    if not parts:
        return None
    return "> ⚠ More than one preprocessing variant is described — " + "; ".join(parts)


def _verdict_for(row: FieldRow, verifier: dict[str, Any] | None) -> dict[str, Any] | None:
    if not verifier or verifier.get("status") != "ok":
        return None
    found: dict[str, Any] | None = verifier.get("fields", {}).get(row.path)
    return found


_UNCONFIRMED = "[inferred by the model, unconfirmed]"


def _resolution_lines(resolution: dict[str, Any]) -> list[str]:
    """2026-11-09 (the author's item 1): the resolution call beside the paper's own motion phrase.
    KB-confirmed answers carry the KB source; model-only answers say so; the paper's phrase above is
    untouched."""
    if resolution.get("status") != "ok":
        return [
            f"    resolution call: {resolution.get('status')} ({resolution.get('error') or ''})"
        ]
    pipe = resolution.get("resolved_pipeline") or {}
    tool = resolution.get("realignment_tool") or {}
    pv = pipe.get("value") or "none"
    pipe_words = f"{pv} (KB)" if pipe.get("kb") else (pv if pv == "none" else f"{pv} (free text)")
    conf = tool.get("kb_confirmation")
    if conf:
        how = "named in the paper" if conf.get("basis") == "package_named" else "pipeline default"
        tool_words = (
            f"{conf['package']} → {conf['program']}   [KB default, {how}: "
            f"{_truncate_quote(str(conf.get('source') or ''))}]"
        )
    elif tool.get("value"):
        tool_words = f"{tool['value']}   {_UNCONFIRMED}"
    else:
        tool_words = "unknown"
    out = [
        f"    resolved pipeline: {pipe_words}",
        f"    realignment tool: {tool_words}",
        f"    resolution basis: {resolution.get('basis') or ''}",
    ]
    for name, item in (resolution.get("sub_items") or {}).items():
        prov = item.get("provenance")
        if prov == "EXTRACTED":
            out.append(
                f"    {name} = {item.get('value')}   [stated]  «{_truncate_quote(item['quote'])}»"
            )
        elif prov == "INFERRED_MODEL":
            out.append(f"    {name} = {item.get('value')}   {_UNCONFIRMED}")
        else:
            out.append(f"    {name}: unknown")
    return out


def _checker_supplied_line(param: str, entry: dict[str, Any]) -> str:
    """2026-11-09 (the author's item 2): an unverifiable field the checking pass judged WRONG and gave a
    value for, from the extraction's own quote. The value is the checking pass's, said so on the line;
    the field's provenance arm is unchanged (still unverifiable in the D.3 coverage section)."""
    quote = f"  «{_truncate_quote(entry['quote'])}»" if entry.get("quote") else ""
    return f"- {param} = {entry['value']}   [checker-supplied]{quote}"


def _with_verdict(main: str, row: FieldRow, verifier: dict[str, Any] | None) -> str:
    """report v2 §3 (2026-10-29): the checking pass beside the field. ``wrong`` demotes the drafted
    value to a flag -- the value stays on the line, never replaced; ``missed`` names what the paper
    states; a verdict whose sentence did not resolve is shown as unverified and does nothing."""
    from extractor_mvp.verifier import effective

    v = _verdict_for(row, verifier)
    if row.state == INFERRED_DEFAULT and verifier and verifier.get("status") == "ok":
        # fix 1d (2026-11-05): an inference is AESPA's, not the paper's; it is never judged against
        # the text, and a verdict a record carries on it (one drawn before the fix) is not shown
        return f"- {main}   [AESPA's inference: not checked against the text]"
    if v is None:
        return f"- {main}"
    eff = effective(v)
    sentence = f" «{_truncate_quote(v['relied_on'])}»" if v.get("relied_on") else ""
    if eff == "supported":
        return f"- {main}   [check: supported]"
    if eff == "wrong":
        better = f"; should be: {v['better_value']}" if v.get("better_value") else ""
        return f"- ⚑ {main}   — checking pass: WRONG — {v.get('reason', '')}{better}{sentence}"
    if eff == "missed":
        return (
            f"- {main}   — checking pass: MISSED — the paper states: "
            f"{v.get('better_value') or '(see sentence)'}{sentence}"
        )
    return f"- {main}   [check: unverified verdict — its sentence did not resolve]"


def _unplaced_section(verifier: dict[str, Any] | None) -> list[str]:
    """The checking pass's ``unplaced`` list as its own section (2026-11-02, the author's item 2).
    It never changes a field. Emitted only when the record carries the list, so a record written
    before it renders byte-identically. A statement whose sentence does not resolve is shown,
    marked unverified."""
    if not verifier or verifier.get("status") != "ok" or "unplaced" not in verifier:
        return []
    from extractor_mvp.cobidas import COBIDAS_D3_ROWS

    aspect = {r.row_id: r.d3_aspect for r in COBIDAS_D3_ROWS}
    out = ["## Preprocessing statements no field captured (checking pass, unvalidated)"]
    items = verifier.get("unplaced") or []
    if not items:
        out.append("The checking pass lists none.")
    for u in items:
        row = u.get("row") or "no row"
        where = f"row: {aspect[row]}" if row in aspect else "no D.3 row"
        line = f"- {u.get('statement', '')} — {where}"
        if u.get("relied_on"):
            line += f"  «{_truncate_quote(' '.join(str(u['relied_on']).split()))}»"
        if u.get("relied_on_resolved") is not True:
            line += "  (its sentence was not found in the text — unverified)"
        out.append(line)
    out.append("")
    return out


def _hop_value(value: Any) -> str:
    """A second-hop value from its stored JSON dump."""
    if isinstance(value, dict):
        if value.get("verbatim") is not None or value.get("resolved") is not None:
            return str(value.get("verbatim") or value.get("resolved"))
        if "name" in value:
            return str(value["name"])
    if isinstance(value, list):
        return ", ".join(_hop_value(v) for v in value)
    if isinstance(value, float) and value.is_integer():
        return str(value)
    return str(value)


def _release_checked(r: dict[str, Any], key: str = "release") -> bool:
    """A quoted value the hop keeps: its quote found in the text and the value found in its quote."""
    return bool(r.get("quote_resolved") and r.get(f"{key}_in_quote"))


_HOP_TARGET_STATE = {
    "no_local_pdf": "no local PDF (PubMed Central is not built yet)",
    "local_pdf_ambiguous": "more than one local PDF matches",
    "fetch_failed": "the PDF could not be read",
}


def _second_hop_section(
    second_hop: list[dict[str, Any]] | None,
    data_release: dict[str, Any] | None = None,
    citing_software: list[dict[str, Any]] | None = None,
) -> list[str]:
    """The citation hop (DESIGN_citation_hop.md, ratified 2026-11-03): every value the hop read in a
    cited paper, shown "as described in <ref>, cited by this paper". Never counted toward this
    paper's COBIDAS compliance; nothing here reaches the coverage section below.

    2026-11-05 (the author's list, second round, item 4): the KB software scan's line (and the data
    release's) renders on every report that carries them, with or without a hop; a record with none
    of the three (every record before the full aespa-report) renders as before."""
    if not second_hop and data_release is None and citing_software is None:
        return []
    from extractor_mvp.citation_hop import release_relation
    from extractor_mvp.motion_guard import is_tool_shaped_frozen
    from extractor_mvp.verifier import effective

    out = (
        [
            "## As described in cited papers (second hop, one hop only; never counted toward this "
            "paper's COBIDAS compliance)"
        ]
        if second_hop
        else [
            "## Read in this paper beside the extraction (not counted toward its COBIDAS "
            "compliance; no field defers to a cited paper, so no hop ran)"
        ]
    )
    named = (data_release or {}).get("releases") or []
    own = [r for r in named if _release_checked(r)]
    if data_release is not None:
        if data_release.get("status") != "ok":
            said = "not read (the call failed)"
        elif not named:
            said = "none stated"
        else:
            said = (
                "; ".join(
                    f"{r['dataset']} {r['release']}  «{_truncate_quote(r['verbatim_quote'])}»"
                    for r in own
                )
                or "none kept"
            )
            if len(own) < len(named):
                said += f" ({len(named) - len(own)} named without its quote and value checked, not shown)"
        out.append(f"This paper's data release (read in this paper): {said}")
    if citing_software is not None:
        kept_own = [t for t in citing_software if t.get("kept")]
        rest = [t["display_name"] for t in citing_software if not t.get("kept")]
        out.append(
            "This paper's software by the KB scan (read in this paper; not counted, the Software "
            "row below is the extraction's): "
            + (
                "; ".join(
                    (
                        f"{t['display_name']} {t['version']}"
                        if t.get("version")
                        else t["display_name"]
                    )
                    + f"  (fMRI use: «{_truncate_quote(t.get('use_quote') or '')}»)"
                    for t in kept_own
                )
                or "no KB package named with an fMRI use"
            )
            + (f"; named, no quoted fMRI use: {', '.join(rest)}" if rest else "")
            + "."
        )
    for rec in second_hop or []:
        ref = rec.get("ref", "(unspecified)")
        out.append(f"### {ref}, cited by this paper")
        refstate = (rec.get("reference") or {}).get("state")
        if refstate != "resolved":
            words = {
                "reference_not_found": "no entry in this paper's reference list matches it",
                "reference_ambiguous": "more than one entry in this paper's reference list matches it",
                "no_reference_section": "this paper's reference list was not found",
            }.get(str(refstate), str(refstate))
            out.append(f"Not read: {words}.")
            out.append("")
            continue
        target = rec.get("target") or {}
        if target.get("state") != "local_pdf":
            out.append(
                "Not retrievable: "
                + _HOP_TARGET_STATE.get(str(target.get("state")), str(target))
                + "."
            )
            out.append("")
            continue
        if rec.get("status") != "ok":
            out.append(f"Not read: the hop's calls failed ({rec.get('error', 'no record')}).")
            out.append("")
            continue
        doi = {True: "DOI confirmed on the PDF", False: "DOI not found on the PDF", None: "no DOI"}[
            target.get("doi_confirmed")
        ]
        out.append(f"Read from a local PDF, {Path(str(target.get('path'))).name} ({doi}).")
        sec = rec.get("fmri_sections")
        if sec and sec.get("found_via") == "headings":
            out.append(
                "Fields read in its fMRI sections only: "
                + "; ".join(
                    f'"{x["heading"]}" and its subsections (characters {x["start"]} to {x["end"]})'
                    for x in sec.get("sections") or []
                )
                + ". The software list reads the whole paper."
            )
        elif sec:
            out.append(
                "No heading names fMRI; fields read in its whole methods section. The software "
                "list reads the whole paper."
            )
        rules = rec.get("rules") or {}
        verifier = rec.get("verifier") or {}
        verdicts = (verifier.get("fields") or {}) if verifier.get("status") == "ok" else {}
        for dotted, pf in (rec.get("fields") or {}).items():
            ext = pf.get("extraction") or {}
            check = effective(verdicts.get(dotted))
            tag = f"   [check: {check}]" if check else ""
            if ext.get("status") == "EXTRACTED":
                quote = (ext.get("spans") or [{}])[0].get("text") or ""
                out.append(
                    f"- {dotted} = {_hop_value(ext.get('value'))} — as described in {ref}"
                    f"  «{_truncate_quote(quote)}»{tag}"
                )
            elif ext.get("status") == "DEFERRED_TO_CITATION":
                refs = ", ".join(d.get("ref", "") for d in ext.get("deferrals") or [])
                out.append(f"- {dotted}: the cited paper defers further, to {refs} (not followed)")
            else:
                rule = rules.get(dotted)
                if rule:
                    src = ", ".join(rule.get("source_fields") or [])
                    out.append(
                        f"- {dotted}: {rule['value']} — by rule, from {src} as described in {ref} "
                        f"({rule.get('note')}){tag}"
                    )
                else:
                    out.append(f"- {dotted}: not reported in {ref}{tag}")
            for v in (rec.get("variants") or {}).get(dotted, []):
                note = "" if v.get("quote_resolved") else "  (its quote was not found — unverified)"
                out.append(
                    f"    - {v.get('applies_to')}: {v.get('value')}"
                    f"  «{_truncate_quote(v.get('verbatim_quote') or '')}»{note}"
                )
        tools = (rec.get("scope") or {}).get("tools") or []
        for t in tools:
            returned = (rec.get("tools") or {}).get(t["field"], [])
            found = [x for x in returned if _release_checked(x, "tool")]
            check = effective(verdicts.get(f"tool.{t['field']}"))
            tag = f"   [check: {check}]" if check else ""
            stated: list[str] = t.get("described_as") or []
            if stated and all(w.startswith("deferred to ") for w in stated):
                head = (
                    f"- {t['field']} tool (this paper: {stated[0]}"  # a deferral, case two's shape
                )
            else:
                head = (
                    f"- {t['field']} tool (this paper: "
                    + "; ".join(f'"{w}"' for w in stated)
                    + ", no tool named"
                )
            # the first hop's tool-shape test on the answer (the author, 2026-11-03): a phrase
            # that names no program is the cited paper describing the method, not a tool
            named = [x for x in found if is_tool_shaped_frozen(str(x["tool"]))]
            if named:
                out.append(
                    f"{head}) = "
                    + "; ".join(x["tool"] for x in named)
                    + f" — as described in {ref}  «{_truncate_quote(named[0]['verbatim_quote'])}»{tag}"
                )
            elif found:
                out.append(
                    f"{head}): the cited paper describes the method without naming a tool: "
                    f"{found[0]['tool']}  «{_truncate_quote(found[0]['verbatim_quote'])}»{tag}"
                )
            elif returned:
                x = returned[0]
                why = (
                    "its quote was not found"
                    if not x.get("quote_resolved")
                    else "it is not in its quote"
                )
                out.append(
                    f"{head}) = {x['tool']}  «{_truncate_quote(x['verbatim_quote'])}»"
                    f"  ({why} — unverified){tag}"
                )
            else:
                out.append(f"{head}): no tool named in {ref}{tag}")
        described = [r for r in rec.get("releases_described") or [] if _release_checked(r)]
        if described:
            out.append(
                f"- Data releases whose processing {ref} describes: "
                + "; ".join(
                    f"{r['dataset']} {r['release']}  «{_truncate_quote(r['verbatim_quote'])}»"
                    for r in described
                )
            )
        for r in own:
            relation = release_relation(r, described)
            if relation == "postdates":
                out.append(
                    f"  Note: this paper's data come from {r['dataset']} {r['release']}, a later "
                    f"release than those {ref} describes; the pipeline described there may differ "
                    "from the one applied to this paper's data."
                )
            elif relation == "undetermined":
                out.append(
                    f"  Whether {r['dataset']} {r['release']} postdates what {ref} describes is not "
                    "determined from the two texts."
                )
        # the software list (the author, 2026-11-03): a deterministic KB scan of the whole cited
        # paper, one scoped question per mention; a tool is listed when a mention's quoted use is
        # fMRI processing or feeds it (software_scan.py)
        scanned = (rec.get("software_scan") or {}).get("tools") or []
        kept = [t for t in scanned if t.get("kept")]
        unverified = [t for t in scanned if t.get("unverified")]
        dropped = [
            t["display_name"] for t in scanned if not t.get("kept") and not t.get("unverified")
        ]
        if kept:
            out.append(
                f"- Software as described in {ref} (KB scan of the whole paper; not counted toward "
                "this paper's Software row): "
                + "; ".join(
                    (
                        f"{t['display_name']} {t['version']}"
                        if t.get("version")
                        else f"{t['display_name']} (no version)"
                    )
                    + f"  (fMRI use: «{_truncate_quote(t.get('use_quote') or '')}»)"
                    for t in kept
                )
            )
        for t in unverified:  # answered "unclear": shown with its quote, never dropped (2026-11-03)
            ver = f" {t['version']}" if t.get("version") else " (no version)"
            note = "" if t.get("unclear_quote_resolved") else ", its quote not found"
            out.append(
                f"  {t['display_name']}{ver}: its fMRI use is unverified{note}  "
                f"«{_truncate_quote(t.get('unclear_quote') or '')}»"
            )
        if dropped:
            out.append(f"  Named, no quoted fMRI use: {', '.join(dropped)}")
        if rec.get("software_scan") is not None:
            out.append(
                "  The scan finds only packages in the KB (kb/tools); a package it does not list is "
                "not looked for."
            )
        outside = (rec.get("scope") or {}).get("rows_outside_calls") or []
        if outside:
            out.append(f"Not asked (outside calls T and S): {', '.join(outside)}.")
    out.append("")
    return out


def _verifier_summary_line(verifier: dict[str, Any] | None, rows: list[FieldRow]) -> str | None:
    """One header line: the checking pass's counts, marked unvalidated; or that it was unavailable."""
    if verifier is None:
        return None
    if verifier.get("status") != "ok":
        return (
            "Checking pass: unavailable — no field was checked "
            f"({verifier.get('error') or 'no record'})."
        )
    from extractor_mvp.verifier import effective

    counts = {"supported": 0, "wrong": 0, "missed": 0, "unverified": 0}
    # fix 1d (2026-11-05): a field AESPA filled by inference is not judged; its verdict, if the
    # record carries one, is not counted, and the field is counted apart
    inferred = {r.path for r in rows if r.state == INFERRED_DEFAULT}
    for path, v in verifier.get("fields", {}).items():
        if path in inferred:
            continue
        eff = effective(v)
        counts[eff if eff in counts else "unverified"] += 1
    n_lines = int(verifier.get("n_draft_lines") or 0)
    # 2026-11-02, the author's ruling: a dropped same-order verdict was checked, not "not checked"
    dropped = 1 if verifier.get("dropped_same_order") else 0
    n_inferred = len(inferred)
    not_checked = max(0, n_lines - sum(counts.values()) - dropped - n_inferred)
    return (
        "Checking pass (unvalidated — spot-checked against a human reading before it is trusted): "
        f"supported {counts['supported']} · wrong {counts['wrong']} · missed {counts['missed']} · "
        f"unverified {counts['unverified']} · not checked {not_checked}"
        + (f" · AESPA's inferences, not judged {n_inferred}" if n_inferred else "")
        + (" · order verdict dropped (its proposal is the current order)" if dropped else "")
    )


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
    motion_inference: Any | None = None,
    multiple_pipelines: dict[str, Any] | None = None,
    verifier: dict[str, Any] | None = None,
    second_hop: list[dict[str, Any]] | None = None,
    data_release: dict[str, Any] | None = None,
    citing_software: list[dict[str, Any]] | None = None,
    supplement: dict[str, Any] | None = None,
    checker_supplied: list[dict[str, Any]] | None = None,
    resolution: dict[str, Any] | None = None,
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
    from extractor_mvp.verifier import drop_same_order_verdict

    verifier = drop_same_order_verdict(verifier, preprocessing)
    rows = flatten(preprocessing)
    supplied = {c["field"]: c for c in checker_supplied or []}
    lines: list[str] = []
    lines.append(f"# Replication Protocol — {source}" if source else "# Replication Protocol")
    lines.append("")

    if methods_slice is not None and methods_slice.suspicious:
        reason = getattr(methods_slice, "fallback_reason", None)
        if methods_slice.found_via == "fallback_full_text" and reason:
            # fix 1a (2026-11-05): a header matched but its slice was rejected, or the text layer
            # cannot show a heading; the reason is said, and the checking pass read the full text
            lines.append(
                f"> ⚠ Methods section not identified — {reason}. Extracted from the FULL "
                "document, and the checking pass read the full document; spans may resolve "
                "against Introduction / Discussion / References."
            )
        elif methods_slice.found_via == "fallback_full_text":
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

    # fix 4 (2026-11-05): whether the paper's own supplement was read with it, and why not
    if supplement is not None:
        lines.append(_supplement_line(supplement))
        lines.append("")
    supp_fields = frozenset((supplement or {}).get("fields_deferred") or [])

    # --- Base pipeline (header line + optional version sub-line) ---
    base_rows = [r for r in rows if r.group == "base_pipeline"]
    base_main = next((r for r in base_rows if r.path == "base_pipeline"), None)
    version_row = next((r for r in base_rows if r.path == "base_pipeline.version"), None)
    if (
        base_main is not None
        and "base_pipeline" in supp_fields
        and base_main.state == DEFERRED_TO_CITATION
    ):
        lines.append(f"Base pipeline: {_supplement_words(supplement)}")
    elif base_main is not None:
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
    check_line = _verifier_summary_line(verifier, rows)
    if check_line:
        lines.append(check_line)
    lines.append("")

    # --- Steps in pipeline (list) order ---
    # report v2 §1d (2026-10-29): say where the order came from. A record written before 0.6.0
    # carries no source and keeps the old header, byte for byte.
    order_source = getattr(preprocessing, "step_order_source", None)
    if order_source is None:
        lines.append("## Preprocessing steps (pipeline order)")
    elif order_source == "paper":
        lines.append("## Preprocessing steps (order as stated in the paper)")
    elif order_source == "partial":
        lines.append(
            "## Preprocessing steps (the paper's order for the steps it orders; the rest follow in "
            "template order, which the paper does not state)"
        )
    else:
        lines.append(
            "## Preprocessing steps (template order — the paper does not state an order; a reader "
            "must not assume one)"
        )
    if order_source in ("paper", "partial") and preprocessing.step_order_spans:
        quotes = "  ".join(f"«{_truncate_quote(sp.text)}»" for sp in preprocessing.step_order_spans)
        lines.append(f"Order stated in: {quotes}")
    lines.append("")
    variants = _multiple_pipelines_line(multiple_pipelines)
    if variants:
        lines.append(variants)
        lines.append("")
    for n, step in enumerate(preprocessing.steps, start=1):
        cobidas_row = getattr(type(step), "cobidas_row", None)
        lines.append(f"### {n}. {step.kind}   (COBIDAS: {cobidas_row})")
        for r in (row for row in rows if row.group == step.kind):
            param = r.path.split(".", 1)[1] if "." in r.path else r.path
            if r.path == "motion_correction.method":
                main = _motion_method_line(r, param, motion_inference)
            elif r.state == INFERRED_DEFAULT and r.extraction_status == DEFERRED_TO_CITATION:
                main = _deferred_inferred_line(r, param)
            elif r.path in supp_fields and r.state == DEFERRED_TO_CITATION:
                main = f"{param}: {_supplement_words(supplement)}"
            else:
                main = _protocol_main(r, param, equals_for_extracted=True)
            if r.path in supplied:
                lines.append(_checker_supplied_line(param, supplied[r.path]))
            else:
                lines.append(_with_verdict(main, r, verifier))
            if r.path == "motion_correction.method" and resolution is not None:
                lines.extend(_resolution_lines(resolution))
            lines.extend(f"    {note}" for note in _protocol_note_lines(r))
        lines.append("")

    # 2026-11-02, the author's item 2: what the checking pass found that no field captured.
    lines.extend(_unplaced_section(verifier))
    lines.extend(_second_hop_section(second_hop, data_release, citing_software))

    # --- COBIDAS D.3 coverage (grounds the gap figure in the standard) ---
    lines.append(
        to_cobidas_coverage(preprocessing, verifier=verifier, supplement=supplement).rstrip()
    )

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# The report surface
# ---------------------------------------------------------------------------


def to_report(
    preprocessing: Preprocessing,
    source: str | None = None,
    *,
    methods_slice: MethodsSlice | None = None,
    motion_inference: Any | None = None,
    multiple_pipelines: dict[str, Any] | None = None,
    verifier: dict[str, Any] | None = None,
    second_hop: list[dict[str, Any]] | None = None,
    data_release: dict[str, Any] | None = None,
    citing_software: list[dict[str, Any]] | None = None,
    supplement: dict[str, Any] | None = None,
    checker_supplied: list[dict[str, Any]] | None = None,
    resolution: dict[str, Any] | None = None,
) -> str:
    """THE supported report surface — the only output safe to present as "the report".

    Delegates to :func:`to_protocol`, which appends :func:`to_cobidas_coverage` so every
    COBIDAS D.3 row is accounted for, including rows the extractor never examined. The
    partial views (:func:`to_field_table`, :func:`to_field_bullets`) walk ``flatten()``
    rows only and silently omit such rows; they are not reports.
    """
    return to_protocol(
        preprocessing,
        source,
        methods_slice=methods_slice,
        motion_inference=motion_inference,
        multiple_pipelines=multiple_pipelines,
        verifier=verifier,
        second_hop=second_hop,
        data_release=data_release,
        citing_software=citing_software,
        supplement=supplement,
        checker_supplied=checker_supplied,
        resolution=resolution,
    )


#: Surfaces a caller may present as "the report". The guard test parametrizes over this
#: tuple: a surface listed here without a coverage section fails, and a surface NOT listed
#: here is not a sanctioned report. :func:`to_protocol` is listed in its own right, not
#: merely reached through :func:`to_report` — it is documented as a report and holds every
#: current caller, so covering it only while delegation happens to hold would leave the
#: guard resting on an implementation detail.
REPORT_SURFACES: tuple[Callable[..., str], ...] = (to_report, to_protocol)


def to_cobidas_coverage(
    preprocessing: Preprocessing,
    verifier: dict[str, Any] | None = None,
    supplement: dict[str, Any] | None = None,
) -> str:
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
    version_status = version_row.extraction_status if version_row else None
    # F1d (2026-10-29): software the checking pass says was not used for preprocessing
    excluded = frozenset(
        " ".join(name.lower().split())
        for name, use in ((verifier or {}).get("software") or {}).items()
        if use is False
    )
    # software_mentions passed only when the record carries them (0.6.0), so a record written
    # before then takes exactly the call it always took
    coverage = (
        assess_coverage(rows, version_status, preprocessing.software_mentions, excluded)
        if preprocessing.software_mentions is not None
        else assess_coverage(rows, version_status)
    )
    mentions, _n_unverified = software_mentions_for_row(
        rows, preprocessing.software_mentions, excluded
    )
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
    # Two different facts, kept apart (DELTA_base_pipeline_diagnostic.md §4a). "Never targeted" is a
    # code property — the extractor assesses fields on only a few rows. "Targeted but unverifiable"
    # is a per-paper outcome — it looked and could not verify what it found. Collapsing them under a
    # header describing only the first is the defect this project is about.
    mand_unverifiable = [rc for rc in mand_not_assessed if rc.unverifiable]
    mand_untargeted = [rc for rc in mand_not_assessed if not rc.unverifiable]
    non_mandatory = [rc for rc in coverage if not rc.row.mandatory]
    non_mand_addressed = [rc for rc in non_mandatory if rc.addressed]
    divergence_present = [s.kind for s in preprocessing.steps if s.kind in DIVERGENCE_KINDS]

    # 2026-11-02 (the author's queued fix): a PARTIALLY reported Software row is not counted under
    # "not reported", so the violation label must not sit there; it goes on the partial segment.
    violation = (
        " (incl. Software — unconditional violation)"
        if any(rc.row.row_id == "software" and not rc.partial for rc in mand_not_reported)
        else ""
    )
    # The expanded coverage (2026-10-28, DESIGN_coverage_expansion.md B5, the author's ruling R5):
    # only a record that carries an expanded step (``performed`` present on some kind) gets the
    # performed=no segment and the per-row section below, so every record written before schema
    # 0.5.2 renders byte-identically -- the same trade the unverifiable breakdown made.
    expanded = is_expanded(preprocessing)
    states = {rc.row.row_id: row_state(rc, rows) for rc in coverage} if expanded else {}
    lines.append(f"Mandatory rows: {len(mandatory)}")
    if expanded:
        # fix 1c (2026-11-05): a row the checking pass flags counts as "flagged", never as addressed
        # (nor partially reported, performed=no or not reported), by the rule the per-row section
        # uses. The segment appears only when a row is flagged, so other reports keep their bytes.
        flagged = {
            rc.row.row_id for rc in mand_assessed if _row_flagged(mapped_rows(rc, rows), verifier)
        }
        n_flagged = len(flagged)
        n_flag_addressed = sum(1 for rc in mand_addressed if rc.row.row_id in flagged)
        n_perf_no = sum(
            1
            for rc in mand_assessed
            if states[rc.row.row_id] == "performed_no" and rc.row.row_id not in flagged
        )
        n_partial = sum(1 for rc in mand_assessed if rc.partial and rc.row.row_id not in flagged)
        n_flag_not_reported = sum(1 for rc in mand_not_reported if rc.row.row_id in flagged)
        software_partial = any(
            rc.row.row_id == "software" and rc.partial and rc.row.row_id not in flagged
            for rc in mand_assessed
        )
        partial_seg = (
            f"partially reported {n_partial}"
            + (
                " (incl. Software — unconditional violation for the software without an exact version)"
                if software_partial
                else ""
            )
            + " · "
            if n_partial
            else ""
        )
        flagged_seg = f"flagged {n_flagged} · " if n_flagged else ""
        if "software" in flagged:
            violation = ""  # the software values are flagged: no violation is claimed on them
        lines.append(
            f"  Assessed by AESPA: {len(mand_assessed)}  →  "
            f"addressed {len(mand_addressed) - n_perf_no - n_flag_addressed} · {flagged_seg}"
            f"{partial_seg}performed=no {n_perf_no} · "
            f"not reported {len(mand_not_reported) - n_partial - n_flag_not_reported}{violation}"
        )
    else:
        lines.append(
            f"  Assessed by AESPA: {len(mand_assessed)}  →  "
            f"addressed {len(mand_addressed)} · not reported {len(mand_not_reported)}{violation}"
        )
    # The breakdown is emitted ONLY when the second fact is present, the way _BUCKET_HEADER emits
    # non-zero segments only. A report with nothing unverifiable is byte-identical to before this
    # change, which is what the re-render identity gate checks.
    #
    # RECORDED TRADE, not an oversight: that byte-identity means a report with ZERO unverifiable
    # fields is indistinguishable from a report produced before this feature existed. Nothing on the
    # page says the distinction was even available. Accepted because the gate's attributability is
    # worth more than self-description while the stored demo reports are regenerated anyway (they are
    # already 16/19 stale — TRACK_A_SCOPE's standing condition). If those reports ever become a
    # durable artifact rather than a regenerable one, revisit this: the honest alternative is to emit
    # the breakdown always and accept that all 19 move once, deliberately, in one attributable diff.
    if mand_unverifiable:
        lines.append(
            f"  Not assessed by AESPA: {len(mand_not_assessed)}  →  "
            f"never targeted {len(mand_untargeted)} · "
            f"targeted but unverifiable {len(mand_unverifiable)}"
        )
    else:
        lines.append(f"  Not assessed by AESPA: {len(mand_not_assessed)}")
    lines.append(
        f"Non-mandatory rows: {len(non_mandatory)} ({len(non_mand_addressed)} addressed)  ·  "
        f"Beyond COBIDAS: {len(divergence_present)} steps"
    )
    # Both clauses of the original go FALSE once a row can be targeted-but-unverifiable: "targets
    # fields on only a few rows" is not why Software is unassessed, and an unverifiable Software row
    # means the paper has no citable claim at all. Variant, not a rewrite, so the common case stays
    # byte-identical.
    software_unverifiable = any(rc.row.row_id == "software" for rc in mand_unverifiable)
    if mand_unverifiable:
        claim = (
            "The Software row is unverifiable here, so this paper carries no unconditional, "
            "citable COBIDAS claim."
            if software_unverifiable
            else "The one unconditional, citable COBIDAS claim here is the Software row."
        )
        lines.append(
            "  (Two different tool gaps, kept apart: 'never targeted' means the extractor "
            "assesses fields on only a few rows; 'targeted but unverifiable' means it looked "
            "and could not verify what it found. Neither is a statement about the paper. "
            f"Silence on the rest is not measurable from text. {claim})"
        )
    else:
        lines.append(
            "  (The 'not assessed' count is a TOOL gap — the extractor targets fields on only a "
            "few rows — not a statement about the paper. Silence on the rest is not measurable "
            "from text. The one unconditional, citable COBIDAS claim here is the Software row.)"
        )
    lines.append("")

    if expanded:
        lines.extend(
            _expanded_rows_section(
                mandatory, states, rows, mentions, verifier, excluded, supplement=supplement
            )
        )

    def _tag(rc: RowCoverage) -> str:
        # Distinct wording from the field-level "not assessed by current extractor" callout:
        # this is the ROW-level statement. THREE states, not two (ruled 2026-10-19,
        # DELTA_conditional_row_unverifiable.md ruling 3): a row the extractor could not verify is
        # not the same as one it never targeted, and the never-targeted tag is FALSE of it — it
        # says "no field on any mapping kind is targeted" when a field was targeted and failed.
        if rc.unverifiable:
            return "  (examined; the extractor could not verify what it found)"
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
        if mentions:
            # report v2 §1c: the row is read over every named software; name the ones without a
            # version, and the ones with one, so the action is concrete.
            # 2026-11-02 (the author's queued fix): a name carrying only a fused major version
            # (SPM5) is named as such, not as "without a version" -- it still fails §4.3.
            # 2026-11-02, the author's ruling: a deferred pipeline is named as deferred with no
            # version in this paper; a version short of an exact release is named as such.
            deferred = [m for m in mentions if m.deferred_to]
            lacking = [
                m.name for m in mentions if not m.version and not m.major_only and not m.deferred_to
            ]
            major = [m.name for m in mentions if m.major_only]
            inexact = [_with_version(m.name, m.version) for m in mentions if m.inexact]
            having = [_with_version(m.name, m.version) for m in mentions if m.exact]
            parts = [_deferred_mention(m) + "." for m in deferred]
            if lacking:
                parts.append("Software named without a version: " + ", ".join(lacking) + ".")
            if major:
                parts.append(
                    "Named with a major version only (COBIDAS §4.3 asks for more than the major "
                    "version): " + ", ".join(major) + "."
                )
            if inexact:
                parts.append(
                    "Named with a version short of an exact release: " + ", ".join(inexact) + "."
                )
            if having:
                parts.append("Named with a version: " + ", ".join(having) + ".")
            detail = " ".join(parts)
        elif deferred_refs:
            # 2026-11-02, the author's ruling: the one deferral wording on every surface. The refs
            # are followed by ";", so a ref ending in a period ("Glasser et al.") keeps it.
            joined = ", ".join(deferred_refs)
            detail = f"Base pipeline deferred to {joined}; version not reported in this paper."
        else:
            name = _base_pipeline_name(preprocessing)
            if name is None:
                # The action is to NAME the software. Telling an author who named nothing
                # that their version is missing is the wrong instruction (DELTA §8).
                detail = (
                    "No software named in the source. Name the software, and give its "
                    "version and revision number."
                )
            elif version_row is not None and version_row.inference_status == "INFERRED_DEFAULT":
                # A disclosure, not guidance: without it a reader takes an AESPA-inferred
                # version for one the paper reported.
                detail = (
                    f"Pipeline named: {name}. Give its version and revision number; AESPA "
                    "inferred one, the paper did not report it."
                )
            else:
                detail = f"Pipeline named: {name}. Give its version and revision number."
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


#: The row-state labels of the expanded coverage section (cobidas.ROW_STATES, in words).
_ROW_STATE_LABEL: dict[str, str] = {
    "flagged": "flagged by the checking pass",
    "reported": "reported",
    "partially_reported": "partially reported",
    "performed_no": "performed: no",
    "deferred": "deferred",
    "unverifiable": "examined; the extractor could not verify what it found",
    "not_reported": "not reported",
    "not_assessed": "not assessed",
}


def _row_flagged(mapped: list[FieldRow], verifier: dict[str, Any] | None) -> bool:
    """report v2 §3 / F3b (2026-10-29): a row whose every addressing field (EXTRACTED or DEFERRED)
    the checking pass marks wrong, with a resolved sentence, is flagged. One rule for the per-row
    section and, since fix 1c (2026-11-05), the header."""
    from extractor_mvp.verifier import effective

    # fix 3 (2026-11-05): a deferred field AESPA filled from the KB still addresses its row by the
    # paper's deferral, and its verdict is not judged (fix 1d), so it never makes a row flagged
    addressing = [r for r in mapped if r.extraction_status in (EXTRACTED, DEFERRED_TO_CITATION)]
    return bool(addressing) and all(
        r.state != INFERRED_DEFAULT and effective(_verdict_for(r, verifier)) == "wrong"
        for r in addressing
    )


def _expanded_rows_section(
    mandatory: list[RowCoverage],
    states: dict[str, str],
    rows: list[FieldRow],
    mentions: list[Any] | None = None,
    verifier: dict[str, Any] | None = None,
    excluded: frozenset[str] = frozenset(),
    supplement: dict[str, Any] | None = None,
) -> list[str]:
    """One line per mandatory row, D.3 order (R5): the aspect, the validation tag, the row state,
    the row's reported values (EXTRACTED and DEFERRED fields only) and the first extracted field's
    quote, truncated as the step lines truncate theirs."""
    out: list[str] = ["### Rows (every mandatory row; the tag says whether labels exist for it)"]
    supp_fields = frozenset((supplement or {}).get("fields_deferred") or [])
    for rc in mandatory:
        state = states[rc.row.row_id]
        mapped = mapped_rows(rc, rows)
        values: list[str] = []
        quote: str | None = None
        # Item 6 (2026-10-28): a row mapped to more than one kind names the kind on each field
        # ("ica_denoise.performed = True; compcor.variant = a"); a one-kind row stays bare.
        prefixed = len(rc.row.spec_kinds) > 1
        for r in mapped:
            param = r.path.split(".", 1)[1] if "." in r.path else r.path
            if prefixed:
                param = f"{r.group}.{param}"
            if r.state == EXTRACTED:
                values.append(f"{param} = {_fmt_row_value(r)}")
                if quote is None and r.span_text:
                    quote = r.span_text
            elif r.extraction_status == DEFERRED_TO_CITATION and r.path in supp_fields:
                values.append(f"{param}: {_supplement_words(supplement)}")  # fix 4 (2026-11-05)
            elif r.extraction_status == DEFERRED_TO_CITATION:
                # fix 3 (2026-11-05): a deferral AESPA filled from the KB is still the paper's deferral
                refs = ", ".join(r.deferral_refs or []) or "(unspecified)"
                values.append(f"{param}: deferred to {refs}")
        if rc.row.row_id == "software" and mentions:
            # report v2 §1c: every named software, with its version or the lack of one.
            values = [
                _deferred_mention(m)
                if m.deferred_to
                else (
                    f"{_with_version(m.name, m.version)} (not an exact release)"
                    if m.inexact
                    else _with_version(m.name, m.version)
                    if m.version
                    else f"{m.name} (major version only)"
                    if m.major_only
                    else f"{m.name} (no version)"
                )
                + (f" — {m.used_for}" if m.used_for else "")
                for m in mentions
            ]
        # report v2 §3 / F3b (2026-10-29): a row whose every addressing field the checking pass marks
        # wrong reads "flagged"; a missed field is named.
        from extractor_mvp.verifier import effective

        verdicts = {r.path: effective(_verdict_for(r, verifier)) for r in mapped}
        if _row_flagged(mapped, verifier):
            state = "flagged"
        missed = [
            # [-1]: the Software row maps base_pipeline, a path with no dot (Silchenko_2023's checking
            # pass marked it missed in stress_v2 and the render raised IndexError, 2026-11-05)
            r.path.split(".", 1)[-1]
            for r in mapped
            if verdicts.get(r.path) == "missed" and r.state != INFERRED_DEFAULT
        ]
        line = f"- {rc.row.d3_aspect} [{validation_tag(rc.row.row_id)}] — {_ROW_STATE_LABEL[state]}"
        if values:
            line += ": " + "; ".join(values)
        if quote:
            line += f"  «{_truncate_quote(quote)}»"
        if rc.row.row_id == "software" and excluded:
            line += f"  (not counted, not preprocessing per the checking pass: {', '.join(sorted(excluded))})"
        if missed:
            line += f"  [missed per the checking pass: {', '.join(missed)}]"
        out.append(line)
    # report v2 §1a (2026-10-29): temporal filtering, beyond COBIDAS -- shown, never counted.
    tf_rows = [r for r in rows if r.group == "temporal_filtering"]
    if any(r.path == "temporal_filtering.performed" for r in tf_rows):
        state = kind_state(tf_rows)
        values = []
        quote = None
        for r in tf_rows:
            param = r.path.split(".", 1)[1]
            if r.state == EXTRACTED:
                values.append(f"{param} = {_fmt_row_value(r)}")
                quote = quote or r.span_text
            elif r.state == DEFERRED_TO_CITATION:
                values.append(
                    f"{param}: deferred to {', '.join(r.deferral_refs or []) or '(unspecified)'}"
                )
        tag = validation_tag("temporal_filtering")
        line = f"- Temporal filtering [beyond COBIDAS; {tag}] — {_ROW_STATE_LABEL[state]}"
        if values:
            line += ": " + "; ".join(values)
        if quote:
            line += f"  «{_truncate_quote(quote)}»"
        out.append(line)
    out.append("")
    return out


def _with_version(name: str, version: str | None) -> str:
    """The name and its version, the version once (fix 5, 2026-11-05): a name that already ends with
    the version ("Statistical Parametric Mapping (SPM) 12", "SPM12" with version "12") is not given
    it again. A longer number ending in the same digits ("1.12" for "12") is not the version."""
    if not version:
        return name
    stripped = name.rstrip()
    if stripped.endswith(version):
        before = stripped[: -len(version)][-1:]
        if not (before.isdigit() or before == "."):
            return stripped
    return f"{name} {version}"


def _deferred_mention(m: Any) -> str:
    """A deferred base pipeline on the Software row (2026-11-02, the author's ruling)."""
    return f"{m.name} deferred to {', '.join(m.deferred_to)}; version not reported in this paper"


def _fmt_row_value(row: Any) -> str:
    """A row's value: a band field (``*_band_hz``) in the one band format, everything else as
    :func:`_fmt_value`. 2026-11-02, the author's queued fix: the step section and the rows section
    showed the same band two ways ("0.02, 0.1" and "0.02-0.1 Hz" with an en dash); every
    surface now goes here."""
    if str(getattr(row, "path", "")).endswith("_band_hz"):
        return _fmt_band(row.value)
    return _fmt_value(row.value)


def _fmt_band(value: Any) -> str:
    """A band (low, high) in Hz; an open edge is shown as such."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return _fmt_value(value)
    low, high = value
    if low is None:
        return f"low-pass {high} Hz"
    if high is None:
        return f"high-pass {low} Hz"
    return f"{low}\u2013{high} Hz"


def _base_pipeline_name(preprocessing: Preprocessing) -> str | None:
    """The base pipeline's name if one is resolved (paper-named or inferred), else None."""
    base = preprocessing.base_pipeline
    if isinstance(base, NotApplicable):
        return None
    pref = _resolved_pipeline_ref(base)
    return pref.name if pref is not None else None
