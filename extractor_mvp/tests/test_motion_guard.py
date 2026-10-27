"""The motion value-in-quote post-check — ``motion_guard.py``, DELTA_value_in_quote_motion.md §4.

Every string here is synthetic. No sentence from any corpus paper appears, held-out or otherwise.

What is pinned, per ruling:
* ruling 1 — the check runs after ``_process_field`` and never reasks: exactly ONE completion,
  the raw ``FieldExtractionResult`` captured by ``raw_out`` is the model's own, and the demotion
  is visible only on the processed layer;
* rulings 2-3 — every motion value is checked, and word forms match;
* ruling 4 — CompCor / ICA-FIX / ICA-AROMA route off the method with their own reason, checked
  AFTER support (an absent structured-noise tool is reported as unsupported);
* the conditional-row rule — both reasons are members of ``cobidas._UNVERIFIABLE_GAP_BASES``, are
  mapped in both render tables, and a demoted motion row renders as *examined; could not verify*,
  never as *not reported*.
"""

from __future__ import annotations

from typing import Any

import pytest

from conftest import stub_client  # tests/ is on sys.path via pytest rootdir insertion
from extractor_mvp import render
from extractor_mvp.cobidas import _UNVERIFIABLE_GAP_BASES, assess_coverage
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    MotionMethodExtraction,
    PreprocessingExtraction,
    extract_motion_method,
    extract_preprocessing,
)
from extractor_mvp.motion_guard import (
    MOTION_VALUE_ROUTED,
    MOTION_VALUE_UNSUPPORTED,
    motion_post_check,
    quote_supports_value_inflected,
    structured_noise_tool,
)
from extractor_mvp.parsed_paper import ParsedPaper

# Synthetic methods text. Three sentences: a realignment sentence that names no tool, a package
# sentence two lines away, and a denoising sentence that names a structured-noise tool as the
# motion step (CALL 4's shape).
TEXT = (
    "Methods\n"
    "All analyses were performed with ToolKit 9.\n"
    "Functional volumes were realigned to the mean image of each run.\n"
    "Motion correction via DenoiseICA-AROMA (version 1.0) was then applied.\n"
    "Data were normalized to MNI152NLin6Asym at 2 mm.\n"
)


def _paper(text: str = TEXT) -> ParsedPaper:
    return ParsedPaper(text=text, source="test", parser="manual")


def _prep_payload() -> PreprocessingExtraction:
    none = FieldExtractionResult(status="missing")
    return PreprocessingExtraction(
        target_space=none,
        resolution_mm=none,
        surface_registration=none,
        target_surface=none,
        intensity_convention=none,
        intensity_value=none,
    )


def _motion(status: str, **kw: Any) -> MotionMethodExtraction:
    # version 3 (2026-10-26): an extracted payload must state its binding; these fixtures are the
    # paper's-own-words shape, so "described_only" unless a test says otherwise.
    binding = kw.pop("binding", "described_only" if status == "extracted" else None)
    return MotionMethodExtraction(
        motion_correction_method=FieldExtractionResult(status=status, **kw),
        motion_correction_binding=binding,
    )


def _method(prep: Any) -> Any:
    return next(s for s in prep.steps if s.kind == "motion_correction").method


# ---------------------------------------------------------------------------
# The pure check (rulings 2-4), on synthetic strings
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "quote", "expected"),
    [
        # exact, the ordinary case
        ("realigned", "Functional volumes were realigned to the mean image.", True),
        # rulings 2-3: word forms
        ("realignment", "Functional volumes were realigned to the mean image.", True),
        ("realigning", "a realignment of all volumes to a reference", True),
        (
            "spatial coregistration using an iterative procedure",
            "images were spatially coregistered using an iterative procedure that minimizes",
            True,
        ),
        ("image", "between images", True),
        # a multi-word value must be contiguous in the quote
        ("mean realigned", "realigned to the mean image", False),
        # the 30-carry shape: a tool from another sentence
        ("ToolKit 9", "Functional volumes were realigned to the mean image.", False),
        ("ACRONYM", "an iterative procedure that minimizes variance (Author, 1999b)", False),
        # short tokens must match exactly: "spm" is not supported by "spm12"
        # flipped 2026-10-26 by motion DELTA §4 ruling 5: an under-claim is tolerated
        ("SPM", "realigned using SPM12", True),
        # digit-exact (2026-10-26 tightening): an identifier is not supported by a prefix of it
        ("MNI152NLin6Asym", "normalized to MNI152 standard space", False),
        ("SPM12", "performed with SPM12b", False),
        ("SPM12", "realigned using SPM12", True),
        # hyphen and case
        ("Denoise-ICA-AROMA", "via DenoiseICA-AROMA (version 1.0)", False),
        ("ICA-AROMA", "motion correction via ICA-AROMA (version 1.0)", True),
        # first-use variant
        ("Motion Correction Tool (MCT)", "we used MCT for realignment", True),
        # empties
        ("", "anything", False),
        ("realigned", "", False),
    ],
)
def test_inflection_tolerant_support(value: str, quote: str, expected: bool) -> None:
    assert quote_supports_value_inflected(value, quote) is expected


