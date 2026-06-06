"""Tests for the methods-section header heuristic."""

from __future__ import annotations

from extractor_mvp.methods_finder import find_methods_section


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
