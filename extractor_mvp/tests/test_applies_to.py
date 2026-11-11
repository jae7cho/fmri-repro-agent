"""DESIGN_applies_to.md Stage 1 (2026-11-11): forks A1 (the Varied arm), B1 with the normalized
same-string rule, C2 (one compared-models entry), D1 (weakest variant), E2 (no alias fallback), F1
(the checking pass judges applies_to as part of the value). Offline: the stub serves every call. The
methods text is written for these tests and quotes no paper."""

from __future__ import annotations

from typing import Any

import pytest
from fmri_repro.spec.preprocessing import Preprocessing
from fmri_repro.spec.provenance import (
    COMPARED_MODELS,
    NotApplicable,
    ProvenancedField,
    Span,
    Variant,
    Varied,
    normalize_applies_to,
)
from pydantic import ValidationError

from conftest import stub_client
from extractor_mvp import render
from extractor_mvp.applies_to_scoring import (
    LabelVariant,
    PredictedVariant,
    is_all,
    score_field,
)
from extractor_mvp.coverage_extractor import (
    SpatialExtraction,
    StepOrderPartResult,
    TemporalVolumeExtraction,
)
from extractor_mvp.extraction_result import FieldExtractionResult, StepFieldResult
from extractor_mvp.extractor import PreprocessingExtraction, _process_field, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pseudocode import render_pseudocode
from extractor_mvp.verifier import (
    VERIFIER_PROMPT,
    FieldVerdict,
    VerifierExtraction,
    compact_draft,
)

S_AMP = "Amplitude maps were computed from data smoothed with a 6 mm FWHM Gaussian kernel."
S_CONN = "Connectivity maps were computed from data that were not smoothed."
S_ORDER_A = "In the first analysis, nuisance regression was followed by temporal filtering."
S_ORDER_B = "In the second analysis, temporal filtering came before nuisance regression."
S_COMPARE = "We compared five denoising models applied to the same data."
TEXT = " ".join((S_AMP, S_CONN, S_ORDER_A, S_ORDER_B, S_COMPARE))


def _v(value: str | None, quote: str, applies_to: str, at_quote: str | None = None) -> dict:
    return {
        "value": value,
        "verbatim_quote": quote,
        "applies_to": applies_to,
        "applies_to_quote": at_quote,
    }


def _varied(*variants: dict) -> StepFieldResult:
    return StepFieldResult(status="varied", variants=list(variants))


def _ex(value: str, quote: str) -> StepFieldResult:
    return StepFieldResult(status="extracted", value=value, verbatim_quote=quote)


def _shared() -> PreprocessingExtraction:
    m = FieldExtractionResult(status="missing")
    return PreprocessingExtraction(
        target_space=m,
        resolution_mm=m,
        surface_registration=m,
        target_surface=m,
        intensity_convention=m,
        intensity_value=m,
    )


def _smoothing_varied() -> dict[str, Any]:
    return {
        "smoothing_performed": _varied(
            _v("yes", S_AMP, "amplitude maps"), _v("no", S_CONN, "connectivity maps")
        ),
        # a different case for the same part: one part under the same-string rule
        "smoothing_fwhm_mm": _varied(_v("6", S_AMP, "Amplitude maps")),
        "smoothing_kernel_type": _ex("gaussian", S_AMP),
    }


def _run(
    spatial: dict[str, Any] | None = None,
    temporal: dict[str, Any] | None = None,
    verifier: VerifierExtraction | None = None,
) -> tuple[Preprocessing, dict[str, Any], str]:
    out: list[Any] = []
    prep, _, _ = extract(
        ParsedPaper(text=TEXT, source="t", parser="manual"),
        "m",
        client=stub_client(
            _shared(),
            spatial=SpatialExtraction(**(spatial or {})),
            temporal=TemporalVolumeExtraction(**(temporal or {})),
            verifier=verifier,
        ),
        verifier_out=out,
    )
    record = out[0]
    report = render.to_report(
        prep, source="t", verifier=record, multiple_pipelines=record.get("multiple_pipelines")
    )
    return prep, record, report


