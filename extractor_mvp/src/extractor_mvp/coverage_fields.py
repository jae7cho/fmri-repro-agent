"""The field table of the two coverage calls, and the alias tables their support check reads.

``docs/design/DESIGN_coverage_expansion.md`` B1/B3 — the author's rulings R1 and R3 of 2026-10-28.
One row per response field of ``TemporalVolumeExtraction`` (call T) and ``SpatialExtraction``
(call S): the kind and bare field id it lands on, the value kind that picks the coercion and the
support check, the Literal behind a term field, the ``ProvenancedField`` generic, and the alias
table (synonym resolution AND quote support read the same table, keyed by the DOTTED id -- never
the bare id, which ``method`` shares across eleven kinds).

Pure: no model, no KB, no text. ``quote_support`` imports the tables from here; this module imports
nothing from the extractor.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any, Literal

from fmri_repro.spec.preprocessing import (
    BrainExtractionMethod,
    CompCorVariant,
    CoregistrationCostFunction,
    CoregistrationInterpolation,
    CoregistrationMethod,
    CoregistrationTransform,
    DespikeMethod,
    Detrend,
    DistortionMethod,
    DistortionSource,
    ICADenoiseMethod,
    IntensityCorrectionMethod,
    IntensityCorrectionTarget,
    MotionExpansion,
    NuisanceRegressionMethod,
    PhysioRegressor,
    ScrubCriterion,
    ScrubInterpolationMethod,
    ScrubMethod,
    ScrubRemediation,
    SegmentationMethod,
    SliceTimingInterpolation,
    SliceTimingMethod,
    SliceTimingReference,
    SliceTimingRelativeToMC,
    SmoothingApproach,
    SmoothingKernelType,
    SmoothingMethod,
    SmoothingSpace,
    SpecifiedTerm,
    TemporalFilteringRelativeToRegression,
    TemporalFilterType,
    TissueClass,
    TissueRegressor,
)

ValueKind = Literal["term", "term_list", "number", "int", "bool", "text", "band"]

#: The thirteen kinds of the eleven uncovered rows (cobidas.COBIDAS_D3_ROWS), by call.
CALL_T_KINDS: tuple[str, ...] = (
    "nonsteadystate_removal",
    "slice_time_correction",
    "despike",
    "scrub",
    "ica_denoise",
    "compcor",
    "nuisance_regression",
    # report v2 §1a (2026-10-29): beyond COBIDAS, asked on the same call
    "temporal_filtering",
)
CALL_S_KINDS: tuple[str, ...] = (
    "brain_extraction",
    "segmentation",
    "coregistration",
    "distortion_correction",
    "intensity_correction",
    "spatial_smoothing",
)
COVERAGE_KINDS: tuple[str, ...] = CALL_T_KINDS + CALL_S_KINDS


@dataclasses.dataclass(frozen=True)
class CoverageFieldSpec:
    call: Literal["T", "S"]
    attr: str  # the response-model attribute
    kind: str  # the step kind the field lands on
    field_id: str  # the bare step attribute (a step invariant)
    value_kind: ValueKind
    literal_type: Any  # the bare Literal behind a term field, else None
    t: Any  # the ProvenancedField generic
    synonyms: dict[str, list[str]] | None = None
    underspecified: list[str] | None = None

    @property
    def dotted(self) -> str:
        return f"{self.kind}.{self.field_id}"


# ---------------------------------------------------------------------------
# Alias tables: canonical member -> the forms a paper writes. Substring-matched on the model's
# value by synonym_resolver.resolve_to_literal; token-run matched on the quote by
# quote_support.phrase_in_quote (an alias is taken whole, never split).
# ---------------------------------------------------------------------------

_INTERPOLATION: dict[str, list[str]] = {
    "linear": ["linear", "trilinear"],
    "spline": ["spline", "b-spline", "cubic spline", "bspline"],
    "sinc": ["sinc"],
}
_INTERPOLATION_OTHER = {**_INTERPOLATION, "other": []}

STC_METHOD: dict[str, list[str]] = {
    "fsl_slicetimer": ["slicetimer", "FSL slice timing", "FSL slicetimer"],
    "spm_slice_timing": ["SPM slice timing", "SPM slice-timing", "spm_slice_timing", "SPM"],
    "afni_3dtshift": ["3dTshift", "AFNI 3dTshift"],
    "other": [],
}
STC_RELATIVE: dict[str, list[str]] = {
    "before": [
        "before motion correction",
        "prior to motion correction",
        "before realignment",
        "prior to realignment",
        "before",
    ],
    "after": [
        "after motion correction",
        "following motion correction",
        "after realignment",
        "following realignment",
        "after",
    ],
}
STC_REFERENCE: dict[str, list[str]] = {
    "first": ["first slice", "first"],
    "middle": ["middle slice", "middle", "central slice", "centre slice", "center slice"],
    "specific_slice": ["specific slice", "slice"],
    "specific_time": ["specific time", "TR/2", "middle of the TR", "midpoint", "half the TR"],
}
DESPIKE_METHOD: dict[str, list[str]] = {
    "afni_3dDespike": ["3dDespike", "AFNI 3dDespike"],
    "other": [],
}
SCRUB_METHOD: dict[str, list[str]] = {
    "afni_3dtproject": ["3dTproject"],
    "fsl_motion_outliers": ["fsl_motion_outliers", "motion outliers"],
    "custom": ["in-house", "custom", "in house"],
    "other": [],
}
SCRUB_CRITERION: dict[str, list[str]] = {
    "fd_power": ["framewise displacement", "frame-wise displacement", "FD", "Power"],
    "fd_jenkinson": ["Jenkinson", "RMS displacement", "relative RMS", "root mean square"],
    "dvars": ["DVARS"],
    "bold_pct": ["percent BOLD", "percentage BOLD", "% BOLD", "BOLD change"],
}
SCRUB_REMEDIATION: dict[str, list[str]] = {
    "censor": [
        "censor",
        "censored",
        "censoring",
        "scrubbed",
        "scrubbing",
        "removed",
        "excluded",
        "discarded",
    ],
    "interpolate": ["interpolate", "interpolated", "interpolation"],
}
SCRUB_INTERPOLATION: dict[str, list[str]] = {
    "spline": ["spline"],
    "spectral": ["spectral", "Lomb-Scargle", "lomb scargle", "Lomb Scargle"],
    "other": [],
}
ICA_METHOD: dict[str, list[str]] = {
    "fix": ["FIX", "ICA-FIX", "FSL FIX", "ICA FIX"],
    "aroma": ["AROMA", "ICA-AROMA", "ICA AROMA"],
}
COMPCOR_VARIANT: dict[str, list[str]] = {
    "a": ["aCompCor", "anatomical CompCor", "anatomical component"],
    "t": ["tCompCor", "temporal CompCor", "temporal component"],
}
MOTION_EXPANSION: dict[str, list[str]] = {
    "none": ["none"],
    "6param": [
        "6 motion parameters",
        "six motion parameters",
        "six rigid-body",
        "6 rigid-body",
        "6 realignment parameters",
        "six realignment parameters",
        "6 parameters",
        "six parameters",
        "6-parameter",
    ],
    # item 3 (2026-10-28): a Volterra expansion of the six parameters IS the 24-parameter model
    # (Friston et al. 1996), so "Volterra" resolves to friston24; the ``volterra`` member keeps no
    # alias of its own and is reached only by the exact token.
    "friston24": [
        "24 motion",
        "Friston",
        "24-parameter",
        "24 parameters",
        "24 regressors",
        "24 head motion",
        "24 nuisance",
        "24 movement",
        "Volterra",
    ],
    "volterra": [],
}
TISSUE_REGRESSOR: dict[str, list[str]] = {
    "whole_brain": ["global signal", "whole brain", "whole-brain", "GSR", "global mean", "global"],
    "gray_matter": ["gray matter", "grey matter", "GM"],
    "white_matter": ["white matter", "WM"],
    "ventricles": ["ventricles", "ventricular", "ventricle", "CSF", "cerebrospinal fluid"],
}
PHYSIO_REGRESSOR: dict[str, list[str]] = {
    "retroicor": ["RETROICOR"],
    "rvt": ["RVT", "respiration volume per time", "respiratory volume"],
    "none": ["none", "no physiological"],
}
DETREND: dict[str, list[str]] = {
    "linear": ["linear detrend", "linear trend", "linearly detrended", "linear"],
    "quadratic": [
        "quadratic",
        "second-order polynomial",
        "2nd order polynomial",
        "second order polynomial",
    ],
    "none": ["none"],
}
NUISANCE_METHOD: dict[str, list[str]] = {
    "afni_3dtproject": ["3dTproject"],
    "afni_3dbandpass": ["3dBandpass"],
    "afni_3ddeconvolve": ["3dDeconvolve"],
    "fsl_regfilt": ["fsl_regfilt", "regfilt"],
    "spm": ["SPM"],
    "nilearn": ["nilearn"],
    "custom": ["in-house", "in house", "custom", "MATLAB"],
    "other": [],
}
BRAIN_EXTRACTION_METHOD: dict[str, list[str]] = {
    "bet": ["BET", "brain extraction tool"],
    "afni_3dskullstrip": ["3dSkullStrip"],
    "freesurfer_recon_all": ["recon-all", "FreeSurfer"],
    "ants": ["ANTs", "antsBrainExtraction"],
    "synthstrip": ["SynthStrip"],
    "other": [],
}
SEGMENTATION_METHOD: dict[str, list[str]] = {
    "fsl_fast": ["FAST", "FSL FAST"],
    "spm_segment": [
        "SPM segment",
        "New Segment",
        "unified segmentation",
        "SPM12 segmentation",
        "SPM segmentation",
        "SPM",
    ],
    "freesurfer_recon_all": ["recon-all", "FreeSurfer"],
    "ants_atropos": ["Atropos"],
    "other": [],
}
TISSUE_CLASS: dict[str, list[str]] = {
    "gray_matter": ["gray matter", "grey matter", "GM"],
    "white_matter": ["white matter", "WM"],
    "csf": ["CSF", "cerebrospinal fluid"],
}
COREG_TRANSFORM: dict[str, list[str]] = {
    "rigid": [
        "rigid",
        "rigid-body",
        "rigid body",
        "6 degrees of freedom",
        "6 DOF",
        "six degrees",
        "6-DOF",
        "six-parameter",
        "6-parameter",
    ],
    "affine": ["affine", "12 degrees of freedom", "12 DOF", "12-parameter"],
    "nonlinear": ["nonlinear", "non-linear"],
}
COREG_METHOD: dict[str, list[str]] = {
    # item 4 (2026-10-28): method = the TOOL. The bare "BBR" / "boundary-based registration" forms
    # left this table -- they are the cost function (COREG_COST) -- so a paper naming only BBR has
    # a cost function and no tool, not a tool named flirt_bbr.
    "flirt_bbr": ["FLIRT BBR", "FLIRT with BBR", "FLIRT (BBR)"],
    "flirt": ["FLIRT"],
    "spm_coreg": ["SPM coregister", "coregister", "SPM"],
    "bbregister": ["bbregister"],
    "ants": ["ANTs"],
    "other": [],
}
COREG_COST: dict[str, list[str]] = {
    "correlation_ratio": ["correlation ratio"],
    "mutual_information": ["mutual information", "normalized mutual information"],
    # item 4 (2026-10-28): the prompt's canonical token is "bbr"; the spec member stays
    # boundary_based (no schema change).
    "boundary_based": ["bbr", "boundary-based", "boundary based", "boundary-based registration"],
    "ssd": ["sum of squared differences", "least squares", "SSD"],
}
DISTORTION_SOURCE: dict[str, list[str]] = {
    "susceptibility_fieldmap": [
        "field map",
        "fieldmap",
        "field-map",
        "susceptibility",
        "B0",
        "phase difference",
        "spin echo",
        # item 3 (2026-10-28): "magnetic field inhomogeneit*" -- both word forms, and the bare
        # "field inhomogeneit*" a paper writes without "magnetic"
        "magnetic field inhomogeneity",
        "magnetic field inhomogeneities",
        "field inhomogeneity",
        "field inhomogeneities",
    ],
    "gradient_nonlinearity": [
        "gradient nonlinearity",
        "gradient non-linearity",
        "gradient distortion",
        "gradient nonlinearities",
    ],
    "fieldmap_less": ["fieldmap-less", "field map-less", "fieldmapless", "SyN-based"],
}
DISTORTION_METHOD: dict[str, list[str]] = {
    "topup": ["topup", "TOPUP"],
    "fugue": ["FUGUE"],
    "gradunwarp": ["gradunwarp", "gradient_unwarp", "gradient unwarp"],
    "sdc_fieldmapless": ["SyN", "fieldmap-less"],
    "other": [],
}
INTENSITY_TARGET: dict[str, list[str]] = {
    "bias_field": [
        "bias field",
        "bias-field",
        "intensity inhomogeneity",
        "inhomogeneity",
        "bias correction",
        "intensity non-uniformity",
        "nonuniformity",
    ],
    "interleaved_slice": [
        "odd and even slice",
        "odd/even",
        "interleaved slice",
        "slice intensity",
        "odd-even",
    ],
}
INTENSITY_METHOD: dict[str, list[str]] = {
    "n4": ["N4", "N4BiasFieldCorrection", "N3"],
    "fast_bias": ["FAST"],
    "other": [],
}
SMOOTHING_METHOD: dict[str, list[str]] = {
    "fsl_susan": ["SUSAN"],
    "fsl_fslmaths": ["fslmaths"],
    "spm_smooth": ["SPM smooth", "SPM"],
    "afni_3dmerge": ["3dmerge"],
    "afni_3dblurtofwhm": ["3dBlurToFWHM"],
    "workbench": ["Workbench", "wb_command"],
    "other": [],
}
SMOOTHING_KERNEL: dict[str, list[str]] = {"gaussian": ["Gaussian"], "other": []}
SMOOTHING_APPROACH: dict[str, list[str]] = {
    "fixed_kernel": ["fixed kernel", "fixed"],
    "iterate_to_fwhm": ["iterative", "iteratively", "until", "3dBlurToFWHM", "to a final"],
}
SMOOTHING_SPACE: dict[str, list[str]] = {
    "native_volume": [
        "native volume",
        "native space",
        "subject space",
        "functional space",
        "individual space",
    ],
    "native_surface": ["native surface"],
    "mni_volume": ["MNI", "MNI volume", "standard space", "template space", "Talairach"],
    # item 3 (2026-10-28), found by the replay: the bare alias "surface" resolved weber's exact
    # member "native_surface" to template_surface (the underscore kept "native surface" from
    # matching). Removed; the specific forms remain.
    "template_surface": [
        "fsaverage",
        "fsLR",
        "fs_LR",
        "template surface",
        "grayordinate",
        "cortical surface",
    ],
}


FILTER_TYPE: dict[str, list[str]] = {
    "butterworth": ["Butterworth"],
    "fir": ["FIR", "finite impulse response"],
    "iir": ["IIR", "infinite impulse response"],
    "ideal_fft": ["ideal", "FFT", "Fourier", "3dBandpass", "3dTproject"],
    "chebyshev": ["Chebyshev"],
    "other": [],
}
FILTER_RELATIVE: dict[str, list[str]] = {
    "before": ["before regression", "prior to regression", "before nuisance", "prior to nuisance"],
    "after": ["after regression", "following regression", "after nuisance", "following nuisance"],
    "simultaneous": [
        "simultaneously",
        "in the same regression",
        "same model",
        "3dTproject",
        "together with the nuisance",
    ],
}


def _spec(
    call: Literal["T", "S"],
    attr: str,
    kind: str,
    field_id: str,
    value_kind: ValueKind,
    literal_type: Any = None,
    synonyms: dict[str, list[str]] | None = None,
    underspecified: list[str] | None = None,
) -> CoverageFieldSpec:
    t: Any
    if value_kind == "term":
        t = SpecifiedTerm[literal_type]
    elif value_kind == "term_list":
        t = list[SpecifiedTerm[literal_type]]
    elif value_kind == "number":
        t = float
    elif value_kind == "int":
        t = int
    elif value_kind == "bool":
        t = bool
    elif value_kind == "band":
        t = tuple[float | None, float | None]
    else:
        t = str
    return CoverageFieldSpec(
        call, attr, kind, field_id, value_kind, literal_type, t, synonyms, underspecified
    )


#: Call T, in response-model order. ``performed`` first on every kind (R2).
CALL_T_SPECS: tuple[CoverageFieldSpec, ...] = (
    _spec("T", "t1_performed", "nonsteadystate_removal", "performed", "bool"),
    _spec("T", "t1_n_discarded", "nonsteadystate_removal", "n_nonsteadystate_discarded", "int"),
    _spec("T", "stc_performed", "slice_time_correction", "performed", "bool"),
    _spec(
        "T", "stc_method", "slice_time_correction", "method", "term", SliceTimingMethod, STC_METHOD
    ),
    _spec(
        "T",
        "stc_relative_to_motion_correction",
        "slice_time_correction",
        "relative_to_motion_correction",
        "term",
        SliceTimingRelativeToMC,
        STC_RELATIVE,
    ),
    _spec(
        "T",
        "stc_reference",
        "slice_time_correction",
        "reference",
        "term",
        SliceTimingReference,
        STC_REFERENCE,
    ),
    _spec(
        "T",
        "stc_interpolation",
        "slice_time_correction",
        "interpolation",
        "term",
        SliceTimingInterpolation,
        _INTERPOLATION,
    ),
    _spec("T", "stc_interpolation_order", "slice_time_correction", "interpolation_order", "int"),
    _spec("T", "despike_performed", "despike", "performed", "bool"),
    _spec("T", "despike_method", "despike", "method", "term", DespikeMethod, DESPIKE_METHOD),
    _spec("T", "despike_threshold", "despike", "threshold", "number"),
    _spec("T", "scrub_performed", "scrub", "performed", "bool"),
    _spec("T", "scrub_method", "scrub", "method", "term", ScrubMethod, SCRUB_METHOD),
    _spec(
        "T", "scrub_criterion", "scrub", "criterion", "term_list", ScrubCriterion, SCRUB_CRITERION
    ),
    _spec("T", "scrub_threshold", "scrub", "threshold", "number"),
    _spec(
        "T",
        "scrub_remediation",
        "scrub",
        "remediation",
        "term",
        ScrubRemediation,
        SCRUB_REMEDIATION,
    ),
    _spec(
        "T",
        "scrub_interpolation_method",
        "scrub",
        "interpolation_method",
        "term",
        ScrubInterpolationMethod,
        SCRUB_INTERPOLATION,
    ),
    _spec("T", "ica_performed", "ica_denoise", "performed", "bool"),
    _spec("T", "ica_method", "ica_denoise", "method", "term_list", ICADenoiseMethod, ICA_METHOD),
    _spec("T", "ica_training_set", "ica_denoise", "training_set", "text"),
    _spec("T", "ica_threshold", "ica_denoise", "threshold", "number"),
    _spec("T", "ica_aggressive", "ica_denoise", "aggressive", "bool"),
    _spec("T", "compcor_performed", "compcor", "performed", "bool"),
    _spec(
        "T", "compcor_variant", "compcor", "variant", "term_list", CompCorVariant, COMPCOR_VARIANT
    ),
    _spec("T", "compcor_n_components", "compcor", "n_components", "int"),
    _spec("T", "compcor_variance_threshold", "compcor", "variance_threshold", "number"),
    _spec("T", "compcor_mask_source", "compcor", "mask_source", "text"),
    _spec("T", "nuisance_performed", "nuisance_regression", "performed", "bool"),
    _spec(
        "T",
        "nuisance_method",
        "nuisance_regression",
        "method",
        "term",
        NuisanceRegressionMethod,
        NUISANCE_METHOD,
    ),
    _spec("T", "nuisance_regressor_list", "nuisance_regression", "regressor_list", "text"),
    _spec(
        "T",
        "nuisance_motion_expansion",
        "nuisance_regression",
        "motion_expansion",
        "term",
        MotionExpansion,
        MOTION_EXPANSION,
    ),
    _spec(
        "T",
        "nuisance_tissue_regressors",
        "nuisance_regression",
        "tissue_regressors",
        "term_list",
        TissueRegressor,
        TISSUE_REGRESSOR,
    ),
    _spec("T", "nuisance_tissue_definition", "nuisance_regression", "tissue_definition", "text"),
    _spec(
        "T",
        "nuisance_tissue_signal_definition",
        "nuisance_regression",
        "tissue_signal_definition",
        "text",
    ),
    _spec(
        "T",
        "nuisance_physio_regressors",
        "nuisance_regression",
        "physio_regressors",
        "term_list",
        PhysioRegressor,
        PHYSIO_REGRESSOR,
    ),
    _spec("T", "nuisance_physio_n_regressors", "nuisance_regression", "physio_n_regressors", "int"),
    _spec("T", "nuisance_detrend", "nuisance_regression", "detrend", "term", Detrend, DETREND),
    _spec(
        "T", "nuisance_filtering_integrated", "nuisance_regression", "filtering_integrated", "bool"
    ),
)

#: report v2 §1a (2026-10-29): temporal filtering on call T, beyond COBIDAS. The band is the canonical
#: ``effective_band_hz``; low_hz/high_hz stay untargeted so the spec's band-consistency validator can
#: never be tripped by the extractor.
CALL_T_SPECS = (
    *CALL_T_SPECS,
    _spec("T", "filter_performed", "temporal_filtering", "performed", "bool"),
    _spec("T", "filter_band_hz", "temporal_filtering", "effective_band_hz", "band"),
    _spec(
        "T",
        "filter_type",
        "temporal_filtering",
        "filter_type",
        "term",
        TemporalFilterType,
        FILTER_TYPE,
    ),
    _spec("T", "filter_order", "temporal_filtering", "order", "int"),
    _spec(
        "T",
        "filter_relative_to_regression",
        "temporal_filtering",
        "relative_to_regression",
        "term",
        TemporalFilteringRelativeToRegression,
        FILTER_RELATIVE,
    ),
    _spec("T", "filter_applied_to", "temporal_filtering", "applied_to", "text"),
)

#: Call S, in response-model order.
CALL_S_SPECS: tuple[CoverageFieldSpec, ...] = (
    _spec("S", "brain_extraction_performed", "brain_extraction", "performed", "bool"),
    _spec(
        "S",
        "brain_extraction_method",
        "brain_extraction",
        "method",
        "term",
        BrainExtractionMethod,
        BRAIN_EXTRACTION_METHOD,
    ),
    _spec("S", "brain_extraction_parameters", "brain_extraction", "parameters", "text"),
    _spec("S", "brain_extraction_manual_edits", "brain_extraction", "manual_edits", "bool"),
    _spec("S", "segmentation_performed", "segmentation", "performed", "bool"),
    _spec(
        "S",
        "segmentation_method",
        "segmentation",
        "method",
        "term",
        SegmentationMethod,
        SEGMENTATION_METHOD,
    ),
    _spec(
        "S",
        "segmentation_tissue_classes",
        "segmentation",
        "tissue_classes",
        "term_list",
        TissueClass,
        TISSUE_CLASS,
    ),
    _spec("S", "coregistration_performed", "coregistration", "performed", "bool"),
    _spec(
        "S",
        "coregistration_method",
        "coregistration",
        "method",
        "term",
        CoregistrationMethod,
        COREG_METHOD,
    ),
    _spec(
        "S",
        "coregistration_transform",
        "coregistration",
        "transform",
        "term",
        CoregistrationTransform,
        COREG_TRANSFORM,
    ),
    _spec(
        "S",
        "coregistration_nonlinear_transform_type",
        "coregistration",
        "nonlinear_transform_type",
        "text",
    ),
    _spec(
        "S",
        "coregistration_cost_function",
        "coregistration",
        "cost_function",
        "term",
        CoregistrationCostFunction,
        COREG_COST,
    ),
    _spec(
        "S",
        "coregistration_interpolation",
        "coregistration",
        "interpolation",
        "term",
        CoregistrationInterpolation,
        _INTERPOLATION_OTHER,
    ),
    _spec("S", "distortion_performed", "distortion_correction", "performed", "bool"),
    _spec(
        "S",
        "distortion_source",
        "distortion_correction",
        "source",
        "term_list",
        DistortionSource,
        DISTORTION_SOURCE,
    ),
    _spec(
        "S",
        "distortion_method",
        "distortion_correction",
        "method",
        "term_list",
        DistortionMethod,
        DISTORTION_METHOD,
    ),
    _spec("S", "intensity_correction_performed", "intensity_correction", "performed", "bool"),
    _spec(
        "S",
        "intensity_correction_target",
        "intensity_correction",
        "target",
        "term",
        IntensityCorrectionTarget,
        INTENSITY_TARGET,
    ),
    _spec(
        "S",
        "intensity_correction_method",
        "intensity_correction",
        "method",
        "term",
        IntensityCorrectionMethod,
        INTENSITY_METHOD,
    ),
    _spec("S", "smoothing_performed", "spatial_smoothing", "performed", "bool"),
    _spec(
        "S",
        "smoothing_method",
        "spatial_smoothing",
        "method",
        "term",
        SmoothingMethod,
        SMOOTHING_METHOD,
    ),
    _spec("S", "smoothing_fwhm_mm", "spatial_smoothing", "fwhm_mm", "number"),
    _spec(
        "S",
        "smoothing_kernel_type",
        "spatial_smoothing",
        "kernel_type",
        "term",
        SmoothingKernelType,
        SMOOTHING_KERNEL,
    ),
    _spec(
        "S",
        "smoothing_approach",
        "spatial_smoothing",
        "approach",
        "term",
        SmoothingApproach,
        SMOOTHING_APPROACH,
    ),
    _spec(
        "S",
        "smoothing_space",
        "spatial_smoothing",
        "space",
        "term",
        SmoothingSpace,
        SMOOTHING_SPACE,
    ),
)

COVERAGE_SPECS: tuple[CoverageFieldSpec, ...] = CALL_T_SPECS + CALL_S_SPECS

#: Record-level fields asked on BOTH calls (the author's item 5, 2026-10-28): whether the text
#: describes more than one preprocessing variant, with its quote, and how many. They land on the
#: record, not on a step (kind ``record``), and render as a header line on the steps section.
RECORD_SPECS: tuple[CoverageFieldSpec, ...] = (
    _spec("T", "multiple_pipelines", "record", "multiple_pipelines", "bool"),
    _spec("T", "pipeline_variant_count", "record", "pipeline_variant_count", "int"),
)

#: The FROZEN per-step phrase lists for ``performed`` (2026-10-28, the author's item 2,
#: DESIGN_coverage_expansion.md B14): a ``performed`` quote must contain one of its step's phrases
#: (token-run matched, word form tolerated) or the cell is unverifiable. Written from D.3's wording
#: and the corpus's own sentences in coverage_v1 (the contaminated sixteen only: four phrases were
#: added after the replay surfaced vanderwal's "dropped", weber's hyphenated "slice-time", gordon's
#: "partialling out" and mueller's "removing the effects"), then frozen: the pin test holds the sha256
#: of this table, and a change here is a dated vintage event. Fitted to those sentences; said so.
PERFORMED_PHRASES: dict[str, tuple[str, ...]] = {
    "nonsteadystate_removal": (
        "discarded",
        "discard",
        "removed",
        "removal",
        "dummy",
        "initial volumes",
        "first volumes",
        "steady state",
        "steady-state",
        "equilibration",
        "equilibrium",
        "saturation",
        "first minute",
        "dropped",
        "seconds were",
    ),
    "slice_time_correction": (
        "slice timing",
        "slice-timing",
        "slice time",
        "slice-time",
        "slice acquisition",
        "acquisition timing",
        "timing among image slices",
        "temporally align",
        "slicetimer",
        "3dTshift",
        "slice time correction",
        "slicetime",
        "slice-time correction",
    ),
    "despike": ("despiking", "despiked", "despike", "de-spiking", "spikes", "spike", "3dDespike"),
    "scrub": (
        "scrubbing",
        "scrubbed",
        "scrub",
        "censoring",
        "censored",
        "censor",
        "framewise",
        "frame-wise",
        "motion outlier",
        "volumes were removed",
        "volumes were excluded",
        "frames",
        "DVARS",
        "interpolated",
        "motion censoring",
    ),
    "ica_denoise": ("ICA", "AROMA", "FIX", "independent component", "independent components"),
    "compcor": ("CompCor", "aCompCor", "tCompCor", "principal component", "PCA", "components"),
    "nuisance_regression": (
        "regressed",
        "regression",
        "regress",
        "regressors",
        "regressor",
        "nuisance",
        "confound",
        "confounds",
        "covariates",
        "covariate",
        "partialling out",
        "partialled out",
        "physiological noise",
        "removing the effects",
    ),
    "brain_extraction": (
        "skull",
        "skull-stripped",
        "skull stripping",
        "brain extraction",
        "brain-extracted",
        "brain extracted",
        "brain mask",
        "BET",
        "3dSkullStrip",
        "non-brain",
        "nonbrain",
        "extracted the brain",
        "brain extraction tool",
    ),
    "segmentation": (
        "segmented",
        "segmentation",
        "segment",
        "tissue class",
        "tissue classes",
        "tissue probability",
        "gray matter",
        "grey matter",
        "white matter",
        "CSF",
        "cerebrospinal fluid",
        "tissue priors",
        "tissue segmentation",
    ),
    "coregistration": (
        "coregistration",
        "coregistered",
        "co-registration",
        "co-registered",
        "registered",
        "registration",
        "aligned",
        "alignment",
        "BBR",
        "boundary-based",
        "boundary based",
        "FLIRT",
        "bbregister",
    ),
    "distortion_correction": (
        "distortion",
        "distortions",
        "field map",
        "fieldmap",
        "field-map",
        "unwarping",
        "unwarped",
        "unwarp",
        "topup",
        "susceptibility",
        "gradient nonlinearity",
        "gradient nonlinearities",
        "gradient non-linearity",
        "B0",
        "inhomogeneities",
        "inhomogeneity",
    ),
    "intensity_correction": (
        "bias",
        "bias field",
        "bias-field",
        "inhomogeneity",
        "inhomogeneities",
        "intensity correction",
        "non-uniformity",
        "nonuniformity",
        "N4",
        "N3",
        "odd and even",
        "interleaved",
        "intensity normalization of the structural",
    ),
    # report v2 §1a (2026-10-29), added with the step; the table's hash re-pinned with a dated note.
    "temporal_filtering": (
        "filtered",
        "filtering",
        "filter",
        "band-pass",
        "bandpass",
        "band pass",
        "high-pass",
        "highpass",
        "high pass",
        "low-pass",
        "lowpass",
        "low pass",
        "Butterworth",
        "passband",
    ),
    "spatial_smoothing": (
        "smoothed",
        "smoothing",
        "smooth",
        "FWHM",
        "kernel",
        "blurred",
        "blurring",
        "blur",
    ),
}
PERFORMED_PHRASES_SHA256: str = hashlib.sha256(
    json.dumps(PERFORMED_PHRASES, sort_keys=True).encode("utf-8")
).hexdigest()

#: Dotted id -> (synonyms, underspecified) for every term and term_list field: the one table both
#: resolution and the quote-support check read (R3: "alias table for Literals").
COVERAGE_SUPPORT_TABLES: dict[str, tuple[dict[str, list[str]], list[str] | None]] = {
    s.dotted: (s.synonyms or {}, s.underspecified)
    for s in COVERAGE_SPECS
    if s.value_kind in ("term", "term_list")
}
COVERAGE_NUMERIC_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS + RECORD_SPECS if s.value_kind in ("number", "int")
)
COVERAGE_TEXT_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "text"
)
COVERAGE_LIST_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "term_list"
)
COVERAGE_BOOL_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS + RECORD_SPECS if s.value_kind == "bool"
)

#: kind -> its specs, in order (``performed`` first on every kind).
SPECS_BY_KIND: dict[str, tuple[CoverageFieldSpec, ...]] = {
    kind: tuple(s for s in COVERAGE_SPECS if s.kind == kind) for kind in COVERAGE_KINDS
}

#: report v2 §1a: band fields (every stated edge digit-exact in the quote).
COVERAGE_BAND_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "band"
)
