"""The checking pass (DESIGN_report_v2.md §3, ratified 2026-10-29). Offline: the stub serves the
VerifierExtraction. Every assertion is about the record and the rendered report."""

from __future__ import annotations

from typing import Any

from conftest import stub_client
from extractor_mvp import render
from extractor_mvp.coverage_extractor import SpatialExtraction, TemporalVolumeExtraction
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.verifier import (
    VERIFIER_PROMPT,
    FieldVerdict,
    SoftwareVerdict,
    VerifierExtraction,
    compact_draft,
)

TEXT = (
    "Structural images were registered and resampled to an isotropic standard space. "
    "Images were smoothed with a 6 mm FWHM Gaussian kernel. "
    "No slice-timing correction was applied. "
    "Statistics were computed in R version 4.1.0. "
    "Two preprocessing variants were compared: with and without global signal regression (n = 2). "
    "Task and rest data were preprocessed separately in two branches."
)
_SMOOTH = "Images were smoothed with a 6 mm FWHM Gaussian kernel."


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _ex(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _prep_payload(**kw: Any) -> PreprocessingExtraction:
    base = dict(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    base.update(kw)
    return PreprocessingExtraction(**base)


def _run(verifier: Any = None, counter: dict | None = None, **kw: Any) -> tuple[Any, dict, str]:
    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    out: list[Any] = []
    prep, _, _ = extract(
        paper,
        "m",
        client=stub_client(
            _prep_payload(**kw.pop("shared", {})),
            spatial=SpatialExtraction(**kw.pop("spatial", {})),
            temporal=TemporalVolumeExtraction(**kw.pop("temporal", {})),
            verifier=verifier,
            counter=counter,
        ),
        verifier_out=out,
    )
    record = out[0]
    report = render.to_report(
        prep, source="t", verifier=record, multiple_pipelines=record.get("multiple_pipelines")
    )
    return prep, record, report


def test_one_more_call_and_never_without_a_caller_asking() -> None:
    counter: dict[str, int] = {}
    _run(counter=counter)
    assert counter["VerifierExtraction"] == 1
    counter2: dict[str, int] = {}
    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    extract(paper, "m", client=stub_client(_prep_payload(), counter=counter2))
    assert "VerifierExtraction" not in counter2


def test_the_draft_carries_full_quotes_and_omits_untargeted_fields() -> None:
    prep, _, _ = _run(
        spatial={"smoothing_performed": _ex("yes", _SMOOTH), "smoothing_fwhm_mm": _ex("6", _SMOOTH)}
    )
    draft = compact_draft(prep)
    assert f'spatial_smoothing.fwhm_mm | extracted | 6.0 | quote: "{_SMOOTH}"' in draft
    assert "not_targeted_by_mvp" not in draft
    assert "{text}" in VERIFIER_PROMPT and "{draft}" in VERIFIER_PROMPT


def test_wrong_demotes_the_value_to_a_flag_and_never_replaces_it() -> None:
    struct = "Structural images were registered and resampled to an isotropic standard space."
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_normalization.target_space",
                verdict="wrong",
                reason="the sentence is about the structural image",
                relied_on=struct,
                better_value="not reported",
            ),
            FieldVerdict(field="spatial_smoothing.fwhm_mm", verdict="supported", relied_on=_SMOOTH),
        ]
    )
    prep, _record, report = _run(
        verifier=verdict,
        shared={"target_space": _ex("isotropic standard space", struct)},
        spatial={
            "smoothing_performed": _ex("yes", _SMOOTH),
            "smoothing_fwhm_mm": _ex("6", _SMOOTH),
        },
    )
    # the extraction arm is untouched
    ts = next(s for s in prep.steps if s.kind == "spatial_normalization").target_space
    assert ts.extraction.status == "EXTRACTED"
    assert ts.extraction.value.verbatim == "isotropic standard space"
    line = next(ln for ln in report.splitlines() if ln.startswith("- ⚑ target_space"))
    assert '"isotropic standard space"' in line
    assert (
        "checking pass: WRONG — the sentence is about the structural image; should be: not reported"
        in line
    )
    assert "- fwhm_mm = 6.0   [from paper]" in report and "[check: supported]" in report
    assert (
        "Intersubject registration [validated against labels] — flagged by the checking pass"
        in report
    )
    assert "Checking pass (unvalidated" in report and "wrong 1" in report


