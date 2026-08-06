"""Forward migration + version-stamp tests (fmri_repro.spec.migrations)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from fmri_repro.spec.migrations import (
    MIGRATION_FLOOR,
    MigrationError,
    detect_source_version,
    migrate_to_current,
    parse_any_version,
)
from fmri_repro.spec.preprocessing import SCHEMA_VERSION, Preprocessing

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_V010 = REPO_ROOT / "examples" / "frozen" / "preprocessing-v0.1.0.json"


def _missing(field_id: str) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {"status": "LEFT_MISSING", "reason": "not_stated_in_text"},
    }


def _v020_doc_with_nuisance() -> dict[str, Any]:
    """A stampless 0.2.0-era Preprocessing dict whose nuisance step lacks the 0.3.0 fields."""
    nuisance = {
        "kind": "nuisance_regression",
        "motion_expansion": _missing("motion_expansion"),
        "tissue_regressors": _missing("tissue_regressors"),
        "physio_regressors": _missing("physio_regressors"),
        "physio_n_regressors": _missing("physio_n_regressors"),
        "detrend": _missing("detrend"),
    }
    return {
        "applies_to": [{"suffix": "bold", "entities": {"task": "rest"}}],
        "base_pipeline": {"kind": "not_applicable"},
        "steps": [nuisance],
    }


# --- detect_source_version --------------------------------------------------


def test_detect_stamped_is_observed():
    assert detect_source_version({"schema_version": "0.3.0", "steps": []}) == ("0.3.0", False)


def test_detect_stampless_assumed_0_2_0_inferred():
    version, inferred = detect_source_version(_v020_doc_with_nuisance())
    assert version == MIGRATION_FLOOR and inferred is True


def test_detect_pre_floor_marker_is_observed_0_1_0():
    doc = json.loads(FROZEN_V010.read_text())
    assert detect_source_version(doc) == ("0.1.0", False)


# --- migrate_to_current -----------------------------------------------------


def test_migrate_fills_new_nuisance_fields_and_stamps():
    src = _v020_doc_with_nuisance()
    original = copy.deepcopy(src)
    out = migrate_to_current(src)

    assert src == original  # read-only: input never mutated
    assert out["schema_version"] == SCHEMA_VERSION
    assert out["written_under"] == "0.2.0"
    assert out["written_under_inferred"] is True
    assert out["migration"]["migrated_from"] == "0.2.0"
    assert out["migration"]["migrator_version"]
    nuis = next(s for s in out["steps"] if s["kind"] == "nuisance_regression")
    for fid in ("method", "filtering_integrated"):
        assert nuis[fid]["inference"]["reason"] == "field_not_in_schema_version"


def test_migrate_current_doc_is_passthrough():
    out = parse_any_version(migrate_to_current({"schema_version": "0.5.0", **_native_min()}))
    assert out.schema_version == "0.5.0"
    assert out.migration is None  # a native/current doc is not marked migrated


def test_migrate_0_3_0_to_current_restamps():
    # 0.3.0 migrates forward to the current stamp (0.5.0). The 0.3.0->0.4.0 (span_recovered) and
    # 0.4.0->0.4.1 (study_specific) hops are pure re-stamps; the structural 0.4.1->0.5.0 hop lifts the
    # five literal_type fields but is a no-op here (this doc has no spatial_normalization / surface /
    # intensity / temporal step). The nuisance step's pre-existing 0.3.0 fields are left untouched
    # (the setdefault backfill is a no-op when the keys are already present).
    nuisance = {
        "kind": "nuisance_regression",
        "method": _missing("method"),
        "filtering_integrated": _missing("filtering_integrated"),
        "motion_expansion": _missing("motion_expansion"),
        "tissue_regressors": _missing("tissue_regressors"),
        "physio_regressors": _missing("physio_regressors"),
        "physio_n_regressors": _missing("physio_n_regressors"),
        "detrend": _missing("detrend"),
    }
    src = {
        "schema_version": "0.3.0",
        "applies_to": [{"suffix": "bold", "entities": {"task": "rest"}}],
        "base_pipeline": {"kind": "not_applicable"},
        "steps": [nuisance],
    }
    original = copy.deepcopy(src)
    out = migrate_to_current(src)

    assert src == original  # read-only: input never mutated
    assert out["schema_version"] == "0.5.0"
    assert out["written_under"] == "0.3.0"  # a 0.3.0-stamped source is observed, not inferred
    assert out["written_under_inferred"] is False
    assert out["migration"]["migrated_from"] == "0.3.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.3.0->0.5.0/v1"
    # No nuisance-field mutation: the sentinel reason from _missing (not the migrator's
    # "field_not_in_schema_version") survives, proving the setdefault backfill did not fire.
    nuis = next(s for s in out["steps"] if s["kind"] == "nuisance_regression")
    assert nuis["method"]["inference"]["reason"] == "not_stated_in_text"
    assert nuis["filtering_integrated"]["inference"]["reason"] == "not_stated_in_text"


def test_migrate_0_4_0_to_current_restamps():
    # A 0.4.0 document migrates forward to the current stamp (0.5.0). For a doc with no retyped-field
    # steps (this one), every in-between hop — the additive 0.4.0->0.4.1 (study_specific) and the
    # structural 0.4.1->0.5.0 (SpecifiedTerm retype) — leaves the content unchanged, so this is
    # effectively a re-stamp. The migration is recorded (source observed, not inferred).
    src = {"schema_version": "0.4.0", **_native_min()}
    original = copy.deepcopy(src)
    out = migrate_to_current(src)
    assert src == original  # read-only
    assert out["schema_version"] == "0.5.0"
    assert out["written_under"] == "0.4.0"
    assert out["written_under_inferred"] is False
    assert out["migration"]["migrated_from"] == "0.4.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.4.0->0.5.0/v1"
    # parses cleanly under the current model
    assert parse_any_version(src).schema_version == "0.5.0"


def _extracted_member(member: str) -> dict[str, Any]:
    """A 0.4.x EXTRACTED field carrying a bare enum member (the pre-retype shape)."""
    return {
        "extraction": {
            "status": "EXTRACTED",
            "value": member,
            "spans": [{"start": 0, "end": len(member), "text": member}],
            "confidence": 0.9,
            "span_recovered": False,
        },
        "inference": {"status": "NOT_APPLICABLE"},
    }


def test_migrate_0_4_1_to_0_5_0_lifts_all_five_retyped_fields_and_carries_false_missing():
    # STRUCTURAL 0.4.1 -> 0.5.0 across ALL FIVE retyped fields, one per affected step kind (regenerating
    # the committed examples bypasses the transform, so the hop's coverage on the other four fields is
    # exercised HERE): each EXTRACTED bare member lifts to SpecifiedTerm{verbatim, resolved, resolution}
    # (verbatim=resolved=old, resolution "resolved"); a MISSING retyped field (the historical
    # false-missing) is carried forward untouched — the paper's term is unrecoverable (it lived only in
    # the gitignored extractor diagnostic), so migration cannot repair it.
    src = {
        "schema_version": "0.4.1",
        "applies_to": [{"suffix": "bold", "entities": {"task": "rest"}}],
        "base_pipeline": {"kind": "not_applicable"},
        "steps": [
            {
                "kind": "spatial_normalization",
                "target_space": {
                    "field_id": "target_space",
                    **_extracted_member("MNI152NLin6Asym"),
                },
                "resolution_mm": _missing("resolution_mm"),
                "method": _missing("method"),
                "warp": _missing("warp"),
                "transform_type": _missing("transform_type"),
                "interpolation": _missing("interpolation"),
                "regularization": _missing("regularization"),
            },
            {
                "kind": "surface_projection",
                "target_surface": {"field_id": "target_surface", **_extracted_member("fsLR_32k")},
                "vol2surf_sampling": _missing("vol2surf_sampling"),
                "surface_registration": {
                    "field_id": "surface_registration",
                    **_extracted_member("msm_all"),
                },
                "cifti": _missing("cifti"),
            },
            {
                "kind": "intensity_normalization",
                "scope": _missing("scope"),
                "convention": {
                    "field_id": "convention",
                    **_extracted_member("fsl_grand_mean_10000"),
                },
                "value": _missing("value"),
            },
            {
                "kind": "temporal_standardization",
                # a MISSING retyped field == the false-missing carry-forward
                "method": _missing("method"),
            },
        ],
    }
    original = copy.deepcopy(src)
    out = migrate_to_current(src)
    assert src == original  # read-only: input never mutated

    def _val(step_i: int, field: str) -> Any:
        return out["steps"][step_i][field]["extraction"]["value"]

    # all four EXTRACTED retyped fields, across all four affected step kinds, lift losslessly
    assert _val(0, "target_space") == {
        "verbatim": "MNI152NLin6Asym",
        "resolved": "MNI152NLin6Asym",
        "resolution": "resolved",
    }
    assert _val(1, "target_surface") == {
        "verbatim": "fsLR_32k",
        "resolved": "fsLR_32k",
        "resolution": "resolved",
    }
    assert _val(1, "surface_registration") == {
        "verbatim": "msm_all",
        "resolved": "msm_all",
        "resolution": "resolved",
    }
    assert _val(2, "convention") == {
        "verbatim": "fsl_grand_mean_10000",
        "resolved": "fsl_grand_mean_10000",
        "resolution": "resolved",
    }
    # the MISSING temporal method carries forward with NO value (false-missing, structurally retyped)
    assert "value" not in out["steps"][3]["method"]["extraction"]
    assert out["schema_version"] == "0.5.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.4.1->0.5.0/v1"

    # the whole doc round-trips cleanly under the current model, verbatim preserved on every arm
    prep = parse_any_version(src)
    sn = next(s for s in prep.steps if s.kind == "spatial_normalization")
    assert sn.target_space.extraction.value.resolved == "MNI152NLin6Asym"
    assert sn.target_space.extraction.value.verbatim == "MNI152NLin6Asym"
    sp = next(s for s in prep.steps if s.kind == "surface_projection")
    assert sp.surface_registration.extraction.value.resolved == "msm_all"
    assert sp.target_surface.extraction.value.verbatim == "fsLR_32k"


def _native_min() -> dict[str, Any]:
    return {
        "applies_to": [{"suffix": "bold", "entities": {"task": "rest"}}],
        "base_pipeline": {"kind": "not_applicable"},
        "steps": [
            {
                "kind": "despike",
                "method": _missing("method"),
                "threshold": _missing("threshold"),
            }
        ],
    }


# --- parse_any_version -------------------------------------------------------


def test_parse_any_version_migrates_and_parses():
    prep = parse_any_version(_v020_doc_with_nuisance())
    assert isinstance(prep, Preprocessing)
    assert prep.schema_version == "0.5.0"
    assert prep.written_under == "0.2.0" and prep.written_under_inferred is True
    assert prep.migration is not None and prep.migration.migrated_from == "0.2.0"
    nr = next(s for s in prep.steps if s.kind == "nuisance_regression")
    assert nr.method.inference.reason == "field_not_in_schema_version"
    assert nr.filtering_integrated.inference.reason == "field_not_in_schema_version"


def test_parse_any_version_refuses_below_floor_loudly():
    # The frozen genuine v0.1.0 specimen carries the pre-0.2.0 marker -> refused, not guessed.
    doc = json.loads(FROZEN_V010.read_text())
    with pytest.raises(MigrationError, match="below the migration floor"):
        parse_any_version(doc)
