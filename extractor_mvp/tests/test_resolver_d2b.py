"""D2b (2026-11-25): the table faults the D1 audit found (DESIGN_prompt_schema_2026-11 A6).

Until D1 the extraction model had returned bare member tokens for most values, so the alias tables
had met few real wordings. The self-check below is the standing form of D1's finding: every alias,
given as the wording, resolves to its own member. The other tests pin each fix with the wording
that failed and a nearby wording that must keep working.
"""

from __future__ import annotations

import typing

import pytest

from extractor_mvp import extractor as ex
from extractor_mvp.coverage_fields import (
    COVERAGE_SPECS,
    SHARED_VOCABULARY_FIELDS,
    TERM_RULES,
    names_no_member,
    rule_hits,
    rules_name,
    vocabulary_table,
)
from extractor_mvp.synonym_resolver import (
    _HYPHENS,
    _INVISIBLE,
    SYNONYMS_BY_FIELD,
    repair_text,
    resolve_to_literal,
)

_SPEC = {s.dotted: s for s in COVERAGE_SPECS if s.value_kind in ("term", "term_list")}
_SHARED = {
    dotted: (field_id, literal_type)
    for _attr, field_id, dotted, literal_type, _t in ex._FIELD_SPECS
    if literal_type is not None and field_id in SYNONYMS_BY_FIELD
}


def _terms(dotted: str, raw: str) -> list[typing.Any]:
    """The value as ``extractor._process_field`` resolves it: a list field is split, then each
    item resolved; a term field is resolved whole."""
    s = _SPEC[dotted]
    syn = (s.synonyms, s.underspecified) if s.synonyms else None
    if s.value_kind == "term_list":
        items = ex._field_items(dotted, raw, s.literal_type, syn)
        return ex._resolve_term_list(items, s.literal_type, syn, dotted)
    return [ex._resolve_term(raw, s.literal_type, syn, dotted)]


def _resolved(dotted: str, raw: str) -> list[str | None]:
    return [t.resolved for t in _terms(dotted, raw)]


def _one(dotted: str, raw: str) -> str | None:
    (member,) = _resolved(dotted, raw)
    return member


# --- the table self-check -------------------------------------------------------------------


def test_the_vocabulary_is_39_fields() -> None:
    assert len(_SPEC) == 35 and len(_SHARED) == 4


def test_every_alias_resolves_to_its_own_member() -> None:
    """D1 found 15 of 448 that did not ("middle slice", "FLIRT BBR", "fieldmap-less", "fsaverage 5",
    "blip-up/blip-down"). An alias that cannot reach its member is dead weight in the table, and
    the paper's term it stands for goes unresolved."""
    failures = []
    checked = 0
    for dotted, s in _SPEC.items():
        for member, aliases in (s.synonyms or {}).items():
            for alias in aliases:
                checked += 1
                if _resolved(dotted, alias) != [member]:
                    failures.append((dotted, member, alias, _resolved(dotted, alias)))
    for dotted, (field_id, _literal) in _SHARED.items():
        syns, under = SYNONYMS_BY_FIELD[field_id]
        for member, aliases in syns.items():
            for alias in aliases:
                checked += 1
                term, _, value = alias.rpartition("@") if "@" in alias else (alias, "", "")
                got = resolve_to_literal(term, syns, under, float(value) if value else None)
                if got.resolved != member:
                    failures.append((dotted, member, alias, [got.resolved]))
    assert checked >= 448
    assert failures == []


def test_every_member_token_resolves_to_itself_or_to_its_ruled_target() -> None:
    for dotted, s in _SPEC.items():
        overrides = TERM_RULES[dotted].exact_overrides if dotted in TERM_RULES else {}
        for member in typing.get_args(s.literal_type):
            assert _one(dotted, member) == overrides.get(member, member), (dotted, member)


# --- the longer alias wins --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        ("slice_time_correction.reference", "middle slice", "middle"),
        ("slice_time_correction.reference", "the first slice in time", "first"),
        ("slice_time_correction.reference", "relative to the middle of the TR", "specific_time"),
        ("slice_time_correction.reference", "slice 17", "specific_slice"),  # control
        ("coregistration.method", "FLIRT with BBR", "flirt_bbr"),
        ("coregistration.method", "FLIRT", "flirt"),  # control
        ("coregistration.method", "FLIRT, then FLIRT BBR", None),  # two mentions: ambiguous
        ("distortion_correction.source", "Fieldmap-less", "fieldmap_less"),
        ("slice_time_correction.reference", "TR/2 (middle slice)", None),  # two members named
    ],
)
def test_an_alias_inside_a_longer_alias_of_another_member_does_not_count(
    dotted: str, raw: str, want: str | None
) -> None:
    assert _one(dotted, raw) == want


