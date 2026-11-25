"""scripts/reresolve_terms.py: stored terms re-resolved with the current resolver (2026-11-24)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from reresolve_terms import reresolve_record


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
