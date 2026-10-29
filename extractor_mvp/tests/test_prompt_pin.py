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

from extractor_mvp.coverage_extractor import SPATIAL_PROMPT, TEMPORAL_VOLUME_PROMPT
from extractor_mvp.coverage_fields import PERFORMED_PHRASES_SHA256
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
    #:
    #: UPDATED 2026-10-22, AFTER the first run, under prereg C11 (iteration on the probe papers
    #: only; no held-out text was read in the session that made it). Superseded value was
    #: 56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a -- the hash every draw of
    #: the 2026-10-21 run carries, and it stays in that run's manifest, projection and findings.
    #: One change, and one proposed change deliberately NOT made:
    #:
    #:   * MADE -- STEP 3's "BOUND BUT ROUTED ELSEWHERE" now names COBIDAS D.3's "Artifact and
    #:     structured noise removal" row and the tools D.3 p.57 lists under it (CompCor, ICA-FIX,
    #:     ICA-AROMA): they belong to that row, supply nothing here, and the value is the paper's
    #:     own phrase for the operation. STEP 4's first rule gained "and not routed elsewhere".
    #:     Prompted by derosa_2025 returning `ICA-AROMA` on 10 of 10 draws (prereg reading 2).
    #:     Because the stanza now names derosa's own tool, derosa's result under this hash is
    #:     FITTED, not independent -- the circularity correction 4 removed is re-admitted by choice.
    #:   * HELD -- a deferral line ("a paper that only names the operation under a cited pipeline
    #:     defers; one that describes how the method works in its own words does not"; poldrack
    #:     deferred, liu_2013 described_only). Checked against CALL 6, CALL 7 and CALL 2a before
    #:     writing, as instructed: it conflicts with CALL 7's enumeration criterion and does not
    #:     separate its two anchors on the axis it names. Reported in prereg Amendment 4, not
    #:     resolved by editing the stanza.
    #:
    #: Every draw after this date names 378a294f...; any draw naming 56bc6305... ran the superseded
    #: stanza. The two are different vintages and are never pooled.
    #:
    #: REVERTED 2026-10-26 to 56bc6305..., by the author's ruling. The 2026-10-25 same-day control
    #: (docs/findings/motion-probe-ab-stanza-vs-day.md; prereg Amendment 5) ran both stanzas on
    #: agtzidis_2020 and binder_1999 back to back: each reproduced its own earlier run, so the
    #: 2026-10-22 edit, not the day, moved agtzidis to `SPM12` (10 of 10) and binder to `AFNI`
    #: (8 of 10) -- tool names from sentences other than the quoted one -- and it left derosa
    #: unchanged (`ICA-AROMA` on all 20 draws across both stanzas). 378a294f... stays on every
    #: artifact of the 2026-10-22 run and of the A/B's 378a arm. The restored stanza is a version
    #: already measured (2026-10-21; the A/B's 56bc arm), so this is not a new vintage. ciric_2017
    #: runs under it next (Amendment 6).
    #:
    #: VERSION 3, 2026-10-26 (later), by the author's ruling: rule A and option (c) together, as ONE
    #: new version (prereg Amendment 7; protocol v1.7 CALL 11). Superseded value
    #: 56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a, which stays on the
    #: 2026-10-21 run, the A/B's 56bc arm and the ciric control of 2026-10-26; 378a294f... stays on
    #: the 2026-10-22 run and the A/B's 378a arm. Written from the protocol, not from any paper's
    #: text: STEP 4 carries CALL 11's deferral line as ordered steps, and STEP 5 sets the new
    #: response-model field `motion_correction_binding` on every extracted draw. A NEW VINTAGE: its
    #: draws are never pooled with any earlier run's. Pre-declared readings are in Amendment 7,
    #: written before the first draw.
    #:
    #: VERSION 4, 2026-10-26 (night), by the author's ruling (prereg Amendment 8). Superseded value
    #: ea7b0084255454fd38a6de566a5cccf2936b67b09910f6ffa15a79d01c5734a7, which stays on the
    #: version-3 run of 2026-10-26 (seven papers, K=10). Three GENERAL edits from CALL 6 and CALL 11,
    #: none naming a paper: citation forms (author-year, a bare number the text layer attaches to a
    #: word, a named pipeline as a target with or without a reference); wholesale deferral when STEP
    #: 1 keeps no passage (CALL 6) -> "deferred", not "missing"; STEP 4's trigger widened to "or a
    #: named pipeline". braun_2015, viduarre_2017 and vanderwal_2016 join the probe set and are fitted
    #: from this version. A NEW VINTAGE; regression on all ten papers; readings pre-declared in
    #: Amendment 8 before this edit was made.
    #:
    #: VERSION 5, 2026-10-26 (late night), by the author's ruling (prereg Amendment 9). Superseded value
    #: b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837, which stays on the
    #: version-4 run of 2026-10-26 (ten papers, K=10) and on the same-day version-4 ARM that this
    #: version is judged against. One general edit in STEP 4: a kept passage is read with the sentence
    #: that introduces its procedure set, whose citation or pipeline -- named or unnamed -- governs the
    #: operation sentences that follow; a bound tool or any stated detail still wins. Adoption rule and
    #: readings are in Amendment 9, written before this edit. The adopted version FREEZES under C11.
    #:
    #: FROZEN, 2026-10-26 (late night): VERSION 4 IS THE FROZEN STANZA. Amendment 9's adoption rule,
    #: applied as written to the same-day A/B (ten papers, K=10 per arm), did not adopt version 5:
    #: poldrack_2015 deferred on 3 of 10, below the pre-declared 6 of 10. Version 5's value
    #: fb5735fba39457a0f67aebe95fa4668f1df7ae55568f3ad86d1274563863e6d2 stays on the version-5 ARM's
    #: records only (results/motion_probe_ab_2026-10-26_v4v5/v5, projection ..._fb57_...). The
    #: constant was restored to version 4 VERBATIM and this pin returns to b0093774..., which is now
    #: the hash the full-corpus run's manifest must carry (prereg C11). scripts/motion_probe.py
    #: carries the same value as _FROZEN_STANZA_SHA256 and refuses to draw under any other; a change
    #: here without a new amendment naming the new hash there is refused at the recorder, not only
    #: here. See docs/findings/motion-probe-v5-ab-results.md.
    #:
    #: VERSION 6, 2026-10-26 (late night), by the author's ruling: protocol v1.8 (CALL 1 gains an
    #: attribution level, named_tool = step or package) and prereg Amendment 10, which LIFTS the
    #: freeze for this DEFINITIONAL CHANGE -- not tuning -- and re-applies it to the adopted version.
    #: Superseded value b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837 (version 4),
    #: which stays on every version-4 run and on the same-day A/B's version-4 arm. Two edits from the
    #: protocol's text: STEP 3's package rule after NOT BOUND (the closed list verbatim; an unlisted
    #: package is not attributed), STEP 5's output rules for named_tool_step / named_tool_package.
    #: The response model's binding literal changed with it. Readings for the 13-paper probe set,
    #: K=10, and the adoption rule are in Amendment 10, written before the edit. scripts/motion_probe.py
    #: carries this value as _FROZEN_STANZA_SHA256 in the same commit.
    #:
    #: VERSION 7, 2026-10-27, by the author's ruling (prereg Amendment 11). Superseded value
    #: 8df070da9cc3f9628d6670c7285740155b05a06dd25972849f0711b056c8ef4f (version 6), which stays on
    #: the version-6 run of 2026-10-27 (13 papers, K=10; not adopted: the model assigned the level
    #: backwards on gordon and mueller). Version 7 is version 6 with the attribution level removed
    #: from the output -- the binding literal is named_tool / described_only again, STEP 3 keeps the
    #: package rule minus any mention of a level, STEP 5's two named_tool bullets both set
    #: "named_tool" -- and the level derived in code on the processed layer. The chain retained:
    #: b0093774... (version 4, the first freeze) -> 8df070da... (version 6) -> this value. Amendment
    #: 11 pre-declares the last iteration before the corpus run: adopted, version 7 freezes; not
    #: adopted, b0093774... is restored by amendment and freezes.
    #:
    #: RESTORED AND FROZEN, 2026-10-27, by Amendment 12: Amendment 11's rule applied as written did not
    #: adopt version 7 (cole 0 of 10, gordon 7 of 10 on clause 1; liu_2013, poldrack and cole lost more
    #: than 2 on clause 2), so the constant is VERSION 4 VERBATIM again and this pin returns to
    #: b0093774... The chain: b0093774... -> 8df070da... (v6) -> d353fb47... (v7) -> b0093774...
    #: The superseded values stay on their runs' records. NO FURTHER ITERATION before the corpus run.
    "MOTION_METHOD_PROMPT": ("b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837"),
    #: The two coverage calls, pinned 2026-10-28 at their first build (DESIGN_coverage_expansion.md,
    #: the author's ruling R8): call T (temporal/volume) and call S (spatial). New constants in a new
    #: module, so the three hashes above do not move -- that is what R8 asks this test to show. The
    #: first run under these hashes is the vintage ``coverage_v1``; a change here is a new vintage,
    #: with a dated note, never an edit to make a test pass.
    #: UPDATED 2026-10-28 (later the same day), the author's item 2 (DESIGN_coverage_expansion.md
    #: B14): ``performed`` is never "deferred" -- the deferral case moved to the parameters and the
    #: quote must be the sentence that names the step. Superseded values, the coverage_v1 vintage:
    #: TEMPORAL_VOLUME_PROMPT 9e52382403967e42ed37cb7f9f2d7a3ac324509d8d2bf6affdc68f11a3837a64,
    #: SPATIAL_PROMPT 17742cbb8f49cfcbf95ccdcce73a715b8fd669ee7a9285f7d6363b438cb23ffa.
    "TEMPORAL_VOLUME_PROMPT": "c2617933046fb988e99e01e1bbb48f08fbb8449456a371009d281d601dfc9beb",
    #: UPDATED 2026-10-28, the author's item 4: coregistration method = the tool, cost_function =
    #: bbr | mutual_information | correlation_ratio | other. Superseded SPATIAL_PROMPT value (item 2):
    #: 95189d772ff6dbe3e547a1cff69941adf4a4f084aaab75f11b4d6d9648b42b80.
    "SPATIAL_PROMPT": "4ac7b0cbd47d895b6c4f280f077485fe916785a58d7c8876723a23bf9f59f78d",
}

