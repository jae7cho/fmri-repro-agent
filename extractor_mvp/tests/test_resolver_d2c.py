"""D2c of DESIGN_prompt_schema_2026-11 (2026-11-25): the table and code items of the author's
rulings C10, C11, C13 and C14. No prompt and no schema changes with them.

Each item is pinned with the wordings it must change and the ones it must leave alone. An
unresolved term keeps the paper's words, which is the safe direction; the controls show that no
member is lost where the wording does name it. Every wording here is constructed, or quoted in the
design note from a paper that is not held out.
"""

from __future__ import annotations

import sys
import typing
from pathlib import Path
from typing import Any

import pytest
from fmri_repro.spec.preprocessing import SpecifiedTerm

from conftest import stub_client
from extractor_mvp import extractor as ex
from extractor_mvp.coverage_extractor import TemporalVolumeExtraction, detrend_highest_order
from extractor_mvp.coverage_fields import (
    COVERAGE_SPECS,
    COVERAGE_SUPPORT_TABLES,
    FAMILY_NAMES,
    OR_JOINS_ITEMS,
    OR_UNITS,
    OR_WEAK_ALIASES,
    PERFORMED_PHRASES,
    SHARED_VOCABULARY_FIELDS,
    TERM_RULES,
    bare_criterion,
    names_no_member,
    resolve_shared,
)
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.quote_support import SUPPORT_TABLES, _term_supported, literal_value_supported
from extractor_mvp.synonym_resolver import (
    FAMILY_NAME_ENTRIES,
    SYNONYMS_BY_FIELD,
    resolve_to_literal,
)
from extractor_mvp.verifier import FieldVerdict, VerifierExtraction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import term_audit as ta

_SPEC = {s.dotted: s for s in COVERAGE_SPECS if s.value_kind in ("term", "term_list")}
_FIELD = {f.dotted: f for f in ta.vocabulary().values()}

INTENSITY = "intensity_correction.method"
MOTION = "nuisance_regression.motion_expansion"
CRITERION = "scrub.criterion"
COMPCOR = "compcor.variant"
ORDER = "slice_time_correction.relative_to_motion_correction"
TRANSFORM = "coregistration.transform"
SEGMENTATION = "segmentation.method"
BRAIN = "brain_extraction.method"
FILTER = "temporal_filtering.filter_type"
SPACE = "spatial_normalization.target_space"
SURFACE = "surface_projection.target_surface"
REGISTRATION = "surface_projection.surface_registration"
CONVENTION = "intensity_normalization.convention"
DETREND = "nuisance_regression.detrend"


def _terms(dotted: str, raw: str) -> list[Any]:
    """A coverage field's value as ``extractor._process_field`` resolves it."""
    s = _SPEC[dotted]
    syn = (s.synonyms, s.underspecified) if s.synonyms else None
    if s.value_kind == "term_list":
        items = ex._field_items(dotted, raw, s.literal_type, syn)
        return ex._resolve_term_list(items, s.literal_type, syn, dotted)
    return [ex._resolve_term(raw, s.literal_type, syn, dotted)]


def _members(dotted: str, raw: str) -> list[str | None]:
    return [t.resolved for t in _terms(dotted, raw)]


def _shared(dotted: str, raw: str, value: float | None = None) -> tuple[str | None, str]:
    """A shared field's term as the extractor resolves it: (member, resolver status)."""
    got = ex._resolve_shared_term(SHARED_VOCABULARY_FIELDS[dotted], dotted, raw, value)
    return got.resolved, got.status


# --- C10: "N3" is no alias of n4 ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("N3", None),
        ("N3 bias field correction", None),
        ("nonparametric nonuniform intensity normalization (N3)", None),
        # controls: N4 keeps its aliases
        ("N4", "n4"),
        ("N4BiasFieldCorrection", "n4"),
        ("N4 bias field correction (ANTs)", "n4"),
        ("FAST", "fast_bias"),
        # N3 beside N4 named n4 through both aliases, and still names it through one
        ("N3 and N4", "n4"),
        ("N3 followed by N4", "n4"),
    ],
)
def test_n3_is_not_n4(raw: str, want: str | None) -> None:
    assert _members(INTENSITY, raw) == [want]


@pytest.mark.parametrize("raw", ["N3 then FAST", "N3 and FAST bias correction", "FAST after N3"])
def test_n3_beside_fast_stays_unresolved(raw: str) -> None:
    """Before C10 such a term named two methods (n4 through "N3", fast_bias) and stayed
    unresolved. With the alias gone it would resolve to fast_bias alone; a block keeps it as it
    was. The control shows the block reads "N3" and nothing else."""
    assert _members(INTENSITY, raw) == [None]
    assert _members(INTENSITY, raw.replace("N3", "N4")) == [None]  # two members: ambiguous
    assert _members(INTENSITY, raw.replace("N3", "ANTs")) == ["fast_bias"]
    assert set(TERM_RULES[INTENSITY].block) == {"fast_bias"}


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # where the alias read "N3": an underscore is a word edge to the table, a plural counts
        ("N3_FAST", None),
        ("FAST_N3", None),
        ("N3s then FAST", None),
        ("(N3), then FAST", None),
        ("n3 then fast", None),
        # where it did not: inside a longer token, or as the head of a longer number
        ("the N30 component, then FAST", "fast_bias"),
        ("AN3 then FAST", "fast_bias"),
        ("5N3 then FAST", "fast_bias"),
        ("N3D then FAST", "fast_bias"),
        ("N3.1 then FAST", "fast_bias"),
        ("N3,4 then FAST", "fast_bias"),
    ],
)
def test_the_block_beside_fast_reads_n3_where_the_alias_did(raw: str, want: str | None) -> None:
    assert _members(INTENSITY, raw) == [want]


def test_n3_is_outside_the_vocabulary_and_still_a_word_of_the_step() -> None:
    assert names_no_member(INTENSITY, "N3") is True  # the report says so
    assert names_no_member(INTENSITY, "N4") is False
    # the hash-pinned phrases that support "performed" are another table, and keep it
    assert "N3" in PERFORMED_PHRASES["intensity_correction"]
    # a value n4 is no longer vouched for by a quote that says N3
    n4 = SpecifiedTerm(verbatim="n4", resolved="n4", resolution="resolved")
    assert _term_supported(INTENSITY, n4, "N3 bias correction was applied") is False
    assert _term_supported(INTENSITY, n4, "N4 bias correction was applied") is True


# --- C13: two aliases from the papers that print them --------------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("24-regressor model of motion", "friston24"),
        ("a 24-regressor model of motion", "friston24"),
        ("24 regressor model of motion", "friston24"),  # a hyphen and a space are one separator
        # the alias is the paper's wording and no shorter: these stay in the paper's words
        ("24-regressor model", None),
        ("24 regressor motion model", None),
        ("24-regressor models of head movement", None),
        # control: the plural alias, as before
        ("24 regressors", "friston24"),
    ],
)
def test_the_24_regressor_model_of_motion(raw: str, want: str | None) -> None:
    assert _members(MOTION, raw) == [want]


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        (
            "ICBM 152 Nonlinear Asymmetrical template version 2009c",
            ("MNI152NLin2009cAsym", "resolved"),
        ),
        (
            "the ICBM 152 Nonlinear Asymmetrical template version 2009c",
            ("MNI152NLin2009cAsym", "resolved"),
        ),
        (
            "ICBM-152 nonlinear asymmetrical template version 2009c",
            ("MNI152NLin2009cAsym", "resolved"),
        ),
        # a near spelling does not reach the alias. It holds the family name, and is a family term
        ("ICBM 152 Nonlinear Asymmetrical template, version 2009c", (None, "underspecified")),
        ("ICBM 152 Non-linear Asymmetrical template version 2009c", (None, "underspecified")),
        # two templates named: no member
        (
            "ICBM 152 Nonlinear Asymmetrical template version 2009c and MNI152NLin6Asym",
            (None, "ambiguous"),
        ),
    ],
)
def test_the_icbm_152_name_of_the_2009c_template(raw: str, want: tuple[str | None, str]) -> None:
    assert _shared(SPACE, raw) == want


def test_every_alias_still_resolves_to_its_own_member() -> None:
    """The table self-check of D2b. 451 aliases before D2c; "N3" left and two came."""
    checked, failures = ta.self_check()
    assert (checked, failures) == (452, [])


# --- C13: family names as underspecified terms of their tables -----------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw"),
    [
        (SURFACE, "fs_LR"),
        (SURFACE, "the fsLR surface"),
        (SURFACE, "fs-LR"),
        (SURFACE, "fs LR mesh"),
        (REGISTRATION, "MSM"),
        (REGISTRATION, "MSM alignment"),
        (REGISTRATION, "MSM folding"),
        (SPACE, "ICBM152"),
        (SPACE, "ICBM 152 template"),
        (SPACE, "Montreal Neurological Institute template"),
    ],
)
def test_a_family_name_is_an_underspecified_term_of_a_shared_field(dotted: str, raw: str) -> None:
    assert _shared(dotted, raw) == (None, "underspecified")
    assert names_no_member(dotted, raw) is False


def test_compcor_with_no_kind_is_an_underspecified_term() -> None:
    (term,) = _terms(COMPCOR, "CompCor")
    assert (term.resolved, term.resolution) == (None, "underspecified")
    kinds = _terms(COMPCOR, "aCompCor and CompCor")
    assert [(t.resolved, t.resolution) for t in kinds] == [
        ("a", "resolved"),
        (None, "underspecified"),
    ]
    # controls: the members, and the coordination that shares its head noun, as before
    assert _members(COMPCOR, "aCompCor") == ["a"]
    assert _members(COMPCOR, "anatomical and temporal CompCor") == ["a", "t"]
    assert _members(COMPCOR, "principal components") == [None]
    assert _terms(COMPCOR, "principal components")[0].resolution == "unrecognized"


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        (SURFACE, "fs_LR 32k", "fsLR_32k"),
        (SURFACE, "fs LR 32k", "fsLR_32k"),
        (SURFACE, "164k_fs_LR", "fsLR_164k"),
        (SPACE, "MNI152NLin6Asym", "MNI152NLin6Asym"),
        (SPACE, "MNI152 2009c", "MNI152NLin2009cAsym"),
    ],
)
def test_a_member_named_with_its_family_still_resolves(dotted: str, raw: str, want: str) -> None:
    assert _shared(dotted, raw) == (want, "resolved")


def test_every_family_name_is_a_family_term_of_its_field() -> None:
    """The report's table of family names and the family lists of the resolver cannot drift: each
    name of the first holds an entry of the second ("ICBM152" holds "ICBM"), and each entry D2c
    added is listed as such."""
    for dotted, names in FAMILY_NAMES.items():
        family = _FIELD[dotted].underspecified or []
        for name in names:
            assert any(entry.lower() in name.lower() for entry in family), (dotted, name)
    lists = [f.underspecified or [] for f in _FIELD.values()]
    for entry in FAMILY_NAME_ENTRIES:
        assert sum(entry in family for family in lists) == 1, entry
    # the entries the ruling of 2026-10-26 covers are the ones that were there before D2c
    older = {e for family in lists for e in family} - FAMILY_NAME_ENTRIES
    assert older == {
        "MNI",
        "MNI152",
        "MNI standard space",
        "MNI standard",
        "standard MNI",
        "standard space",
        "standard volumetric space",
        "MNI template",
        "MNI atlas",
        "FreeSurfer",
        "FreeSurfer-based",
        "via FreeSurfer",
        "sphere registration",
        "spherical registration",
    }