def test_target_surface_with_a_space_before_the_density() -> None:
    syns, under = SYNONYMS_BY_FIELD["target_surface"]
    assert resolve_to_literal("fsaverage 5", syns, under).resolved == "fsaverage5"
    assert resolve_to_literal("fsaverage-6", syns, under).resolved == "fsaverage6"
    assert resolve_to_literal("fsaverage", syns, under).resolved == "fsaverage"  # control
    # the whole-word rule of 2026-11-24 stands: no member for an unlisted density
    assert resolve_to_literal("fsaverage4", syns, under).resolved is None


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # the number ends the phrase: it is the mesh density
        ("fsaverage 6", "fsaverage6"),
        ("fsaverage 6.", "fsaverage6"),
        ("(fsaverage 6)", "fsaverage6"),
        ("[fsaverage 6]", "fsaverage6"),
        ("fsaverage 6; smoothed", "fsaverage6"),
        ("fsaverage 5: 10,242 vertices", "fsaverage5"),
        ('"fsaverage 6"', "fsaverage6"),
        ("'fsaverage 6'", "fsaverage6"),
        ("fsaverage 6!", "fsaverage6"),
        ("fsaverage 6?", "fsaverage6"),
        ("fsaverage 5, 6 mm FWHM", "fsaverage5"),
        ("fsaverage 6 , smoothed", "fsaverage6"),  # a text layer's space before the punctuation
        ("( fsaverage 6 )", "fsaverage6"),
        ("projected to fsaverage-6", "fsaverage6"),
        ("fsaverage6 surface", "fsaverage6"),  # written as one word, the density is not in doubt
        # a word follows the number and may be what it counts: both members named, as before D2b
        ("fsaverage 6 mm FWHM", None),
        ("fsaverage-6 mm FWHM smoothing", None),
        ("fsaverage 6 millimeter FWHM", None),
        ("fsaverage 6-millimetre kernel", None),
        ("fsaverage 6 FWHM", None),
        ("fsaverage 6 (mm)", None),
        ("fsaverage 6 [mm]", None),
        ("fsaverage 6\u339c FWHM", None),
        ("fsaverage 6 cm", None),
        ("fsaverage 5 subjects", None),
        ("fsaverage 6 runs", None),
        # D2c (2026-11-25, C13): one of four nouns may follow the density and end the phrase
        ("fsaverage 6 surface", "fsaverage6"),
        ("fsaverage 6 (40,962 vertices)", None),
        # a decimal part or a thousands group: the alias's number is not in the text at all
        ("fsaverage 5.3", "fsaverage"),
        ("fsaverage 5,3", "fsaverage"),
        ("fsaverage5.3", None),
        # the whole-word boundary of 2026-11-24, unchanged: "6mm" is not the word "6"
        ("fsaverage 6mm", "fsaverage"),
    ],
)
def test_an_alias_that_ends_in_a_digit_wins_only_when_its_number_ends_the_phrase(
    raw: str, want: str | None
) -> None:
    syns, under = SYNONYMS_BY_FIELD["target_surface"]
    assert resolve_to_literal(raw, syns, under).resolved == want


def test_the_whole_number_rule_on_the_other_digit_aliases() -> None:
    assert _one("slice_time_correction.reference", "TR/2") == "specific_time"  # control
    assert _one("slice_time_correction.reference", "TR/2.") == "specific_time"  # a full stop
    assert _one("slice_time_correction.reference", "TR/2.5") is None
    assert _one("intensity_correction.method", "N4") == "n4"  # control
    assert _resolved("distortion_correction.source", "B0, 3 T") == ["susceptibility_fieldmap", None]
    # the two rules are for an alias that ends in a digit: a word after a digit-final alias that
    # holds no other member's alias changes nothing, and a number after a letter-final alias
    # (a citation set against the name) does not hide it
    assert _one("intensity_correction.method", "N4 bias field correction") == "n4"
    assert _resolved("distortion_correction.source", "B 0 distortions") == [
        "susceptibility_fieldmap"
    ]
    assert _one("brain_extraction.method", "BET,3") == "bet"
    assert _one("brain_extraction.method", "BET.5") == "bet"
    syns, under = SYNONYMS_BY_FIELD["convention"]
    assert resolve_to_literal("mode value of 1000", syns, under).resolved == "global_mode_1000"
    assert resolve_to_literal("mode value of 1000.5", syns, under).resolved is None
    assert resolve_to_literal("mode value of 1,000,000", syns, under).resolved is None


# --- the SPM releases ---------------------------------------------------------------------------


_SPM_FIELDS = [
    ("slice_time_correction.method", "spm_slice_timing"),
    ("nuisance_regression.method", "spm"),
    ("segmentation.method", "spm_segment"),
    ("coregistration.method", "spm_coreg"),
    ("spatial_smoothing.method", "spm_smooth"),
]


def test_every_field_with_an_spm_alias_has_the_release_rules() -> None:
    with_spm = {
        (dotted, member)
        for dotted, s in _SPEC.items()
        for member, aliases in (s.synonyms or {}).items()
        if "SPM" in aliases
    }
    assert with_spm == set(_SPM_FIELDS)
    for dotted, member in _SPM_FIELDS:
        assert set(TERM_RULES[dotted].require_all) == {member}
        assert set(TERM_RULES[dotted].named_by) == {member}


@pytest.mark.parametrize(("dotted", "member"), _SPM_FIELDS)
def test_an_spm_release_named_alone_is_the_spm_member(dotted: str, member: str) -> None:
    for release in ("SPM99", "SPM2", "SPM5", "SPM8", "SPM12", "SPM25"):
        assert _one(dotted, release) == member, release
        # a beta: maheu_2011 prints "SPM99b" and silchenko_2023 "SPM12b"
        assert _one(dotted, release + "b") == member, release
    assert _one(dotted, "SPM") == member  # control: the bare name, as before
    for alone in ("spm12", "the SPM12 software", "SPM12 package", "(SPM12)", "SPM12."):
        assert _one(dotted, alone) == member, alone
        assert rules_name(dotted, alone) == {member}, alone
    # written apart, "SPM" is a word of its own and the bare alias resolves it, as before D2b
    for apart in ("SPM 12", "spm-8", "SPM_12", "SPM\u201012"):
        assert _one(dotted, apart) == member, apart
        assert rules_name(dotted, apart) == set(), apart
    # a closed list, not a rule that lets digits follow any alias: "SPM" with a number the list
    # lacks names the SPM member (no other member can take the term, and the report makes no
    # claim about it) and does not resolve
    for unlisted in ("SPM13", "SPM96", "SPM12c"):
        assert _one(dotted, unlisted) is None, unlisted
        assert rules_name(dotted, unlisted) == {member}, unlisted
        assert names_no_member(dotted, unlisted) is False, unlisted
    for other in ("SPMx", "xSPM12", "SPM123", "SPM12bc"):
        assert _one(dotted, other) is None, other
        assert rules_name(dotted, other) == set(), other
    # "SPM" as a word of its own is the bare alias, whatever follows it: as before D2b
    assert _one(dotted, "SPM 3") == member and rules_name(dotted, "SPM 3") == set()


