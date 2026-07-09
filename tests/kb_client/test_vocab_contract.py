"""Controlled-vocabulary contract test: KB ⊆ spec.

Every controlled-vocab value the KB serves for a spec ``Literal``-typed field
must be a member of that ``Literal``. Lives in the agent repo because the
import direction is one-way agent → KB (same as ``KB_BASIS_LITERALS``).

Two layers, because the KB has two surfaces:

1. **Data-level** (the primary check). Walk every ``kb/pipelines/*.yaml``,
   pick out values served at field paths whose spec type is
   ``ProvenancedField[Literal[...]]`` or
   ``ProvenancedField[list[Literal[...]]]``, and assert each value is a
   member of the spec literal. Catches drift even when the KB schema does
   not constrain vocab.
2. **Schema-shape guard**. ``pipeline_registry.schema.json`` currently does
   NOT enumerate values for these fields (``param_default.value`` is a
   ``oneOf`` over scalar / array / sentinel — a free string at the schema
   level). The day someone adds an ``enum`` anywhere, the guard test below
   trips and we'll add a KB-schema-walk subset check too (KB ⊆ spec on
   both the data AND the schema, defense in depth). Today that walk is
   moot, so we don't pay for it.

The CONTRACTS map is built by introspecting the spec's step models — any
``ProvenancedField[Literal]`` field on any ``PreprocStep`` is covered
automatically, not just ``intensity_normalization.convention``.
"""

from __future__ import annotations

import json
import typing
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

import yaml
from fmri_defaults_kb.io import find_kb_root
from pydantic import BaseModel

from fmri_repro.spec.preprocessing import (
    BrainExtraction,
    CompCor,
    Coregistration,
    Despike,
    DistortionCorrection,
    ICADenoise,
    IntensityCorrection,
    IntensityNormalization,
    MotionCorrection,
    NonsteadystateRemoval,
    NuisanceRegression,
    PreprocStep,
    Scrub,
    Segmentation,
    SliceTimeCorrection,
    SpatialNormalization,
    SpatialSmoothing,
    SurfaceProjection,
    TemporalFiltering,
    TemporalStandardization,
)

# Hand-mirror of the PreprocStep discriminated union, kept explicit so the
# coverage surface is readable in one place. A new kind added to the union
# but forgotten here would have its Literal fields silently unchecked, so
# test_step_classes_match_preproc_step_union asserts equality with the
# union below — it is the one guard that keeps the contract complete.
_STEP_CLASSES: tuple[type[BaseModel], ...] = (
    NonsteadystateRemoval,
    SliceTimeCorrection,
    MotionCorrection,
    DistortionCorrection,
    BrainExtraction,
    Segmentation,
    Coregistration,
    IntensityCorrection,
    SpatialNormalization,
    SurfaceProjection,
    ICADenoise,
    CompCor,
    NuisanceRegression,
    Despike,
    Scrub,
    TemporalFiltering,
    IntensityNormalization,
    SpatialSmoothing,
    TemporalStandardization,
)


def _preproc_step_union_members() -> tuple[type, ...]:
    """Members of the ``PreprocStep = Annotated[A | B | ..., Field(...)]`` union."""
    annotated_args = typing.get_args(PreprocStep)
    union = annotated_args[0]
    return typing.get_args(union)


# --- introspection -----------------------------------------------------------


def _provenanced_payload(annotation: Any) -> Any | None:
    """If ``annotation`` is ``ProvenancedField[X]``, return ``X``; else ``None``.

    Uses Pydantic's generic metadata (``typing.get_args`` returns ``()`` on
    Pydantic v2 parameterized subclasses).
    """
    meta = getattr(annotation, "__pydantic_generic_metadata__", None)
    if not meta:
        return None
    args = meta.get("args")
    if not args:
        return None
    return args[0]


def _literal_members(payload: Any) -> tuple[str, tuple[Any, ...]] | None:
    """Classify the payload of a ProvenancedField.

    Returns ``("scalar", allowed)`` for ``Literal[...]``,
    ``("list", allowed)`` for ``list[Literal[...]]``, else ``None``.
    """
    if typing.get_origin(payload) is Literal:
        return ("scalar", typing.get_args(payload))
    if typing.get_origin(payload) is list:
        inner = typing.get_args(payload)
        if inner and typing.get_origin(inner[0]) is Literal:
            return ("list", typing.get_args(inner[0]))
    return None


