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

import functools
import re
from dataclasses import dataclass
from typing import Literal

from extractor_mvp.span_resolver import _EXPLICIT_NORMALIZATIONS, _hyphenation_drop_indices

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
        # REMOVED 2026-10-26, by the author's ruling (DELTA_value_in_quote_step_fields.md §7.7):
        # the phrase forms "FSL MNI152", "FSL's MNI152" and "MNI152 (FSL)". A tool-generic MNI
        # reference resolves FAMILY-level per target_space protocol CALL 2 (:168, :186-188); the
        # template FSL ships is a tool fact for the inference arm, to be carried by the KB once
        # kb/tools has a reader (backlog). Such a phrase now falls to the underspecified list via
        # its "MNI152" token, i.e. resolution="underspecified", resolved=None. No committed cell
        # had ever resolved through these forms (§7.2). The FILE forms below stay: a file name
        # identifies the template (CALL 2's oconnor case).
        # FSL standard-template FILE forms — FSL ships NLin6Asym; the file IS that template
        # (verified vs FSL docs + TemplateFlow + Lead-DBS). Safe identity, NOT silent substitution.
        # Substring-matched, so "MNI152T1_2mm" covers "...MNI152T1_2mm_brain.nii.gz". Fires only when
        # the model extracts the file form as the value; a bare "MNI" value stays family-specified.
        "MNI152_T1_2mm",
        "MNI152T1_2mm",
        "MNI152_T1_1mm",
        "MNI152T1_1mm",
        "MNI152_T1_2mm_brain",
        "MNI152T1_2mm_brain",
    ],
    "MNI152NLin2009cAsym": [
        "MNI152NLin2009cAsym",
        "MNI152 NLin2009cAsym",
        "MNI152NLin2009c",
        "MNI152 2009c",
        "Fonov 2009c",  # the distinctive published tag
        "Fonov MNI152",
        # D2c (2026-11-25, C13): ladouceur_2023 writes the template's name out
        "ICBM 152 Nonlinear Asymmetrical template version 2009c",
    ],
    "Talairach": ["Talairach", "Talairach atlas"],
    "native_volume": [
        "native space",
        "individual's native space",
        "subject's native space",
        "subject's own space",
    ],
    # study_specific (v0.4.1): a template CONSTRUCTED for the study. Key on CONSTRUCTION, not the
    # bare word "subject-specific" (native-space-ambiguous) — every form here carries "template"
    # (a constructed reference) or explicit construction phrasing, the discriminator vs native_volume.
    "study_specific": [
        "study-specific template",
        "study specific template",
        "sample-specific template",
        "cohort-specific template",
        "custom template",
        "subject-specific anatomical template",  # mueller (ANTs-constructed)
        "subject-specific template",
        "multivariate template construction",  # ANTs template-construction phrasing
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
    # D2c (2026-11-25, the author's ruling C13): the family under its other two names. Until now
    # they were read for the report's note only (coverage_fields.FAMILY_NAMES). "ICBM" also
    # reads "ICBM152" and "ICBM 152", as "MNI" reads "MNI152".
    "Montreal Neurological Institute",
    "ICBM",
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
    # D2c (2026-11-25, the author's ruling C13): "MSM" with no variant names the family
    "MSM",
]

#: D2c (2026-11-25, the author's ruling C13): "fs_LR" with no density names the family and no
#: mesh. An entry is read as a plain substring, with no folding of separators, so each spelling
#: of the joint is listed.
TARGET_SURFACE_UNDERSPECIFIED: list[str] = ["fs_LR", "fsLR", "fs-LR", "fs LR"]

#: The entries of the family lists that D2c added: the five family names of C13 ("CompCor" among
#: them, whose list is coverage_fields.COMPCOR_UNDERSPECIFIED). They give a term its status,
#: "underspecified". The quote check does not read them as it reads the older entries: a value
#: that holds only such a name must stand in its quote in its own words, as it had to before D2c
#: (quote_support._family_term_supported). So the move changes a status and no outcome of the
#: check. It does change the report's note: an entry is a plain substring, so a name glued to
#: more text ("fs_LR32k", "MSMv3") holds a family term now, and the report no longer says of it
#: that it is outside the vocabulary (coverage_fields.names_no_member).
FAMILY_NAME_ENTRIES: frozenset[str] = frozenset(
    {"Montreal Neurological Institute", "ICBM", "MSM", "CompCor", *TARGET_SURFACE_UNDERSPECIFIED}
)