def _step(prep: Preprocessing, kind: str) -> Any:
    return next(s for s in prep.steps if s.kind == kind)


# --- the schema (fork A1) ------------------------------------------------------------------------

_SP = Span(start=0, end=4, text="text")


def _variant(value: Any, applies_to: str) -> Variant[Any]:
    return Variant[Any](value=value, spans=[_SP], applies_to=applies_to, confidence=0.8)


def test_the_same_string_rule_normalizes_case_dashes_ampersand_and_a_leading_the() -> None:
    assert normalize_applies_to("The Parts I\u2013II") == normalize_applies_to("parts i-ii")
    assert normalize_applies_to("ALFF & fALFF") == normalize_applies_to("alff and falff.")
    assert normalize_applies_to("task-fMRI") != normalize_applies_to("rest-fMRI")


def test_a_varied_arm_never_holds_all_a_repeated_part_or_a_stray_valueless_entry() -> None:
    Varied[Any](variants=[_variant(6.0, "ALFF")])
    with pytest.raises(ValidationError, match="all"):
        Varied[Any](variants=[_variant(6.0, "All")])
    with pytest.raises(ValidationError, match="share"):
        Varied[Any](variants=[_variant(6.0, "Part III"), _variant(4.0, "part  III")])
    with pytest.raises(ValidationError, match="value-less variant"):
        Varied[Any](variants=[_variant(None, "ReHo")])
    with pytest.raises(ValidationError, match="value-less variant"):
        Varied[Any](variants=[_variant(None, COMPARED_MODELS), _variant(6.0, "ALFF")])
    Varied[Any](variants=[_variant(None, "Varied across compared models")])


def test_a_varied_field_takes_no_inference() -> None:
    from fmri_repro.spec.provenance import FieldConventionBasis, InferredDefault

    ok = ProvenancedField[Any](
        field_id="fwhm_mm",
        extraction=Varied[Any](variants=[_variant(6.0, "ALFF")]),
        inference=NotApplicable(),
    )
    with pytest.raises(ValidationError, match="VARIED requires inference=NOT_APPLICABLE"):
        ProvenancedField[Any](
            field_id="fwhm_mm",
            extraction=ok.extraction,
            inference=InferredDefault[Any](
                value=8.0,
                basis=FieldConventionBasis(source="x"),
                confidence=0.3,
                alternative_inferences=[],
            ),
        )


def test_the_varied_status_is_only_on_the_three_targeted_calls() -> None:
    """Every other call keeps FieldExtractionResult, so its schema is unchanged."""
    assert "varied" not in str(FieldExtractionResult.model_json_schema())
    assert "varied" in str(SpatialExtraction.model_json_schema())
    assert "varied" in str(TemporalVolumeExtraction.model_json_schema())
    assert "varied" in str(PreprocessingExtraction.model_json_schema()["$defs"]["StepFieldResult"])
    bp = PreprocessingExtraction.model_fields["base_pipeline_name"].annotation
    assert bp is FieldExtractionResult
    assert "multiple_pipelines" not in VerifierExtraction.model_fields


# --- processing: every variant through the one span path -------------------------------------------


def _process(fe: StepFieldResult, dotted: str = "spatial_smoothing.fwhm_mm") -> Any:
    return _process_field(
        dotted.split(".")[1], dotted, fe, None, float, TEXT, None, False, "number", None
    )


def test_each_variant_is_quote_checked_and_one_that_fails_is_dropped_and_counted() -> None:
    pf, diag, _ = _process(
        _varied(
            _v("6", S_AMP, "Amplitude maps"),
            _v("4", "A sentence the paper never wrote.", "connectivity maps"),
        )
    )
    assert isinstance(pf.extraction, Varied)
    assert [(v.applies_to, v.value) for v in pf.extraction.variants] == [("Amplitude maps", 6.0)]
    assert pf.extraction.variants_dropped == 1
    assert diag is not None and diag.failure_reason.startswith("extraction_quote_unresolved")
    # a value its sentence does not state is dropped the same way
    pf, diag, _ = _process(_varied(_v("6", S_AMP, "Amplitude maps"), _v("8", S_AMP, "x maps")))
    assert pf.extraction.variants_dropped == 1
    assert diag is not None and diag.failure_reason == "value_unsupported_by_quote"


