"""v0.3.0: _assemble emits the anatomical-target steps fully untargeted, and the
protocol emitter renders them generically (no emitter change)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from extractor_mvp.render import to_protocol

if TYPE_CHECKING:
    from fmri_repro.spec.preprocessing import Preprocessing

# The builder and its pf map now live in tests/conftest.py as the `assembled` fixture, because
# test_batch.py needs it too and test modules must not import each other.


def test_assemble_includes_anatomical_steps_before_spatial(assembled: Preprocessing):
    prep = assembled
    kinds = [s.kind for s in prep.steps]
    assert kinds[:3] == ["brain_extraction", "segmentation", "spatial_normalization"]


def test_assemble_step_list_unchanged(assembled: Preprocessing):
    # The COBIDAS coverage work is emitter-side only: _assemble still emits exactly these
    # 7 kinds in this order. If this changes, the coverage denominator reasoning is affected.
    assert [s.kind for s in assembled.steps] == [
        "brain_extraction",
        "segmentation",
        "spatial_normalization",
        "surface_projection",
        "nuisance_regression",
        "intensity_normalization",
        "temporal_standardization",
    ]


def test_assemble_new_steps_fields_are_untargeted(assembled: Preprocessing):
    prep = assembled
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


def test_protocol_renders_new_steps_generically(assembled: Preprocessing):
    # No emitter change: to_protocol walks steps generically, so the new steps render
    # with their cobidas_row group tags and the "not examined by the extractor" line.
    out = to_protocol(assembled)
    for kind in ("brain_extraction", "segmentation", "nuisance_regression"):
        assert kind in out
    # Field-level callouts use "not examined by the extractor"; the COBIDAS section uses
    # distinct row-level wording ("no fields assessed ..."), so a plain global count is exact.
    # 8 pre-existing untargeted + 4 anatomical (brain_extraction 2, segmentation 2)
    # + 7 nuisance_regression = 19.
    assert out.count("not examined by the extractor") == 19
