"""scripts/term_audit.py: the standing audit of vocabulary terms in stored records (B12; D2b)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import term_audit as ta


def _term(verbatim: str, resolved: str | None) -> dict[str, Any]:
    return {
        "verbatim": verbatim,
        "resolved": resolved,
        "resolution": "resolved" if resolved else "unrecognized",
    }


def _span(text: str, start: int, key: str = "span_in_full_paper") -> dict[str, Any]:
    return {"start": 0, "end": len(text), "text": text, key: {"start": start, "end": start + 1}}


def _step(kind: str, **fields: tuple[Any, list[dict[str, Any]]]) -> dict[str, Any]:
    step: dict[str, Any] = {"kind": kind}
    for field_id, (value, spans) in fields.items():
        step[field_id] = {
            "field_id": field_id,
            "extraction": {"status": "EXTRACTED", "value": value, "spans": spans},
        }
    return step


def _write(root: Path, paper: str, *steps: dict[str, Any]) -> None:
    (root / "papers").mkdir(parents=True, exist_ok=True)
    (root / "papers" / f"{paper}.json").write_text(
        json.dumps({"preprocessing": {"steps": list(steps)}}), encoding="utf-8"
    )


def test_the_tables_pass_their_self_check() -> None:
    checked, failures = ta.self_check()
    assert checked >= 448 and failures == []


def test_the_vocabulary_is_35_coverage_fields_and_4_shared() -> None:
    fields = ta.vocabulary().values()
    assert sum(not f.shared for f in fields) == 35 and sum(f.shared for f in fields) == 4


def test_spans_are_joined_in_text_order_not_stored_order() -> None:
    spans = [
        _span("Images were then slice-time corrected.", 900),
        _span("Images were realigned.", 100),
        _span("A supplement sentence.", 5, key="span_in_supplement"),
        _span("A sentence located in the methods slice only.", 500, key="span_in_slice"),
    ]
    assert ta.quote_in_text_order(spans) == ta.SPAN_JOIN.join(
        [
            "Images were realigned.",
            "A sentence located in the methods slice only.",
            "Images were then slice-time corrected.",
            "A supplement sentence.",
        ]
    )


def test_the_token_trace_sorts_a_token_by_what_its_quote_holds(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "paper_a",
        _step(
            "temporal_filtering",
            # the member's alias is in the quote
            pass_type=(
                _term("band_pass", "band_pass"),
                [_span("data were band-pass filtered", 10)],
            ),
            # no alias of the member in the quote: an inference from order, or a forced token
            relative_to_regression=(
                _term("before", "before"),
                [_span("filtered, and nuisance signals were regressed", 50)],
            ),
        ),
        _step(
            "coregistration",
            # an alias of a member the record did not return stands beside the member's own
            method=(
                _term("flirt", "flirt"),
                [_span("registered with FLIRT; bbregister refined the alignment", 80)],
            ),
        ),
    )
    a = ta.audit([tmp_path])
    assert a.trace["temporal_filtering.pass_type"]["in quote"] == 1
    assert a.trace["temporal_filtering.relative_to_regression"]["not in quote"] == 1
    assert a.trace["coregistration.method"]["competing"] == 1
    assert sorted((c[0], c[2], c[3]) for c in a.trace_cases) == [
        ("coregistration.method", "flirt", "competing"),
        ("temporal_filtering.relative_to_regression", "before", "not in quote"),
    ]
    # the listed tokens carry their quote only when asked for
    with_quotes = ta.render(a, [tmp_path], quotes=True)
    assert "bbregister refined the alignment" in with_quotes
    assert "| field | paper | token | trace | quote |" in with_quotes
    without = ta.render(a, [tmp_path])
    assert "bbregister refined the alignment" not in without
    assert "| coregistration.method | paper_a | flirt | competing |" in without


def test_the_token_s_own_member_today_is_what_the_trace_grades(tmp_path: Path) -> None:
    # stored before the ruling that sends the token volterra to friston24 (2026-10-28): the
    # stored member has no alias anywhere, and today's member is the one the quote names
    _write(
        tmp_path / "a",
        "paper_a",
        _step(
            "nuisance_regression",
            motion_expansion=(
                _term("volterra", "volterra"),
                [_span("a Volterra expansion of the motion parameters", 1)],
            ),
        ),
    )
    c = ta.audit([tmp_path / "a"]).trace["nuisance_regression.motion_expansion"]
    assert (c["in quote"], c["not in quote"], c["competing"]) == (1, 0, 0)
    # the other item of the list was left unresolved by an older resolver; today it is the member
    # the quote names beside the token's own, so it is not a competitor
    value = [_term("white_matter", "white_matter"), _term("CSF", None)]
    quote = [_span("white matter and CSF signals were regressed", 10)]
    _write(
        tmp_path / "b", "paper_b", _step("nuisance_regression", tissue_regressors=(value, quote))
    )
    c = ta.audit([tmp_path / "b"]).trace["nuisance_regression.tissue_regressors"]
    assert (c["values"], c["in quote"], c["competing"]) == (2, 1, 0)
    # the other way round: the other item holds a stored member that today's resolver no longer
    # gives its words ("white" alone); the record holds that member all the same
    value = [_term("ventricles", "ventricles"), _term("white", "white_matter")]
    _write(
        tmp_path / "c", "paper_c", _step("nuisance_regression", tissue_regressors=(value, quote))
    )
    c = ta.audit([tmp_path / "c"]).trace["nuisance_regression.tissue_regressors"]
    assert (c["values"], c["in quote"], c["competing"]) == (2, 1, 0)


def test_the_detrend_field_is_resolved_as_the_extractor_resolves_it(tmp_path: Path) -> None:
    """The extractor resolves the term, then takes the highest order its quote names (2026-10-28).
    The audit had re-run the first step only and called such a value stale."""
    field = "nuisance_regression.detrend"
    quote = [_span("Linear and quadratic trends were removed.", 80)]
    _write(
        tmp_path / "a",
        "paper_a",
        _step("nuisance_regression", detrend=(_term("linear, quadratic", "quadratic"), quote)),
    )
    a = ta.audit([tmp_path / "a"])
    row = a.wordings[(field, "linear, quadratic", "quadratic")]
    assert row["stale"] == set() and row["flags"] == ["by rule"]
    # a token below the highest order the quote names: the rule moved the member, and the trace
    # lists the token for reading whatever member the record holds
    _write(
        tmp_path / "b",
        "paper_b",
        _step("nuisance_regression", detrend=(_term("linear", "quadratic"), quote)),
    )
    b = ta.audit([tmp_path / "b"])
    row = b.wordings[(field, "linear", "quadratic")]
    assert row["stale"] == set() and row["flags"] == ["token", "sent elsewhere"]
    assert b.trace[field] == {"values": 1, "competing": 1}
    # a token at the highest order: the lower order named beside it is no competitor
    _write(
        tmp_path / "b2",
        "paper_b2",
        _step("nuisance_regression", detrend=(_term("quadratic", "quadratic"), quote)),
    )
    assert ta.audit([tmp_path / "b2"]).trace[field] == {"values": 1, "in quote": 1}
    # a record from before the rule is stale, and says what it stored
    _write(
        tmp_path / "c",
        "paper_c",
        _step("nuisance_regression", detrend=(_term("linear", "linear"), quote)),
    )
    assert ta.audit([tmp_path / "c"]).wordings[(field, "linear", "quadratic")]["stale"] == {
        "linear"
    }
    # a part of a varied value is not moved: the extractor applies the rule to an extracted one
    step = {
        "kind": "nuisance_regression",
        "detrend": {
            "field_id": "detrend",
            "extraction": {
                "status": "VARIED",
                "variants": [
                    {"value": _term("linear", "linear"), "spans": quote, "applies_to": "rest"}
                ],
            },
        },
    }
    _write(tmp_path / "d", "paper_d", step)
    assert ta.audit([tmp_path / "d"]).wordings[(field, "linear", "linear")]["stale"] == set()
    # control: a quote that names no higher order leaves the member as resolved
    plain = [_span("Linear trends were removed.", 80)]
    _write(
        tmp_path / "e",
        "paper_e",
        _step("nuisance_regression", detrend=(_term("linear", "linear"), plain)),
    )
    assert ta.audit([tmp_path / "e"]).wordings[(field, "linear", "linear")]["stale"] == set()
    # a value the checking pass supplied goes through the rule too, since D2c (C14): a record
    # made before that holds the member the words gave, and is stale against today's rule
    supplied = _step("nuisance_regression", detrend=(_term("linear", "linear"), quote))
    supplied["detrend"]["extraction"]["checker_supplied"] = True
    _write(tmp_path / "f", "paper_f", supplied)
    assert ta.audit([tmp_path / "f"]).wordings[(field, "linear", "quadratic")]["stale"] == {
        "linear"
    }
    # the quote is the spans as stored, joined by one space, as the extractor joins them: the
    # order phrase runs over two spans whose stored order is not their order in the text
    split = [_span("Data were detrended with a second-order", 60), _span("polynomial.", 10)]
    _write(
        tmp_path / "g",
        "paper_g",
        _step("nuisance_regression", detrend=(_term("detrended", "quadratic"), split)),
    )
    row = ta.audit([tmp_path / "g"]).wordings[(field, "detrended", "quadratic")]
    assert row["stale"] == set() and row["flags"] == ["by rule"]


def test_the_detrend_rule_raises_a_member_and_never_lowers_it() -> None:
    from extractor_mvp.coverage_extractor import detrend_highest_order

    both = "Linear and quadratic trends were removed."
    assert detrend_highest_order("linear", both) == "quadratic"
    assert detrend_highest_order(None, both) == "quadratic"
    assert detrend_highest_order("quadratic", both) == "quadratic"
    # the quote names a lower order than the resolved one: the member stays
    assert detrend_highest_order("quadratic", "A linear trend was removed.") == "quadratic"
    assert detrend_highest_order("linear", "The data were detrended.") == "linear"
    assert detrend_highest_order(None, "The data were detrended.") is None


def test_an_spm_release_in_the_quote_holds_the_spm_member(tmp_path: Path) -> None:
    """D1 found the tokens of maheu_2011, shen_2013 and agtzidis_2020 coded "not in quote": their
    quotes name SPM by its release."""
    _write(
        tmp_path,
        "paper_a",
        _step(
            "spatial_smoothing",
            method=(
                _term("spm_smooth", "spm_smooth"),
                [_span("Images were smoothed in SPM12 with an 8 mm kernel.", 10)],
            ),
        ),
        _step(
            "nuisance_regression",
            # the release alone, in the slot for the paper's words: resolved by the rule
            method=(_term("SPM12", "spm"), [_span("Regression was run in SPM12.", 90)]),
        ),
    )
    a = ta.audit([tmp_path])
    assert a.trace["spatial_smoothing.method"] == {"values": 1, "in quote": 1}
    assert a.wordings[("nuisance_regression.method", "SPM12", "spm")]["flags"] == ["by rule"]


def test_a_list_competes_only_with_members_it_did_not_return(tmp_path: Path) -> None:
    value = [_term("white_matter", "white_matter"), _term("ventricles", "ventricles")]
    own = [_span("white matter and CSF signals were regressed", 10)]
    _write(tmp_path / "a", "paper_a", _step("nuisance_regression", tissue_regressors=(value, own)))
    c = ta.audit([tmp_path / "a"]).trace["nuisance_regression.tissue_regressors"]
    # each token's quote also holds the other token's alias, which the record returned too
    assert (c["values"], c["in quote"], c["competing"]) == (2, 2, 0)
    more = [_span("white matter, CSF and global signals were regressed", 10)]
    _write(tmp_path / "b", "paper_b", _step("nuisance_regression", tissue_regressors=(value, more)))
    c = ta.audit([tmp_path / "b"]).trace["nuisance_regression.tissue_regressors"]
    # "global signal" is whole_brain's alias, and the record did not return whole_brain
    assert (c["values"], c["in quote"], c["competing"]) == (2, 0, 2)


def test_wordings_are_listed_with_today_s_member_and_their_flags(tmp_path: Path) -> None:
    nothing: list[dict[str, Any]] = []
    for paper in ("paper_a", "paper_b"):
        _write(
            tmp_path,
            paper,
            _step(
                "nuisance_regression",
                motion_expansion=(_term("six motion estimates", None), nothing),
            ),
            _step("brain_extraction", method=(_term("FSL BET v5", "bet"), nothing)),
        )
    _write(
        tmp_path,
        "paper_c",
        _step(
            "nuisance_regression",
            # stored by an older resolver as 6param; today the rule gives 12param (schema 0.8.0)
            motion_expansion=(
                _term("6 parameters and their first order derivatives", "6param"),
                nothing,
            ),
        ),
        _step("brain_extraction", method=(_term("BET", "bet"), nothing)),
        _step(
            "spatial_normalization",
            # no alias spells this token: only the exact-member fallback resolves it
            target_space=(_term("native_volume", "native_volume"), nothing),
        ),
        _step(
            "distortion_correction",
            # a ligature from the text layer: the alias covers the whole wording once repaired
            source=([_term("\ufb01eld map", "susceptibility_fieldmap")], nothing),
        ),
    )
    _write(
        tmp_path,
        "paper_d",
        _step(
            "nuisance_regression",
            motion_expansion=(_term("volterra", "friston24"), nothing),
        ),
        _step(
            "distortion_correction",
            # "other (phrase)" is stored as the phrase alone, with the member other
            method=([_term("unwarping with a field map", "other")], nothing),
        ),
    )
    _write(
        tmp_path,
        "paper_e",
        _step(
            "nuisance_regression",
            # six, derivatives and squares: the field's rule chose the member, not an alias alone
            motion_expansion=(
                _term("six parameters, their derivatives and squares", "friston24"),
                nothing,
            ),
        ),
    )
    a = ta.audit([tmp_path])
    field = "nuisance_regression.motion_expansion"
    unresolved = a.wordings[(field, "six motion estimates", None)]
    assert unresolved["papers"] == {"paper_a", "paper_b"}
    # "partial": the alias covers part of the wording; a whole alias carries no flag
    assert a.wordings[("brain_extraction.method", "FSL BET v5", "bet")]["flags"] == ["partial"]
    assert a.wordings[("brain_extraction.method", "BET", "bet")]["flags"] == []
    stale = a.wordings[(field, "6 parameters and their first order derivatives", "12param")]
    assert stale["stale"] == {"6param"} and stale["flags"] == ["by rule"]
    assert a.wordings[(field, "volterra", "friston24")]["flags"] == ["token", "sent elsewhere"]
    by_rule = "six parameters, their derivatives and squares"
    assert a.wordings[(field, by_rule, "friston24")]["flags"] == ["by rule"]
    # a bare member token on a shared field resolves through the exact-member fallback
    shared = a.wordings[("spatial_normalization.target_space", "native_volume", "native_volume")]
    assert shared["flags"] == ["token"] and shared["stale"] == set()
    ligature = a.wordings[
        ("distortion_correction.source", "\ufb01eld map", "susceptibility_fieldmap")
    ]
    assert ligature["flags"] == [] and ligature["stale"] == set()
    # "other (phrase)" is stored as the phrase; the alias inside it does not claim today's member
    other = a.wordings[("distortion_correction.method", "unwarping with a field map", "other")]
    assert other["stale"] == set() and other["flags"] == []
    text = ta.render(a, [tmp_path])
    # the recurring unresolved wording leads section 3
    section3 = text.split("## 3. Unresolved wordings")[1].split("## 4.")[0]
    first_row = next(ln for ln in section3.splitlines() if ln.startswith("| nuisance"))
    assert "six motion estimates" in first_row and "| 2 |" in first_row
    assert "unwarping with a field map" not in section3
    assert "stale: stored 6param" in text and "sent elsewhere" in text and "by rule" in text


def test_a_held_out_paper_is_counted_and_never_shown(tmp_path: Path) -> None:
    marker = "zzz-held-out-wording"
    quote = [_span(f"a sentence that must not be shown, with {marker}", 10)]
    # the id anywhere in the file name, whatever its case, prefix or suffix
    for name in ("liu_2005", "B_Tang_2025", "WHEATON_2004_suppl"):
        _write(
            tmp_path,
            name,
            _step("brain_extraction", method=(_term(marker, None), quote)),
            _step("temporal_filtering", relative_to_regression=(_term("before", "before"), quote)),
        )
    _write(
        tmp_path,
        "paper_a",
        _step("brain_extraction", method=(_term("optiBET", None), [_span("optiBET was used", 1)])),
    )
    a = ta.audit([tmp_path])
    assert a.held_out == {"terms": 6, "tokens": 3, "unresolved": 3, "not in quote": 3}
    assert all(not ta.is_held_out(paper) for _f, paper, *_rest in a.trace_cases)
    text = ta.render(a, [tmp_path], quotes=True)
    assert marker not in text and "must not be shown" not in text
    for held in ("liu_2005", "tang_2025", "wheaton_2004"):
        assert held not in text.lower()
    assert "optiBET" in text and "paper_a" in text  # control: a development paper is shown
    assert "Terms 6; bare tokens 3; unresolved today 3" in text


def test_the_shared_fields_use_the_sibling_value(tmp_path: Path) -> None:
    quote = [_span("grand-mean scaling to 10000", 5)]
    step = _step(
        "intensity_normalization",
        convention=(_term("grand mean scaling", None), quote),
        value=(10000.0, quote),
    )
    _write(tmp_path / "a", "paper_a", step)
    a = ta.audit([tmp_path / "a"])
    key = ("intensity_normalization.convention", "grand mean scaling", "fsl_grand_mean_10000")
    assert a.wordings[key]["stale"] == {"None"}
    # a shared field has no field rules: the gated alias is the whole wording, so no flag
    assert a.wordings[key]["flags"] == []
    # the value failed its own check and was not stored: the stored member tells which value the
    # extractor resolved the convention with
    step = _step(
        "intensity_normalization",
        convention=(_term("grand mean scaling", "fsl_grand_mean_10000"), quote),
    )
    _write(tmp_path / "b", "paper_b", step)
    b = ta.audit([tmp_path / "b"])
    assert b.wordings[key]["stale"] == set()


def test_the_trace_reads_a_quote_as_the_resolver_reads_a_value(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "paper_a",
        _step(
            "slice_time_correction",
            # "slice" is specific_slice's alias, inside the longer "middle slice"
            reference=(
                _term("middle", "middle"),
                [_span("the middle slice was the reference", 1)],
            ),
        ),
        _step(
            "nuisance_regression",
            # the resolver blocks 6param on a quote that names derivatives: a forced token
            motion_expansion=(
                _term("6param", "6param"),
                [_span("six motion parameters and their temporal derivatives", 1)],
            ),
        ),
    )
    _write(
        tmp_path,
        "paper_b",
        _step(
            "nuisance_regression",
            # no alias of friston24 is here; the field's rule names it (six, derivatives, squares)
            motion_expansion=(
                _term("friston24", "friston24"),
                [_span("six parameters, their derivatives and the squares of both", 1)],
            ),
        ),
    )
    _write(
        tmp_path,
        "paper_c",
        _step(
            "surface_projection",
            # "fsaverage" beside "fsaverage5": the resolver keeps the more specific member only
            target_surface=(
                _term("fsaverage5", "fsaverage5"),
                [_span("data were sampled to fsaverage and then to fsaverage5", 1)],
            ),
        ),
    )
    a = ta.audit([tmp_path])
    assert a.trace["slice_time_correction.reference"]["in quote"] == 1
    assert a.trace["nuisance_regression.motion_expansion"] == {
        "values": 2,
        "not in quote": 1,
        "in quote": 1,
    }
    assert a.trace["surface_projection.target_surface"] == {"values": 1, "in quote": 1}
    assert [(c[1], c[2], c[3]) for c in a.trace_cases] == [("paper_a", "6param", "not in quote")]


def test_the_parts_of_a_varied_field_do_not_compete_with_each_other(tmp_path: Path) -> None:
    quote = [_span("high-pass filtered for task runs and band-pass filtered for rest runs", 1)]
    step = {
        "kind": "temporal_filtering",
        "pass_type": {
            "field_id": "pass_type",
            "extraction": {
                "status": "VARIED",
                "variants": [
                    {
                        "value": _term("high_pass", "high_pass"),
                        "spans": quote,
                        "applies_to": "task",
                    },
                    {
                        "value": _term("band_pass", "band_pass"),
                        "spans": quote,
                        "applies_to": "rest",
                    },
                ],
            },
        },
    }
    _write(tmp_path, "paper_a", step)
    c = ta.audit([tmp_path]).trace["temporal_filtering.pass_type"]
    assert (c["values"], c["in quote"], c["competing"]) == (2, 2, 0)


def test_a_list_item_that_borrowed_its_head_noun_is_flagged(tmp_path: Path) -> None:
    nothing: list[dict[str, Any]] = []
    borrowed = [_term("white", None), _term("gray matter", "gray_matter")]
    alone = [_term("white", None), _term("CSF", "ventricles")]
    _write(tmp_path, "paper_a", _step("nuisance_regression", tissue_regressors=(borrowed, nothing)))
    _write(tmp_path, "paper_b", _step("nuisance_regression", tissue_regressors=(alone, nothing)))
    a = ta.audit([tmp_path])
    field = "nuisance_regression.tissue_regressors"
    # one row per member today, whatever the order the papers are read in
    assert a.wordings[(field, "white", "white_matter")]["flags"] == ["completed"]
    assert a.wordings[(field, "white", "white_matter")]["papers"] == {"paper_a"}
    assert a.wordings[(field, "white", None)]["papers"] == {"paper_b"}


def test_a_member_the_model_mapped_is_not_called_stale(tmp_path: Path) -> None:
    """Schema 0.8.0 (C7): ``model_mapped`` marks a member that is the model's reading of the
    words. The table does not confirm it, and the record is not out of date for that: the audit
    lists the words under the model's member, as an alias candidate. reresolve_terms keeps such a
    term as stored, and the audit said "stale" about the same term (the second review)."""
    mapped = {
        "verbatim": "normalised cross-information",
        "resolved": "mutual_information",
        "resolution": "model_mapped",
    }
    _write(tmp_path, "paper_a", _step("coregistration", cost_function=(mapped, [])))
    # control: the same words stored as a table resolution are out of date
    _write(
        tmp_path,
        "paper_b",
        _step("coregistration", cost_function=(_term("normalised cross-entropy", "ssd"), [])),
    )
    a = ta.audit([tmp_path])
    field = "coregistration.cost_function"
    row = a.model_wordings[(field, "normalised cross-information", "mutual_information")]
    assert row["flags"] == ["the model's member"] and row["stale"] == set()
    assert row["resolution"] == "model_mapped"
    assert (field, "normalised cross-information", "mutual_information") not in a.wordings
    assert a.wordings[(field, "normalised cross-entropy", None)]["stale"] == {"ssd"}
    text = ta.render(a, [tmp_path])
    assert "| normalised cross-information | mutual_information | 1 | the model's member |" in text
    # the trace says what it cannot find
    assert "A member with no alias has none to find: `other`, and the members" in text
    # Where the table resolves the words itself, the row stands under the table's member. A
    # model's member that differs is named, and is not "stale": reresolve_terms keeps it, so that
    # word would never clear. One that agrees leaves no mark.
    other = tmp_path / "other"
    differs = {"verbatim": "mutual information", "resolved": "ssd", "resolution": "model_mapped"}
    agrees = {"verbatim": "BBR", "resolved": "boundary_based", "resolution": "model_mapped"}
    nothing = {"verbatim": "zzz", "resolved": None, "resolution": "model_mapped"}
    _write(other, "paper_c", _step("coregistration", cost_function=(differs, [])))
    _write(other, "paper_d", _step("coregistration", cost_function=(agrees, [])))
    _write(other, "paper_e", _step("coregistration", cost_function=(nothing, [])))
    b = ta.audit([other])
    row = b.wordings[(field, "mutual information", "mutual_information")]
    assert row["model"] == {"ssd"} and row["stale"] == set() and row["flags"] == []
    confirmed = b.wordings[(field, "BBR", "boundary_based")]
    assert confirmed["model"] == set() and confirmed["stale"] == set()
    # a term marked model_mapped that holds no member is an unresolved term like any other
    assert b.wordings[(field, "zzz", None)]["resolution"] == "unrecognized"
    assert "| mutual information | mutual_information | 1 | the model read ssd |" in ta.render(
        b, [other]
    )
    # A member the model mapped to "other" is the model's reading of the paper's words too, not
    # an "other (phrase)" term whose wrapper is lost: where the table resolves the words, the
    # row stands under the table's member (the fourth review).
    third = tmp_path / "third"
    as_other = {"verbatim": "BBR", "resolved": "other", "resolution": "model_mapped"}
    phrase = {"verbatim": "normalised cross-entropy", "resolved": "other", "resolution": "resolved"}
    _write(third, "paper_f", _step("coregistration", cost_function=(as_other, [])))
    _write(third, "paper_g", _step("coregistration", cost_function=(phrase, [])))
    c = ta.audit([third])
    assert c.wordings[(field, "BBR", "boundary_based")]["model"] == {"other"}
    # control: an "other (phrase)" term the table did not write stays under other
    assert (field, "normalised cross-entropy", "other") in c.wordings
    assert c.model_wordings == {}


def test_the_model_s_member_is_a_row_of_its_own(tmp_path: Path) -> None:
    """Two papers hold the same words under the same member. In one the member is the model's
    (``model_mapped``, and the table resolves the words to nothing); in the other the extractor
    or the table reached it. As one row, the flags were those of whichever paper was read first
    (the fifth review): the model's mapping went unflagged, or a table reading was called the
    model's and lost its own flag. Both orders are run."""
    field = "distortion_correction.method"
    nothing: list[dict[str, Any]] = []
    words = "fieldmap-less susceptibility"
    for mapped_paper, plain_paper in (("paper_a", "paper_b"), ("paper_b", "paper_a")):
        root = tmp_path / f"{mapped_paper}_holds_the_model_s"
        # an "other (phrase)" term, and the same words the model mapped to other
        as_other = {
            "verbatim": "in-house unwarping",
            "resolved": "other",
            "resolution": "model_mapped",
        }
        phrase = _term("in-house unwarping", "other")
        _write(root / "o", mapped_paper, _step("distortion_correction", method=(as_other, nothing)))
        _write(root / "o", plain_paper, _step("distortion_correction", method=(phrase, nothing)))
        a = ta.audit([root / "o"])
        key = (field, "in-house unwarping", "other")
        assert a.model_wordings[key]["papers"] == {mapped_paper}
        assert a.model_wordings[key]["flags"] == ["the model's member"]
        assert a.wordings[key]["papers"] == {plain_paper} and a.wordings[key]["flags"] == []
        text = ta.render(a, [root / "o"])
        by_model_row = "| in-house unwarping | other | 1 | the model's member |"
        by_table_row = "| in-house unwarping | other | 1 |  |"
        # both rows, the table's first (one paper each), whichever paper was read first
        assert text.index(by_table_row) < text.index(by_model_row)
        # a list item the table completes, and the same words the model mapped
        by_model = {"verbatim": words, "resolved": "fieldmap_less", "resolution": "model_mapped"}
        completed = [_term(words, None), _term("fieldmap distortion correction", "fieldmap")]
        _write(root / "l", mapped_paper, _step("distortion_correction", method=(by_model, nothing)))
        _write(root / "l", plain_paper, _step("distortion_correction", method=(completed, nothing)))
        b = ta.audit([root / "l"])
        key = (field, words, "fieldmap_less")
        assert b.model_wordings[key]["papers"] == {mapped_paper}
        assert b.model_wordings[key]["flags"] == ["the model's member"]
        assert b.model_wordings[key]["stale"] == set()
        assert b.wordings[key]["papers"] == {plain_paper}
        assert b.wordings[key]["flags"] == ["completed"] and b.wordings[key]["stale"] == {"None"}
        text = ta.render(b, [root / "l"])
        assert f"| {words} | fieldmap_less | 1 | the model's member |" in text
        assert f"| {words} | fieldmap_less | 1 | completed; stale: stored None |" in text