def test_the_quote_check_reads_the_family_list_the_resolver_reads() -> None:
    for dotted, field_id in SHARED_VOCABULARY_FIELDS.items():
        assert SUPPORT_TABLES[dotted][1] is SYNONYMS_BY_FIELD[field_id][1], dotted
    assert COVERAGE_SUPPORT_TABLES[COMPCOR][1] == ["CompCor"]


@pytest.mark.parametrize(
    ("dotted", "verbatim", "quote", "want"),
    [
        # a family name of D2c stands in its quote in its own words, as it had to before D2c
        (SURFACE, "fs_LR", "sampled to the fs_LR surface", True),
        (SURFACE, "fs_LR", "sampled to fsaverage", False),
        (SURFACE, "fs_LR32k", "sampled to fs_LR32k", True),  # glued: read by its own words
        (SURFACE, "fs-LR32k", "sampled to fs-LR32k", True),
        (SURFACE, "fs LR32k", "sampled to fs LR32k", True),
        (SURFACE, "fsLR32k", "sampled to the fsLR surface", False),  # says more than its quote
        (SPACE, "ICBM152", "normalized to the ICBM152 template", True),
        (SPACE, "ICBM152", "normalized to MNI space", False),
        (SPACE, "ICBM452", "normalized to standard space", False),
        (SPACE, "Montreal Neurological Institute template", "normalized to MNI space", False),
        (
            SPACE,
            "Montreal Neurological Institute template",
            "the Montreal Neurological Institute template",
            True,
        ),
        (REGISTRATION, "MSM", "surfaces were aligned with MSM", True),
        (REGISTRATION, "MSM", "registered with FreeSurfer", False),  # another family's term
        (REGISTRATION, "MSM", "surfaces were aligned with MSMAll", False),  # a longer name
        (REGISTRATION, "MSM alignment", "spherical registration", False),
        # a family term of the 2026-10-26 lists is read as it was: any term of its list
        (SPACE, "MNI", "normalized to standard space", True),
        (SPACE, "MNI152", "normalized to MNI space", True),
        (SPACE, "MNI305", "normalized to the MNI305 template", True),
        (SPACE, "standard space", "normalized to Talairach coordinates", False),
        (REGISTRATION, "FreeSurfer", "registered with FreeSurfer", True),
        (REGISTRATION, "spherical registration", "registered with FreeSurfer", True),
        (REGISTRATION, "FreeSurfer", "aligned with MSMAll", False),  # "MSM" vouches for no other
        # a soft hyphen inside the older term: the value is read as the resolver reads it
        (REGISTRATION, "Free\u00adSurfer", "aligned by spherical registration", True),
        # a term that holds both is a term of the older list
        (SPACE, "Montreal Neurological Institute (MNI) space", "in MNI space", True),
        (REGISTRATION, "MSM after FreeSurfer", "surfaces from FreeSurfer", True),
        # also where the older term stands after an "@": the resolver reads the whole value
        (REGISTRATION, "MSM @ FreeSurfer", "registered with FreeSurfer", True),
        (REGISTRATION, "MSM @ FreeSurfer", "aligned with MSM", False),
        (SPACE, "ICBM@MNI152", "normalized to MNI space", True),
        (SPACE, "ICBM@MNI152", "the ICBM template", False),
        # a value of a D2c name alone is checked by the phrase before an "@", as it was
        (REGISTRATION, "MSM@v3", "aligned with MSM", True),
        (REGISTRATION, "MSM@v3", "registered with FreeSurfer", False),
        # the older rule is the only check of a value that holds an older term: its own words
        # in the quote do not pass it where no family term starts a word there, as before D2c
        (SPACE, "xMNI", "registered to xMNI space", False),
    ],
)
def test_a_family_value_against_its_quote(
    dotted: str, verbatim: str, quote: str, want: bool
) -> None:
    assert _shared(dotted, verbatim)[1] == "underspecified"
    assert literal_value_supported(dotted, verbatim, None, "underspecified", quote) is want


@pytest.mark.parametrize(
    ("verbatim", "quote", "want"),
    [
        ("CompCor", "CompCor regressors were removed", True),
        ("CompCor", "motion regressors were removed", False),
        ("aCompCor50", "aCompCor50 was used", True),
        ("aCompCor50", "CompCor was used", False),
    ],
)
def test_a_compcor_family_value_against_its_quote(verbatim: str, quote: str, want: bool) -> None:
    (term,) = _terms(COMPCOR, verbatim)
    assert (term.resolved, term.resolution) == (None, "underspecified")
    assert _term_supported(COMPCOR, term, quote) is want


@pytest.mark.parametrize(
    ("dotted", "raw", "noted"),
    [
        # a name glued to more text holds a family term now, and the report's note that the term
        # is outside the vocabulary is no longer made of it (a family list is a plain substring)
        (SURFACE, "fs_LR32k", False),
        (REGISTRATION, "MSMv3", False),
        (SPACE, "ICBM2009c", False),
        (COMPCOR, "tCompCorCSF", False),
        (SURFACE, "fs_LR", False),
        # controls: a term that holds no family term keeps the note
        (SURFACE, "Conte69", True),
        (COMPCOR, "FooCor", True),
    ],
)
def test_the_note_of_a_term_outside_the_vocabulary_and_the_family_names(
    dotted: str, raw: str, noted: bool
) -> None:
    assert names_no_member(dotted, raw) is noted


# --- C13: a noun after the density of a mesh ---------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("fsaverage 6 surface", "fsaverage6"),
        ("fsaverage 5 space", "fsaverage5"),
        ("the fsaverage 6 template", "fsaverage6"),
        ("fsaverage 5 mesh", "fsaverage5"),
        ("fsaverage-6 surface.", "fsaverage6"),
        ("fsaverage_6_surface", "fsaverage6"),
        ("(fsaverage 5 surface)", "fsaverage5"),
        ('"fsaverage 6 surface"', "fsaverage6"),
        ("the 'fsaverage 5 template'", "fsaverage5"),
        ("[the fsaverage 6 mesh];", "fsaverage6"),
        ("fsaverage 6 surface )", "fsaverage6"),  # a space before the closing mark
        ("The  fsaverage 6  surface !?", "fsaverage6"),
        # each mark that may stand around the wording, once and more than once
        ("fsaverage 6 surface,", "fsaverage6"),
        ("fsaverage 6 surface:", "fsaverage6"),
        ("( fsaverage 6 surface )", "fsaverage6"),
        ("'fsaverage 6 surface'", "fsaverage6"),
        ("((fsaverage 6 surface))", "fsaverage6"),
        ("the (fsaverage 6 surface)", "fsaverage6"),
        ("the [fsaverage 6 surface]", "fsaverage6"),
        ('the "fsaverage 6 surface"', "fsaverage6"),
        ("the ((fsaverage 6 surface))", "fsaverage6"),
        ("the ( fsaverage 6 surface )", "fsaverage6"),
        # the separators are folded: at either end they count as nothing
        ("fsaverage 6 surface -", "fsaverage6"),
        ("- fsaverage 5 template", "fsaverage5"),
        ("_fsaverage_6_mesh_", "fsaverage6"),
        # the plural "s" every alias may carry
        ("fsaverage 6s surface", "fsaverage6"),
        # the term is the mesh and its noun and nothing else: what stands after the noun, or
        # before the mesh, may say that the mesh is another one (the reviews of D2c)
        ("fsaverage 6 surface, smoothed", None),
        ("fsaverage 6 template, symm.", None),
        ("fsaverage 5 mesh; symm", None),
        ("fsaverage 6 surface, xhemi", None),
        ("fsaverage 6 space: bisymmetric", None),
        ("symm. fsaverage 6 surface", None),
        ("projected to the (fsaverage 5 surface)", None),
        ("the 'fsaverage 5 template' was used", None),
        ("a fsaverage 6 surface", None),  # no article but "the"
        ("the the fsaverage 6 surface", None),  # and "the" once
        ("the(fsaverage 6 surface)", None),  # with a space after it
        ("thefsaverage 6 surface", None),
        ("fsaverage 6 surface/", None),  # a slash closes nothing
        ("fsaverage 6 surface - based", None),
        ("fsaverage 6 surface (", None),  # an opening mark closes nothing
        ("fsaverage 6 surface's vertices", None),
        ('fsaverage 6 surface"1', None),
        # a word after the noun may be what the number counts
        ("fsaverage 6 surface vertices", None),
        ("fsaverage 5 template subjects", None),
        ("fsaverage 6 mesh points per mm", None),
        ("fsaverage 6 space-time", None),
        ("fsaverage 6 surface-based smoothing", None),
        ("fsaverage 5 mesh (10,242 vertices)", None),
        # a plural after a bare number is the counted reading
        ("fsaverage 6 surfaces", None),
        ("fsaverage 5 meshes", None),
        ("fsaverage 6 templates", None),
        # only directly after the number, and only the four nouns
        ("fsaverage 6 cortical surface", None),
        ("fsaverage 6 sphere", None),
        ("fsaverage 6 mm", None),
    ],
)
def test_a_noun_may_follow_the_density_of_a_mesh(raw: str, want: str | None) -> None:
    syns, under = SYNONYMS_BY_FIELD["target_surface"]
    assert resolve_to_literal(raw, syns, under).resolved == want


def test_the_noun_rule_is_for_the_two_meshes_only() -> None:
    """The intensity convention holds the one other alias that ends in a digit and holds another
    member's alias. Its number must still end the phrase."""
    syns, under = SYNONYMS_BY_FIELD["convention"]
    assert (
        resolve_to_literal("spm grand mean 100", syns, under, 10000).resolved
        == "spm_grand_mean_100"
    )
    assert resolve_to_literal("spm grand mean 100 space", syns, under, 10000).resolved is None
    assert resolve_to_literal("spm grand mean 100 template", syns, under, 10000).resolved is None


