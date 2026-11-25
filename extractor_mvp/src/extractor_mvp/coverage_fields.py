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
import re
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
    DistortionSource,
    DistortionTool,
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
    TemporalPassType,
    TissueClass,
    TissueRegressor,
)

from extractor_mvp.synonym_resolver import (
    SYNONYMS_BY_FIELD,
    _fold_separators,
    _rejoin_line_wraps,
    members_named,
    repair_text,
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
# Alias tables: canonical member -> the forms a paper writes. Matched as whole words on the
# model's value by synonym_resolver.resolve_to_literal (2026-11-24), the longer alias winning
# where one holds another (D2b, 2026-11-25); token-run matched on the quote by
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
    "spm_slice_timing": [
        "SPM slice timing",
        "SPM slice-timing",
        "spm_slice_timing",
        "SPM",
    ],
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
    # D2b (2026-11-25): "ICA+FIX" is HCP's own name (glasser2016_nature: "the ICA+FIX pipeline"). The
    # list splitter cut it at "+", leaving an unresolved "ICA" beside fix; an alias that holds a
    # separator is now kept whole (extractor._split_terms).
    "fix": ["FIX", "ICA-FIX", "FSL FIX", "ICA FIX", "ICA+FIX"],
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


@dataclasses.dataclass(frozen=True)
class TermRules:
    """Field rules applied before and after the alias table (2026-11-24, the author's ruling on the
    resolver audit). A value whose meaning turns on a count or a modifier is not left to substring
    aliases: "6 parameters and their derivatives" is not the six-parameter model.

    - ``require_all``: a member resolved when every pattern occurs in the term (case-insensitive).
    - ``block``: a member the alias table may not return when any of its patterns occurs; the term
      is then kept unresolved, in the paper's words.
    - ``exact_overrides``: an exact member token resolved elsewhere by a dated ruling.
    - ``named_by`` (D2b, 2026-11-25): a member the term names when any of its patterns occurs,
      without the term resolving to it. The alias table may then not return ANOTHER member (the
      term names two), a quote that holds the pattern holds the member (the token trace), and the
      report does not say the term is outside the vocabulary. The member itself still needs an
      alias or a ``require_all`` rule to be resolved.
    """

    require_all: dict[str, tuple[str, ...]] = dataclasses.field(default_factory=dict)
    block: dict[str, tuple[str, ...]] = dataclasses.field(default_factory=dict)
    exact_overrides: dict[str, str] = dataclasses.field(default_factory=dict)
    named_by: dict[str, tuple[str, ...]] = dataclasses.field(default_factory=dict)


#: Keyed on the dotted path. Motion expansion (the audit of 2026-11-24 found ten stored wordings
#: with derivatives, squares or a count of 12 or 24 resolved to 6param through "6 parameters"):
#: six parameters with derivatives and squares (or quadratic terms) is friston24, the project's
#: convention; any derivative, square, quadratic, expansion or regressor count blocks 6param, so
#: a wording no member fits keeps its words (12param is schema 0.8.0, DESIGN_prompt_schema_2026-11
#: B1). The exact token "volterra" stays friston24 (item 3, 2026-10-28).
#:
#: D2b (2026-11-25): the wrong-member matches of the D1 sweep that both of its verifiers confirmed
#: (DESIGN_prompt_schema_2026-11 A6; results/d1_token_audit_2026-11-24/REPORT.md). Each is a block:
#: the alias table may not return the member, and the paper's words are kept. None adds an alias.
#:
#: - motion expansion: "six motion parameters and their first differences" resolved to 6param,
#:   because the block list named derivatives and not differences. The same day the two patterns
#:   were narrowed from "deriv" and "differ": "six motion parameters derived from the realignment"
#:   and "... for the different runs" are the six-parameter model, and the rule of 2026-11-24 had
#:   kept them unresolved (no stored wording showed it). "derivat" covers derivative, derivate and
#:   derivation and leaves "derived" alone;
#: - distortion method and source: "fieldmap-less" and "fieldmap-free" resolved to fieldmap (the
#:   opposite method) and to susceptibility_fieldmap through "fieldmap";
#: - brain extraction: "HD-BET" resolved to bet (a hyphen is a word boundary, so the whole-word rule
#:   that stopped "optiBET" did not stop it);
#: - slice timing reference: fMRIPrep's "0.5 of slice acquisition range" resolved to specific_slice
#:   through "slice"; it states a time;
#: - smoothing space: "native cortical surface", "the subject's cortical surface" and "individual
#:   cortical surface" resolved to template_surface through "cortical surface" (sims_2021 and
#:   smith_2013 word a subject's own surface this way).
#: - the SPM members and an SPM release written as one word. The whole-word rule of 2026-11-24
#:   stopped such a release from resolving through "SPM"; the stored quotes print SPM99 and SPM99b
#:   (maheu_2011, dimitrova_2002), SPM5 (shen_2013), SPM8 (gordon_2014, greene_2022), SPM12
#:   (agtzidis_2020 and others) and SPM12b (silchenko_2023). A release written apart ("SPM 12",
#:   "SPM-8") holds "SPM" as a word of its own and resolves through that alias, as it always has.
#:   Two rules:
#:   - a listed release that is the whole wording is that member ("SPM12", "the SPM99b
#:     software"). The list is closed: 99, 2, 5, 8, 12 and 25, each with or without the "b" of a
#:     beta;
#:   - "SPM" with a number inside a longer wording, or with a number the list lacks ("SPM96"),
#:     NAMES the member and does not resolve to it. As a plain alias it would resolve, and "CONN
#:     toolbox (SPM12)", "DPARSF (SPM8)" or "CAT12 (SPM12)" would become SPM's own tool for the
#:     step, which a toolbox that runs on SPM is not (C3); a list of such toolboxes to block
#:     cannot be closed (the review of this change found six names the first list missed). Naming
#:     keeps another member from taking the term ("SPM12 in MATLAB" is not custom), lets the token
#:     trace find the release in a quote, and keeps the report from calling the term outside the
#:     vocabulary.
#:   The bare alias "SPM" is as it was: "CONN toolbox (SPM)" still resolves to the SPM member, and
#:   whether it should is put to the author.
_FIELDMAP_FREE = r"field[\s_-]*map[\s_-]*(?:less|free)"
_DERIVATIVE = r"derivat|\bderivs?\b"
_SPM_RELEASE = r"(?<![a-z0-9])spm(?:99|2|5|8|12|25)b?(?![a-z0-9])"
_SPM_RELEASE_ALONE = rf"\A\W*(?:the\s+)?{_SPM_RELEASE}(?:\s+(?:software|package))?\W*\Z"
_SPM_NUMBERED = r"(?<![a-z0-9])spm\d{1,2}[a-z]?(?![a-z0-9])"


def _spm_member(member: str) -> TermRules:
    return TermRules(
        require_all={member: (_SPM_RELEASE_ALONE,)}, named_by={member: (_SPM_NUMBERED,)}
    )


TERM_RULES: dict[str, TermRules] = {
    "nuisance_regression.motion_expansion": TermRules(
        require_all={"friston24": (r"\b(?:6|six)\b", _DERIVATIVE, r"squar|quadrat")},
        block={
            "6param": (
                _DERIVATIVE,
                r"differenc",
                r"squar",
                r"quadrat",
                r"expan",
                r"\b(?:12|18|24|36)\b",
                r"\bR\s*['\u2032\u00b4]",
            )
        },
        exact_overrides={"volterra": "friston24"},
    ),
    "distortion_correction.method": TermRules(block={"fieldmap": (_FIELDMAP_FREE,)}),
    "distortion_correction.source": TermRules(block={"susceptibility_fieldmap": (_FIELDMAP_FREE,)}),
    "brain_extraction.method": TermRules(block={"bet": (r"\bhd[\s_-]*bet\b",)}),
    "nuisance_regression.method": _spm_member("spm"),
    "segmentation.method": _spm_member("spm_segment"),
    "slice_time_correction.method": _spm_member("spm_slice_timing"),
    "coregistration.method": _spm_member("spm_coreg"),
    "spatial_smoothing.method": _spm_member("spm_smooth"),
    "slice_time_correction.reference": TermRules(
        block={"specific_slice": (r"slice[\s-]*acquisition[\s-]*range",)}
    ),
    "spatial_smoothing.space": TermRules(
        block={
            "template_surface": (
                r"\b(?:native|fsnative|individual|own|subjects?(?:'s?)?|participants?(?:'s?)?)\b"
                r"[^,;.]{0,30}cortical[\s-]+surface",
            )
        }
    ),
}

#: D2b (2026-11-25): fields whose prompt line offers "other" while the vocabulary has no such
#: member. There the model's "other (phrase)" says that no member fits, so no alias inside the
#: phrase may claim one ("other (normalized correlation, not mutual information)" had resolved to
#: mutual_information). The cost function gets the member in schema 0.8.0 (C9), and leaves this set.
OTHER_OFFERED_WITHOUT_MEMBER: frozenset[str] = frozenset({"coregistration.cost_function"})

#: D2b (2026-11-25): a term of a LIST field that holds a list separator of its own and is one term
#: all the same, as a regular expression (case-insensitive). The list splitter keeps it whole
#: (extractor._split_terms). The aliases of the field that hold a separator ("blip-up/blip-down",
#: "ICA+FIX") are kept whole without being listed here. SPM's tool is "Realign & Unwarp";
#: achuthan_2023 and mueller_2021 write "realigned and unwarped".
COMPOUND_TERMS: dict[str, tuple[str, ...]] = {
    "distortion_correction.tool": (r"realign\w*\s+and\s+unwarp\w*",),
    "distortion_correction.method": (r"realign\w*\s+and\s+unwarp\w*",),
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
        # D2b (2026-11-25): hagler_2019's text layer prints the token split, "B 0 distortions"
        "B 0",
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
#: 2026-11-03 (the author's ruling): the method FAMILY, separate from the program (DISTORTION_TOOL).
#: Case one's Hagler et al. (2019) states "the same reversing polarity method"; a tool name returned
#: for it was rejected by the value-in-quote check in every draw.
DISTORTION_METHOD: dict[str, list[str]] = {
    "reverse_phase_encoding": [
        "reverse_phase_encoding",
        "reversing polarity",
        "reversed polarity",
        "reverse polarity",
        "opposite phase-encoding",
        "opposite phase encoding",
        "reverse phase-encoding",
        "reversed phase-encoding",
        "reverse phase encoding",
        "blip-up/blip-down",
        "blip up/blip down",
        "blip-up blip-down",
    ],
    "fieldmap": ["fieldmap", "field map", "field-map", "phase difference", "phase-difference"],
    # 2026-11-03 (the author's ruling): case one's "Images are next corrected for distortions due
    # to gradient nonlinearities", which the model had returned as "other"
    "gradient_nonlinearity_correction": [
        "gradient_nonlinearity_correction",
        "gradient nonlinearities",
        "gradient nonlinearity distortions",
    ],
    "other": [],
}
#: The families the extractor may resolve a method to (2026-11-03). The schema's DistortionMethod also
#: keeps the five program members so a 0.6.0 document stays valid; a new extraction never resolves to
#: them, so a program name returned as the method stays unrecognized (and its quote must hold it).
DistortionFamily = Literal[
    "reverse_phase_encoding", "fieldmap", "gradient_nonlinearity_correction", "other"
]
#: The program (2026-11-03): the members the 0.6.0 method table held.
DISTORTION_TOOL: dict[str, list[str]] = {
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
#: fix 5 (2026-11-05, after stress_v1): the band's shape, asked apart from the filter's design.
PASS_TYPE: dict[str, list[str]] = {
    "high_pass": ["high-pass", "highpass", "high pass", "high-passed", "high-pass filtered"],
    "low_pass": ["low-pass", "lowpass", "low pass", "low-passed", "low-pass filtered"],
    "band_pass": ["band-pass", "bandpass", "band pass", "band-passed", "band-pass filtered"],
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
    _spec(
        "T",
        "filter_pass_type",
        "temporal_filtering",
        "pass_type",
        "term",
        TemporalPassType,
        PASS_TYPE,
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
        DistortionFamily,
        DISTORTION_METHOD,
    ),
    _spec(
        "S",
        "distortion_tool",
        "distortion_correction",
        "tool",
        "term_list",
        DistortionTool,
        DISTORTION_TOOL,
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

#: The record-level multiple_pipelines / pipeline_variant_count specs (the author's item 5,
#: 2026-10-28; moved to the checking pass 2026-10-29) are gone (2026-11-11, DESIGN_applies_to.md
#: fork F1): whether a paper has variants is read off its values. A stored record keeps its answer.

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
        # 2026-11-02, the author's queued fix, DECLARED FITTED: added after shen_2013 (one of the
        # two unseen papers of 2026-10-29) rendered its regression sentence unverifiable -- shen is
        # contaminated for this table from here on. "orthogonalized" covers "orthogonalised" and
        # "orthogonalization" through the word-form matcher; bare "orthogonal" is NOT matched (an
        # orthogonal design is not a regression). The "regressed out" family already matched
        # through "regressed"/"regress" before this entry; listed so the family is explicit.
        "orthogonalized",
        "orthogonalised",
        "orthogonalization",
        "regressed out",
        "regressing out",
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
    s.dotted for s in COVERAGE_SPECS if s.value_kind in ("number", "int")
)
COVERAGE_TEXT_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "text"
)
COVERAGE_LIST_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "term_list"
)
COVERAGE_BOOL_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "bool"
)

#: kind -> its specs, in order (``performed`` first on every kind).
SPECS_BY_KIND: dict[str, tuple[CoverageFieldSpec, ...]] = {
    kind: tuple(s for s in COVERAGE_SPECS if s.kind == kind) for kind in COVERAGE_KINDS
}

#: report v2 §1a: band fields (every stated edge digit-exact in the quote).
COVERAGE_BAND_FIELDS: frozenset[str] = frozenset(
    s.dotted for s in COVERAGE_SPECS if s.value_kind == "band"
)


# ---------------------------------------------------------------------------
# The vocabulary as a whole: 35 coverage fields and the 4 fields of the shared call (D2b, 2026-11-25)
# ---------------------------------------------------------------------------

#: The four vocabulary fields of the shared call: dotted path -> the bare field id that keys
#: ``synonym_resolver.SYNONYMS_BY_FIELD``. ``extractor._FIELD_SPECS`` holds the same pairs;
#: tests/test_resolver_d2b.py checks that the two agree.
SHARED_VOCABULARY_FIELDS: dict[str, str] = {
    "spatial_normalization.target_space": "target_space",
    "surface_projection.surface_registration": "surface_registration",
    "surface_projection.target_surface": "target_surface",
    "intensity_normalization.convention": "convention",
}


def vocabulary_table(dotted: str) -> tuple[dict[str, list[str]], list[str] | None] | None:
    """The alias table and the family (underspecified) list of a vocabulary field, or None for a
    field that has no table: a number, free text, the motion phrase (read by the resolution call),
    temporal_standardization.method (exact members only)."""
    if dotted in COVERAGE_SUPPORT_TABLES:
        synonyms, underspecified = COVERAGE_SUPPORT_TABLES[dotted]
        return (synonyms, underspecified) if synonyms else None
    field_id = SHARED_VOCABULARY_FIELDS.get(dotted)
    return SYNONYMS_BY_FIELD.get(field_id) if field_id else None


def rule_hits(pattern: str, words: str) -> bool:
    """Whether a TERM_RULES pattern occurs in the words: as written, as repaired (a ligature, a
    Unicode hyphen, a soft hyphen inside a word), or with a word that a line break split put back
    together ("deriva-", newline, "tives"). These are the readings the alias table matches on."""
    repaired = repair_text(words)
    return any(
        re.search(pattern, text, re.IGNORECASE)
        for text in (words, repaired, _rejoin_line_wraps(repaired))
    )


#: Names of a FAMILY whose members the vocabulary holds, read for the report's note only (B11).
#: A term that holds one says which family and not which member ("fs_LR" with no density, "MSM"
#: with no variant, "CompCor" with no kind), so the report does not call it outside the
#: vocabulary. Resolution is untouched: the term stays unresolved, in the paper's words. The
#: tables hold such terms for one field only ("MNI" and its kin, as underspecified terms of the
#: target space); whether these join them, which changes their resolution status, is put to the
#: author.
FAMILY_NAMES: dict[str, tuple[str, ...]] = {
    "surface_projection.target_surface": ("fsLR", "fs_LR"),
    "surface_projection.surface_registration": ("MSM",),
    "compcor.variant": ("CompCor",),
    "spatial_normalization.target_space": ("Montreal Neurological Institute", "ICBM", "ICBM152"),
}


def rules_name(dotted: str, words: str) -> set[str]:
    """The members the field's ``named_by`` rules find in the words (an SPM release)."""
    rules = TERM_RULES.get(dotted)
    if not rules:
        return set()
    return {
        member
        for member, patterns in rules.named_by.items()
        if any(rule_hits(p, words) for p in patterns)
    }


def names_no_member(dotted: str, words: str) -> bool:
    """True when nothing of today's vocabulary occurs in these words (B11): the field has a table,
    and the words hold no alias, no member token, no wording a field rule resolves or names, no
    family term and no family name (:data:`FAMILY_NAMES`).

    False for a field with no table. False whenever a member is named, even when the words stay
    unresolved: two members named ("FLIRT and bbregister": ambiguous), a member a rule blocks
    ("native cortical surface" names template_surface's alias, and the field holds native_surface),
    a member token in another case ("Friston24", "Native Volume"), a release inside a longer
    wording ("CONN toolbox (SPM12)"), a record an older resolver left unresolved. The report makes
    a claim about the vocabulary, so it is made only where no part of the words is a name the
    vocabulary knows. An alias gated on a value ("grand mean@10000") counts whatever the value is.

    A member's own token counts inside a longer wording as an alias does, with two exceptions that
    count only as the whole wording: the catch-all "other" and a one-letter token (CompCor's "a"),
    which are ordinary words inside a sentence ("ROBEX and other tools", "a custom method")."""
    table = vocabulary_table(dotted)
    if table is None:
        return False
    synonyms, underspecified = table
    # every member is a key of its table, except "other" on the four shared fields
    members = {*synonyms, *(["other"] if dotted in SHARED_VOCABULARY_FIELDS else [])}
    whole = _fold_separators(repair_text(words).lower()).strip(" .,;:()[]\"'")
    if whole in {_fold_separators(m.lower()) for m in members}:
        return False
    names = {
        member: [
            *(a.rpartition("@")[0] if "@" in a else a for a in aliases),
            *([member] if member != "other" and len(member) > 1 else []),
        ]
        for member, aliases in synonyms.items()
    }
    rules = TERM_RULES.get(dotted)
    if rules and any(
        all(rule_hits(p, words) for p in patterns) for patterns in rules.require_all.values()
    ):
        return False
    if rules_name(dotted, words):
        return False
    if members_named(words, {**names, "(family)": list(FAMILY_NAMES.get(dotted, ()))}):
        return False
    lowered = repair_text(words).lower()
    return not any(u.lower() in lowered for u in underspecified or [])
