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
        "recon-all",  # recon-all is unambiguously FreeSurfer
        "FreeSurfer recon-all",
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
# Bare sphere/spherical registration is FS-vs-MSM ambiguous -> underspecified, not resolved.
SURFACE_REGISTRATION_UNDERSPECIFIED: list[str] = [
    "FreeSurfer",
    "FreeSurfer-based",
    "via FreeSurfer",
    "sphere registration",
    "spherical registration",
]

TARGET_SURFACE_SYNONYMS: dict[str, list[str]] = {
    "native": ["native midthickness", "native surface", "subject's native surface"],
    "fsaverage": ["fsaverage", "fsaverage template"],
    "fsaverage5": ["fsaverage5", "fsaverage 5", "fsaverge5"],  # observed typo (Chen p4)
    "fsaverage6": ["fsaverage6", "fsaverage 6"],
    "fsLR_32k": ["32k_fs_LR", "fs_LR 32k", "fsLR 32k", "32k grayordinates", "fs_LR_32k"],
    "fsLR_164k": ["164k_fs_LR", "fs_LR 164k", "fsLR 164k", "fs_LR_164k"],
}

INTENSITY_CONVENTION_SYNONYMS: dict[str, list[str]] = {
    "fsl_grand_mean_10000": [
        "fsl_grand_mean_10000",
        "grand-mean scaling@10000",
        "grand mean scaling@10000",  # space variant (fixes hyphen false-negative)
        "grand mean@10000",  # space variant; "grand mean" denotes the convention
        "FSL grand-mean@10000",
        "fslmaths -ing@10000",
        "global mean@10000",  # value-context form (Chen "global mean ... to 10,000")
        # Dropped "mean intensity@10000": bare "mean intensity" false-fired on a
        # registration sentence ("registering the mean intensity image") — Marek probe.
        # Direct-phrase fallbacks for when value_context is not supplied.
        "global mean intensity to 10000",
        "global mean intensity to 10,000",
    ],
    "fsl_median_10000": [
        "fsl_median_10000",
        "median scaling@10000",
        "median intensity@10000",
        # Dropped bare "median@10000": "median" alone false-fires on statistics
        # vocabulary (median sample size / effect size) — Marek probe.
        "per-volume median@10000",
    ],
    "spm_grand_mean_100": [
        "spm_grand_mean_100",
        "SPM grand-mean@100",
        "grand-mean scaling@100",
    ],
    # voxel_temporal_zscore intentionally has NO resolver entry: per-voxel temporal
    # z-scoring is not a magnitude-scaling convention, so it must not resolve here
    # (z-score category-error corpus finding). The Literal member + its no-magnitude
    # validator remain in the schema (PATH 0); only this synonym mapping is removed.
    "global_median_1000": [
        "global_median_1000",
        "global median scaling@1000",
        "median scaling@1000",
        "median intensity@1000",
        "median value@1000",
        # Dropped bare "median@1000" (false-fires on statistics vocabulary — Marek probe).
        "median = 1,000",
        "Global signal scaling (median = 1,000)",
    ],
    "global_mode_1000": [
        "global_mode_1000",
        "mode value@1000",
        "mode scaling@1000",
        # Poldrack 2015: the LLM abbreviates the canonical to the token "mode_1000"
        # (drops the "global_" prefix). Value-context-scoped so it fires ONLY with
        # intensity_value==1000. Marek-safe: the underscored token "mode_1000" is not a
        # substring of the false-fire phrases ("default mode", "median sample size"), so
        # this reopens nothing the bare "mode@1000" did.
        "mode_1000@1000",
        # Dropped bare "mode@1000" (false-fires on "default mode" / "mode of covariation"
        # — Marek probe). Direct phrases below still carry the convention unambiguously.
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

    # Token-prefix containment collapse: drop member A when its matched alias is a
    # strict prefix-substring of member B's matched alias AND the char in B's alias
    # immediately following the A-substring is alphanumeric (so "fsaverage" inside
    # "fsaverage5" collapses to the more specific 5, but "foo" inside "foo bar"
    # stays — the next char is a space, so both remain and the result is ambiguous).
    def _next_char_alnum(alias_a: str, alias_b: str) -> bool:
        j = alias_b.index(alias_a) + len(alias_a)
        return j < len(alias_b) and alias_b[j].isalnum()

    drops = {
        a
        for a, alias_a in matched.items()
        if any(
            b != a
            and alias_a.lower() != alias_b.lower()
            and alias_a.lower() in alias_b.lower()
            and _next_char_alnum(alias_a.lower(), alias_b.lower())
            for b, alias_b in matched.items()
        )
    }
    matched = {k: v for k, v in matched.items() if k not in drops}

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