# --- C13: the wrong-member matches of the D1 sweep, coverage fields ------------------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        # the order of the OTHER step is stated: slice timing came before, the alias said after
        (ORDER, "realignment was performed after slice timing correction", None),
        (ORDER, "motion correction was applied before slice-timing correction", None),
        (ORDER, "realigned after the slice timing step", None),
        (ORDER, "after STC", None),
        (ORDER, "realignment after slice-time correction", None),
        (ORDER, "MCFLIRT after slicetimer", None),
        (ORDER, "realigned after slice-timing correction", None),
        (ORDER, "after slice_timing", None),
        (ORDER, "after_the_slice_timing", None),
        (ORDER, "after STCx", "after"),
        (ORDER, "motion_correction_after_STC", None),
        (ORDER, "realignment after slice acquisition time correction", None),
        (ORDER, "motion correction before STC", None),
        (ORDER, "motion correction before STCs", None),
        (ORDER, "realignment before the slice timing step", None),
        (ORDER, "realignment after a slice timing step", None),
        (ORDER, "after its slice-timing correction", None),
        (ORDER, "thereafter slice timing was run", None),
        (ORDER, "realignment_before_slice_timing", None),
        (ORDER, "realignment before-slice-timing", None),
        (ORDER, "motion_correction_before_STC", None),
        (ORDER, "after their slice timing", None),
        (ORDER, "before our slice timing", None),
        (ORDER, "realignment after an STC", None),
        (ORDER, "realigned after_the_slice timing", None),
        (ORDER, "realigned before_the_slice timing", None),
        # "after" inside a longer word is not the block's word
        (ORDER, "after realignment; thereafter slice timing was applied", "after"),
        (ORDER, "before realignment (hereinbefore slice timing)", "before"),
        (ORDER, "before slice acquisition time correction", None),
        (ORDER, "after motion correction", "after"),
        (ORDER, "slice timing correction after realignment", "after"),
        (ORDER, "before realignment", "before"),
        (ORDER, "prior to motion correction", "before"),
        (ORDER, "after", "after"),
        (ORDER, "before", "before"),
        # FD-RMS is Jenkinson's measure, or an RMS over the series: not Power's FD
        (CRITERION, "FD-RMS", None),
        (CRITERION, "FD_RMS > 0.25 mm", None),
        (CRITERION, "FD RMS", None),
        (CRITERION, "RMS-FD", None),
        (CRITERION, "RMS FD > 0.2 mm", None),
        (CRITERION, "x_FD-RMS", None),
        (CRITERION, "x_RMS-FD", None),
        # a longer token on either side is another word
        (CRITERION, "FD-RMSD > 0.2 mm", "fd_power"),
        (CRITERION, "framewise displacement (dFD-RMS)", "fd_power"),
        (CRITERION, "FD > 0.5 mm (RMS-FDR)", "fd_power"),
        (CRITERION, "root mean square displacement", "fd_jenkinson"),
        (CRITERION, "relative RMS displacement > 0.25 mm", "fd_jenkinson"),
        (CRITERION, "FD", "fd_power"),
        (CRITERION, "FD > 0.5 mm", "fd_power"),
        (CRITERION, "RMS displacement > 0.25 mm", "fd_jenkinson"),
        (CRITERION, "relative RMS", "fd_jenkinson"),
        (TRANSFORM, "non-rigid", None),
        (TRANSFORM, "non rigid", None),
        (TRANSFORM, "Non-Rigid registration", None),
        (TRANSFORM, "x_non_rigid", None),
        (TRANSFORM, "rigid, then 3non-rigid", "rigid"),  # a digit or a letter before is no edge
        (TRANSFORM, "rigid, then xnon-rigid", "rigid"),
        (TRANSFORM, "rigid", "rigid"),
        (TRANSFORM, "rigid-body (6 DOF)", "rigid"),
        (TRANSFORM, "nonlinear", "nonlinear"),
        (SEGMENTATION, "SynthSeg (FreeSurfer 7)", None),
        (SEGMENTATION, "mri_synthseg (FreeSurfer 7.3)", None),
        (SEGMENTATION, "Synth-Seg in FreeSurfer", None),
        (SEGMENTATION, "FreeSurfer", "freesurfer_recon_all"),
        (SEGMENTATION, "recon-all (FreeSurfer 7)", "freesurfer_recon_all"),
        (SEGMENTATION, "FSL FAST", "fsl_fast"),
        # the same wording on the other field that has the member
        (BRAIN, "SynthSeg (FreeSurfer 7)", None),
        (BRAIN, "FreeSurfer SynthSeg", None),
        (BRAIN, "FreeSurfer", "freesurfer_recon_all"),
        (BRAIN, "FreeSurfer's mri_watershed", "freesurfer_recon_all"),  # no ruling names it (C16)
        (BRAIN, "HD-BET", None),
        (BRAIN, "BET", "bet"),
        # SPM's Fourier basis set is a set of regressors, not an ideal filter
        (FILTER, "Fourier basis set (SPM)", None),
        (FILTER, "Fourier bases", None),
        (FILTER, "Fourier-basis regressors", None),
        (FILTER, "fast Fourier transform", "ideal_fft"),
        (FILTER, "FFT", "ideal_fft"),
        (FILTER, "ideal rectangular filter", "ideal_fft"),
        (FILTER, "Butterworth", "butterworth"),
    ],
)
def test_a_wrong_member_of_the_sweep_is_kept_out(dotted: str, raw: str, want: str | None) -> None:
    assert _members(dotted, raw) == [want]


def test_a_block_reads_the_whole_term() -> None:
    """A term that names the member properly beside the blocked form loses it too. The paper's
    words are kept, and the loss is on the safe side."""
    assert _members(TRANSFORM, "rigid-body, not non-rigid") == [None]
    assert _members(SEGMENTATION, "FreeSurfer (recon-all), not SynthSeg") == [None]
    assert _members(FILTER, "ideal band-pass filter (Fourier basis)") == [None]
    assert _members(ORDER, "slice timing after realignment; smoothing after slice timing") == [None]
    # the word "symmetric" is read wherever it stands, the "symmetric normalization" of ANTs too
    assert _shared(SPACE, "MNI152NLin2009cAsym (ANTs symmetric normalization)") == (
        None,
        "underspecified",
    )
    # and where a line wrap breaks "asymmetric" after its first letter: a pattern is read in the
    # text as written too, so that a form a wrap glues together is not missed
    assert _shared(SPACE, "MNI152 2009c a-\nsymmetric") == (None, "underspecified")
    assert _shared(SPACE, "MNI152NLin2009c asym-\nmetrical template")[0] == "MNI152NLin2009cAsym"
    assert _members(ORDER, "realignment after-\nslice timing") == [None]


@pytest.mark.parametrize(
    ("dotted", "raw", "member"),
    [
        (TRANSFORM, "semi-rigid", "rigid"),
        (TRANSFORM, "non-affine", "affine"),
        (FILTER, "Fourier series regressors", "ideal_fft"),
        (FILTER, "Fourier set (SPM)", "ideal_fft"),
        (CRITERION, "FD (RMS of the six realignment parameters)", "fd_power"),
        (CRITERION, "RMS framewise displacement", "fd_power"),
        # a description of DVARS as an item of its own meets the bare alias "root mean square"
        (CRITERION, "root mean square of the temporal derivative", "fd_jenkinson"),
        (CRITERION, "root mean square intensity change > 0.5%", "fd_jenkinson"),
        (ORDER, "after correcting for slice timing", "after"),
        (ORDER, "after 3dTshift", "after"),
        (SEGMENTATION, "SAMSEG (FreeSurfer)", "freesurfer_recon_all"),
        (SEGMENTATION, "aseg (FreeSurfer)", "freesurfer_recon_all"),
    ],
)
def test_a_neighbour_with_no_ruling_is_as_it_was(dotted: str, raw: str, member: str) -> None:
    """The same fault as a ruled match, in a wording no ruling names. D2c stops the eight ruled
    forms and no more; each of these is put to the author (the design note, C16 and C17). The
    rows pin that a block reads its own form and not its neighbour's."""
    assert _members(dotted, raw) == [member]


def test_the_spm_rules_of_segmentation_stand_beside_its_block() -> None:
    rules = TERM_RULES[SEGMENTATION]
    assert set(rules.require_all) == {"spm_segment"} and set(rules.named_by) == {"spm_segment"}
    assert set(rules.block) == {"freesurfer_recon_all"}
    assert _members(SEGMENTATION, "SPM12") == ["spm_segment"]
    assert _members(SEGMENTATION, "CAT12 (SPM12)") == [None]


# --- C13: the wrong-member matches of the D1 sweep, the shared call's fields ---------------------


