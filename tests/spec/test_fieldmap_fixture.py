"""Verify ``examples/hcp_glasser_fieldmaps.json`` — the HCP S1200 / Glasser
2013 reference fixture — exercises both fieldmap mechanisms and resolves
``intended_for`` across all three acquisition arms.
"""

from __future__ import annotations

from pathlib import Path

from fmri_repro.spec.core import (
    AnatomicalAcquisition,
    FieldmapAcquisition,
    FunctionalAcquisition,
)
from fmri_repro.spec.v0_3_0 import StudySpec  # current root; the fixture is a 0.3.0 document

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "examples" / "hcp_glasser_fieldmaps.json"


def _load() -> StudySpec:
    study: StudySpec = StudySpec.model_validate_json(FIXTURE_PATH.read_text())
    return study


def test_fixture_validates_and_has_single_spec() -> None:
    study = _load()
    assert len(study.specs) == 1
    spec = study.specs[0]
    assert spec.dataset.name == "HCP S1200 (Glasser 2013 pipelines)"
    assert spec.dataset.site is None
    assert len(spec.acquisitions) == 7


def test_fixture_has_both_fieldmap_mechanisms() -> None:
    """An ``epi`` reverse-PE fieldmap AND the phasediff + magnitude1 + magnitude2 triple."""
    spec = _load().specs[0]
    fmap_suffixes = {a.suffix for a in spec.acquisitions if isinstance(a, FieldmapAcquisition)}
    assert "epi" in fmap_suffixes
    assert {"phasediff", "magnitude1", "magnitude2"}.issubset(fmap_suffixes)


def test_epi_fieldmap_intended_for_resolves_to_bold() -> None:
    spec = _load().specs[0]
    epi = next(
        a for a in spec.acquisitions if isinstance(a, FieldmapAcquisition) and a.suffix == "epi"
    )
    bold = next(
        a for a in spec.acquisitions if isinstance(a, FunctionalAcquisition) and a.suffix == "bold"
    )
    # exactly one intended target, resolving to the bold
    assert len(epi.intended_for) == 1
    target = epi.intended_for[0]
    assert target.suffix == "bold"
    assert target.entities.task == bold.entities.task == "rest"
    assert target.entities.dir == bold.entities.dir == "LR"


def test_phasediff_fieldmap_intended_for_resolves_to_t1w_and_t2w() -> None:
    spec = _load().specs[0]
    phasediff = next(
        a
        for a in spec.acquisitions
        if isinstance(a, FieldmapAcquisition) and a.suffix == "phasediff"
    )
    anatomicals = {a.suffix for a in spec.acquisitions if isinstance(a, AnatomicalAcquisition)}
    assert anatomicals == {"T1w", "T2w"}
    intended_suffixes = {ref.suffix for ref in phasediff.intended_for}
    assert intended_suffixes == {"T1w", "T2w"}
    # entities default to empty for the anatomicals — refs match exactly
    for ref in phasediff.intended_for:
        assert ref.entities.task is None
        assert ref.entities.dir is None
        assert ref.entities.run is None
        assert ref.entities.acq is None


def test_suffix_entities_uniqueness_holds_across_seven_acquisitions() -> None:
    spec = _load().specs[0]
    keys = [
        (a.suffix, a.entities.task, a.entities.run, a.entities.dir, a.entities.acq)
        for a in spec.acquisitions
    ]
    assert len(set(keys)) == len(keys) == 7


def test_bold_repetition_time_and_echo_time_are_deferred_to_citation() -> None:
    """Sanity: the Glasser fixture exercises DEFERRED_TO_CITATION on the
    BOLD TR + multi-echo TE (paper cites Smith 2013 / Ugurbil 2013)."""
    spec = _load().specs[0]
    bold = next(
        a for a in spec.acquisitions if isinstance(a, FunctionalAcquisition) and a.suffix == "bold"
    )
    assert bold.repetition_time_s.extraction.status == "DEFERRED_TO_CITATION"
    assert bold.echo_time_ms.extraction.status == "DEFERRED_TO_CITATION"
