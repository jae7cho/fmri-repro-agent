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


def test_software_coverage_is_silent_only_for_the_unverifiable_conditions():
    """Ruled 2026-10-01 (DELTA_base_pipeline_diagnostic.md §4a): ``covered=False`` for the gaps where
    the extractor LOOKED and could not verify what it found; ``covered=True`` for the gap where it
    looked and found nothing.

    Before this, every one of these reached ``covered=True, addressed=False`` and the report counted
    the paper an unconditional COBIDAS violation — produced, for three of the four, by a span
    resolver failing rather than by anything the author did or did not write.

    The split is only possible because the reason lands. The rule READS the reason; it does not
    re-derive the condition, which is the point of the diagnostic.
    """
    cases = [
        # label, LeftMissing reason on the base_pipeline row, covered, unverifiable
        ("A no name returned", "no_base_pipeline_named", True, False),
        (
            "B quote not found",
            "extraction_quote_unresolved:base_pipeline_name:quote_not_found",
            False,
            True,
        ),
        (
            "B quote ambiguous",
            "extraction_quote_unresolved:base_pipeline_name:quote_ambiguous",
            False,
            True,
        ),
        ("C value unsupported", "base_pipeline_value_unsupported", False, True),
        ("4th deferral unresolved", "deferral_quote_unresolved:base_pipeline_ref", False, True),
    ]
    for label, reason, covered, unverifiable in cases:
        rc = _by_id(assess_coverage([_bp_row("MISSING_FROM_PAPER", reason)], None))["software"]
        assert rc.covered_by_extractor is covered, f"{label}: covered_by_extractor"
        assert rc.unverifiable is unverifiable, f"{label}: unverifiable"
        # Never addressed in any of these: the paper did not give a version either way.
        assert rc.addressed is False, f"{label}: addressed"
        # The section is emitted iff covered and not addressed, so silence falls out of covered.
        emitted = rc.covered_by_extractor and not rc.addressed
        assert emitted is covered, f"{label}: violation section emitted"


def test_the_version_arm_is_untouched_by_the_unverifiable_rule():
    """§10 scope line, pinned. A version row exists only when the outer arm resolved a PipelineRef,
    so base_pipeline is EXTRACTED and carries no gap reason — the unverifiable branch must not be
    reachable through the version arm. _build_version_pf's own four-way collapse is the larger half
    of this defect and ships separately; this test fails if that work is started here by accident.
    """
    for version_status in ("EXTRACTED", "MISSING_FROM_PAPER"):
        rc = _by_id(assess_coverage([_bp_row("EXTRACTED")], version_status))["software"]
        assert rc.covered_by_extractor is True, version_status
        assert rc.unverifiable is False, version_status
        assert rc.addressed is (version_status == "EXTRACTED"), version_status


def test_any_row_mapping_spec_kinds_can_now_be_unverifiable():
    """REPLACES ``test_only_the_software_row_can_be_unverifiable``, which asserted the opposite.

    That test was SUPERSEDED by the 2026-10-19 ruling, not deleted: its input already carried
    ``extraction_quote_unresolved`` on a non-Software row, and its own docstring said it would fail
    first if another row became unverifiable. It has, so the same input now pins the new rule — a
    superseded guard that merely disappears leaves the property it protected unguarded.
    """
    rows = [
        _bp_row("MISSING_FROM_PAPER", "base_pipeline_value_unsupported"),
        _fr(
            "motion_correction", "MISSING_FROM_PAPER", "extraction_quote_unresolved:quote_not_found"
        ),
        _fr("spatial_smoothing", "MISSING_FROM_PAPER", "not_targeted_by_mvp"),
    ]
    flagged = sorted(rc.row.row_id for rc in assess_coverage(rows, None) if rc.unverifiable)
    assert flagged == ["motion_correction", "software"], flagged
    # and the untargeted row is NOT swept in with them
    by = _by_id(assess_coverage(rows, None))
    assert by["spatial_smoothing"].unverifiable is False
    assert by["spatial_smoothing"].covered_by_extractor is False


# ---------------------------------------------------------------------------
# The precedence, ruled 2026-10-19 (DELTA_conditional_row_unverifiable.md §2).
# One test per level, so a mutation to one level fails exactly one test.
# ---------------------------------------------------------------------------
def test_precedence_level_1_addressed_beats_everything():
    """An EXTRACTED or DEFERRED field addresses the row, whatever else is on it."""
    for status in ("EXTRACTED", "DEFERRED_TO_CITATION"):
        rows = [
            _bp_row(None),
            _fr("spatial_normalization", status),
            _fr(
                "surface_projection",
                "MISSING_FROM_PAPER",
                "extraction_quote_unresolved:quote_not_found",
            ),
        ]
        rc = _by_id(assess_coverage(rows, None))["intersubject_registration"]
        assert rc.addressed is True, status
        assert rc.unverifiable is False, status
        assert rc.covered_by_extractor is True, status


def test_precedence_level_2_unverifiable_beats_not_reported():
    """The reason §2 gives: the failed quote may be exactly where the paper reported the step, so
    "not reported" would be a false statement rather than a cautious one."""
    rows = [
        _bp_row(None),
        _fr(
            "spatial_normalization",
            "MISSING_FROM_PAPER",
            "extraction_quote_unresolved:quote_not_found",
        ),
    ]
    rc = _by_id(assess_coverage(rows, None))["intersubject_registration"]
    assert rc.addressed is False
    assert rc.unverifiable is True
    assert rc.covered_by_extractor is False