@pytest.mark.parametrize(
    ("dotted", "raw", "want"),
    [
        (REGISTRATION, "MSM folding-based registration", (None, "underspecified")),
        (REGISTRATION, "folding-based registration (MSM)", (None, "underspecified")),
        (REGISTRATION, "x_MSM folding-based registration", (None, "underspecified")),
        # a letter before "MSM" is another word, and the member stays
        (REGISTRATION, "EMSM folding-based registration", ("freesurfer_recon", "resolved")),
        (
            REGISTRATION,
            "multimodal surface matching folding-based registration",
            (None, "no_match"),
        ),
        (
            REGISTRATION,
            "multi-modal surface matching, a folding-based registration",
            (None, "no_match"),
        ),
        (
            REGISTRATION,
            "multi-modal_surface_matching folding-based registration",
            (None, "no_match"),
        ),
        (
            REGISTRATION,
            "multi_modal surface matching folding-based registration",
            (None, "no_match"),
        ),
        # a shared field's block reads the repaired text, as a coverage field's does
        (
            REGISTRATION,
            "multi\u2010modal surface matching folding-based registration",
            (None, "no_match"),
        ),
        (REGISTRATION, "folding-based registration", ("freesurfer_recon", "resolved")),
        (REGISTRATION, "FreeSurfer's spherical registration", ("freesurfer_recon", "resolved")),
        (REGISTRATION, "MSMSulc", ("msm_sulc", "resolved")),
        (REGISTRATION, "MSMAll", ("msm_all", "resolved")),
        # the symmetric 2009c template is another template. The family is still named
        (SPACE, "MNI152 2009c symmetric", (None, "underspecified")),
        (SPACE, "MNI152NLin2009c Sym", (None, "underspecified")),
        (SPACE, "Fonov 2009c symmetrical template", (None, "no_match")),
        (SPACE, "MNI152 2009c nonlinear symmetric", (None, "underspecified")),
        (SPACE, "MNI152NLin2009cAsym", ("MNI152NLin2009cAsym", "resolved")),
        (SPACE, "MNI152 2009c asymmetric", ("MNI152NLin2009cAsym", "resolved")),
        (SPACE, "MNI152 2009c Asym", ("MNI152NLin2009cAsym", "resolved")),
        (SPACE, "the Fonov 2009c template", ("MNI152NLin2009cAsym", "resolved")),
        (SPACE, "MNI152 2009c coordinate system", ("MNI152NLin2009cAsym", "resolved")),
        # "sym" is read as a word of its own or as the head of "symmetr...", not of another word
        (SPACE, "MNI152 2009c symbol", ("MNI152NLin2009cAsym", "resolved")),
        (SPACE, "MNI152 2009c symmetry-preserving", (None, "underspecified")),
        (SPACE, "MNI152 2009c sym2", (None, "underspecified")),  # a digit ends the word
        # TemplateFlow glues the word to the release
        (SPACE, "MNI152NLin2009cSym (Fonov 2009c)", (None, "underspecified")),
        (SPACE, "Fonov 2009c, MNI152NLin2009cSym", (None, "underspecified")),
        (SURFACE, "fsaverage_sym", (None, "no_match")),
        (SURFACE, "fsaverage sym", (None, "no_match")),
        (SURFACE, "fsaverage-sym template", (None, "no_match")),
        (SURFACE, "fsaverage symmetric", (None, "no_match")),
        (SURFACE, "fsaverage5_sym", (None, "no_match")),
        (SURFACE, "fsaverage6_sym", (None, "no_match")),
        (SURFACE, "symmetric fsaverage", (None, "no_match")),
        (SURFACE, "symmetric_fsaverage", (None, "no_match")),
        (SURFACE, "the symmetric fsaverage template", (None, "no_match")),
        (SURFACE, "asymmetric fsaverage", ("fsaverage", "resolved")),
        (SURFACE, "fsaverage", ("fsaverage", "resolved")),
        (SURFACE, "fsaverage template", ("fsaverage", "resolved")),
        (SURFACE, "fsaverage5", ("fsaverage5", "resolved")),
        (SURFACE, "fsaverage 6", ("fsaverage6", "resolved")),
        # the word is read wherever it stands in the term, as for the template
        (SURFACE, "fsaverage template symmetric", (None, "no_match")),
        (SURFACE, "fsaverage6 surface symmetric", (None, "no_match")),
        (SURFACE, "symmetric version of fsaverage5", (None, "no_match")),
        (SURFACE, "fsaverage (left-right symmetric)", (None, "no_match")),
        (SURFACE, "fsaverge5_sym", (None, "no_match")),  # the misspelt alias of the table
        (SURFACE, "fsaverage, smoothed with a symmetric kernel", (None, "no_match")),
        # with more in the term than the mesh and its noun, the density written apart names
        # two meshes, as it did before D2c: no member where HEAD gave none
        (SURFACE, "fsaverage 6 surface, symmetric", (None, "ambiguous")),
        (SURFACE, "fsaverage 5 mesh; sym", (None, "ambiguous")),
        (SURFACE, "fsaverage 6 surface, smoothed", (None, "ambiguous")),
        (SURFACE, "fsaverage 6 surface", ("fsaverage6", "resolved")),
        (SURFACE, "symmetric fsaverage 6 surface", (None, "ambiguous")),
        # glued to the name of the mesh, beside the mesh named properly
        (SURFACE, "fsaverage (fsaveragesym)", (None, "no_match")),
        (SURFACE, "fsaverage (fsaverages)", ("fsaverage", "resolved")),
        # every form of the word, and the word after a digit
        (SURFACE, "fsaverage5 symmetrised", (None, "no_match")),
        (SURFACE, "symmetrized fsaverage", (None, "no_match")),
        (SURFACE, "fsaverage, symmetrically registered", (None, "no_match")),
        (SURFACE, "fsaverage 5sym", (None, "no_match")),
        (SURFACE, "fsaverage5sym, fsaverage5", (None, "no_match")),
        # another word, and another mesh
        (SURFACE, "fsaverage5 (asymmetric)", ("fsaverage5", "resolved")),
        (SURFACE, "fsaverage5 symbol", ("fsaverage5", "resolved")),
        (SURFACE, "fsaverage (symbolic link)", ("fsaverage", "resolved")),
        (SURFACE, "fs_LR 32k symmetric mesh", ("fsLR_32k", "resolved")),
        # spellings the word does not hold keep the member they had (C17)
        (SURFACE, "fsaverage (symm.)", ("fsaverage", "resolved")),
        (SURFACE, "fsaverage symetric", ("fsaverage", "resolved")),
    ],
)
def test_a_wrong_member_is_kept_out_of_a_shared_field(
    dotted: str, raw: str, want: tuple[str | None, str]
) -> None:
    assert _shared(dotted, raw) == want
    # the helper of coverage_fields is the one the extractor calls
    got = resolve_shared(dotted, raw)
    assert (got.resolved, got.status) == want


def test_a_blocked_shared_term_through_the_shared_call() -> None:
    """End to end: the shared call's values through ``extract_preprocessing``. A blocked term is
    stored in the paper's words with no member, and the resolution record credits no alias of
    the member that was kept out."""
    text = (
        "Volumes were normalized to the MNI152 2009c symmetric template. "
        "Surfaces were aligned by MSM folding-based registration and sampled to fsaverage_sym."
    )

    def given(value: str, quote: str) -> FieldExtractionResult:
        return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)

    missing = FieldExtractionResult(status="missing")
    payload = ex.PreprocessingExtraction(
        target_space=given("MNI152 2009c symmetric", "normalized to the MNI152 2009c symmetric"),
        resolution_mm=missing,
        surface_registration=given(
            "MSM folding-based registration", "aligned by MSM folding-based registration"
        ),
        target_surface=given("fsaverage_sym", "sampled to fsaverage_sym"),
        intensity_convention=missing,
        intensity_value=missing,
    )
    records: list[Any] = []
    prep, _, _ = ex.extract_preprocessing(
        ParsedPaper(text=text, source="test", parser="manual"),
        "m",
        client=stub_client(payload),
        resolutions=records,
    )
    stored = {
        f"{step.kind}.{name}": getattr(step, name).extraction
        for step in prep.steps
        for name in ("target_space", "surface_registration", "target_surface")
        if hasattr(step, name)
    }
    want = {
        SPACE: ("MNI152 2009c symmetric", None, "underspecified", "MNI"),
        REGISTRATION: ("MSM folding-based registration", None, "underspecified", "MSM"),
        SURFACE: ("fsaverage_sym", None, "unrecognized", None),
    }
    for dotted, (verbatim, member, resolution, alias) in want.items():
        ext = stored[dotted]
        assert ext.status == "EXTRACTED", dotted
        term = ext.value
        assert (term.verbatim, term.resolved, term.resolution) == (verbatim, member, resolution)
        (record,) = [r for r in records if r.field == dotted]
        assert (record.raw_value, record.resolved_value, record.matched_alias) == (
            verbatim,
            member,
            alias,
        )


def test_a_blocked_shared_term_credits_no_alias() -> None:
    blocked = resolve_shared(SURFACE, "fsaverage_sym")
    assert (blocked.status, blocked.matched_alias) == ("no_match", None)
    family = resolve_shared(REGISTRATION, "MSM folding-based registration")
    assert (family.status, family.matched_alias) == ("underspecified", "MSM")
    family = resolve_shared(SPACE, "MNI152 2009c symmetric")
    assert family.matched_alias == "MNI"  # the family term, not the alias of the blocked member
    assert resolve_shared(SPACE, "MNI152 2009c").matched_alias == "MNI152 2009c"


def test_the_block_of_a_shared_field_is_read_for_that_field_alone() -> None:
    """A field that shares a bare id with one of the four and is not one of them reads the table
    and no rule, as every field of the shared call did before D2c."""
    other = ex._resolve_shared_term(
        "target_surface", "some_step.target_surface", "fsaverage_sym", None
    )
    assert (other.resolved, other.status) == ("fsaverage", "resolved")
    assert (
        ex._resolve_shared_term("target_surface", SURFACE, "fsaverage_sym", None).resolved is None
    )
    # the value context still reaches the table through the helper
    assert _shared(CONVENTION, "grand mean scaling", 10000) == ("fsl_grand_mean_10000", "resolved")
    assert _shared(CONVENTION, "grand mean scaling", None) == (None, "no_match")


def test_the_scripts_resolve_the_shared_fields_as_the_extractor_does() -> None:
    for dotted, raw in (
        (REGISTRATION, "MSM folding-based registration"),
        (REGISTRATION, "folding-based registration"),
        (SPACE, "MNI152 2009c symmetric"),
        (SPACE, "ICBM 152 Nonlinear Asymmetrical template version 2009c"),
        (SPACE, "ICBM152"),
        (SURFACE, "fsaverage_sym"),
        (SURFACE, "fsaverage 6 surface"),
        (SURFACE, "fs_LR"),
    ):
        member, status = _shared(dotted, raw)
        want = (
            "resolved"
            if member
            else ("underspecified" if status == "underspecified" else "unrecognized")
        )
        assert ta.resolve(_FIELD[dotted], [raw]) == [(member, want)], (dotted, raw)


def test_no_pattern_of_a_block_reads_an_alias_of_its_own_member() -> None:
    """A block that hit one of the member's own aliases would close that alias for good."""
    from extractor_mvp.coverage_fields import rule_hits

    for dotted, rules in TERM_RULES.items():
        field = _FIELD[dotted]
        for member, patterns in rules.block.items():
            assert member in field.members, (dotted, member)
            for alias in [member, *field.synonyms.get(member, [])]:
                words = alias.rpartition("@")[0] if "@" in alias else alias
                assert not any(rule_hits(p, words) for p in patterns), (dotted, member, alias)


# --- C11: "or" between two scrub criteria -------------------------------------------------------


