"""Tests for the preprocessing render layer (extractor_mvp.render).

Offline only: builds spec objects in-process and loads the committed
``examples/spec.json``; no network, no LLM, no PDF.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from fmri_repro.spec.migrations import parse_any_version
from fmri_repro.spec.preprocessing import (
    DistortionCorrection,
    PipelineRef,
    Preprocessing,
    SpatialSmoothing,
)
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    Basis,
    DateInferredVersionBasis,
    Deferral,
    DeferredToCitation,
    DerivedBasis,
    Extracted,
    FieldConventionBasis,
    InferredDefault,
    LabPriorBasis,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    PriorPublicationBasis,
    ProvenancedField,
    Span,
    VersionDefaultBasis,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef
from fmri_repro.spec.v0_4_0 import StudySpec  # current root; examples/spec.json is a 0.4.0 doc

from extractor_mvp import render
from extractor_mvp.cobidas import COBIDAS_D3_ROWS

# ---------------------------------------------------------------------------
# Locating the example spec (repo_root/examples/spec.json)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_SPEC = _REPO_ROOT / "examples" / "spec.json"


def _example_preprocessings() -> list[Preprocessing]:
    study = StudySpec.model_validate_json(_EXAMPLE_SPEC.read_text())
    out: list[Preprocessing] = []
    for spec in study.specs:
        out.extend(spec.preprocessing)
    return out


# ---------------------------------------------------------------------------
# Synthetic field builders (one per state), keyed to real step classes
# ---------------------------------------------------------------------------


def _span(text: str = "verbatim methods sentence") -> Span:
    return Span(start=0, end=len(text), text=text, section="Methods")


def _extracted(field_id: str, value: object) -> ProvenancedField:
    return ProvenancedField(
        field_id=field_id,
        extraction=Extracted(value=value, spans=[_span()], confidence=0.95),
        inference=NotApplicable(),
    )


def _missing_left(field_id: str) -> ProvenancedField:
    return ProvenancedField(
        field_id=field_id,
        extraction=MissingFromPaper(
            searched_terms=["smoothing", "FWHM"], sections_searched=["Methods"]
        ),
        inference=LeftMissing(reason="no defensible default"),
    )


def _missing_inferred(field_id: str, value: object) -> ProvenancedField:
    return ProvenancedField(
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=["kernel"], sections_searched=["Methods"]),
        inference=InferredDefault(
            value=value,
            basis=VersionDefaultBasis(tool="fmriprep", version="23.1.3"),
            confidence=0.9,
            alternative_inferences=[],
        ),
    )


def _deferred_left(field_id: str, ref: str) -> ProvenancedField:
    return ProvenancedField(
        field_id=field_id,
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(ref=ref, span=_span(f"as described in {ref}"), target_kind="paper")
            ],
            searched_terms=["approach"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(),
    )


def _applies_to() -> list[AcquisitionRef]:
    return [AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))]


def _synthetic_preprocessing() -> Preprocessing:
    """SpatialSmoothing exercising all four reachable extraction/inference states,
    plus a base_pipeline whose outer arm (INFERRED) and inner version (DEFERRED)
    differ.
    """
    smoothing = SpatialSmoothing(
        fwhm_mm=_extracted("fwhm_mm", 6.0),  # EXTRACTED
        space=_missing_left("space"),  # MISSING + LEFT_MISSING -> MISSING_FROM_PAPER
        kernel_type=_missing_inferred("kernel_type", "gaussian"),  # MISSING + INFERRED_DEFAULT
        approach=_deferred_left("approach", "Esteban 2019"),  # DEFERRED + LEFT_MISSING
    )
    # base_pipeline: pipeline identity INFERRED; its version DEFERRED (different states).
    version_field = _deferred_left("version", "fMRIPrep docs")
    base_pipeline: ProvenancedField[PipelineRef] = ProvenancedField(
        field_id="base_pipeline",
        extraction=MissingFromPaper(searched_terms=["pipeline"], sections_searched=["Methods"]),
        inference=InferredDefault(
            value=PipelineRef(name="fmriprep", version=version_field),
            basis=VersionDefaultBasis(tool="fmriprep", version="23.1.3"),
            confidence=0.9,
            alternative_inferences=[],
        ),
    )
    return Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[smoothing])


# ---------------------------------------------------------------------------
# 1. Example spec: all three renderers run; JSON round-trips
# ---------------------------------------------------------------------------


def test_example_spec_present():
    assert _EXAMPLE_SPEC.exists(), f"missing example spec: {_EXAMPLE_SPEC}"


@pytest.mark.parametrize("idx", range(len(_example_preprocessings())))
def test_example_renderers_run_and_json_round_trips(idx: int):
    prep = _example_preprocessings()[idx]
    # no exceptions
    rows = render.flatten(prep)
    assert rows
    txt = render.to_field_table(prep)
    bullets = render.to_field_bullets(prep)
    js = render.to_json(prep)
    assert txt and bullets and js
    # round-trip
    assert Preprocessing.model_validate_json(js) == prep


def test_example_state_coverage(capsys):
    """Report which of the five states the example exercises."""
    ext_seen: set[str] = set()
    inf_seen: set[str] = set()
    for prep in _example_preprocessings():
        for r in render.flatten(prep):
            if r.extraction_status:
                ext_seen.add(r.extraction_status)
            if r.inference_status:
                inf_seen.add(r.inference_status)
    all_states = ext_seen | inf_seen
    five = {
        "EXTRACTED",
        "MISSING_FROM_PAPER",
        "DEFERRED_TO_CITATION",
        "INFERRED_DEFAULT",
        "LEFT_MISSING",
    }
    print("example extraction states:", sorted(ext_seen))
    print("example inference states:", sorted(inf_seen))
    print("five-state coverage:", {s: (s in all_states) for s in sorted(five)})
    # The committed example exercises all five.
    assert five <= all_states


# ---------------------------------------------------------------------------
# 2. Detection method: isinstance works on a real ProvenancedField[str]
# ---------------------------------------------------------------------------


def test_isinstance_matches_real_provenanced_field():
    """isinstance(v, ProvenancedField) matches a real parametrized field from the
    example (base_pipeline.version is ProvenancedField[str]). render uses isinstance.
    """
    prep = _example_preprocessings()[0]
    base = prep.base_pipeline
    assert isinstance(base, ProvenancedField)  # ProvenancedField[PipelineRef]
    pref = base.extraction.value if base.extraction.status == "EXTRACTED" else base.inference.value
    version = pref.version
    assert type(version).__name__ == "ProvenancedField[str]"
    assert isinstance(version, ProvenancedField)
    assert render.is_provenanced_field(version)
    assert render.is_provenanced_field(base)


# ---------------------------------------------------------------------------
# 3. Synthetic: every ProvenancedField (incl. base_pipeline.version) emits a row
#    with the correct label; all five states present
# ---------------------------------------------------------------------------


def test_synthetic_emits_row_per_field_with_correct_labels():
    prep = _synthetic_preprocessing()
    rows = render.flatten(prep)
    by_path = {r.path: r for r in rows}

    # base_pipeline outer (INFERRED) and inner version (DEFERRED) are distinct rows
    assert "base_pipeline" in by_path
    assert "base_pipeline.version" in by_path
    assert by_path["base_pipeline"].state == render.INFERRED_DEFAULT
    assert by_path["base_pipeline.version"].state == render.DEFERRED_TO_CITATION

    # step fields, one per reachable display state
    assert by_path["spatial_smoothing.fwhm_mm"].state == render.EXTRACTED
    assert by_path["spatial_smoothing.kernel_type"].state == render.INFERRED_DEFAULT
    assert by_path["spatial_smoothing.approach"].state == render.DEFERRED_TO_CITATION
    assert by_path["spatial_smoothing.space"].state == render.MISSING_FROM_PAPER

    # one row per ProvenancedField: 2 (base+version) + 4 smoothing fields
    assert len(rows) == 6

    # all five raw states present across the rows
    ext = {r.extraction_status for r in rows if r.extraction_status}
    inf = {r.inference_status for r in rows if r.inference_status}
    assert ext == {"EXTRACTED", "MISSING_FROM_PAPER", "DEFERRED_TO_CITATION"}
    assert inf == {"NOT_APPLICABLE", "INFERRED_DEFAULT", "LEFT_MISSING"}


def test_synthetic_row_payloads():
    prep = _synthetic_preprocessing()
    by_path = {r.path: r for r in render.flatten(prep)}

    extracted = by_path["spatial_smoothing.fwhm_mm"]
    assert extracted.value == 6.0
    assert extracted.span_text and "verbatim" in extracted.span_text

    inferred = by_path["spatial_smoothing.kernel_type"]
    assert inferred.value == "gaussian"
    assert inferred.basis_type == "version_default"
    assert inferred.confidence == 0.9

    deferred = by_path["spatial_smoothing.approach"]
    assert deferred.deferral_refs == ["Esteban 2019"]

    missing = by_path["spatial_smoothing.space"]
    assert missing.value is None
    assert missing.searched_terms  # captured for MISSING


def test_synthetic_renderers_run_and_round_trip():
    prep = _synthetic_preprocessing()
    txt = render.to_field_table(prep)
    bullets = render.to_field_bullets(prep)
    js = render.to_json(prep)
    assert Preprocessing.model_validate_json(js) == prep
    # to_field_table shows the five-state header line and the expected per-state phrasing
    assert "states:" in txt
    assert "from paper: 6.0" in txt
    assert "inferred: gaussian" in txt
    assert "(version_default, conf 0.9)" in txt
    assert "deferred to Esteban 2019" in txt
    # a gap row characterises its reason instead of asserting the paper omitted it.
    # _missing_left's reason is deliberately unknown (see the unclassified test below).
    assert "unspecified (reason: no defensible default)" in txt
    # to_field_bullets: bold step header + path-prefixed bullets
    assert "**spatial_smoothing**" in bullets
    assert "- spatial_smoothing.fwhm_mm: extracted 6.0" in bullets
    assert "- base_pipeline.version: deferred" in bullets


# ---------------------------------------------------------------------------
# 4. Path labels: step.kind-prefixed; base_pipeline.version distinct from base_pipeline
# ---------------------------------------------------------------------------


def test_path_labels_are_kind_prefixed_and_base_version_distinct():
    prep = _synthetic_preprocessing()
    rows = render.flatten(prep)
    paths = [r.path for r in rows]
    # every step-field path is prefixed with the step kind
    for r in rows:
        if r.group == "base_pipeline":
            assert r.path in ("base_pipeline", "base_pipeline.version")
        else:
            assert r.path.startswith(f"{r.group}.")
    # base_pipeline and base_pipeline.version are two separate rows
    assert paths.count("base_pipeline") == 1
    assert paths.count("base_pipeline.version") == 1
    assert paths.index("base_pipeline") < paths.index("base_pipeline.version")


def test_field_id_collision_disambiguated_by_kind():
    """`interpolation` collides across kinds; kind-prefixing keeps paths unique
    within a single Preprocessing (across pipelines, `base_pipeline` recurs)."""
    for prep in _example_preprocessings():
        seen: set[str] = set()
        for r in render.flatten(prep):
            assert r.path not in seen, f"duplicate path {r.path}"
            seen.add(r.path)


# ---------------------------------------------------------------------------
# 5. Structural fields produce no rows
# ---------------------------------------------------------------------------


def test_structural_fields_emit_no_rows():
    # DistortionCorrection carries the structural `intended_fieldmap`; PipelineRef
    # carries the structural `name`; every step carries the `kind` literal.
    distortion = DistortionCorrection(
        source=_missing_left("source"),
        method=_missing_left("method"),
        intended_fieldmap=NotApplicable(),
    )
    version_field = _extracted("version", "23.1.3")
    base_pipeline = ProvenancedField(
        field_id="base_pipeline",
        extraction=Extracted(
            value=PipelineRef(name="fmriprep", version=version_field),
            spans=[_span()],
            confidence=0.9,
        ),
        inference=NotApplicable(),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[distortion])
    rows = render.flatten(prep)
    paths = {r.path for r in rows}
    # no structural fields
    assert not any(p.endswith(".intended_fieldmap") for p in paths)
    assert not any(p.endswith(".name") or p == "base_pipeline.name" for p in paths)
    assert not any(p.endswith(".kind") for p in paths)
    # only the real provenanced fields appear
    assert paths == {
        "base_pipeline",
        "base_pipeline.version",
        "distortion_correction.source",
        "distortion_correction.method",
    }


# ---------------------------------------------------------------------------
# 6. NotApplicable base_pipeline: single sentinel row, no version recursion
# ---------------------------------------------------------------------------


def test_notapplicable_base_pipeline_single_row():
    smoothing = SpatialSmoothing(
        fwhm_mm=_extracted("fwhm_mm", 5.0),
        space=_missing_left("space"),
        kernel_type=_missing_left("kernel_type"),
        approach=_missing_left("approach"),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=NotApplicable(), steps=[smoothing])
    rows = render.flatten(prep)
    base_rows = [r for r in rows if r.group == "base_pipeline"]
    assert len(base_rows) == 1
    assert base_rows[0].path == "base_pipeline"
    assert base_rows[0].state == render.BASE_NOT_APPLICABLE
    assert not any(r.path == "base_pipeline.version" for r in rows)
    assert "not applicable (from-scratch)" in render.to_field_table(prep)


def test_to_json_matches_model_dump_json():
    prep = _synthetic_preprocessing()
    assert render.to_json(prep) == prep.model_dump_json(indent=2)
    assert json.loads(render.to_json(prep))  # valid JSON


# ---------------------------------------------------------------------------
# 7. base_pipeline outer-arm coverage: MISSING / DEFERRED carry no PipelineRef,
#    so the version recursion must be skipped (no .value crash, no version row).
# ---------------------------------------------------------------------------


def _one_step() -> SpatialSmoothing:
    """A minimal valid step so the Preprocessing is well-formed."""
    return SpatialSmoothing(
        fwhm_mm=_extracted("fwhm_mm", 5.0),
        space=_missing_left("space"),
        kernel_type=_missing_left("kernel_type"),
        approach=_missing_left("approach"),
    )


def test_base_pipeline_outer_missing_no_version_row():
    base_pipeline = ProvenancedField(
        field_id="base_pipeline",
        extraction=MissingFromPaper(
            searched_terms=["pipeline", "fMRIPrep", "HCP"], sections_searched=["Methods"]
        ),
        # the reason extractor.py:867 actually emits for this shape
        inference=LeftMissing(reason="no_base_pipeline_named"),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[_one_step()])
    rows = render.flatten(prep)
    base_rows = [r for r in rows if r.group == "base_pipeline"]
    assert len(base_rows) == 1
    assert base_rows[0].path == "base_pipeline"
    assert base_rows[0].state == render.MISSING_FROM_PAPER
    assert not any(r.path == "base_pipeline.version" for r in rows)
    # BEFORE (Track A item D): asserted "base_pipeline: not reported" — a claim about the
    # author's manuscript, emitted without consulting the reason. Now characterised.
    assert (
        "base_pipeline: no base pipeline named in source — you must specify"
        in render.to_field_table(prep)
    )


def test_base_pipeline_outer_deferred_no_version_row():
    base_pipeline = ProvenancedField(
        field_id="base_pipeline",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(
                    ref="Glasser 2013 - HCP MPP",
                    span=_span("preprocessed with the HCP minimal pipeline (Glasser et al., 2013)"),
                    target_kind="pipeline",
                )
            ],
            searched_terms=["pipeline version"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[_one_step()])
    rows = render.flatten(prep)
    base_rows = [r for r in rows if r.group == "base_pipeline"]
    assert len(base_rows) == 1
    assert base_rows[0].path == "base_pipeline"
    assert base_rows[0].state == render.DEFERRED_TO_CITATION
    assert base_rows[0].deferral_refs == ["Glasser 2013 - HCP MPP"]
    assert not any(r.path == "base_pipeline.version" for r in rows)
    assert "base_pipeline: deferred to Glasser 2013 - HCP MPP" in render.to_field_table(prep)


def test_to_field_table_shows_inferred_line(capsys):
    """TASK 3: a step field at (MISSING, INFERRED_DEFAULT) renders the inferred line."""
    smoothing = SpatialSmoothing(
        fwhm_mm=_extracted("fwhm_mm", 6.0),
        space=_missing_left("space"),
        kernel_type=_missing_inferred("kernel_type", "gaussian"),  # MISSING + INFERRED_DEFAULT
        approach=_missing_left("approach"),
    )
    base_pipeline = ProvenancedField(
        field_id="base_pipeline",
        extraction=Extracted(
            value=PipelineRef(name="fMRIPrep", version=_extracted("version", "23.1.3")),
            spans=[_span("fMRIPrep 23.1.3")],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[smoothing])
    txt = render.to_field_table(prep)
    print(txt)
    assert "kernel_type: inferred: gaussian   (version_default, conf 0.9)" in txt


# ---------------------------------------------------------------------------
# View 4: to_protocol — tool-agnostic replication protocol
# ---------------------------------------------------------------------------


def _basis_row(basis: Basis, confidence: float) -> render.FieldRow:
    """Minimal INFERRED_DEFAULT FieldRow for exercising _fmt_basis_note directly."""
    return render.FieldRow(
        path="step.field",
        group="step",
        state=render.INFERRED_DEFAULT,
        basis_type=basis.basis_type,
        confidence=confidence,
        basis=basis,
    )


def _missing_reason(field_id: str, reason: str) -> ProvenancedField:
    """A MISSING_FROM_PAPER field carrying a specific LeftMissing.reason."""
    return ProvenancedField(
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=LeftMissing(reason=reason),
    )


def test_protocol_pipeline_order_base_first_then_steps():
    # 1. base_pipeline section precedes the steps section, in that order.
    out = render.to_protocol(_synthetic_preprocessing(), source="synthetic")
    i_title = out.index("# Replication Protocol — synthetic")
    i_base = out.index("Base pipeline")
    i_steps = out.index("## Preprocessing steps (pipeline order)")
    i_step1 = out.index("### 1. spatial_smoothing")
    assert i_title < i_base < i_steps < i_step1


def test_protocol_each_state_renders_its_line():
    # 2. one field per reachable display state -> its exact protocol line.
    out = render.to_protocol(_synthetic_preprocessing())
    assert "- fwhm_mm = 6.0   [from paper]" in out  # EXTRACTED
    # MISSING: _missing_left uses an unknown reason -> unclassified callout wording
    assert "- space: unspecified (reason: no defensible default)" in out
    assert "- kernel_type = gaussian   [INFERRED — not stated in source]" in out  # INFERRED
    assert (  # DEFERRED
        "- approach: deferred to Esteban 2019 — resolve by consulting the cited source" in out
    )


def test_protocol_basis_note_dispatch_all_bases():
    # 3. one field per basis_type; specifics + confidence/ceiling suffix.
    from datetime import date

    n_date = render._fmt_basis_note(
        _basis_row(
            DateInferredVersionBasis(
                tool="fMRIPrep", inferred_version="25.2.5", paper_date=date(2015, 3, 1)
            ),
            0.75,
        )
    )
    # source-neutral + upper-bound-honest: paper_date is /CreationDate (not the pub date),
    # and resolve_version picks the latest release <= paper_date (a bound, not a pinpoint).
    assert "fMRIPrep 25.2.5 — latest release on or before paper date 2015-03-01" in n_date
    assert "publication date" not in n_date  # lock the over-claim fix against regression
    assert f"(confidence 0.75 / ceiling {BASIS_CEILINGS['date_inferred_version']})" in n_date

    n_ver = render._fmt_basis_note(
        _basis_row(VersionDefaultBasis(tool="fMRIPrep", version="23.1.3"), 0.9)
    )
    assert "fMRIPrep 23.1.3 (version stated/confirmed)" in n_ver
    assert f"ceiling {BASIS_CEILINGS['version_default']}" in n_ver

    n_prior = render._fmt_basis_note(
        _basis_row(PriorPublicationBasis(citation="Glasser 2013"), 0.6)
    )
    assert "from cited work Glasser 2013" in n_prior

    n_lab = render._fmt_basis_note(_basis_row(LabPriorBasis(lab_id="poldrack_lab"), 0.5))
    assert "lab default (poldrack_lab)" in n_lab

    n_conv = render._fmt_basis_note(_basis_row(FieldConventionBasis(source="COBIDAS"), 0.4))
    assert "field convention (COBIDAS)" in n_conv

    n_der = render._fmt_basis_note(
        _basis_row(DerivedBasis(source_field_ids=["surface_projection.target_surface"]), 0.7)
    )
    assert "derived from surface_projection.target_surface" in n_der
    assert f"ceiling {BASIS_CEILINGS['derived']}" in n_der

    # the Configurator-authored note is rendered verbatim when present
    n_noted = render._fmt_basis_note(
        _basis_row(VersionDefaultBasis(tool="X", version="1", note="per release notes"), 0.9)
    )
    assert "— per release notes" in n_noted


def _one_field_spec(reason_field: ProvenancedField) -> Preprocessing:
    """A SpatialSmoothing whose `space` carries a reason-bearing MISSING field; the
    other three fields are EXTRACTED so only `space` is a gap. Base = from-scratch."""
    smoothing = SpatialSmoothing(
        fwhm_mm=_extracted("fwhm_mm", 6.0),
        space=reason_field,
        kernel_type=_extracted("kernel_type", "gaussian"),
        approach=_extracted("approach", "fixed_kernel"),
    )
    return Preprocessing(applies_to=_applies_to(), base_pipeline=NotApplicable(), steps=[smoothing])


def test_protocol_each_base_reason_renders_its_line():
    # 4. each of the 9 known base reasons -> its exact _REASON_LINE callout.
    expected = {
        "not_stated_in_text": "not reported in source — you must specify",
        "no_base_pipeline_named": "no base pipeline named in source — you must specify",
        "version_deferred_to_kb": "version not reported in source — you must specify",
        "value_not_in_literal": (
            "reported in source but not resolvable to a controlled value — map manually"
        ),
        "not_targeted_by_mvp": "not examined by the extractor — check the source yourself",
        "extraction_quote_unresolved": (
            "value present in source but span unresolved (extractor limitation)"
        ),
        # These three fire before/instead of quote validation, so they describe the
        # extractor and assert nothing about the manuscript.
        "value_not_numeric": (
            "extractor returned a non-numeric value for this field — enter manually"
        ),
        "extraction_quote_missing": (
            "extractor returned a value with no supporting quote — unverifiable, "
            "check the source yourself"
        ),
        "deferral_quote_unresolved": (
            "extractor reported a deferral to another source but could not locate the "
            "deferring sentence — check the source yourself"
        ),
    }
    for reason, line in expected.items():
        out = render.to_protocol(_one_field_spec(_missing_reason("space", reason)))
        assert f"- space: {line}" in out, reason


def test_protocol_suffixed_reason_uses_base():
    # suffixed reason resolves via its base ("extraction_quote_unresolved").
    out = render.to_protocol(
        _one_field_spec(_missing_reason("space", "extraction_quote_unresolved:quote_not_found"))
    )
    assert "- space: value present in source but span unresolved (extractor limitation)" in out
    assert "1 not covered by extractor" in out  # base -> not_covered bucket


def test_protocol_unknown_reason_is_unclassified_not_a_source_gap():
    # unknown reason -> "unclassified" bucket + literal callout, NOT a source bucket.
    out = render.to_protocol(_one_field_spec(_missing_reason("space", "some_future_reason")))
    assert "- space: unspecified (reason: some_future_reason)" in out
    assert "1 unclassified" in out
    assert "not reported in source" not in out
    assert "unmappable to controlled vocabulary" not in out


#: Reason bases that provably cannot reach a gap callout: each is paired with a
#: DeferredToCitation extraction, so _display_state routes the row to DEFERRED_TO_CITATION
#: and neither _fmt_field_text nor _protocol_main ever consults the reason tables.
_UNREACHABLE_REASON_BASES = {
    "deferred_to_citation",  # extractor.py:472, :734
    "citation_shaped_name_value_unsupported",  # extractor.py:783
}


def _producible_reason_bases(path: Path) -> tuple[set[str], list[str]]:
    """Base LeftMissing.reasons a module can produce, and any it builds non-literally.

    Resolves the two ways a reason reaches a ProvenancedField — the 3rd positional argument
    of ``_missing_pf(...)`` and the ``reason=`` keyword of ``LeftMissing(...)`` — through
    string constants, f-string prefixes, and module/function locals bound to either.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))

    def literal(node: ast.AST, consts: dict[str, str]) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr) and node.values:  # f"base:{suffix}" -> "base:"
            head = node.values[0]
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                return head.value
        if isinstance(node, ast.Name):
            return consts.get(node.id)
        return None

    consts: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            lit = literal(node.value, {})
            if lit is not None:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        consts[target.id] = lit

    bases: set[str] = set()
    dynamic: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        args: list[ast.AST] = []
        if node.func.id == "_missing_pf" and len(node.args) >= 3:
            args.append(node.args[2])
        elif node.func.id == "LeftMissing":
            args += [kw.value for kw in node.keywords if kw.arg == "reason"]
        for arg in args:
            lit = literal(arg, consts)
            if lit is None:
                dynamic.append(f"{path.name}:{getattr(arg, 'lineno', '?')}")
            else:
                bases.add(lit.split(":", 1)[0])
    return bases, dynamic


