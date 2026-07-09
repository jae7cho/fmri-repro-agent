"""Tests for the current StudySpec root + example round-trip + schema export.

The committed example (``examples/spec.json``) is a CURRENT (0.3.0) document and is
validated with the current root. A coherent v0.1.0 document is no longer constructible
(nested ``Preprocessing.schema_version`` is ``Literal["0.3.0"]``), so version pinning is
asserted as a constant on each root, not by building a document; the genuine v0.1.0
artifact lives frozen under ``examples/frozen/``.
"""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from fmri_repro.spec.core import FunctionalAcquisition
from fmri_repro.spec.v0_3_0 import StudySpec as CurrentStudySpec

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = REPO_ROOT / "examples" / "spec.json"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_schema.py"


def _example_payload() -> dict[str, object]:
    """A valid StudySpec payload sourced from examples/spec.json."""
    payload: dict[str, object] = json.loads(EXAMPLE_PATH.read_text())
    return payload


# ---------------------------------------------------------------------------
# schema_version is pinned per root — asserted as a constant, not via a document.
# A coherent v0.1.0/v0.2.0 document is no longer constructible (see module docstring).
# ---------------------------------------------------------------------------
def test_each_root_pins_its_schema_version_constant() -> None:
    # v0.1.0 / v0.2.0 are demoted to version constants (no StudySpec root to misuse); only
    # the current root is a live class.
    from fmri_repro.spec import v0_1_0, v0_2_0

    assert v0_1_0.SCHEMA_VERSION == "0.1.0"
    assert v0_2_0.SCHEMA_VERSION == "0.2.0"
    assert not hasattr(v0_2_0, "StudySpec")  # demoted: the footgun root is gone
    assert CurrentStudySpec.model_fields["schema_version"].default == "0.3.0"


def test_current_root_rejects_wrong_schema_version() -> None:
    payload = _example_payload()
    payload["schema_version"] = "0.2.0"
    with pytest.raises(ValidationError) as excinfo:
        CurrentStudySpec.model_validate(payload)
    assert "schema_version" in str(excinfo.value)


# ---------------------------------------------------------------------------
# specs: min_length=1 enforced
# ---------------------------------------------------------------------------
def test_specs_min_length_one_enforced() -> None:
    payload = _example_payload()
    payload["specs"] = []
    with pytest.raises(ValidationError) as excinfo:
        CurrentStudySpec.model_validate(payload)
    msg = str(excinfo.value)
    assert "specs" in msg
    assert "at least 1" in msg or "min_length" in msg or "too_short" in msg


# ---------------------------------------------------------------------------
# Every ReplicationSpec carries a populated DatasetRef
# ---------------------------------------------------------------------------
def test_each_spec_has_dataset_ref() -> None:
    study = CurrentStudySpec.model_validate_json(EXAMPLE_PATH.read_text())
    assert len(study.specs) >= 1
    for spec in study.specs:
        assert spec.dataset.name  # non-empty
    # The committed example carries the HNU and MSC datasets
    names = {spec.dataset.name for spec in study.specs}
    assert names == {"HNU1", "MSC"}


# ---------------------------------------------------------------------------
# Multiple specs are supported (committed example has two)
# ---------------------------------------------------------------------------
def test_multiple_specs_supported() -> None:
    study = CurrentStudySpec.model_validate_json(EXAMPLE_PATH.read_text())
    assert len(study.specs) == 2
    accessions = {spec.dataset.accession for spec in study.specs}
    assert accessions == {"HNU_1", "ds000224"}


# ---------------------------------------------------------------------------
# examples/spec.json validates and round-trips; DEFERRED_TO_CITATION is present
# ---------------------------------------------------------------------------
def test_example_validates_and_round_trips() -> None:
    raw = EXAMPLE_PATH.read_text()
    study = CurrentStudySpec.model_validate_json(raw)
    dumped = study.model_dump_json()
    study_again = CurrentStudySpec.model_validate_json(dumped)
    assert study == study_again


