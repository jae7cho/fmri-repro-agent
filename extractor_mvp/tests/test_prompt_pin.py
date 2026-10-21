"""The shared prompt is pinned, because changing it re-vintages every field.

Ruling A, 2026-10-19 (``docs/design/DESIGN_motion_correction_extraction.md`` §4): new step kinds get
their OWN call rather than a stanza in ``EXTRACTION_PROMPT``, and the shared prompt is frozen with its
hash pinned here. The point is not that the prompt may never change — it is that changing it becomes a
DELIBERATE act with a dated vintage note, instead of a side effect of adding a row.

The cost is measured, not assumed: the v1→v2 prompt change coerced 5 of 7 MNI terms at the shipped
EXTRACTED level (6 of 7 at the raw value level; oconnor_2017's v2 raw value was the coerced term but
failed span resolution). See ``docs/findings/sfn-v1-v2-delta-coercion.md``.
"""

from __future__ import annotations

import hashlib
import re

from extractor_mvp.extractor import (
    EXTRACTION_PROMPT,
    MOTION_METHOD_PROMPT,
    PER_ACQUISITION_EXTRACTION_PROMPT,
)
from extractor_mvp.subject_validator import _PROMPT_TAXONOMY

#: sha256 of the two constants actually sent to the model, pinned 2026-10-21 at HEAD ef10931.
#: UPDATING EITHER VALUE IS A VINTAGE EVENT. See the failure message below.
_PINNED = {
    "EXTRACTION_PROMPT": "31a050b291161c31d5b535b2411234df12b484039a436b7a85df6b4081b77535",
    "PER_ACQUISITION_EXTRACTION_PROMPT": (
        "04ba3cb76b55342cee2ed2fd8b62fb515226fdb21511c6803f380d51913c4648"
    ),
    #: The motion stanza, pinned 2026-10-21 BEFORE the reachability probe runs. This is what makes
    #: prereg C2 ("committed BEFORE the run") and C21 ("the vocabulary may not be extended after
    #: seeing output") checkable rather than remembered: the probe recorder writes this hash into
    #: its provenance header, so every draw names the stanza it ran under, and a stanza edited
    #: mid-probe cannot be passed off as the pre-registered one.
    #:
    #: C11 DOES license iterating this wording on the six already-contaminated probe papers. Such
    #: an iteration is a deliberate update here plus a new header hash on the draws that follow —
    #: not a silent edit. It does NOT license iterating on liu_2005, tang_2025 or wheaton_2004.
    #: UPDATED 2026-10-21, before any run, by author review of the stanza. Superseded value was
    #: 5242bc5f73261c2230b2453f7173f32a0594c7ceb30f49d2c7fd38532a6bb80d. Two defects, both of which
    #: would have corrupted the probe rather than merely degraded it:
    #:
    #:   * STEP 4's deferral arm was unscoped. It fired whenever the estimate was "attributed to" a
    #:     citation or a package with unnamed internals, which catches TWO probe papers whose
    #:     committed label is `described_only` -- binder, whose quote describes the procedure and
    #:     cites Cox (1996b) FOR it, and derosa, where FSL is named as the governing package.
    #:     Neither "deferred" outcome is among the pre-declared readings, so either would have
    #:     produced an outcome interpreted after the fact. CALL 7 supplies the missing limit --
    #:     "does the citation SUBSTITUTE for a description of that row, or SUPPORT one that is
    #:     present?" -- and names binder as the support case.
    #:   * STEP 2 said "the surviving passage" while STEP 1 can keep several.
    #:
    #: This is what a pin update looks like: deliberate, dated, superseded hash retained, reason
    #: recorded. It is NOT a licence to edit the stanza to make a test pass.
    "MOTION_METHOD_PROMPT": ("56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a"),
}

_VINTAGE_NOTE = (
    "\n\nThis hash pins a prompt that is SENT TO THE MODEL. A change here changes what every "
    "targeted field is extracted under, so the next numbers for EVERY field are a NEW VINTAGE — "
    "not comparable to any committed rate without saying so. Do not update this constant to make "
    "a test pass. Update it only alongside a dated vintage note recording what changed and which "
    "numbers it supersedes (the 2026-10-19 ruling: committed numbers stand as history under their "
    "named vintages). If you are adding a field, ruling A says give it its OWN call and prompt "
    "constant; EXTRACTION_PROMPT stays untouched and this test stays green."
)


