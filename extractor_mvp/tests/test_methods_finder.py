"""Tests for the methods-section header heuristic."""

from __future__ import annotations

from pathlib import Path

import pytest

from extractor_mvp.methods_finder import _METHODS_RE, _NEXT_RE, find_methods_section
from extractor_mvp.pdf_loader import load_pdf_text

_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
_corpus = pytest.mark.skipif(not _CORPUS.exists(), reason="corpus PDFs absent (e.g. CI)")


#: Neutral methods prose, 2,040 characters: since fix 1a (2026-11-05) a slice under 2,000 characters
#: is methods_not_found, so the synthetic papers below carry it to stay header slices.
_PAD = "The scanner room was kept at a constant temperature throughout. " * 32 + "\n"


def _text(name: str) -> str:
    return load_pdf_text(_CORPUS / f"{name}.pdf")[0]


def test_header_match_slices_to_next_section():
    text = (
        "Intro blah blah\nMethods\nWe preprocessed with X at 2 mm.\n"
        + _PAD
        + "Results\nWe found Y."
        + _PAD
    )
    s = find_methods_section(text)
    assert s.found_via == "header_match"
    assert s.matched_header == "Methods"
    assert "We preprocessed with X at 2 mm." in s.text
    assert "We found Y." not in s.text  # terminated at Results
    assert text[s.start_offset :].startswith("Methods")


def test_earliest_header_wins_over_later_subsection():
    # both top-level "Methods" and a "Preprocessing" subsection match; earliest wins
    text = "Methods\nGeneral.\nPreprocessing\nDetails here.\n" + _PAD + "Discussion\nend" + _PAD
    s = find_methods_section(text)
    assert s.matched_header == "Methods"
    assert s.start_offset == text.index("Methods")
    assert "Details here." in s.text  # subsection still inside the slice


def test_subsection_header_when_no_toplevel_methods():
    text = (
        "Introduction\nstuff\nImage preprocessing\nNormalized to MNI.\n"
        + _PAD
        + "Results\nx"
        + _PAD
    )
    s = find_methods_section(text)
    assert s.found_via == "header_match"
    assert "Normalized to MNI." in s.text


def test_no_match_falls_back_to_full_text():
    text = "There is no recognizable section header anywhere in this prose."
    s = find_methods_section(text)
    assert s.found_via == "fallback_full_text"
    assert s.matched_header is None
    assert s.text == text
    assert s.start_offset == 0


def test_runs_to_end_when_no_next_section():
    text = "Methods\n" + _PAD + "We did things and stopped."
    s = find_methods_section(text)
    assert s.found_via == "header_match"
    assert s.text.endswith("stopped.")
    assert s.ended_at == "end_of_text"
    assert s.suspicious is True  # no next-section boundary -> distrust


# --- D1 anchor regression + vocabulary guard --------------------------------


def test_anchor_regression_body_line_starting_methods_not_matched() -> None:
    # chen's literal Introduction body line begins with "methods" — the ^...$ anchor must
    # NOT let it anchor the slice; the real "Methods and Analysis" header must win.
    text = (
        "Introduction\n"
        "methods [22] are relatively less reliable than independent component analysis\n"
        "more introduction text\n"
        "Methods and Analysis\n"
        "We projected to fsaverage5.\n" + _PAD + "Results\n"
        "findings\n" + _PAD
    )
    s = find_methods_section(text)
    assert s.matched_header == "Methods and Analysis"
    assert s.start_offset == text.index("Methods and Analysis")
    assert "fsaverage5" in s.text


def test_methods_and_x_matches_but_results_and_discussion_is_next() -> None:
    assert any(rx.search("Methods and Analysis") for rx in _METHODS_RE)
    assert any(rx.search("Materials and Methods") for rx in _METHODS_RE)
    # the D2 guard: a combined next-section header is NOT a methods header, and IS a next one
    assert not any(rx.search("Results and Discussion") for rx in _METHODS_RE)
    assert any(rx.search("Results and Discussion") for rx in _NEXT_RE)


