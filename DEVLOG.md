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

---

## 2026-07-18

Hours: 08:24 - 19:48 ET

Finalized and pre-registered the `base_pipeline` ground-truth protocol
(`docs/ground-truth-protocol.md`). STEP-1 verified the two open rulings against the papers' verbatim
text (pypdf via the repo loader, zero model calls): D9 — ciric_2017's "BOLD time series processing"
section opens "processed using the XCP Engine (Ciric et al., In Preparation)" with FUGUE/MCFLIRT/
boundary-based-registration/Butterworth as common elements *within* the engine and the 14 models as
confound-regression strategies (nuisance field, not base pipelines) -> REPORTED, XCP Engine; D12 —
viduarre_2017 defers "the technique of Smith et al." + "the procedure described by Glasser et al.",
HCP is dataset-use only, FIX/FSL is a denoising step (Griffanti) -> DEFERRED_TO_CITATION, {Smith,
Glasser}. Both confirmed, so applied four edits: the D9 and D12 rulings (replacing the <<OPEN>>
blocks), a multi-target-deferral subsection in value-matching (all targets verbatim in value, resolved
name in notes never value, ANY-target set-membership scoring), and a consortium-data spec-
expressiveness backlog line.

Then recorded the rater scope BEFORE any label exists: v1 is single-rater, author-labeled (Jae Wook
Cho) — stated as a limitation up front (labels not independent of the system under evaluation; v1
metrics indicative, not an independent benchmark), the eight non-blind author-adjudicated papers named
(wheaton/agtzidis/ciric/viduarre/derosa/braun/mueller/cole), a second/panel rater + inter-rater kappa
deferred and conditional on publication. Filled labeler + start date; left the second-rater slot
blank. The protocol was NOT committed until this point, so it stays v1 (completing the draft, not
amending a pre-registered doc).

Committed the protocol ALONE as 9eff653 and pushed. The Tier-A/Tier-B matcher (`base_pipeline_match.py`
+ test, previously staged) was deliberately unstaged and held back as untracked — it lands as its own
commit later, after its two known bugs (C-PAC/CPAC tokenize-before-join; greedy boundary-blind
version-strip) are fixed against real label/prediction pairs. Only the protocol needs to be
permanent-before-labeling; the matcher explicitly does not. Labeling begins next.

---

## 2026-07-18 (evening)

Hours: 20:13 - 22:05 ET

Two protocol amendments, the label corrections they enabled, and the labels into version control.
First, v1.1 (`34aa9cb`): `pipeline_specificity` became a list parallel and positionally aligned to
`value` for REPORTED rows (singletons are one-element lists; blank for DEFERRED/NOT_REPORTED) — driven
by multi-tool-plus-custom papers (liu_2005, mueller, cole, ciric) a singular field would flatten.
Replaced the lost 21-line citation-index backlog stub with the full regenerated write-up (`500ae38`;
DOIs are `<verify>` placeholders, flagged unverified-from-memory; the deferral-reproducibility section
survives as one of nine).

Then v1.2 (`e0eb09d`) after solo labeling surfaced three status mislabels (vanderwal, power, tang):
added a Status decision rule (status tracks whether a tool is NAMED — independent of detail level,
version, or parameter-deferral) and sharpened D11 with the "names tool + defers steps -> REPORTED"
shape. With v1.2 committed, applied six confirmed label corrections to the workbook (backed up to
_v1.1 first, then verified only 9 cells changed): vanderwal DEFERRED->REPORTED (misclick), power
REPORTED->NOT_REPORTED (first NOT_REPORTED row — names no tool), tang DEFERRED->REPORTED with
DPABI/SPM12 named + steps deferred to ref 28, liu_2005 value filled to match its 2-element specificity,
cole specificity made a 2-element list, ciric "XCP Enginer" typo fixed. Post-edit structural check
clean corpus-wide (every REPORTED row len(value)==len(specificity)).

Finally brought the answer key under version control (`3b34b80`): the 19 labels had existed only as a
lone xlsx in Downloads. Created ground_truth/ with the human-editable workbook, a pre-v1.2 provenance
snapshot, a README, and a canonical CSV DERIVED from the xlsx (self-describing: labeler +
protocol_version per row). Verified the CSV faithful to the xlsx row-by-row across all 19 rows before
committing — a scored CSV that didn't match the labeled xlsx would silently corrupt every downstream
number. The matcher remains untracked (its two known bugs unfixed); it lands separately. Labeling of
the base_pipeline field is complete under v1.2.

---

## 2026-07-20

Hours: 18:48 - 20:06 ET

Established the post-v0.4.0 base_pipeline prediction set for scoring, diagnosed a fabrication, and
hardened the ground-truth artifact. No post-v0.4.0 full-corpus batch existed (all batches <= Jul 10;
v0.4.0 span-recovery = 2560bb1, Jul 13), and batch_v7_full showed oconnor/derosa base_pipeline MISSING
— the pre-v0.4.0 signature. So ran base_pipeline extraction on the 18 distinct labeled paper_ids at
HEAD, model pinned to v7's sonnet-4-5 (delta = code-only), K=3 (user-confirmed) into a gitignored
results/batch_v040_labelset/ with a manifest. 4 papers span-recovered (derosa, liu_2013, oconnor,
weber) — all MISSING in v7, EXTRACTED now, exactly why v7 was stale. Alignment preview (not scored): 14
aligned, 4 flagged — cole/liu_2005 pred-MISSING vs label-REPORTED (extraction vs slicing),
poldrack/viduarre pred-EXTRACTED vs label-DEFERRED. K=3 earned its keep: viduarre flipped 2 EXTRACTED /
1 DEFERRED. (Process lesson: mis-killed a healthy first run — per-paper print()s were block-buffered to
the log and output landed in a doubled path from a relative output_dir; re-ran clean watching written
files, not the log.)