def test_every_producible_reason_base_is_mapped() -> None:
    """No reason this codebase produces may fall through to the ``unclassified`` fallback.

    Regression guard for Track A item D. ``value_not_numeric``, ``extraction_quote_missing``
    and ``deferral_quote_unresolved`` were live producers present in NEITHER reason table, so
    a real report could render ``unspecified (reason: value_not_numeric)`` — a raw internal
    token in author-facing output — and count the row as ``unclassified`` in the completeness
    header. Enumerating the producers, rather than pinning a hand-written list, means a newly
    added reason fails here until it is either mapped or documented as unreachable.
    """
    from fmri_repro.spec import migrations

    sources = [
        Path(render.__file__).with_name("extractor.py"),
        Path(migrations.__file__),
    ]
    bases: set[str] = set()
    dynamic: list[str] = []
    for src in sources:
        assert src.is_file(), f"reason source moved: {src}"
        found, unresolved = _producible_reason_bases(src)
        bases |= found
        dynamic += unresolved

    assert not dynamic, (
        f"reason argument(s) this scan cannot resolve: {dynamic}. The guard is only as good "
        "as its enumeration — extend _producible_reason_bases rather than ignoring these."
    )
    # the scan really does reach all three producer shapes (literal, f-string, local)
    for expected in ("not_stated_in_text", "not_targeted_by_mvp", "deferral_quote_unresolved"):
        assert expected in bases, f"scan missed a known producer: {expected}"

    unmapped = sorted(
        b
        for b in bases - _UNREACHABLE_REASON_BASES
        if b not in render._REASON_BUCKET or b not in render._REASON_LINE
    )
    assert not unmapped, (
        f"reason base(s) missing from _REASON_BUCKET and/or _REASON_LINE: {unmapped}. "
        "An unmapped reason renders as 'unspecified (reason: ...)' in author-facing output "
        "and is counted as 'unclassified'. Add an entry to BOTH tables in render.py."
    )


