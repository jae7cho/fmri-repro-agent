"""The step-field quote-support check — ``quote_support.py``, DELTA_value_in_quote_step_fields.md §5.

Every string is synthetic; no sentence from any corpus paper appears. What is pinned, per ruling:
1. Literal fields: an alias of the returned value, taken WHOLE, in the repaired quote;
2. numeric fields: the number in the quote, digit-exact (no tolerance; "3" == "3.0"; not "30");
3. the temporal table exists for the check and matches through hyphenation repair;
4. aliases are never split into first-use variants;
5. the shared matcher is digit-exact;
6. a rejected value renders unverifiable, never "not reported".
"""

from __future__ import annotations

from typing import Any

import pytest

from conftest import stub_client
from extractor_mvp import render
from extractor_mvp.cobidas import _UNVERIFIABLE_GAP_BASES, assess_coverage
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract_preprocessing
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.quote_support import (
    NUMERIC_FIELDS,
    SUPPORT_TABLES,
    VALUE_UNSUPPORTED,
    literal_value_supported,
    number_in_quote,
    phrase_in_quote,
    step_value_supported,
    token_equivalent,
)
from extractor_mvp.synonym_resolver import TS_METHOD_SYNONYMS

TEXT = (
    "Methods\n"
    "Functional volumes were realigned to the mean image of each run.\n"
    "Data were normalized to MNI152 standard space and resampled to 2 mm.\n"
    "Images were registered to the FSL MNI152 template.\n"
    "Each run was normalized to a mode of 1,000 across all voxels.\n"
    "Finally, for each voxel, the signal was temporally normal-\n"
    "ized by subtracting its mean and dividing by its temporal standard deviation.\n"
)


def _paper(text: str = TEXT) -> ParsedPaper:
    return ParsedPaper(text=text, source="test", parser="manual")


def _payload(**fields: FieldExtractionResult) -> PreprocessingExtraction:
    none = FieldExtractionResult(status="missing")
    base = dict(
        target_space=none,
        resolution_mm=none,
        surface_registration=none,
        target_surface=none,
        intensity_convention=none,
        intensity_value=none,
        temporal_standardization_method=none,
    )
    base.update(fields)
    return PreprocessingExtraction(**base)


def _ex(value: Any, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _field(prep: Any, kind: str, name: str) -> Any:
    return getattr(next(s for s in prep.steps if s.kind == kind), name)


# ---------------------------------------------------------------------------
# Ruling 5 — the shared matcher is digit-exact; word forms for alphabetic tokens only
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("realignment", "realigned", True),
        ("coregistration", "coregistered", True),
        ("spatially", "spatial", True),
        ("mni152", "mni152nlin6asym", False),  # the prefix leak, closed
        # Motion DELTA §4 ruling 5 (2026-10-26): a letter-ending value may be followed by a digit run in the quote --
        # the text layer's citation-number artefact ("AFNI48", "Louis45"); under-claim only.
        ("spm", "spm12", True),  # was False before that ruling: an under-claim is now tolerated
        ("afni", "afni48", True),
        ("louis", "louis45", True),
        ("fsl", "fsl5", True),
        ("spm8", "spm12", False),  # the value ends in a digit: still exact
        ("spm12", "spm", False),  # the reverse direction is never tolerated
        ("afni48", "afni", False),
        ("spm", "spm12a", False),  # a digit run, not a mixed suffix
        ("3", "30", False),
        ("fsaverage5", "fsaverage", False),
        ("mode", "model", False),
    ],
)
def test_token_equivalence_is_digit_exact(a: str, b: str, expected: bool) -> None:
    assert token_equivalent(a, b) is expected


# ---------------------------------------------------------------------------
# Rulings 1 and 4 — alias of the value, taken whole, in the repaired quote
# ---------------------------------------------------------------------------
TS = "spatial_normalization.target_space"
CONV = "intensity_normalization.convention"
TEMP = "temporal_standardization.method"


def test_canonical_value_is_supported_by_an_alias_in_the_quote() -> None:
    # the model returned the canonical token; the quote carries a known alias
    assert literal_value_supported(
        CONV,
        "global_mode_1000",
        "global_mode_1000",
        "resolved",
        "Each run was normalized to a mode of 1,000 across all voxels.",
    )
    # an alias with the @value marker matches on its phrase alone
    assert literal_value_supported(
        CONV,
        "global_mode_1000",
        "global_mode_1000",
        "resolved",
        "intensity was scaled so the mode value was 1000",
    )
    # and not when no alias is present
    assert not literal_value_supported(
        CONV, "global_mode_1000", "global_mode_1000", "resolved", "intensities were left unscaled"
    )