def _build_contracts() -> dict[tuple[str, str], tuple[str, tuple[Any, ...]]]:
    """Introspect every step class; return ``{(step_kind, field): (container, allowed)}``
    for every ``ProvenancedField[Literal]`` / ``ProvenancedField[list[Literal]]``."""
    contracts: dict[tuple[str, str], tuple[str, tuple[Any, ...]]] = {}
    for step_cls in _STEP_CLASSES:
        kind_default = step_cls.model_fields["kind"].default
        for fname, finfo in step_cls.model_fields.items():
            if fname == "kind":
                continue
            payload = _provenanced_payload(finfo.annotation)
            if payload is None:
                continue
            entry = _literal_members(payload)
            if entry is not None:
                contracts[(kind_default, fname)] = entry
    return contracts


CONTRACTS = _build_contracts()


# --- KB yaml walk ------------------------------------------------------------


def _iter_kb_param_defaults() -> Iterator[tuple[Path, str, str, dict[str, Any]]]:
    """Yield ``(yaml_path, pipeline_id, version, param_defaults_dict)`` for
    every version record in every ``kb/pipelines/*.yaml``."""
    root = find_kb_root()
    pipelines = root / "pipelines"
    if not pipelines.is_dir():
        raise RuntimeError(f"KB pipelines dir not found at {pipelines}")
    for yaml_path in sorted(pipelines.glob("*.yaml")):
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        pid = doc.get("pipeline_id", yaml_path.stem)
        for vrec in doc.get("versions", []):
            yield (
                yaml_path,
                pid,
                str(vrec.get("version", "?")),
                vrec.get("param_defaults") or {},
            )


def _is_sentinel(value: Any) -> bool:
    """KB encodes 'not applicable' / 'needs verification' as object sentinels
    on ``param_default.value`` — these are not vocab strings and must be skipped."""
    return isinstance(value, dict) and value.get("kind") in {
        "not_applicable",
        "needs_verification",
    }


def _is_conditional(value: Any) -> bool:
    """A conditional_default: ``{conditional_on, rules: [{when, value, ...}]}``.
    Each rule's ``value`` is what the Configurator emits, so vocab membership is
    checked per-rule (the wrapper dict itself is never a vocab string)."""
    return isinstance(value, dict) and "conditional_on" in value


# --- tests -------------------------------------------------------------------


def test_kb_controlled_vocab_subset_of_spec() -> None:
    """Every controlled-vocab value in ``kb/pipelines/*.yaml`` is a member of
    the matching spec ``Literal``. Direction: KB ⊆ spec."""
    failures: list[str] = []
    seen = 0
    for yaml_path, pid, version, params in _iter_kb_param_defaults():
        for dotted_key, payload in params.items():
            kind, _, fname = dotted_key.partition(".")
            entry = CONTRACTS.get((kind, fname))
            if entry is None:
                continue
            container, allowed = entry
            value = payload.get("value") if isinstance(payload, dict) else None
            if value is None or _is_sentinel(value):
                continue
            if _is_conditional(value):
                # Validate the produced value of every rule; a "scalar" field yields one
                # value per rule, a "list" field a list per rule.
                for rule in value.get("rules", []):
                    rule_value = rule.get("value")
                    produced = (
                        rule_value
                        if container == "list" and isinstance(rule_value, list)
                        else [rule_value]
                    )
                    for v in produced:
                        seen += 1
                        if v not in allowed:
                            failures.append(
                                f"{yaml_path.name}:{pid}@{version}:{dotted_key} "
                                f"rule value {v!r} not in spec Literal {list(allowed)!r}"
                            )
                continue
            if container == "scalar":
                seen += 1
                if value not in allowed:
                    failures.append(
                        f"{yaml_path.name}:{pid}@{version}:{dotted_key} = "
                        f"{value!r} not in spec Literal {list(allowed)!r}"
                    )
            else:  # container == "list"
                if not isinstance(value, list):
                    failures.append(
                        f"{yaml_path.name}:{pid}@{version}:{dotted_key} "
                        f"expected list, got {type(value).__name__}"
                    )
                    continue
                for v in value:
                    seen += 1
                    if v not in allowed:
                        failures.append(
                            f"{yaml_path.name}:{pid}@{version}:{dotted_key} "
                            f"contains {v!r} not in spec Literal {list(allowed)!r}"
                        )
    assert not failures, "KB ⊄ spec:\n  " + "\n  ".join(failures)
    # Guard against the test silently passing because no KB yaml ever served a
    # controlled-vocab value at a path the spec recognises.
    if seen == 0:
        raise AssertionError(
            "No controlled-vocab KB values exercised. Either kb/pipelines/*.yaml "
            "is empty of Literal-typed defaults or CONTRACTS lost coverage."
        )


