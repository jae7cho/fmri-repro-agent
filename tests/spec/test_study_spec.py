"""Tests for the v0.1.0 StudySpec root + example round-trip + schema export."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from fmri_repro.spec.v0_1_0 import FunctionalAcquisition, StudySpec

# export_schema.py emits the CURRENT versioned root; import it to derive the
# exported filename (the 0.1.0 StudySpec above stays for the frozen example).
from fmri_repro.spec.v0_2_0 import StudySpec as CurrentStudySpec

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = REPO_ROOT / "examples" / "spec.json"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_schema.py"


def _example_payload() -> dict[str, object]:
    """A valid StudySpec payload sourced from examples/spec.json."""
    payload: dict[str, object] = json.loads(EXAMPLE_PATH.read_text())
    return payload


# ---------------------------------------------------------------------------
# schema_version is pinned via Literal["0.1.0"] on StudySpec
# ---------------------------------------------------------------------------
def test_schema_version_is_pinned() -> None:
    payload = _example_payload()
    payload["schema_version"] = "0.2.0"
    with pytest.raises(ValidationError) as excinfo:
        StudySpec.model_validate(payload)
    assert "schema_version" in str(excinfo.value)


def test_schema_version_default_is_0_1_0() -> None:
    payload = _example_payload()
    del payload["schema_version"]
    study = StudySpec.model_validate(payload)
    assert study.schema_version == "0.1.0"


# ---------------------------------------------------------------------------
# specs: min_length=1 enforced
# ---------------------------------------------------------------------------
def test_specs_min_length_one_enforced() -> None:
    payload = _example_payload()
    payload["specs"] = []
    with pytest.raises(ValidationError) as excinfo:
        StudySpec.model_validate(payload)
    msg = str(excinfo.value)
    assert "specs" in msg
    assert "at least 1" in msg or "min_length" in msg or "too_short" in msg


# ---------------------------------------------------------------------------
# Every ReplicationSpec carries a populated DatasetRef
# ---------------------------------------------------------------------------
def test_each_spec_has_dataset_ref() -> None:
    study = StudySpec.model_validate_json(EXAMPLE_PATH.read_text())
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
    study = StudySpec.model_validate_json(EXAMPLE_PATH.read_text())
    assert len(study.specs) == 2
    accessions = {spec.dataset.accession for spec in study.specs}
    assert accessions == {"HNU_1", "ds000224"}


# ---------------------------------------------------------------------------
# examples/spec.json validates and round-trips; DEFERRED_TO_CITATION is present
# ---------------------------------------------------------------------------
def test_example_validates_and_round_trips() -> None:
    raw = EXAMPLE_PATH.read_text()
    study = StudySpec.model_validate_json(raw)
    dumped = study.model_dump_json()
    study_again = StudySpec.model_validate_json(dumped)
    assert study == study_again


def test_example_exercises_deferred_to_citation_arm() -> None:
    study = StudySpec.model_validate_json(EXAMPLE_PATH.read_text())
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
    study = StudySpec.model_validate_json(EXAMPLE_PATH.read_text())
    sites = [s.dataset.site for s in study.specs]
    assert any(site is not None for site in sites)


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

    # schema_version is pinned to "0.2.0" (Literal exports as const or enum).
    # Concrete literal (NOT derived) so an accidental future bump fails this test.
    sv = props["schema_version"]
    assert sv.get("const") == "0.2.0" or sv.get("enum") == ["0.2.0"]

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