@pytest.mark.parametrize(("dotted", "member"), _SPM_FIELDS)
def test_an_spm_release_inside_a_longer_wording_names_the_member_and_does_not_resolve(
    dotted: str, member: str
) -> None:
    """A toolbox that runs on SPM is not SPM's own tool for the step (C3), and the toolboxes
    cannot be listed: the release resolves only when it is the whole wording."""
    for raw in (
        "CONN toolbox (SPM12)",
        "DPARSF (based on SPM8)",
        "the rest of the SPM12 pipeline",
        "run in SPM12",
        "SPM12 (v7771)",
        "SPM12 toolbox",
    ):
        assert _one(dotted, raw) is None, raw
        assert rules_name(dotted, raw) == {member}, raw
        assert names_no_member(dotted, raw) is False, raw  # the report makes no claim about it
    assert rules_name(dotted, "SPM") == set()  # the bare name is an alias, as before
    assert names_no_member(dotted, "CONN toolbox") is True  # control: nothing of the vocabulary
    # joined by an underscore, as a function or a build is written
    assert rules_name(dotted, "SPM12_r7771") == {member}
    assert names_no_member(dotted, "spm8_smooth") is False


def test_an_spm_release_beside_another_member_is_ambiguous_not_the_other_member() -> None:
    # was `custom` through "MATLAB", once the whole-word rule had stopped "SPM12" matching "SPM"
    assert _one("nuisance_regression.method", "SPM12 in MATLAB") is None
    assert _one("nuisance_regression.method", "SPM12b in MATLAB") is None
    assert _one("nuisance_regression.method", "SPM96 in MATLAB") is None  # a release the list lacks
    assert _one("nuisance_regression.method", "in-house MATLAB scripts") == "custom"  # control
    assert _one("coregistration.method", "FLIRT, on images segmented in SPM8") is None
    assert _one("coregistration.method", "FLIRT, on segmented images") == "flirt"  # control
    assert _one("spatial_smoothing.method", "SUSAN (not SPM12)") is None
    # an alias of the SPM member itself still resolves beside its release
    assert _one("segmentation.method", "SPM12 unified segmentation") == "spm_segment"
    assert _one("segmentation.method", "SPM12 segmentation") == "spm_segment"
    assert _one("coregistration.method", "SPM8 coregister") == "spm_coreg"
    assert _one("spatial_smoothing.method", "SPM (release SPM12)") == "spm_smooth"


# --- the text the tables match on ---------------------------------------------------------------


def test_text_artifacts_no_longer_hide_a_term() -> None:
    ligature = "\ufb01eld\nmap"  # poldrack_2015's text layer
    assert _resolved("distortion_correction.method", ligature) == ["fieldmap"]
    assert _one("temporal_filtering.pass_type", "band\u2013pass") == "band_pass"  # en dash
    # a token the text layer split is an alias taken from the paper that prints it
    assert _resolved("distortion_correction.source", "B 0 distortions") == [
        "susceptibility_fieldmap"
    ]  # hagler_2019
    syns, under = SYNONYMS_BY_FIELD["target_surface"]
    assert resolve_to_literal("32 k fs_LR", syns, under).resolved == "fsLR_32k"  # marek_2022
    # ... and not a general tolerance: FAST's class flag "-n 3" is not the alias "N3"
    assert _one("intensity_correction.method", "FAST -B -n 3") == "fast_bias"
    assert _one("intensity_correction.method", "-n 4") is None
    assert _one("intensity_correction.method", "N4") == "n4"  # control


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        # U+2010 and U+2011: the hyphens a PDF text layer prints
        ("distortion_correction.source", "fieldmap\u2010less", ["fieldmap_less"]),
        ("distortion_correction.method", "fieldmap\u2010less", ["fieldmap_less"]),  # schema 0.8.0
        ("distortion_correction.method", "fieldmap\u2011free", [None]),
        ("brain_extraction.method", "HD\u2010BET", [None]),
        ("coregistration.method", "FLIRT\u2010BBR", ["flirt_bbr"]),
        ("temporal_filtering.pass_type", "high\u2010pass", ["high_pass"]),
        ("slice_time_correction.reference", "0.5 of slice\u2010acquisition range", [None]),
        # a soft hyphen and a zero-width space inside a word are not there for a reader
        ("distortion_correction.method", "field\u00admap", ["fieldmap"]),
        ("coregistration.method", "FLIRT\u200b BBR", ["flirt_bbr"]),
    ],
)
def test_unicode_hyphens_and_invisible_characters_are_read_as_a_reader_reads_them(
    dotted: str, raw: str, want: list[str | None]
) -> None:
    terms = _terms(dotted, raw)
    assert [t.resolved for t in terms] == want
    assert [t.verbatim for t in terms] == [raw]  # the stored words are never repaired


def test_a_mark_after_a_tool_name_does_not_hide_it() -> None:
    """The first build folded every compatibility character (NFKD): a trademark sign became "TM"
    and a footnote superscript a digit, joined to the word, and the alias no longer matched."""
    assert repair_text("MATLAB\u2122") == "MATLAB\u2122"
    assert _one("nuisance_regression.method", "MATLAB\u2122") == "custom"
    assert _one("brain_extraction.method", "BET\u00b9") == "bet"
    syns, under = SYNONYMS_BY_FIELD["target_surface"]
    assert resolve_to_literal("fsaverage\u2075", syns, under).resolved == "fsaverage"


def test_a_line_break_at_a_hyphen_keeps_a_compound_and_rejoins_a_split_word() -> None:
    assert _one("coregistration.transform", "rigid-\nbody") == "rigid"
    assert _one("nuisance_regression.motion_expansion", "24-\nparameter") == "friston24"
    assert _resolved("ica_denoise.method", "ICA-\nAROMA") == ["aroma"]
    # the rejoined reading is tried only when the first one names no member
    assert _one("temporal_filtering.filter_type", "Butter-\nworth") == "butterworth"


def test_the_stored_words_are_never_repaired() -> None:
    ligature = "\ufb01eld map"
    (term,) = _terms("distortion_correction.method", ligature)
    assert term.verbatim == ligature and term.resolved == "fieldmap"


