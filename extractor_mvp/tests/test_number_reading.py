"""How a number is read (2026-11-25): one reading for the model's value and for the quote.

Three faults stood at 9d5ddc6, in ``extractor._parse_number`` (the value) and
``quote_support.number_in_quote`` (the quote):

1. the value reader deleted every comma, so the decimal "0,5" was 5.0, and the quote reader read
   each side of the comma as a whole number, so 5.0 was "in" the quote "FD > 0,5 mm": a wrong
   value, stored as extracted;
2. the same deletion joined two numbers written with no space, "0.5,3" to 0.53: a lost value;
3. the quote reader had no number that begins with its decimal point, so a correct 0.5 was not in
   "FD > .5 mm" (it read 5): a lost value.

Both readers now go through ``quote_support._NUMBER``. Each case below that failed before the
change says what it read then; the others are controls and passed before as they do now. The
quotes marked "stored" are forms the stored records hold.
"""

from __future__ import annotations

from typing import Any

import pytest

from extractor_mvp import extractor as ex
from extractor_mvp.coverage_fields import COVERAGE_SPECS, CoverageFieldSpec
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.quote_support import (
    coverage_value_supported,
    leading_number,
    number_in_quote,
    read_numbers,
    step_value_supported,
)

# --- the value reader ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("0,5", 0.5),  # was 5.0 (fault 1)
        ("0,25", 0.25),  # was 25.0
        ("3,5", 3.5),  # was 35.0
        ("0,5 mm", 0.5),  # was 5.0
        ("0,125", 0.125),  # was 125.0: a number that begins with 0 has no thousands groups
        ("0.5,3", 0.5),  # was 0.53 (fault 2): two numbers, the first kept
        ("0.5, 3", 0.5),  # control: the same two numbers with a space
        ("1, 000", 1000.0),  # was 1.0: a group that begins with 0 is not a number of its own
        (".5 mm", 0.5),  # was None: no number that begins with its decimal point
        (".5 (framewise displacement), 3 (standard deviations of average signal)", 0.5),  # stored
        (".5", 0.5),
        ("-.5", -0.5),
        # controls
        ("1,000", 1000.0),
        ("10,000", 10000.0),
        ("1,234,567", 1234567.0),
        ("1,000.5", 1000.5),
        ("0.5", 0.5),
        ("0.5 mm", 0.5),
        ("3rd", 3.0),
        ("5%", 5.0),
        ("3 SD, 0.5 mm", 3.0),
        ("0.5 mm (Power et al., 2012)", 0.5),
        ("2, 500", 2.0),  # a comma and a space separate two numbers, as in "0.5, 3"
    ],
)
def test_the_value_reader(raw: str, want: float) -> None:
    assert ex._parse_number(raw, integer=False) == want


@pytest.mark.parametrize(
    "raw",
    [
        "FD > 0,5 mm",
        "> .5 mm",
        "stringent",
        "",
        "mm.5",
        ",5",  # was 5.0: the comma was deleted before the string was read
    ],
)
def test_the_value_reader_still_reads_only_a_leading_number(raw: str) -> None:
    assert ex._parse_number(raw, integer=False) is None


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("3rd", 3),
        ("1,000", 1000),
        ("4", 4),
        ("0,5", None),  # was 5: a decimal is no value for a count
        ("3,5", None),  # was 35
        ("0.5", None),
    ],
)
def test_an_integer_field_refuses_a_decimal_comma(raw: str, want: int | None) -> None:
    got = ex._parse_number(raw, integer=True)
    assert got == want
    assert got is None or isinstance(got, int)


