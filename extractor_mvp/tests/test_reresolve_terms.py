"""scripts/reresolve_terms.py: stored terms re-resolved with the current resolver (2026-11-24)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from reresolve_terms import main, reresolve_record


def _rec(field: str, kind: str, extraction: dict) -> dict:
    return {
        "preprocessing": {
            "steps": [{"kind": kind, field: {"field_id": field, "extraction": extraction}}]
        }
    }


def _t(verbatim: str, resolved: str | None) -> dict:
    return {
        "verbatim": verbatim,
        "resolved": resolved,
        "resolution": "resolved" if resolved else "unrecognized",
    }


def test_a_stale_member_is_re_resolved_and_counted() -> None:
    words = "six parameters plus their derivatives and squares"
    rec = _rec(
        "motion_expansion",
        "nuisance_regression",
        {"status": "EXTRACTED", "value": _t(words, "6param")},
    )
    counts = reresolve_record(rec)
    value = rec["preprocessing"]["steps"][0]["motion_expansion"]["extraction"]["value"]
    assert value == {"verbatim": words, "resolved": "friston24", "resolution": "resolved"}
    assert counts["nuisance_regression.motion_expansion"] == 1


def test_variants_and_lists_are_re_resolved() -> None:
    rec = _rec(
        "motion_expansion",
        "nuisance_regression",
        {
            "status": "VARIED",
            "variants": [
                {"value": _t("six motion parameters and their first-order derivatives", "6param")}
            ],
        },
    )
    reresolve_record(rec)
    var = rec["preprocessing"]["steps"][0]["motion_expansion"]["extraction"]["variants"][0]
    assert var["value"]["resolved"] is None and var["value"]["verbatim"].startswith("six motion")


def test_a_stored_other_and_an_unchanged_term_are_left_as_stored() -> None:
    other = _rec(
        "method",
        "intensity_correction",
        {"status": "EXTRACTED", "value": _t("crude bias field", "other")},
    )
    same = _rec(
        "motion_expansion",
        "nuisance_regression",
        {"status": "EXTRACTED", "value": _t("6param", "6param")},
    )
    assert sum(reresolve_record(other).values()) == 0
    assert (
        other["preprocessing"]["steps"][0]["method"]["extraction"]["value"]["resolved"] == "other"
    )
    assert sum(reresolve_record(same).values()) == 0


def test_a_list_is_re_resolved_as_the_extractor_resolves_it() -> None:
    # D2b (2026-11-25): "white and gray matter" was stored as "white" (unresolved) and "gray matter"
    rec = _rec(
        "tissue_regressors",
        "nuisance_regression",
        {"status": "EXTRACTED", "value": [_t("white", None), _t("gray matter", "gray_matter")]},
    )
    counts = reresolve_record(rec)
    value = rec["preprocessing"]["steps"][0]["tissue_regressors"]["extraction"]["value"]
    assert [v["resolved"] for v in value] == ["white_matter", "gray_matter"]
    assert [v["verbatim"] for v in value] == ["white", "gray matter"]
    assert counts["nuisance_regression.tissue_regressors"] == 1


def test_a_stored_other_inside_a_list_is_left_as_stored() -> None:
    rec = _rec(
        "method",
        "distortion_correction",
        {
            "status": "EXTRACTED",
            "value": [_t("unwarping with a field map", "other"), _t("field map", "fieldmap")],
        },
    )
    assert sum(reresolve_record(rec).values()) == 0
    value = rec["preprocessing"]["steps"][0]["method"]["extraction"]["value"]
    assert [v["resolved"] for v in value] == ["other", "fieldmap"]


def test_the_shared_fields_are_re_resolved_too() -> None:
    # D2b (2026-11-25): the four fields of the shared call use the same resolver
    rec = _rec(
        "target_surface",
        "surface_projection",
        {"status": "EXTRACTED", "value": _t("fsaverage 5", None)},
    )
    counts = reresolve_record(rec)
    value = rec["preprocessing"]["steps"][0]["target_surface"]["extraction"]["value"]
    assert value["resolved"] == "fsaverage5" and value["verbatim"] == "fsaverage 5"
    assert counts["surface_projection.target_surface"] == 1


def test_show_lists_each_changed_term_and_counts_a_held_out_paper(tmp_path, capsys) -> None:
    import json

    words = "six motion parameters and their temporal derivatives"
    for paper in ("paper_a", "B_liu_2005"):
        rec = _rec(
            "motion_expansion",
            "nuisance_regression",
            {"status": "EXTRACTED", "value": _t(words, "6param")},
        )
        (tmp_path / "in" / "papers").mkdir(parents=True, exist_ok=True)
        (tmp_path / "in" / "papers" / f"{paper}.json").write_text(json.dumps(rec), encoding="utf-8")
    # a field that changes in the held-out paper only
    held = json.loads((tmp_path / "in" / "papers" / "B_liu_2005.json").read_text())
    held["preprocessing"]["steps"].append(
        {
            "kind": "brain_extraction",
            "method": {
                "field_id": "method",
                "extraction": {"status": "EXTRACTED", "value": _t("optiBET", "bet")},
            },
        }
    )
    (tmp_path / "in" / "papers" / "B_liu_2005.json").write_text(json.dumps(held), encoding="utf-8")
    assert main(["--in", str(tmp_path / "in"), "--out", str(tmp_path / "out"), "--show"]) == 0
    out = capsys.readouterr().out
    # the per-field counts are those of the papers that are not held out
    assert "nuisance_regression.motion_expansion: 1 terms changed" in out
    assert f"paper_a | nuisance_regression.motion_expansion | {words!r}: 6param -> None" in out
    assert "liu_2005" not in out.lower()
    # one number for the held-out papers: no field of theirs, in the counts or in the list
    assert "held-out papers: 2 terms changed (counted, never listed by field)" in out
    assert "brain_extraction" not in out and "optiBET" not in out
    # without --show: the counts and the held-out total, no listing
    assert main(["--in", str(tmp_path / "in"), "--out", str(tmp_path / "out2")]) == 0
    quiet = capsys.readouterr().out
    assert "nuisance_regression.motion_expansion: 1 terms changed" in quiet
    assert "paper_a |" not in quiet and "brain_extraction" not in quiet
    assert "held-out papers: 2 terms changed" in quiet
    # the copy is written for both, the input is untouched
    stored = json.loads((tmp_path / "in" / "papers" / "paper_a.json").read_text())
    assert (
        stored["preprocessing"]["steps"][0]["motion_expansion"]["extraction"]["value"]["resolved"]
        == "6param"
    )
    copy = json.loads((tmp_path / "out" / "papers" / "B_liu_2005.json").read_text())
    assert (
        copy["preprocessing"]["steps"][0]["motion_expansion"]["extraction"]["value"]["resolved"]
        is None
    )


def test_the_command_refuses_to_write_into_its_input(tmp_path) -> None:
    import pytest

    (tmp_path / "papers").mkdir()
    with pytest.raises(SystemExit):
        main(["--in", str(tmp_path), "--out", str(tmp_path)])


def _detrend(extraction: dict) -> dict:
    return _rec("detrend", "nuisance_regression", extraction)


def test_the_detrend_rule_is_applied_as_the_extractor_applies_it() -> None:
    """The extractor resolves the term, then takes the highest order its quote names
    (coverage_extractor, 2026-10-28). Re-running the first step alone wrote ciric_2017's
    "linear, quadratic" back unresolved."""
    quote = [{"text": "Linear and quadratic trends"}, {"text": "were removed."}]
    stored = _t("linear, quadratic", "quadratic")
    rec = _detrend({"status": "EXTRACTED", "value": dict(stored), "spans": quote})
    assert sum(reresolve_record(rec).values()) == 0
    assert rec["preprocessing"]["steps"][0]["detrend"]["extraction"]["value"] == stored
    # a record from before the rule is brought to what the extractor stores today
    rec = _detrend({"status": "EXTRACTED", "value": _t("linear", "linear"), "spans": quote})
    assert reresolve_record(rec)["nuisance_regression.detrend"] == 1
    value = rec["preprocessing"]["steps"][0]["detrend"]["extraction"]["value"]
    assert value == {"verbatim": "linear", "resolved": "quadratic", "resolution": "resolved"}
    # a part of a varied value is not moved: the extractor applies the rule to an extracted one
    rec = _detrend(
        {"status": "VARIED", "variants": [{"value": _t("linear", "linear"), "spans": quote}]}
    )
    assert sum(reresolve_record(rec).values()) == 0
    # controls: a quote that names no higher order, and a value with no quote at all
    plain = [{"text": "Linear trends were removed."}]
    rec = _detrend({"status": "EXTRACTED", "value": _t("linear", "linear"), "spans": plain})
    assert sum(reresolve_record(rec).values()) == 0
    # no quote at all: nothing to read the order from, so the term keeps what its words give
    rec = _detrend({"status": "EXTRACTED", "value": _t("linear, quadratic", "quadratic")})
    assert reresolve_record(rec)["nuisance_regression.detrend"] == 1
    # a value the checking pass supplied is promoted after the rule has run: left to _resolve_term
    rec = _detrend(
        {
            "status": "EXTRACTED",
            "value": _t("linear", "linear"),
            "spans": quote,
            "checker_supplied": True,
        }
    )
    assert sum(reresolve_record(rec).values()) == 0
    # the spans are joined as stored, by one space: the order phrase runs over two of them
    split = [{"text": "Data were detrended with a second-order"}, {"text": "polynomial."}]
    rec = _detrend({"status": "EXTRACTED", "value": _t("detrended", "quadratic"), "spans": split})
    assert sum(reresolve_record(rec).values()) == 0
    # ... and in the other stored order the phrase is not there
    rec = _detrend(
        {"status": "EXTRACTED", "value": _t("detrended", None), "spans": list(reversed(split))}
    )
    assert sum(reresolve_record(rec).values()) == 0


def _convention(value: dict, number: float | None) -> dict:
    step: dict = {
        "kind": "intensity_normalization",
        "convention": {
            "field_id": "convention",
            "extraction": {"status": "EXTRACTED", "value": value},
        },
    }
    if number is not None:
        step["value"] = {
            "field_id": "value",
            "extraction": {"status": "EXTRACTED", "value": number},
        }
    return {"preprocessing": {"steps": [step]}}


def test_the_intensity_convention_is_re_resolved_with_its_sibling_value() -> None:
    # an alias of this field is gated on the value beside it ("grand mean@10000")
    rec = _convention(_t("grand mean scaling", None), 10000.0)
    assert reresolve_record(rec)["intensity_normalization.convention"] == 1
    value = rec["preprocessing"]["steps"][0]["convention"]["extraction"]["value"]
    assert value["resolved"] == "fsl_grand_mean_10000"
    # a value the gate does not name: the term keeps its words
    rec = _convention(_t("grand mean scaling", None), 37.0)
    assert sum(reresolve_record(rec).values()) == 0
    # no stored value (it failed its own check): the stored member tells which value was used
    rec = _convention(_t("grand mean scaling", "fsl_grand_mean_10000"), None)
    assert sum(reresolve_record(rec).values()) == 0
    value = rec["preprocessing"]["steps"][0]["convention"]["extraction"]["value"]
    assert value["resolved"] == "fsl_grand_mean_10000"