def test_an_article_is_not_joined_to_a_number() -> None:
    # span_resolver's split-measurement rule would turn "a 24" into "a24"; it is not applied here
    assert repair_text("a 24 parameter model") == "a 24 parameter model"
    assert _one("nuisance_regression.motion_expansion", "a 24 parameter model") == "friston24"
    assert _one("coregistration.transform", "a 6 DOF transformation") == "rigid"


# --- the block rules ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        # the opposite method, through "fieldmap". Since schema 0.8.0 the method field holds the
        # family (fieldmap_less) and its longer alias wins; the block is for the forms no alias
        # holds
        ("distortion_correction.method", "fieldmap-less", ["fieldmap_less"]),
        ("distortion_correction.method", "field map-less", ["fieldmap_less"]),
        ("distortion_correction.method", "fieldmap-free", [None]),
        ("distortion_correction.method", "field map-free", [None]),
        (
            "distortion_correction.method",
            "\ufb01eldmap-less",
            ["fieldmap_less"],
        ),  # the table reads repaired text
        (
            "distortion_correction.method",
            "\ufb01eldmap-free",
            [None],
        ),  # ... and so does the rule
        ("distortion_correction.method", "field map", ["fieldmap"]),  # control
        ("distortion_correction.source", "fieldmap-free", [None]),
        ("distortion_correction.source", "field map", ["susceptibility_fieldmap"]),  # control
        # another tool, through "BET"
        ("brain_extraction.method", "HD-BET", [None]),
        ("brain_extraction.method", "HD BET (Isensee et al., 2019)", [None]),
        ("brain_extraction.method", "FSL BET", ["bet"]),  # control
        # a time, through "slice"
        ("slice_time_correction.reference", "0.5 of slice acquisition range", [None]),
        ("slice_time_correction.reference", "reference slice 1", ["specific_slice"]),  # control
        # the subject's own surface, through "cortical surface"
        ("spatial_smoothing.space", "native cortical surface", [None]),
        ("spatial_smoothing.space", "each subject's cortical surface", [None]),
        ("spatial_smoothing.space", "individual subjects\u2019 cortical surfaces", [None]),
        ("spatial_smoothing.space", "cortical surface", ["template_surface"]),  # control
        ("spatial_smoothing.space", "fsaverage cortical surface", ["template_surface"]),  # control
        # twelve parameters, through "six motion parameters"
        (
            "nuisance_regression.motion_expansion",
            "six motion parameters and their first differences",
            [None],
        ),
        ("nuisance_regression.motion_expansion", "six motion parameters", ["6param"]),  # control
    ],
)
def test_a_wrong_member_is_blocked_and_the_words_are_kept(
    dotted: str, raw: str, want: list[str | None]
) -> None:
    terms = _terms(dotted, raw)
    assert [t.resolved for t in terms] == want
    assert [t.verbatim for t in terms] == [raw]


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # "derived" and "different" are not a derivative and a difference
        ("six motion parameters derived from the realignment step", "6param"),
        ("six motion parameters, estimated separately for the different runs", "6param"),
        ("the 6 realignment parameters derived by MCFLIRT", "6param"),
        # no derivative is stated, so this is not the 24-parameter model; the squares block 6param
        ("six motion parameters derived from MCFLIRT and their squares", None),
        # controls: the rules of 2026-11-24 still hold (a derivative without squares is 12param
        # since schema 0.8.0; before, no member fitted and the words were kept)
        ("six motion parameters and their temporal derivatives", "12param"),
        ("six parameters, their derivatives and squares", "friston24"),
        ("6 motion parameters and their backward differences", None),
        ("motion parameters after temporal differencing, six in all", None),
    ],
)
def test_derived_and_different_are_not_derivative_and_difference(
    raw: str, want: str | None
) -> None:
    assert _one("nuisance_regression.motion_expansion", raw) == want


# --- the list splitter --------------------------------------------------------------------------


def _split(dotted: str, raw: str) -> list[str]:
    s = _SPEC[dotted]
    return ex._field_items(dotted, raw, s.literal_type, (s.synonyms, s.underspecified))


def test_nested_parentheses_are_one_piece() -> None:
    raw = "white matter and CSF (eroded masks (2 voxels), mean signal)"
    assert _split("nuisance_regression.tissue_regressors", raw) == [
        "white matter",
        "CSF (eroded masks (2 voxels), mean signal)",
    ]
    raw = "other (nonlinear registration to the T1w (SyN), without a field map)"
    assert _split("distortion_correction.method", raw) == [raw]
    # the tail of the broken "other (...)" had resolved to fieldmap through "field map"
    (term,) = _terms("distortion_correction.method", raw)
    assert term.resolved == "other" and term.verbatim.endswith("without a field map")


def test_a_number_and_a_unit_ratio_are_not_split() -> None:
    assert _split("scrub.criterion", "FD > 0,5 mm") == ["FD > 0,5 mm"]
    assert _split("scrub.criterion", "FD > 0.2 mm/TR, DVARS > 0.5 %BOLD/s") == [
        "FD > 0.2 mm/TR",
        "DVARS > 0.5 %BOLD/s",
    ]
    assert _resolved("scrub.criterion", "FD > 0.2 mm/TR, DVARS > 0.5 %BOLD/s") == [
        "fd_power",
        "dvars",
    ]
    # controls: a comma after a number, and a slash between two terms, still separate
    assert _split("scrub.criterion", "FD > 0.5, DVARS") == ["FD > 0.5", "DVARS"]
    assert _split("scrub.criterion", "FD/DVARS") == ["FD", "DVARS"]
    assert _split("nuisance_regression.tissue_regressors", "WM/CSF") == ["WM", "CSF"]


def test_an_alias_that_holds_a_separator_is_kept_whole() -> None:
    assert _resolved("distortion_correction.method", "blip-up/blip-down") == [
        "reverse_phase_encoding"
    ]
    assert _resolved("distortion_correction.method", "blip up / blip down, field map") == [
        "reverse_phase_encoding",
        "fieldmap",
    ]
    assert _resolved("ica_denoise.method", "ICA+FIX") == ["fix"]  # glasser2016_nature
    assert _resolved("ica_denoise.method", "sICA + FIX and ICA-AROMA") == ["fix", "aroma"]
    # control: a plus sign between two terms still separates
    assert _resolved("ica_denoise.method", "FIX + AROMA") == ["fix", "aroma"]


