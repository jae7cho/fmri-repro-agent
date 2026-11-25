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
    out = parse_any_version(migrate_to_current({"schema_version": "0.8.0", **_native_min()}))
    assert out.schema_version == "0.8.0"
    assert out.migration is None  # a native/current doc is not marked migrated


def test_migrate_0_3_0_to_current_restamps():
    # 0.3.0 migrates forward to the current stamp (0.5.1). The 0.3.0->0.4.0 (span_recovered) and
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
    assert out["schema_version"] == "0.8.0"
    assert out["written_under"] == "0.3.0"  # a 0.3.0-stamped source is observed, not inferred
    assert out["written_under_inferred"] is False
    assert out["migration"]["migrated_from"] == "0.3.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.3.0->0.8.0/v1"
    # No nuisance-field mutation: the sentinel reason from _missing (not the migrator's
    # "field_not_in_schema_version") survives, proving the setdefault backfill did not fire.
    nuis = next(s for s in out["steps"] if s["kind"] == "nuisance_regression")
    assert nuis["method"]["inference"]["reason"] == "not_stated_in_text"
    assert nuis["filtering_integrated"]["inference"]["reason"] == "not_stated_in_text"


def test_migrate_0_4_0_to_current_restamps():
    # A 0.4.0 document migrates forward to the current stamp (0.5.1). For a doc with no retyped-field
    # steps (this one), every in-between hop — the additive 0.4.0->0.4.1 (study_specific) and the
    # structural 0.4.1->0.5.0 (SpecifiedTerm retype) — leaves the content unchanged, so this is
    # effectively a re-stamp. The migration is recorded (source observed, not inferred).
    src = {"schema_version": "0.4.0", **_native_min()}
    original = copy.deepcopy(src)
    out = migrate_to_current(src)
    assert src == original  # read-only
    assert out["schema_version"] == "0.8.0"
    assert out["written_under"] == "0.4.0"
    assert out["written_under_inferred"] is False
    assert out["migration"]["migrated_from"] == "0.4.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.4.0->0.8.0/v1"
    # parses cleanly under the current model
    assert parse_any_version(src).schema_version == "0.8.0"


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
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.4.1->0.8.0/v1"

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
    assert prep.schema_version == "0.8.0"
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


def test_migrate_0_5_3_to_0_6_0_lifts_the_listed_fields_to_one_item_lists():
    """0.5.3 -> 0.6.2 (2026-10-29, DESIGN_report_v2.md §1b): a stored scalar on a field that became a
    list is wrapped in a one-item list; a missing field is untouched."""
    term = {"verbatim": "FUGUE", "resolved": "fugue", "resolution": "resolved"}
    dist = {
        "kind": "distortion_correction",
        "source": _missing("source"),
        "method": {
            "field_id": "method",
            "extraction": {
                "status": "EXTRACTED",
                "value": term,
                "spans": [{"start": 0, "end": 5, "text": "FUGUE", "section": None}],
                "confidence": 0.9,
            },
            "inference": {"status": "NOT_APPLICABLE"},
        },
        "intended_fieldmap": {"kind": "not_applicable"},
    }
    src = {
        "schema_version": "0.5.3",
        "applies_to": [{"suffix": "bold", "entities": {"task": "rest"}}],
        "base_pipeline": {"kind": "not_applicable"},
        "steps": [dist],
    }
    out = migrate_to_current(src)
    step = out["steps"][0]
    assert step["method"]["extraction"]["value"] == [term]
    assert step["source"]["extraction"]["status"] == "MISSING_FROM_PAPER"
    prep = parse_any_version(src)
    assert prep.steps[0].method.extraction.value[0].resolved == "fugue"