# Enum paths in pipeline_registry.schema.json that are KB-internal metadata
# with NO spec ``Literal`` counterpart — they cannot create a second source of
# truth for controlled vocab, so they are exempt from the tombstone below.
#   - version_kind: how to interpret the version id (tag/commit/paper_anchored);
#     additive, non-load-bearing, never mapped onto a spec field.
_NON_VOCAB_ENUM_PATHS: frozenset[str] = frozenset(
    {"$defs/version_record/properties/version_kind/enum"}
)


def test_kb_schema_does_not_enumerate_shared_vocab() -> None:
    """Tombstone for the schema-walk path.

    ``pipeline_registry.schema.json`` restricts no *controlled-vocab* field via
    ``enum`` — ``param_default.value`` is a free scalar/array/sentinel. If
    someone adds an ``enum`` at a value-bearing path, the KB starts carrying a
    second source of truth for vocab; this test fails so we'll add the
    ``_enum_at`` schema walk + ``kb_enum ⊆ spec_literal`` subset check at that
    time.

    KB-internal metadata enums with no spec ``Literal`` counterpart (see
    ``_NON_VOCAB_ENUM_PATHS``) are exempt: they constrain self-documentation
    fields like ``version_kind``, not preprocessing-parameter values, so the
    KB⊆spec contract is untouched.
    """
    schema_path = find_kb_root().parent / "schemas" / "pipeline_registry.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    enum_paths: list[str] = []

    def walk(node: Any, path: list[str]) -> None:
        if isinstance(node, dict):
            if "enum" in node:
                enum_paths.append("/".join(path) + "/enum")
            for k, v in node.items():
                walk(v, [*path, str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, [*path, str(i)])

    walk(schema, [])
    vocab_enum_paths = [p for p in enum_paths if p not in _NON_VOCAB_ENUM_PATHS]
    assert not vocab_enum_paths, (
        "KB pipeline_registry.schema.json now contains enum constraints at: "
        f"{vocab_enum_paths}. Add a KB-schema-walk subset check to "
        "test_kb_controlled_vocab_subset_of_spec — see this test's docstring. "
        "(If the new enum is KB-internal metadata with no spec Literal, add it "
        "to _NON_VOCAB_ENUM_PATHS instead.)"
    )


def test_step_classes_match_preproc_step_union() -> None:
    """``_STEP_CLASSES`` must equal the ``PreprocStep`` union's member set.

    A new step kind added to the union but forgotten in ``_STEP_CLASSES``
    would never enter ``CONTRACTS`` and its controlled-vocab fields would be
    silently unchecked. This guard closes that hole.
    """
    declared = set(_STEP_CLASSES)
    actual = set(_preproc_step_union_members())
    missing = actual - declared
    extra = declared - actual
    assert not missing and not extra, (
        "_STEP_CLASSES diverged from PreprocStep union. "
        f"missing from _STEP_CLASSES: {sorted(c.__name__ for c in missing)}; "
        f"extra in _STEP_CLASSES: {sorted(c.__name__ for c in extra)}."
    )


def test_contracts_cover_known_shared_fields() -> None:
    """Regression guard: spec-type drift could silently shrink CONTRACTS to {}.
    Pin the fields the KB *currently* serves so coverage can't vanish quietly."""
    expected = {
        ("intensity_normalization", "convention"),
        ("surface_projection", "surface_registration"),
        ("surface_projection", "target_surface"),
        ("spatial_normalization", "target_space"),
        ("temporal_standardization", "method"),
    }
    missing = expected - set(CONTRACTS.keys())
    assert not missing, f"CONTRACTS missing expected vocab fields: {missing}"
