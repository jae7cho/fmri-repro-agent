"""MVP output layer for a single :class:`~fmri_repro.spec.preprocessing.Preprocessing`.

One flattener, three thin formatters (COBIDAS reporting is per-pipeline, so the
unit here is exactly one ``Preprocessing``):

- :func:`flatten` — ``Preprocessing -> list[FieldRow]``. The single source of
  truth. Walks ``base_pipeline`` (incl. the nested ``PipelineRef.version``) then
  ``steps`` in list order (list position *is* pipeline order — never reordered).
- :func:`to_json` — ``preprocessing.model_dump_json(indent=2)`` (round-trippable).
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
from fmri_repro.spec.provenance import NotApplicable, ProvenancedField

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
    """Canonical JSON serialization (round-trips via ``model_validate_json``)."""
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