def test_one_surviving_variant_stays_varied_and_none_surviving_is_a_gap() -> None:
    pf, _, _ = _process(_varied(_v("6", S_AMP, "Amplitude maps")))
    assert pf.extraction.status == "VARIED"  # never collapsed to an "all" value
    pf, _, _ = _process(_varied(_v("4", "Not in the text.", "connectivity maps")))
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason.startswith("extraction_quote_unresolved")
    pf, _, _ = _process(_varied(_v("6", S_AMP, "all")))
    assert pf.inference.reason == "varied_no_variant_checked"


def test_an_unfound_part_is_kept_unverified_and_its_own_sentence_can_verify_it() -> None:
    pf, diag, _ = _process(_varied(_v("6", S_AMP, "the ALFF maps")))
    (v,) = pf.extraction.variants
    assert v.applies_to == "the ALFF maps" and v.applies_to_verified is False
    assert diag is not None and diag.failure_reason == "applies_to_unverified"
    # the sentence tying the value to the part, resolved, verifies it
    pf, diag, _ = _process(_varied(_v("6", S_AMP, "connectivity maps", at_quote=S_CONN)))
    (v,) = pf.extraction.variants
    assert v.applies_to_verified is True and v.applies_to_spans[0].text == S_CONN
    assert diag is None


def test_all_and_a_repeated_part_are_dropped_with_their_reasons() -> None:
    pf, diag, _ = _process(
        _varied(
            _v("6", S_AMP, "Amplitude maps"),
            _v("6", S_AMP, "amplitude  maps"),
            _v("6", S_AMP, "ALL"),
        )
    )
    assert len(pf.extraction.variants) == 1 and pf.extraction.variants_dropped == 2
    assert diag is not None and diag.failure_reason == "varied_applies_to_repeated"


def test_fork_c2_one_compared_models_entry_with_the_sentence_and_no_value() -> None:
    pf, diag, _ = _process(_varied(_v(None, S_COMPARE, "varied across compared models")))
    (v,) = pf.extraction.variants
    assert v.value is None and v.applies_to == COMPARED_MODELS and v.spans[0].text == S_COMPARE
    assert diag is None
    # a value-less entry under any other label, or beside another variant, is dropped
    pf, diag, _ = _process(_varied(_v(None, S_CONN, "connectivity maps")))
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    pf, _, _ = _process(
        _varied(_v(None, S_COMPARE, COMPARED_MODELS), _v("6", S_AMP, "Amplitude maps"))
    )
    assert [v.applies_to for v in pf.extraction.variants] == ["Amplitude maps"]


# --- the report (§4) -----------------------------------------------------------------------------


def test_variant_lines_the_values_differ_header_and_not_performed_parts() -> None:
    prep, record, report = _run(spatial=_smoothing_varied())
    sm = _step(prep, "spatial_smoothing")
    assert sm.performed.extraction.status == "VARIED" and sm.fwhm_mm.extraction.status == "VARIED"
    assert record["multiple_pipelines"] is None
    # one spelling per part under the same-string rule; the fields that differ
    assert (
        "> Values differ by: amplitude maps, connectivity maps "
        "(spatial_smoothing.performed, spatial_smoothing.fwhm_mm)" in report
    )
    assert "More than one preprocessing variant is described" not in report
    lines = report.splitlines()
    i = lines.index("- fwhm_mm: differs by what it applies to")
    assert lines[i + 1].startswith("    - Amplitude maps: 6.0   [from paper]  «Amplitude maps")
    # the step is stated as not performed for the other part, so the parameter says so
    assert lines[i + 2].startswith("    - connectivity maps: not performed   (the step is stated")
    j = lines.index("- performed: differs by what it applies to")
    assert lines[j + 2].startswith("    - connectivity maps: not performed   [from paper]")