TARGET_SURFACE_SYNONYMS: dict[str, list[str]] = {
    "native": ["native midthickness", "native surface", "subject's native surface"],
    "fsaverage": ["fsaverage", "fsaverage template"],
    "fsaverage5": ["fsaverage5", "fsaverage 5", "fsaverge5"],  # observed typo (Chen p4)
    "fsaverage6": ["fsaverage6", "fsaverage 6"],
    "fsLR_32k": [
        "32k_fs_LR",
        "fs_LR 32k",
        "fsLR 32k",
        "32k grayordinates",
        "fs_LR_32k",
        # D2b (2026-11-25): marek_2022's text layer prints the token split, "32 k fs_LR"
        "32 k fs_LR",
    ],
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


def _fold_separators(s: str) -> str:
    """Underscore, hyphen and space are one separator (the author's item 3, 2026-10-28): a model
    writing ``cerebrospinal_fluid`` or ``boundary-based`` meets an alias written with spaces."""
    return " ".join(s.replace("_", " ").replace("-", " ").split())


#: Hyphens a PDF text layer prints in place of "-" (U+2010 hyphen, U+2011 non-breaking hyphen,
#: U+2012 figure dash, U+FE63 small hyphen-minus, U+FF0D full-width hyphen-minus). The en dash, the
#: em dash and the minus sign are in span_resolver's table already.
_HYPHENS = "\u2010\u2011\u2012\ufe63\uff0d"
#: Characters with no width, dropped: the soft hyphen, the zero-width space, non-joiner and joiner,
#: the word joiner and the byte-order mark. "field\u00admap" is "fieldmap" to a reader.
_INVISIBLE = "\u00ad\u200b\u200c\u200d\u2060\ufeff"


def repair_text(raw: str) -> str:
    """The text as a reader sees it, for MATCHING only (D2b, 2026-11-25; the stored words are never
    changed). The D1 token trace found paper terms hidden from the alias tables by a ligature and
    by dashes; the review of this change added the Unicode hyphens and the invisible characters,
    which let "fieldmap\u2010less" and "HD\u2010BET" past the rules written for them.

    One character at a time, by an explicit table: span_resolver's (ligatures, the en and em dash,
    the minus sign, curly quotes, the no-break space, the multiplication sign) and the hyphens of
    :data:`_HYPHENS`; the characters of :data:`_INVISIBLE` are dropped. Nothing else is folded:

    - no NFKD. It turns a trademark sign or a footnote superscript into letters or digits joined to
      the word before it ("MATLAB(TM)" as one word, "BET1"), which hides the alias;
    - not span_resolver's split-measurement rule. It joins an article to a number ("a 24 parameter
      model" becomes "a24 parameter model"). Both are harmless where the quote and the text are
      normalized alike, and not here, where only this side is.
    """
    out: list[str] = []
    for ch in raw:
        if ch in _INVISIBLE:
            continue
        if ch in _HYPHENS:
            out.append("-")
        else:
            out.append(_EXPLICIT_NORMALIZATIONS.get(ch, ch))
    return "".join(out)


def _rejoin_line_wraps(text: str) -> str:
    """``text`` with a word that a line break split at a hyphen put back together ("Butter-",
    newline, "worth"). Used only as a second reading, when the first names no member: a real
    compound split at the same place ("rigid-", newline, "body") must keep its hyphen."""
    drops = _hyphenation_drop_indices(text)
    return "".join(ch for i, ch in enumerate(text) if i not in drops)


@functools.lru_cache(maxsize=4096)
def _alias_regex(alias_folded: str) -> re.Pattern[str]:
    """The alias as whole words of the raw text (2026-11-24, the author's ruling on the resolver
    audit): "optiBET" no longer resolves through the alias "BET". A boundary is any character that
    is not a letter or a digit, or the end of the text; a plural "s" after the alias is allowed
    ("grayordinates" for the alias "grayordinate"). Spaces are tolerated around a slash the alias
    holds ("blip up / blip down", D2b). No other whitespace is tolerated: a token the text layer
    split ("B 0", "32 k fs_LR") is an alias of its own, taken from the paper that prints it.

    An alias that ends in a digit names a whole number (D2b): no decimal part or thousands group
    may follow it. "fsaverage 5.3" holds the number 5.3 (a FreeSurfer release), not the mesh
    density 5, and "mode value of 1,000,000" is not the alias "mode value of 1,000". A citation
    number set against such an alias ("SPM12,23") leaves it unmatched too, which costs a member
    and never gives a wrong one."""
    body = re.escape(alias_folded).replace("/", r"\s*/\s*")
    whole_number = r"(?![.,]\d)" if alias_folded[-1:].isdigit() else ""
    return re.compile(rf"(?<![a-z0-9]){body}s?(?![a-z0-9]){whole_number}")


def _phrase_in(alias_folded: str, raw_folded: str) -> bool:
    """Whether the alias occurs as whole words of the raw text (see :func:`_alias_regex`)."""
    return bool(_alias_regex(alias_folded).search(raw_folded))


def _alias_term(alias: str, value_context: float | None) -> str | None:
    """The folded term an alias searches for, or None when its ``@VALUE`` gate does not pass:
    ``term@VALUE`` counts only when value_context == VALUE."""
    if "@" not in alias:
        return _fold_separators(alias.lower())
    term, _, val = alias.rpartition("@")
    if value_context is None:
        return None
    try:
        if float(val) != float(value_context):
            return None
    except ValueError:
        return None
    return _fold_separators(term.lower())


def _alias_matches(alias: str, raw_lower: str, value_context: float | None) -> bool:
    """``term@VALUE`` matches only when value_context == VALUE; plain ``term``
    matches whenever it occurs as whole words of the raw text, case-insensitively, with
    underscore, hyphen and space read as the same separator on both sides."""
    term = _alias_term(alias, value_context)
    return term is not None and _phrase_in(term, _fold_separators(raw_lower))


def members_named(
    raw: str, synonyms: dict[str, list[str]], value_context: float | None = None
) -> dict[str, str]:
    """member -> the first of its aliases that the text names, before any tie is settled.

    D2b (2026-11-25, the author's go-ahead on the D1 table self-check): the longer alias wins. An
    occurrence that lies inside a longer occurrence of ANOTHER member's alias does not count, so
    "slice" inside "middle slice", "FLIRT" inside "FLIRT BBR" and "fieldmap" inside
    "fieldmap-less" no longer make the paper's term ambiguous. Fifteen aliases could not resolve to
    their own member before this. An occurrence elsewhere in the text still counts: "FLIRT, then
    FLIRT BBR" names both members and stays ambiguous.

    One limit, found by the reviews of this change: an alias that ends in a digit wins only when
    its number ends the phrase (nothing follows it, or closing or list punctuation). "fsaverage
    6" is the mesh fsaverage6; in "fsaverage 6 mm FWHM", "fsaverage 6 millimetre kernel" and
    "fsaverage 5 subjects" the number belongs to what follows, and no list of units can be
    closed. There both members stay named and the term stays ambiguous, as it was before D2b.
    Since D2c one of four nouns may follow the density of a mesh where the term is the mesh and
    its noun and nothing else (:data:`_MESH_NOUN_ENDS`): "fsaverage 6 surface" is fsaverage6.

    The text is read as :func:`repair_text` gives it. When that reading names no member and a line
    break split a word at a hyphen, the rejoined text is read instead."""
    repaired = repair_text(str(raw))
    named = _members_named(_fold_separators(repaired.lower()), synonyms, value_context)
    if not named and "\n" in repaired:
        rejoined = _rejoin_line_wraps(repaired)
        if rejoined != repaired:
            named = _members_named(_fold_separators(rejoined.lower()), synonyms, value_context)

    # Token-prefix containment collapse (2026-06, kept as it was): drop member A when its matched
    # alias is a strict prefix-substring of member B's matched alias AND the char in B's alias
    # immediately following the A-substring is alphanumeric (so "fsaverage" beside "fsaverage5"
    # collapses to the more specific 5). Until D2b this rule deliberately left "foo" inside
    # "foo bar" ambiguous; the positional rule now settles that case when the shorter alias
    # occurs only inside the longer one.
    def next_char_alnum(alias_a: str, alias_b: str) -> bool:
        j = alias_b.index(alias_a) + len(alias_a)
        return j < len(alias_b) and alias_b[j].isalnum()

    drops = {
        a
        for a, alias_a in named.items()
        if any(
            b != a
            and alias_a.lower() != alias_b.lower()
            and alias_a.lower() in alias_b.lower()
            and next_char_alnum(alias_a.lower(), alias_b.lower())
            for b, alias_b in named.items()
        )
    }
    return {k: v for k, v in named.items() if k not in drops}


#: What may follow an alias that ends in a digit for its number to end the phrase: nothing, or
#: closing and list punctuation. A word after the number may be what it counts.
_PHRASE_ENDS = re.compile(r"""\s*(?:\Z|[)\],;:.!?"'])""")
#: D2c (2026-11-25, the author's ruling C13): after the density of a mesh one noun may stand that
#: names what the mesh is: "fsaverage 6 surface", "fsaverage 5 space", "the fsaverage 6
#: template", "fsaverage 5 mesh". The list is closed, and so is the wording: the term is the mesh
#: and its noun and nothing else, but for "the" before it and for brackets, quote marks and
#: closing punctuation around it. The wording is read with its separators folded, so a hyphen,
#: a dash or an underscore at either end counts as nothing ("fsaverage 6 surface -"), and the
#: density may carry the plural "s" that every alias may ("fsaverage 6s surface"). A plural of
#: the noun is not in the list ("fsaverage 6 surfaces" may count six surfaces). Only the two
#: meshes take a noun: on any other alias that ends in a digit the number still has to end the
#: phrase.
#:
#: A first form asked only that the noun end its phrase. The term could go on after a comma, and
#: what followed could say that the mesh is another one ("fsaverage 6 template, symm."), so that
#: the term took a member it had not had before D2c (the reviews of D2c). No list of what may
#: not follow can be closed; the whole wording can.
_MESH_MEMBERS = frozenset({"fsaverage5", "fsaverage6"})
_MESH_NOUN_ENDS = re.compile(r"""\s(?:surface|space|template|mesh)[\s)\].,;:!?"']*\Z""")
_MESH_OPENS = re.compile(r"""[\s(\["']*(?:the\s[\s(\["']*)?""")


def _members_named(
    raw_folded: str, synonyms: dict[str, list[str]], value_context: float | None
) -> dict[str, str]:
    # Every whole-word occurrence of every alias, per member, in table order. ``wins``: whether
    # the occurrence takes precedence over a shorter alias of another member inside it.
    found: dict[str, list[tuple[str, int, int, bool]]] = {}
    for member, aliases in synonyms.items():
        for alias in aliases:
            term = _alias_term(alias, value_context)
            if term is None:
                continue
            for m in _alias_regex(term).finditer(raw_folded):
                wins = (
                    not term[-1:].isdigit()
                    or bool(_PHRASE_ENDS.match(raw_folded, m.end()))
                    or (
                        member in _MESH_MEMBERS
                        and bool(_MESH_NOUN_ENDS.match(raw_folded, m.end()))
                        and bool(_MESH_OPENS.fullmatch(raw_folded, 0, m.start()))
                    )
                )
                found.setdefault(member, []).append((alias, m.start(), m.end(), wins))

    def shadowed(member: str, start: int, end: int) -> bool:
        return any(
            other != member and wins and s <= start and end <= e and (e - s) > (end - start)
            for other, occurrences in found.items()
            for _alias, s, e, wins in occurrences
        )

    named: dict[str, str] = {}
    for member, occurrences in found.items():
        for alias, start, end, _wins in occurrences:
            if not shadowed(member, start, end):
                named[member] = alias
                break
    return named


def resolve_to_literal(
    raw: str | None,
    synonyms: dict[str, list[str]],
    underspecified_aliases: list[str] | None = None,
    value_context: float | None = None,
) -> SynonymResolution:
    """Resolve a free-text term to a unique canonical member, or flag why not."""
    if raw is None or not str(raw).strip():
        return SynonymResolution(None, "no_match", None)
    raw_lower = repair_text(str(raw)).lower()
    matched = members_named(str(raw), synonyms, value_context)

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
# temporal_standardization.method — the table build 2 §4c proposed and no build made
# (docs/design/DESIGN_temporal_standardization_build2.md:226-234), built 2026-10-26 FOR THE
# QUOTE-SUPPORT CHECK (quote_support.py; DELTA_value_in_quote_step_fields.md §5 ruling 3). It is
# deliberately NOT in SYNONYMS_BY_FIELD: that map is keyed on the bare field id, "method" is the
# bare id of two fields (motion opts out explicitly), and the author's condition for this change
# was that resolution and raw outputs stay as they are — the field still resolves by exact Literal
# membership (extractor.py, "no synonym table; exact member only"). Seeded from §4c's phrasings,
# with the ellipsis form split into its two halves, plus z-scored / z-scoring stems for Cho 2021's
# wording ("z-scoring the segments"). Kept TIGHT per §4c: the object discrimination (signal vs
# regressor vs component) is the prompt's job and cannot be encoded here — identical words.
TS_METHOD_SYNONYMS: dict[str, list[str]] = {
    "voxel_temporal_zscore": [
        "voxel temporal zscore",
        "voxel-wise temporal z-score",
        "per-voxel temporal z-score",
        "temporal z-score",
        "temporal z-scoring",
        "z-scored over time",
        "z-scored across time",
        "temporally normalized",
        "temporally standardized",
        "temporal standard deviation",
        "z-scored",
        "z-scoring",
        "zscored",
        "zscoring",
    ],
}

SYNONYMS_BY_FIELD: dict[str, tuple[dict[str, list[str]], list[str] | None]] = {
    "target_space": (TARGET_SPACE_SYNONYMS, TARGET_SPACE_UNDERSPECIFIED),
    "surface_registration": (SURFACE_REGISTRATION_SYNONYMS, SURFACE_REGISTRATION_UNDERSPECIFIED),
    "target_surface": (TARGET_SURFACE_SYNONYMS, TARGET_SURFACE_UNDERSPECIFIED),
    "convention": (INTENSITY_CONVENTION_SYNONYMS, None),
}