def test_precedence_level_3_a_plain_absence_is_still_not_reported():
    """The negative control for level 2: a gap reason that is NOT in the set leaves the row
    exactly as it was, so level 2 is shown to discriminate rather than to flag everything."""
    rows = [_bp_row(None), _fr("spatial_normalization", "MISSING_FROM_PAPER", "not_stated_in_text")]
    rc = _by_id(assess_coverage(rows, None))["intersubject_registration"]
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, True, False)


def test_precedence_ordering_is_level_1_then_level_2():
    """Mixing one addressing field with one unverifiable field must give ADDRESSED.

    Reversing the two levels would read this row as unverifiable and silence a row the paper
    actually reported — the inverse of the defect the ruling fixes.
    """
    rows = [
        _bp_row(None),
        _fr("spatial_normalization", "EXTRACTED"),
        _fr(
            "spatial_normalization",
            "MISSING_FROM_PAPER",
            "extraction_quote_unresolved:quote_not_found",
        ),
    ]
    rc = _by_id(assess_coverage(rows, None))["intersubject_registration"]
    assert (rc.addressed, rc.unverifiable) == (True, False)


def test_optional_rows_follow_the_same_rule():
    """Ruling 5: one rule for every row that maps to spec kinds. intensity_normalization is the
    only non-mandatory row the extractor targets, and it is the real case —
    batch_sfn_v5/papers/mueller_2021.json carries quote_not_found on both its fields."""
    rows = [
        _bp_row(None),
        _fr(
            "intensity_normalization",
            "MISSING_FROM_PAPER",
            "extraction_quote_unresolved:quote_not_found",
        ),
    ]
    rc = _by_id(assess_coverage(rows, None))["intensity_normalization"]
    assert rc.row.mandatory is False
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, False, True)


def test_unverifiable_implies_not_covered():
    """Ruling 4. The both-true state is SILENT, not loud: render builds its unverifiable list from
    ``mand_not_assessed``, so such a row would count as assessed, skip the third counter and
    render as a bare line. Nothing would have failed."""
    import pytest

    with pytest.raises(ValueError, match="unverifiable implies not covered_by_extractor"):
        RowCoverage(
            row=COBIDAS_D3_ROWS[0], addressed=False, covered_by_extractor=True, unverifiable=True
        )
    # the legal states all still construct
    for cov, unv in ((True, False), (False, True), (False, False)):
        RowCoverage(
            row=COBIDAS_D3_ROWS[0], addressed=False, covered_by_extractor=cov, unverifiable=unv
        )


def test_the_software_deferral_rule_is_unchanged():
    """Positive re-test, required by the DELTA's acceptance because one rejected reading of the
    ruling (R2) would have overturned DELTA_software_row_deferral.md silently.

    A DEFERRED_TO_CITATION base_pipeline does NOT address the Software row, and a version row
    answers it when one exists. Both are re-asserted here rather than merely left unbroken.
    """
    deferred = _bp_row("DEFERRED_TO_CITATION", "deferred_to_citation")
    rc = _by_id(assess_coverage([deferred], None))["software"]
    assert rc.addressed is False, "a deferral must not address the Software row"
    assert rc.unverifiable is False, "deferred_to_citation is not a gap reason"
    # the version arm still answers when a version row exists
    extracted_bp = _bp_row("EXTRACTED")
    assert _by_id(assess_coverage([extracted_bp], "EXTRACTED"))["software"].addressed is True
    assert _by_id(assess_coverage([extracted_bp], "MISSING_FROM_PAPER"))["software"].addressed is (
        False
    )


def test_every_gap_base_in_the_set_is_matched_by_gap_base():
    """Acceptance item 8: a base cannot be silently reclassified by editing one frozenset, and the
    two KB bases must be REACHABLE — ruling 6 exists so they are no longer free text."""
    from extractor_mvp.cobidas import _UNVERIFIABLE_GAP_BASES, _gap_base

    assert _UNVERIFIABLE_GAP_BASES == frozenset(
        {
            "extraction_quote_unresolved",
            "base_pipeline_value_unsupported",
            "deferral_quote_unresolved",
            "extraction_quote_missing",
            "kb_ambiguous",
        }
    )
    # every member matches through _gap_base, suffixed as the producers emit them
    for base in _UNVERIFIABLE_GAP_BASES:
        assert _gap_base(f"{base}:some_suffix") in _UNVERIFIABLE_GAP_BASES, base
    # and the deliberately-excluded bases stay out, each for its recorded reason
    for excluded in (
        "deferred_to_citation",  # sits on a DEFERRED_TO_CITATION field
        "citation_shaped_name_value_unsupported",  # ditto
        "field_not_in_schema_version",  # the extractor never looked
        "not_targeted_by_mvp",  # the untargeted case itself
        "kb_not_applicable",  # a NotApplicable verdict, not a gap
        "not_stated_in_text",  # a claim about the paper
    ):
        assert excluded not in _UNVERIFIABLE_GAP_BASES, excluded