def test_missed_names_what_the_paper_states_and_fills_nothing() -> None:
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.fwhm_mm",
                verdict="missed",
                reason="the kernel is stated",
                relied_on=_SMOOTH,
                better_value="6",
            )
        ]
    )
    prep, _, report = _run(verifier=verdict)
    fwhm = next(s for s in prep.steps if s.kind == "spatial_smoothing").fwhm_mm
    assert fwhm.extraction.status == "MISSING_FROM_PAPER"
    assert "checking pass: MISSED — the paper states: 6 «Images were smoothed" in report
    assert "[missed per the checking pass: fwhm_mm]" in report


def test_a_verdict_whose_sentence_does_not_resolve_has_no_effect() -> None:
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.fwhm_mm",
                verdict="wrong",
                reason="x",
                relied_on="a sentence nowhere in the text",
            )
        ]
    )
    _, _, report = _run(
        verifier=verdict,
        spatial={
            "smoothing_performed": _ex("yes", _SMOOTH),
            "smoothing_fwhm_mm": _ex("6", _SMOOTH),
        },
    )
    assert "- ⚑ fwhm_mm" not in report
    assert "[check: unverified verdict — its sentence did not resolve]" in report
    assert "flagged by the checking pass" not in report


def test_a_failing_verifier_never_fails_the_paper() -> None:
    class Boom:
        def __init__(self) -> None:
            from types import SimpleNamespace

            self.inner = stub_client(_prep_payload())
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, *, response_model: Any = None, **kw: Any) -> Any:
            if response_model is VerifierExtraction:
                raise RuntimeError("transport down")
            return self.inner.chat.completions.create(response_model=response_model, **kw)

    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    out: list[Any] = []
    prep, _, _ = extract(paper, "m", client=Boom(), verifier_out=out)
    assert out[0]["status"] == "unavailable" and "transport down" in out[0]["error"]
    report = render.to_report(prep, source="t", verifier=out[0])
    assert "Checking pass: unavailable — no field was checked" in report


def test_multiple_pipelines_is_asked_nowhere_now() -> None:
    """2026-11-11 (DESIGN_applies_to.md, fork F1): the record-level question is gone from the checking
    pass, as it left the coverage calls on 2026-10-29 (F3a); a record's variants are read off its
    values (tests/test_applies_to.py). A stored answer still renders (the same file)."""
    _, record, report = _run()
    assert record["multiple_pipelines"] is None
    assert "More than one preprocessing variant" not in report
    assert "multiple_pipelines" not in VERIFIER_PROMPT
    assert "multiple_pipelines" not in VerifierExtraction.model_fields
    assert "multiple_pipelines" not in SpatialExtraction.model_fields
    assert "multiple_pipelines" not in TemporalVolumeExtraction.model_fields


def test_software_the_checking_pass_marks_not_preprocessing_is_shown_not_counted() -> None:
    from extractor_mvp.coverage_extractor import SoftwareMentionResult

    r = SoftwareMentionResult(
        name="R", version="4.1.0", verbatim_quote="Statistics were computed in R version 4.1.0."
    )
    _, _, report = _run(
        verifier=VerifierExtraction(software=[SoftwareVerdict(name="R", preprocessing_use=False)]),
        spatial={"software_mentions": [r]},
    )
    assert "not counted, not preprocessing per the checking pass: r" in report


_MOTION_FILTER = "Task and rest data were preprocessed separately in two branches."


