"""Verification suite for the per-arm v0.1.0 acquisition collection.

Covers:
1. Multi-value Literal discriminator: T1w/T2w → Anatomical, all 5 fmap
   suffixes → Fieldmap, ``bold`` → Functional; unknown suffix rejected.
2. JSON-schema export of the inheritance-based generic discriminated union
   succeeds for the ``Acquisition`` union; each arm round-trips.
3. ``echo_time_ms`` shape per arm: Functional accepts list[float] and rejects
   scalar; Anatomical accepts scalar and rejects list.
4. Per-arm registry bijection (raises when an entry is removed).
5. ``inference_applicable`` invariant per arm.
6. Collection invariants: duplicate (suffix, entities) rejected; dangling
   ``intended_for`` rejected; valid ``intended_for`` accepted.
7. :func:`bids_stem` produces expected strings.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from fmri_repro.spec import core
from fmri_repro.spec.core import (
    ANATOMICAL_FIELD_META,
    COMMON_FIELD_META,
    FIELDMAP_FIELD_META,
    FUNCTIONAL_FIELD_META,
    Acquisition,
    AcquisitionEntities,
    AnatomicalAcquisition,
    FieldmapAcquisition,
    FirstLevelModel,
    FunctionalAcquisition,
    GroupLevelModel,
    Preprocessing,
    ReplicationSpec,
    Thresholding,
    _check_arm_bijection,
    bids_stem,
)


# ---------------------------------------------------------------------------
# Payload helpers — every PF defaults to MISSING + LEFT_MISSING for brevity.
# ---------------------------------------------------------------------------
def _missing_pf(field_id: str) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {"status": "LEFT_MISSING", "reason": "placeholder"},
    }


def _common_payload() -> dict[str, Any]:
    """The 13 CommonAcquisitionParams fields, all set to MISSING + LEFT_MISSING."""
    return {name: _missing_pf(name) for name in COMMON_FIELD_META}


def _functional_payload(entities: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _common_payload()
    payload["suffix"] = "bold"
    payload["entities"] = entities or {}
    for name in FUNCTIONAL_FIELD_META:
        payload[name] = _missing_pf(name)
    return payload


def _anatomical_payload(suffix: str = "T1w") -> dict[str, Any]:
    payload = _common_payload()
    payload["suffix"] = suffix
    payload["entities"] = {}
    for name in ANATOMICAL_FIELD_META:
        payload[name] = _missing_pf(name)
    return payload


def _fieldmap_payload(
    suffix: str = "epi",
    entities: dict[str, Any] | None = None,
    intended_for: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = _common_payload()
    payload["suffix"] = suffix
    payload["entities"] = entities or {}
    for name in FIELDMAP_FIELD_META:
        payload[name] = _missing_pf(name)
    payload["intended_for"] = intended_for or []
    return payload


def _minimal_preprocessing_payload(
    functional_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Construct the smallest valid ``Preprocessing`` payload covering the
    given functional acquisitions: one ``nonsteadystate_removal`` step,
    ``base_pipeline=NotApplicable``."""
    return {
        "applies_to": functional_refs,
        "base_pipeline": {"status": "NOT_APPLICABLE"},
        "steps": [
            {
                "kind": "nonsteadystate_removal",
                "n_nonsteadystate_discarded": _missing_pf("n_nonsteadystate_discarded"),
            },
        ],
    }


def _replication_spec_payload(
    acquisitions: list[dict[str, Any]],
    site: str | None = None,
) -> dict[str, Any]:
    # Auto-generate a minimal Preprocessing covering every functional (bold)
    # acquisition so the new ReplicationSpec partition rule is satisfied.
    functional_refs = [
        {"suffix": a["suffix"], "entities": a.get("entities", {}) or {}}
        for a in acquisitions
        if a.get("suffix") == "bold"
    ]
    preprocessing = [_minimal_preprocessing_payload(functional_refs)] if functional_refs else []
    return {
        "dataset": {"name": "TEST", "site": site},
        "acquisitions": acquisitions,
        "preprocessing": preprocessing,
        "first_level": {},
        "group_level": {},
        "thresholding": {},
    }


# ---------------------------------------------------------------------------
# 1. Multi-value Literal discriminator dispatch (and round-trip)
# ---------------------------------------------------------------------------
_ACQUISITION_ADAPTER: TypeAdapter[Acquisition] = TypeAdapter(Acquisition)


