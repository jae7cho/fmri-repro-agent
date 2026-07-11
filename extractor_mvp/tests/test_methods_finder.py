"""Tests for the methods-section header heuristic."""

from __future__ import annotations

from pathlib import Path

import pytest

from extractor_mvp.methods_finder import _METHODS_RE, _NEXT_RE, find_methods_section
from extractor_mvp.pdf_loader import load_pdf_text

_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
_corpus = pytest.mark.skipif(not _CORPUS.exists(), reason="corpus PDFs absent (e.g. CI)")


def _text(name: str) -> str:
    return load_pdf_text(_CORPUS / f"{name}.pdf")[0]


def test_header_match_slices_to_next_section():
    text = "Intro blah blah\nMethods\nWe preprocessed with X at 2 mm.\nResults\nWe found Y."
    s = find_methods_section(text)
    assert s.found_via == "header_match"
    assert s.matched_header == "Methods"
    assert "We preprocessed with X at 2 mm." in s.text
    assert "We found Y." not in s.text  # terminated at Results
    assert text[s.start_offset :].startswith("Methods")


def test_earliest_header_wins_over_later_subsection():
    # both top-level "Methods" and a "Preprocessing" subsection match; earliest wins
    text = "Methods\nGeneral.\nPreprocessing\nDetails here.\nDiscussion\nend"
    s = find_methods_section(text)
    assert s.matched_header == "Methods"
    assert s.start_offset == text.index("Methods")
    assert "Details here." in s.text  # subsection still inside the slice


def test_subsection_header_when_no_toplevel_methods():
    text = "Introduction\nstuff\nImage preprocessing\nNormalized to MNI.\nResults\nx"
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
    text = "Methods\nWe did things and stopped."
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
        "We projected to fsaverage5.\n"
        "Results\n"
        "findings\n"
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
    text = "Intro line\nMethods\nWe used X at 2 mm here.\nResults\ntail"
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
    text = ("intro and results and discussion " * 40) + "\nMethods\nWe did a few things."
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