def test_unplaced_lists_what_no_field_captured_and_changes_no_field() -> None:
    """2026-11-02, the author's item 2: an `unplaced` list, each statement with its quote-checked
    sentence and its D.3 row or "no row"; its own section; never a field change."""
    from extractor_mvp.verifier import UnplacedStatement

    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(field="spatial_smoothing.fwhm_mm", verdict="supported", relied_on=_SMOOTH)
        ],
        unplaced=[
            UnplacedStatement(
                statement="separate task and rest branches",
                relied_on=_MOTION_FILTER,
                row="no row",
            ),
            UnplacedStatement(
                statement="a 6 mm kernel", relied_on=_SMOOTH, row="spatial_smoothing"
            ),
            UnplacedStatement(
                statement="a filter on the motion estimates",
                relied_on="The motion estimates were band-stop filtered.",  # not in the text
                row="artifact_and_noise",  # not a D.3 row id
            ),
        ],
    )
    baseline, _, _ = _run(spatial={"smoothing_performed": _ex("yes", _SMOOTH)})
    prep, record, report = _run(
        verifier=verdict, spatial={"smoothing_performed": _ex("yes", _SMOOTH)}
    )
    # never changes a field: the record's preprocessing equals the run without the list
    assert prep.model_dump(mode="json") == baseline.model_dump(mode="json")
    u = record["unplaced"]
    assert [x["row"] for x in u] == ["no row", "spatial_smoothing", "no row"]
    assert [x["relied_on_resolved"] for x in u] == [True, True, False]
    assert u[2]["row_raw"] == "artifact_and_noise"
    section = report.split(
        "## Preprocessing statements no field captured (checking pass, unvalidated)"
    )[1]
    section = section.split("\n## ")[0]
    assert "- separate task and rest branches — no D.3 row  «Task and rest data" in section
    assert "- a 6 mm kernel — row: Spatial smoothing  «Images were smoothed" in section
    assert (
        "- a filter on the motion estimates — no D.3 row  «The motion estimates were band-stop "
        "filtered.»  (its sentence was not found in the text — unverified)" in section
    )
    # the section sits before the coverage and the rows are untouched
    assert report.index("no field captured") < report.index("## COBIDAS D.3 coverage")
    # the prompt asks for it, with the D.3 row ids
    assert "unplaced: a list of the preprocessing statements" in VERIFIER_PROMPT
    assert "{rows}" in VERIFIER_PROMPT


def test_an_empty_unplaced_list_says_none_and_an_old_record_has_no_section() -> None:
    _, record, report = _run(verifier=VerifierExtraction())
    assert record["unplaced"] == []
    assert "The checking pass lists none." in report
    old = dict(record)
    old.pop("unplaced")
    assert render._unplaced_section(old) == []


def test_an_order_verdict_proposing_the_current_order_is_dropped() -> None:
    """2026-11-02, the author's ruling: an order verdict whose proposal equals the current order is
    dropped in code. shen_2013's shape: the draft lists every kind, the proposal lists the performed
    ones in the same relative order."""
    from extractor_mvp.verifier import drop_same_order_verdict, same_order

    kinds = ["motion_correction", "slice_time_correction", "spatial_smoothing", "despike"]
    assert same_order("motion_correction, slice_time_correction, spatial_smoothing", kinds)
    assert same_order("motion correction -> slice-time correction", kinds)
    assert not same_order("slice_time_correction, motion_correction", kinds)  # a real reorder
    assert not same_order("motion_correction, realignment", kinds)  # a token not in the draft
    assert not same_order("motion_correction, motion_correction", kinds)
    assert not same_order("", kinds) and not same_order(None, kinds)

    prep, record, _ = _run(
        spatial={"smoothing_performed": _ex("yes", _SMOOTH), "smoothing_fwhm_mm": _ex("6", _SMOOTH)}
    )
    current = ", ".join(s.kind for s in prep.steps[:3])
    reversed_ = ", ".join(s.kind for s in reversed(prep.steps[:3]))

    def with_order(better: str) -> dict[str, Any]:
        v = {"verdict": "wrong", "reason": "r", "relied_on": _SMOOTH, "relied_on_resolved": True}
        fields = {**record["fields"], "step_order": {**v, "better_value": better}}
        return {**record, "fields": fields}

    kept = drop_same_order_verdict(with_order(reversed_), prep)
    dropped = drop_same_order_verdict(with_order(current), prep)
    assert "step_order" in kept["fields"] and "dropped_same_order" not in kept
    assert "step_order" not in dropped["fields"] and dropped["dropped_same_order"] is True
    # a record stored before the ruling renders without the verdict
    report = render.to_report(prep, source="t", verifier=with_order(current))
    assert "wrong 0" in report
    assert "· order verdict dropped (its proposal is the current order)" in report
    report = render.to_report(prep, source="t", verifier=with_order(reversed_))
    assert "wrong 1" in report