def test_protocol_header_bucket_math_and_not_covered_never_source():
    # 5. header partitions gaps by reason; not_targeted_by_mvp -> not_covered, never source.
    smoothing = SpatialSmoothing(
        fwhm_mm=_extracted("fwhm_mm", 6.0),  # 1 specified
        space=_missing_reason("space", "not_stated_in_text"),  # not_reported
        kernel_type=_missing_reason("kernel_type", "value_not_in_literal"),  # unmappable
        approach=_missing_reason("approach", "not_targeted_by_mvp"),  # not_covered
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=NotApplicable(), steps=[smoothing])
    out = render.to_protocol(prep)
    header = next(ln for ln in out.splitlines() if ln.startswith("Completeness:"))
    assert "1 specified in source" in header
    assert "1 not reported in source" in header
    assert "1 reported but unmappable to controlled vocabulary" in header
    assert "1 not covered by extractor" in header
    # not_covered is NEVER summed into a source-completeness figure
    assert "specified in source · 1 not covered" not in header  # not adjacent-merged
    # zero-count buckets omitted
    assert "inferred" not in header and "deferred" not in header and "unclassified" not in header


def test_protocol_left_missing_reason_set_after_flatten():
    # regression for the gating bug: a (MISSING_FROM_PAPER, LeftMissing(reason=X)) field
    # carries row.left_missing_reason == X after flatten() (NOT gated on display state).
    prep = _one_field_spec(_missing_reason("space", "value_not_in_literal:underspecified"))
    row = next(r for r in render.flatten(prep) if r.path.endswith(".space"))
    assert row.state == render.MISSING_FROM_PAPER
    assert row.left_missing_reason == "value_not_in_literal:underspecified"