# --- diagnostics + span round-trip ------------------------------------------


def test_diagnostics_fields_and_span_round_trip() -> None:
    text = "Intro line\nMethods\nWe used X at 2 mm here.\n" + _PAD + "Results\ntail" + _PAD
    s = find_methods_section(text)
    assert s.end_offset == text.index("Results")
    assert s.ended_at == "Results"
    assert 0.0 < s.slice_ratio < 1.0
    # start_offset maps a slice-relative offset back to the full-text offset
    rel = s.text.index("2 mm")
    assert text[s.start_offset + rel :].startswith("2 mm")


def test_suspicious_flag_on_high_ratio() -> None:
    # a header slice > 60% of the paper is distrusted even with a clean next-section end
    text = "x\nMethods\n" + ("filler " * 400) + "\nResults\nend"
    s = find_methods_section(text)
    assert s.slice_ratio > 0.6
    assert s.suspicious is True


def test_early_header_running_to_end_is_suspicious() -> None:
    # EARLY methods header + no terminator -> likely swallowed Results/Discussion -> flag.
    text = "Methods\n" + ("body " * 50)
    s = find_methods_section(text)
    assert s.ended_at == "end_of_text"
    assert (s.start_offset / len(text)) < 0.5
    assert s.suspicious is True


def test_late_header_running_to_end_is_not_suspicious() -> None:
    # LATE (terminal) methods header running to end-of-text is the normal terminal-Methods
    # shape (Braun/Viduarre) — NOT a defect, must not cry wolf.
    text = ("intro and results and discussion " * 140) + "\nMethods\nWe did a few things." + _PAD
    s = find_methods_section(text)
    assert s.found_via == "header_match"
    assert s.ended_at == "end_of_text"
    assert (s.start_offset / len(text)) >= 0.5
    assert s.slice_ratio <= 0.6
    assert s.suspicious is False


def test_determinism() -> None:
    text = "Intro\nMethods\nbody\nResults\nx"
    assert find_methods_section(text) == find_methods_section(text)


# --- corpus (skipped when PDFs absent) --------------------------------------


@_corpus
def test_chen_now_header_match_not_full_document() -> None:
    # was fallback_full_text (slice=whole doc) because "Methods and Analysis" was uncovered.
    s = find_methods_section(_text("Chen_2015"))
    assert s.found_via == "header_match"
    assert s.slice_ratio < 1.0
    assert "fsaverage5" in s.text  # backs an extracted value
    assert "10,000" in s.text or "grand" in s.text.lower()  # grand-mean convention


@_corpus
def test_oconnor_terminates_before_references_keeping_cpac() -> None:
    # was header_match running to References (0.63), swallowing data-descriptor sections.
    s = find_methods_section(_text("OConnor_2017"))
    assert "reference" not in s.ended_at.lower()  # ends at end-matter, not References
    assert s.slice_ratio < 0.63
    assert "C-PAC" in s.text and "0.4.0" in s.text  # the missed pipeline + version survive


@_corpus
def test_cabral_review_correctly_falls_back() -> None:
    # a review with NO Methods section: fallback is CORRECT behaviour, not a bug.
    s = find_methods_section(_text("Cabral_2017"))
    assert s.found_via == "fallback_full_text"
    assert s.suspicious is True


@_corpus
def test_no_header_match_silently_swallows_content() -> None:
    # The oconnor bug (ending at References with non-methods sections swallowed) is fixed:
    # no header_match paper ends at "References" with a bloated slice. And an EARLY header
    # running to end-of-text is still flagged (swallowed Results/Discussion).
    for pdf in sorted(_CORPUS.glob("*.pdf")):
        t = load_pdf_text(pdf)[0]
        s = find_methods_section(t)
        if s.found_via != "header_match":
            continue
        assert s.ended_at != "References" or s.slice_ratio < 0.6, pdf.name
        if s.ended_at == "end_of_text" and (s.start_offset / len(t)) < 0.5:
            assert s.suspicious is True, pdf.name