def _items(dotted: str, raw: str) -> list[tuple[str, str | None]]:
    return [(t.verbatim, t.resolved) for t in _terms(dotted, raw)]


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("FD > 0.2 mm or DVARS > 5%", [("FD > 0.2 mm", "fd_power"), ("DVARS > 5%", "dvars")]),
        ("FD > 0.2 mm/TR or DVARS > 5%", [("FD > 0.2 mm/TR", "fd_power"), ("DVARS > 5%", "dvars")]),
        ("FD or DVARS", [("FD", "fd_power"), ("DVARS", "dvars")]),
        ("fd_power or dvars", [("fd_power", "fd_power"), ("dvars", "dvars")]),  # the tokens
        (
            "fd_jenkinson or bold_pct",
            [("fd_jenkinson", "fd_jenkinson"), ("bold_pct", "bold_pct")],
        ),
        ("FD or global_signal", [("FD", "fd_power"), ("global_signal", "global_signal")]),
        ("global_signal or FD", [("global_signal", "global_signal"), ("FD", "fd_power")]),
        # the threshold of DVARS in its own unit
        (
            "FD > 0.5 mm or DVARS > 0.5% \u0394BOLD",
            [("FD > 0.5 mm", "fd_power"), ("DVARS > 0.5% \u0394BOLD", "dvars")],
        ),
        (
            "FD > 0.2 mm/TR or DVARS > 0.5 %BOLD/s",
            [("FD > 0.2 mm/TR", "fd_power"), ("DVARS > 0.5 %BOLD/s", "dvars")],
        ),
        (
            "relative RMS > 0.25 mm/TR or FD",
            [("relative RMS > 0.25 mm/TR", "fd_jenkinson"), ("FD", "fd_power")],
        ),
        (
            "either FD > 0.5 mm or DVARS > 0.5%",
            [("either FD > 0.5 mm", "fd_power"), ("DVARS > 0.5%", "dvars")],
        ),
        (
            "FD > 0.5 mm, DVARS > 5% or BOLD change > 3%",
            [
                ("FD > 0.5 mm", "fd_power"),
                ("DVARS > 5%", "dvars"),
                ("BOLD change > 3%", "bold_pct"),
            ],
        ),
        (
            "FD or global signal > 3 SD",
            [("FD", "fd_power"), ("global signal > 3 SD", "global_signal")],
        ),
        # a side the field's rule reads whole is closed by that rule, whatever its words
        (
            "FD > 0.5 mm or 3 SD of average signal",
            [("FD > 0.5 mm", "fd_power"), ("3 SD of average signal", "global_signal")],
        ),
        # a comparative after "or" is part of its criterion
        ("FD > 0.5 mm or more", [("FD > 0.5 mm or more", "fd_power")]),
        ("DVARS 3 SD or above", [("DVARS 3 SD or above", "dvars")]),
        (
            "FD greater than or equal to 0.5 mm or DVARS > 5%",
            [("FD greater than or equal to 0.5 mm", "fd_power"), ("DVARS > 5%", "dvars")],
        ),
        (
            "DVARS > 5% or FD greater than or equal to 0.5 mm",
            [("DVARS > 5%", "dvars"), ("FD greater than or equal to 0.5 mm", "fd_power")],
        ),
        (
            "DVARS > 5% or FD Greater Than or Equal To 0.5 mm",
            [("DVARS > 5%", "dvars"), ("FD Greater Than or Equal To 0.5 mm", "fd_power")],
        ),
        (
            "DVARS > 5% or FD greater than  or equal to 0.5 mm",  # two spaces
            [("DVARS > 5%", "dvars"), ("FD greater than  or equal to 0.5 mm", "fd_power")],
        ),
        (
            "DVARS > 5% or FD greater than or\tequal to 0.5 mm",  # a tab
            [("DVARS > 5%", "dvars"), ("FD greater than or\tequal to 0.5 mm", "fd_power")],
        ),
        (
            "FD >= 0.5 mm or DVARS >= 3 SD or above",
            [("FD >= 0.5 mm", "fd_power"), ("DVARS >= 3 SD or above", "dvars")],
        ),
        # the last item must still be a criterion when a later "or" has added to it; where it is
        # not, nothing is made of the item
        (
            "FD > 0.5 mm or DVARS > 5% or both",
            [("FD > 0.5 mm or DVARS > 5% or both", None)],
        ),
        (
            "FD > 0.5 mm or more or DVARS > 5%",
            [("FD > 0.5 mm or more", "fd_power"), ("DVARS > 5%", "dvars")],
        ),
        *[
            (value, [(value, None)])
            for value in (
                # a rule read the first piece of the last item whole; what was added is a weak
                # name, a negation or a description (the review of D2c: each took that member)
                "DVARS > 5% or global signal > 3 SD or Power",
                "DVARS > 5% or global signal > 3 SD or Jenkinson",
                "FD > 0.5 mm or global signal > 3 SD or no DVARS",
                "FD > 0.5 mm or global_signal or DVARS was not used",
                "DVARS > 5% or global signal > 3 SD or framewise displacement was not computed",
                "FD > 0.5 or global signal > 3 SD or the root mean square of the temporal derivative",
                "FD > 0.5 mm or global signal > 3 SD or an average BOLD change > 3 SD",
                "FD > 0.5 mm or bold_pct or no DVARS",
                # an alias read the first piece, and the rest rules it out or counts something
                "FD > 0.5 mm or DVARS or rather the global signal > 3 SD",
                "DVARS > 5% or FD or rather no motion criterion",
                "FD > 0.5 mm or DVARS or rather no DVARS",
                "FD > 0.5 mm or DVARS or not",
                "DVARS > 5% or FD of 2 or more volumes",
                "DVARS > 5% or FD over 2 or 3 runs",
                # a threshold in a unit of another measure (an RMS of intensities is DVARS)
                "FD > 0.5 mm or relative RMS > 0.5% BOLD",
                "FD > 0.5 mm or RMS displacement > 0.5% BOLD",
                "DVARS > 5% or FD > 0.5% BOLD",
                "FD > 0.5 mm or relative RMS > 5%",
                # a number alone is no threshold: a reference number, a year
                "FD [12] or DVARS [13]",
                "FD (Power 2012) or relative RMS (Jenkinson 2002)",
                "FD 2012 or DVARS 2014",
            )
        ],
        (
            "FD > 0.5 mm or 2 or more contiguous volumes",
            [("FD > 0.5 mm or 2 or more contiguous volumes", "fd_power")],
        ),
        # two names for one measure: one item, one member
        ("FD or frame-wise displacement", [("FD or frame-wise displacement", "fd_power")]),
        ("framewise or RMS displacement", [("framewise or RMS displacement", "fd_jenkinson")]),
        # one measure, two candidate formulas: the authors' names alone part nothing
        ("FD computed per Power or Jenkinson", [("FD computed per Power or Jenkinson", None)]),
        ("Power or Jenkinson FD", [("Power or Jenkinson FD", None)]),
        # a side that rules its criterion out is no criterion
        ("FD > 0.5 mm or no DVARS", [("FD > 0.5 mm or no DVARS", None)]),
        ("FD > 0.5 mm or not DVARS", [("FD > 0.5 mm or not DVARS", None)]),
        # nor is a side with any other word that rules its criterion out: the word is beside
        # the name, and the side is no bare criterion
        ("DVARS > 5% or rather than FD", [("DVARS > 5% or rather than FD", None)]),
        ("FD > 0.5 mm or instead of DVARS", [("FD > 0.5 mm or instead of DVARS", None)]),
        ("FD > 0.5 mm or DVARS not > 5%", [("FD > 0.5 mm or DVARS not > 5%", None)]),
        # a side the vocabulary does not know stays inside the item, as before
        (
            "translation > 2 mm or rotation > 2 degrees",
            [("translation > 2 mm or rotation > 2 degrees", None)],
        ),
        (
            "head rotation > 2 degrees or FD > 0.5 mm",
            [("head rotation > 2 degrees or FD > 0.5 mm", "fd_power")],
        ),
        ("FD or global signal", [("FD or global signal", "fd_power")]),
        # inside parentheses, joined by a hyphen, in capitals: no separator, as for "and"
        ("FD (Power or Jenkinson)", [("FD (Power or Jenkinson)", None)]),
        ("FD-or-DVARS", [("FD-or-DVARS", None)]),
        ("FD > 0.5 mm OR DVARS > 5%", [("FD > 0.5 mm OR DVARS > 5%", None)]),
        # an "or" that opens an item, a comma or a slash before it having parted the list, is
        # dropped where a criterion follows it
        (
            "FD > 0.5 mm, DVARS > 5%, or global signal > 3 SD",
            [
                ("FD > 0.5 mm", "fd_power"),
                ("DVARS > 5%", "dvars"),
                ("global signal > 3 SD", "global_signal"),
            ],
        ),
        ("FD > 0.5 mm; or DVARS > 5%", [("FD > 0.5 mm", "fd_power"), ("DVARS > 5%", "dvars")]),
        (" or DVARS > 5%", [("DVARS > 5%", "dvars")]),  # also where the value opens with a space
        ("FD > 0.5 mm, or or DVARS > 5%", [("FD > 0.5 mm", "fd_power"), ("DVARS > 5%", "dvars")]),
        ("FD and/or DVARS", [("FD", "fd_power"), ("DVARS", "dvars")]),
        (
            "FD > 0.5 mm, or DVARS > 5% or BOLD change > 3%",
            [
                ("FD > 0.5 mm", "fd_power"),
                ("DVARS > 5%", "dvars"),
                ("BOLD change > 3%", "bold_pct"),
            ],
        ),
        # and where what follows grows into something else, the item is as it was, "or" and all
        (
            "FD > 0.5 mm, or DVARS or both",
            [("FD > 0.5 mm", "fd_power"), ("or DVARS or both", "dvars")],
        ),
        # and stays where none does: the item is as it was before D2c, its member too
        ("FD > 0.5 mm, or more", [("FD > 0.5 mm", "fd_power"), ("or more", None)]),
        ("FD, or more or DVARS", [("FD", "fd_power"), ("or more or DVARS", "dvars")]),
        (
            "FD computed per Power, or Jenkinson",
            [("FD computed per Power", "fd_power"), ("or Jenkinson", "fd_jenkinson")],
        ),
        ("FD > 0.5 mm, or no DVARS", [("FD > 0.5 mm", "fd_power"), ("or no DVARS", "dvars")]),
        ("FD > 0.5 mm, or, DVARS", [("FD > 0.5 mm", "fd_power"), ("or", None), ("DVARS", "dvars")]),
        # the block on FD-RMS reads the whole item, and no side of it is parted off
        ("FD (Power) or FD-RMS", [("FD (Power) or FD-RMS", None)]),
        ("FD-RMS or DVARS", [("FD-RMS or DVARS", None)]),
        # the left side is read as it has grown, not as its first piece: a side that holds a
        # criterion the vocabulary does not know is no bare criterion
        (
            "translation > 2 mm or FD > 0.5 mm or DVARS > 5%",
            [("translation > 2 mm or FD > 0.5 mm or DVARS > 5%", None)],
        ),
        (
            "FD > 0.5 mm or no DVARS or BOLD change > 3%",
            [("FD > 0.5 mm or no DVARS or BOLD change > 3%", None)],
        ),
        # a parenthesis is held whole, and read again before a side is read, left or right: it
        # counts as what it holds
        (
            "framewise displacement (FD) or DVARS",
            [("framewise displacement (FD)", "fd_power"), ("DVARS", "dvars")],
        ),
        (
            "DVARS > 5% or framewise displacement (FD) > 0.5 mm",
            [("DVARS > 5%", "dvars"), ("framewise displacement (FD) > 0.5 mm", "fd_power")],
        ),
        (
            "FD (> 0.5 mm) or DVARS (> 5%)",
            [("FD (> 0.5 mm)", "fd_power"), ("DVARS (> 5%)", "dvars")],
        ),
        # any other word beside the name leaves the side in its item: a word before a
        # parenthesis, a citation, a negation in a parenthesis, a qualifier, a description
        ("motion (FD) or DVARS", [("motion (FD) or DVARS", None)]),
        ("DVARS > 5% or motion (FD)", [("DVARS > 5% or motion (FD)", None)]),
        (
            "FD (Smyser et al., 2010) > 0.5 mm or DVARS > 5%",
            [("FD (Smyser et al., 2010) > 0.5 mm or DVARS > 5%", None)],
        ),
        ("FD > 0.5 mm or DVARS (not used)", [("FD > 0.5 mm or DVARS (not used)", None)]),
        (
            "FD > 0.5 mm or standardized DVARS > 1.5",
            [("FD > 0.5 mm or standardized DVARS > 1.5", None)],
        ),
        (
            "FD > 0.5 mm or the temporal derivative measure (DVARS) > 5%",
            [("FD > 0.5 mm or the temporal derivative measure (DVARS) > 5%", None)],
        ),
        # a description that holds an alias of some member is no criterion of that member (the
        # reviews of D2c): each of these stays whole and unresolved, as before D2c
        *[
            (f"FD > 0.5 mm or {words}", [(f"FD > 0.5 mm or {words}", None)])
            for words in (
                "the RMS of the volume-to-volume BOLD change > 0.5%",
                "an average BOLD change > 3 SD",
                "a whole-brain mean BOLD change of more than 3 standard deviations",
                "the relative RMS intensity difference to the reference volume > 0.3",
                "the relative RMS of the BOLD signal derivative > 0.5%",
            )
        ],
        # the bare "root mean square" makes no criterion of a side: a description of DVARS in
        # words holds it too. The item stays whole and names two members, as before D2c
        *[
            (f"FD > 0.5 mm or {words}", [(f"FD > 0.5 mm or {words}", None)])
            for words in (
                "root mean square of the temporal derivative > 0.5%",
                "root mean square of the volume-to-volume change in voxel values > 0.5%",
                "root mean square of successive differences of the voxel time series > 3%",
                "root mean square of the differentiated time courses",
                "the root mean square of the frame-to-frame image difference > 2%",
                "root mean square of the temporal difference > 0.5%",
                "root-mean-square intensity change > 0.5%",
                # nor of a displacement named through it alone: unresolved, as before D2c
                "root mean square displacement > 0.25 mm",
            )
        ],
        ("Power or DVARS", [("Power or DVARS", None)]),
        # the other aliases of that member name the displacement, and part
        (
            "FD > 0.5 mm or RMS displacement > 0.25 mm",
            [("FD > 0.5 mm", "fd_power"), ("RMS displacement > 0.25 mm", "fd_jenkinson")],
        ),
        # after a comma the description is an item of its own and meets the bare alias, as it
        # did before D2c (put to the author, C17)
        (
            "FD > 0.5 mm, root mean square of the temporal derivative > 0.5%",
            [
                ("FD > 0.5 mm", "fd_power"),
                ("root mean square of the temporal derivative > 0.5%", "fd_jenkinson"),
            ],
        ),
        (
            "DVARS (the root mean square of the temporal derivative) > 5% or FD > 0.5 mm",
            [("DVARS (the root mean square of the temporal derivative) > 5% or FD > 0.5 mm", None)],
        ),
        # two names of one measure that are aliases of two members read as two criteria: the
        # wording does not say that the "or" renames (put to the author, C17)
        (
            "framewise displacement (FD) or relative RMS displacement > 0.3 mm",
            [
                ("framewise displacement (FD)", "fd_power"),
                ("relative RMS displacement > 0.3 mm", "fd_jenkinson"),
            ],
        ),
    ],
)
def test_or_parts_two_scrub_criteria(raw: str, want: list[tuple[str, str | None]]) -> None:
    assert _items(CRITERION, raw) == want


