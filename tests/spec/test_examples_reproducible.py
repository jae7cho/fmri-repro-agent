"""Reproducibility lock for the committed example artifacts.

Each committed example under ``examples/`` must be byte-identical to what its generator
script emits. This single assertion covers two failure modes at once:

  * the generator RUNS (it regressed to raising at build time — a required
    ``NuisanceRegression`` field was dropped from the construction), and
  * the committed artifact is REPRODUCIBLE from it (the two drifted independently —
    the examples were last genuinely generated mid-0.3.0 development and thereafter
    only hand-patched, so they no longer matched their own generators).

Byte-identity is the right test only because the generators are deterministic (a fixed
``_FIXED_CREATED_AT`` timestamp, no ``datetime.now()``); regenerate the example (or fix
the generator) whenever this fails, rather than loosening the assertion.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

# (generator script, the committed example it must reproduce byte-for-byte)
_CASES = [
    ("make_example_spec.py", "spec.json"),
    ("make_glasser_fieldmap_example.py", "hcp_glasser_fieldmaps.json"),
]


@pytest.mark.parametrize(("script_name", "example_name"), _CASES)
def test_committed_example_is_reproducible_from_generator(
    script_name: str,
    example_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    committed = (REPO_ROOT / "examples" / example_name).read_bytes()

    # Run the generator in an isolated CWD so it writes tmp_path/examples/<name> and never
    # touches the repo's committed copy (the scripts write Path("examples")/<name> relative
    # to CWD).
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir(exist_ok=True)
    script = SCRIPTS / script_name
    sys.path.insert(0, str(script.parent))
    try:
        runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.path.remove(str(script.parent))

    produced = (tmp_path / "examples" / example_name).read_bytes()
    assert produced == committed, (
        f"{script_name} output is not byte-identical to committed examples/{example_name}. "
        "Regenerate the example from its generator (or fix the generator) so they match."
    )
