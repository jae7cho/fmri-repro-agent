"""Tests for the quote -> Span resolver."""

from __future__ import annotations

from extractor_mvp.span_resolver import resolve_quote

TEXT = "Data were normalized to MNI152NLin6Asym space at 2 mm isotropic resolution."


def test_exact_match_success():
    r = resolve_quote("normalized to MNI152NLin6Asym", TEXT)
    assert r.failure_reason is None
    assert r.span is not None
    assert TEXT[r.span.start : r.span.end] == "normalized to MNI152NLin6Asym"
    assert r.span.text == "normalized to MNI152NLin6Asym"


def test_case_insensitive_success():
    r = resolve_quote("NORMALIZED TO mni152nlin6asym", TEXT)
    assert r.failure_reason is None
    assert r.span is not None
    # span points at the original-cased text
    assert TEXT[r.span.start : r.span.end] == "normalized to MNI152NLin6Asym"


def test_whitespace_collapse_success_maps_to_original_offsets():
    # PDF-style line break inside the text; LLM quoted it single-spaced.
    text = "normalized to MNI152NLin6Asym\nspace at 2 mm"
    r = resolve_quote("MNI152NLin6Asym space", text)
    assert r.failure_reason is None
    assert r.span is not None
    # the span covers the ORIGINAL text including the newline
    assert text[r.span.start : r.span.end] == "MNI152NLin6Asym\nspace"


def test_zero_matches_not_found():
    r = resolve_quote("registered with MSMSulc", TEXT)
    assert r.span is None
    assert r.failure_reason == "quote_not_found"


def test_multiple_matches_ambiguous():
    text = "2 mm here and 2 mm there"
    r = resolve_quote("2 mm", text)
    assert r.span is None
    assert r.failure_reason == "quote_ambiguous"


def test_empty_quote_not_found():
    assert resolve_quote("", TEXT).failure_reason == "quote_not_found"
    assert resolve_quote("   ", TEXT).failure_reason == "quote_not_found"


def test_quote_longer_than_text_not_found():
    assert resolve_quote(TEXT + " and then some more", TEXT).failure_reason == "quote_not_found"


def test_exact_preferred_over_case_insensitive_ambiguity():
    # one exact-case occurrence, plus a different-case one: exact match wins (count==1 exact)
    text = "MNI152NLin6Asym ... mni152nlin6asym"
    r = resolve_quote("MNI152NLin6Asym", text)
    assert r.span is not None
    assert r.span.start == 0


# --- Tier 3: Unicode normalization -----------------------------------------

from extractor_mvp.span_resolver import normalize_with_offset_map  # noqa: E402


def _resolves_to(quote: str, text: str, original: str, normalized: str):
    r = resolve_quote(quote, text)
    assert r.failure_reason is None and r.span is not None
    assert text[r.span.start : r.span.end] == original  # span points into ORIGINAL text
    assert normalize_with_offset_map(text[r.span.start : r.span.end])[0] == normalized
    return r


def test_ligature_fl():
    _resolves_to(
        "fluctuations", "global signal ﬂuctuations were noted", "ﬂuctuations", "fluctuations"
    )


def test_multiplication_sign():
    _resolves_to(
        "resampled at 2x2x2mm",
        "data resampled at 2×2×2mm voxels",
        "resampled at 2×2×2mm",
        "resampled at 2x2x2mm",
    )


def test_superscript_decomposes():
    # ³ NFKD-decomposes to "3" on both sides
    _resolves_to(
        "at 33 resolution", "voxels at 3³ resolution here", "at 3³ resolution", "at 33 resolution"
    )


def test_smart_double_quotes():
    _resolves_to('"MNI152"', "the “MNI152” template", "“MNI152”", '"MNI152"')


def test_em_dash():
    _resolves_to(
        "preprocessing-including",
        "preprocessing—including motion correction",
        "preprocessing—including",
        "preprocessing-including",
    )


def test_nbsp():
    _resolves_to("MNI152 space", "warped to MNI152 space at 2mm", "MNI152 space", "MNI152 space")


def test_combining_mark_diacritic():
    _resolves_to("cafe protocol", "the café protocol was used", "café protocol", "cafe protocol")


def test_normalized_ambiguity_preserved():
    # both occurrences are ligatures (no literal match), normalize identically -> ambiguous
    r = resolve_quote("flowed", "signal ﬂowed and then ﬂowed again")
    assert r.span is None
    assert r.failure_reason == "quote_ambiguous"


def test_ascii_fallthrough_identity_map():
    # pure ASCII: normalization is identity; exact tier (1) wins
    norm, offs = normalize_with_offset_map("MNI152")
    assert norm == "MNI152"
    assert offs == [0, 1, 2, 3, 4, 5, 6]
    r = resolve_quote("MNI152", "normalized to MNI152 space")
    assert r.span is not None and r.span.start == len("normalized to ")


def test_normalize_offset_map_ligature_offsets():
    # ﬂ at index 0 -> 'f','l' both map to 0; sentinel at end
    norm, offs = normalize_with_offset_map("ﬂx")
    assert norm == "flx"
    assert offs == [0, 0, 1, 2]  # f->0, l->0, x->1, sentinel->2


# --- Measurement-token whitespace splits (pypdf artifact) -------------------


def test_measurement_split_unit_letters():
    # pypdf split "3mm" into "3m m"; LLM quoted the clean form.
    _resolves_to(
        "resampled to 3mm voxels",
        "data were resampled to 3m m voxels",
        "resampled to 3m m voxels",
        "resampled to 3mm voxels",
    )