@pytest.mark.parametrize("suffix", ["T1w", "T2w"])
def test_anatomical_suffixes_dispatch_to_anatomical(suffix: str) -> None:
    parsed = _ACQUISITION_ADAPTER.validate_python(_anatomical_payload(suffix=suffix))
    assert isinstance(parsed, AnatomicalAcquisition)
    assert parsed.suffix == suffix


@pytest.mark.parametrize("suffix", ["epi", "phasediff", "magnitude1", "magnitude2", "fieldmap"])
def test_fieldmap_suffixes_dispatch_to_fieldmap(suffix: str) -> None:
    parsed = _ACQUISITION_ADAPTER.validate_python(_fieldmap_payload(suffix=suffix))
    assert isinstance(parsed, FieldmapAcquisition)
    assert parsed.suffix == suffix


def test_bold_dispatches_to_functional() -> None:
    parsed = _ACQUISITION_ADAPTER.validate_python(_functional_payload())
    assert isinstance(parsed, FunctionalAcquisition)
    assert parsed.suffix == "bold"


def test_unknown_suffix_rejected() -> None:
    payload = _anatomical_payload()
    payload["suffix"] = "NOTREAL"
    with pytest.raises(ValidationError) as excinfo:
        _ACQUISITION_ADAPTER.validate_python(payload)
    msg = str(excinfo.value).lower()
    assert "discriminator" in msg or "tag" in msg or "suffix" in msg


# ---------------------------------------------------------------------------
# 2. JSON-schema export of the inheritance-based discriminated union
# ---------------------------------------------------------------------------
def test_acquisition_union_json_schema_export() -> None:
    schema = _ACQUISITION_ADAPTER.json_schema()
    # Each arm class should be reachable in $defs (or at top level for direct ones).
    blob = repr(schema)
    for cls_name in (
        "FunctionalAcquisition",
        "AnatomicalAcquisition",
        "FieldmapAcquisition",
    ):
        assert cls_name in blob, f"{cls_name} missing from generated schema"


@pytest.mark.parametrize(
    "payload_builder",
    [
        _functional_payload,
        lambda: _anatomical_payload("T1w"),
        lambda: _anatomical_payload("T2w"),
        _fieldmap_payload,
    ],
)
def test_each_arm_round_trips_via_union(payload_builder: Any) -> None:
    payload = payload_builder()
    acq = _ACQUISITION_ADAPTER.validate_python(payload)
    js = _ACQUISITION_ADAPTER.dump_json(acq)
    again = _ACQUISITION_ADAPTER.validate_json(js)
    assert acq == again


# ---------------------------------------------------------------------------
# 3. echo_time_ms shape per arm
# ---------------------------------------------------------------------------
def _echo_pf(value: Any) -> dict[str, Any]:
    return {
        "field_id": "echo_time_ms",
        "extraction": {
            "status": "EXTRACTED",
            "value": value,
            "spans": [{"start": 0, "end": 9, "text": "TE = 30ms", "section": "Methods"}],
            "confidence": 0.9,
        },
        "inference": {"status": "NOT_APPLICABLE"},
    }


def test_functional_echo_time_accepts_list_rejects_scalar() -> None:
    ok = _functional_payload()
    ok["echo_time_ms"] = _echo_pf([30.0])
    FunctionalAcquisition.model_validate(ok)

    bad = _functional_payload()
    bad["echo_time_ms"] = _echo_pf(30.0)  # scalar
    with pytest.raises(ValidationError):
        FunctionalAcquisition.model_validate(bad)


def test_anatomical_echo_time_accepts_scalar_rejects_list() -> None:
    ok = _anatomical_payload()
    ok["echo_time_ms"] = _echo_pf(2.34)
    AnatomicalAcquisition.model_validate(ok)

    bad = _anatomical_payload()
    bad["echo_time_ms"] = _echo_pf([2.34])  # list
    with pytest.raises(ValidationError):
        AnatomicalAcquisition.model_validate(bad)


# ---------------------------------------------------------------------------
# 4. Per-arm registry bijection
# ---------------------------------------------------------------------------
def test_functional_bijection_raises_on_missing_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(core.FUNCTIONAL_FIELD_META, "shimming")
    with pytest.raises(RuntimeError, match="registry/field mismatch"):
        _check_arm_bijection(FunctionalAcquisition, core.FUNCTIONAL_FIELD_META)