def test_completeness_counts_a_varied_field_once_under_its_weakest_variant() -> None:
    _, _, verified = _run(spatial=_smoothing_varied())
    spatial = _smoothing_varied()
    spatial["smoothing_fwhm_mm"] = _varied(_v("6", S_AMP, "the ALFF maps"))  # part not in the text
    prep, _, unverified = _run(spatial=spatial)

    def header(report: str) -> str:
        return next(ln for ln in report.splitlines() if ln.startswith("Completeness:"))

    def n(report: str, label: str) -> int:
        segs = header(report).removeprefix("Completeness: ").split(" · ")
        seg = next((s for s in segs if s.endswith(label)), "0 x")
        return int(seg.split()[0])

    assert n(verified, "specified in source") == n(unverified, "specified in source") + 1
    assert n(unverified, "not covered by extractor") == n(verified, "not covered by extractor") + 1
    assert "(what it applies to was not found in the text, unverified)" in unverified
    # D1 on the COBIDAS row: performed still verified, so the row is reported
    rows = render.flatten(prep)
    fwhm = next(r for r in rows if r.path == "spatial_smoothing.fwhm_mm")
    assert fwhm.coverage_status == "MISSING_FROM_PAPER"
    assert fwhm.left_missing_reason == "applies_to_unverified"


def test_a_row_addressed_only_by_an_unverified_variant_is_unverifiable() -> None:
    from extractor_mvp.cobidas import assess_coverage, row_state

    spatial = {"smoothing_fwhm_mm": _varied(_v("6", S_AMP, "the ALFF maps"))}
    prep, _, _ = _run(spatial=spatial)
    rows = render.flatten(prep)
    rc = next(c for c in assess_coverage(rows, None) if c.row.row_id == "spatial_smoothing")
    assert row_state(rc, rows) == "unverifiable"
    # positive control: the same field, verified, reports the row
    prep, _, _ = _run(spatial={"smoothing_fwhm_mm": _varied(_v("6", S_AMP, "Amplitude maps"))})
    rows = render.flatten(prep)
    rc = next(c for c in assess_coverage(rows, None) if c.row.row_id == "spatial_smoothing")
    assert row_state(rc, rows) == "reported"


def test_c2_renders_one_line_and_counts_in_its_own_bucket() -> None:
    spatial = {"smoothing_fwhm_mm": _varied(_v(None, S_COMPARE, COMPARED_MODELS))}
    _, _, report = _run(spatial=spatial)
    assert (
        "- fwhm_mm: varies across the models the paper compares; no single value   [from paper]"
        in report
    )
    assert "1 varied across compared models" in report
    assert "> Values differ by: varied across compared models (spatial_smoothing.fwhm_mm)" in report


def test_a_record_written_before_keeps_its_stored_warning_line() -> None:
    """§4: a stored record carries no applies_to and keeps its multiple_pipelines answer."""
    prep, _, _ = _run()
    stored = {
        "V": {
            "multiple_pipelines": {
                "extraction": {"status": "EXTRACTED", "value": True, "spans": [{"text": S_CONN}]}
            },
            "pipeline_variant_count": {"extraction": {"status": "MISSING_FROM_PAPER"}},
        }
    }
    report = render.to_report(prep, source="t", multiple_pipelines=stored)
    assert "> ⚠ More than one preprocessing variant is described — checking pass: yes" in report
    assert "Values differ by" not in report


def test_the_order_stated_per_part() -> None:
    temporal = {
        "step_order_parts": [
            StepOrderPartResult(
                kinds=["nuisance_regression", "temporal_filtering"],
                verbatim_quotes=[S_ORDER_A],
                applies_to="first analysis",
            ),
            StepOrderPartResult(
                kinds=["temporal_filtering", "nuisance_regression"],
                verbatim_quotes=[S_ORDER_B],
                applies_to="the 2nd analysis",  # not the paper's words
            ),
            StepOrderPartResult(
                kinds=["temporal_filtering", "despike"],
                verbatim_quotes=["A sentence the paper never wrote."],
                applies_to="third",
            ),
        ]
    }
    prep, _, report = _run(temporal=temporal)
    assert prep.step_order_source == "by_part"
    assert [(p.applies_to, p.applies_to_verified) for p in prep.step_order_parts or []] == [
        ("first analysis", True),
        ("the 2nd analysis", False),
    ]
    assert "## Preprocessing steps (template order — the paper states a different order" in report
    assert (
        "Order stated in: first analysis: nuisance_regression → temporal_filtering  «In the first"
        in report
    )
    assert "Values differ by: first analysis, the 2nd analysis (step order)" in report
    draft = compact_draft(prep)
    assert (
        "step_order[first analysis] | extracted | nuisance_regression, temporal_filtering" in draft
    )
    assert "step_order | by_part" not in draft


