"""B11 (DESIGN_prompt_schema_2026-11; built 2026-11-25): a term for which the vocabulary holds no
member says so in the report and the pseudo-code, and nowhere in what the checking pass is sent.
Offline: the stub client answers the calls."""

from __future__ import annotations

from typing import Any

from conftest import stub_client
from extractor_mvp.coverage_extractor import SpatialExtraction, TemporalVolumeExtraction
from extractor_mvp.extraction_result import FieldExtractionResult, StepFieldResult, VariantResult
from extractor_mvp.extractor import MotionMethodExtraction, PreprocessingExtraction, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pseudocode import render_pseudocode
from extractor_mvp.render import NOT_IN_VOCABULARY, to_report, unmatched_terms
from extractor_mvp.verifier import compact_draft

S_FILTER = "The time series were band-pass filtered with a Gaussian filter."
S_YOUNG = "In young adults, brains were extracted with optiBET."
S_OLD = "In older adults, brains were extracted with BET."
S_DIST = "Distortion was corrected with topup and with Smith's method."
S_COREG = "Images were coregistered with FLIRT and bbregister."
S_SPACE = "Images were normalized to MNI space."
S_MOTION = "Images were realigned and unwarped."
S_Z = "The time series were z-scored."
TEXT = " ".join([S_MOTION, S_FILTER, S_YOUNG, S_OLD, S_DIST, S_COREG, S_SPACE, S_Z])


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _got(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _prep() -> Any:
    shared = PreprocessingExtraction(
        target_space=_got("MNI", S_SPACE),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
        temporal_standardization_method=_got("z-scored", S_Z),
    )
    temporal = TemporalVolumeExtraction(
        filter_performed=_got("yes", S_FILTER),
        filter_pass_type=_got("band-pass", S_FILTER),
        filter_type=_got("Gaussian filter", S_FILTER),
    )
    spatial = SpatialExtraction(
        brain_extraction_performed=_got("yes", S_YOUNG),
        # one part names a tool the vocabulary lacks, the other a member
        brain_extraction_method=StepFieldResult(
            status="varied",
            variants=[
                VariantResult(value="optiBET", verbatim_quote=S_YOUNG, applies_to="young adults"),
                VariantResult(value="BET", verbatim_quote=S_OLD, applies_to="older adults"),
            ],
        ),
        distortion_performed=_got("yes", S_DIST),
        distortion_tool=_got("topup, Smith's method", S_DIST),  # a list, one item unmatched
        coregistration_performed=_got("yes", S_COREG),
        coregistration_method=_got("FLIRT and bbregister", S_COREG),  # two members: ambiguous
    )
    motion = MotionMethodExtraction(
        motion_correction_method=_got("realigned and unwarped", S_MOTION),
        motion_correction_binding="described_only",
    )
    prep, _, _ = extract(
        ParsedPaper(text=TEXT, source="t", parser="manual"),
        "m",
        client=stub_client(shared, temporal=temporal, spatial=spatial, motion=motion),
    )
    return prep


def _step(prep: Any, kind: str) -> Any:
    return next(s for s in prep.steps if s.kind == kind)


def test_the_fixture_holds_one_term_of_each_kind() -> None:
    prep = _prep()
    filt = _step(prep, "temporal_filtering")
    assert filt.filter_type.extraction.value.resolution == "unrecognized"
    assert filt.pass_type.extraction.value.resolved == "band_pass"
    tools = _step(prep, "distortion_correction").tool.extraction.value
    assert [(t.verbatim, t.resolved) for t in tools] == [
        ("topup", "topup"),
        ("Smith's method", None),
    ]
    coreg = _step(prep, "coregistration").method.extraction.value
    assert (coreg.resolved, coreg.resolution) == (None, "unrecognized")  # the spec folds ambiguous
    space = _step(prep, "spatial_normalization").target_space.extraction.value
    assert (space.resolved, space.resolution) == (None, "underspecified")
    brain = _step(prep, "brain_extraction").method.extraction
    assert brain.status == "VARIED"
    assert [v.value.resolved for v in brain.variants] == [None, "bet"]
    motion = _step(prep, "motion_correction").method.extraction.value
    assert (motion.verbatim, motion.resolved) == ("realigned and unwarped", None)
    zscore = _step(prep, "temporal_standardization").method.extraction.value
    assert (zscore.verbatim, zscore.resolved) == ("z-scored", None)
    # the list splitter and the list resolution are the ones _process_field calls
    assert unmatched_terms("distortion_correction.tool", tools) == ["Smith's method"]
    assert unmatched_terms("coregistration.method", coreg) == []  # ambiguous: both are members
    assert unmatched_terms("spatial_normalization.target_space", space) == []  # a family term
    assert unmatched_terms("motion_correction.method", motion) == []  # no table: the phrase field
    assert unmatched_terms("temporal_standardization.method", zscore) == []  # no table
    assert unmatched_terms("spatial_smoothing.fwhm_mm", 3.0) == []


def test_the_report_says_which_terms_are_not_in_the_vocabulary() -> None:
    out = to_report(_prep(), source="t")
    assert f'- filter_type = "Gaussian filter" ({NOT_IN_VOCABULARY})   [from paper]' in out
    # a list marks the item, not the list
    assert f'- tool = topup, "Smith\'s method" ({NOT_IN_VOCABULARY})   [from paper]' in out
    # a part of a varied field is marked on its own
    assert f'young adults: "optiBET" ({NOT_IN_VOCABULARY})' in out
    assert 'older adults: bet (paper: "BET")' in out
    assert out.count(NOT_IN_VOCABULARY) >= 3
    # controls: these read as they did before B11
    assert '- pass_type = band_pass (paper: "band-pass")   [from paper]' in out
    assert '- target_space = "MNI"   [from paper]' in out  # a family term is in the vocabulary
    assert '"FLIRT and bbregister"   [from paper]' in out  # two members fit: not "not in ..."
    assert f'"FLIRT and bbregister" ({NOT_IN_VOCABULARY})' not in out
    assert f'"realigned and unwarped" ({NOT_IN_VOCABULARY})' not in out  # the motion phrase
    assert f'"z-scored" ({NOT_IN_VOCABULARY})' not in out  # a field with no alias table
    assert f'"MNI" ({NOT_IN_VOCABULARY})' not in out


def test_the_pseudo_code_marks_the_same_terms() -> None:
    code = render_pseudocode({"preprocessing": _prep().model_dump(mode="json")})
    assert code is not None
    assert f'filter_type="Gaussian filter" [E: {NOT_IN_VOCABULARY}]' in code
    # a list names the unmatched item, quoted as the argument quotes it (the apostrophe kept)
    assert f'tool="topup, Smith\'s method" [E: "Smith\'s method" {NOT_IN_VOCABULARY}]' in code
    # the record has two parts, so each part's block shows its own value
    assert f'brain_extraction(method="optiBET" [E: {NOT_IN_VOCABULARY}]' in code
    assert 'brain_extraction(method="BET" [E]' in code
    # controls
    assert 'pass_type="band-pass" [E]' in code
    assert 'target_space="MNI" [E]' in code
    assert 'method="FLIRT and bbregister" [E]' in code
    assert 'motion_correction(method="realigned and unwarped" [E]' in code
    assert 'temporal_standardization(method="z-scored" [E]' in code


def test_the_checking_pass_is_sent_no_note() -> None:
    draft = compact_draft(_prep())
    assert NOT_IN_VOCABULARY not in draft
    # the same values are in the draft, unmarked: an extracted term, a list, a part of a varied field
    assert 'temporal_filtering.filter_type | extracted | "Gaussian filter" | quote:' in draft
    assert 'distortion_correction.tool | extracted | topup, "Smith\'s method" | quote:' in draft
    assert 'brain_extraction.method[young adults] | extracted | "optiBET" | quote:' in draft


def _unresolved(words: str) -> Any:
    from fmri_repro.spec.preprocessing import SpecifiedTerm

    return SpecifiedTerm(verbatim=words, resolved=None, resolution="unrecognized")


def test_only_a_term_that_holds_no_name_of_the_vocabulary_is_marked() -> None:
    """The note is a claim about the vocabulary, so it is made only where no part of the words is
    a name the vocabulary knows."""
    from extractor_mvp.render import _fmt_row_value, _ValueOnly

    term = _unresolved("optiBET")
    assert _fmt_row_value(_ValueOnly("brain_extraction.method", term)) == (
        f'"optiBET" ({NOT_IN_VOCABULARY})'
    )
    # without the field's path nothing is marked: this is how the checking pass's draft is built
    assert _fmt_row_value(_ValueOnly("brain_extraction.method", term), False) == '"optiBET"'
    for path, words in (
        # an alias that a rule blocks: the field may hold the member the words mean
        ("spatial_smoothing.space", "native cortical surface"),
        ("distortion_correction.method", "fieldmap-less"),
        # a member's own token in another case
        ("nuisance_regression.motion_expansion", "Friston24"),
        # an SPM release inside a longer wording
        ("nuisance_regression.method", "CONN toolbox (SPM12)"),
        # a record an older resolver left unresolved, whose words today's tables resolve
        ("slice_time_correction.reference", "middle slice"),
    ):
        assert _fmt_row_value(_ValueOnly(path, _unresolved(words))) == f'"{words}"', words


def test_an_inferred_value_is_never_marked() -> None:
    """The note is for a term read in the paper. The pseudo-code marks [E] arguments only, and
    the report follows the same rule."""
    from types import SimpleNamespace

    from extractor_mvp.pseudocode import _row_arg
    from extractor_mvp.render import (
        EXTRACTED,
        INFERRED_DEFAULT,
        _fmt_field_text,
        _fmt_row_value,
    )

    def row(state: str) -> Any:
        return SimpleNamespace(
            path="brain_extraction.method",
            value=_unresolved("optiBET"),
            state=state,
            span_text="brains were extracted with optiBET",
            span_recovered=False,
            checker_supplied=False,
            basis_type="knowledge_base",
            basis=None,
            confidence="low",
            variants=None,
        )

    assert _fmt_row_value(row(EXTRACTED)) == f'"optiBET" ({NOT_IN_VOCABULARY})'  # control
    assert _fmt_row_value(row(INFERRED_DEFAULT)) == '"optiBET"'
    assert NOT_IN_VOCABULARY not in _fmt_field_text(row(INFERRED_DEFAULT))
    assert NOT_IN_VOCABULARY in _fmt_field_text(row(EXTRACTED))  # control
    inferred = _row_arg(row(INFERRED_DEFAULT), "method", {}, {})
    extracted = _row_arg(row(EXTRACTED), "method", {}, {})
    assert inferred is not None and NOT_IN_VOCABULARY not in inferred.text()
    assert extracted is not None and NOT_IN_VOCABULARY in extracted.text()  # control


def test_the_part_tables_of_the_pseudo_code_carry_the_note() -> None:
    """Five or more parts are tabulated per part (Stage 2b); the unmatched cell says so."""
    tools = ["optiBET", "BET", "BET", "BET", "BET"]
    sentences = [
        f"In cohort {i}, brains were extracted with {tool}."
        for i, tool in enumerate(tools, start=1)
    ]
    variants = [
        VariantResult(value=tool, verbatim_quote=sentence, applies_to=f"cohort {i}")
        for i, (tool, sentence) in enumerate(zip(tools, sentences, strict=True), start=1)
    ]
    shared = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    spatial = SpatialExtraction(
        brain_extraction_performed=_got("yes", sentences[0]),
        brain_extraction_method=StepFieldResult(status="varied", variants=variants),
    )
    prep, _, _ = extract(
        ParsedPaper(text=" ".join(sentences), source="t", parser="manual"),
        "m",
        client=stub_client(shared, spatial=spatial),
    )
    code = render_pseudocode({"preprocessing": prep.model_dump(mode="json")})
    assert code is not None
    assert f'# | cohort 1 | "optiBET" ({NOT_IN_VOCABULARY}) |' in code
    assert '# | cohort 2 | "BET" |' in code  # control
    # the same five parts in the draft the checking pass is sent: no note
    assert NOT_IN_VOCABULARY not in compact_draft(prep)


def test_a_list_cell_of_a_part_table_names_the_unmatched_item() -> None:
    """A cell that holds a list marks the item the vocabulary lacks, not the whole cell."""
    tools = ["topup, Smith's method", "topup", "topup", "FUGUE, Q|warp", "topup"]
    sentences = [
        f"In cohort {i}, distortion was corrected with {tool}."
        for i, tool in enumerate(tools, start=1)
    ]
    variants = [
        VariantResult(value=tool, verbatim_quote=sentence, applies_to=f"cohort {i}")
        for i, (tool, sentence) in enumerate(zip(tools, sentences, strict=True), start=1)
    ]
    shared = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    spatial = SpatialExtraction(
        distortion_performed=_got("yes", sentences[0]),
        distortion_tool=StepFieldResult(status="varied", variants=variants),
    )
    prep, _, _ = extract(
        ParsedPaper(text=" ".join(sentences), source="t", parser="manual"),
        "m",
        client=stub_client(shared, spatial=spatial),
    )
    code = render_pseudocode({"preprocessing": prep.model_dump(mode="json")})
    assert code is not None
    cell = f'"topup, Smith\'s method" ("Smith\'s method" {NOT_IN_VOCABULARY})'
    assert f"# | cohort 1 | {cell} |" in code
    assert '# | cohort 2 | "topup" |' in code  # control
    # a "|" in the paper's words would add a column: replaced in the value and in the note
    assert f'# | cohort 4 | "FUGUE, Q/warp" ("Q/warp" {NOT_IN_VOCABULARY}) |' in code
    row = next(ln for ln in code.splitlines() if ln.startswith("# | cohort 4 |"))
    assert row.count("|") == 3


def test_a_one_block_varied_argument_names_the_unmatched_part() -> None:
    """pseudocode._unmatched_detail over the values of several parts: the note names the term."""
    from fmri_repro.spec.preprocessing import SpecifiedTerm

    from extractor_mvp.pseudocode import _row_arg, _unmatched_detail
    from extractor_mvp.render import flatten

    # the varied row itself, rendered as one argument
    row = next(r for r in flatten(_prep()) if r.path == "brain_extraction.method")
    arg = _row_arg(row, "method", {}, {})
    assert arg is not None and arg.value.startswith("varies(young adults:")
    assert arg.text().endswith(f'[E: "optiBET" {NOT_IN_VOCABULARY}]')

    no = SpecifiedTerm(verbatim="optiBET", resolved=None, resolution="unrecognized")
    yes = SpecifiedTerm(verbatim="BET", resolved="bet", resolution="resolved")
    path = "brain_extraction.method"
    assert _unmatched_detail(path, [no, yes]) == f'"optiBET" {NOT_IN_VOCABULARY}'
    assert _unmatched_detail(path, [no]) == NOT_IN_VOCABULARY
    assert _unmatched_detail(path, [no, no]) == f'"optiBET" {NOT_IN_VOCABULARY}'  # named once
    assert _unmatched_detail(path, [yes]) is None
    # a bracket in the paper's words must not close the note's own bracket
    odd = SpecifiedTerm(verbatim="3dQwarp [-plusminus]", resolved=None, resolution="unrecognized")
    assert _unmatched_detail("distortion_correction.tool", [[yes, odd]]) == (
        f'"3dQwarp (-plusminus)" {NOT_IN_VOCABULARY}'
    )