def test_anatomical_bijection_raises_on_missing_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(core.ANATOMICAL_FIELD_META, "echo_time_ms")
    with pytest.raises(RuntimeError, match="registry/field mismatch"):
        _check_arm_bijection(AnatomicalAcquisition, core.ANATOMICAL_FIELD_META)


def test_fieldmap_bijection_raises_on_missing_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(core.FIELDMAP_FIELD_META, "total_readout_time_s")
    with pytest.raises(RuntimeError, match="registry/field mismatch"):
        _check_arm_bijection(FieldmapAcquisition, core.FIELDMAP_FIELD_META)


def test_all_arms_bijective_on_unmodified_state() -> None:
    _check_arm_bijection(FunctionalAcquisition, core.FUNCTIONAL_FIELD_META)
    _check_arm_bijection(AnatomicalAcquisition, core.ANATOMICAL_FIELD_META)
    _check_arm_bijection(FieldmapAcquisition, core.FIELDMAP_FIELD_META)


# ---------------------------------------------------------------------------
# 5. inference_applicable invariant per arm
# ---------------------------------------------------------------------------
def _inferred_default_pf(field_id: str, value: Any) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {
            "status": "INFERRED_DEFAULT",
            "value": value,
            "basis": {"basis_type": "lab_prior", "lab_id": "some_lab", "note": None},
            "confidence": 0.4,
            "alternative_inferences": [],
        },
    }


def test_inferred_default_rejected_on_receive_coil_anatomical() -> None:
    payload = _anatomical_payload()
    payload["receive_coil"] = _inferred_default_pf("receive_coil", "32ch_head")
    with pytest.raises(ValidationError) as excinfo:
        AnatomicalAcquisition.model_validate(payload)
    assert "inference_applicable=False" in str(excinfo.value)
    assert "receive_coil" in str(excinfo.value)


def test_inferred_default_accepted_on_multiband_factor_functional() -> None:
    payload = _functional_payload()
    payload["multiband_factor"] = {
        "field_id": "multiband_factor",
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": ["multiband"],
            "sections_searched": [],
        },
        "inference": {
            "status": "INFERRED_DEFAULT",
            "value": 1,
            "basis": {
                "basis_type": "field_convention",
                "source": "BIDS Multiband ∅ → 1",
                "note": None,
            },
            "confidence": 0.35,
            "alternative_inferences": [],
        },
    }
    fa = FunctionalAcquisition.model_validate(payload)
    assert fa.multiband_factor.inference.status == "INFERRED_DEFAULT"


def _derived_inferred_pf(field_id: str, value: Any, source_field_ids: list[str]) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {
            "status": "INFERRED_DEFAULT",
            "value": value,
            "basis": {
                "basis_type": "derived",
                "source_field_ids": source_field_ids,
                "note": "voxel/matrix/fov triple — any from the other two",
            },
            "confidence": 0.6,
            "alternative_inferences": [],
        },
    }


def test_voxel_size_mm_accepts_inferred_default_derived_in_functional() -> None:
    """Bassett-style: FOV + matrix reported, voxel derived as fov / matrix."""
    payload = _functional_payload()
    payload["voxel_size_mm"] = _derived_inferred_pf(
        "voxel_size_mm",
        [3.0, 3.0, 3.0],
        source_field_ids=["fov_mm", "matrix_size"],
    )
    fa = FunctionalAcquisition.model_validate(payload)
    assert fa.voxel_size_mm.inference.status == "INFERRED_DEFAULT"


def test_matrix_size_accepts_inferred_default_derived_in_anatomical() -> None:
    """Schwartz-style reverse: voxel + FOV reported, matrix derived as fov / voxel."""
    payload = _anatomical_payload()
    payload["matrix_size"] = _derived_inferred_pf(
        "matrix_size",
        [64, 64, 36],
        source_field_ids=["fov_mm", "voxel_size_mm"],
    )
    aa = AnatomicalAcquisition.model_validate(payload)
    assert aa.matrix_size.inference.status == "INFERRED_DEFAULT"


def test_field_id_must_match_attribute_name_functional() -> None:
    payload = _functional_payload()
    payload["repetition_time_s"]["field_id"] = "wrong_name"
    with pytest.raises(ValidationError) as excinfo:
        FunctionalAcquisition.model_validate(payload)
    assert "field_id mismatch" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 6. Collection invariants on ReplicationSpec