def test_protocol_base_pipeline_variants():
    # 6a. named base (EXTRACTED) + EXTRACTED version sub-row.
    base_named = ProvenancedField(
        field_id="base_pipeline",
        extraction=Extracted(
            value=PipelineRef(name="fMRIPrep", version=_extracted("version", "23.1.3")),
            spans=[_span("fMRIPrep 23.1.3")],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )
    out_a = render.to_protocol(
        Preprocessing(applies_to=_applies_to(), base_pipeline=base_named, steps=[_one_step()])
    )
    assert "Base pipeline: fMRIPrep   [from paper]" in out_a
    assert "  version = 23.1.3   [from paper]" in out_a

    # 6b. from-scratch (NotApplicable) -> single sentinel line, no version recursion.
    out_b = render.to_protocol(
        Preprocessing(applies_to=_applies_to(), base_pipeline=NotApplicable(), steps=[_one_step()])
    )
    assert "Base pipeline: built from scratch (no named base pipeline)" in out_b
    assert "version" not in out_b.split("## Preprocessing")[0]  # no version line in base section

    # 6c. named base but version MISSING (the Chen case: version_deferred_to_kb).
    base_noverson = ProvenancedField(
        field_id="base_pipeline",
        extraction=Extracted(
            value=PipelineRef(
                name="CCS", version=_missing_reason("version", "version_deferred_to_kb")
            ),
            spans=[_span("CCS")],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )
    out_c = render.to_protocol(
        Preprocessing(applies_to=_applies_to(), base_pipeline=base_noverson, steps=[_one_step()])
    )
    assert "Base pipeline: CCS   [from paper]" in out_c
    assert "  version: version not reported in source — you must specify" in out_c


def test_protocol_deterministic():
    # 7. two calls on the same spec are byte-identical.
    prep = _synthetic_preprocessing()
    assert render.to_protocol(prep, source="x") == render.to_protocol(prep, source="x")


# ---------------------------------------------------------------------------
# COBIDAS D.3 coverage section
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("surface", render.REPORT_SURFACES, ids=lambda f: f.__name__)
def test_report_surface_accounts_for_every_mandatory_d3_row(surface) -> None:
    """Every sanctioned report surface must account for D.3 rows the extractor never saw.

    Replaces the older `to_protocol`-specific check, which asserted a string was present in
    one function's output and so passed while a new caller bypassed that function entirely.
    This keys on the OUTPUT and on the registry, never on the call graph.

    `_synthetic_preprocessing()` is `steps=[SpatialSmoothing]`, so `motion_correction` emits
    no FieldRows at all: a surface walking present steps would omit it silently.
    """
    out = surface(_synthetic_preprocessing())

    # 1. fails on any report lacking the coverage section, however it was produced
    header = re.search(r"^Mandatory rows: (\d+)$", out, re.M)
    assert header is not None, "report carries no COBIDAS D.3 coverage section"
    n_mandatory = int(header.group(1))

    # 2. the denominator is the standard, not this Preprocessing's steps
    assert n_mandatory == sum(1 for r in COBIDAS_D3_ROWS if r.mandatory)

    # 3. a denominator switched from the catalog to present-steps would not reconcile
    assessed = re.search(r"^  Assessed by AESPA: (\d+)", out, re.M)
    not_assessed = re.search(r"^  Not assessed by AESPA: (\d+)", out, re.M)
    assert assessed is not None and not_assessed is not None
    assert int(assessed.group(1)) + int(not_assessed.group(1)) == n_mandatory

    # 4. the live regression: a step with NO extractor is NAMED, not silently dropped
    assert "Motion correction" in out


def test_field_views_are_not_reports() -> None:
    """The partial views must NOT grow a coverage section.

    Bolting one on is the obvious wrong move once the rename lands: it would make them look
    like reports while they still omit D.3 rows for which no field rows exist.
    """
    prep = _synthetic_preprocessing()
    for view in (render.to_field_table, render.to_field_bullets):
        out = view(prep)
        assert "Mandatory rows:" not in out
        assert "COBIDAS D.3 coverage" not in out


def test_field_view_characterises_an_untargeted_field_like_the_report() -> None:
    """The surfaces must not contradict each other about the same field.

    Was xfail(strict=True) until Track A item D routed the field views' MISSING branch
    through _REASON_LINE. Both field views are covered, not just to_field_table: the
    to_field_bullets conflation lived in _SHORT_LABEL and was a separate code path.
    """
    prep = _one_field_spec(_missing_reason("space", "not_targeted_by_mvp"))
    line = "not examined by the extractor — check the source yourself"
    assert line in render.to_report(prep)
    for view in (render.to_field_table(prep), render.to_field_bullets(prep)):
        assert line in view
        # the field the extractor never targeted is NOT called a reporting gap...
        assert "space: not reported" not in view
        # ...and is not silently dropped either (the harm A2 prevents, relocated)
        assert "space" in view


def test_software_violation_surfaces_agree_for_every_base_pipeline_state() -> None:
    """Header and body must make the SAME claim about the Software row (Track A item A3).

    The header guarded the unconditional-violation flag on ``covered_by_extractor``; the body
    guarded only on ``addressed``, so for a base_pipeline the extractor could not assess, one
    report contradicted itself — the header counting Software as unassessed while the body
    accused the author of an unconditional COBIDAS violation. Both now require coverage.
    """

    def _prep(bp: object) -> Preprocessing:
        return Preprocessing(applies_to=_applies_to(), base_pipeline=bp, steps=[_one_step()])

    deferred = ProvenancedField(
        field_id="base_pipeline",
        extraction=DeferredToCitation(
            deferrals=[Deferral(ref="Glasser 2013", span=_span(), target_kind="pipeline")],
            searched_terms=["pipeline"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="deferred_to_citation"),
    )
    none_named = ProvenancedField(
        field_id="base_pipeline",
        extraction=MissingFromPaper(searched_terms=["pipeline"], sections_searched=["Methods"]),
        inference=LeftMissing(reason="no_base_pipeline_named"),
    )
    cases = (
        # a cited pipeline answers identity, not version -> a violation, worded as a
        # deferral rather than as an unnamed-software report (DELTA §8)
        ("deferred to a citation", deferred, True),
        # searched and nothing named -> a real, citable violation on both surfaces
        ("searched, none named", none_named, True),
        # NotApplicable carries two opposite meanings -> the tool cannot tell -> silence
        ("NotApplicable", NotApplicable(), False),
    )
    for label, bp, expect_violation in cases:
        out = render.to_cobidas_coverage(_prep(bp))
        header = out.split("###")[0]
        in_header = "Software — unconditional violation" in header
        in_body = "NOT REPORTED — COBIDAS D.3 requires" in out
        assert in_header == in_body, f"{label}: header says {in_header}, body says {in_body}"
        assert in_body is expect_violation, label


def test_deferred_software_line_names_the_citation() -> None:
    """The deferral line says identity was deferred, and names the ref.

    Without this branch a deferring paper receives the bare "No version reported by the
    paper." written for the unnamed-software case, because ``_base_pipeline_name`` returns
    None when no ``PipelineRef`` resolves. Pins the fourth line of
    docs/design/DELTA_software_row_deferral.md §8.
    """
    base_pipeline = ProvenancedField(
        field_id="base_pipeline",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(
                    ref="refs. 47 and 48",
                    span=_span("as previously described in refs. 47 and 48"),
                    target_kind="paper",
                )
            ],
            searched_terms=["pipeline"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="deferred_to_citation"),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[_one_step()])
    out = render.to_cobidas_coverage(prep)
    assert "### Not reported (mandatory, unconditional)" in out
    assert "pipeline identity deferred to refs. 47 and 48." in out
    # Must not fall through to either non-deferral line. Asserting the CURRENT strings, not
    # a retired one: an exclusion of a string nothing emits any more cannot fail.
    assert "No software named in the source." not in out
    assert "Pipeline named:" not in out


def test_software_line_states_the_action_for_each_case() -> None:
    """One heading, four lines, each naming the action the author needs (DELTA §8).

    The unnamed case is the one that motivated the rework: telling an author who named no
    software that their version is missing is the wrong instruction. The inferred case is a
    disclosure rather than guidance and must keep saying AESPA supplied the version.
    """
    named = ProvenancedField(
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(name="CCS", version=_missing_reason("version", "not_stated_in_text")),
            spans=[_span("preprocessed with CCS")],
            confidence=0.8,
        ),
        inference=NotApplicable(),
    )
    none_named = ProvenancedField(
        field_id="base_pipeline",
        extraction=MissingFromPaper(searched_terms=["pipeline"], sections_searched=["Methods"]),
        inference=LeftMissing(reason="no_base_pipeline_named"),
    )

    out_named = render.to_cobidas_coverage(
        Preprocessing(applies_to=_applies_to(), base_pipeline=named, steps=[_one_step()])
    )
    assert "Pipeline named: CCS. Give its version and revision number." in out_named

    out_unnamed = render.to_cobidas_coverage(
        Preprocessing(applies_to=_applies_to(), base_pipeline=none_named, steps=[_one_step()])
    )
    assert "No software named in the source. Name the software," in out_unnamed
    assert "Pipeline named:" not in out_unnamed


def test_deferred_software_line_does_not_double_the_terminator() -> None:
    """A ref that already ends in a period must not render as "et al..".

    viduarre_2017's real ref is "Glasser et al.", so this is corpus-shaped, not hypothetical.
    """
    base_pipeline = ProvenancedField(
        field_id="base_pipeline",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(
                    ref="Glasser et al.",
                    span=_span("preprocessed as in Glasser et al."),
                    target_kind="paper",
                )
            ],
            searched_terms=["pipeline"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="deferred_to_citation"),
    )
    prep = Preprocessing(applies_to=_applies_to(), base_pipeline=base_pipeline, steps=[_one_step()])
    out = render.to_cobidas_coverage(prep)
    assert "deferred to Glasser et al.)" in out
    assert "et al.." not in out