def test_the_checking_pass_reads_the_text_it_is_given_and_says_which() -> None:
    # fix 1a (2026-11-05): on a suspicious slice the caller passes the full text; the sentences
    # resolve against it, and the record says what was read
    full = TEXT + " Head motion was corrected with MCFLIRT."
    seen: list[str] = []
    v = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.performed",
                verdict="missed",
                relied_on="Head motion was corrected with MCFLIRT.",
            )
        ]
    )
    paper = ParsedPaper(text=TEXT, source="t", parser="manual")
    out: list[Any] = []
    from types import SimpleNamespace

    inner = stub_client(_prep_payload(), verifier=v)

    def create(**kw: Any) -> Any:
        if kw.get("response_model") is VerifierExtraction:
            seen.append(kw["messages"][0]["content"])
        return inner.chat.completions.create(**kw)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    extract(paper, "m", client=client, verifier_out=out, verifier_text=full)
    assert out[0]["read"] == "full_text"
    assert out[0]["fields"]["spatial_smoothing.performed"]["relied_on_resolved"] is True
    assert any("MCFLIRT" in p for p in seen)
    out2: list[Any] = []
    extract(paper, "m", client=stub_client(_prep_payload(), verifier=v), verifier_out=out2)
    assert out2[0]["read"] == "methods_slice"
    assert out2[0]["fields"]["spatial_smoothing.performed"]["relied_on_resolved"] is False


def _header(report: str) -> str:
    return next(ln for ln in report.splitlines() if ln.startswith("  Assessed by AESPA:"))


def test_a_flagged_row_counts_as_flagged_never_as_addressed_in_the_header() -> None:
    # fix 1c (2026-11-05)
    struct = "Structural images were registered and resampled to an isotropic standard space."
    wrong = FieldVerdict(
        field="spatial_normalization.target_space",
        verdict="wrong",
        relied_on=struct,
        better_value="not reported",
    )
    kw: dict[str, Any] = {
        "shared": {"target_space": _ex("isotropic standard space", struct)},
        "spatial": {"smoothing_performed": _ex("yes", _SMOOTH)},
    }
    _, _, plain = _run(verifier=VerifierExtraction(), **dict(kw))
    _, _, flagged = _run(verifier=VerifierExtraction(fields=[wrong]), **dict(kw))
    assert "flagged" not in _header(plain)
    n = int(_header(plain).split("addressed ", 1)[1].split(" ", 1)[0])
    assert f"addressed {n - 1} · flagged 1 · " in _header(flagged)
    nr = _header(plain).split("not reported ", 1)[1].split(" ", 1)[0]
    assert f"not reported {nr}" in _header(flagged)  # the flagged row is not moved there either
    # an unresolved sentence is an unverified verdict: no effect, so not flagged
    unresolved = wrong.model_copy(update={"relied_on": "Not a sentence of the paper."})
    _, _, unverified = _run(verifier=VerifierExtraction(fields=[unresolved]), **dict(kw))
    assert _header(unverified) == _header(plain)


def test_a_row_with_one_supported_field_is_not_flagged() -> None:
    wrong = FieldVerdict(field="spatial_smoothing.performed", verdict="wrong", relied_on=_SMOOTH)
    ok = FieldVerdict(field="spatial_smoothing.fwhm_mm", verdict="supported", relied_on=_SMOOTH)
    spatial = {"smoothing_performed": _ex("yes", _SMOOTH), "smoothing_fwhm_mm": _ex("6", _SMOOTH)}
    _, _, report = _run(verifier=VerifierExtraction(fields=[wrong, ok]), spatial=spatial)
    assert "flagged" not in _header(report)
    _, _, both = _run(
        verifier=VerifierExtraction(fields=[wrong, ok.model_copy(update={"verdict": "wrong"})]),
        spatial=spatial,
    )
    assert "flagged 1 · " in _header(both)
    assert (
        "Spatial smoothing [validated against labels (diagnostic, 14 papers)] — flagged by the checking pass"
        in both
    )