def test_a_compound_term_and_a_hyphenated_and_are_kept_whole() -> None:
    assert _split("distortion_correction.tool", "SPM Realign and Unwarp") == [
        "SPM Realign and Unwarp"
    ]
    assert _split("distortion_correction.tool", "Realign-and-Unwarp") == ["Realign-and-Unwarp"]
    assert _split("distortion_correction.tool", "realigned and unwarped, topup") == [
        "realigned and unwarped",
        "topup",
    ]
    # control: "and" between two tools still separates
    assert _resolved("distortion_correction.tool", "topup and FUGUE") == ["topup", "fugue"]


def test_the_stored_split_of_2026_10_28_is_unchanged() -> None:
    assert ex._split_terms("reverse_phase_encoding, other (unwarping and resampling)") == [
        "reverse_phase_encoding",
        "other (unwarping and resampling)",
    ]
    assert ex._split_terms("white matter, CSF and global signal; motion + derivatives") == [
        "white matter",
        "CSF",
        "global signal",
        "motion",
        "derivatives",
    ]


# --- a coordination that shares its head noun -----------------------------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "want", "words"),
    [
        ("compcor.variant", "anatomical and temporal CompCor", ["a", "t"], "anatomical"),
        ("compcor.variant", "temporal and anatomical CompCor", ["t", "a"], "temporal"),
        (
            "nuisance_regression.tissue_regressors",
            "white and gray matter",
            ["white_matter", "gray_matter"],
            "white",
        ),
        (
            "segmentation.tissue_classes",
            "grey/white matter, CSF",
            ["gray_matter", "white_matter", "csf"],
            "grey",
        ),
        (
            "distortion_correction.source",
            "gradient- and susceptibility-induced distortions",
            ["gradient_nonlinearity", "susceptibility_fieldmap"],
            "gradient-",
        ),
    ],
)
def test_the_first_item_borrows_the_shared_head_noun(
    dotted: str, raw: str, want: list[str], words: str
) -> None:
    terms = _terms(dotted, raw)
    assert [t.resolved for t in terms] == want
    assert terms[0].verbatim == words  # the paper's words for the item, not the completed phrase


def test_the_three_conditions_of_borrowing_a_head_noun() -> None:
    # the borrowed words alone name a member: "in-house topup" would make "in-house" topup
    assert _resolved("distortion_correction.tool", "in-house and FSL topup") == [None, "topup"]
    assert _resolved("scrub.criterion", "outlier scans and DVARS") == [None, "dvars"]
    # the next item did not resolve, so its noun belongs to no known term
    assert _resolved("compcor.variant", "temporal and spatial CompCor") == [None, None]
    # the first item rules something out
    assert _resolved(
        "nuisance_regression.tissue_regressors", "excluding white and gray matter"
    ) == [
        None,
        "gray_matter",
    ]
    assert _resolved("segmentation.tissue_classes", "not white and gray matter") == [
        None,
        "gray_matter",
    ]
    # controls: the last two words are borrowed when the last one is not enough, and a long first
    # item is completed like a short one
    assert _resolved("nuisance_regression.tissue_regressors", "white and gray matter signal") == [
        "white_matter",
        "gray_matter",
    ]
    assert _resolved(
        "nuisance_regression.tissue_regressors", "mean signal of the white and gray matter"
    ) == ["white_matter", "gray_matter"]
    assert _resolved(
        "nuisance_regression.tissue_regressors", "signal from the deep nuclei and gray matter"
    ) == [None, "gray_matter"]


# --- "other" with the paper's phrase -----------------------------------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "phrase"),
    [
        (
            "nuisance_regression.method",
            "other - CONN toolbox (SPM-based)",
            "CONN toolbox (SPM-based)",
        ),
        ("nuisance_regression.method", "other \u2013 CONN, run in MATLAB", "CONN, run in MATLAB"),
        ("brain_extraction.method", "other, ROBEX (not BET)", "ROBEX (not BET)"),
        (
            "segmentation.method",
            "other: CAT12 (SPM)",
            "CAT12 (SPM)",
        ),  # control: the 2026-11-03 form
        ("segmentation.method", "other (SynthSeg (FreeSurfer 7))", "SynthSeg (FreeSurfer 7)"),
    ],
)
def test_other_keeps_its_phrase_whatever_introduces_it(dotted: str, raw: str, phrase: str) -> None:
    (term,) = _terms(dotted, raw)
    assert (term.resolved, term.verbatim) == ("other", phrase)


def test_other_on_the_cost_function_is_a_member_since_schema_0_8_0() -> None:
    """The prompt line offered "other" before the vocabulary held it. D2b kept "other (phrase)"
    unresolved there, so that no alias inside the phrase could claim a member; the member (C9)
    replaces that stopgap, and the phrase is kept as the paper's words."""
    assert "other" in typing.get_args(_SPEC["coregistration.cost_function"].literal_type)
    raw = "other (normalized correlation, not mutual information)"
    (term,) = _terms("coregistration.cost_function", raw)
    assert (term.resolved, term.resolution) == ("other", "resolved")
    assert term.verbatim == "normalized correlation, not mutual information"
    assert _one("coregistration.cost_function", "mutual information") == "mutual_information"
    assert _one("coregistration.cost_function", "other") == "other"
    # a field with no member "other" resolves the phrase through its table, as before
    assert "other" not in typing.get_args(_SPEC["slice_time_correction.reference"].literal_type)
    assert _one("slice_time_correction.reference", "other: TR/2") == "specific_time"