def test_cobidas_coverage_deterministic() -> None:
    prep = _synthetic_preprocessing()
    assert render.to_cobidas_coverage(prep) == render.to_cobidas_coverage(prep)


def test_to_protocol_methods_suspicious_warning() -> None:
    from extractor_mvp.methods_finder import MethodsSlice

    prep = _synthetic_preprocessing()
    # no methods_slice -> no warning
    assert "⚠" not in render.to_protocol(prep)
    # whole-document fallback -> the strong warning
    fallback = MethodsSlice(
        text="x",
        start_offset=0,
        found_via="fallback_full_text",
        matched_header=None,
        end_offset=1,
        slice_ratio=1.0,
        ended_at="end_of_text",
        suspicious=True,
    )
    assert "Methods section not identified" in render.to_protocol(prep, methods_slice=fallback)
    # bloated header slice -> the softer warning
    bloated = MethodsSlice(
        text="x",
        start_offset=0,
        found_via="header_match",
        matched_header="Methods",
        end_offset=1,
        slice_ratio=0.7,
        ended_at="References",
        suspicious=True,
    )
    assert "Methods slice may include Results" in render.to_protocol(prep, methods_slice=bloated)


_CHEN_JSON = (
    _REPO_ROOT / "extractor_mvp" / "results" / "batch_v6_full" / "papers" / "chen_2015.json"
)