def test_a_flagged_software_row_claims_no_violation_in_the_header() -> None:
    # fix 1c (2026-11-05): Gao_2026's Software row was flagged and still carried the violation label
    stats = "Statistics were computed in R version 4.1.0."
    kw: dict[str, Any] = {"shared": {"base_pipeline_name": _ex("R", stats)}}
    _, _, plain = _run(verifier=VerifierExtraction(), **dict(kw))
    wrong = FieldVerdict(field="base_pipeline", verdict="wrong", relied_on=stats)
    _, _, flagged = _run(verifier=VerifierExtraction(fields=[wrong]), **dict(kw))
    if "Software [validated against labels] — flagged" not in flagged:
        raise AssertionError("the Software row is not flagged: the test's premise failed")
    assert "Software — unconditional violation" in _header(plain)
    assert "flagged 1 · " in _header(flagged)
    assert "unconditional violation" not in _header(flagged)


# --- 2026-11-05: Ladouceur_2023's checking pass (stress_v1) ---------------------------------------


def test_a_verdict_list_sent_as_a_json_string_is_read_as_the_list() -> None:
    import json

    row = {"field": "spatial_smoothing.performed", "verdict": "supported"}
    v = VerifierExtraction.model_validate({"fields": json.dumps([row]), "unplaced": "[]"})
    assert [f.field for f in v.fields] == ["spatial_smoothing.performed"] and v.unplaced == []
    # a string that is not a JSON list is still rejected, never guessed at
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VerifierExtraction.model_validate({"fields": '[{"field": "x", "verdict": ""broken"}]'})


def test_the_checking_pass_reads_no_double_quote_and_its_sentences_still_resolve() -> None:
    quoted = 'The data were "scrubbed" at 0.5 mm. ' + TEXT
    seen: list[str] = []
    v = VerifierExtraction(
        fields=[
            FieldVerdict(
                field="spatial_smoothing.performed",
                verdict="missed",
                relied_on="The data were 'scrubbed' at 0.5 mm.",
            )
        ]
    )
    from types import SimpleNamespace

    inner = stub_client(_prep_payload(), verifier=v)

    def create(**kw: Any) -> Any:
        if kw.get("response_model") is VerifierExtraction:
            seen.append(kw["messages"][0]["content"])
        return inner.chat.completions.create(**kw)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    out: list[Any] = []
    extract(
        ParsedPaper(text=quoted, source="t", parser="manual"), "m", client=client, verifier_out=out
    )
    body = seen[0].split('Methods text:\n"""', 1)[1].split('"""', 1)[0]
    assert '"scrubbed"' not in body and "'scrubbed'" in body
    assert out[0]["fields"]["spatial_smoothing.performed"]["relied_on_resolved"] is True


def test_the_draft_s_quotes_carry_no_double_quote() -> None:
    sent = 'Images were smoothed with a "6 mm" FWHM Gaussian kernel.'
    paper = ParsedPaper(text=sent + " " + TEXT, source="t", parser="manual")
    prep, _, _ = extract(
        paper,
        "m",
        client=stub_client(
            _prep_payload(), spatial=SpatialExtraction(smoothing_fwhm_mm=_ex("6", sent))
        ),
    )
    line = next(
        ln for ln in compact_draft(prep).splitlines() if ln.startswith("spatial_smoothing.fwhm_mm")
    )
    assert "'6 mm'" in line and '"6 mm"' not in line


def test_a_missed_verdict_on_the_base_pipeline_names_it_on_the_software_row() -> None:
    # stress_v2 (2026-11-05): Silchenko_2023's checking pass marked base_pipeline missed; the per-row
    # section took the text after a dot that path does not have and raised IndexError
    missed = FieldVerdict(
        field="base_pipeline",
        verdict="missed",
        relied_on="Statistics were computed in R version 4.1.0.",
        better_value="R",
    )
    _, _, report = _run(
        verifier=VerifierExtraction(fields=[missed]),
        spatial={"smoothing_performed": _ex("yes", _SMOOTH)},
    )
    row = next(ln for ln in report.splitlines() if ln.startswith("- Software ["))
    assert "[missed per the checking pass: base_pipeline]" in row