@_corpus
def test_terminal_methods_papers_not_flagged_suspicious() -> None:
    # Braun_2015 and Viduarre_2017: LATE methods headers running to end-of-text are the
    # normal terminal-Methods shape — the refined predicate must NOT cry wolf on them.
    for name in ("Braun_2015", "Viduarre_2017"):
        s = find_methods_section(_text(name))
        assert s.found_via == "header_match"
        assert s.ended_at == "end_of_text"
        assert (s.start_offset / len(_text(name))) > 0.5
        assert s.suspicious is False, name


# --- fix 1a (2026-11-05): a slice too small to be a methods section, and the terminators ---------

_BODY = "We preprocessed the data with a pipeline and smoothed at 6 mm FWHM. " * 60


def test_experimental_procedures_is_a_methods_heading() -> None:
    text = "Introduction\nintro\nExperimental Procedures\n" + _BODY + "\nResults\nfound"
    s = find_methods_section(text)
    assert s.found_via == "header_match"
    assert s.matched_header == "Experimental Procedures"


def test_a_lone_supplementary_line_does_not_end_the_slice_but_the_heading_does() -> None:
    text = (
        "Introduction\nintro\nMethods\n"
        + _BODY
        + "\nas described in the\nSupplementary\nMaterial, we then\n"
        + _BODY
        + "\nSupplementary Material\nsee web\nResults\nfound"
    )
    s = find_methods_section(text)
    assert s.ended_at == "Supplementary Material"
    assert "Material, we then" in s.text


def test_a_slice_under_the_floor_is_methods_not_found_and_says_why() -> None:
    text = "Introduction\n" + _BODY * 3 + "\nMethods\nToo short.\nResults\n" + _BODY * 3
    s = find_methods_section(text)
    assert s.found_via == "fallback_full_text" and s.suspicious
    assert s.text == text and s.matched_header is None
    assert s.fallback_reason is not None and "'Methods' gave" in s.fallback_reason


def test_a_slice_under_the_ratio_floor_is_methods_not_found() -> None:
    long_tail = "x " * 200_000  # 2,500 characters of methods in a 400,000-character text
    text = "Methods\n" + "y" * 2500 + "\nResults\n" + long_tail
    assert find_methods_section(text).found_via == "fallback_full_text"


def test_a_one_word_per_line_text_layer_is_methods_not_found() -> None:
    words = ("Methods\n" + "\n".join(_BODY.split()) + "\nResults\n").splitlines()
    s = find_methods_section("\n".join(words))
    assert s.found_via == "fallback_full_text"
    assert s.fallback_reason is not None and "one word per line" in s.fallback_reason


def test_an_ordinary_methods_slice_is_kept() -> None:
    s = find_methods_section("Intro\nx\nMethods\n" + _BODY + "\nResults\nend")
    assert s.found_via == "header_match" and s.fallback_reason is None


_STRESS = Path("/Users/cwook/Documents/neurorepro/tested_lit/stress_v1")


@pytest.mark.skipif(not (_STRESS / "Cattarinussi_2026.pdf").exists(), reason="corpus PDF absent")
def test_cattarinussi_is_sliced_after_reflow() -> None:
    # the author's list of 2026-11-05, third round, item 4: its one-word-per-line layer had made it
    # methods_not_found (fix 1a); reflowed, its Methods heading slices to its Results heading
    from extractor_mvp.pdf_loader import reflow_one_word_lines

    raw = load_pdf_text(_STRESS / "Cattarinussi_2026.pdf")[0]
    assert find_methods_section(raw).found_via == "fallback_full_text"
    text, info = reflow_one_word_lines(raw)
    assert info is not None and info["one_word_share_after"] < 0.8
    s = find_methods_section(text)
    assert s.found_via == "header_match" and s.ended_at == "Results"
    assert 0.1 < s.slice_ratio < 0.3


# --- a supplement's MRI sections (the author's list of 2026-11-05, third round, item 1) ----------

