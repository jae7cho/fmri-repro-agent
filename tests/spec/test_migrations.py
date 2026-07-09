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
    out = parse_any_version(migrate_to_current({"schema_version": "0.3.0", **_native_min()}))
    assert out.schema_version == "0.3.0"
    assert out.migration is None  # a native/current doc is not marked migrated


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
    assert prep.schema_version == "0.3.0"
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
