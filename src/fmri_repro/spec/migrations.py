"""Forward migration of archived ``Preprocessing`` artifacts to the current schema.

Old data is read via :func:`parse_any_version` (migrate-then-parse), never by pinning an
old version module — those share the one mutating :mod:`fmri_repro.spec.preprocessing`
and cannot parse their own changed steps. The migrator is **read-only in memory**: it
returns a new dict and never rewrites the archived bytes, so the original file remains the
citable artifact.

Migration floor is 0.2.0. The 0.1.0 -> 0.2.0 hop is a SEMANTIC restructuring (the
``voxel_temporal_zscore`` move out of ``IntensityNormalizationConvention`` into the
``temporal_standardization`` step) that needs judgment we decline to automate for two
regenerable fixtures. A document still carrying the pre-0.2.0 marker is refused **loudly**
rather than silently guessed.

Version dispatch note: pre-0.3.0 documents carry no ``schema_version`` stamp (stamping was
introduced in 0.3.0). So a stampless document is either 0.1.0 or 0.2.0. If it carries the
structural pre-0.2.0 marker it is below the floor; otherwise it is ASSUMED 0.2.0 and that
assumption is recorded as ``written_under_inferred=True`` — absence of a stamp is not
evidence of a specific version, so the guess never masquerades as observed fact.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from fmri_repro.spec.preprocessing import SCHEMA_VERSION, Preprocessing
from fmri_repro.spec.provenance import LeftMissing, MissingFromPaper, ProvenancedField

MIGRATION_FLOOR = "0.2.0"
_MIGRATOR_ID = "spec.migrations/0.2.0->0.3.0/v1"
# Invalid as an intensity-normalization convention value from 0.2.0 on; its presence there
# is the structural signature of a pre-0.2.0 (0.1.0) document.
_PRE_FLOOR_MARKER = "voxel_temporal_zscore"
_ADDED_IN_0_3_0 = ("method", "filtering_integrated")  # required fields NuisanceRegression gained


class MigrationError(RuntimeError):
    """A document is below the migration floor (pre-0.2.0) and is not auto-migrated."""


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _has_pre_floor_marker(doc: dict[str, Any]) -> bool:
    for step in doc.get("steps", []):
        if not isinstance(step, dict) or step.get("kind") != "intensity_normalization":
            continue
        value = (((step.get("convention") or {}).get("extraction")) or {}).get("value")
        if value == _PRE_FLOOR_MARKER:
            return True
    return False


def detect_source_version(doc: dict[str, Any]) -> tuple[str, bool]:
    """Return ``(source_schema_version, inferred)`` for a Preprocessing-level document.

    A stamped document reports its own version (observed, ``inferred=False``). A stampless
    one carrying the pre-0.2.0 marker is reported ``("0.1.0", False)``; any other stampless
    document is ASSUMED ``"0.2.0"`` with ``inferred=True``.
    """
    stamp = doc.get("schema_version")
    if isinstance(stamp, str):
        return stamp, False
    if _has_pre_floor_marker(doc):
        return "0.1.0", False
    return MIGRATION_FLOOR, True


def _missing_field(field_id: str) -> dict[str, Any]:
    """A schema-correct MISSING_FROM_PAPER / LEFT_MISSING field dict, reason
    ``field_not_in_schema_version`` (renders into the ``not_covered`` bucket)."""
    pf = ProvenancedField[str](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
        inference=LeftMissing(reason="field_not_in_schema_version"),
    )
    return dict(json.loads(pf.model_dump_json()))


def migrate_to_current(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a NEW dict migrated to the current schema. Never mutates ``doc``.

    Raises :class:`MigrationError` if the document is below the 0.2.0 floor.
    """
    source, inferred = detect_source_version(doc)
    if source == SCHEMA_VERSION:
        return copy.deepcopy(doc)
    if _version_tuple(source) < _version_tuple(MIGRATION_FLOOR):
        raise MigrationError(
            f"document source schema {source} is below the migration floor "
            f"{MIGRATION_FLOOR}; the 0.1.0 -> 0.2.0 hop is a semantic restructuring and is "
            "not automated. Retain the original as a frozen v0.1.0 specimen."
        )
    out = copy.deepcopy(doc)
    # 0.2.0 -> 0.3.0: NuisanceRegression gained two required fields.
    for step in out.get("steps", []):
        if isinstance(step, dict) and step.get("kind") == "nuisance_regression":
            for fid in _ADDED_IN_0_3_0:
                step.setdefault(fid, _missing_field(fid))
    out["schema_version"] = SCHEMA_VERSION
    out["written_under"] = source
    out["written_under_inferred"] = inferred
    out["migration"] = {"migrated_from": source, "migrator_version": _MIGRATOR_ID}
    return out


def parse_any_version(doc: dict[str, Any]) -> Preprocessing:
    """Migrate-then-parse: the supported door for reading an archived ``Preprocessing`` of
    any supported version. Callers must not pin an old version module directly."""
    prep: Preprocessing = Preprocessing.model_validate(migrate_to_current(doc))
    return prep