def test_split_alias_is_rejected_whole_alias_passes() -> None:
    """Ruling 4: an alias is taken whole, so a quote naming only MNI152 does not support the specific
    template; the identifier does, and so does a file form (CALL 2's oconnor case).

    UPDATED 2026-10-26 (DELTA §7.7): the phrase forms "FSL MNI152" / "FSL's MNI152" / "MNI152 (FSL)"
    were removed from the table, so a quote naming FSL's MNI152 no longer supports the specific
    template either -- the phrase is family-level, and the family-level value it now resolves to IS
    supported by that quote.
    """
    assert not literal_value_supported(
        TS,
        "MNI152NLin6Asym",
        "MNI152NLin6Asym",
        "resolved",
        "Data were normalized to MNI152 standard space.",
    )
    assert not literal_value_supported(
        TS, "MNI152NLin6Asym", "MNI152NLin6Asym", "resolved", "normalized to MNI space"
    )
    assert not literal_value_supported(
        TS,
        "MNI152NLin6Asym",
        "MNI152NLin6Asym",
        "resolved",
        "Images were registered to the FSL MNI152 template.",
    )
    assert literal_value_supported(
        TS,
        "FSL MNI152",
        None,
        "underspecified",
        "Images were registered to the FSL MNI152 template.",
    )
    assert literal_value_supported(
        TS, "MNI152NLin6Asym", "MNI152NLin6Asym", "resolved", "warped to MNI152NLin6Asym"
    )
    assert literal_value_supported(
        TS, "MNI152_T1_2mm", "MNI152NLin6Asym", "resolved", "the MNI152_T1_2mm template"
    )


def test_underspecified_value_is_supported_by_a_family_term() -> None:
    assert literal_value_supported(TS, "MNI", None, "underspecified", "normalized to MNI space")
    assert literal_value_supported(TS, "MNI152", None, "underspecified", "mapped to MNI152 space")
    assert not literal_value_supported(TS, "MNI", None, "underspecified", "kept in native space")
    # the safe direction: a family term is supported by a quote whose identifier begins with it
    assert literal_value_supported(
        TS, "MNI152", None, "underspecified", "normalized to MNI152NLin6Asym"
    )
    # and never the reverse (the specific value against the family term)
    assert not literal_value_supported(
        TS, "MNI152NLin6Asym", "MNI152NLin6Asym", "resolved", "normalized to MNI152"
    )


def test_a_member_with_no_aliases_passes_through() -> None:
    """``other`` names nothing a quote could carry; it is a recorded limit, not a hole the check claims."""
    assert literal_value_supported(TEMP, "other", "other", "resolved", "any sentence at all")
    assert literal_value_supported(TS, "other", "other", "resolved", "any sentence at all")


def test_unrecognized_value_is_its_own_only_alias() -> None:
    assert literal_value_supported(
        TS, "atlas space", None, "unrecognized", "resampled in atlas space"
    )
    assert not literal_value_supported(TS, "atlas space", None, "unrecognized", "resampled to 3 mm")


def test_phrase_is_never_split_into_first_use_variants() -> None:
    # a phrase with a parenthetical matches only as a whole (synthetic strings)
    assert phrase_in_quote("Template (TPL)", "the Template (TPL) atlas")
    assert not phrase_in_quote("Template (TPL)", "Template standard space")


# ---------------------------------------------------------------------------
# Ruling 3 — the temporal table, matched on repaired text
# ---------------------------------------------------------------------------
def test_temporal_table_exists_for_the_check_and_carries_the_design_phrasings() -> None:
    assert SUPPORT_TABLES[TEMP][0] is TS_METHOD_SYNONYMS
    phr = TS_METHOD_SYNONYMS["voxel_temporal_zscore"]
    for must in (
        "temporally normalized",
        "temporal standard deviation",
        "z-scored over time",
        "z-scored",
    ):
        assert must in phr, must


@pytest.mark.parametrize(
    "quote",
    [
        # liu-shaped: hyphenated across a line break, repaired by the resolver's normaliser
        "for each voxel, the signal was temporally normal-\nized by subtracting its mean and dividing by its temporal standard deviation",
        # Cho-shaped: a z-scoring stem
        "after concatenation we applied z-scoring to the segments",
        "the BOLD time series were z-scored over time",
        "each voxel's time series was zscored",
    ],
)
def test_temporal_canonical_is_supported_by_the_design_phrasings(quote: str) -> None:
    assert literal_value_supported(
        TEMP, "voxel_temporal_zscore", "voxel_temporal_zscore", "resolved", quote
    )