Diagnosed the viduarre fabrication ("HCP minimal preprocessing pipeline", absent from the paper, on
2/3 draws). The v0.4.0 value-support guard is real and its matching is sound (quote_supports_value
returns False on the pair; whole-token, not substring), but extractor.py:682 gates it
`(not recovered) or quote_supports_value(...)` — so it fires ONLY on tolerant-recovery spans; a clean
span match bypasses it. The model attached the real Glasser deferral sentence as the span for a
fabricated name; on the 2 draws where that quote clean-matched, the guard never ran. Classification:
(a) guard not wired into the clean-span path — NOT the substring hole. The guard is inconsistent, not
the model (draw 3 the model also emitted the fabrication; the guard caught it because that draw's span
was recovered). Report-only; fix is a separate scoped task (run the guard on every extracted value).

Protocol v1.3 (named-by-provenance rule): a pipeline referred to only by institution/lab + citation
("a pipeline developed at Washington University, St Louis [45]", poldrack_2015) names no invocable tool
-> DEFERRED_TO_CITATION, not REPORTED; recorded the provenance-phrase-as-name extractor-error class
(distinct from fabrication). poldrack's label already conformed. Then Option B for label-set
versioning: dropped the per-row protocol_version CSV column (unreproducible from the xlsx, which has no
version column, so it silently reverted on re-derive), moved the version to a set-level statement in
README, and wrote a committable deriver (derive_labels_csv.py) that reads the version from README and
emits no version column. Verified the invariant: re-derive is byte-identical and loses no label data
vs the committed CSV (all 19 rows, 7 shared columns) — the ground-truth CSV is now faithfully
reproducible from its xlsx source. v1.3 + Option B staged; matcher still untracked.

---

## 2026-07-22

Hours: 19:15 - 20:42 ET

Committed v1.3 + Option B (e19007c) and the 2026-07-20 DEVLOG entry (de4ddb1), then scored the first
base_pipeline number end-to-end. Fixed the matcher's real latent bug (greedy version-strip ate
digit-led tool names: `normalize("3dvolreg")==""`) with a boundary-aware regex; blast-radius gate
showed zero corpus impact; the C-PAC/CPAC concern was already handled by the whole-token join (verified,
not "fixed"). Froze the post-v0.4.0 prediction set (predictions_v040_frozen.csv, provenance header,
per-paper 3 draws + majority + span_recovered + methods_found) because the gitignored batch is
non-reproducible (non-stationary) — the scorer now reads the frozen file and is byte-identical
frozen-vs-batch. Committed the minimal pre-registered Tier-B alias table (FCP, motivated by liu_2013;
KB recognize() covers chen/oconnor/vanderwal) BEFORE scoring Tier B.

Tier-A (N=17 blind, examples excluded as non-blind, viduarre reported separately): status agreement
14/17 (82.4%), Tier-A full 10/17 (58.8%), Tier-B full 14/17 (82.4%); A->B delta +23.5pts recovered
ONLY the 4 surface-variant same-pipeline pairs, absorbed zero errors. Error decomposition (not a lump):
cole = INPUT-CORRUPTION (pypdf glue AFNI48, re-adjudicated from "extraction failure"), liu_2005 =
SLICING (methods_not_found), poldrack = CONTESTED (bracketed-citation deferral needs citation-reading),
power = correct honest absence. Of the 2 non-viduarre errors, NEITHER is a model reasoning failure —
both are upstream-input failures. viduarre (separate) fabricates "HCP minimal preprocessing pipeline"
2/3 draws.

Then the guard-scope fix. Diagnosed extractor.py:682 `(not recovered) or quote_supports_value(...)` —
the guard runs ONLY on recovered spans, so a clean-span fabrication (viduarre's Glasser-deferral quote
clean-matches) bypasses it. C1 blast-radius gate: the model's raw verbatim_quote is NOT persisted for
base_pipeline (only the resolved span), BUT resolve_quote tiers 1-4 are never-fuzzy and
quote_supports_value is normalization-invariant, so the resolved span.text is a PROVABLY-equivalent
proxy for the gate on clean spans. Gate PASSES: every correct clean-span extraction has its value in
its quote (none demoted); the only two that flip (viduarre, poldrack) were wrong EXTRACTEDs. Applied
the fix (guard unconditional), added clean-span guard tests, and replayed on the frozen data: viduarre
-> DEFERRED 3/3 (fabrication caught), poldrack -> MISSING (bracketed citation unparseable by the
attribution matcher, so honest MISSING not DEFERRED — the fabricated name is gone but the deferral
still unrecognized). Blind rates unchanged (poldrack was and stays a status-disagreement); the fix's
value is eliminating the fabrication class, not moving the blind number. No correct extraction demoted.
Also recorded the PDF-glue false-MISSING finding as a backlog note. All staged, not committed: matcher +
test (commit 1), frozen + alias + scorer (commit 2), guard fix + tests + backlog (commit 3).

---

## 2026-07-23

Hours: 17:07 - 22:38 ET

