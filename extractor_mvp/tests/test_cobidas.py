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


def _bp_row(extraction_status: str | None, reason: str | None = None) -> FieldRow:
    """The OUTER base_pipeline row exactly as ``flatten()`` emits it.

    ``path`` must be literally ``base_pipeline`` — the ``base_pipeline.version`` row shares
    the same ``group``, so the software rule selects on path.
    """
    return FieldRow(
        path="base_pipeline",
        group="base_pipeline",
        state=extraction_status or "BASE_NOT_APPLICABLE",
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


def test_software_coverage_over_every_base_pipeline_state() -> None:
    """(covered, addressed) for the Software row under every base_pipeline state, A-F.

    REPLACES ``test_software_addressed_iff_version_extracted``, which asserted over
    ``assess_coverage([], "EXTRACTED")`` — no base_pipeline row, yet a version status. That
    input cannot occur: ``flatten()`` emits a version row only when the outer arm resolved a
    PipelineRef, so a version status always implies a base_pipeline row. The old test was
    pinning behaviour for an impossible state, which is why it did not catch the deferral bug.

    ``addressed`` answers "did the PAPER answer the software question?" and has two arms —
    the version row's status when one exists, else the base_pipeline row's own status.
    ``covered`` answers "did the EXTRACTOR look?".
    """
    cases = [
        # label, base_pipeline row, version status, covered, addressed
        ("A extracted + version reported", _bp_row("EXTRACTED"), "EXTRACTED", True, True),
        ("B extracted, version missing", _bp_row("EXTRACTED"), "MISSING_FROM_PAPER", True, False),
        (
            "C searched, none named",
            _bp_row("MISSING_FROM_PAPER", "no_base_pipeline_named"),
            None,
            True,
            False,
        ),
        (
            # Ruled 2026-09-07: a deferral answers pipeline identity, not version, and the
            # row's mandatory content is version and revision number. Was True until the
            # DELTA; see docs/design/DELTA_software_row_deferral.md.
            "D deferred to citation",
            _bp_row("DEFERRED_TO_CITATION", "deferred_to_citation"),
            None,
            True,
            False,
        ),
        (
            "E untargeted (unreachable today)",
            _bp_row("MISSING_FROM_PAPER", "not_targeted_by_mvp"),
            None,
            False,
            False,
        ),
        ("F NotApplicable", _bp_row(None), None, False, False),
    ]
    for label, bp, ver, covered, addressed in cases:
        rc = _by_id(assess_coverage([bp], ver))["software"]
        assert rc.covered_by_extractor is covered, f"{label}: covered_by_extractor"
        assert rc.addressed is addressed, f"{label}: addressed"


def test_deferred_pipeline_addresses_identity_not_version() -> None:
    """A citing paper answers pipeline IDENTITY; the Software row asks for the VERSION.

    SUPERSEDES ``test_deferred_pipeline_is_not_a_software_violation``, which asserted
    ``addressed is True`` here. That test was correct under A3's ruling (``c9c2951``) and is
    replaced rather than silently inverted — its name asserted the proposition now reversed,
    so a successor under the old name would read as the old claim.

    Its diagnosis still stands and is not what changed: keying software coverage off the
    version row alone left a deferral unaddressed, so the report accused a citing paper of an
    unconditional COBIDAS violation. It fired on real corpus papers (braun_2015, whose span
    reads "preprocessed according to standard protocols as previously described in refs. 47
    and 48"; also viduarre_2017). What is superseded is the REPAIR: the false part was the
    accusation's wording, not the finding. The row is unaddressed, and the line beneath the
    heading now names the citation instead of reading as an unnamed-software report.
    See docs/design/DELTA_software_row_deferral.md.
    """
    rc = _by_id(assess_coverage([_bp_row("DEFERRED_TO_CITATION", "deferred_to_citation")], None))[
        "software"
    ]
    assert rc.addressed is False and rc.covered_by_extractor is True


def test_searched_but_none_named_is_covered_like_any_other_row() -> None:
    """The whole point of the fix: software obeys the rule the other 15 rows already follow.

    A field the extractor targeted and found nothing for is COVERED (compare
    ``test_targeted_missing_field_is_covered_by_extractor``), so it renders as a claim about
    the paper rather than disappearing into the tool-gap bucket.
    """
    rc = _by_id(assess_coverage([_bp_row("MISSING_FROM_PAPER", "no_base_pipeline_named")], None))[
        "software"
    ]
    assert rc.covered_by_extractor is True and rc.addressed is False


def test_registry_denominator_is_static_not_steps_present() -> None:
    """``assess_coverage`` returns all 16 D.3 rows whatever the spec contains.

    This is the property the cobidas.py fence protected: the denominator comes from the
    STANDARD, not from the steps present. Computed over present steps it would measure tool
    coverage and report it as compliance.
    """
    for rows in ([], [_fr("spatial_normalization", "EXTRACTED")], [_bp_row("EXTRACTED")]):
        cov = assess_coverage(rows, None)
        assert len(cov) == 16
        assert [rc.row.row_id for rc in cov] == [r.row_id for r in COBIDAS_D3_ROWS]


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