def test_citation_number_attached_to_a_package_name_is_tolerated_under_claim_only() -> None:
    """Motion DELTA §4 ruling 5 (2026-10-26): the text layer attaches a citation number to the word before it, so
    a package-level value is supported by a quote in which the package name carries a digit run.
    Under-claim only: a value that ends in a digit still matches exactly."""
    from extractor_mvp.motion_guard import quote_supports_value_inflected

    quote = "Images were processed with AFNI12 and a surface package13 before realignment"
    assert quote_supports_value_inflected("AFNI", quote) is True
    assert quote_supports_value_inflected("AFNI12", quote) is True
    assert quote_supports_value_inflected("AFNI1", quote) is False  # ends in a digit: exact only
    assert quote_supports_value_inflected("SPM8", "realigned with SPM12 in MATLAB") is False
    assert quote_supports_value_inflected("SPM", "realigned with SPM12 in MATLAB") is True


@pytest.mark.parametrize(
    ("value", "tool"),
    [
        ("ICA-AROMA", "ica_aroma"),
        ("motion correction via ICA-AROMA", "ica_aroma"),
        ("ICA FIX", "ica_fix"),
        ("ICA-FIX", "ica_fix"),
        ("CompCor", "compcor"),
        ("aCompCor", "compcor"),
        ("tCompCor", "compcor"),
        ("MCFLIRT", None),
        ("realigned", None),
        ("ICA", None),  # the bare acronym names no row
        ("fix", None),
    ],
)
def test_structured_noise_routing_table(value: str, tool: str | None) -> None:
    assert structured_noise_tool(value) == tool


def test_post_check_order_support_before_routing() -> None:
    # supported and routed -> routed
    assert motion_post_check("ICA-AROMA", "motion correction via ICA-AROMA") == (
        f"{MOTION_VALUE_ROUTED}:ica_aroma"
    )
    # named but NOT in the quote -> unsupported wins, the more general finding
    assert (
        motion_post_check("ICA-AROMA", "Functional volumes were realigned to the mean image.")
        == MOTION_VALUE_UNSUPPORTED
    )
    # supported, not routed -> keep
    assert motion_post_check("realignment", "volumes were realigned") is None
    # nothing to check -> unsupported, never keep
    assert motion_post_check(None, "x") == MOTION_VALUE_UNSUPPORTED
    assert motion_post_check("x", None) == MOTION_VALUE_UNSUPPORTED


# ---------------------------------------------------------------------------
# Ruling 1 — a post-check on the processed layer, no reask
# ---------------------------------------------------------------------------
def test_unsupported_value_is_demoted_after_resolution_with_one_completion() -> None:
    counter: dict[str, int] = {}
    raw_out: list[FieldExtractionResult] = []
    # the quote RESOLVES (it is in TEXT); the value is taken from the package sentence
    pf, diag, _ = extract_motion_method(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="ToolKit 9",
                verbatim_quote="Functional volumes were realigned to the mean image of each run.",
            ),
            counter=counter,
        ),
        raw_out=raw_out,
    )
    assert counter == {"MotionMethodExtraction": 1}, counter  # no reask
    assert (
        raw_out[0].motion_correction_method.value == "ToolKit 9"
    )  # the raw layer is the model's own
    assert raw_out[0].motion_correction_binding == "described_only"
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == MOTION_VALUE_UNSUPPORTED
    assert diag is not None and diag.failure_reason == MOTION_VALUE_UNSUPPORTED
    assert diag.raw_value == "ToolKit 9"