# --- the quote reader ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "quote", "want"),
    [
        (0.5, "FD > 0,5 mm", True),  # was False (fault 1)
        (5.0, "FD > 0,5 mm", False),  # was True: the wrong value the quote supported
        (0.0, "FD > 0,5 mm", False),  # was True
        (0.5, "FD > .5 mm", True),  # was False (fault 3)
        (5.0, "FD > .5 mm", False),  # was True
        (0.5, "or >.5mm framewise displacement", True),  # stored (schwartz_2018); was False
        (0.54, "(max rotation = .54\u00b0)", True),  # stored (gordon_2014); was False
        (0.25, "a threshold of 0,25 mm", True),
        (3.5, "a 3,5 mm kernel", True),
        (0.008, "a high-pass filter at 0,008 Hz", True),  # was False, and 8.0 was True
        (8.0, "a high-pass filter at 0,008 Hz", False),
        (1000.0, "a mode of 1, 000", True),  # was False, and 1.0 was True
        (1.0, "a mode of 1, 000", False),
        (2000.0, "TR = 2,000ms", True),  # was False: the old reader wanted a word boundary
        # controls
        (0.5, "FD > 0.5 mm.", True),
        (0.5, "FD > 0.5 mm", True),
        (1000.0, "a mode of 1,000", True),
        (10000.0, "normalized the 4D global mean intensity to 10,000.", True),  # stored
        (1000.0, "signal scaling (median = 1,000) was applied", True),  # stored
        (91282.0, "The 91,282 standard grayordinates", True),  # stored
        (0.01, "the low-frequency O = [0.01,0.1] (Hz) oscillations", True),  # stored
        (0.1, "the low-frequency O = [0.01,0.1] (Hz) oscillations", True),
        (3.0, "resampled to 3mm isotropic", True),
        (3.0, "resampled to 3.5 mm", False),
        (3.0, "30 slices were acquired", False),
        (4.0, "the first four volumes were discarded", True),
    ],
)
def test_the_quote_reader(value: float, quote: str, want: bool) -> None:
    assert number_in_quote(value, quote) is want


@pytest.mark.parametrize(
    ("quote", "is_not", "is_still"),
    [
        # a full stop, then a citation number or the next sentence's count
        ("the volumes were removed.12 The data were then smoothed", 0.12, 12.0),
        ("smoothed with a 6 mm kernel.5 Subjects were excluded", 0.5, 5.0),
        # names that hold dots: a DOI, a figure, a version
        ("doi: 10.1016/j.neuroimage.2005.02.018", 0.018, 18.0),
        ("as shown in Fig.5", 0.5, 5.0),
        ("FSL version 5.0.9", 0.9, 9.0),
        ("The threshold was 3. Then five volumes were removed", 0.5, 3.0),
    ],
)
def test_a_sentence_ending_period_is_not_a_decimal_point(
    quote: str, is_not: float, is_still: float
) -> None:
    assert not number_in_quote(is_not, quote)
    assert number_in_quote(is_still, quote)


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("0,5", [0.5]),
        ("0.5,3", [0.5, 3.0]),
        ("0.5, 3", [0.5, 3.0]),
        ("1,000", [1000.0]),
        ("1, 000", [1000.0]),
        ("0,125", [0.125]),
        ("1,0000", [1.0]),  # four digits after the comma: no thousands group
        (".5", [0.5]),
        ("p<.05", [0.05]),
        ("(.01-.1 Hz)", [0.01, 0.1]),
        ("0.01\u2013.1 Hz", [0.01, 0.1]),
        ("0,0.1", [0.0, 0.1]),  # a part that holds a decimal point is a number of its own
        ("registration [49,54,55].", [49.0, 54.0, 55.0]),  # stored: three parts are a list
        ("3,55,7", [3.0, 55.0, 7.0]),
        # stored pairs after a comma and a space: never one number
        ("the EFNY study (n = 253, 123 females", [253.0, 123.0]),
        ("Neuroimage 84, 320\u2013341 (2014).", [84.0, 320.0, 341.0, 2014.0]),
        ("2, 500", [2.0, 500.0]),
        ("sub-001, 002", [1.0, 2.0]),
        # the two readings the rule leaves open (see quote_support._NUMBER)
        ("3,125", [3125.0]),
        ("intensity inverted [13,14] constrained", [13.14]),  # stored: a citation pair
        ("3rd", [3.0]),
        ("version 5.3.0", [5.3, 0.0]),
        ("", []),
    ],
)
def test_read_numbers(text: str, want: list[float]) -> None:
    assert read_numbers(text) == want


@pytest.mark.parametrize(
    "raw",
    [
        "0,5",
        "0,25",
        "3,5",
        "0,125",
        "0.5,3",  # was 0.53 against [0.5, 3]
        "0.5, 3",
        "1,000",
        "1, 000",
        "1,0000",  # was 10000 against [1, 0]
        "12,5",  # was 125 against [12, 5]
        "2,000ms",  # was 2000 against [2, 0]
        ".5",  # was 0.5 against [5]
        ".5 mm",
        "0.5",
        "0.5 mm",
        "3rd",
        "1,234,567",
    ],
)
def test_the_two_readers_agree(raw: str) -> None:
    """What the value reader makes of a string, the quote reader finds in the same string."""
    value = ex._parse_number(raw, integer=False)
    assert value is not None
    assert leading_number(raw) == value
    assert read_numbers(raw)[0] == value
    assert number_in_quote(value, raw)