Finished the guard-scope task from 2026-07-22 (clean-span guard regression tests, PDF-glue backlog
note) and committed + pushed the whole base_pipeline first-number arc: matcher fix (45618e1), frozen
predictions + Tier-A/B scorer + FCP alias (b329345), value-support guard scope fix (efbe14a), DEVLOG
(3c3c261), a cole/coverage correction (a79c089) — pushed de4ddb1..a79c089.

Then a long deterministic + causal-test sitting that overturned two inferences of my own. (1)
Quantified pypdf tool-citation glue: incidence is rare (only cole AFNI48/Freesurfer49; all 7 SPM+digit
hits are real versions, discriminated), and measured the deglue blast radius (541 word+digit tokens,
~0.2% naive precision — versions/templates/atlases/genes would be corrupted; do not ship). (2) Deglue
CAUSAL test refuted my own Part B "cole = PDF-glue" reclassification: both variants (AFNI48->'AFNI 48'
and ->'AFNI', K=3) still MISSING 3/3 — cole is a genuine extraction failure, not corrupted input.
Corrected the scorer + findings doc + README accordingly, and named two denominator omissions
(binder_1999 unlabeled; chen's counted row non-independent).

(3) Tested liu_2005 the same way: its full-text fallback interleaved the BrainVoyager sentence with
the reference list (two-column pypdf); a clean de-interleaved slice recovers BrainVoyager 3/3, so its
MISSING WAS input-corruption (attribution held) — distinct from cole. (4) Surfaced a multi-tool
under-extraction pattern (single-tool 11/11; multi-tool <= 1 of N) and the D4 recall-blindness that
hides it (set-membership is precision-only), in a new findings doc (d981c38); layered honestly — liu
is both (corruption + 1-of-2), and the dropped elements differ (cole 2 named tools, tang 1, liu a
descriptor). (5) Coordination probe (95de4ce): holding cole's real slice constant, singleton 'AFNI'
extracts 3/3 while 'AFNI and Freesurfer' MISSES 3/3 -> the "X and Y" coordination is causal IN
FULL-SLICE CONTEXT (short slice extracts it mangled; qualifier load-bearing). Prompt-fixable. Caught
and fixed my own confounded first probe (changed slice length + sentence).

Closed with the next target scoped, not started: the base_pipeline.version false claim —
extractor.py:636 hardcodes version to MissingFromPaper (prompt never asks), render.py:607 ->
cobidas.py:156 surfaces it as COBIDAS coverage, reading as a literature finding ("papers don't report
versions") though 7/19 papers do (oconnor 0.4.0, derosa 5.0.10, liu_2013 1.1-beta, 4 fused-SPM).
Presented fix options A (stop the misrepresentation, minimal) vs B (build version extraction, gated);
awaiting scope. The through-line of the day: four inferences tested, two refuted (cole-glue, and my
own confounded probe) — the record working as intended.

---

## 2026-07-24

Hours: 17:46 - 22:43 ET

Pushed the 2026-07-23 tail (a79c089..a91f5bd), zipped both repos' tracked source+docs for a Claude-chat
context handoff (~/Downloads/neurorepro-context-2026-07-24.zip, 206 files, venvs/results/PDFs
excluded), then built base_pipeline version extraction (Q1: paper-STATED versions) to option B, the
real fix for the false "0/N papers report a version" claim.

The bug: base_pipeline.version was hardcoded to MissingFromPaper (extractor.py ~636) and the prompt
never asked, so cobidas.assess_coverage read the constant back out as a literature finding — false
(oconnor 0.4.0, derosa 5.0.10, liu_2013 1.1-beta, plus fused-SPM). Verified all four design anchors at
HEAD first, and confirmed infer_base_pipeline_version bails on an EXTRACTED extraction arm (so Q1/Q2
never cross). Built Q1 paper-only, firewall-clean: new base_pipeline_version FieldExtractionResult +
prompt stanza + _build_version_pf helper — EXTRACTED iff the paper states a SEPARATE version string AND
quote_supports_value passes (the same guard the name uses, so an inferred "0.4.0 was current then"
can't launder in as EXTRACTED); else MISSING. DECISION locked (Option 1): a version FUSED into the name
("SPM12") is name-only, version MISSING — do not decompose. The ProvenancedField invariant caught a
design slip (EXTRACTED requires inference=NOT_APPLICABLE, not LeftMissing — Q2 bails anyway).
infer_base_pipeline_version / KB / cobidas.py all UNTOUCHED — cobidas just reads a real status now.

Wired version as a trailing optional arg so the 9 existing name/ref tests were unchanged. 4 new tests
(separate-version EXTRACTED for 0.4.0/5.0.10/1.1-beta; fused-SPM MISSING; version-not-in-quote guarded
to MISSING; none -> MISSING); 270 passed, ruff/mypy clean. Stage-A inspection (K=1, NOT a scored rate —
no version ground truth yet; caught + fixed my own type().__name__ accessor bug that first showed a
false 0/18): oconnor 0.4.0, derosa 5.0.10, liu_2013 1.1-beta extracted; fused-SPM and no-version cases
MISSING; assess_coverage version-addressed 3/18 (was 0) — the false "0/N" is gone. Committed 597e42e
and pushed. Deferred: Stage B (seed base_pipeline_version ground truth, then score a rate) and the
multi-tool "X and Y" prompt fix.

---

## 2026-07-25

Hours: 14:19 - 20:21 ET

target_space, end to end: audited the abstract's number, reproduced it at K=3, then fixed the real
issues under it. First a read-only audit of the SfN "13 of 20 (65%) could not be resolved to a
canonical specification": it lives ONLY in untracked sfn_review_v5/v6.xlsx (generate_sfn_review reading
gitignored batch_sfn_v5), the generator docstring says a stale "10/20", it is EXTRACTOR-OUTPUT-ONLY
(no target_space ground truth; review columns empty), from a murky-provenance ~June run, with the
target_space silent-drop bug (span-resolution-hard-drop.md, Phase-2 unfixed) able to move it. Then a
K=3 re-run surfaced the 13 verbatim sentences and bucketed them — mostly bare "MNI" (anachronism/era-
standard), 2 genuinely vague ("atlas space"), and oconnor naming a specific FSL file the value
flattened to "MNI".

Built the fix as one coherent change (design B): FORMALIZED the versioning convention (additive vocab =
patch bump IN PLACE, pure re-stamp hop, no new root file; structural = minor/major with a doc-
transform), added study_specific to TargetSpace as the first patch (0.4.0->0.4.1), fixed the FSL-file
resolver (oconnor), and REFRAMED the reporting middle state "Out-of-vocab" -> "Family-specified" (a
completeness level, not a failure) with the distribution as the headline (replacing the contradictory
10/13). Verified the B premise at HEAD; corrected the design's wrong assertion list (test_methods_finder
had no 0.4.0; real files were 3 test modules + the per-version schema export). Regenerated the two
examples + a new study_spec-0.4.1.schema.json (0.4.0 frozen); added a 0.4.0->0.4.1 migration test + 4
resolver tests. Main 234, extractor_mvp 274, ruff+mypy green, zero regressions. Post-change K=3: 5-way
distribution Canonical 2 / Family-specified 12 / study_specific 1 / native 0 / Absent 5 (stable, 0
flips); mueller flipped absent->study_specific (fix works); oconnor stayed family-specified (model
extracts bare "MNI"; resolver fix correct but inert — the file is only in the quote).

Committed the change (08e3795 schema-only from a pre-commit stash quirk, then 9f9677e completing it —
no force-push) and pushed. Then a read-only inspection of the oconnor question: is specificity-
flattening systematic? Deterministic value-vs-quote AND value-vs-full-text diff across 20 papers ->
FLATTENED = 1/20, oconnor only. The other family-specified papers are genuinely bare "MNI"/"atlas
space"; every other specificity signal adjudicated to a non-target_space context (fsaverage5/Conte69 =
surface field, a results .nii.gz, an activation description, an ANTs reference title). No cross-field
flattening (base_pipeline versions now route to base_pipeline_version; resolution_mm atomic). Wrote
docs/findings/extraction-specificity-flattening.md (staged, not committed). Recommendation: label FIRST
— oconnor is a one-off to label as canonical (scoring surfaces one clean extraction error), not a
systematic flattening needing a prompt fix. Next: seed target_space 3-state ground truth (Stage B).