def test_example_exercises_deferred_to_citation_arm() -> None:
    study = CurrentStudySpec.model_validate_json(EXAMPLE_PATH.read_text())
    # Find the (sole) functional acquisition that defers prospective_motion_correction.
    deferred_pfs = [
        a.prospective_motion_correction
        for s in study.specs
        for a in s.acquisitions
        if isinstance(a, FunctionalAcquisition)
        and a.prospective_motion_correction.extraction.status == "DEFERRED_TO_CITATION"
    ]
    assert len(deferred_pfs) == 1
    pmc = deferred_pfs[0]
    assert pmc.extraction.status == "DEFERRED_TO_CITATION"
    assert pmc.extraction.deferrals[0].ref == "Gordon 2017"
    assert pmc.inference.status == "LEFT_MISSING"


def test_example_carries_site_on_at_least_one_spec() -> None:
    """DatasetRef.site is exercised by the committed example."""
    study = CurrentStudySpec.model_validate_json(EXAMPLE_PATH.read_text())
    sites = [s.dataset.site for s in study.specs]
    assert any(site is not None for site in sites)


# ---------------------------------------------------------------------------
# v0.3.0 StudySpec cross-validator: pinned schema_version == nested Preprocessing stamp
# ---------------------------------------------------------------------------
def test_current_studyspec_accepts_matching_nested_stamp() -> None:
    # The example carries the v0.3.0 preprocessing fields; labeling it 0.3.0 and validating
    # under the current root passes the cross-validator (top version == nested stamp, both
    # defaulting to 0.3.0).
    payload = _example_payload()
    payload["schema_version"] = "0.3.0"
    study = CurrentStudySpec.model_validate(payload)
    assert study.schema_version == "0.3.0"
    for spec in study.specs:
        for prep in spec.preprocessing:
            assert prep.schema_version == "0.3.0"


def test_current_studyspec_rejects_mismatched_nested_stamp() -> None:
    # A nested Preprocessing stamp that disagrees with the current version is rejected. Today
    # the first line of defense is Preprocessing.schema_version being a Literal["0.3.0"] (so a
    # "0.2.0" stamp fails at the field), with the StudySpec cross-validator as the backstop for
    # a future bump that desyncs the two Literals.
    payload = _example_payload()
    payload["schema_version"] = "0.3.0"
    prep0 = payload["specs"][0]["preprocessing"][0]  # type: ignore[index]
    prep0["schema_version"] = "0.2.0"
    with pytest.raises(ValidationError, match="schema_version"):
        CurrentStudySpec.model_validate(payload)


# ---------------------------------------------------------------------------
# export_schema.py writes a non-empty schema file with expected $defs
# ---------------------------------------------------------------------------
def test_export_schema_writes_expected_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(EXPORT_SCRIPT.parent))
    try:
        result = runpy.run_path(str(EXPORT_SCRIPT), run_name="__main__")
    finally:
        sys.path.remove(str(EXPORT_SCRIPT.parent))

    # Filename is derived from the model's declared version (parametric — a future
    # minor won't need editing here); the version const below stays a concrete
    # literal so an unintended bump is caught.
    version = CurrentStudySpec.model_fields["schema_version"].default
    out_path = tmp_path / "schema" / f"study_spec-{version}.schema.json"
    assert out_path.exists(), f"export_schema did not produce {out_path}"
    schema = json.loads(out_path.read_text())
    assert schema, "schema file is empty"

    # Top-level: StudySpec exposes the four expected fields
    assert "properties" in schema
    props = schema["properties"]
    for field in ("schema_version", "run", "specs", "study_analysis"):
        assert field in props, f"missing top-level field {field!r}"

    # schema_version is pinned to "0.3.0" (Literal exports as const or enum).
    # Concrete literal (NOT derived) so an accidental future bump fails this test.
    sv = props["schema_version"]
    assert sv.get("const") == "0.3.0" or sv.get("enum") == ["0.3.0"]

    # $defs should contain ReplicationSpec, DatasetRef, StudyAnalysis, all three
    # extraction arms, and all three inference arms.
    assert "$defs" in schema
    def_names = "\n".join(schema["$defs"].keys())
    for name in (
        "ReplicationSpec",
        "DatasetRef",
        "StudyAnalysis",
        "AcquisitionEntities",
        "AcquisitionRef",
        "FunctionalAcquisition",
        "AnatomicalAcquisition",
        "FieldmapAcquisition",
        "MissingFromPaper",
        "DeferredToCitation",
        "LeftMissing",
        "NotApplicable",
        "Extracted",
        "InferredDefault",
    ):
        assert name in def_names, f"{name!r} not in $defs"

    assert "main" in result
