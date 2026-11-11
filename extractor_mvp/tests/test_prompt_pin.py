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
from extractor_mvp.verifier import VERIFIER_PROMPT

#: sha256 of the two constants actually sent to the model, pinned 2026-10-21 at HEAD ef10931.
#: UPDATING EITHER VALUE IS A VINTAGE EVENT. See the failure message below.
_PINNED = {
    #: UPDATED 2026-11-09 (the author's item 3: the shared rules of prompt_rules.py; a vintage event,
    #: deliberate). Superseded value was 31a050b291161c31d5b535b2411234df12b484039a436b7a85df6b4081b77535.
    #: UPDATED 2026-11-11 (DESIGN_applies_to.md Stage 1, a vintage event, deliberate): the variant paragraph (prompt_rules.VARIANT_RULES, with fork B1's same-phrase instruction) and the "varied" status on the Layer-2 fields. Not
    #: yet drawn; Stage 2 re-runs the case papers. Superseded value was bea152d7189c96cf4d07f20833918f6bafe96d18f1165b4aa30c2a5cd5a71426.
    "EXTRACTION_PROMPT": "e81e5d0a8ddcae9470ed63933a453e9fb84fe2987caf1a68853010d22133a221",
    #: UPDATED 2026-11-09 (the author's item 3: the shared rules of prompt_rules.py; a vintage event,
    #: deliberate). Superseded value was 04ba3cb76b55342cee2ed2fd8b62fb515226fdb21511c6803f380d51913c4648.
    #: UPDATED 2026-11-11 (DESIGN_applies_to.md Stage 1, a vintage event, deliberate): inherits EXTRACTION_PROMPT's variant paragraph. Not
    #: yet drawn; Stage 2 re-runs the case papers. Superseded value was b9f050d0c1b8b5ebfdb6cbfd34fa4684dfe4a0c653a31d9040a8d876a24290be.
    "PER_ACQUISITION_EXTRACTION_PROMPT": (
        "7292b1b94129db5afe519a8dfe3e2a2f07ac8b9de9b34d97a2ffd5d62feb7783"
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
    #: 2026-11-09: NOT changed by the shared rules of prompt_rules.py. This is the pre-registered
    #: probe stanza; the probe recorder refuses any other (tests/test_motion_probe_freeze.py), so the
    #: rules were left out of it rather than break the pre-registration. The author decides otherwise.
    "MOTION_METHOD_PROMPT": "b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837",
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
    #: UPDATED 2026-10-28, the author's item 5: a record-level multiple_pipelines question (with
    #: quote and count) on both calls. Superseded TEMPORAL_VOLUME_PROMPT value (item 2):
    #: c2617933046fb988e99e01e1bbb48f08fbb8449456a371009d281d601dfc9beb.
    #: UPDATED 2026-10-29, report v2 step 1 (DESIGN_report_v2.md §1b): six fields become lists; their prompt lines ask for comma-separated lists. Superseded TEMPORAL_VOLUME_PROMPT value:
    #: 18b47abfb9aca06c195686567f59394ff5984a4969ca4721021ac74fcdc4ef19.
    #: UPDATED 2026-10-29, report v2 step 3 (DESIGN_report_v2.md §1a): call T asks temporal filtering (performed, band, filter type, order, relative to regression, applied to). Superseded TEMPORAL_VOLUME_PROMPT value:
    #: 8c46e26a78af72505b2d8c4331d9c79ef0baed8d00f0cdf7152b1df5b57028be.
    #: UPDATED 2026-10-29, report v2 step 4 (DESIGN_report_v2.md §2): the SCOPE paragraph in both coverage prompts (BOLD preprocessing only; structural preprocessing and first-level model covariates out). Superseded TEMPORAL_VOLUME_PROMPT value:
    #: 8f21ca02c0d660a8364c53d63f40735260a13731fd15d2b6de90e44e75d56795.
    #: UPDATED 2026-10-29, report v2 step 5 (DESIGN_report_v2.md §1d): call T asks step_order (the paper's order, every sentence stating it). Superseded TEMPORAL_VOLUME_PROMPT value:
    #: 2129f31135fb0e7f9256a23e2fc962217dc432c668281494be056eb92ccce3fe.
    #: UPDATED 2026-10-29, report v2 step 6 (DESIGN_report_v2.md §3, F3a): the multiple_pipelines question leaves calls T and S for the checking pass. Superseded TEMPORAL_VOLUME_PROMPT value:
    #: b2feb797352b95d0dc17e39d5edd13b1c74aac0a6c3a6c1a759b18a6ea7f5830.
    #: UPDATED 2026-11-02, the author's ruling: the SCOPE paragraph restated -- structural steps that feed the fMRI analysis are IN (brain extraction, segmentation for masks or regressors, bias-field correction, the structural registration target), citing D.3's "For structural images"; structural-only analyses (morphometry, diffusion, tractography) and first-level covariates OUT. First drawn as coverage_v4. Superseded TEMPORAL_VOLUME_PROMPT value:
    #: 5832804631604a8d92c0154c8798cae4772a08b766824d00410f8b43ae8f44ee.
    #: UPDATED 2026-11-03, the author's ruling dated 2026-11-02: the SCOPE paragraph gains one generic example of a first-level model covariate sentence (written for the prompt, quoting no paper), after the GLM covariates refilled nuisance regression and detrend on gracia-tabuenca_2024 in coverage_v4. Not yet drawn. Superseded TEMPORAL_VOLUME_PROMPT value:
    #: a9230438e3f29e6d604cd13eb7840a921e0a5a44125af53ca3362fb6a08eb05e.
    #: UPDATED 2026-11-05, fix 5 of the author's list after stress_v1 (schema 0.6.3): call T asks
    #: filter_pass_type (high_pass, low_pass, band_pass), and the filter_type line says it is the
    #: filter's design, not the band's shape; the six stress papers the checking pass said
    #: filter_type missed all named a pass type. Superseded TEMPORAL_VOLUME_PROMPT value:
    #: c043aa86afb437224aa68011827b746ff1515025252574e8493f401f6b5dd23e.
    #: UPDATED 2026-11-09 (the author's item 3: the shared rules of prompt_rules.py; a vintage event,
    #: deliberate). Superseded value was 2ab16fbfeb7b0b744f09a1f58c3b5d8950f4677ded8f43a354ac849220410f90.
    #: UPDATED 2026-11-11 (DESIGN_applies_to.md Stage 1, a vintage event, deliberate): the variant paragraph, the "varied" status, and step_order_parts (an order stated per part). Not
    #: yet drawn; Stage 2 re-runs the case papers. Superseded value was b2159934aadf963558d7ed17af3e326dd31e9ec0accf36c7ec8a1ba02136a0b8.
    "TEMPORAL_VOLUME_PROMPT": "d0c8827d10daabf1939e1ed1c823bfaf1361bc687bc42b3a4a716ea3e92da614",
    #: UPDATED 2026-10-28, the author's item 4: coregistration method = the tool, cost_function =
    #: bbr | mutual_information | correlation_ratio | other. Superseded SPATIAL_PROMPT value (item 2):
    #: 95189d772ff6dbe3e547a1cff69941adf4a4f084aaab75f11b4d6d9648b42b80.
    #: UPDATED 2026-10-28, item 5 (see above). Superseded SPATIAL_PROMPT value (item 4):
    #: 4ac7b0cbd47d895b6c4f280f077485fe916785a58d7c8876723a23bf9f59f78d.
    #: UPDATED 2026-10-29, report v2 step 1 (DESIGN_report_v2.md §1b): six fields become lists; their prompt lines ask for comma-separated lists. Superseded SPATIAL_PROMPT value:
    #: dd46672b9cc43b6eb2d64c115138b2a559c82a581b4e9d3909c4308d1c2feff6.
    #: UPDATED 2026-10-29, report v2 step 2 (DESIGN_report_v2.md §1c): call S asks software_mentions (name, version, used_for, quote). Superseded SPATIAL_PROMPT value:
    #: b29d4c06d72b4092e25d6edc78dab6595316fee36eebde6aaad675166b871a0b.
    #: UPDATED 2026-10-29, report v2 step 4 (DESIGN_report_v2.md §2): the SCOPE paragraph in both coverage prompts (BOLD preprocessing only; structural preprocessing and first-level model covariates out). Superseded SPATIAL_PROMPT value:
    #: 2291c503605d2d887463f119cc2b5218533fa132b11f575cb6c0f9efd0899ea2.
    #: UPDATED 2026-10-29, report v2 step 6 (DESIGN_report_v2.md §3, F3a): the multiple_pipelines question leaves calls T and S for the checking pass. Superseded SPATIAL_PROMPT value:
    #: 6d9f03681daf28300de60e23ec0512c9e1deb43e19969ebc927a5e3e60417b66.
    #: UPDATED 2026-11-02, the author's queued fix: the SCOPE rule applied to software_mentions (only software used to preprocess the functional data; structural-only analysis, statistics, prediction and stimulus software out; software whose output the functional preprocessing uses stays in). Not yet run: the next coverage draw is a new vintage. Superseded SPATIAL_PROMPT value:
    #: 697c868be398f23b4cd9e86a7a557e42771d89f3b5ba1e3563aa49d13536ab2a.
    #: UPDATED 2026-11-02 (later), the author's ruling: the SCOPE paragraph restated as on TEMPORAL_VOLUME_PROMPT (D.3's "For structural images"), and the software list follows it (software for a structural step that feeds the fMRI analysis is listed; structural-only analysis, statistics, prediction, stimulus software is not). First drawn as coverage_v4; 3c8d604b was never drawn. Superseded SPATIAL_PROMPT value:
    #: 3c8d604b5776aef6c332d3ab2aed508f7410cf35936c6264de30248c15398959.
    #: UPDATED 2026-11-03, the author's ruling dated 2026-11-02: the SCOPE paragraph gains one generic example of a first-level model covariate sentence (written for the prompt, quoting no paper), after the GLM covariates refilled nuisance regression and detrend on gracia-tabuenca_2024 in coverage_v4. Not yet drawn. Superseded SPATIAL_PROMPT value:
    #: 8b54be37ca891c80c141a881c11123278cb6c0af501bab0fe9c705f6fd42ebbf.
    #: UPDATED 2026-11-03 (evening), the author's ruling (schema 0.6.1): distortion_method asks the
    #: method FAMILY (reverse_phase_encoding, fieldmap, other; "Never a program name here") and the new
    #: distortion_tool asks the program (the 0.6.0 method members). First drawn under tool calling.
    #: Superseded SPATIAL_PROMPT value:
    #: 87cf358db49c62dfb72a57e14027e68dab7275cc917a70eddb5e7a9ec8fa55ed.
    #: UPDATED 2026-11-03 (later evening), the author's ruling (schema 0.6.2): the family list gains
    #: gradient_nonlinearity_correction, and "other" is written "other (the paper's own words)" and
    #: checked against them. First drawn on case one that evening. Superseded SPATIAL_PROMPT value:
    #: cbb6193c43f61cc31f1c1054769d23a359a15908e2067cd79a6cadece1f51fd6.
    #: UPDATED 2026-11-09 (the author's item 3: the shared rules of prompt_rules.py; a vintage event,
    #: deliberate). Superseded value was 81875e3baa97e3fe734a7719e035e35d4be3527f04ec957e741be8fbfa938339.
    #: UPDATED 2026-11-11 (DESIGN_applies_to.md Stage 1, a vintage event, deliberate): the variant paragraph and the "varied" status. Not
    #: yet drawn; Stage 2 re-runs the case papers. Superseded value was ecfa8177ac20771d5be34a908d00adf71e89994ac633346578e53a85247e36f0.
    "SPATIAL_PROMPT": "68bf6651e83e3694178bdd7ac6fc31f3c7ff81700e2f2392b07eae044ef0aa92",
    #: The checking pass, pinned 2026-10-29 at its first build (DESIGN_report_v2.md §3, ratified that
    #: day). Its first run is the vintage coverage_v3; a change is a dated vintage event.
    #: UPDATED 2026-11-02, the author's item 2: the checking pass returns `unplaced` (preprocessing statements no field captured, each with its sentence and its D.3 row or "no row"; never changes a field); its scope paragraph and software question restated to the SCOPE rule of the same day (structural steps that feed the fMRI analysis in). First drawn as coverage_v4. Superseded VERIFIER_PROMPT value:
    #: 42cb343c7b2f4fea94fa47cb0f25146640f5f1101896ba8b67a79c31e2956a70.
    #: UPDATED 2026-11-09 (the author's item 3: the shared rules of prompt_rules.py; a vintage event,
    #: deliberate). Superseded value was f078f100496a21e873e20de5c41372aa633877f03154c0c324ba000f6741a557.
    #: UPDATED 2026-11-11 (DESIGN_applies_to.md Stage 1, a vintage event, deliberate): fork F1: a `[<part>]` draft line is judged for its part, and "missed" covers a value the paper ties to a part; the multiple_pipelines question removed. Not
    #: yet drawn; Stage 2 re-runs the case papers. Superseded value was 6db3abb9f963c2196b850bd00c368e50529a400d36f9c38fd38d011a5f05feec.
    "VERIFIER_PROMPT": "a699d8b29209a3b3025a1e8b8675f697cd117f6ae416276bd3bcf4f2f81843ba",
}

#: The frozen per-step phrase table behind the ``performed`` support check (item 2, 2026-10-28):
#: sha256 of ``json.dumps(PERFORMED_PHRASES, sort_keys=True)``. Written from D.3's wording and the
#: coverage_v1 sentences of the contaminated sixteen, then frozen; a change is a dated event here.
#: UPDATED 2026-10-29, report v2 step 3: the temporal_filtering entry added with the step.
#: Superseded value: 85566a83441d91338076acf3f7c321afc6d735524bae55c734971cbab1ccc32f.
#: UPDATED 2026-11-02, the author's queued fix: nuisance_regression gains the "orthogonalized" and
#: "regressed out" families, DECLARED FITTED to shen_2013 (now contaminated for this table). The
#: table is not sent to the model; it is the processed-layer check, so no prompt hash moves.
#: Superseded value: 02acd07d8fab2ea17c4f730c2da45a0d8ee5176bc507ea8d34ac442f6ba14ef4.
_PINNED_PERFORMED_PHRASES = "f77f032b8026077b667472d0d4d29b4975408d1a92cea968e2205dd21c917a8f"

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
        ("VERIFIER_PROMPT", VERIFIER_PROMPT),
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
    """R8 (2026-10-28), as a literal. The coverage build left these three untouched; they moved once,
    deliberately, on 2026-11-09 with the shared rules of prompt_rules.py (the author's item 3), and
    again on 2026-11-11 with DESIGN_applies_to.md Stage 1's variant paragraph. The values before
    those were 31a050b2…b77535 / 04ba3cb7…c4648, then bea152d7…5a71426 / b9f050d0…24290be; the
    motion stanza did not move."""
    assert _PINNED["EXTRACTION_PROMPT"] == (
        "e81e5d0a8ddcae9470ed63933a453e9fb84fe2987caf1a68853010d22133a221"
    )
    assert _PINNED["PER_ACQUISITION_EXTRACTION_PROMPT"] == (
        "7292b1b94129db5afe519a8dfe3e2a2f07ac8b9de9b34d97a2ffd5d62feb7783"
    )
    assert _PINNED["MOTION_METHOD_PROMPT"] == (
        "b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837"
    )
    assert len(_PINNED) == 6  # 2026-10-29: + VERIFIER_PROMPT


def test_the_performed_phrase_table_is_frozen() -> None:
    assert PERFORMED_PHRASES_SHA256 == _PINNED_PERFORMED_PHRASES, (
        "PERFORMED_PHRASES changed: a performed cell's support now depends on a different table. "
        "Update the pin only with a dated note recording what changed and which vintage it supersedes."
    )


#: The citation hop's addendum to calls T and S (DESIGN_citation_hop.md, forks ratified 2026-11-03):
#: the fields asked and the per-variant question, inserted before the text block of the pinned
#: TEMPORAL_VOLUME_PROMPT and SPATIAL_PROMPT, which stay unchanged. Pinned at its first build,
#: 2026-11-03; first drawn on gracia-tabuenca_2024 -> Hagler et al. (2019). A change is a dated event.
#: Was a167221c5021b455834d984343bf1de561f57fd41cf5c78b6e55e7750e64ab7e (the addendum alone, the first
#: case-one draw). Re-pinned 2026-11-03 (afternoon, the author's rulings of that day): call S also
#: asks the tool for a step the citing paper describes without one (fork A widened) and the data
#: releases the cited paper describes; the pin now covers the addendum and both asks
#: (HOP_ADDENDUM + _TOOLS_ASK + _RELEASES_ASK). Supersedes the first draw for case one.
#: Was 64d8979fd5267a7daafbd3893f0c512e63e622aa011e1f1de05d8885fd9257a6 (the second build). Re-pinned 2026-11-03 (later afternoon, the author's
#: scoping ruling): the releases ask moved out of call S to its own call RD on the methods slice,
#: since calls T and S now read only the fMRI preprocessing section; the pin covers
#: HOP_ADDENDUM + _TOOLS_ASK. Supersedes the second build's draws.
#: Was 097a8eb1435eb7b949169e1f4afad8eae3eb394014b5bddad432dcdfc84b6ec3 (the third build). Re-pinned 2026-11-03 (the author's scoping
#: correction): the software list moved to its own call SW on the whole cited paper, asking each
#: tool's fMRI use quote (_SOFTWARE_ASK); the pin covers HOP_ADDENDUM + _TOOLS_ASK + _SOFTWARE_ASK.
#: Was f2785d924064367b2a21a83ffb3362dc758f7308624f2c2d2036b360d40865a7 (never drawn on case one). Re-pinned 2026-11-03: the use quote is asked
#: from the fMRI processing sections, where fmri_use now checks it.
#: Was 8f928a217ee9e60a413c2edcd46d604883aab7cc5dbea92354220b1f4c206816. Re-pinned 2026-11-03 (evening, the author's ruling): the software list
#: leaves the model for a deterministic KB scan with one scoped question per mention
#: (software_scan.SOFTWARE_USE_PROMPT, pinned below); _SOFTWARE_ASK is removed and the pin covers
#: HOP_ADDENDUM + _TOOLS_ASK again (097a8eb1..., the third round's value: the addendum itself did
#: not change).
_PINNED_HOP_ADDENDUM = "097a8eb1435eb7b949169e1f4afad8eae3eb394014b5bddad432dcdfc84b6ec3"

#: The per-mention software question (software_scan.py, 2026-11-03, the author's ruling). Pinned at
#: its first build.
_PINNED_SOFTWARE_USE_PROMPT = "e89f7a63464f829e62ab65f698f67102736c1d444a2e97de5f3c172879dad50e"


def test_the_software_use_prompt_is_hash_pinned() -> None:
    from extractor_mvp.software_scan import SOFTWARE_USE_PROMPT

    got = hashlib.sha256(SOFTWARE_USE_PROMPT.encode("utf-8")).hexdigest()
    assert got == _PINNED_SOFTWARE_USE_PROMPT, f"SOFTWARE_USE_PROMPT changed: {got}{_VINTAGE_NOTE}"


#: Call RD, the releases the cited paper describes, on its methods slice (2026-11-03, later
#: afternoon). Pinned at its first build.
_PINNED_CITED_RELEASE_PROMPT = "f9324f34c0bc24d385ab039d203832b386e515fea4aaee84c2221765ad0c1413"


def test_the_cited_release_prompt_is_hash_pinned() -> None:
    from extractor_mvp.citation_hop import CITED_RELEASE_PROMPT

    got = hashlib.sha256(CITED_RELEASE_PROMPT.encode("utf-8")).hexdigest()
    assert got == _PINNED_CITED_RELEASE_PROMPT, (
        f"CITED_RELEASE_PROMPT changed: {got}{_VINTAGE_NOTE}"
    )


#: The citing paper's data-release call R (first hop; the author's "described vs applied" ruling,
#: 2026-11-03). Pinned at its first build, 2026-11-03.
_PINNED_RELEASE_PROMPT = "28518830db6b8b7e7ff75194f7bd6caac7ae1995aa3911b4ea537d35fec3391c"


def test_the_release_prompt_is_hash_pinned() -> None:
    from extractor_mvp.citation_hop import RELEASE_PROMPT

    got = hashlib.sha256(RELEASE_PROMPT.encode("utf-8")).hexdigest()
    assert got == _PINNED_RELEASE_PROMPT, f"RELEASE_PROMPT changed: {got}{_VINTAGE_NOTE}"


def test_the_hop_addendum_is_hash_pinned() -> None:
    from extractor_mvp.citation_hop import _TOOLS_ASK, HOP_ADDENDUM, hop_prompt

    got = hashlib.sha256((HOP_ADDENDUM + _TOOLS_ASK).encode("utf-8")).hexdigest()
    assert got == _PINNED_HOP_ADDENDUM, f"HOP_ADDENDUM changed: {got}{_VINTAGE_NOTE}"
    # the base prompt is untouched around the insertion
    p = hop_prompt(SPATIAL_PROMPT, ["smoothing_fwhm_mm"], False)
    head, tail = SPATIAL_PROMPT.rsplit('Text:\n"""', 1)
    assert p.startswith(head) and p.endswith('Text:\n"""' + tail)


#: The instructor mode is part of a vintage (2026-11-03, the author's ruling): every client switched
#: from JSON mode to tool calling, a new vintage whatever the prompt hashes. A change is a dated event.
_PINNED_INSTRUCTOR_MODE = "tools"


def test_the_instructor_mode_is_pinned_and_every_client_uses_it() -> None:
    import instructor

    from extractor_mvp.citation_hop import CallMeter
    from extractor_mvp.extractor import INSTRUCTOR_MODE, build_client

    assert INSTRUCTOR_MODE == _PINNED_INSTRUCTOR_MODE
    assert build_client().mode == instructor.Mode.TOOLS
    assert CallMeter().client().mode == instructor.Mode.TOOLS


#: The fMRI gate (fix 1b, the author's list of 2026-11-05): one call before extraction. Pinned at its
#: first build, 2026-11-05.
_PINNED_FMRI_GATE_PROMPT = "14df0f33bd1c1d5313b65371ce826e287cd23f70066afc41a9f5e201625aa813"


def test_the_fmri_gate_prompt_is_hash_pinned() -> None:
    from extractor_mvp.fmri_gate import FMRI_GATE_PROMPT

    got = hashlib.sha256(FMRI_GATE_PROMPT.encode("utf-8")).hexdigest()
    assert got == _PINNED_FMRI_GATE_PROMPT, f"FMRI_GATE_PROMPT changed: {got}{_VINTAGE_NOTE}"