def test_the_command_writes_the_report(tmp_path: Path) -> None:
    _write(tmp_path / "set", "paper_a", _step("brain_extraction", method=(_term("BET", "bet"), [])))
    out = tmp_path / "report.md"
    assert ta.main(["--in", str(tmp_path / "set"), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    for heading in (
        "## 1. Table self-check",
        "## 2. Stored wordings",
        "## 3. Unresolved",
        "## 4. Token trace",
        "## 5. Held-out",
    ):
        assert heading in text
    assert "Not resolving to their own member: 0." in text


def test_the_report_shows_a_failed_alias_and_cuts_long_cells(tmp_path: Path, monkeypatch) -> None:
    nothing: list[dict[str, Any]] = []
    for i in range(5):
        _write(
            tmp_path,
            f"paper_{i}",
            _step("brain_extraction", method=(_term("ROBEX | v1.2", None), nothing)),
        )
    a = ta.audit([tmp_path])
    failure = ("brain_extraction.method", "bet", "BET | x", [None])
    monkeypatch.setattr(ta, "self_check", lambda: (448, [failure]))
    text = ta.render(a, [tmp_path])
    assert "Not resolving to their own member: 1." in text
    assert "| brain_extraction.method | bet | BET / x | [None] |" in text
    # a "|" in the paper's words cannot break the table, and the paper list stops at four
    assert (
        "| brain_extraction.method | ROBEX / v1.2 | 5 | paper_0, paper_1, paper_2, paper_3 ... |"
        in text
    )
    assert ta._cell("x" * 200) == "x" * 107 + "..."


def test_the_command_refuses_a_folder_with_no_papers(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(SystemExit):
        ta.main(["--in", str(tmp_path)])