@pytest.mark.skipif(not _CHEN_JSON.exists(), reason="gitignored batch output absent (e.g. CI)")
def test_protocol_faithful_chen_fixture():
    # 8. real chen_2015 spec: reason-partitioned header (5 specified · 3 not reported ·
    # 1 unmappable · 8 not covered), 0 inferred, 0 deferred. The 8 not_covered fields are
    # extractor-coverage, NOT source absence (the core honesty fix).
    data = json.loads(_CHEN_JSON.read_text())
    prep = parse_any_version(data["preprocessing"])  # 0.4.x batch output -> migrate to 0.5.0
    out = render.to_protocol(prep, source="chen_2015")
    assert out.count("[from paper]") == 5
    assert "[INFERRED" not in out
    assert (
        "Completeness: 5 specified in source · 3 not reported in source · "
        "1 reported but unmappable to controlled vocabulary · 8 not covered by extractor"
    ) in out
    # Field-level callouts use "not examined by the extractor"; the COBIDAS section uses
    # distinct row-level wording, so the plain global count is exactly the 8 per-field callouts.
    assert out.count("not examined by the extractor") == 8  # coverage gap, not absence
    assert out.count("map manually") == 1  # value_not_in_literal
    # multi-step pipeline order preserved
    assert (
        out.index("### 1. spatial_normalization")
        < out.index("### 2. surface_projection")
        < out.index("### 3. intensity_normalization")
        < out.index("### 4. temporal_standardization")
    )