from extractor_mvp.methods_finder import (  # noqa: E402
    SUPP_MIN_SLICE_CHARS,
    find_supplement_mri_section,
)

_SUPP_BODY = "The scanner room was kept at a constant temperature throughout the session.\n" * 10


def _supp(*parts: str) -> str:
    return "".join(p if p.endswith("\n") else p + "\n" for p in parts)


def test_a_supplement_is_sliced_from_its_mri_heading_to_the_next_table() -> None:
    text = _supp(
        "Supplemental Information",
        "Table of Contents",
        "Preprocessing procedures with fMRIPrep \u2013 pages 4-6",
        "Participants",
        _SUPP_BODY,
        "fMRI acquisition",
        _SUPP_BODY,
        "Cross-participant alignment",
        _SUPP_BODY,
        "Table S2. Regions of interest",
        _SUPP_BODY,
    )
    s = find_supplement_mri_section(text)
    assert s.found_via == "header_match" and s.matched_header == "fMRI acquisition"
    assert s.text.startswith("fMRI acquisition") and "Cross-participant alignment" in s.text
    assert s.ended_at == "Table S2. Regions of interest" and "Table S2" not in s.text
    assert text[s.start_offset : s.end_offset] == s.text


def test_sentences_that_open_with_a_section_word_do_not_end_the_slice() -> None:
    text = _supp(
        "MRI acquisition and preprocessing",
        _SUPP_BODY,
        "reference volume and its skull-stripped version were generated",
        "Results included in this manuscript come from the models in the main text",
        _SUPP_BODY,
        "Reference image creation",
        _SUPP_BODY,
        "Supplementary Results",
        _SUPP_BODY,
    )
    s = find_supplement_mri_section(text)
    assert s.ended_at == "Supplementary Results" and "Results included" in s.text
    assert "Reference image creation" in s.text


def test_a_supplement_without_an_mri_heading_is_read_whole() -> None:
    text = _supp("Supplementary methods", _SUPP_BODY, "Table S1", _SUPP_BODY)
    s = find_supplement_mri_section(text)
    assert s.found_via == "fallback_full_text" and s.text == text
    assert s.fallback_reason is not None and "names MRI" in s.fallback_reason


def test_a_supplement_slice_under_the_floor_is_read_whole() -> None:
    text = _supp("fMRI acquisition", "TR was 2 s.", "Table S1", _SUPP_BODY * 3)
    s = find_supplement_mri_section(text)
    assert s.found_via == "fallback_full_text" and s.text == text
    assert s.fallback_reason is not None and "'fMRI acquisition' gave" in s.fallback_reason
    long_enough = _supp("fMRI acquisition", "x" * SUPP_MIN_SLICE_CHARS, "Table S1", _SUPP_BODY)
    assert find_supplement_mri_section(long_enough).found_via == "header_match"


_STRESS_SUPPS = {
    "Bakker_2012": ("fMRI acquisition", "end_of_text"),
    "Cattarinussi_2026": ("MRI acquisition and preprocessing", "Supplementary Results"),
    "Hermans_2024": ("fMRIPrep Methods Summary:", "end_of_text"),
    "Ladouceur_2023": (
        "Preprocessing procedures with fMRIPrep:",
        "Framewise Displacement Sensitivity Analyses",
    ),
}


@pytest.mark.skipif(not _STRESS.exists(), reason="corpus PDFs absent (e.g. CI)")
@pytest.mark.parametrize("paper", sorted(_STRESS_SUPPS))
def test_the_four_supplements_read_in_stress_v2_are_sliced_at_their_mri_headings(
    paper: str,
) -> None:
    from extractor_mvp.pdf_loader import reflow_one_word_lines
    from extractor_mvp.software_scan import _body_end

    raw = load_pdf_text(_STRESS / f"{paper}_supp.pdf")[0]
    text = reflow_one_word_lines(raw)[0]
    s = find_supplement_mri_section(text[: _body_end(text)])
    assert (s.matched_header, s.ended_at) == _STRESS_SUPPS[paper]
    assert s.slice_ratio < 0.4
