"""v0.3.0: _assemble emits the anatomical-target steps fully untargeted, and the
protocol emitter renders them generically (no emitter change)."""

from __future__ import annotations

from fmri_repro.spec.provenance import MissingFromPaper

from extractor_mvp.extractor import _assemble, _missing_pf
from extractor_mvp.render import to_protocol

# pf dict keys are the extractor's names; each value's field_id is the STEP attribute name.
_PF_FIELD_IDS = {
    "target_space": "target_space",
    "resolution_mm": "resolution_mm",
    "target_surface": "target_surface",
    "surface_registration": "surface_registration",
    "intensity_convention": "convention",
    "intensity_value": "value",
    "temporal_standardization_method": "method",
}


def _assembled():
    pf = {k: _missing_pf(fid, str, "not_stated_in_text") for k, fid in _PF_FIELD_IDS.items()}
    return _assemble(pf, MissingFromPaper(searched_terms=[], sections_searched=["M"]))


def test_assemble_includes_anatomical_steps_before_spatial():
    prep = _assembled()
    kinds = [s.kind for s in prep.steps]
    assert kinds[:3] == ["brain_extraction", "segmentation", "spatial_normalization"]


def test_assemble_new_steps_fields_are_untargeted():
    prep = _assembled()
    by_kind = {s.kind: s for s in prep.steps}
    # brain_extraction + segmentation (v0.3.0 anatomical) and nuisance_regression (emitted as
    # a COBIDAS-mandatory decision point) all present with every field untargeted.
    for kind in ("brain_extraction", "segmentation", "nuisance_regression"):
        step = by_kind[kind]
        for name in type(step).model_fields:
            if name == "kind":
                continue
            field = getattr(step, name)
            assert field.extraction.status == "MISSING_FROM_PAPER"
            assert field.inference.reason == "not_targeted_by_mvp"


def test_protocol_renders_new_steps_generically():
    # No emitter change: to_protocol walks steps generically, so the new steps render
    # with their cobidas_row group tags and the "not assessed by current extractor" line.
    out = to_protocol(_assembled())
    for kind in ("brain_extraction", "segmentation", "nuisance_regression"):
        assert kind in out
    # 8 pre-existing untargeted + 4 anatomical (brain_extraction 2, segmentation 2)
    # + 7 nuisance_regression = 19.
    assert out.count("not assessed by current extractor") == 19
