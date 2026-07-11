"""COBIDAS D.3 registry + coverage-predicate tests (pure, no LLM/IO)."""

from __future__ import annotations

from extractor_mvp.cobidas import (
    COBIDAS_D3_ROWS,
    DIVERGENCE_KINDS,
    RowCoverage,
    assess_coverage,
)
from extractor_mvp.render import FieldRow


def _fr(group: str, extraction_status: str, reason: str | None = None) -> FieldRow:
    return FieldRow(
        path=f"{group}.f",
        group=group,
        state=extraction_status,
        extraction_status=extraction_status,
        left_missing_reason=reason,
    )


def _by_id(rows: list[RowCoverage]) -> dict[str, RowCoverage]:
    return {rc.row.row_id: rc for rc in rows}


# --- registry ---------------------------------------------------------------


def test_registry_shape() -> None:
    assert len(COBIDAS_D3_ROWS) == 16
    assert sum(1 for r in COBIDAS_D3_ROWS if r.mandatory) == 14
    non_mandatory = {r.row_id for r in COBIDAS_D3_ROWS if not r.mandatory}
    assert non_mandatory == {"software_citation", "intensity_normalization"}
    unconditional = [r for r in COBIDAS_D3_ROWS if r.unconditional]
    assert len(unconditional) == 1 and unconditional[0].row_id == "software"


def test_intersubject_registration_maps_both_kinds_one_row() -> None:
    rows = [r for r in COBIDAS_D3_ROWS if r.row_id == "intersubject_registration"]
    assert len(rows) == 1  # ONE D.3 row, not two
    assert set(rows[0].spec_kinds) == {"spatial_normalization", "surface_projection"}


def test_divergence_kinds_have_no_row() -> None:
    mapped_kinds = {k for r in COBIDAS_D3_ROWS for k in r.spec_kinds}
    for kind in DIVERGENCE_KINDS:
        assert kind not in mapped_kinds


# --- predicate: extraction-arm only -----------------------------------------


def test_one_extracted_field_addresses_row() -> None:
    cov = _by_id(assess_coverage([_fr("motion_correction", "EXTRACTED")], None))
    assert cov["motion_correction"].addressed is True


def test_all_missing_is_unaddressed() -> None:
    cov = _by_id(
        assess_coverage(
            [_fr("motion_correction", "MISSING_FROM_PAPER", "not_stated_in_text")], None
        )
    )
    assert cov["motion_correction"].addressed is False


def test_deferred_to_citation_addresses_row() -> None:
    cov = _by_id(assess_coverage([_fr("coregistration", "DEFERRED_TO_CITATION")], None))
    assert cov["coregistration"].addressed is True


def test_inferred_default_only_does_not_address() -> None:
    # An inferred value is not a *report*: extraction arm is MISSING_FROM_PAPER -> unaddressed.
    row = _fr("spatial_normalization", "MISSING_FROM_PAPER", "not_stated_in_text")
    row.inference_status = "INFERRED_DEFAULT"
    cov = _by_id(assess_coverage([row], None))
    assert cov["intersubject_registration"].addressed is False


def test_intersubject_addressed_via_either_kind() -> None:
    # A surface_projection EXTRACTED field addresses the shared row even with spatial missing.
    rows = [
        _fr("spatial_normalization", "MISSING_FROM_PAPER", "not_stated_in_text"),
        _fr("surface_projection", "EXTRACTED"),
    ]
    assert _by_id(assess_coverage(rows, None))["intersubject_registration"].addressed is True


# --- software row special case ----------------------------------------------


def test_software_addressed_iff_version_extracted() -> None:
    assert _by_id(assess_coverage([], "EXTRACTED"))["software"].addressed is True
    # date_inferred_version leaves the extraction arm MISSING -> NOT addressed (a violation).
    assert _by_id(assess_coverage([], "MISSING_FROM_PAPER"))["software"].addressed is False
    assert _by_id(assess_coverage([], None))["software"].addressed is False


# --- covered-by-extractor (tool gap vs source gap) --------------------------


def test_untargeted_fields_are_not_covered_by_extractor() -> None:
    rows = [_fr("brain_extraction", "MISSING_FROM_PAPER", "not_targeted_by_mvp")]
    assert _by_id(assess_coverage(rows, None))["brain_extraction"].covered_by_extractor is False


def test_targeted_missing_field_is_covered_by_extractor() -> None:
    rows = [_fr("spatial_normalization", "MISSING_FROM_PAPER", "not_stated_in_text")]
    rc = _by_id(assess_coverage(rows, None))["intersubject_registration"]
    assert rc.covered_by_extractor is True and rc.addressed is False


def test_never_emitted_kind_row_is_not_covered() -> None:
    # No FieldRows at all for motion_correction (never emitted) -> not covered by extractor.
    assert _by_id(assess_coverage([], None))["motion_correction"].covered_by_extractor is False
