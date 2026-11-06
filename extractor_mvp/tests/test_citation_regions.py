"""Tier 5b (the author's ruling 2 of 2026-11-06): on GROBID text every citation is carried between
CITATION_OPEN and CITATION_CLOSE, and a quote matches with or without any citation text there:
numeric, author-year, or GROBID's own rewriting. Synthetic text throughout."""

from __future__ import annotations

from extractor_mvp.span_resolver import CITATION_CLOSE, CITATION_OPEN, resolve_quote


def r_(s: str) -> str:
    return CITATION_OPEN + s + CITATION_CLOSE


TEXT = (
    "Methods\n"
    "Data were preprocessed with fMRIPrep "
    + r_("(Author et al., 2019")
    + r_("(Author et al., , 2020")
    + "; version 20.2.0), then smoothed.\n"
    "Connectivity was estimated in networks "
    + r_("[1,]")
    + r_("[2]")
    + " that were defined before.\n"
    "Motion was corrected " + r_("[Other, 1995]") + ".\n"
    "Nuisance signals were regressed out as in prior work " + r_("(Third et al., 2001)") + "\n"
)


def _span(q: str) -> tuple[str, bool]:
    r = resolve_quote(q, TEXT)
    assert r.span is not None, (q, r.failure_reason)
    return r.span.text, r.recovered


def test_a_quote_without_the_citation_resolves_across_it() -> None:
    text, recovered = _span("preprocessed with fMRIPrep; version 20.2.0), then smoothed")
    assert recovered and text.startswith("preprocessed") and text.endswith("smoothed")
    assert CITATION_OPEN in text  # the span holds the citation the quote skipped


def test_a_quote_with_the_papers_own_citation_text_resolves() -> None:
    # the paper prints "(Author et al., 2019, 2020"; GROBID's second ref repeats the author
    _span("fMRIPrep (Author et al., 2019, 2020; version 20.2.0), then smoothed")


def test_superscript_numerals_glued_to_a_word_resolve() -> None:
    _span("estimated in networks1,2 that were defined before")


def test_a_quote_that_opens_with_a_citation_resolves_and_covers_it() -> None:
    text, _ = _span("(Author et al., 2019, 2020; version 20.2.0), then smoothed")
    assert text.startswith(CITATION_OPEN)


def test_a_quote_that_ends_inside_a_citation_resolves_and_covers_it() -> None:
    text, _ = _span("regressed out as in prior work (Third et al., 2001)")
    assert text.endswith(CITATION_CLOSE)


def test_a_quote_ending_before_the_citation_ends_at_the_word() -> None:
    text, _ = _span("Motion was corrected.")
    assert text.startswith("Motion") and text.endswith(".")


def test_a_quote_cannot_put_new_words_where_a_citation_is() -> None:
    for q in (
        "Motion was corrected using a new tool",  # words the citation does not hold
        "Motion was corrected [Other, 1996].",  # a year the citation does not hold
    ):
        r = resolve_quote(q, TEXT)
        assert r.span is None and r.failure_reason == "quote_not_found", q


def test_a_citation_is_never_a_wildcard_for_a_sentence() -> None:
    long = "a long passage that the paper never printed at this place at all, " * 2
    r = resolve_quote(f"estimated in networks {long} that were defined before", TEXT)
    assert r.span is None and r.failure_reason == "quote_not_found"


def test_text_outside_citations_still_has_to_match() -> None:
    r = resolve_quote("estimated in networks1,2 that were chosen before", TEXT)
    assert r.span is None and r.failure_reason == "quote_not_found"


def test_the_same_quote_in_two_places_is_ambiguous() -> None:
    twice = TEXT + "Motion was corrected " + r_("[Fourth, 1999]") + ".\n"
    assert resolve_quote("Motion was corrected.", twice).failure_reason == "quote_ambiguous"


def test_a_quote_copied_with_the_delimiters_resolves_exactly() -> None:
    q = "corrected " + r_("[Other, 1995]") + "."
    r = resolve_quote(q, TEXT)
    assert r.span is not None and not r.recovered


def test_text_without_regions_is_unchanged() -> None:
    plain = TEXT.replace(CITATION_OPEN, "").replace(CITATION_CLOSE, "")
    r = resolve_quote("fMRIPrep (Author et al., 2019, 2020; version 20.2.0), then smoothed", plain)
    assert r.span is None and r.failure_reason == "quote_not_found"
    assert resolve_quote("Motion was corrected [Other, 1995].", plain).span is not None


def test_a_flattened_grobid_paragraph_resolves_a_pypdf_era_quote() -> None:
    from pathlib import Path

    from extractor_mvp.grobid_source import flatten_tei

    tei = Path(__file__).parent / "fixtures" / "grobid" / "cattarinussi_2026_structure.tei.xml"
    text = flatten_tei(tei.read_bytes())
    # pypdf glues a superscript citation number to the word before it
    assert resolve_quote("regression of nuisance signals34, 35 and a band-pass filter", text).span
    assert resolve_quote("regression of nuisance signals and a band-pass filter", text).span


def test_a_quote_with_the_citation_verbatim_is_an_ordinary_match() -> None:
    # tiers 3 to 6 read GROBID text with its citations inline, as before the delimiters
    r = resolve_quote("Motion was corrected [Other, 1995].", TEXT)
    assert r.span is not None and not r.recovered


def test_a_verbatim_citation_and_a_source_repair_in_one_quote_resolve() -> None:
    # binder_1999's shape: the text layer prints the fi ligature as "ª"; tier 6 repairs it, and
    # it must see through the citation delimiters to do so
    text = (
        "Images were smoothed " + r_("(Toga et al., 1993)") + ", then a Gaussian ªlter was applied."
    )
    q = "smoothed (Toga et al., 1993), then a Gaussian filter was applied"
    r = resolve_quote(q, text)
    assert r.span is not None and r.recovered


def test_one_citation_printed_differently_resolves() -> None:
    # a single citation, its comma dropped: only tier 5b can match it
    text, recovered = _span("Motion was corrected [Other 1995].")
    assert recovered and CITATION_OPEN in text


def test_a_quote_ending_in_a_differently_printed_citation_covers_it() -> None:
    text, _ = _span("regressed out as in prior work (Third 2001")
    assert text.endswith(CITATION_CLOSE)


def test_a_quote_opening_with_citation_text_starts_at_the_citation() -> None:
    # the text after the citation repeats, so a plain start there would also fit if it could
    # swallow citation text; only the start that covers the citation is a match
    text = "Before " + r_("(Lee, 2001)") + "lee lee lee lee lee lee x."
    r = resolve_quote("Lee lee lee lee lee lee lee x", text)
    assert r.span is not None and r.span.text.startswith(CITATION_OPEN)