def test_a_stated_order_that_holds_throughout_is_unchanged() -> None:
    from extractor_mvp.coverage_extractor import StepOrderResult

    temporal = {
        "step_order": StepOrderResult(
            kinds=["nuisance_regression", "temporal_filtering"], verbatim_quotes=[S_ORDER_A]
        )
    }
    prep, _, _ = _run(temporal=temporal)
    assert prep.step_order_source in ("paper", "partial") and prep.step_order_parts is None


# --- the checking pass (fork F1) -----------------------------------------------------------------


def test_the_draft_has_one_line_per_part_and_a_verdict_lands_on_its_variant() -> None:
    prep, _, _ = _run(spatial=_smoothing_varied())
    draft = compact_draft(prep)
    assert "spatial_smoothing.fwhm_mm[Amplitude maps] | extracted | 6.0 | quote:" in draft
    assert "spatial_smoothing.performed[connectivity maps] | extracted | not performed" in draft
    verdicts = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.fwhm_mm[Amplitude maps]",
                verdict="wrong",
                reason="the kernel is for another part",
                relied_on=S_AMP,
            ),
            FieldVerdict(
                field="spatial_smoothing.performed[amplitude maps]",
                verdict="supported",
                relied_on=S_AMP,
            ),
        ]
    )
    _, record, report = _run(spatial=_smoothing_varied(), verifier=verdicts)
    assert set(record["fields"]) == {
        "spatial_smoothing.fwhm_mm[Amplitude maps]",
        "spatial_smoothing.performed[amplitude maps]",
    }
    lines = report.splitlines()
    wrong = next(ln for ln in lines if ln.startswith("    - ⚑ Amplitude maps: 6.0   [from paper]"))
    assert "— checking pass: WRONG — the kernel is for another part" in wrong
    ok = next(ln for ln in lines if ln.startswith("    - amplitude maps: performed   [from paper]"))
    assert ok.endswith("[check: supported]")
    # the other part carries no verdict of its own
    other = next(
        ln for ln in lines if ln.startswith("    - connectivity maps: not performed   [fr")
    )
    assert "check" not in other


def test_the_checking_prompt_judges_the_part_and_no_longer_asks_multiple_pipelines() -> None:
    assert "A line whose field ends in `[<part>]`" in VERIFIER_PROMPT
    assert "value does not hold for the part named" in VERIFIER_PROMPT
    assert "the paper ties the value to a part of its data" in VERIFIER_PROMPT
    assert "multiple_pipelines" not in VERIFIER_PROMPT
    assert "pipeline_variant_count" not in VERIFIER_PROMPT


# --- the pseudo-code -----------------------------------------------------------------------------


def test_the_pseudocode_has_one_block_per_part() -> None:
    prep, record, _ = _run(spatial=_smoothing_varied())
    code = render_pseudocode({"preprocessing": prep.model_dump(mode="json"), "verifier": record})
    assert code is not None
    assert "# --- applies to: amplitude maps" in code
    assert "# --- applies to: connectivity maps" in code
    amp, conn = code.split("# --- applies to: connectivity maps")
    amp = amp.split("# --- applies to: amplitude maps")[1]
    assert "fwhm_mm=6 [E]" in amp and 'kernel_type="gaussian" [E]' in amp
    assert "spatial_smoothing()  [x]" in conn and "fwhm_mm" not in conn


# --- inference never writes over a varied field -------------------------------------------------