def test_a_0_6_0_doc_with_tool_names_in_the_distortion_method_restamps_unchanged():
    """0.6.0 -> 0.6.1 -> 0.6.2 (2026-11-03) is additive: the program-named method members stay valid
    and the new ``tool`` field is not synthesised."""
    step = {
        "kind": "distortion_correction",
        "source": _missing("source"),
        "method": {
            "field_id": "method",
            "extraction": {
                "status": "EXTRACTED",
                "value": [{"verbatim": "topup", "resolved": "topup", "resolution": "resolved"}],
                "spans": [{"start": 0, "end": 5, "text": "topup"}],
                "confidence": 0.8,
            },
            "inference": {"status": "NOT_APPLICABLE"},
        },
        "intended_fieldmap": {"status": "NOT_APPLICABLE"},
    }
    src = {"schema_version": "0.6.0", **_native_min(), "steps": [step]}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"]  # no doc transform
    assert out["schema_version"] == "0.8.0" and out["written_under"] == "0.6.0"
    dc = parse_any_version(src).steps[0]
    assert dc.method.extraction.value[0].resolved == "topup" and dc.tool is None


def test_a_0_6_1_doc_restamps_unchanged_to_0_6_2():
    """0.6.1 -> 0.6.2 (2026-11-03): DistortionMethod gains gradient_nonlinearity_correction."""
    src = {"schema_version": "0.6.1", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.6.1"
    assert out["schema_version"] == "0.8.0"


def test_a_0_6_2_doc_restamps_unchanged_to_0_6_3_without_pass_type():
    """0.6.2 -> 0.6.3 (2026-11-05, fix 5): TemporalFiltering gains an optional pass_type."""
    src = {"schema_version": "0.6.2", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.6.2"
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.6.2->0.8.0/v1"
    prep = parse_any_version(src)
    tf = [s for s in prep.steps if s.kind == "temporal_filtering"]
    assert all(s.pass_type is None for s in tf)


def test_a_0_6_3_doc_restamps_unchanged_to_0_7_0_every_value_applying_to_all():
    """0.6.3 -> 0.7.0 (2026-11-11, DESIGN_applies_to.md Stage 1): the Varied arm and step-order parts
    are additive. Every stored value stays an Extracted value, which is what "all" means under A1."""
    src = {"schema_version": "0.6.3", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.6.3"
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.6.3->0.8.0/v1"
    prep = parse_any_version(src)
    assert prep.step_order_parts is None
    for step in prep.steps:
        for name in type(step).model_fields:
            pf = getattr(step, name)
            assert getattr(getattr(pf, "extraction", None), "status", None) != "VARIED"


def test_a_0_7_0_doc_restamps_unchanged_to_0_7_1() -> None:
    """0.7.0 -> 0.7.1 (2026-11-11, Stage 2b item 3): StepOrderPart gains optional applies_to_spans."""
    src = {"schema_version": "0.7.0", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.7.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.7.0->0.8.0/v1"
    span = {"start": 0, "end": 4, "text": "text"}
    part = {"kinds": ["scrub", "despike"], "applies_to": "Part III", "spans": [span]}
    prep = parse_any_version({**src, "step_order_source": "by_part", "step_order_parts": [part]})
    assert prep.step_order_parts is not None and prep.step_order_parts[0].applies_to_spans == []


def test_a_0_7_1_doc_restamps_unchanged_to_0_7_2() -> None:
    """0.7.1 -> 0.7.2 (2026-11-11, pre-rerun item 1): a value's spans may be 1-3 places of the text."""
    src = {"schema_version": "0.7.1", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.7.1"
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.7.1->0.8.0/v1"


def test_a_0_7_2_doc_restamps_unchanged_to_0_7_3() -> None:
    """0.7.2 -> 0.7.3 (2026-11-11, pre-rerun item 2): Extracted and Variant gain checker_supplied, default False."""
    src = {"schema_version": "0.7.2", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.7.2"
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.7.2->0.8.0/v1"


def test_a_0_7_3_doc_restamps_unchanged_to_0_7_4() -> None:
    """0.7.3 -> 0.7.4 (2026-11-11, pre-rerun item 4): Deferral gains source_could_not_be_opened, default False."""
    src = {"schema_version": "0.7.3", **_native_min()}
    out = migrate_to_current(src)
    assert out["steps"] == src["steps"] and out["written_under"] == "0.7.3"
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.7.3->0.8.0/v1"


# --- 0.7.4 -> 0.8.0 (2026-11-25, DESIGN_prompt_schema_2026-11 D3) -----------------------------


def _term_dict(member: str) -> dict[str, Any]:
    return {"verbatim": member, "resolved": member, "resolution": "resolved"}


def _varied(field_id: str, *parts: tuple[Any, str]) -> dict[str, Any]:
    """A 0.7.x VARIED field: one (value, applies_to) pair per part of the data."""
    return {
        "field_id": field_id,
        "extraction": {
            "status": "VARIED",
            "variants": [
                {
                    "value": value,
                    "spans": [{"start": i, "end": i + 4, "text": "text"}],
                    "applies_to": applies_to,
                    "confidence": 0.9,
                }
                for i, (value, applies_to) in enumerate(parts)
            ],
        },
        "inference": {"status": "NOT_APPLICABLE"},
    }


def _spatial_normalization_074(method: dict[str, Any], warp: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "spatial_normalization",
        "target_space": {
            "field_id": "target_space",
            **_extracted_member("MNI152NLin6Asym"),
            "extraction": {
                **_extracted_member("MNI152NLin6Asym")["extraction"],
                "value": _term_dict("MNI152NLin6Asym"),
            },
        },
        "resolution_mm": _missing("resolution_mm"),
        "method": method,
        "warp": warp,
        "transform_type": _missing("transform_type"),
        "interpolation": _missing("interpolation"),
        "regularization": _missing("regularization"),
    }


def _scrub_074(threshold: dict[str, Any]) -> dict[str, Any]:
    criterion = {
        "field_id": "criterion",
        **_extracted_member("fd_power"),
    }
    criterion["extraction"] = {
        **criterion["extraction"],
        "value": [_term_dict("fd_power"), _term_dict("dvars")],
    }
    return {
        "kind": "scrub",
        "criterion": criterion,
        "threshold": threshold,
        "remediation": _missing("remediation"),
        "interpolation_method": _missing("interpolation_method"),
    }


def test_a_0_7_4_doc_restamps_to_0_8_0_and_keeps_steps_the_hop_does_not_name() -> None:
    """0.7.4 -> 0.8.0: the two transforms touch spatial_normalization and scrub only."""
    src = {"schema_version": "0.7.4", **_native_min()}
    original = copy.deepcopy(src)
    out = migrate_to_current(src)
    assert src == original
    assert out["steps"] == src["steps"] and out["written_under"] == "0.7.4"
    assert out["schema_version"] == "0.8.0"
    assert out["migration"]["migrator_version"] == "spec.migrations/0.7.4->0.8.0/v1"


def test_0_8_0_lifts_spatial_normalization_method_and_warp_to_specified_terms() -> None:
    """B2: a bare member becomes a SpecifiedTerm on the extracted arm and on each part of a varied
    value. A field with no value, and a field that is a term already, are left as they are."""
    method = {"field_id": "method", **_extracted_member("fnirt")}
    warp = _varied("warp", ("affine", "dataset A"), ("nonlinear", "dataset B"))
    src = {
        "schema_version": "0.7.4",
        **_native_min(),
        "steps": [_spatial_normalization_074(method, warp)],
    }
    original = copy.deepcopy(src)
    out = migrate_to_current(src)
    assert src == original  # read-only
    step = out["steps"][0]
    assert step["method"]["extraction"]["value"] == _term_dict("fnirt")
    assert [v["value"] for v in step["warp"]["extraction"]["variants"]] == [
        _term_dict("affine"),
        _term_dict("nonlinear"),
    ]
    assert step["target_space"] == src["steps"][0]["target_space"]  # a term since 0.5.0
    assert step["resolution_mm"] == _missing("resolution_mm")
    sn = parse_any_version(src).steps[0]
    assert sn.method.extraction.value.resolved == "fnirt"
    assert [v.value.resolved for v in sn.warp.extraction.variants] == ["affine", "nonlinear"]
    # the 0.7.4 run records: the extractor never targeted the two fields, so nothing is lifted
    untargeted = _spatial_normalization_074(_missing("method"), _missing("warp"))
    out = migrate_to_current({"schema_version": "0.7.4", **_native_min(), "steps": [untargeted]})
    assert out["steps"][0]["method"] == _missing("method")
    assert out["steps"][0]["warp"] == _missing("warp")


def test_0_8_0_makes_the_scrub_threshold_a_list() -> None:
    """C9: the threshold is a list. A stored number becomes a one-item list; the criteria
    beside it are untouched, so two criteria and one number stay two and one."""
    threshold = {"field_id": "threshold", **_extracted_member("0.5")}
    threshold["extraction"]["value"] = 0.5
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [_scrub_074(threshold)]}
    original = copy.deepcopy(src)
    out = migrate_to_current(src)
    assert src == original
    step = out["steps"][0]
    assert step["threshold"]["extraction"]["value"] == [0.5]
    assert step["criterion"] == src["steps"][0]["criterion"]
    scrub = parse_any_version(src).steps[0]
    assert scrub.threshold.extraction.value == [0.5]
    assert [t.resolved for t in scrub.criterion.extraction.value] == ["fd_power", "dvars"]
    # a missing threshold keeps no value
    out = migrate_to_current(
        {"schema_version": "0.7.4", **_native_min(), "steps": [_scrub_074(_missing("threshold"))]}
    )
    assert out["steps"][0]["threshold"] == _missing("threshold")


def test_0_8_0_lifts_each_part_of_a_varied_threshold_and_keeps_a_part_with_no_value() -> None:
    varied = _varied("threshold", (0.9, "task fMRI"), (0.2, "resting-state fMRI"))
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [_scrub_074(varied)]}
    out = migrate_to_current(src)
    assert [v["value"] for v in out["steps"][0]["threshold"]["extraction"]["variants"]] == [
        [0.9],
        [0.2],
    ]
    scrub = parse_any_version(src).steps[0]
    assert [v.value for v in scrub.threshold.extraction.variants] == [[0.9], [0.2]]
    # the compared-models entry holds no value, and still holds none
    compared = _varied("threshold", (None, "varied across compared models"))
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [_scrub_074(compared)]}
    out = migrate_to_current(src)
    assert out["steps"][0]["threshold"]["extraction"]["variants"][0]["value"] is None
    assert parse_any_version(src).steps[0].threshold.extraction.variants[0].value is None


def test_the_0_8_0_hop_runs_after_the_earlier_ones_on_an_older_document() -> None:
    """A 0.5.1 scrub step: the criterion is a bare member (lifted in 0.5.2, listed in 0.6.0) and
    the threshold a number (listed in 0.8.0)."""
    threshold = {"field_id": "threshold", **_extracted_member("0.3")}
    threshold["extraction"]["value"] = 0.3
    step = {
        "kind": "scrub",
        "criterion": {"field_id": "criterion", **_extracted_member("fd_power")},
        "threshold": threshold,
        "remediation": _missing("remediation"),
        "interpolation_method": _missing("interpolation_method"),
    }
    src = {"schema_version": "0.5.1", **_native_min(), "steps": [step]}
    out = migrate_to_current(src)
    assert out["steps"][0]["criterion"]["extraction"]["value"] == [_term_dict("fd_power")]
    assert out["steps"][0]["threshold"]["extraction"]["value"] == [0.3]
    assert out["migration"]["migrator_version"] == "spec.migrations/0.5.1->0.8.0/v1"
    assert parse_any_version(src).steps[0].threshold.extraction.value == [0.3]


def test_migrating_a_0_8_0_document_changes_nothing() -> None:
    """A current document is returned as it is (migrate_to_current copies it and stops), so its
    list is not wrapped again and its term not lifted again."""
    threshold = {"field_id": "threshold", **_extracted_member("0.5")}
    threshold["extraction"]["value"] = [3.0, 0.5]
    method = {"field_id": "method", **_extracted_member("fnirt")}
    method["extraction"]["value"] = _term_dict("fnirt")
    steps = [_scrub_074(threshold), _spatial_normalization_074(method, _missing("warp"))]
    src = {"schema_version": "0.8.0", **_native_min(), "steps": steps}
    assert migrate_to_current(src) == src
    assert parse_any_version(src).steps[0].threshold.extraction.value == [3.0, 0.5]


def test_a_0_7_4_document_that_already_holds_the_0_8_0_shapes_is_read_as_it_is() -> None:
    """A re-check or a promotion run by 0.8.0 code writes a list threshold into a stored record
    whose stamp is older. The lifts leave a list, and a term, as they are."""
    threshold = {"field_id": "threshold", **_extracted_member("0.5")}
    threshold["extraction"]["value"] = [3.0, 0.5]
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [_scrub_074(threshold)]}
    assert migrate_to_current(src)["steps"][0]["threshold"]["extraction"]["value"] == [3.0, 0.5]
    assert parse_any_version(src).steps[0].threshold.extraction.value == [3.0, 0.5]
    varied = _varied("threshold", ([0.9], "task fMRI"), (0.2, "resting-state fMRI"))
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [_scrub_074(varied)]}
    out = migrate_to_current(src)
    assert [v["value"] for v in out["steps"][0]["threshold"]["extraction"]["variants"]] == [
        [0.9],
        [0.2],
    ]
    method = {"field_id": "method", **_extracted_member("fnirt")}
    method["extraction"]["value"] = _term_dict("fnirt")
    step = _spatial_normalization_074(method, _missing("warp"))
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [step]}
    assert migrate_to_current(src)["steps"][0]["method"]["extraction"]["value"] == _term_dict(
        "fnirt"
    )


