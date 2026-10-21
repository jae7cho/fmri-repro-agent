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
    # R7a, 2026-10-19: motion_correction is emitted between segmentation and spatial_normalization
    # (ruling C turned the row on). What this pins is the ORDER, which is the spec's own step order.
    assert kinds[:4] == [
        "brain_extraction",
        "segmentation",
        "motion_correction",
        "spatial_normalization",
    ]


def test_assemble_step_list_unchanged(assembled: Preprocessing):
    # _assemble emits exactly these kinds in this order. If this changes, the coverage
    # denominator reasoning is affected.
    #
    # 7 -> 8, 2026-10-19: motion_correction joins, because ruling C turns the motion row on. This
    # is the first change to this list since the COBIDAS coverage work, which was emitter-side only.
    assert [s.kind for s in assembled.steps] == [
        "brain_extraction",
        "segmentation",
        "motion_correction",
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
    #
    # 19 -> 29, 2026-10-19. MotionCorrection has TEN data fields besides ``kind``: method,
    # reference_scan, similarity_metric, interpolation, transforms_combined, nonrigid,
    # transform_type, fieldmap_unwarping, unwarping_method, slice_to_volume. In THIS path all ten
    # are untargeted, because ``_build_assembled`` calls ``_assemble`` with no motion field — the
    # fixture makes no model call. 19 + 10 = 29.
    #
    # A REAL single-acquisition run gives 28, not 29: ``method`` comes from its own call and so
    # carries a real reason instead of not_targeted_by_mvp. The two numbers differing is the point —
    # this fixture asserts the untargeted skeleton, not a run.
    assert out.count("not examined by the extractor") == 29
