"""The range mark of a band string (2026-11-25).

``extractor._parse_band`` parted a band string at its FIRST hyphen. The extraction writes the band
as the prompt asks ("0.01-0.1", "0.008-", "-0.1"), but the checking pass writes its value in words
("high-pass with a 50 s cutoff period (0.02 Hz)"), and ``checker_promotion.promote`` runs that
string through the same reader. Parted inside "high-pass", it was the low-pass (None, 50.0); the
sentence held 50, so the field was filled. Six stored values have that origin (bassett_2011 and
hermans_2024, in arms_2026-11-15 and fable_arms_bc), each marked ``checker_supplied``.

The string is now parted at the first hyphen that is not directly followed by a letter. Each case
below that read otherwise before the change says what it read then; the others are controls. The
strings marked "stored" are ones the stored records hold.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from conftest import FULL_TEXT, _canned_payload, stub_client
from extractor_mvp import extractor as ex
from extractor_mvp.checker_promotion import promote
from extractor_mvp.coverage_fields import COVERAGE_SPECS
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import extract
from extractor_mvp.parsed_paper import ParsedPaper

_BAND = "temporal_filtering.effective_band_hz"
_SPEC = next(s for s in COVERAGE_SPECS if s.dotted == _BAND)
_HIGH_PASS = "Images were high-pass filtered with a 50 s cutoff period."
_BAND_PASS = "The data were band-pass filtered (0.01-0.1 Hz)."


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # stored, the checking pass's words: the four that filled a field
        ("high-pass with a 50 s cutoff period (0.02 Hz)", None),  # was (None, 50.0)
        ("high-pass with a 50 s cutoff period (about 0.02 Hz)", None),  # was (None, 50.0)
        ("high-pass with 128s cut-off (about 0.008 Hz)", None),  # was (None, 128.0)
        ("high-pass with 128 s cut-off (about 0.0078 Hz)", None),  # was (None, 128.0)
        # stored, the checking pass's words: read wrongly, or rightly by the same accident
        ("0.02 Hz (high-pass cutoff from 50 s period)", None),  # was (0.02, 50.0)
        ("low-pass filter sigma = 1.55", None),  # was (None, 1.55)
        ("0.008 Hz (high-pass)", None),  # was (0.008, None)
        # the band stands after a word that holds a hyphen
        ("band-pass 0.01-0.1 Hz", (0.01, 0.1)),  # was (None, 0.01)
        ("zero-phase band-pass 0.01-0.1 Hz", (0.01, 0.1)),  # was (None, 0.01)
        ("high-pass 0.008-", (0.008, None)),  # was (None, 0.008): a high-pass read as a low-pass
        ("high-pass 0.01 Hz", None),  # was (None, 0.01): no range mark, and no band
        ("low-pass -0.1", (None, 0.1)),
    ],
)
def test_a_hyphen_inside_a_word_is_no_range_mark(
    raw: str, want: tuple[float | None, float | None] | None
) -> None:
    assert ex._parse_band(raw) == want


@pytest.mark.parametrize(
    "raw",
    [
        "a 128-s high-pass filter",  # was (128.0, None)
        "0.1-Hz low-pass filter",  # was (0.1, None): a low-pass read as a high-pass
        "a 0.01-Hz high-pass filter",  # was (0.01, None)
        "0.008-Hz",  # was (0.008, None): a frequency with its unit, which names no band
        "0.01-inf",  # was (0.01, None)
    ],
)
def test_a_number_joined_to_a_word_by_its_hyphen_is_no_edge(raw: str) -> None:
    assert ex._parse_band(raw) is None


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # the three forms the prompt asks for
        ("0.01-0.1", (0.01, 0.1)),
        ("0.008-", (0.008, None)),
        ("-0.1", (None, 0.1)),
        # with a unit, with spaces, with "to"
        ("0.01-0.1 Hz", (0.01, 0.1)),
        ("0.01 - 0.1 Hz", (0.01, 0.1)),
        ("0.01 Hz - 0.1 Hz", (0.01, 0.1)),
        ("0.01Hz-0.1Hz", (0.01, 0.1)),
        ("0.01 to 0.1 Hz", (0.01, 0.1)),
        ("0.008- Hz", (0.008, None)),
        ("0.008 Hz-", (0.008, None)),
        (".01-.1", (0.01, 0.1)),
        # stored, the extraction's raw values and two of the checking pass's
        ("0.0078125-", (0.0078125, None)),
        ("0.02-", (0.02, None)),
        ("0.31-0.43", (0.31, 0.43)),
        ("0.008-0.09 Hz", (0.008, 0.09)),
        ("0.009-0.08 Hz for rest-fMRI", (0.009, 0.08)),
        # stored strings that hold no hyphen: no band before, no band now
        ("sigma of 1,000 s", None),
        ("50 s cutoff period", None),
        ("0.008 Hz, None", None),
        ("0.01 Hz (100 s period)", None),
        # the low edge must be below the high edge
        ("0.1-0.01", None),
    ],
)
def test_the_bands_read_as_they_were(
    raw: str, want: tuple[float | None, float | None] | None
) -> None:
    assert ex._parse_band(raw) == want


# --- from the string to the stored field ----------------------------------------------------------


def _field(raw: str, quote: str) -> Any:
    fe = FieldExtractionResult(status="extracted", value=raw, verbatim_quote=quote)
    pf, diag, _ = ex._process_field(
        _SPEC.field_id,
        _SPEC.dotted,
        fe,
        _SPEC.literal_type,
        _SPEC.t,
        "Methods. " + quote + " The data were then analysed.",
        None,
        use_synonym_table=False,
        value_kind=_SPEC.value_kind,
        synonyms=None,
    )
    return pf, diag


def test_the_stored_case_is_no_longer_a_value() -> None:
    """bassett_2011: the checking pass's words and the sentence it relied on."""
    pf, diag = _field("high-pass with a 50 s cutoff period (0.02 Hz)", _HIGH_PASS)
    assert pf.extraction.status == "MISSING_FROM_PAPER"  # was EXTRACTED (None, 50.0)
    assert pf.inference.reason == "value_not_numeric"
    assert diag is not None
    assert diag.raw_value == "high-pass with a 50 s cutoff period (0.02 Hz)"
    # controls: the band the reader reads is stored, with words before it or without
    for raw in ("0.01-0.1", "band-pass 0.01-0.1 Hz"):
        control, _ = _field(raw, _BAND_PASS)
        assert control.extraction.status == "EXTRACTED"
        assert tuple(control.extraction.value) == (0.01, 0.1)


