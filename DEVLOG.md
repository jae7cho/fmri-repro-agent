# Development log

Contemporaneous dated record of project sessions. Each entry: date, hours, what I worked on. Maintained as evidentiary record.

---

## 2026-05-19

Project repository initialized. Scaffolding created via Claude Code session.

---

## 2026-07-14

Hours: 21:16:03 - 22:55 ET

v0.4.0. Bumped `Preprocessing.schema_version` 0.3.0 -> 0.4.0 with the full version
ceremony: new live root `spec/v0_4_0.py`, `spec/v0_3_0.py` demoted to a bare
`SCHEMA_VERSION` constant, and a 0.3.0 -> 0.4.0 migration hop that is a pure re-stamp
(the sole delta is an optional-default field, so no document transform runs; the
migrator id is now generic). Added `Extracted.span_recovered` (optional, default
False) in the version-stable provenance layer — it marks an extraction whose
char-offset span was located only by the corrupted-source tolerant tier (span_resolver
tier 5), not a clean match. Consumed those recoveries: `_process_field` and
`_build_base_pipeline` now keep a tier-5 recovered span instead of dropping it, marking
`span_recovered=True`. Added the value-support guard (Option A) on `base_pipeline`:
before promoting a recovered pipeline name to EXTRACTED, it checks the model's own value
is tolerantly present in its own quote (firewall-clean, no KB at extraction); a
recovered-but-unsupported citation-shaped quote (e.g. "...described by Glasser et al.")
is reclassified to DeferredToCitation rather than fabricating a name. Committed as 2560bb1.

Also this sitting: made the committed example generators reproducible. Added the required
`NuisanceRegression` `method` / `filtering_integrated` fields the generator scripts had been
raising on (rotted unnoticed since 0.3.0 made those fields required, because nothing invoked the
scripts), regenerated `examples/spec.json` and `examples/hcp_glasser_fieldmaps.json` under 0.4.0
(data-identical to the committed files; the stale serializations also gained the `written_under` /
`migration` fields they had been missing, correcting a false "natively written under 0.4.0" claim),
and added a byte-identity reproducibility test guarding both scripts. Committed as c75eccf. The
temporal-firewall A/B (next entry) was started at the end of this sitting; its ~100 model calls ran
autonomously 22:55-23:20 and are recorded under 2026-07-15.

---

## 2026-07-15

Hours: 19:21:26 - 21:55 ET

Temporal firewall for `temporal_standardization_method`. Adopted the validated subject-first
DECISION RULE + SFC near-miss as a prompt-only change (moved to the top of the field's stanza,
verbatim from the finding doc's candidate). The single-session A/B compute itself ran the prior
night (2026-07-14 22:55-23:20); today was re-baseline review, wording correction, and commit.
Result: chen 17/20 -> 0/20 EXTRACTED (target SFC false positive converted), liu 10/10 preserved,
`intensity_convention` stable — both pre-declared STOP gates clear. Scope held to the chen/SFC
shape the near-miss quotes; viduarre (ICA) and derosa (activation-patterns) are derived-subject
shapes the patch does not reach — recorded as a scope-miss and a controlled non-stationarity data
point (viduarre fixed-arm 4/10 pre-v0.4.0 -> 0/10 this session, byte-identical slice and prompt,
only the session varying). Marked the finding doc's pre-v0.4.0 numbers historical and added the
re-baseline. Committed as b396772; a follow-up (19872d6) pinned a prompt-identity control to a
fixed commit (c75eccf) rather than a moving HEAD.

Then built the deterministic subject validator (`subject_validator.py`), SHIPPED INERT — a post-hoc
check that flags the derived-product SUBJECT of a normalization verb, targeting the two
derived-subject shapes the prompt patch cannot reach. Two separately-measured lists: an enforcement
list lifted verbatim from the prompt's DECISION RULE, and a declared extension list (fit to derosa's
"activation patterns"). Measured on arm-1's recorded draws, no new model calls: liu 0/30 flagged
(true positive preserved), chen 31/31 and viduarre 4/4 via the enforcement list, derosa 19/19 via the
extension list. Not wired into the four-state (production byte-identical to HEAD); consumption is a
separate decision. Committed as 977c7fb.