def test_routed_tool_is_demoted_with_the_tool_in_its_reason() -> None:
    pf, diag, _ = extract_motion_method(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="ICA-AROMA",
                verbatim_quote="Motion correction via DenoiseICA-AROMA (version 1.0) was then applied.",
            ),
        ),
    )
    # NOTE the quote's token is "denoiseica", so "ICA-AROMA" is NOT supported by it -> unsupported
    assert pf.inference.reason == MOTION_VALUE_UNSUPPORTED
    text = TEXT.replace("DenoiseICA-AROMA", "ICA-AROMA")
    pf, diag, _ = extract_motion_method(
        _paper(text),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="ICA-AROMA",
                verbatim_quote="Motion correction via ICA-AROMA (version 1.0) was then applied.",
            ),
        ),
    )
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == f"{MOTION_VALUE_ROUTED}:ica_aroma"
    assert diag is not None and diag.failure_reason == f"{MOTION_VALUE_ROUTED}:ica_aroma"


def test_supported_inflected_value_stays_extracted() -> None:
    pf, diag, _ = extract_motion_method(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="realignment",
                verbatim_quote="Functional volumes were realigned to the mean image of each run.",
            ),
        ),
    )
    assert pf.extraction.status == "EXTRACTED"
    assert pf.extraction.value.verbatim == "realignment"
    assert diag is None


@pytest.mark.parametrize(
    ("payload", "expect_reason"),
    [
        (_motion("missing"), "not_stated_in_text"),
        (
            _motion("extracted", value="realigned", verbatim_quote="nowhere in the text"),
            "extraction_quote_unresolved:quote_not_found",
        ),
    ],
    ids=["missing_untouched", "unresolved_untouched"],
)
def test_non_extracted_outcomes_are_untouched(payload: Any, expect_reason: str) -> None:
    """The post-check sees only an EXTRACTED processed field; everything else passes through."""
    pf, _, _ = extract_motion_method(
        _paper(), "m", client=stub_client(_prep_payload(), motion=payload)
    )
    assert pf.inference.reason == expect_reason


# ---------------------------------------------------------------------------
# The conditional-row rule — unverifiable, never "not reported"
# ---------------------------------------------------------------------------
def test_both_reasons_are_unverifiable_gap_bases_and_mapped() -> None:
    for base in (MOTION_VALUE_UNSUPPORTED, MOTION_VALUE_ROUTED):
        assert base in _UNVERIFIABLE_GAP_BASES, base
        assert render._REASON_BUCKET[base] == "not_covered", base
        assert "not reported" not in render._REASON_LINE[base], base


@pytest.mark.parametrize(
    ("value", "quote", "reason_prefix"),
    [
        (
            "ToolKit 9",
            "Functional volumes were realigned to the mean image of each run.",
            MOTION_VALUE_UNSUPPORTED,
        ),
        (
            "ICA-AROMA",
            "Motion correction via ICA-AROMA (version 1.0) was then applied.",
            MOTION_VALUE_ROUTED,
        ),
    ],
    ids=["unsupported", "routed"],
)
def test_demoted_motion_row_renders_unverifiable_not_not_reported(
    value: str, quote: str, reason_prefix: str
) -> None:
    text = TEXT.replace("DenoiseICA-AROMA", "ICA-AROMA")
    prep, _, _ = extract_preprocessing(
        _paper(text),
        "m",
        client=stub_client(
            _prep_payload(), motion=_motion("extracted", value=value, verbatim_quote=quote)
        ),
    )
    assert _method(prep).inference.reason.startswith(reason_prefix)
    rc = {c.row.row_id: c for c in assess_coverage(render.flatten(prep), None)}["motion_correction"]
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, False, True)
    out = render.to_cobidas_coverage(prep)
    assert "- Motion correction  (examined; the extractor could not verify what it found)" in out
    assert "- Motion correction  (no fields assessed by current extractor)" not in out
    # and the per-field wording never claims the paper said nothing
    row = next(
        r
        for r in render.flatten(prep)
        if r.group == "motion_correction" and r.path.endswith("method")
    )
    assert "not reported in source" not in render._reason_detail(row)