_PREP: Any = None


def _prep() -> Any:
    """A record whose band the extraction left without a value (every coverage field missing)."""
    global _PREP
    if _PREP is None:
        _PREP, _, _ = extract(
            ParsedPaper(text=FULL_TEXT, source="p"), "m", client=stub_client(_canned_payload())
        )
    return copy.deepcopy(_PREP)


def _band(prep: Any) -> Any:
    return next(s for s in prep.steps if s.kind == "temporal_filtering").effective_band_hz


def _supplied(better: str, sentence: str) -> dict[str, Any]:
    verdict = {
        "verdict": "missed",
        "better_value": better,
        "relied_on": sentence,
        "relied_on_resolved": True,
    }
    return {"status": "ok", "fields": {_BAND: verdict}}


def test_the_checking_pass_words_stay_a_flag() -> None:
    prep = _prep()
    assert _band(prep).extraction.status == "MISSING_FROM_PAPER"
    log = promote(
        prep,
        _supplied("high-pass with a 50 s cutoff period (0.02 Hz)", _HIGH_PASS),
        "Methods. " + _HIGH_PASS,
    )
    assert [e["outcome"] for e in log] == ["flag: value_not_numeric"]  # was "filled"
    assert _band(prep).extraction.status == "MISSING_FROM_PAPER"  # was (None, 50.0)


def test_a_band_the_checking_pass_writes_as_a_band_still_fills_the_field() -> None:
    prep = _prep()
    log = promote(prep, _supplied("0.01-0.1 Hz", _BAND_PASS), "Methods. " + _BAND_PASS)
    assert [e["outcome"] for e in log] == ["filled"]
    band = _band(prep).extraction
    assert band.status == "EXTRACTED"
    assert tuple(band.value) == (0.01, 0.1)
    assert band.checker_supplied is True
