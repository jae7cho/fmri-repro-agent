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

Versioning convention (what makes vocabulary growth cheap):

- **ADDITIVE change -> PATCH bump, in-place, pure re-stamp hop.** Adding an OPTIONAL field with
  a default, or adding an allowed value to an existing enum. Every document valid under the prior
  version stays valid under the new version *unchanged* (an old doc simply never carries the new
  value). Bump ``SCHEMA_VERSION`` patch (e.g. 0.4.0 -> 0.4.1) in ``preprocessing.py`` and the
  ``StudySpec`` Literal, and add a re-stamp migration hop (no doc transform). **No new
  version-root file** — the version modules are write-time stamp-pinners over the one shared
  mutating :mod:`preprocessing`, and old data migrates forward. The 0.3.0 -> 0.4.0 hop
  (``span_recovered`` optional field) and the 0.4.0 -> 0.4.1 hop (``study_specific`` TargetSpace
  value) are both this kind.
- **STRUCTURAL change -> MINOR/MAJOR bump, real migration.** Renames/removes an enum value, adds
  a REQUIRED field, changes a field type, or restructures the chain — anything that makes an
  existing document invalid or changes its meaning. Needs a doc-transform hop (like 0.2.0 -> 0.3.0,
  which added required ``NuisanceRegression`` fields) and may warrant a distinct root declaration.
- **The test for "additive":** does every prior-version document remain valid, *unchanged*, under
  the new version? Yes -> additive/patch (in-place). No -> structural.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from fmri_repro.spec.preprocessing import SCHEMA_VERSION, Preprocessing
from fmri_repro.spec.provenance import LeftMissing, MissingFromPaper, ProvenancedField

MIGRATION_FLOOR = "0.2.0"
# Invalid as an intensity-normalization convention value from 0.2.0 on; its presence there
# is the structural signature of a pre-0.2.0 (0.1.0) document.
_PRE_FLOOR_MARKER = "voxel_temporal_zscore"
_ADDED_IN_0_3_0 = ("method", "filtering_integrated")  # required fields NuisanceRegression gained
# 0.4.1 -> 0.5.0: the five literal_type fields retype from a bare Literal member to
# SpecifiedTerm{verbatim, resolved, resolution}. Step kind -> the retyped field(s) it carries.
_RETYPED_IN_0_5_0: dict[str, tuple[str, ...]] = {
    "spatial_normalization": ("target_space",),
    "surface_projection": ("target_surface", "surface_registration"),
    "intensity_normalization": ("convention",),
    "temporal_standardization": ("method",),
}


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


def _lift_value(v: Any) -> Any:
    """One bare enum member -> the 0.5.0 ``SpecifiedTerm`` struct. Old values were resolved
    members by construction, so the lossless lift is ``verbatim = resolved = old``. Idempotent:
    an already-lifted dict value is returned unchanged."""
    if isinstance(v, dict):
        return v
    return {"verbatim": v, "resolved": v, "resolution": "resolved"}


def _lift_to_specified_term(field: Any) -> None:
    """In place: rewrite a retyped field's bare-member value into the ``SpecifiedTerm`` struct,
    on whichever provenance arm carries a value (Extracted / InferredDefault + its alternatives).

    A field carrying NO value (MissingFromPaper / DeferredToCitation / LeftMissing) is left
    untouched — there is nothing to lift, which is exactly why a historical false-missing cannot
    be repaired here (see the hop comment in :func:`migrate_to_current`)."""
    if not isinstance(field, dict):
        return
    ext = field.get("extraction")
    if isinstance(ext, dict) and ext.get("status") == "EXTRACTED":
        ext["value"] = _lift_value(ext.get("value"))
    inf = field.get("inference")
    if isinstance(inf, dict) and inf.get("status") == "INFERRED_DEFAULT":
        inf["value"] = _lift_value(inf.get("value"))
        for alt in inf.get("alternative_inferences") or []:
            if isinstance(alt, dict):
                alt["value"] = _lift_value(alt.get("value"))


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
    # 0.3.0 -> 0.4.0: adds only the optional-default Extracted.span_recovered field; no doc
    # transform is needed (an absent flag validates to False) — the hop is a pure re-stamp.
    # 0.4.0 -> 0.4.1: adds only the additive TargetSpace value "study_specific"; no doc transform
    # (a doc that never used it validates unchanged) — pure re-stamp.
    #
    # 0.4.1 -> 0.5.0 (STRUCTURAL, a real doc-transform — NOT a re-stamp): the five literal_type
    # fields retype from a bare Literal member to SpecifiedTerm{verbatim, resolved, resolution}.
    # Lift each carried value in place; old values were resolved enum members, so
    # verbatim=resolved=old with resolution="resolved" is lossless.
    #
    # HISTORICAL FALSE-MISSINGS CANNOT BE REPAIRED HERE. A <=0.4.1 doc that recorded
    # MissingFromPaper for a stated-but-unresolvable term (the value_not_in_literal false-missing:
    # a paper wrote "MNI", the resolver returned underspecified, and the extractor relabeled the
    # field MISSING) carries NO value to lift — the paper's term lived only in the extractor_mvp
    # ExtractionDiagnostic, which was NEVER part of the committed spec model (it sits in a gitignored
    # results/ tree). So this hop carries those false-missings FORWARD: structurally retyped and still
    # empty. The retype prevents FUTURE false-missings; correcting the existing ones needs
    # re-extraction under 0.5.0, not migration.
    if _version_tuple(source) < _version_tuple("0.5.0"):
        for step in out.get("steps", []):
            if not isinstance(step, dict):
                continue
            for fid in _RETYPED_IN_0_5_0.get(step.get("kind", ""), ()):
                _lift_to_specified_term(step.get(fid))
    # 0.5.0 -> 0.5.1 (PATCH, pure re-stamp — NO doc transform): MotionCorrection gains a bool field
    # (transforms_combined) and retypes its four closed Literals to SpecifiedTerm[X]. VERSION-CONFLICT
    # NOTE: the convention's enumeration lists "changes a field type" under STRUCTURAL, but its governing
    # TEST is "does every prior document remain valid, unchanged?" — and it does: NO committed document
    # contains a motion_correction step (MotionCorrection is never instantiated in _assemble), so
    # retyping fields that appear in zero documents, and adding one to that step, breaks none. The
    # additive test (the substance) governs over the field-type enumeration (a proxy for "makes existing
    # documents invalid") when the two conflict on a never-emitted step. Hence patch + re-stamp: there is
    # nothing to transform. (If motion_correction is ever emitted, a future doc-transform hop must lift
    # its literal_type fields like the 0.5.0 block above.)
    #
    # Both re-stamp hops and the 0.5.0 transform fall through to the single stamp write below;
    # migrator_version is f-string-generated from SCHEMA_VERSION.
    out["schema_version"] = SCHEMA_VERSION
    out["written_under"] = source
    out["written_under_inferred"] = inferred
    out["migration"] = {
        "migrated_from": source,
        "migrator_version": f"spec.migrations/{source}->{SCHEMA_VERSION}/v1",
    }
    return out


def parse_any_version(doc: dict[str, Any]) -> Preprocessing:
    """Migrate-then-parse: the supported door for reading an archived ``Preprocessing`` of
    any supported version. Callers must not pin an old version module directly."""
    prep: Preprocessing = Preprocessing.model_validate(migrate_to_current(doc))
    return prep
