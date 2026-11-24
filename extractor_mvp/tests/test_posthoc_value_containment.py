"""The post-hoc containment column (scripts/posthoc_value_containment.py, 2026-11-24)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from posthoc_value_containment import contained


def _t(verbatim: str, resolved: str | None = None) -> dict[str, str | None]:
    return {"verbatim": verbatim, "resolved": resolved}


def test_a_record_term_inside_an_annotated_label_agrees() -> None:
    assert contained("bbregister (FreeSurfer v6.0.1)", _t("bbregister", "bbregister"))
    assert contained("boundary-based registration", _t("bbr", "boundary_based"))  # "_"/"-" alike
    assert contained("rigid (6 degrees of freedom)", _t("rigid", "rigid"))
    assert contained("CONN", _t("CONN functional connectivity toolbox"))  # label inside the record


def test_whole_words_only_and_no_short_forms() -> None:
    assert not contained("MNI152NLin2009cAsym", _t("MNI"))  # not a word boundary
    assert not contained("nonlinear", _t("linear", "linear"))
    assert not contained("2 mm", _t("mm"))  # under three characters


def test_numbers_and_yes_no_keep_the_as_stated_result() -> None:
    assert not contained("6 mm FWHM", 6.0)
    assert not contained("yes", True)
    assert not contained("2, 3", [2.0, 3.0])


def test_lists_need_every_item_and_any_of_needs_one() -> None:
    label = "cerebrospinal fluid (CSF), white-matter (WM) and gray-matter (GM)"
    assert contained(label, [_t("csf", "csf"), _t("white_matter", "white_matter")])
    assert not contained(label, [_t("csf", "csf"), _t("ventricles", "ventricles")])
    assert contained("32k fs_LR", ("any of", [_t("MNI"), _t("fsLR_32k", "fs_LR")]))