---

## 2026-07-27

Hours: 19:21 - 21:12 ET

target_space ground truth, pre-registered end to end. First closed out the specificity-flattening
finding: committed docs/findings/extraction-specificity-flattening.md (31b02b1, pushed) — oconnor is a
1/20 one-off (verified value-vs-quote AND value-vs-full-text), so ground truth labels around it rather
than a prompt fix. Then the load-bearing STEP-0 check gating dual-axis reporting: is target_surface
genuinely EXTRACTED or schema-only? Direct grep + a 6-agent adversarial workflow both confirmed
EXTRACTED — all four legs wired (spec ProvenancedField preprocessing.py:844; required no-default
FieldExtractionResult extractor.py:86; prompt stanza 221-228; build-path _FIELD_SPECS->loop->_assemble,
no hard-coded default). K=3 cached inspection: poldrack->fsLR_32k, chen->fsaverage5 fire cleanly;
weber's "Conte69" flattens to MISSING via value_not_in_literal (raw preserved in diagnostics). Placed
the protocol (docs/ground-truth-protocol-target_space.md), updated CALL 1's verify note + CALL 4's
DEPENDENCY with the confirmed extraction fact, and built the blank labeling workbook
(ground_truth/target_space_labels_v1.xlsx) — 3 tabs mirroring base_pipeline, dropdown + 2 worked
examples (oconnor->canonical, mueller->study_specific), 18 blank corpus rows; staged, not committed.

