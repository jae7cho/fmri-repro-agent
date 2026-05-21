"""Tests for the v0.1.0 ReplicationSpec root + example round-trip + schema export."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from fmri_repro.spec.v0_1_0 import ReplicationSpec

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = REPO_ROOT / "examples" / "spec.json"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_schema.py"


def _example_payload() -> dict[str, object]:
    """A minimal valid ReplicationSpec payload sourced from examples/spec.json."""
    payload: dict[str, object] = json.loads(EXAMPLE_PATH.read_text())
    return payload


# ---------------------------------------------------------------------------
# schema_version is pinned via Literal["0.1.0"]
# ---------------------------------------------------------------------------
def test_schema_version_is_pinned() -> None:
    payload = _example_payload()
    payload["schema_version"] = "0.2.0"
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "schema_version" in str(excinfo.value)


def test_schema_version_default_is_0_1_0() -> None:
    payload = _example_payload()
    del payload["schema_version"]
    spec = ReplicationSpec.model_validate(payload)
    assert spec.schema_version == "0.1.0"


# ---------------------------------------------------------------------------
# examples/spec.json validates and round-trips
# ---------------------------------------------------------------------------
def test_example_validates_and_round_trips() -> None:
    raw = EXAMPLE_PATH.read_text()
    spec = ReplicationSpec.model_validate_json(raw)
    # Dump back and re-validate
    dumped = spec.model_dump_json()
    spec_again = ReplicationSpec.model_validate_json(dumped)
    assert spec == spec_again


# ---------------------------------------------------------------------------
# export_schema.py writes a non-empty schema file with expected $defs
# ---------------------------------------------------------------------------
def test_export_schema_writes_expected_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # Ensure scripts/ is importable as a path, but use runpy to invoke as a module.
    sys.path.insert(0, str(EXPORT_SCRIPT.parent))
    try:
        result = runpy.run_path(str(EXPORT_SCRIPT), run_name="__main__")
    finally:
        sys.path.remove(str(EXPORT_SCRIPT.parent))

    out_path = tmp_path / "schema" / "replication_spec-0.1.0.schema.json"
    assert out_path.exists(), f"export_schema did not produce {out_path}"
    schema = json.loads(out_path.read_text())
    assert schema, "schema file is empty"

    # Top-level: ReplicationSpec properties cover all seven fields
    assert "properties" in schema
    props = schema["properties"]
    for field in (
        "schema_version",
        "run",
        "acquisition",
        "preprocessing",
        "first_level",
        "group_level",
        "thresholding",
    ):
        assert field in props, f"missing top-level field {field!r}"

    # schema_version is pinned to "0.1.0" (Literal exports as const or enum)
    sv = props["schema_version"]
    assert sv.get("const") == "0.1.0" or sv.get("enum") == ["0.1.0"]

    # $defs should contain the inference arms and the discriminated extraction arms
    assert "$defs" in schema
    def_names = "\n".join(schema["$defs"].keys())
    assert "MissingFromPaper" in def_names
    assert "LeftMissing" in def_names
    assert "NotApplicable" in def_names
    assert "Extracted" in def_names
    assert "InferredDefault" in def_names

    # runpy returns the module globals dict — make sure main() ran without raising.
    assert "main" in result