def test_both_model_facing_prompts_are_hash_pinned() -> None:
    for name, prompt in (
        ("EXTRACTION_PROMPT", EXTRACTION_PROMPT),
        ("PER_ACQUISITION_EXTRACTION_PROMPT", PER_ACQUISITION_EXTRACTION_PROMPT),
        ("MOTION_METHOD_PROMPT", MOTION_METHOD_PROMPT),
    ):
        got = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        assert got == _PINNED[name], f"{name} changed: {got} != {_PINNED[name]}{_VINTAGE_NOTE}"


def test_the_per_acquisition_prompt_still_contains_the_shared_one() -> None:
    """Pinning both is not redundant: the per-acquisition constant is built as
    ``prefix + EXTRACTION_PROMPT`` (extractor.py), so it inherits every shared-prompt change. Pinning
    only the shared one would leave the prefix unpinned; pinning only the composite would not say
    which half moved. This asserts the composition that makes both hashes interpretable — and it is
    the same fact that makes a SEPARATE motion call invisible to the multi-acquisition path, a cost
    ruling A records."""
    assert PER_ACQUISITION_EXTRACTION_PROMPT.endswith(EXTRACTION_PROMPT)
    assert len(PER_ACQUISITION_EXTRACTION_PROMPT) > len(EXTRACTION_PROMPT)


# ---------------------------------------------------------------------------
# The copy of the DECISION RULE's taxonomy living in subject_validator.py
# ---------------------------------------------------------------------------
#: ``subject_validator.py`` says its taxonomy is "Lifted VERBATIM from EXTRACTION_PROMPT's DECISION
#: RULE". Measured 2026-10-21, that is true of 11 of its 13 terms and NOT of two — so a byte- or
#: span-equality test would fail on correct code. Both are the same shape: the prompt writes one
#: slash-compound and the copy splits it into the shapes it covers. They are enumerated here with the
#: reason, and the test below fails if a THIRD appears, or if one of these two stops being needed.
#: The property worth guarding is not that the copy is identical but that every divergence is declared.
#:
#: A third term, ``statistical map``, is LINE-WRAPPED in the prompt literal and so differs only in
#: whitespace. It is deliberately NOT listed here: the whitespace squash below handles it, and listing
#: it would be cover for a difference that does not exist. The stale-entry assertion caught exactly
#: that when this file was first written.
_DECLARED_DIVERGENCES = {
    "correlation matrix": "correlation/connectivity matrix",
    # subject_validator.py:52-53 records WHY the bare acronym was not used: "ICA" collides with
    # anatomICAl / cortICAl in real methods text.
    "ICA components": "ICA/PCA components",
}


def _squashed(text: str) -> str:
    """Collapse the prompt's own line wrapping, which is layout and not content."""
    return re.sub(r"\s+", " ", text)


def test_the_copied_decision_rule_taxonomy_still_matches_its_source() -> None:
    squashed = _squashed(EXTRACTION_PROMPT)
    undeclared: list[str] = []
    for term in _PROMPT_TAXONOMY:
        if term in squashed:
            continue
        source = _DECLARED_DIVERGENCES.get(term)
        if source is not None and _squashed(source) in squashed:
            continue
        undeclared.append(term)
    assert not undeclared, (
        f"taxonomy term(s) no longer traceable to EXTRACTION_PROMPT's DECISION RULE: {undeclared}. "
        "subject_validator.py claims this tuple is lifted verbatim from the prompt, and the hash "
        "pin above does NOT cover the copy — the two can drift apart in either direction without "
        "failing anything else. Either restore the term, or add it to _DECLARED_DIVERGENCES with "
        "the reason it differs."
    )
    # every declared divergence must still be REAL: if the prompt is reworded so that a term now
    # appears verbatim, the entry is stale and should be removed rather than left as cover.
    stale = [t for t in _DECLARED_DIVERGENCES if t in squashed]
    assert not stale, (
        f"divergence(s) no longer needed — the term is now verbatim in the prompt: {stale}"
    )


def test_the_decision_rule_section_is_where_the_taxonomy_lives() -> None:
    """Positive control for the search above: the terms are found because the DECISION RULE is in the
    prompt, not because the assertion is vacuous. If this section is ever moved out, the test above
    would keep passing on incidental matches elsewhere in the literal."""
    assert "DECISION RULE (apply BEFORE choosing status)" in EXTRACTION_PROMPT
    section = _squashed(EXTRACTION_PROMPT[EXTRACTION_PROMPT.index("DECISION RULE") :][:1200])
    # a representative term from each shape: plain, slash-compound, line-wrapped
    assert "ReHo" in section
    assert "ICA/PCA components" in section
    assert "statistical map" in section