def test_the_kb_leaves_a_varied_field_alone() -> None:
    from fmri_repro.kb_client import base_pipeline as bp

    prep, _, _ = _run()
    tf = _step(prep, "temporal_filtering")
    result = type("R", (), {"value": 4, "proposed_confidence": 0.9, "source": "x"})()
    # positive control: the same call fills the field while it is missing
    assert tf.order.extraction.status == "MISSING_FROM_PAPER"
    bp._apply_param_result(prep, "temporal_filtering", "order", result, "fmriprep", "20.2.0")
    assert tf.order.inference.status == "INFERRED_DEFAULT"
    tf.order = ProvenancedField[Any](
        field_id="order",
        extraction=Varied[Any](variants=[_variant(2, "task runs"), _variant(1, "rest runs")]),
        inference=NotApplicable(),
    )
    before = tf.order
    bp._apply_param_result(prep, "temporal_filtering", "order", result, "fmriprep", "20.2.0")
    assert tf.order is before


# --- scoring (§5, forks E2) ----------------------------------------------------------------------


def _eq(a: Any, b: Any) -> bool:
    return bool(a == b)


def test_scope_classes() -> None:
    labels = [LabelVariant("ALFF", 6, S_AMP), LabelVariant("ReHo", None, S_CONN)]
    assert score_field(labels, [PredictedVariant("all", 6)], _eq).outcome == "collapsed"
    assert score_field([LabelVariant("all", 6)], [PredictedVariant("x", 6)], _eq).outcome == "split"
    assert score_field([LabelVariant("all runs", 6)], [PredictedVariant("all", 6)], _eq).correct
    assert is_all("All (Parts I\u2013III)") and not is_all("allocated")


def test_variants_match_by_quote_overlap_never_by_alias_e2() -> None:
    labels = [LabelVariant("ALFF and fALFF", 6, S_AMP), LabelVariant("ReHo", None, S_CONN)]
    preds = [
        PredictedVariant("amplitude maps", 6, (S_AMP,)),
        PredictedVariant("connectivity maps", None, (S_CONN,)),
    ]
    fs = score_field(labels, preds, _eq)
    assert fs.correct and fs.matches == [0, 1]
    # same words, no overlapping sentence: missed plus spurious, not matched (E2)
    fs = score_field(
        [LabelVariant("ReHo", None, S_CONN)], [PredictedVariant("ReHo", None, (S_AMP,))], _eq
    )
    assert fs.outcome == "wrong" and fs.label_classes == [("ReHo", "missed")]
    assert fs.spurious == ["ReHo"]
    # matched with the wrong value
    fs = score_field(labels, [PredictedVariant("a", 8, (S_AMP,)), preds[1]], _eq)
    assert fs.label_classes == [("ALFF and fALFF", "matched_wrong"), ("ReHo", "matched_correct")]
    assert not fs.correct


def test_a_resolved_citation_never_fills_a_varied_field() -> None:
    from fmri_repro.spec.provenance import InferredDefault, PriorPublicationBasis

    from extractor_mvp.extractor import _apply_resolved_citations

    prep, _, _ = _run(spatial=_smoothing_varied())
    before = _step(prep, "spatial_smoothing").fwhm_mm
    resolved = {
        "spatial_smoothing.fwhm_mm": InferredDefault[Any](
            value=8.0,
            basis=PriorPublicationBasis(citation="x"),
            confidence=0.5,
            alternative_inferences=[],
        )
    }
    after = _apply_resolved_citations(prep, resolved)
    assert _step(after, "spatial_smoothing").fwhm_mm == before


def test_the_motion_arm_infers_nothing_over_a_varied_method() -> None:
    from extractor_mvp.motion_inference import infer_motion_method

    prep, _, _ = _run()
    step = _step(prep, "motion_correction")
    step.method = ProvenancedField[Any](
        field_id="method",
        extraction=Varied[Any](variants=[_variant("mcflirt", "task runs")]),
        inference=NotApplicable(),
    )
    _, rec = infer_motion_method(prep)
    assert rec.path == "never" and rec.reason.startswith("varied")
    assert step.method.inference.status == "NOT_APPLICABLE"


# --- Stage 2b (2026-11-11, the author's items 1-4) ----------------------------------------------