@pytest.mark.skipif(not _CHEN_JSON.exists(), reason="gitignored batch output absent (e.g. CI)")
def test_cobidas_coverage_chen_fixture() -> None:
    from extractor_mvp.cobidas import assess_coverage

    prep = parse_any_version(
        json.loads(_CHEN_JSON.read_text())["preprocessing"]
    )  # migrate 0.4.x->0.5.0
    rows = render.flatten(prep)
    vr = next((r for r in rows if r.path == "base_pipeline.version"), None)
    cov = assess_coverage(rows, vr.extraction_status if vr else None)

    # Exactly two D.3 rows are addressed by chen: intersubject registration (target_surface /
    # surface_registration EXTRACTED) and intensity normalization (EXTRACTED but NON-mandatory).
    addressed = {rc.row.row_id for rc in cov if rc.addressed}
    assert addressed == {"intersubject_registration", "intensity_normalization"}
    inten = next(rc for rc in cov if rc.row.row_id == "intensity_normalization")
    assert inten.addressed and not inten.row.mandatory
    # Software (unconditional) is unaddressed -> the one true COBIDAS violation.
    assert next(rc for rc in cov if rc.row.row_id == "software").addressed is False

    out = render.to_cobidas_coverage(prep)
    # Partitioned summary — the denominator is what AESPA can assess, not a raw / 16.
    assert "Mandatory rows: 14" in out
    assert "Assessed by AESPA: 2  →  addressed 1 · not reported 1" in out
    assert "Software — unconditional violation" in out
    assert "Not assessed by AESPA: 12" in out
    assert "Non-mandatory rows: 2 (1 addressed)" in out
    assert "Software: version and revision number NOT REPORTED" in out
    assert "Connectome Computation System (CCS)" in out  # pipeline named in the violation
    # divergence step (temporal_standardization) is beyond COBIDAS, never in the denominator
    assert "### Beyond COBIDAS (AESPA extensions)" in out