def test_other_is_a_word_of_its_own() -> None:
    # a hyphen with no space before it is part of a word, not an introducer
    assert _resolved(
        "distortion_correction.method", "other-direction phase encoding (blip up/blip down)"
    ) == ["reverse_phase_encoding"]
    assert _one("brain_extraction.method", "otherwise BET") == "bet"
    # one outer pair of parentheses: these are not "other (phrase)", and resolve as before D2b
    for raw in ("other (a) (b)", "other (unwarping (FUGUE)"):
        (term,) = _terms("distortion_correction.method", raw)
        assert (term.resolved, term.verbatim) == (None, raw)
    assert _one("nuisance_regression.method", "other \u2014 CONN") == "other"  # an em dash


# --- found by the review of the first build -------------------------------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        # the longer alias first, then the shorter one on its own: two mentions, still ambiguous
        ("coregistration.method", "FLIRT BBR, then FLIRT", None),
        ("slice_time_correction.reference", "middle slice, then slice 17", None),
        # "derivat" covers the spellings papers use and leaves "derived" alone
        (
            "nuisance_regression.motion_expansion",
            "six motion parameters and their derivates",
            "12param",
        ),
        (
            "nuisance_regression.motion_expansion",
            "six parameters and their first derivs",
            "12param",
        ),
        (
            "nuisance_regression.motion_expansion",
            "six motion parameters, their derivates and squares",
            "friston24",
        ),
        # a soft hyphen inside "derivatives": the written text already holds "deriv" as a word
        (
            "nuisance_regression.motion_expansion",
            "six motion parameters, their deriv\u00adatives and squares",
            "friston24",
        ),
        # ... and the text with a line-wrapped word put back together
        (
            "nuisance_regression.motion_expansion",
            "six motion parameters, their deriva-\ntives and squares",
            "friston24",
        ),
        # a toolbox that runs on SPM is not SPM's own tool for the step, however it is named
        ("nuisance_regression.method", "CONN toolbox (SPM12)", None),
        ("nuisance_regression.method", "DPARSF (based on SPM8)", None),
        ("nuisance_regression.method", "DPARSFA (SPM8)", None),
        ("nuisance_regression.method", "DPABI (SPM12)", None),
        ("nuisance_regression.method", "GIFT (SPM12)", None),
        ("nuisance_regression.method", "REST toolbox in SPM8", None),
        ("nuisance_regression.method", "REST toolkit (SPM8)", None),
        ("nuisance_regression.method", "RESTplus V1.2 (SPM12)", None),
        ("nuisance_regression.method", "Resting-State fMRI Data Analysis Toolkit (SPM8)", None),
        ("nuisance_regression.method", "SPM12", "spm"),  # control
        ("nuisance_regression.method", "the rest of the SPM12 pipeline", None),  # not alone
        ("segmentation.method", "CAT12 (SPM12)", None),
        ("segmentation.method", "CAT 12 (SPM12)", None),
        ("segmentation.method", "Computational Anatomy Toolbox (SPM12)", None),
        ("segmentation.method", "VBM8 toolbox (SPM8)", None),
        # no alias: the table holds "SPM segment" and "SPM12 segmentation", not this wording
        ("segmentation.method", "SPM12 Segment", None),
        ("segmentation.method", "SPM12 segmentation", "spm_segment"),  # control: the alias
        # the subject's own surface, in the other words the block names
        ("spatial_smoothing.space", "fsnative cortical surface", None),
        ("spatial_smoothing.space", "each participant's cortical surface", None),
        ("spatial_smoothing.space", "their own cortical surface", None),
        ("spatial_smoothing.space", "individual cortical surface", None),
        ("spatial_smoothing.space", "native cortical-surface", None),
        # only the repaired reading holds the block's words: a Unicode hyphen at a line break
        ("spatial_smoothing.space", "native cortical\u2010\nsurface", None),
        # "deriv" as a word of its own, with and without its "s"
        (
            "nuisance_regression.motion_expansion",
            "six motion parameters and their deriv",
            "12param",
        ),
    ],
)
def test_wordings_the_review_added(dotted: str, raw: str, want: str | None) -> None:
    assert _one(dotted, raw) == want


def test_split_cases_the_review_added() -> None:
    # either hyphen alone keeps "and" inside a name
    assert _split("distortion_correction.tool", "Realign-and Unwarp") == ["Realign-and Unwarp"]
    assert _split("distortion_correction.tool", "Realign and-Unwarp") == ["Realign and-Unwarp"]
    # a comma with a digit on one side only still separates
    assert _split("nuisance_regression.tissue_regressors", "WM,6 motion parameters") == [
        "WM",
        "6 motion parameters",
    ]
    assert _split("scrub.criterion", "FD > 0.5 mm, DVARS > 1/2") == [
        "FD > 0.5 mm",
        "DVARS > 1/2",
    ]  # a slash between digits is a fraction
    # an alias that holds a separator is kept whole across a line break
    assert _split("distortion_correction.method", "blip up/blip\ndown") == ["blip up/blip\ndown"]
    # the compound term on the method field too
    assert _split("distortion_correction.method", "realigned and unwarped, field map") == [
        "realigned and unwarped",
        "field map",
    ]
    # the placeholder's own character in the value cannot hang the restore loop
    assert ex._split_terms("FD (\x000\x00) and DVARS") == ["FD (0)", "DVARS"]