Then ratified both open calls to v1.1 and pre-registered. Verified the load-bearing facts FIRST with a
4-agent workflow (never launder a ratification's premises into a committed pre-reg): poldrack's CIFTI
subcortical/cerebellar units come from the individual's FreeSurfer segmentation, not an atlas
parcellation (CALL 4 warrant HOLDS — honest caveat kept in text: the BOLD IS resampled into the unnamed
atlas grid as a registration substrate, so deferred not native_volume); poldrack's pipeline is
provenance-deferred ("a pipeline developed at Washington University, St Louis45"), matching base_pipeline
v1.3's named-by-provenance DEFERRED, so `absent` here would contradict a committed protocol on the same
paper; and — correcting the ratification's own framing — Conte69 IS the fs_LR space the enum already has
(fsLR_32k/164k), so weber's flattening is a SYNONYM-resolver gap, NOT an enum gap and NOT oconnor-class.
CALL 4 ratified in the NARROW form (per-axis completeness; exemption only under the conjunction
[volumetric target unnamed in-paper AND volumetric analysis units individually-defined]; chen/weber name
MNI -> no credit-by-substitution; headline = two distributions + a joint statement, papers in both).
CALL 5 resolved Option A: added `deferred` as the sixth state; poldrack volumetric SUPERSEDED
absent->deferred (explicit, not a silent edit). Updated the workbook to a 6-state dropdown. A 2-agent
adversarial pre-commit review came back clean (all 7 cautions satisfied — no overclaim/contradiction/
leak; workbook still blank, only the 2 examples). Committed the pre-registration 65e7d91 and pushed.
Deferred (logged in the protocol's Carry-forward, not acted on): the Conte69 synonym-resolver fix (a
cheap additive alias, possibly an fsLR_10k value) — label around it, let the score surface it. Next:
label the 18 papers blind, then derive + score.

---

## 2026-07-28

Hours: 18:40 - 21:33 ET

Mostly manual labeling. Author worked the first pass of target_space ground truth against the
pre-registered v1.1 protocol — blind, full-text, one of the six states per paper for the 18-paper corpus
— in a first-pass workbook (ground_truth/target_space_labels_v1_firstpass.xlsx). Housekeeping only on
the code side: committed + pushed the 2026-07-27 DEVLOG entry (a8df866). First-pass labels are still in
progress and uncommitted (the committed blank instrument target_space_labels_v1.xlsx is untouched as the
pre-registration). Next: finish/QC the pass, then commit the ground truth as a distinct act (labels
committed before any scoring run, per the protocol), and derive + score.

---

## 2026-07-29

Hours: 17:04 - 21:31 ET

Protocol v1.2 (CALL 6/7) + finalized the 19-paper ground truth — authored, adversarially verified,
staged, NOT committed (held for review). Ratified CALL 6 (a composed transform chain stated end-to-end
and terminating in a named template specifies that template — ciric → study_specific) and CALL 7
(target_space = terminal volumetric state of the functional TIMESERIES: (a) normalizing derived
statistical maps doesn't set it, binder → native_volume; (b) a timeseries exiting to the surface axis
with no volumetric target is native_volume, chen). STEP-0 verify caught that the pasted CALL 6/7 text was
NOT in the file (protocol still v1.1) — halted per the pre-reg discipline, then authored v1.2: title +
changelog bump, chen SUPERSEDED family_specified → native_volume (its only MNI is the surface frame via
sphere registration), binder added as the 19th paper, family_specified broadened to match CALL 3's "a
template was named" rule (covers gordon's "an EPI template", wheaton's "SPM MNI template"; absent stays
"named no template").

Two adversarial-read rounds (parallel Explore agents + synthesis) hardened it. Round 1: the native_volume
criterion admitted poldrack (its unnamed atlas grid IS an identifiable terminal state → added "AND is
native / reaches no volumetric template" at every locus); binder mis-filed 7(b)→7(a); the recording
convention's "stated absence" re-imported the requirement CALL 7(b) relaxes (harmonized to "stated OR
evident from the enumerated pipeline"); weber/chen asymmetry made explicit (weber named MNI152
volumetrically → family_specified; chen's MNI is the surface frame → native_volume). Round 2 caught the
load-bearing one: the broadened family_specified could pull power out of `absent` (the sole absent the
reframe rests on). First fix (artifact-vs-space) was still leaky — pinned power by enumeration, not
principle — so reframed to the NAMED-vs-UNNAMED test: power resampled into SOME (unnamed) atlas grid, an
artifact exists, but named no template → absent; poldrack's atlas is equally unnamed but
citation-attributed → deferred; gordon named a specific template (modality "EPI", referent UNVERIFIED) →
family_specified. Also fixed a Value-column vs labeling-step-4 contradiction for deferred papers (Value =
verbatim term or blank per the convention — poldrack "atlas", braun/viduarre blank; cited work goes in
the quote/Notes) and softened gordon's over-asserted referent.

Workbook finalized (Excel closed first): B1 moved binder's Value annotation to Notes (Value column =
verbatim target term only, so the future CSV has one meaning per column); added gordon's
unverified-lineage caveat; regenerated Start-here/Glossary to v1.2 while preserving the Labels sheet —
proved by a cell-diff showing EXACTLY the 3 authorized edits and by asserting the dropdown (B4:B22) +
frozen panes survived the openpyxl round-trip (openpyxl silently drops those). Renamed firstpass →
canonical target_space_labels_v1.xlsx (git renders blank→filled). Final labels: family_specified 10 /
deferred 3 / native_volume 2 / study_specific 2 / canonical 1 / absent 1 = 19. Both files modified +
UNCOMMITTED — the final-read fixes are applied but not yet re-verified; the two-commit pre-registration
(protocol first, then labels, per base_pipeline discipline) is held for author review next session.

---

## 2026-07-31

Hours: 17:00 - 17:16 ET