def test_0_8_0_keeps_the_part_of_a_varied_method_that_holds_no_value() -> None:
    """The compared-models entry of a varied value holds none (0.7.0), and is the only part then.
    The term lift must not make a term of it."""
    compared = _varied("method", (None, "varied across compared models"))
    step = _spatial_normalization_074(compared, _missing("warp"))
    src = {"schema_version": "0.7.4", **_native_min(), "steps": [step]}
    out = migrate_to_current(src)
    assert out["steps"][0]["method"]["extraction"]["variants"][0]["value"] is None
    assert parse_any_version(src).steps[0].method.extraction.variants[0].value is None


@pytest.mark.parametrize(
    "status", ["INFERRED_DEFAULT", "INFERRED_FROM_TEXT", "INFERRED_FROM_CITATION"]
)
def test_the_lift_helpers_cover_every_inferred_status(status: str) -> None:
    """No 0.7.4 document holds the two statuses 0.8.0 adds; a later structural hop will meet them,
    and the helpers lift an inferred value and its alternatives whatever the status."""
    from fmri_repro.spec.migrations import _lift_to_list, _lift_to_specified_term

    def field(value: Any, alternative: Any) -> dict[str, Any]:
        return {
            "extraction": {"status": "MISSING_FROM_PAPER"},
            "inference": {
                "status": status,
                "value": value,
                "alternative_inferences": [{"value": alternative}],
            },
        }

    listed = field(0.5, 0.2)
    _lift_to_list(listed)
    assert listed["inference"]["value"] == [0.5]
    assert listed["inference"]["alternative_inferences"][0]["value"] == [0.2]
    termed = field("ants", "fnirt")
    _lift_to_specified_term(termed)
    assert termed["inference"]["value"] == _term_dict("ants")
    assert termed["inference"]["alternative_inferences"][0]["value"] == _term_dict("fnirt")
    # a second pass changes nothing: a list is not wrapped again, a term not lifted again
    _lift_to_list(listed)
    _lift_to_specified_term(termed)
    assert listed["inference"]["value"] == [0.5]
    assert listed["inference"]["alternative_inferences"][0]["value"] == [0.2]
    assert termed["inference"]["value"] == _term_dict("ants")
    # an arm with no value is left alone
    left = {"extraction": {"status": "MISSING_FROM_PAPER"}, "inference": {"status": "LEFT_MISSING"}}
    _lift_to_list(left)
    _lift_to_specified_term(left)
    assert left["inference"] == {"status": "LEFT_MISSING"}