def test_measurement_split_unit_and_superscript():
    # the liu_2013 case: pypdf renders "3 × 3 × 3mm³" as "3 × 3 × 3m m\n3"; the
    # LLM quotes it cleanly as "3 × 3 × 3mm3" (× preserved, unit/superscript joined).
    text = "resampled at\nthe 3 × 3 × 3m m\n3 resolution of the MNI normalized brain space"
    r = resolve_quote("the 3 × 3 × 3mm3 resolution of the MNI normalized brain space", text)
    assert r.failure_reason is None and r.span is not None
    assert text[r.span.start : r.span.end] == (
        "the 3 × 3 × 3m m\n3 resolution of the MNI normalized brain space"
    )


def test_measurement_split_does_not_merge_identifier_and_word():
    # "MNI152 space" must NOT collapse to "MNI152space" (no single-letter flank).
    norm, _ = normalize_with_offset_map("warped to MNI152 space")
    assert norm == "warped to MNI152 space"


def test_measurement_split_does_not_merge_number_and_word():
    # "20 subjects" / "Table 3 shows" are ordinary word boundaries — preserved.
    assert normalize_with_offset_map("20 subjects")[0] == "20 subjects"
    assert normalize_with_offset_map("Table 3 shows")[0] == "Table 3 shows"


def test_measurement_number_space_unit_preserved():
    # "2 mm" (number-space-unit, not glued) is left alone — neither side is a
    # single LETTER, so it stays resolvable only via the whitespace tier.
    assert normalize_with_offset_map("at 2 mm isotropic")[0] == "at 2 mm isotropic"


# ---------------------------------------------------------------------------
# Line-wrap soft-hyphen de-hyphenation (diagnosed on liu_2013 "normal-\nized")
# ---------------------------------------------------------------------------


def test_dehyphenation_normalize_only_on_hyphen_newline():
    # -\n word-split is rejoined; a hyphen followed by anything else is untouched.
    assert normalize_with_offset_map("normal-\nized")[0] == "normalized"
    assert normalize_with_offset_map("normal- \nized")[0] == "normalized"  # optional space
    assert normalize_with_offset_map("normal-\n  ized")[0] == "normalized"  # trailing space
    # NO newline -> legitimate compounds/ranges stay intact:
    assert normalize_with_offset_map("grand-mean")[0] == "grand-mean"
    assert normalize_with_offset_map("z-score")[0] == "z-score"
    assert normalize_with_offset_map("test-retest")[0] == "test-retest"
    assert normalize_with_offset_map("0.01-0.1 Hz")[0] == "0.01-0.1 Hz"
    # hyphen not attached to a word (space before it) -> untouched even with a newline:
    assert normalize_with_offset_map("word - \nword")[0] == "word - \nword"


def test_dehyphenation_liu_positive_resolves():
    # 2a — Liu's exact case: PDF wraps "normalized" as "normal-\nized" and has a plain
    # newline in "temporal\nstandard"; the LLM quote has the intact words.
    text = (
        "Preprocessing details follow. Finally, for each voxel, the fMRI signal was "
        "temporally normal-\nized by subtracting its mean and then dividing by its "
        "temporal\nstandard deviation (SD). EXTRACTION OF CAPs follows."
    )
    quote = (
        "the fMRI signal was temporally normalized by subtracting its mean and then "
        "dividing by its temporal standard deviation (SD)"
    )
    r = resolve_quote(quote, text)
    assert r.failure_reason is None
    assert r.span is not None
    # the span covers the ORIGINAL (hyphenated + line-broken) region
    assert text[r.span.start : r.span.end].startswith("the fMRI signal was temporally normal-")
    assert text[r.span.start : r.span.end].endswith("deviation (SD)")


def test_dehyphenation_offset_correctness_no_shift():
    # 2b — the CRITICAL test: a de-hyphenation that matches but mis-maps would return a
    # shifted span. Put the hyphenated word mid-passage and assert exact original slice.
    prefix = "AAAA bbbb CCCC dddd. "  # 21 chars
    original_sentence = "the signal was normal-\nized here."
    suffix = " EEEE ffff GGGG."
    text = prefix + original_sentence + suffix
    quote = "the signal was normalized here."
    r = resolve_quote(quote, text)
    assert r.span is not None
    # sliced from ORIGINAL text, the span is exactly the hyphenated original sentence
    assert text[r.span.start : r.span.end] == original_sentence
    # and it starts at the right place (not shifted by the removed hyphen/newline)
    assert r.span.start == len(prefix)
    assert r.span.text == original_sentence


def test_dehyphenation_does_not_false_join_compound():
    # 2c — a legitimate compound with hyphen+normal-char (NO newline) is NOT de-hyphenated:
    # the compound stays intact and a quote carrying the hyphen resolves against it.
    text = "we applied grand-mean scaling to 10000 across the run."
    r = resolve_quote("grand-mean scaling to 10000", text)
    assert r.span is not None
    assert text[r.span.start : r.span.end] == "grand-mean scaling to 10000"
    # z-score / test-retest with no following newline resolve intact too
    text2 = "z-score and test-retest reliability were computed."
    r2 = resolve_quote("z-score and test-retest reliability", text2)
    assert r2.span is not None
    assert text2[r2.span.start : r2.span.end] == "z-score and test-retest reliability"