Pre-registration committed. Ran the terminal DERIVABILITY check on v1.2 — a blind test (one agent per
paper, protocol + recorded quote only, no conversation, no full paper): can each of the 19 labels be
derived from the document alone? Designed with a hard stopping criterion (fix only a rule that
contradicts a label or another rule; wording nits commit as-is) so the review loop terminates rather than
generating endless plausible findings. 18/19 derived cleanly and matched the workbook. One defect:
liu_2005 — its quote "transformed into Talairach space (Talairach and Tournoux, 1988)", with the
functional timeseries reaching Talairach, literally satisfies the v1.1 canonical clause "OR Talairach
with its atlas", so a blind rater is COMPELLED to canonical, contradicting the family_specified label.
Fixed the PROTOCOL (never the label): Talairach reclassified canonical → family_specified (it is a
coordinate system realized by many digital templates — AFNI TT_N27, the 1988 atlas, SPM's — so citing it
names the family, not a resolvable variant); struck the canonical clause; added the Talairach identifier
to family_specified + a CALL 2 bullet + changelog item 6. cole (cites no atlas — "a Talairach template")
correctly stayed a nit. Committed the pre-registration in order — protocol first (305bcb6), then labels
(bc28f12) — and pushed (73a17ea..bc28f12). Final distribution: family_specified 10 / deferred 3 /
native_volume 2 / study_specific 2 / canonical 1 / absent 1 = 19. Three adversarial-read rounds plus this
derivability check converged; the timestamped commit order is the pre-registration. Next: derive the
scored CSV + build a target_space scorer (none exists yet), then score extractor output against the key.

---

## 2026-07-31 (evening)

Hours: 17:16 - 21:48 ET

Scored target_space end to end, and the scoring surfaced more than the labels did. Derived the labels CSV,
PRE-REGISTERED the extractor->label mapping table + froze the K=3 predictions before scoring (7bca618),
then built a scorer (fbde79d). First number (3 correct / 15 error) was WRONG — the map v1 keyed on status
alone, so 9 papers where the extractor GRABBED a bare "MNI" but relabeled status->MISSING
(value_not_in_literal) scored as absent, a spurious "enum-gap capability class." Author caught it against
my own earlier "12 family-specified" inspection; map v2 keys on failure_reason -> 11 correct / 7 error.
Kept the integrity discipline: committed v2 with a stated reason, reported both numbers; the collapse was
PREDICTED (9) before the change and came out 8 (liu_2005 deviated), and the deviation was run down rather
than absorbed — that mismatch is the argument v2 tracks the extractor, not a target number.