def test_the_compared_phrase_in_the_value_is_normalised_to_the_null_entry() -> None:
    """power_2014 in Stage 2: the phrase came back as the value."""
    for variant in (
        _v("varied across compared models", S_COMPARE, "the regressor sets"),
        _v('"Varied across compared models."', S_COMPARE, "regressor sets"),
        _v("24P", S_COMPARE, "varied across compared models"),
    ):
        pf, diag, _ = _process(_varied(variant))
        (v,) = pf.extraction.variants
        assert v.value is None and v.applies_to == COMPARED_MODELS
        assert v.spans[0].text == S_COMPARE and diag is None


def test_described_variants_win_over_a_compared_entry_beside_them() -> None:
    pf, diag, _ = _process(
        _varied(
            _v("6", S_AMP, "Amplitude maps"),
            _v("varied across compared models", S_COMPARE, "all models"),
        )
    )
    assert [v.applies_to for v in pf.extraction.variants] == ["Amplitude maps"]
    assert pf.extraction.variants_dropped == 1
    assert (
        diag is not None
        and diag.failure_reason == "varied_compared_entry_beside_described_variants"
    )


def test_a_part_is_found_anywhere_in_the_methods_text_and_its_location_kept() -> None:
    pf, diag, _ = _process(_varied(_v("6", S_AMP, "second analysis")))
    (v,) = pf.extraction.variants
    assert v.applies_to_verified is True and diag is None
    (at,) = v.applies_to_spans
    assert at.text == "second analysis" and TEXT[at.start : at.end] == "second analysis"
    # found nowhere: still unverified, nothing located
    pf, diag, _ = _process(_varied(_v("6", S_AMP, "the ALFF maps")))
    assert pf.extraction.variants[0].applies_to_verified is False
    assert pf.extraction.variants[0].applies_to_spans == []


def test_locate_phrase() -> None:
    from extractor_mvp.quote_support import locate_phrase

    t = "Model 10 used AROMA. In Parts I\u2013II the data were filtered. Task runs were censored."
    assert locate_phrase("Model 1", t) is None  # whole words only
    assert t[slice(*locate_phrase("Model 10", t))] == "Model 10"  # type: ignore[misc]
    assert t[slice(*locate_phrase("parts i-ii", t))] == "Parts I\u2013II"  # type: ignore[misc]
    assert t[slice(*locate_phrase("task run", t))] == "Task runs"  # type: ignore[misc]


def test_a_step_order_part_is_found_anywhere_in_the_methods_text() -> None:
    temporal = {
        "step_order_parts": [
            StepOrderPartResult(
                kinds=["nuisance_regression", "temporal_filtering"],
                verbatim_quotes=[S_ORDER_A],
                applies_to="second analysis",
            )
        ]
    }
    prep, _, _ = _run(temporal=temporal)
    (part,) = prep.step_order_parts or []
    assert part.applies_to_verified is True
    assert [s.text for s in part.applies_to_spans] == ["second analysis"]


def test_the_part_rules_are_in_the_extraction_prompts_and_the_checking_pass() -> None:
    from extractor_mvp.coverage_extractor import SPATIAL_PROMPT, TEMPORAL_VOLUME_PROMPT
    from extractor_mvp.extractor import EXTRACTION_PROMPT

    for line in (
        "Preprocessing applied before a derived measure is computed (e.g. ALFF, fALFF, ReHo",
        "is preprocessing for that part of the data, not analysis",
        "A statement that a step was not applied to one part of the data is a value for that part",
    ):
        for prompt in (EXTRACTION_PROMPT, TEMPORAL_VOLUME_PROMPT, SPATIAL_PROMPT, VERIFIER_PROMPT):
            assert line in " ".join(prompt.split()), line
    compared = "describes each one, return one variant per model"
    assert compared in " ".join(SPATIAL_PROMPT.split())
    assert "WITHOUT describing them" in SPATIAL_PROMPT


