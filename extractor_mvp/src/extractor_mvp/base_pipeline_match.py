"""base_pipeline value-matching — Tier A (strict identity) and Tier B (alias-equivalent).

PRE-REGISTRATION: this module, INCLUDING ``_TOOLBOX_ALIASES``, is committed to git BEFORE any scoring
run — so no alias entry can be added after seeing a hallucination rate to tune it. Commit-order is the
proof. Tier A and Tier B are pure functions of ``(predicted_list, label_list)``; the labels themselves
are the human labeler's, never produced here.

Matching is NORMALIZE-then-EQUALS on whole tokens with SET MEMBERSHIP (D4). There is NO substring
matching anywhere, in either direction — that is the ``ants ⊂ avants`` / ``\\bspm\\b`` lesson: substring
is unsafe for short names. A predicted list matches a label list iff EVERY predicted element equals
some label element under the tier's equivalence.
"""

from __future__ import annotations

import re

from fmri_defaults_kb.registry import recognize

# wrapper / version-marker words stripped in Tier-A normalization
_STRIP_WORDS = frozenset(
    {"suite", "software", "pipeline", "toolbox", "package", "version", "release", "ver"}
)
# A version TOKEN, boundary-aware. Three shapes only: v-prefixed (v3, v3.4.0), dotted
# (5.0.10, 20.2.1, 1.1-beta), or a bare integer standing alone (the "12" in "… Mapping 12").
# Crucially NOT digits glued to a name (3dvolreg, fsl6): the old greedy trailing `[a-z-]*` ate
# such names (`normalize("3dvolreg")==""`). An alpha suffix is now consumed ONLY when
# hyphen-attached to a real v-/dotted version (…-beta, …-rc1) — never bare trailing letters.
_VERSION = re.compile(
    r"\bv\d+(?:\.\d+)*(?:-[a-z0-9]+)*\b"  # v3, v3.4.0, v1-rc1
    r"|\b\d+(?:\.\d+)+(?:-[a-z0-9]+)*\b"  # 5.0.10, 20.2.1, 1.1-beta
    r"|\b\d+\b",  # bare integer token: the "12" in "Statistical Parametric Mapping 12"
    re.IGNORECASE,
)
_SPM_FUSED = re.compile(r"\bspm\s*(?:99|2|5|8|12)\b", re.IGNORECASE)  # SPM99/2/5/8/12 -> spm


def normalize(x: str) -> str:
    """Tier-A canonical string: lowercase; fused SPM digits -> ``spm``; strip version tokens,
    punctuation, whitespace, and wrapper words; concatenate the surviving WHOLE tokens.

    The concatenation is only ever used with ``==`` (never ``in``), so ``fsl`` cannot match inside
    ``fslsuite`` — wrapper words are removed as whole tokens before joining.
    """
    s = x.lower()
    s = _SPM_FUSED.sub(" spm ", s)  # before the generic version strip, or "12" would be eaten first
    s = _VERSION.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return "".join(t for t in s.split() if t and t not in _STRIP_WORDS)


# PRE-REGISTERED toolbox alias table — for toolboxes NOT in the KB. Maps a NORMALIZED surface variant
# to a canonical id. The 4 KB pipelines (ccs / cpac / fmriprep / hcp_minimal) are handled by
# recognize(), not here. Every entry is a decision that two strings name the same tool; committed
# before any score.
_TOOLBOX_ALIASES: dict[str, str] = {}


def _register(canon: str, *surface_variants: str) -> None:
    for v in surface_variants:
        _TOOLBOX_ALIASES[normalize(v)] = canon


_register("spm", "SPM", "Statistical Parametric Mapping")
_register("fsl", "FSL", "FMRIB Software Library", "FMRIB")
_register("afni", "AFNI", "Analysis of Functional NeuroImages", "MCW-AFNI")
_register("freesurfer", "FreeSurfer")
_register("ants", "ANTs", "Advanced Normalization Tools")
_register("brainvoyager", "BrainVoyager")


def _canon_b(x: str) -> str:
    """Tier-B canonical id: KB recognize() for the 4 KB pipelines, else the pre-registered toolbox
    alias (falling back to the Tier-A normal form)."""
    kb = recognize(x)
    if kb:
        return f"kb:{kb}"
    n = normalize(x)
    return f"tb:{_TOOLBOX_ALIASES.get(n, n)}"


def matches_tier_a(predicted: list[str], label: list[str]) -> bool:
    """Strict identity: every predicted element's Tier-A normal form is in the label's normal-form
    set. Empty prediction never matches a (non-empty) label."""
    if not predicted:
        return False
    label_norms = {normalize(x) for x in label}
    return all(normalize(p) in label_norms for p in predicted)


def matches_tier_b(predicted: list[str], label: list[str]) -> bool:
    """Alias-equivalent: Tier-A normal-form OR Tier-B canonical id (KB recognize / alias table)."""
    if not predicted:
        return False
    label_norms = {normalize(x) for x in label}
    label_canon = {_canon_b(x) for x in label}
    return all(normalize(p) in label_norms or _canon_b(p) in label_canon for p in predicted)
