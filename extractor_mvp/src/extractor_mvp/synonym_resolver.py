"""Map LLM free-text to canonical Literal members — precision over recall.

Load-bearing invariant: a synonym entry maps a free-text term to a canonical
member ONLY when the term is **equal to or more specific than** the member's
denotation. Synonyms NEVER broaden meaning. Underspecified terms (e.g. "MNI",
"MNI152", "FreeSurfer") stay unresolved → they trip ``value_not_in_literal``
downstream, preserving the underspecification diagnostic the project measures.

When in doubt, do not add an entry: a coerced false-specific extraction is worse
than an extractable value going unresolved.

Value-context disambiguation: an alias of the form ``"term@VALUE"`` matches only
when the caller passes ``value_context == VALUE`` (e.g. ``"mode@1000"`` fires for
"mode" + value 1000, not "mode" + value 10000 or "mode" with no value).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ResolveStatus = Literal["resolved", "underspecified", "ambiguous", "no_match"]


@dataclass(frozen=True)
class SynonymResolution:
    resolved: str | None  # canonical Literal member, or None
    status: ResolveStatus
    matched_alias: str | None  # the synonym/underspecified entry that fired


# --- tables (curated per the strict invariant) ------------------------------

TARGET_SPACE_SYNONYMS: dict[str, list[str]] = {
    "MNI152NLin6Asym": [
        "MNI152NLin6Asym",
        "MNI152 NLin6Asym",
        "MNI152 NLin6 Asym",
        "FSL MNI152",  # FSL ships NLin6Asym unambiguously
        "FSL's MNI152",
        "MNI152 (FSL)",
    ],
    "MNI152NLin2009cAsym": [
        "MNI152NLin2009cAsym",
        "MNI152 NLin2009cAsym",
        "MNI152NLin2009c",
        "MNI152 2009c",
        "Fonov 2009c",  # the distinctive published tag
        "Fonov MNI152",
    ],
    "Talairach": ["Talairach", "Talairach atlas"],
    "native_volume": [
        "native space",
        "individual's native space",
        "subject's native space",
        "subject's own space",
    ],
}
# Explicitly NOT mapped — broader than any member (the 7/20 v1 cases v2 coerced).
TARGET_SPACE_UNDERSPECIFIED: list[str] = [
    "MNI",
    "MNI152",
    "MNI standard space",
    "MNI standard",
    "standard MNI",
    "standard space",
    "standard volumetric space",
    "MNI template",
    "MNI atlas",
]

SURFACE_REGISTRATION_SYNONYMS: dict[str, list[str]] = {
    "freesurfer_recon": [
        "freesurfer_recon",
        "FreeSurfer's spherical registration",
        "spherical registration via FreeSurfer",
        "folding-based registration",  # specific operation name
        "sphere.reg",  # FS file produced by recon-all
        "FS recon-all",
    ],
    "msm_sulc": [
        "msm_sulc",
        "MSMSulc",
        "MSM-Sulc",
        "MSM with sulcal depth",
        "multimodal surface matching using sulcal depth",
    ],
    "msm_all": ["msm_all", "MSMAll", "MSM-All", "MSM with multiple modalities"],
}
# "FreeSurfer" alone is insufficient to identify the registration method.
SURFACE_REGISTRATION_UNDERSPECIFIED: list[str] = [
    "FreeSurfer",
    "FreeSurfer-based",
    "via FreeSurfer",
]

TARGET_SURFACE_SYNONYMS: dict[str, list[str]] = {
    "native": ["native midthickness", "native surface", "subject's native surface"],
    "fsaverage": ["fsaverage", "fsaverage template"],
    "fsaverage5": ["fsaverage5", "fsaverage 5"],
    "fsaverage6": ["fsaverage6", "fsaverage 6"],
    "fsLR_32k": ["32k_fs_LR", "fs_LR 32k", "fsLR 32k", "32k grayordinates", "fs_LR_32k"],
    "fsLR_164k": ["164k_fs_LR", "fs_LR 164k", "fsLR 164k", "fs_LR_164k"],
}

INTENSITY_CONVENTION_SYNONYMS: dict[str, list[str]] = {
    "fsl_grand_mean_10000": [
        "fsl_grand_mean_10000",
        "grand-mean scaling@10000",
        "FSL grand-mean@10000",
        "fslmaths -ing@10000",
    ],
    "fsl_median_10000": [
        "fsl_median_10000",
        "median scaling@10000",
        "median@10000",
        "per-volume median@10000",
    ],
    "spm_grand_mean_100": [
        "spm_grand_mean_100",
        "SPM grand-mean@100",
        "grand-mean scaling@100",
    ],
    "voxel_temporal_zscore": [
        "voxel_temporal_zscore",
        "z-score",
        "z-scored",
        "temporal z-score",
        "voxel-wise z-score",
        "per-voxel temporal z-score",
        "subtracting its mean and then dividing by its temporal standard deviation",
    ],
    "global_median_1000": [
        "global_median_1000",
        "global median scaling@1000",
        "median@1000",
        "median = 1,000",
        "Global signal scaling (median = 1,000)",
    ],
    "global_mode_1000": [
        "global_mode_1000",
        "mode@1000",
        "mode value of 1000",
        "mode value of 1,000",
        "normalized to a mode of 1,000",
    ],
}


# --- resolution -------------------------------------------------------------


def _alias_matches(alias: str, raw_lower: str, value_context: float | None) -> bool:
    """``term@VALUE`` matches only when value_context == VALUE; plain ``term``
    matches whenever it is a case-insensitive substring of the raw text."""
    if "@" in alias:
        term, _, val = alias.rpartition("@")
        if value_context is None:
            return False
        try:
            if float(val) != float(value_context):
                return False
        except ValueError:
            return False
        return term.lower() in raw_lower
    return alias.lower() in raw_lower


def resolve_to_literal(
    raw: str | None,
    synonyms: dict[str, list[str]],
    underspecified_aliases: list[str] | None = None,
    value_context: float | None = None,
) -> SynonymResolution:
    """Resolve a free-text term to a unique canonical member, or flag why not."""
    if raw is None or not str(raw).strip():
        return SynonymResolution(None, "no_match", None)
    raw_lower = str(raw).lower()

    matched: dict[str, str] = {}
    for member, aliases in synonyms.items():
        for alias in aliases:
            if _alias_matches(alias, raw_lower, value_context):
                matched[member] = alias
                break

    if len(matched) == 1:
        member, alias = next(iter(matched.items()))
        return SynonymResolution(member, "resolved", alias)
    if len(matched) > 1:
        return SynonymResolution(None, "ambiguous", None)

    if underspecified_aliases:
        for ua in underspecified_aliases:
            if ua.lower() in raw_lower:
                return SynonymResolution(None, "underspecified", ua)
    return SynonymResolution(None, "no_match", None)


# Bare-field-id -> (synonyms, underspecified) used by the extractor.
SYNONYMS_BY_FIELD: dict[str, tuple[dict[str, list[str]], list[str] | None]] = {
    "target_space": (TARGET_SPACE_SYNONYMS, TARGET_SPACE_UNDERSPECIFIED),
    "surface_registration": (SURFACE_REGISTRATION_SYNONYMS, SURFACE_REGISTRATION_UNDERSPECIFIED),
    "target_surface": (TARGET_SURFACE_SYNONYMS, None),
    "convention": (INTENSITY_CONVENTION_SYNONYMS, None),
}
