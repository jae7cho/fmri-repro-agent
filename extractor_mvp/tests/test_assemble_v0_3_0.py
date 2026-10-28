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
    # 2026-10-28 (DESIGN_coverage_expansion.md B6): the anatomical pair still precedes motion and
    # spatial normalization; the T1 and slice-timing kinds now come first, in catalog order.
    assert kinds.index("brain_extraction") < kinds.index("segmentation")
    assert kinds.index("segmentation") < kinds.index("motion_correction")
    assert kinds.index("motion_correction") < kinds.index("spatial_normalization")


def test_assemble_step_list_unchanged(assembled: Preprocessing):
    # Eighteen kinds since 2026-10-28 (the author's ruling R6: every kind of the eleven uncovered
    # D.3 rows is emitted, fields carrying states); the eight emitted before keep their relative
    # order. temporal_filtering has no D.3 row and stays unemitted.
    assert [s.kind for s in assembled.steps] == [
        "nonsteadystate_removal",
        "slice_time_correction",
        "brain_extraction",
        "segmentation",
        "motion_correction",
        "distortion_correction",
        "coregistration",
        "intensity_correction",
        "spatial_normalization",
        "surface_projection",
        "ica_denoise",
        "compcor",
        "nuisance_regression",
        "despike",
        "scrub",
        "intensity_normalization",
        "spatial_smoothing",
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
            if name in type(step).STRUCTURAL_FIELDS:
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
    #
    # 29 -> 81, 2026-10-28 (DESIGN_coverage_expansion.md B6). The fixture makes no coverage call
    # either, so every field of the thirteen kinds is untargeted: the ten newly emitted kinds carry
    # 2 + 6 + 3 + 6 + 3 + 5 + 5 + 3 + 6 + 6 = 45 fields (nonsteadystate_removal, slice_time_correction,
    # distortion_correction, coregistration, intensity_correction, ica_denoise, compcor, despike,
    # scrub, spatial_smoothing), and the three already-emitted kinds gained 2 + 1 + 4 = 7
    # (brain_extraction: performed, parameters; segmentation: performed; nuisance_regression:
    # performed, regressor_list, tissue_definition, tissue_signal_definition). 29 + 45 + 7 = 81.
    # A real run gives fewer: the coverage calls supply real reasons for those 52 fields.
    assert out.count("not examined by the extractor") == 81