# --- the band -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("0,01-0,1", (0.01, 0.1)),  # was None: each edge read as 0
        ("0,008-0,09 Hz", (0.008, 0.09)),  # was None
        ("0,01-0.1", (0.01, 0.1)),  # was (0.0, 0.1), which the quote "0,01-0.1" supported
        ("0,01-", (0.01, None)),  # was (0.0, None)
        # controls
        ("0.01-0.1", (0.01, 0.1)),
        ("0.01-0.1 Hz", (0.01, 0.1)),
        (".01-.1", (0.01, 0.1)),
        ("0.01\u20130.08", (0.01, 0.08)),
        ("0.01 to 0.1 Hz", (0.01, 0.1)),
        ("0.01-", (0.01, None)),
        ("-0.1", (None, 0.1)),
    ],
)
def test_the_band_reads_each_edge_as_the_quote_reader_does(
    raw: str, want: tuple[float | None, float | None]
) -> None:
    assert ex._parse_band(raw) == want


_BAND = "temporal_filtering.effective_band_hz"


@pytest.mark.parametrize(
    ("value", "quote", "want"),
    [
        ((0.01, 0.1), "band-pass filtered (.01-.1 Hz)", True),  # was False (fault 3)
        ((0.01, 0.1), "band-pass filtered (0,01-0,1 Hz)", True),  # was False
        ((0.0, 0.1), "band-pass filtered (0,01-0.1 Hz)", False),  # was True
        ((0.01, 0.1), "band-pass filtered (0.01-0.1 Hz)", True),  # control
        ((0.01, 0.08), "band-pass filtered (0.01-0.1 Hz)", False),  # control
    ],
)
def test_a_band_edge_in_the_quote(value: tuple[float, float], quote: str, want: bool) -> None:
    assert coverage_value_supported(_BAND, value, quote) is want


# --- every numeric field of the coverage calls, from the model's string to the stored field ------

_NUMERIC_SPECS = [s for s in COVERAGE_SPECS if s.value_kind in ("number", "int", "number_list")]
_BAND_SPECS = [s for s in COVERAGE_SPECS if s.value_kind == "band"]


def _field(spec: CoverageFieldSpec, raw: str, quote: str) -> Any:
    """``coverage_extractor._process`` for one field: the model's value and quote in, the
    provenanced field out."""
    fe = FieldExtractionResult(status="extracted", value=raw, verbatim_quote=quote)
    pf, _, _ = ex._process_field(
        spec.field_id,
        spec.dotted,
        fe,
        spec.literal_type,
        spec.t,
        "Methods. " + quote + " The data were then analysed.",
        None,
        use_synonym_table=False,
        value_kind=spec.value_kind,
        synonyms=None,
    )
    return pf


def _stored(spec: CoverageFieldSpec, number: float) -> Any:
    """The value a field stores for one number: a one-item list for a list field."""
    return [number] if spec.value_kind == "number_list" else number


def _reason(pf: Any) -> str:
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    return str(pf.inference.reason)


def test_the_numeric_fields_are_the_ones_checked_here() -> None:
    assert len(_NUMERIC_SPECS) >= 10
    assert [s.dotted for s in _BAND_SPECS] == [_BAND]
    assert {"scrub.threshold", "spatial_smoothing.fwhm_mm", "temporal_filtering.order"} <= {
        s.dotted for s in _NUMERIC_SPECS
    }


@pytest.mark.parametrize("spec", _NUMERIC_SPECS, ids=lambda s: s.dotted)
def test_a_decimal_comma_is_stored_as_the_decimal(spec: CoverageFieldSpec) -> None:
    pf = _field(spec, "0,5", "The value was set to 0,5 units for every run.")
    if spec.value_kind == "int":
        assert _reason(pf) == "value_not_numeric"  # was EXTRACTED 5
    else:
        assert pf.extraction.status == "EXTRACTED"
        assert pf.extraction.value == _stored(spec, 0.5)  # was 5.0