Findings that outlived the rate. false-missing: the spec records MissingFromPaper for papers that stated
"MNI" — asserting absence where there's presence, in the system whose thesis is that distinction (a core
defect the reporting layer masks). CALL 7 native_volume (binder/chen) can't be emitted by the extractor
because the value-support guard (the anti-fabrication firewall, shipped after viduarre) forbids an
absence-evidenced value — right to keep the guard, wrong to force it through extraction. Verified poldrack
is NOT the base_pipeline [45] parser bug (target_space deferral is model-driven; poldrack extract-over-
defer'd "atlas space") — my own over-reach for a demonstrated mechanism, retracted; viduarre is a distinct
silent-miss, so the deferral class split in two.

Found the bedrock-extractor AWS profile (I'd wrongly said no creds) and ran the two pending items, outcomes
pre-committed. liu_2005: clean de-interleaved slice -> Talairach 3/3 with the BrainVoyager 3/3 slice-
validity gate passing -> input-corruption DEMONSTRATED CAUSAL (cole's opposite). binder: Talairach 3/3 ->
results-space leak confirmed live (CALL 7(a)); denominator closed at 19. Reframed scoring three ways
(separating "model wrong?" from "label scoreable?"): 5 reachable-accuracy / 2 unreachable-LEAK (active
defects, not absorbed — would count if native_volume becomes reachable) / 1 input-corruption; both
denominators with Wilson (blind 11/17 = 64.7% [41,83]; reachable-only 11/14 = 78.6% [52,92]), the exclusion
marked post-hoc; and wired the scorer to consume the system's OWN methods_not_found slice flag (auto-flag,
0 collateral, scales past hand-tests).

Closed on the architecture (design-resolution.md): the false-missing is a TYPE problem (closed Literal),
not vocabulary — neither add-enum-member (A) nor add-completeness-field (B) fixes it; the fix is
verbatim-always typing (verbatim term always + optional resolved id), which makes extraction structurally
incapable of the defect and makes completeness derived not stored (kills B). CALL 7 routes to the
INFERENCE layer (basis enumerated_pipeline_complete + ceiling; guard intact). Step-absence ("deliberately
not performed" != silence — the hallucination-vs-absence thesis at the step level) HELD until it recurs
(motion/smoothing). Both correctness fixes are focused next-session work, recorded so the reasoning
survives — the conversation is not the artifact. Commits 305bcb6..c041f6f.


## 2026-08-06

Hours: 17:50 - 20:54 ET

Built the verbatim+resolved retype the last session designed (v0.5.0), the false-missing TYPE fix. Opened by
splitting slice_suspicious into two corruption states — SUSPECT (the system's own methods_not_found flag;
untested; stays in the denominator) vs DEMONSTRATED (a tested causal claim; excluded) — numbers invariant.
Two hard gates before touching the core type: nested generics (ProvenancedField[SpecifiedTerm[TargetSpace]])
round-trip and reject bad members in this Pydantic v2 — PASS; and what power_2014 actually emits — "atlas
space" (no_match), so the two-field struct is insufficient and the resolver-verdict field goes in. Retyped
all five literal_type fields to SpecifiedTerm{verbatim, resolved, resolution}; structural 0.4.1->0.5.0 with a
REAL doc-transform hop (lift EXTRACTED bare->struct, carry MISSING false-missings forward — migration CANNOT
repair them, the term lived only in the gitignored diagnostic); _process_field stops relabeling; consumers, kb
inference, generators, schema, scoring map v3 (keyed on the value; 11/8 held) all moved. Full suite green
(root 235, extractor_mvp 275), mypy+ruff. Commit 382795a.

Caught gordon at DESIGN time, before STEP 5's gate could. The design's completeness rule "unrecognized ->
absent" would have silently moved gordon ("EPI template", a NAMED template) correct->error; kept v2's
named-vs-unnamed gesture test inside the unrecognized branch, applied after underspecified->family, so no
number moved. And named the honest limit of GATE 2's third field: on this corpus it changes NO grade (the
gesture heuristic reproduces v2), and gordon/power are both unrecognized yet grade differently — so resolution
is PROVENANCE, not the grader; completeness derives from the heuristic PLUS the field. Wrote that into the
docstrings so a future reader isn't misled.

Then demonstrated it end to end, and the demonstration was more interesting than the retype — as the pre-reg
warned. Pre-registered before spending (7ab4894). The 1-paper smoke contradicted the expectation on the first
data point: agtzidis stayed MissingFromPaper via quote_not_found, not EXTRACTED. The cause was a COMMITTED
finding the pre-reg failed to consult — span-resolution-hard-drop.md (Phase 1) named agtzidis target_space as
a pypdf /C2 mangle (× rendered "/C2"), Phase 2 fixes never run. The value_not_in_literal short-circuit had been
HIDING it: the old flow never reached quote resolution for these papers; remove it and a latent, documented
defect surfaces. Artifact-vs-conversation gap in a new direction — the findings doc had it, the pre-reg
didn't. Amended the pre-reg to a true expectation (bae9a84), restated the claim narrow, then ran K=3 x 19
papers (57 bedrock calls, 0 failed, 0 value_not_in_literal on every draw). Result: 11/12 false-missings now
record the term — EXTRACTED, K=3-stable, verbatim MATCHING the frozen raw (extraction unchanged, only
recording). agtzidis stayed quote_not_found all 3 draws, scored family_specified via the diagnostic raw = the
OLD side-channel, NOT the fix (flagged, not laundered). Two non-stationarity movers (braun deferred->absent,
mueller absent->study_specific, both stable 3/3 this run) shifted the BLIND rate 11/17->10/17 = model variance,
not the retype; the translation was faithful for the target population. The headline "the spec no longer
records MissingFromPaper for a stated term" is too broad and now known false for agtzidis; the true claim is
narrower — value_not_in_literal path closed, quote_not_found path (a separate, previously-documented defect)
still open. Refreshed the frozen predictions into real 0.5.0 shape (v050 CSV). Commit 015a5ce.

Closed scoping motion_correction (read-only) as the next field. Rich 9-field step, 4 closed Literals, method
the headline candidate; neither extracted nor emitted today. Corpus attests it densely — 16/19 name or imply
a tool, only braun truly silent (deferred). The real work is not enum coverage but two boundaries the protocol
must adjudicate — realignment vs coregistration terminology (binder/liu_2013 state motion correction AS
"coregistration"/"iterative procedure") and the realignment step vs motion-params-for-nuisance (ciric/gordon/
chen name both in one breath) — plus the same pypdf mangling that broke agtzidis: wheaton's "motion
correc-tion" (hyphenated line break) evaded the grep, a survey false-negative to design around. COBIDAS commits
only the D.3 row title + mandatory-conditional flag, not the sub-item list.

Commits: 382795a (retype), 7ab4894 + bae9a84 (pre-reg + amendment), 015a5ce (demonstration).


## 2026-08-07

Hours: 17:46 - 21:49 ET

Motion arc: protocol-before-extraction, a stronger blindness than target_space had — motion_correction is not
extracted, not emitted, not in `_assemble`, so the labels get written before any extractor output exists and
extraction is built TO the protocol, not the protocol audited FROM extraction. Schema prep first (v0.5.1):
added `transforms_combined` (COBIDAS D.3 bullet 6, "whether transforms are combined to allow a single
interpolation" — poldrack attests it) and retyped MotionCorrection's four closed Literals to SpecifiedTerm[X],
because the corpus already exceeds MotionCorrectionMethod's five members (derosa ICA-AROMA, binder's Cox
procedure, WashU in-house rigid-body) and a raw Literal would reintroduce the false-missing the retype just
fixed. Version-conflict named and resolved: the convention's enumeration lists "changes a field type" as
STRUCTURAL, but its governing TEST is "does any prior document break?" — none do, because no committed document
contains a motion_correction step. The test governs the enumeration on a never-emitted step → PATCH, pure
re-stamp; flagged, proceeded per instruction, recorded in the migration hop.

The artifact-vs-conversation gap, twice more. The step wanted me to amend DESIGN_cobidas_coverage.md; it existed
NOWHERE — repo, Downloads, git history. A governing decision living only in the chat project. Stopped rather
than fabricate the sections the amendment references but does not reproduce. Author supplied it; committed the
base VERBATIM (9bba492, the stale `extractor.py:645-725` ref preserved and noted, not silently fixed), then
merged the four-state amendment (b4bd214) — superseded text retained under pointers, firewall + 16-row registry
preserved verbatim, the Intersubject re-render dated as a consequence, not a new power finding. Then the gap one
level deeper: the committed coverage doc's §5 depends on the reason-partition concept, defined in an UNCOMMITTED
DELTA. Batch-committed all eight uncommitted design records verbatim (b6972ef; `--no-verify` to preserve one
file's trailing whitespace — archival records, not code) with a docs/design/README flagging that
DESIGN_anatomical_steps_v0_3_0 carries a now-FALSE claim (COBIDAS PDFs are page images, no text layer — they
aren't, D.3 reads fine, which is how the seven-bullet motion row got quoted). Without the note someone
re-derives row titles from the catalog on a stale caveat.

Ratified the five motion calls and pre-registered. CALL 2a is the sharp one: binder = described_only, not
deferred — the test is whether the paper's OWN text identifies the method (binder characterises the algorithm
in-paper: iterative, minimising variance between images) or whether you must read the citation (oconnor gives
only the operation name + a pointer → deferred). described_only therefore spans cole's bare "motion correction"
to binder's characterised algorithm; the detail lives in the verbatim quote, not the state. Flagged Cox 1996b
as unverified (1996a is the AFNI paper; 1996b is a different work) rather than assume a volume-registration
paper. CALL 1: deferred is not a reporting failure — DESIGN §2 counts DEFERRED_TO_CITATION as addressed, so
oconnor satisfies bullet 1; compliance and label state are different axes. Named-vs-unnamed stated as MECHANISM
not magnitude (tool identity changes estimated parameters → different nuisance regressors and FD-censored
frames; six papers feed those parameters) — did NOT cite a comparison study neither of us verified. Synced the
workbook Glossary to the ratified calls; confirmed the Labels sheet byte-identical (fingerprint match) so it
cannot drift and stays blank. Two commits, schema first so the protocol's `transforms_combined` reference
resolves against a committed field: c297479 (schema) then 2e331d0 (pre-registration — protocol + blank
instrument, before any label; the commit ORDER is the proof). First push of the arc: b89fef3..2e331d0 carried
08-06 and 08-07 both to origin/main.

Commits: 9bba492 (cobidas base) · b6972ef (8 design records) · b4bd214 (four-state amendment) · c297479 (motion
schema v0.5.1) · 2e331d0 (motion pre-registration). Pushed.


## 2026-08-11

Hours: 20:18 - 20:51 ET

Protocol v1.2 for `motion_correction`. Added CALL 8: D.3 bullet 7 ("slice-to-volume registration methods,
or integrated with slice time correction") is a property OF the motion correction — motion estimated
per-slice not per-volume, or motion+STC solved as one integrated operation — NOT whether STC ran at all
(that is the separate `slice_time_correction` row). A sentence listing STC and motion correction as
sequential steps addresses neither clause → `not_reported` (cole, gordon, chen); narrow exception, a stated
ABSENCE of STC forecloses integration → `reported` (agtzidis "(without slice timing correction)", ciric "We
did not apply slice timing correction"), consistent with the existing stated-negative-is-reported rule.
Expectation note: slice-to-volume registration is rare (fetal/infant); the scoping survey found zero corpus
instances, so the bullet should be near-empty — a high `reported` rate signals the bullet is being misread,
a finding about the standard, not a labelling failure. Bumped v1.1 → v1.2 (title, changelog, §5 header);
committed the protocol only (pathspec-scoped) as 4fa807f and pushed (cf0373b..4fa807f). Standing checks
first: ET clock (weekday but 20:xx, past the 17:00 commit block), HEAD, CALL count 1–8.

Excel had the labelling instrument open at first, so held the workbook sync rather than clobber the live
session, and gave the STEP 4 relabel report for the author's hand-edits (bullet 7 → `not_reported` for
chen/cole/gordon and liu_2005 — the last `reported` with no verbatim, unsupported under §6 regardless;
stays `reported` for agtzidis/ciric as stated negatives; `co-adjudicated` owed for agtzidis_2020 +
braun_2015). Once Excel closed, synced the Glossary tab to v1.2 (CALL 8 + near-empty note; legend → CALLs
1–8) under a gate proving only the instructional legend cell A22 changed and every label data cell +
dropdowns + freeze were byte-identical. Then, at the author's explicit direction and with the author
supplying every adjudication, transcribed the derosa_2025 row: method_state named_tool → described_only
(CALL 4 — ICA-AROMA is ICA denoising, no realignment tool named; performance asserted, so described_only
over absent); bullets 2–6 → `not_reported`; the two orphaned verbatims (F7 FLIRT/BBR coregistration, L7
"12 DOF" MNI transform) MOVED byte-identical into Notes with their exclusion rationale (evidence for a
second rater, not cleared); flagged `co-adjudicated` (§7 — assistant supplied the CALL 4 conflict and the
bullet-by-bullet corrections, author ratified); label marked PROVISIONAL pending Supplemental Materials
(§2.4.4 defers the FC-stream preprocessing). Also noted in Notes: realignment demonstrably occurred (§2.4.3
six motion regressors, §2.4.9 mean FD) though the step is never stated — the CALL 3 boundary in reverse.
Committed labels + Glossary together as c016858 and pushed; the gate confirmed no unintended cell moved.

Open for the author: bullet 7 → `not_reported` still to apply for chen/cole/gordon/liu_2005;
`co-adjudicated` Notes still owed for agtzidis_2020 + braun_2015; chen_2015 per-row CALL 7 scope; the
remaining SPM-family and other rows unlabelled. Flagged a protocol gap surfaced by derosa (three analysis
streams — univariate FSL+AROMA, RSA SPM12, FC CONN+SPM): which stream does the motion row record when a
paper runs several? Not worth a CALL for one paper, but a trigger if a second multi-stream paper appears in
the remaining ~ten (recorded here; a labelling-time home in the protocol still open).

Commits: 4fa807f (protocol v1.2 — CALL 8, 20:22) · c016858 (derosa labels + Glossary v1.2, 20:50). Both pushed.