# ---------------------------------------------------------------------------
def test_duplicate_suffix_entities_rejected() -> None:
    payload = _replication_spec_payload(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),
            _functional_payload(entities={"task": "rest"}),  # duplicate
        ],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "duplicate acquisition" in str(excinfo.value)


def test_dangling_intended_for_rejected() -> None:
    fmap = _fieldmap_payload(
        intended_for=[{"suffix": "bold", "entities": {"task": "nback"}}],
    )
    payload = _replication_spec_payload(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),  # different task
            fmap,
        ],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "intended_for" in str(excinfo.value)


def test_valid_intended_for_accepted() -> None:
    fmap = _fieldmap_payload(
        entities={"dir": "PA"},
        intended_for=[{"suffix": "bold", "entities": {"task": "rest"}}],
    )
    payload = _replication_spec_payload(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),
            fmap,
        ],
    )
    spec = ReplicationSpec.model_validate(payload)
    assert len(spec.acquisitions) == 2


def test_acquisitions_min_length_enforced() -> None:
    payload = _replication_spec_payload(acquisitions=[])
    with pytest.raises(ValidationError):
        ReplicationSpec.model_validate(payload)


def test_intended_for_resolves_across_arms_to_anatomical() -> None:
    """intended_for resolution accepts any present acquisition, including
    anatomicals — HCP phasediff fieldmaps are intended_for T1w/T2w."""
    fmap = _fieldmap_payload(
        suffix="phasediff",
        intended_for=[
            {"suffix": "T1w", "entities": {}},
            {"suffix": "T2w", "entities": {}},
        ],
    )
    payload = _replication_spec_payload(
        acquisitions=[
            _anatomical_payload("T1w"),
            _anatomical_payload("T2w"),
            fmap,
        ],
    )
    spec = ReplicationSpec.model_validate(payload)
    assert len(spec.acquisitions) == 3


def test_intended_for_to_absent_target_rejected() -> None:
    """A reference to a (suffix, entities) not present in the collection
    is rejected even when the same suffix exists with different entities."""
    fmap = _fieldmap_payload(
        suffix="phasediff",
        intended_for=[{"suffix": "T2w", "entities": {}}],  # T2w not in collection
    )
    payload = _replication_spec_payload(
        acquisitions=[
            _anatomical_payload("T1w"),  # only T1w present
            fmap,
        ],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "intended_for" in str(excinfo.value)
    assert "T2w" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 7. bids_stem helper
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("suffix", "entities_kwargs", "expected"),
    [
        ("T1w", {}, "T1w"),
        ("bold", {"task": "rest"}, "task-rest_bold"),
        ("bold", {"task": "rest", "dir": "LR"}, "task-rest_dir-LR_bold"),
        ("epi", {"dir": "PA"}, "dir-PA_epi"),
        (
            "bold",
            {"task": "nback", "acq": "mb", "dir": "AP", "run": 2},
            "task-nback_acq-mb_dir-AP_run-2_bold",
        ),
    ],
)
def test_bids_stem(suffix: str, entities_kwargs: dict[str, Any], expected: str) -> None:
    assert bids_stem(suffix, AcquisitionEntities(**entities_kwargs)) == expected


# ---------------------------------------------------------------------------
# 8. Sanity: end-to-end build of a real ReplicationSpec in code
# ---------------------------------------------------------------------------
def test_smoke_construct_replication_spec_in_code() -> None:
    """Belt-and-suspenders: round-trip a hand-built ReplicationSpec carrying
    one Anatomical + one Functional + one Fieldmap-with-intended_for."""
    spec_payload = _replication_spec_payload(
        acquisitions=[
            _anatomical_payload("T1w"),
            _functional_payload(entities={"task": "rest"}),
            _fieldmap_payload(
                entities={"dir": "PA"},
                intended_for=[{"suffix": "bold", "entities": {"task": "rest"}}],
            ),
        ],
        site="LabA",
    )
    spec = ReplicationSpec.model_validate(spec_payload)
    js = spec.model_dump_json()
    again = ReplicationSpec.model_validate_json(js)
    assert spec == again
    # Stubs are reachable
    assert isinstance(spec.preprocessing, list)
    assert all(isinstance(p, Preprocessing) for p in spec.preprocessing)
    assert isinstance(spec.first_level, FirstLevelModel)
    assert isinstance(spec.group_level, GroupLevelModel)
    assert isinstance(spec.thresholding, Thresholding)