_WEAK = frozenset(name.lower() for name in OR_WEAK_ALIASES[CRITERION])


def _bare(member: str, words: str, weak: frozenset[str] = _WEAK) -> bool:
    """``bare_criterion`` as ``extractor._or_member`` calls it for a side that resolved to this
    member: its token and aliases, the weak aliases, the unit of its threshold."""
    names = [member, *_SPEC[CRITERION].synonyms[member]]
    return bare_criterion(words, names, weak, OR_UNITS[CRITERION].get(member))


@pytest.mark.parametrize(
    "words",
    [
        # the name alone: an alias, the token, a plural, an article, "either"
        "FD",
        "fd_power",
        "FDs",
        "frame-wise displacement",
        "the FD",
        "a FD",
        "an FD",
        "either FD",
        "either the FD > 0.5 mm",
        # a comparison in signs
        "FD > 0.5 mm",
        "FD < 0.5 mm",
        "FD >= 0.5 mm",
        "FD <= 0.5",
        "FD = 0.5",
        "FD ~ 0.5 mm",
        "FD \u2265 0.5 mm",
        "FD \u2264 0.5 mm",
        "FD \u2248 0.5 mm",
        # or in words
        "FD greater than 0.5 mm",
        "FD more than 0.5 mm",
        "FD less than 0.5 mm",
        "FD larger than 0.5 mm",
        "FD smaller than 0.5 mm",
        "FD higher than 0.5 mm",
        "FD lower than 0.5 mm",
        "FD greater than or equal to 0.5 mm",
        "FD less than or equal to 0.5 mm",
        "FD above 0.5 mm",
        "FD below 0.5 mm",
        "FD over 0.5 mm",
        "FD under 0.5 mm",
        "FD exceeding 0.5 mm",
        "FD exceeds 0.5 mm",
        "FD exceeded 0.5 mm",
        "FD exceed 0.5 mm",
        "FD at least 0.5 mm",
        "FD at most 0.5 mm",
        "FD of 0.5 mm",
        "FD equal to 0.5 mm",
        "FD of at least 0.5 mm",
        # the number
        "FD > 0,5 mm",
        "FD > .5 mm",
        "FD > 2",
        "FD > 10 mm",
        "FD 0.5 mm",
        # the unit
        "FD > 0.5 cm",
        "FD > 1 voxel",
        "FD > 2 voxels",
        # the rate
        "FD > 0.2 mm/TR",
        "FD > 0.2 mm / TR",
        "FD > 0.2 mm per TR",
        "FD > 0.2 mm/s",
        "FD > 0.2 mm/sec",
        "FD > 0.2 mm per second",
        "FD > 0.2 mm per seconds",
        "FD > 0.2 mm/ms",
        "FD > 0.2 mm/min",
        "FD > 0.2 mm per volume",
        "FD > 0.2 mm per volumes",
        "FD > 0.2 mm/vol",
        "FD > 0.2 mm/vols",
        "FD > 0.2 mm per frame",
        "FD > 0.2 mm per frames",
        "FD > 0.2 mm per scan",
        "FD > 0.2 mm per scans",
        "FD > 0.2 mm per time point",
        "FD > 0.2 mm per timepoints",
        # a comparative after the threshold
        "FD of 0.5 mm or more",
        "FD of 0.5 mm or above",
        "FD of 0.5 mm or greater",
        "FD of 0.5 mm or higher",
        "FD of 0.5 mm or larger",
        "FD of 0.5 mm or less",
        "FD of 0.5 mm or below",
        "FD of 0.5 mm or lower",
        "FD of 0.5 mm or smaller",
        "FD > 0.5 mm per TR or more",
        # brackets count as what they hold; several names of the member; the joints of the table
        "framewise displacement (FD) > 0.5 mm",
        "FD (> 0.5 mm)",
        "FD [framewise displacement]",
        "FD (Power) > 0.5 mm",
        "framewise_displacement > 0.5 mm",
        "frame\u2010wise displacement > 0.5 mm",
        "FD (FD) > 0.5 mm",
        "FD>0.5mm",
        "FD > 0.5 mm.",
        "FD > 0.5 mm .",
    ],
)
def test_one_measure_with_at_most_its_threshold(words: str) -> None:
    assert _bare("fd_power", words)


@pytest.mark.parametrize(
    ("member", "words"),
    [
        # DVARS: a percentage of the BOLD signal, or a number of standard deviations
        ("dvars", "DVARS > 5%"),
        ("dvars", "DVARS > 5 %"),
        ("dvars", "DVARS > 5 percent"),
        ("dvars", "DVARS > 0.5% BOLD"),
        ("dvars", "DVARS > 0.5 %BOLD/s"),
        ("dvars", "DVARS > 0.5% \u0394BOLD"),
        ("dvars", "DVARS > 0.5% \u2206 BOLD"),
        ("dvars", "DVARS > 3 SD"),
        ("dvars", "DVARS > 3 SDs"),
        ("dvars", "DVARS > 3 s.d."),
        ("dvars", "DVARS > 3 standard deviations"),
        ("dvars", "DVARS > 1 standard deviation"),
        ("dvars", "DVARS 3 SD or above"),
        ("dvars", "DVARS > 5"),
        # a percentage BOLD change: a percentage
        ("bold_pct", "percent BOLD change > 3%"),
        ("bold_pct", "BOLD change > 3 percent"),
        ("bold_pct", "BOLD change > 0.5% BOLD"),
        ("bold_pct", "% BOLD > 2"),
        # a displacement: a length
        ("fd_jenkinson", "relative RMS > 0.25 mm"),
        ("fd_jenkinson", "RMS displacement > 0.1 cm"),
        ("fd_jenkinson", "RMS displacement > 1 voxel"),
        ("fd_jenkinson", "relative RMS > 0.25"),
    ],
)
def test_a_threshold_in_a_unit_of_its_measure(member: str, words: str) -> None:
    assert _bare(member, words)


@pytest.mark.parametrize(
    ("member", "words"),
    [
        # a unit of another kind says the name stands for another measure: an RMS of intensities
        # is DVARS and not Jenkinson's displacement (the review of D2c)
        ("fd_jenkinson", "relative RMS > 0.5% BOLD"),
        ("fd_jenkinson", "relative RMS > 0.5%\u0394BOLD"),
        ("fd_jenkinson", "RMS displacement > 0.5% BOLD"),
        ("fd_jenkinson", "relative RMS > 5%"),
        ("fd_jenkinson", "relative RMS > 3 SD"),
        ("fd_power", "FD > 0.5% BOLD"),
        ("fd_power", "FD > 5%"),
        ("fd_power", "FD > 5 percent"),
        ("fd_power", "FD > 3 SD"),
        ("fd_power", "FD > 3 standard deviations"),
        ("dvars", "DVARS > 0.5 mm"),
        ("dvars", "DVARS > 2 voxels"),
        ("dvars", "DVARS > 0.5%: BOLD"),  # only a delta may stand between the sign and "BOLD"
        ("dvars", "DVARS > 0.5% BOLD signal change"),
        ("bold_pct", "BOLD change > 3 SD"),
        ("bold_pct", "BOLD change > 0.5 mm"),
        # a unit is read in the spellings listed and in no near one
        ("dvars", "DVARS > 5% \u0394"),
        ("dvars", "DVARS > 0.5 percentBOLD"),
        ("dvars", "DVARS > 3 s.d"),
        ("dvars", "DVARS > 3 std"),
        ("dvars", "DVARS > 3 sods"),
        ("bold_pct", "BOLD change > 3 percents"),
        ("fd_power", "FD > 0.5 mmmm"),
        # no measure of the field is in degrees
        ("fd_power", "FD > 2 degrees"),
        ("fd_power", "FD > 2 deg"),
        ("fd_power", "FD > 2\u00b0"),
    ],
)
def test_a_unit_of_another_kind_is_no_threshold(member: str, words: str) -> None:
    assert not _bare(member, words)
    assert set(OR_UNITS) == OR_JOINS_ITEMS
    assert set(OR_UNITS[CRITERION]) == {"fd_power", "fd_jenkinson", "dvars", "bold_pct"}