#: The frozen per-step phrase table behind the ``performed`` support check (item 2, 2026-10-28):
#: sha256 of ``json.dumps(PERFORMED_PHRASES, sort_keys=True)``. Written from D.3's wording and the
#: coverage_v1 sentences of the contaminated sixteen, then frozen; a change is a dated event here.
_PINNED_PERFORMED_PHRASES = "85566a83441d91338076acf3f7c321afc6d735524bae55c734971cbab1ccc32f"

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
        ("TEMPORAL_VOLUME_PROMPT", TEMPORAL_VOLUME_PROMPT),
        ("SPATIAL_PROMPT", SPATIAL_PROMPT),
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


def test_the_three_pre_existing_hashes_did_not_move_with_the_coverage_calls() -> None:
    """R8 (2026-10-28), as a literal: the values the three constants were pinned at BEFORE the
    coverage build, so a coverage change that touched a shared constant fails here by name, not
    only through the table above."""
    assert _PINNED["EXTRACTION_PROMPT"] == (
        "31a050b291161c31d5b535b2411234df12b484039a436b7a85df6b4081b77535"
    )
    assert _PINNED["PER_ACQUISITION_EXTRACTION_PROMPT"] == (
        "04ba3cb76b55342cee2ed2fd8b62fb515226fdb21511c6803f380d51913c4648"
    )
    assert _PINNED["MOTION_METHOD_PROMPT"] == (
        "b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837"
    )
    assert len(_PINNED) == 5


def test_the_performed_phrase_table_is_frozen() -> None:
    assert PERFORMED_PHRASES_SHA256 == _PINNED_PERFORMED_PHRASES, (
        "PERFORMED_PHRASES changed: a performed cell's support now depends on a different table. "
        "Update the pin only with a dated note recording what changed and which vintage it supersedes."
    )