@pytest.mark.parametrize("spec", _NUMERIC_SPECS, ids=lambda s: s.dotted)
def test_a_whole_number_is_not_supported_by_a_decimal_in_the_quote(
    spec: CoverageFieldSpec,
) -> None:
    for quote in (
        "The value was set to 0,5 units for every run.",  # was EXTRACTED 5
        "The value was set to .5 units for every run.",  # was EXTRACTED 5
    ):
        assert _reason(_field(spec, "5", quote)) == "value_unsupported_by_quote"
    control = _field(spec, "5", "The value was set to 5 units for every run.")
    assert control.extraction.value == _stored(spec, 5)


@pytest.mark.parametrize(
    "spec", [s for s in _NUMERIC_SPECS if s.value_kind != "int"], ids=lambda s: s.dotted
)
def test_a_decimal_is_supported_by_a_quote_that_begins_it_with_the_point(
    spec: CoverageFieldSpec,
) -> None:
    pf = _field(spec, "0.5", "The value was set to .5 units for every run.")
    assert pf.extraction.status == "EXTRACTED"  # was value_unsupported_by_quote
    assert pf.extraction.value == _stored(spec, 0.5)
    stored = _field(spec, ".5 (the first), 3 (the second)", "The value was >.5mm or > 3 SD.")
    assert stored.extraction.value == _stored(spec, 0.5)  # was value_not_numeric


@pytest.mark.parametrize(
    "spec", [s for s in _NUMERIC_SPECS if s.value_kind != "int"], ids=lambda s: s.dotted
)
def test_two_numbers_with_no_space_keep_the_first(spec: CoverageFieldSpec) -> None:
    quote = "The value was set to 0.5 units, or to 3 units in the second sample."
    pf = _field(spec, "0.5,3", quote)
    assert pf.extraction.status == "EXTRACTED"  # was 0.53: value_unsupported_by_quote
    assert pf.extraction.value == _stored(spec, 0.5)
    assert _field(spec, "0.5, 3", quote).extraction.value == _stored(spec, 0.5)  # control


@pytest.mark.parametrize("spec", _NUMERIC_SPECS, ids=lambda s: s.dotted)
def test_the_controls_are_stored_as_they_were(spec: CoverageFieldSpec) -> None:
    thousand = _field(spec, "1,000", "The value was set to 1,000 units for every run.")
    assert thousand.extraction.value == _stored(spec, 1000)
    third = _field(spec, "3rd", "The 3rd unit was used for every run.")
    assert third.extraction.value == _stored(spec, 3)
    if spec.value_kind != "int":
        for raw in ("0.5", "0.5 mm"):
            pf = _field(spec, raw, "Volumes with FD > 0.5 mm.")
            assert pf.extraction.value == _stored(spec, 0.5)
    assert _reason(_field(spec, "0.7", "Volumes with FD > 0.5 mm.")) in (
        "value_unsupported_by_quote",
        "value_not_numeric",  # an integer field
    )


@pytest.mark.parametrize("spec", _BAND_SPECS, ids=lambda s: s.dotted)
def test_a_band_is_stored_from_either_way_of_writing_it(spec: CoverageFieldSpec) -> None:
    comma = _field(spec, "0,01-0,1", "The data were band-pass filtered (0,01-0,1 Hz).")
    assert tuple(comma.extraction.value) == (0.01, 0.1)  # was value_not_numeric
    dot = _field(spec, ".01-.1", "The data were band-pass filtered (.01-.1 Hz).")
    assert tuple(dot.extraction.value) == (0.01, 0.1)  # was value_unsupported_by_quote
    control = _field(spec, "0.01-0.1", "The data were band-pass filtered (0.01-0.1 Hz).")
    assert tuple(control.extraction.value) == (0.01, 0.1)


# --- the two numeric fields of the shared call (their value is read by float(), unchanged) -------


def test_the_shared_call_reads_its_quote_the_same_way() -> None:
    resolution = "spatial_normalization.resolution_mm"
    scale = "intensity_normalization.value"
    point, comma = "resampled to .5 mm isotropic", "resampled to 2,5 mm isotropic"
    assert step_value_supported(resolution, 0.5, point) is True  # was False
    assert step_value_supported(resolution, 5.0, point) is False  # was True
    assert step_value_supported(resolution, 2.5, comma) is True  # was False
    assert step_value_supported(resolution, 5.0, comma) is False  # was True
    # controls
    assert step_value_supported(scale, 1000.0, "normalized to a mode of 1,000") is True
    assert step_value_supported(resolution, 2.0, "resampled to 2 mm.") is True