def test_the_extractor_splits_and_resolves_a_list_this_way() -> None:
    """Through extract(): the one call site of _keep_whole and _resolve_term_list."""
    from conftest import stub_client
    from extractor_mvp.coverage_extractor import SpatialExtraction, TemporalVolumeExtraction
    from extractor_mvp.extraction_result import FieldExtractionResult
    from extractor_mvp.extractor import PreprocessingExtraction, extract
    from extractor_mvp.parsed_paper import ParsedPaper

    s_dist = "Distortion was corrected with Realign and Unwarp, then topup."
    s_reg = "White and gray matter signals were regressed out."
    missing = FieldExtractionResult(status="missing")

    def got(value: str, quote: str) -> FieldExtractionResult:
        return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)

    shared = PreprocessingExtraction(
        target_space=missing,
        resolution_mm=missing,
        surface_registration=missing,
        target_surface=missing,
        intensity_convention=missing,
        intensity_value=missing,
    )
    prep, _, _ = extract(
        ParsedPaper(text=f"{s_dist} {s_reg}", source="t", parser="manual"),
        "m",
        client=stub_client(
            shared,
            temporal=TemporalVolumeExtraction(
                nuisance_performed=got("yes", s_reg),
                nuisance_tissue_regressors=got("White and gray matter", s_reg),
            ),
            spatial=SpatialExtraction(
                distortion_performed=got("yes", s_dist),
                distortion_tool=got("Realign and Unwarp, topup", s_dist),
            ),
        ),
    )
    tools = next(s for s in prep.steps if s.kind == "distortion_correction").tool.extraction.value
    assert [(t.verbatim, t.resolved) for t in tools] == [
        ("Realign and Unwarp", None),
        ("topup", "topup"),
    ]
    tissue = next(s for s in prep.steps if s.kind == "nuisance_regression").tissue_regressors
    assert [(t.verbatim, t.resolved) for t in tissue.extraction.value] == [
        ("White", "white_matter"),
        ("gray matter", "gray_matter"),
    ]


def test_the_shared_vocabulary_fields_are_the_extractor_s() -> None:
    assert {dotted: field_id for dotted, (field_id, _lit) in _SHARED.items()} == (
        SHARED_VOCABULARY_FIELDS
    )
    assert vocabulary_table("spatial_smoothing.fwhm_mm") is None
    assert vocabulary_table("motion_correction.method") is None
    assert vocabulary_table("temporal_standardization.method") is None
    assert all(vocabulary_table(d) is not None for d in [*_SPEC, *_SHARED])


@pytest.mark.parametrize(
    ("dotted", "words", "want"),
    [
        ("brain_extraction.method", "optiBET", True),  # no alias occurs
        # a member's alias occurs and a rule blocks it: no claim is made, whether the field holds
        # the member the words mean (native_surface) or not
        ("distortion_correction.method", "fieldmap-free", False),
        ("distortion_correction.source", "fieldmap-free", False),
        ("spatial_smoothing.space", "individual cortical surface", False),
        # a member's own token, in another case or with a space for the underscore
        ("nuisance_regression.motion_expansion", "Friston24", False),
        ("nuisance_regression.motion_expansion", "the Friston24 model", False),
        ("spatial_smoothing.space", "Native Volume", False),
        ("spatial_smoothing.space", "in the native volume", False),
        ("surface_projection.target_surface", "Native", False),
        # the catch-all and a one-letter token name their member only as the whole wording
        ("brain_extraction.method", "Other", False),
        ("brain_extraction.method", "ROBEX and other tools", True),
        ("spatial_normalization.target_space", "Other.", False),  # a shared field holds it too
        ("compcor.variant", "A", False),
        ("compcor.variant", "a principal components approach", True),
        # "other" where the field holds no such member is a word like any other
        ("slice_time_correction.reference", "other", True),
        ("coregistration.cost_function", "Other", False),  # a member since schema 0.8.0
        # the punctuation a value may come wrapped in
        ("brain_extraction.method", "(Other)", False),
        ("brain_extraction.method", "[other]", False),
        ("brain_extraction.method", "Other;", False),
        ("brain_extraction.method", "Other:", False),
        ("brain_extraction.method", "Other,", False),
        ("brain_extraction.method", "'Other'", False),
        ("brain_extraction.method", '"Other"', False),
        ("compcor.variant", "[A]", False),
        # the name of a family whose members the vocabulary holds
        ("surface_projection.target_surface", "fs_LR", False),
        ("surface_projection.target_surface", "the fsLR surface", False),
        ("surface_projection.target_surface", "32k fsLR mesh", False),
        ("surface_projection.surface_registration", "MSM alignment", False),
        ("compcor.variant", "CompCor", False),
        ("compcor.variant", "a-CompCor", False),
        ("spatial_normalization.target_space", "Montreal Neurological Institute template", False),
        ("spatial_normalization.target_space", "ICBM152", False),
        (
            "spatial_normalization.target_space",
            "ICBM 152 Nonlinear Asymmetrical template version 2009c",
            False,
        ),
        # controls: a family name of one field is no name on another, nor inside a longer word
        ("surface_projection.surface_registration", "CompCor", True),
        ("compcor.variant", "MSM", True),
        # D2c (2026-11-25, C13): "MSM" is a family term of the table now, read as a plain
        # substring as "MNI" is, so it is found inside a longer word too
        ("surface_projection.surface_registration", "MSMx alignment", False),
        ("surface_projection.surface_registration", "MSx alignment", True),
        # an SPM release inside a longer wording names the SPM member
        ("nuisance_regression.method", "CONN toolbox (SPM12)", False),
        ("nuisance_regression.method", "CONN toolbox", True),
        ("coregistration.method", "FLIRT and bbregister", False),  # two members: ambiguous
        ("spatial_normalization.target_space", "MNI", False),  # a family term
        ("spatial_normalization.target_space", "atlas space", True),
        ("slice_time_correction.reference", "middle slice", False),  # a member is named
        ("nuisance_regression.motion_expansion", "six, derivatives, squares", False),  # by rule
        ("intensity_normalization.convention", "grand mean scaling", False),  # whatever the value
        ("motion_correction.method", "realigned", False),  # no table
        ("temporal_standardization.method", "z-scored", False),  # no table
    ],
)
def test_names_no_member(dotted: str, words: str, want: bool) -> None:
    assert names_no_member(dotted, words) is want


def test_every_member_is_a_key_of_its_table_except_other_on_the_shared_fields() -> None:
    """names_no_member reads the members off the table; this is what lets it."""
    for dotted, s in _SPEC.items():
        if s.synonyms:
            assert set(typing.get_args(s.literal_type)) == set(s.synonyms), dotted
    for dotted, (field_id, literal_type) in _SHARED.items():
        syns, _under = SYNONYMS_BY_FIELD[field_id]
        assert set(typing.get_args(literal_type)) == {*syns, "other"}, dotted


