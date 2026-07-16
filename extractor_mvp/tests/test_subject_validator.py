"""Unit tests for the INERT subject validator. Quotes are VERBATIM from the arm-1 raw dumps.

The validator is measured, not wired: these tests lock its lexical behavior on the four arm-1
cases plus the two known holes. A regression on liu (the true positive) is a design failure, not
a tuning problem — see the STOP note there.
"""

from __future__ import annotations

from extractor_mvp.subject_validator import derived_subject_term

# --- verbatim arm-1 quotes (extractor_mvp/results/*.jsonl) ---
LIU = (
    "Finally, for each voxel, the fMRI signal was temporally normalized by subtracting its mean "
    "and then dividing by its temporal standard deviation (SD)."
)
CHEN_PLAIN = (
    "This surface-based SFC was estimated using the same preprocessed rfMRI data as ReHo but "
    "normalized (0 mean and 1 variance)."
)
CHEN_OF_NOTE = "Of note, " + CHEN_PLAIN[0].lower() + CHEN_PLAIN[1:]
# The U+00D7 multiplication signs below are verbatim from the paper/dump — kept, not ASCII 'x'.
VIDUARRE = (
    "Such time series (size: number of participants× number of scans× number of time points× "  # noqa: RUF001
    "number of ICA components= 820 × 4 × 1,200 × 50) were finally standardized so that, for each "  # noqa: RUF001
    "scan, subject, and ICA component, the data have a mean of 0 and SD of 1."
)
DEROSA = (
    "Activation patterns were standardized prior to further analysis to ensure consistency across "
    "parcels and sessions."
)


def test_liu_true_positive_must_pass() -> None:
    # TRUE POSITIVE: a real voxelwise BOLD z-scoring. MUST be None. A flag here is the design
    # failing (STOP), not something to tune around.
    assert derived_subject_term(LIU) is None


def test_chen_both_variants_flag_connectivity_from_prompt_taxonomy() -> None:
    for q in (CHEN_PLAIN, CHEN_OF_NOTE):
        r = derived_subject_term(q)
        assert r is not None, q
        assert r.source == "prompt"  # SFC/ReHo are named in the DECISION RULE
        assert r.term.lower() in {"sfc", "reho"}


def test_viduarre_flags_ica_from_prompt_taxonomy() -> None:
    # NAMED-but-overridden: the DECISION RULE lists ICA/PCA components; the model extracted anyway.
    r = derived_subject_term(VIDUARRE)
    assert r is not None
    assert r.source == "prompt"
    assert "ica" in r.term.lower()


def test_derosa_flags_activation_from_declared_extension() -> None:
    # NOT-NAMED: "activation patterns" is absent from the DECISION RULE; caught only via the
    # declared extension. source must be "extension", never "prompt".
    r = derived_subject_term(DEROSA)
    assert r is not None
    assert r.source == "extension"
    assert "activation" in r.term.lower()


def test_downstream_derived_mention_after_verb_is_not_flagged() -> None:
    # The whole reason for the before-verb window: FC is named AFTER the verb (downstream), so the
    # BOLD-signal z-scoring stays a true positive.
    q = "The BOLD time series were z-scored before computing functional connectivity."
    assert derived_subject_term(q) is None


def test_active_voice_is_a_documented_known_hole() -> None:
    # KNOWN HOLE (by design): active voice puts the derived object AFTER the verb, so the
    # subject-before-verb scan cannot see it. Asserted explicitly so the hole is a fixed,
    # visible property rather than an accident.
    q = "We normalized the SFC map to zero mean and unit variance."
    assert derived_subject_term(q) is None  # NOT caught — active voice hole


def test_quote_with_no_normalization_verb_is_none() -> None:
    assert (
        derived_subject_term("Functional connectivity matrices were computed for each subject.")
        is None
    )