---

## 2026-07-16

Hours: 17:04 - 21:38 ET

Arm 2 (second-session A/B) of the temporal firewall: chen fixed arm replicated 0/20 -> 0/40 across
two sessions (95% CI upper bound 8.8%). RETRACTED the doc's "baseline drift" claim after a homogeneity
test — the three hash-asserted baseline points (14/17/14 of 20) pool to ~75% and are homogeneous
(chi2=1.60, p=0.45); variance is not separable from sampling noise at K=20. Demoted viduarre's
"0/10 never fired" headline to a low-rate override. Committed as e73be02.

Prompted by the subject-validator corpus sweep, found and fixed a SHIPPED v0.4.0 fabrication hole: the
value-support guard `quote_supports_value` used whitespace-deleted substring matching, so a short
pipeline value matched inside a longer word — `q("ANTs", "...described by Avants et al.")` = True, the
viduarre fabrication path re-opened by the author's own surname. Fixed to token-boundary matching;
verified no regression across all 5 recorded recovered-keep base_pipelines. Committed as 3cb396e.
Subject-validator consumption gate stays INERT: the pre-declared escalation criterion (a 2nd unnamed
derived shape, liu CAPs) was met, so LLM Tier 2 is indicated; the substring collision was recorded as
an implementation finding, not a falsification (5ae4040; anecdote in 9e94112).

Started the base_pipeline ground-truth harness (STEP 0, report-only, NO labels — an LLM must not label
truth for an LLM extractor). Surfaced base-pipeline reporting shapes across all 20 corpus papers, then
diagnosed a VERIFIED false absence: wheaton_2004 plainly states "Data were analyzed using SPM99" in the
methods slice, which the LLM-filtered shapes report had called absent — though the extractor itself DID
extract SPM99 (adjudication-order-generalization.md's model claim survives). Re-derived the evidence
base deterministically by grep: >=20 tool-token sentences were missing from the prior screen, and 2 of
3 "no-preprocessing" excluded papers (braun_2015, liu_2005) were false absences. No commits from the
ground-truth work (report-only); artifact in gitignored results/.

---

## 2026-07-17

Hours: 17:27 - 21:44 ET

Report-only diagnostic sitting — deterministic sweeps, zero model calls, NO code/doc commits;
artifacts in gitignored results/. (No commits to bracket against the hours.)

Investigated the citable "0/19 corpus papers report a pipeline version" claim. It is NOT in the repo
(only per-paper render strings). `cobidas.assess_coverage` computes coverage from the EXTRACTION status
of `base_pipeline.version` — what AESPA extracted, not what papers say. AESPA extracted 0 versions
across all 20 papers, yet the text plainly reports them: oconnor "C-PAC version 0.4.0", derosa "FSL
suite (version 5.0.10)", liu_2013 "FCP analysis scripts (version 1.1-beta)" (all three with
base_pipeline itself MISSING in the batch), plus the SPM-fusion papers (SPM99/8/12). So the claim
inverts from a fact about the literature into a fact about the extractor — false as stated. Report
only, no patch (the remedy is a decision).

Continued the deterministic re-derivation of ground-truth protocol rules from corpus text (the STEP-0
LLM shapes report has a verified, unbounded false-absence surface):
- SI check: no corpus PDF contains supplementary BODY text — every SI heading is a pointer. braun_2015
  and viduarre_2017 are 6-page PNAS main articles with SI online (viduarre explicitly cites its own
  "SI Methods") — a FOURTH partition class, corpus-construction failure (incomplete artifact), distinct
  from extraction and slicing.
- D1 deferral census: 7 papers pair a preprocessing verb with a deferral marker/citation in-slice (not
  the assumed four).
- D9 (ciric): printed the full XCP-Engine methods paragraphs verbatim (a paper about 14 evaluated
  pipelines — scope ruling left to the labeler).
- D12 (HCP token): re-derived every occurrence across the corpus; surfaced a 4th context (weber's
  "HCP Workbench" software command) beyond the prior screen's three roles.