@pytest.mark.parametrize(
    "words",
    [
        "",
        "DVARS",  # no name of this member
        "Power",  # a weak alias alone
        "Power > 0.5 mm",
        # a negation, in any words and in brackets
        "no FD",
        "FD not used",
        "FD (not used)",
        "rather than FD",
        # a qualifier, a description, a citation
        "standardized FD",
        "mean FD > 0.2 mm",
        "FD > 0.5 mm in more than half the volumes",
        "FD threshold of 0.5 mm",
        "FD (Smyser et al., 2010) > 0.5 mm",
        # a threshold that is not one
        "FD or more",
        "FD greater than",
        "FD > mm",
        "FD > 0.5 mm 0.2 mm",
        "FD > 0.5 parsecs",
        # each list of the form is closed: a word that is in none of them
        "FD not > 0.5 mm",
        "its FD",
        "FD in 2 voxels",
        "FD to 0.5 mm",
        "FD by 0.5 mm",
        "FD greater 0.5 mm",
        "FD > five mm",
        "FD > 0.5 m",
        "FD > 0.5 mm per day",
        "FD > 0.5 mm signal change",
        "FD > 0.5 BOLD",
        "FD {FD} > 0.5 mm",  # braces are no brackets
        "either either FD > 0.5 mm",
        "the the FD > 0.5 mm",
        # and each part stands once, in its place
        "FD > 0.5 mm per TR per s",
        "FD > 0.5 mm%",
        "FD > 5%%",
        "FD > 0.5 mmor more",
        # a number alone is no threshold: a year, a reference, a version
        "FD 2012",
        "FD (2012)",
        "FD [12]",
        "FD (Power 2012)",
        "FD 2.0",
        "FD 1,2",
        "FD > 0.5 mm per fortnight",
        "FD > 0.5 mm per",
        "FD > 0.5.5 mm",
        "FD > 0.5 mm or more or less",
        "FD > 0.5 mm or elsewhere",
        "FD > 0.5 mm or",
        "FD > 0.5 mm..",
        "FD > 0.5 mm:",
        "FD > 0.5 mm;",
        "FD: 0.5 mm",
        # the order: the name comes first, "either" and the article before it
        "0.5 mm FD",
        "FD either",
        "FD > 0.5 mm the",
        "FD and",
        # a longer token is another word
        "xFD > 0.5",
        "theFD",
        "FDR > 0.05",
    ],
)
def test_anything_else_beside_the_name_is_no_bare_criterion(words: str) -> None:
    assert not _bare("fd_power", words)


def test_a_bare_criterion_needs_a_name_that_is_not_weak() -> None:
    assert _bare("fd_jenkinson", "RMS displacement > 0.25 mm")
    assert _bare("fd_jenkinson", "relative RMS displacement > 0.25 mm")  # two aliases overlap
    assert not _bare("fd_jenkinson", "Jenkinson's relative RMS")  # "'s" is left over
    assert _bare("fd_jenkinson", "Jenkinson relative RMS > 0.2 mm")
    for weak_alone in ("Jenkinson", "root mean square > 0.3 mm", "Jenkinson root mean square"):
        assert not _bare("fd_jenkinson", weak_alone), weak_alone
        assert _bare("fd_jenkinson", weak_alone, frozenset()), weak_alone  # no weak list: bare
    assert _bare("bold_pct", "percent BOLD change > 3%")  # two aliases overlap
    assert not _bare("bold_pct", "percent BOLD signal change > 3%")
    # A member with no unit of its own takes a number after a comparison and no unit at all.
    # That is the function's answer; the extraction never asks it about a threshold, since a
    # side is global_signal only through its rule or as the bare token.
    assert bare_criterion("global_signal > 3", ["global_signal"])
    for words in ("global_signal > 3 SD", "global_signal > 3 mm", "global_signal > 3 %"):
        assert not bare_criterion(words, ["global_signal"]), words
    assert not bare_criterion("global_signal 3", ["global_signal"])
    assert _items(CRITERION, "FD > 0.5 mm or global_signal > 3") == [
        ("FD > 0.5 mm or global_signal > 3", "fd_power")
    ]


def test_a_control_character_in_the_words_is_read_as_it_stands() -> None:
    # the character the form writes a name as can pad a name, and hides no word and no unit
    assert _bare("fd_power", "FD\x01 > 0.5 mm")
    assert not _bare("fd_power", "FD > 0.5 mm\x01")
    assert not _bare("fd_power", "FD > 0.5\x01mm")
    assert not _bare("fd_power", "\x01 > 0.5 mm")


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # the item before would borrow the head noun of an item the rule makes ("displacement",
        # "BOLD"): the value is split as it was before D2c
        (
            "global intensity RMS, framewise displacement or DVARS > 5%",
            [("global intensity RMS", None), ("framewise displacement or DVARS > 5%", None)],
        ),
        (
            "RMS, framewise displacement or DVARS > 5%",
            [("RMS", None), ("framewise displacement or DVARS > 5%", None)],
        ),
        (
            "(GIR) global intensity RMS, framewise displacement or DVARS > 5%",
            [("(GIR) global intensity RMS", None), ("framewise displacement or DVARS > 5%", None)],
        ),
        (
            " global intensity RMS, framewise displacement or DVARS > 5%",  # a space opens the value
            [("global intensity RMS", None), ("framewise displacement or DVARS > 5%", None)],
        ),
        (
            "volumes with spikes > 3 %, % BOLD or FD > 0.5 mm",
            [("volumes with spikes > 3 %", None), ("% BOLD or FD > 0.5 mm", None)],
        ),
        # the rule made no more than a dropped "or", and the item before borrows all the same
        (
            "global intensity RMS, global signal, or global signal > 3 SD",
            [
                ("global intensity RMS", None),
                ("global signal", None),
                ("or global signal > 3 SD", None),
            ],
        ),
        # an item that would LOSE the member the list gave it: the noun it borrowed is gone
        (
            "global intensity RMS, global signal > 3 SD or framewise displacement",
            [
                ("global intensity RMS", "fd_jenkinson"),
                ("global signal > 3 SD or framewise displacement", "fd_power"),
            ],
        ),
        (
            "%, global_signal or % BOLD",
            [("%", "bold_pct"), ("global_signal or % BOLD", "bold_pct")],
        ),
        # an empty item between two separators is no item, with the rule or without it
        (
            "global intensity RMS,, framewise displacement or DVARS > 5%",
            [("global intensity RMS", None), ("framewise displacement or DVARS > 5%", None)],
        ),
        (
            "FD > 0.5 mm,, DVARS > 5% or global signal > 3 SD",
            [
                ("FD > 0.5 mm", "fd_power"),
                ("DVARS > 5%", "dvars"),
                ("global signal > 3 SD", "global_signal"),
            ],
        ),
        # the item that would borrow may stand anywhere in the value, not only first
        (
            "FD > 0.5 mm, global intensity RMS, framewise displacement or DVARS > 5%",
            [
                ("FD > 0.5 mm", "fd_power"),
                ("global intensity RMS", None),
                ("framewise displacement or DVARS > 5%", None),
            ],
        ),
        (
            "DVARS or FD, spikes, global intensity RMS, framewise displacement or DVARS > 5%",
            [
                ("DVARS or FD", None),
                ("spikes", None),
                ("global intensity RMS", None),
                ("framewise displacement or DVARS > 5%", None),
            ],
        ),
        # an item the rule did not part and that resolves as before leaves the rule its items,
        # also one the list resolver completed before D2c ("framewise" from "RMS displacement")
        (
            "framewise, RMS displacement, FD > 0.5 mm or DVARS > 5%",
            [
                ("framewise", "fd_power"),
                ("RMS displacement", "fd_jenkinson"),
                ("FD > 0.5 mm", "fd_power"),
                ("DVARS > 5%", "dvars"),
            ],
        ),
        (
            "translation > 2 mm, FD > 0.5 mm or DVARS > 5%",
            [("translation > 2 mm", None), ("FD > 0.5 mm", "fd_power"), ("DVARS > 5%", "dvars")],
        ),
        (
            "DVARS > 5%, FD > 0.5 mm or global signal > 3 SD, spikes",
            [
                ("DVARS > 5%", "dvars"),
                ("FD > 0.5 mm", "fd_power"),
                ("global signal > 3 SD", "global_signal"),
                ("spikes", None),
            ],
        ),
    ],
)
def test_the_or_rule_gives_a_member_to_its_own_items_alone(
    raw: str, want: list[tuple[str, str | None]]
) -> None:
    """The list resolver completes an unresolved item with the head noun of the next item when
    that one resolved (D2b). An item the "or" rule makes resolves where the item it came from did
    not, so the rule is dropped for a value in which that would give another item a member."""
    assert _items(CRITERION, raw) == want
    spec = _SPEC[CRITERION]
    table = (spec.synonyms, spec.underspecified)
    plain = ex._split_terms(raw, ex._keep_whole(CRITERION, table))
    made = ex._field_items(CRITERION, raw, spec.literal_type, table)
    assert (made == plain) is (len(want) == len(plain))


@pytest.mark.parametrize(
    ("dotted", "raw"),
    [
        ("distortion_correction.method", "fieldmap or reverse phase encoding"),
        ("distortion_correction.tool", "FSL topup or FUGUE"),
        ("ica_denoise.method", "ICA-FIX or ICA-AROMA"),
        (COMPCOR, "aCompCor or tCompCor"),
        ("nuisance_regression.tissue_regressors", "white matter or CSF"),
        ("nuisance_regression.physio_regressors", "RETROICOR or RVT"),
    ],
)
def test_or_parts_nothing_in_another_list_field(dotted: str, raw: str) -> None:
    """In a tool or method list "or" joins alternatives of which one was used: both members
    would be recorded, and one of them is wrong."""
    assert dotted not in OR_JOINS_ITEMS
    assert _items(dotted, raw) == [(raw, None)]


def test_the_or_rule_is_given_by_the_field_and_not_by_the_splitter() -> None:
    assert frozenset({CRITERION}) == OR_JOINS_ITEMS
    assert OR_WEAK_ALIASES == {CRITERION: ("Power", "Jenkinson", "root mean square")}
    # the splitter on its own parts nothing at "or", for any text
    assert ex._split_terms("FD or DVARS") == ["FD or DVARS"]
    spec = _SPEC[CRITERION]
    table = (spec.synonyms, spec.underspecified)
    assert ex._field_items(CRITERION, "FD or DVARS", spec.literal_type, table) == ["FD", "DVARS"]
    # each weak alias is an alias of the table, so the list cannot drift from it
    aliases = {a for group in spec.synonyms.values() for a in group}
    assert set(OR_WEAK_ALIASES[CRITERION]) <= aliases
    # no alias of the field holds "or" as a word: none has to be held whole against the rule
    assert not [a for a in aliases if ex._OR.search(a)]


def _shared_call_all_missing() -> Any:
    missing = FieldExtractionResult(status="missing")
    return ex.PreprocessingExtraction(
        target_space=missing,
        resolution_mm=missing,
        surface_registration=missing,
        target_surface=missing,
        intensity_convention=missing,
        intensity_value=missing,
    )