def test_a_bare_citation_marker_ref_is_a_deferral_never_a_validation_failure() -> None:
    base = {
        k: {"status": "missing"}
        for k in (
            "target_space",
            "resolution_mm",
            "surface_registration",
            "target_surface",
            "intensity_convention",
            "intensity_value",
        )
    }
    got = PreprocessingExtraction.model_validate(
        {**base, "base_pipeline_ref": {"status": "extracted", "value": "(67)"}}
    )
    ref = got.base_pipeline_ref
    assert (ref.status, ref.ref_string, ref.deferral_sentence) == ("deferred", "(67)", "(67)")
    got = PreprocessingExtraction.model_validate(
        {**base, "base_pipeline_ref": {"status": "extracted", "value": "the usual pipeline"}}
    )
    assert got.base_pipeline_ref.status == "missing"
    # positive control: an extracted ref WITH a quote is untouched
    got = PreprocessingExtraction.model_validate(
        {
            **base,
            "base_pipeline_ref": {
                "status": "extracted",
                "value": "(67)",
                "verbatim_quote": "q (67)",
            },
        }
    )
    assert got.base_pipeline_ref.status == "extracted"


def test_a_marker_deferral_is_grounded_on_the_sentence_carrying_it() -> None:
    from extractor_mvp.extractor import _build_base_pipeline

    text = (
        "Imaging was at 3T. Data were preprocessed with the pipeline described in (12, 67). Then."
    )
    ref = FieldExtractionResult(status="deferred", ref_string="(67)", deferral_sentence="(67)")
    pf, record = _build_base_pipeline(FieldExtractionResult(status="missing"), ref, text)
    assert pf.extraction.status == "DEFERRED_TO_CITATION"
    (d,) = pf.extraction.deferrals
    assert (
        d.ref == "(67)"
        and d.span.text == "Data were preprocessed with the pipeline described in (12, 67)."
    )
    assert record is not None and record.deferral_sentence == d.span.text
    # a marker the text does not carry does not ground: the existing unresolved reason, no failure
    pf, _ = _build_base_pipeline(FieldExtractionResult(status="missing"), ref, "No markers here.")
    assert pf.extraction.status != "DEFERRED_TO_CITATION"


def _many_parts_record(kind: str, field: str, n: int, numeric: bool = False) -> dict[str, Any]:
    prep, _, _ = _run()
    step = _step(prep, kind)
    span = {"start": 0, "end": 4, "text": "text"}
    variants = [
        {
            "value": float(i) if numeric else f"v{i}",
            "spans": [span],
            "applies_to": f"Model {i}",
            "confidence": 0.8,
        }
        for i in range(1, n + 1)
    ]
    # the field's own class, so the value is typed as the schema types it
    pf = type(getattr(step, field)).model_validate(
        {
            "field_id": field,
            "extraction": {"status": "VARIED", "variants": variants},
            "inference": {"status": "NOT_APPLICABLE"},
        }
    )
    setattr(step, field, pf)
    return {"preprocessing": prep.model_dump(mode="json")}


def test_more_than_four_confound_parts_render_the_steps_once_and_a_table() -> None:
    code = render_pseudocode(_many_parts_record("nuisance_regression", "regressor_list", 5))
    assert code is not None
    assert "# --- applies to:" not in code
    assert "regressor_list=by_part [E]" in code
    assert "# | part | nuisance_regression.regressor_list |" in code
    assert '# | Model 5 | "v5" |' in code
    assert code.count("nuisance_regression(") == 1


def test_four_parts_or_a_non_confound_field_keep_one_block_per_part() -> None:
    code = render_pseudocode(_many_parts_record("nuisance_regression", "regressor_list", 4))
    assert code is not None and code.count("# --- applies to: Model") == 4 and "by_part" not in code
    code = render_pseudocode(_many_parts_record("spatial_smoothing", "fwhm_mm", 6, numeric=True))
    assert code is not None and code.count("# --- applies to: Model") == 6 and "by_part" not in code


def test_variant_spans_get_full_paper_offsets() -> None:
    from extractor_mvp.batch import _translate_spans

    prep, _, _ = _run(spatial=_smoothing_varied())
    dump = prep.model_dump(mode="json")
    _translate_spans(dump, 1000)
    step = next(s for s in dump["steps"] if s["kind"] == "spatial_smoothing")
    for v in step["fwhm_mm"]["extraction"]["variants"]:
        sp = v["spans"][0]
        assert sp["span_in_full_paper"] == {"start": sp["start"] + 1000, "end": sp["end"] + 1000}