def test_temporal_canonical_is_not_supported_by_an_unrelated_quote() -> None:
    assert not literal_value_supported(
        TEMP,
        "voxel_temporal_zscore",
        "voxel_temporal_zscore",
        "resolved",
        "correlations were Fisher z-transformed",
    )


# ---------------------------------------------------------------------------
# Ruling 2 — numbers, digit-exact
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "quote", "expected"),
    [
        (3.0, "resampled into 3 × 3 × 3 mm voxels", True),  # noqa: RUF001 -- the sign papers print
        (3.0, "resampled to 3mm isotropic", True),
        (2.0, "resampled to 2 mm", True),
        (3.0, "resampled to 2 mm", False),
        (3.0, "resampled to 3.5 mm", False),
        (3.0, "30 slices were acquired", False),
        (1000.0, "normalized to a mode of 1,000", True),
        (10000.0, "grand-mean scaled to 10000", True),
        (1000.0, "grand-mean scaled to 10000", False),
    ],
)
def test_number_in_quote_is_digit_exact(value: float, quote: str, expected: bool) -> None:
    assert number_in_quote(value, quote) is expected


def test_step_value_supported_dispatch() -> None:
    assert (
        step_value_supported("spatial_normalization.resolution_mm", 2.0, "resampled to 2 mm")
        is True
    )
    assert (
        step_value_supported("spatial_normalization.resolution_mm", 3.0, "resampled to 2 mm")
        is False
    )
    assert (
        step_value_supported("motion_correction.method", object(), "anything") is None
    )  # not covered
    assert "spatial_normalization.resolution_mm" in NUMERIC_FIELDS


# ---------------------------------------------------------------------------
# Through the extractor, and ruling 6 — unverifiable, never "not reported"
# ---------------------------------------------------------------------------
def test_unsupported_literal_value_is_demoted_and_supported_ones_stay() -> None:
    prep, _, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _payload(
                # specific template, quote names only MNI152 -> demoted
                target_space=_ex(
                    "MNI152NLin6Asym",
                    "Data were normalized to MNI152 standard space and resampled to 2 mm.",
                ),
                # number in the quote -> stays
                resolution_mm=_ex(
                    "2", "Data were normalized to MNI152 standard space and resampled to 2 mm."
                ),
                # canonical convention with its alias in the quote -> stays
                intensity_convention=_ex(
                    "global_mode_1000",
                    "Each run was normalized to a mode of 1,000 across all voxels.",
                ),
                intensity_value=_ex(
                    "1000", "Each run was normalized to a mode of 1,000 across all voxels."
                ),
                # the temporal canonical, through hyphenation repair -> stays
                temporal_standardization_method=_ex(
                    "voxel_temporal_zscore",
                    "Finally, for each voxel, the signal was temporally normal-\nized by subtracting its mean and dividing by its temporal standard deviation.",
                ),
            )
        ),
    )
    ts = _field(prep, "spatial_normalization", "target_space")
    assert ts.extraction.status == "MISSING_FROM_PAPER"
    assert ts.inference.reason == VALUE_UNSUPPORTED
    assert _field(prep, "spatial_normalization", "resolution_mm").extraction.status == "EXTRACTED"
    assert _field(prep, "intensity_normalization", "convention").extraction.status == "EXTRACTED"
    assert _field(prep, "intensity_normalization", "value").extraction.status == "EXTRACTED"
    assert _field(prep, "temporal_standardization", "method").extraction.status == "EXTRACTED"


def test_reason_is_unverifiable_and_mapped() -> None:
    assert VALUE_UNSUPPORTED in _UNVERIFIABLE_GAP_BASES
    assert render._REASON_BUCKET[VALUE_UNSUPPORTED] == "not_covered"
    assert "not reported" not in render._REASON_LINE[VALUE_UNSUPPORTED]


def test_demoted_row_renders_unverifiable_not_not_reported() -> None:
    prep, _, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _payload(
                target_space=_ex(
                    "MNI152NLin6Asym",
                    "Data were normalized to MNI152 standard space and resampled to 2 mm.",
                )
            )
        ),
    )
    rc = {c.row.row_id: c for c in assess_coverage(render.flatten(prep), None)}[
        "intersubject_registration"
    ]
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, False, True)
    out = render.to_cobidas_coverage(prep)
    assert (
        "- Intersubject registration  (examined; the extractor could not verify what it found)"
        in out
    )
    row = next(
        r
        for r in render.flatten(prep)
        if r.group == "spatial_normalization" and r.path.endswith("target_space")
    )
    assert "not reported in source" not in render._reason_detail(row)