def test_or_parts_two_criteria_through_the_coverage_call() -> None:
    """End to end: the model's list value through ``extract_preprocessing``. Every other test
    of the rule calls the splitter; this one shows the extraction's own call uses it."""
    sentence = "Frames with FD > 0.5 mm or DVARS > 5% were censored."
    value = FieldExtractionResult(
        status="extracted", value="FD > 0.5 mm or DVARS > 5%", verbatim_quote=sentence
    )
    prep, _, _ = ex.extract_preprocessing(
        ParsedPaper(text=sentence, source="test", parser="manual"),
        "m",
        client=stub_client(
            _shared_call_all_missing(), temporal=TemporalVolumeExtraction(scrub_criterion=value)
        ),
    )
    scrub = next(step for step in prep.steps if step.kind == "scrub")
    assert scrub.criterion.extraction.status == "EXTRACTED"
    assert [(t.verbatim, t.resolved) for t in scrub.criterion.extraction.value] == [
        ("FD > 0.5 mm", "fd_power"),
        ("DVARS > 5%", "dvars"),
    ]


def test_an_item_of_many_ors_stays_whole() -> None:
    """Each "or" resolves the text on both of its sides, the left one as it has grown. A value
    made of "or"s cost seconds before the limit (the review of D2c)."""
    spec = _SPEC[CRITERION]
    table = (spec.synonyms, spec.underspecified)
    at_limit = " or ".join(["FD", "DVARS"] * 4 + ["FD"])  # eight "or"s
    assert at_limit.count(" or ") == ex._OR_LIMIT
    assert len(ex._field_items(CRITERION, at_limit, spec.literal_type, table)) == 9
    over = at_limit + " or DVARS"
    assert ex._field_items(CRITERION, over, spec.literal_type, table) == [over]


def test_the_or_rule_resolves_a_bounded_number_of_sides() -> None:
    """The cost of the rule, counted and not timed: each "or" of an item within the limit asks
    for the member of two sides and an "or" that opens an item for one; the last item is asked
    about once more wherever an item was begun as a criterion (after a cut or a dropped "or"),
    whether or not anything is then made; an item over the limit asks for nothing."""
    spec = _SPEC[CRITERION]
    table = (spec.synonyms, spec.underspecified)
    member = ex._or_member(CRITERION, spec.literal_type, table)
    assert member is not None
    asked: list[str] = []

    def counting(piece: str) -> str | None:
        asked.append(piece)
        return member(piece)

    for ors in range(ex._OR_LIMIT + 1):
        asked.clear()
        value = " or ".join(["FD > 0.5 mm", "DVARS > 5%"] * 5)  # nine "or"s
        value = " or ".join(value.split(" or ")[: ors + 1])
        ex._split_terms(value, (), counting)
        assert len(asked) == 2 * ors + (1 if ors else 0), (ors, asked)
    asked.clear()
    over = " or ".join(["FD > 0.5 mm", "DVARS > 5%"] * 400)
    assert ex._split_terms(over, (), counting) == [over] and asked == []
    # the limit is per item: a comma starts a new count
    two_items = " or ".join(["FD", "DVARS"] * 3) + ", " + " or ".join(["FD", "DVARS"] * 3)
    asked.clear()
    assert len(ex._split_terms(two_items, (), counting)) == 12 and len(asked) == 22
    # an "or" that opens an item has no left side to ask about
    for value, items, asks in (
        ("FD, or DVARS", 2, 2),
        ("FD, or DVARS or BOLD change", 3, 4),
        ("FD > 0.5 mm or DVARS > 5% or both", 1, 5),  # nothing made, and asked all the same
    ):
        asked.clear()
        assert len(ex._split_terms(value, (), counting)) == items and len(asked) == asks, value


# --- C14: the detrend rule ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "quote",
    [
        "No linear detrending was applied.",
        "Linear and quadratic trends were not removed.",
        "No linear or quadratic detrending was applied.",
        "Detrending: none (a quadratic fit was tested and rejected).",
        "No detrending, linear or otherwise, was applied.",
    ],
)
def test_the_detrend_rule_leaves_none_alone(quote: str) -> None:
    """Each sentence names an order, which the rule handed to the value none before C14."""
    assert detrend_highest_order(None, quote) in ("linear", "quadratic")
    assert detrend_highest_order("none", quote) == "none"
    assert ta.resolve(_FIELD[DETREND], ["none"], None, quote) == [("none", "resolved")]


@pytest.mark.parametrize(
    ("resolved", "quote", "want"),
    [
        # the rule of 2026-10-28, as it was
        ("linear", "Linear and quadratic trends were removed.", "quadratic"),
        ("quadratic", "Linear trends were removed.", "quadratic"),
        ("linear", "Linear trends were removed.", "linear"),
        (None, "Linear and quadratic trends were removed.", "quadratic"),
        (None, "Data were detrended.", None),
        (None, "Detrending: none.", "none"),
        # no other negation is read: a term that resolved to nothing takes the order its quote
        # names, also where the quote rules it out (put to the author, C19)
        (None, "No linear detrending was applied.", "linear"),
        ("linear", "Linear, but not quadratic, trends were removed.", "quadratic"),
    ],
)
def test_the_detrend_rule_is_otherwise_as_it_was(
    resolved: str | None, quote: str, want: str | None
) -> None:
    assert detrend_highest_order(resolved, quote) == want


def test_an_unresolved_term_of_the_coverage_call_takes_the_order_its_quote_names() -> None:
    """The rule of 2026-10-28 on the coverage call's own value, as it was before D2c: a term that
    resolved to nothing takes the highest order its quote names. Only promote() asks for less
    (``raise_only``)."""
    sentence = "Data were detrended with linear and quadratic terms."
    value = FieldExtractionResult(status="extracted", value="detrended", verbatim_quote=sentence)
    prep, diagnostics, _ = ex.extract_preprocessing(
        ParsedPaper(text=sentence, source="test", parser="manual"),
        "m",
        client=stub_client(
            _shared_call_all_missing(), temporal=TemporalVolumeExtraction(nuisance_detrend=value)
        ),
    )
    detrend = next(s for s in prep.steps if s.kind == "nuisance_regression").detrend.extraction
    assert (detrend.value.verbatim, detrend.value.resolved) == ("detrended", "quadratic")
    assert [d.failure_reason for d in diagnostics if d.field == DETREND] == [
        "detrend_highest_order_named:None->quadratic"
    ]


def test_a_negated_term_that_names_an_order_resolves_as_before() -> None:
    """Negation is not read by the alias table (C14 leaves that as it is): a term that names the
    order it rules out still resolves to it through the alias."""
    assert _members(DETREND, "No linear detrending") == ["linear"]
    assert _members(DETREND, "no detrending") == [None]


def _detrend_record(extraction: dict[str, Any]) -> dict[str, Any]:
    step = {
        "kind": "nuisance_regression",
        "detrend": {"field_id": "detrend", "extraction": extraction},
    }
    return {"preprocessing": {"steps": [step]}}


def _stored_span(text: str) -> dict[str, Any]:
    return {
        "text": text,
        "start": 0,
        "end": len(text),
        "span_in_full_paper": {"start": 5, "end": 6},
    }


def test_the_scripts_apply_the_detrend_rule_to_a_supplied_order() -> None:
    """term_audit.iter_values gives the rule's quote to every extracted value, an order the
    checking pass supplied included. A supplied term that resolved to nothing gets none (the next
    test), and neither does a part of a varied value."""
    span = _stored_span("Linear and quadratic trends were removed.")
    term = {"verbatim": "linear", "resolved": "linear", "resolution": "resolved"}
    supplied = {"status": "EXTRACTED", "value": term, "spans": [span], "checker_supplied": True}
    (value,) = ta.iter_values(_detrend_record(supplied), "paper_a")
    assert value.rule_quote == span["text"] and value.now == (("quadratic", "resolved"),)
    part = {"value": term, "spans": [span], "applies_to": "rest"}
    (varied,) = ta.iter_values(_detrend_record({"status": "VARIED", "variants": [part]}), "paper_a")
    assert varied.rule_quote is None and varied.now == (("linear", "resolved"),)


def test_the_scripts_leave_a_supplied_term_that_resolved_to_nothing() -> None:
    """promote() only raises an order. A supplied term that resolved to nothing is not given the
    order its sentence names, and the two scripts read such a record the same way; the same term
    from the coverage call takes the order, as it always did."""
    from reresolve_terms import reresolve_record

    span = _stored_span("Linear detrending was omitted.")
    term = {"verbatim": "omitted", "resolved": None, "resolution": "unrecognized"}
    supplied = {"status": "EXTRACTED", "value": term, "spans": [span], "checker_supplied": True}
    (value,) = ta.iter_values(_detrend_record(supplied), "paper_a")
    assert value.now == ((None, "unrecognized"),) and value.rule_quote is None
    assert sum(reresolve_record(_detrend_record(supplied)).values()) == 0
    extracted = {"status": "EXTRACTED", "value": dict(term), "spans": [span]}
    (own,) = ta.iter_values(_detrend_record(extracted), "paper_a")
    assert own.now == (("linear", "resolved"),) and own.rule_quote == span["text"]
    assert reresolve_record(_detrend_record(extracted))["nuisance_regression.detrend"] == 1


def test_a_supplied_order_is_raised_through_the_whole_extraction() -> None:
    """End to end: ``extract`` with the checking pass. The rule's diagnostic for a supplied value
    reaches the list ``extract`` returns, which the batch writes into the record."""
    sentence = "Linear and quadratic trends were removed from each run."
    verdict = FieldVerdict(
        field="nuisance_regression.detrend",
        verdict="missed",
        relied_on=sentence,
        better_value="linear",
    )
    checked: list[Any] = []
    prep, diagnostics, _ = ex.extract(
        ParsedPaper(text=sentence, source="test", parser="manual"),
        "m",
        client=stub_client(
            _shared_call_all_missing(), verifier=VerifierExtraction(fields=[verdict])
        ),
        verifier_out=checked,
    )
    detrend = next(s for s in prep.steps if s.kind == "nuisance_regression").detrend.extraction
    assert detrend.status == "EXTRACTED" and detrend.checker_supplied is True
    assert (detrend.value.verbatim, detrend.value.resolved) == ("linear", "quadratic")
    moved = "detrend_highest_order_named:linear->quadratic"
    assert [d.failure_reason for d in diagnostics if d.field == DETREND] == [moved]
    (entry,) = checked[0]["supplied"]
    assert (entry["outcome"], entry["rule"]) == ("filled", moved)


def test_every_member_a_rule_names_is_a_member_of_its_field() -> None:
    """D2c adds no member. That no schema and no prompt changed is shown by the gates of the
    design note (the request schemas and the prompt hashes), not by this test."""
    for dotted, rules in TERM_RULES.items():
        members = set(_FIELD[dotted].members)
        named = {*rules.require_all, *rules.block, *rules.named_by, *rules.exact_overrides.values()}
        assert named <= members, (dotted, named - members)
    assert set(typing.get_args(_SPEC[COMPCOR].literal_type)) == {"a", "t"}