# --- found by the review of the second build ------------------------------------------------------


@pytest.mark.parametrize("ch", list(_HYPHENS))
def test_every_hyphen_the_repair_lists_is_read_as_a_hyphen(ch: str) -> None:
    assert repair_text(f"fieldmap{ch}less") == "fieldmap-less"
    assert _one("distortion_correction.source", f"fieldmap{ch}less") == "fieldmap_less"
    assert _resolved("distortion_correction.method", f"fieldmap{ch}less") == ["fieldmap_less"]
    # the block reads the repaired text: no alias holds "-free", and fieldmap may not take it
    assert _resolved("distortion_correction.method", f"fieldmap{ch}free") == [None]
    assert rule_hits(TERM_RULES["brain_extraction.method"].block["bet"][0], f"HD{ch}BET")


@pytest.mark.parametrize("ch", list(_INVISIBLE))
def test_every_invisible_character_the_repair_lists_is_dropped(ch: str) -> None:
    assert repair_text(f"field{ch}map") == "fieldmap"
    assert _resolved("distortion_correction.method", f"field{ch}map") == ["fieldmap"]


def test_the_repair_lists_are_the_ones_these_tests_walk() -> None:
    assert _HYPHENS == "\u2010\u2011\u2012\ufe63\uff0d"
    assert _INVISIBLE == "\u00ad\u200b\u200c\u200d\u2060\ufeff"


@pytest.mark.parametrize(
    "word", ["no", "not", "non", "without", "excluding", "except", "neither", "nor"]
)
def test_an_item_that_rules_something_out_borrows_no_head_noun(word: str) -> None:
    assert _resolved("nuisance_regression.tissue_regressors", f"{word} white and gray matter") == [
        None,
        "gray_matter",
    ]


@pytest.mark.parametrize(
    "ratio",
    [
        "0.5 mm/frame",
        "0.5 mm/frames",
        "3%/s",
        "0.5 % BOLD/s",
        "0.5 voxels/TR",
        "1 voxel/TR",
        "0.3 mm/volume",
        "0.3 mm/volumes",
        "0.3 mm/vol",
        "0.3 mm/vols",
        "0.2 cm/s",
        "0.2 mm/sec",
        "0.2 mm/second",
        "0.2 mm/seconds",
        "200 mm/ms",
        "2 mm/min",
        "1 degree/TR",
        "2 degrees/TR",
        "1 deg/scan",
        "1 deg/scans",
        "1\u00b0/TR",
        "0.2 mm/time point",
        "0.2 mm/timepoints",
        "0.2 mm / TR",
    ],
)
def test_a_unit_and_what_it_is_counted_per_are_one_token(ratio: str) -> None:
    raw = f"FD > {ratio}"
    assert _split("scrub.criterion", f"{raw}, DVARS") == [raw, "DVARS"]


def test_a_slash_that_is_not_a_unit_ratio_still_separates() -> None:
    assert _split("scrub.criterion", "FD > 0.5 mm/DVARS") == ["FD > 0.5 mm", "DVARS"]
    # "mm" inside a word is not the unit
    assert _split("scrub.criterion", "comm/TR") == ["comm", "TR"]


@pytest.mark.parametrize(
    ("dotted", "raw", "phrase"),
    [
        (
            "distortion_correction.method",
            "other (nonlinear\nregistration, no field map)",
            "nonlinear\nregistration, no field map",
        ),
        (
            "nuisance_regression.method",
            "other: CONN toolbox,\nrun in MATLAB",
            "CONN toolbox,\nrun in MATLAB",
        ),
    ],
)
def test_an_other_phrase_may_run_over_a_line_break(dotted: str, raw: str, phrase: str) -> None:
    (term,) = _terms(dotted, raw)
    assert (term.resolved, term.verbatim) == ("other", phrase)


def test_a_rule_reads_the_words_as_written_as_repaired_and_with_wraps_rejoined() -> None:
    block = TERM_RULES["spatial_smoothing.space"].block["template_surface"][0]
    assert rule_hits(block, "native cortical surface")  # as written
    assert rule_hits(block, "native cortical\u2010surface")  # only as repaired
    assert not rule_hits(block, "fsaverage cortical surface")
    derivative = TERM_RULES["nuisance_regression.motion_expansion"].block["6param"][0]
    assert rule_hits(derivative, "their deriva-\ntives")  # only with the wrapped word rejoined
    assert not rule_hits(derivative, "their deriva- tives")  # a space is not a line break


def test_a_shorter_member_named_beside_its_longer_form_is_dropped_from_the_reading() -> None:
    """The token-prefix collapse is part of how a text is read (synonym_resolver.members_named),
    so the quote reading of the audit applies it as the resolver does."""
    from extractor_mvp.synonym_resolver import members_named

    syns, under = SYNONYMS_BY_FIELD["target_surface"]
    assert set(members_named("sampled to fsaverage, then to fsaverage5", syns)) == {"fsaverage5"}
    assert resolve_to_literal("fsaverage, then fsaverage5", syns, under).resolved == "fsaverage5"
    assert set(members_named("fsaverage", syns)) == {"fsaverage"}  # control


def test_a_family_name_suppresses_the_note_and_resolves_nothing() -> None:
    from extractor_mvp.coverage_fields import FAMILY_NAMES

    assert set(FAMILY_NAMES) <= {*_SPEC, *_SHARED}
    # D2c (2026-11-25, C13): the five families are underspecified terms of their tables as
    # well, so their status is "underspecified"
    for dotted, names in FAMILY_NAMES.items():
        for name in names:
            assert names_no_member(dotted, name) is False, (dotted, name)
            if dotted in _SPEC:
                (term,) = _terms(dotted, name)
                assert (term.resolved, term.resolution) == (None, "underspecified"), (dotted, name)
            else:
                syns, under = SYNONYMS_BY_FIELD[_SHARED[dotted][0]]
                got = resolve_to_literal(name, syns, under)
                assert (got.resolved, got.status) == (None, "underspecified"), (dotted, name)
