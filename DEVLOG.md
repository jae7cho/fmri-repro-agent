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


## 2026-08-12

Hours: 18:23 - 19:29 ET

Two author-ratified label-correction batches on `motion_correction_labels_v1.xlsx` plus a protocol
amendment, ending in an unresolved staging slip. Author adjudicated every label change; I executed the
specified diffs and did not adjudicate.

**51-cell correction set.** Four C-PAC/CCS wrapper papers (chen, oconnor, vanderwal, weber) → method
`deferred` with all six bullets `deferred` (CALL 1 pipeline-wrapper + CALL 7 bullet-level default; this
also resolved chen's long-open per-row scope); chen value → CCS. poldrack → `deferred`, bullets `deferred`
except fieldmap + combined-transforms `reported` with verbatims (CALL 7 overrides — applywarp *resamples*,
does not estimate motion; method deferred to ref 45, the WashU pipeline). viduarre bullets → `deferred`,
value blanked (wholesale deferral like braun, deferral target Smith/Glasser recorded in Notes) — the
on-disk value was already "Smith/Glasser", not the spec's "HCP", so blanked per the wholesale-deferral
intent and flagged. binder b5 verbatim extended to "…between images"; power b2 + b6 `reported` (rigid-body
stated-negative + combined interpolation); mueller b3 `reported` (SPM Realign & Unwarp). Applied
idempotently — the author had pre-applied several method_state changes during her own labelling, so the
spec's "from" states were stale-at-target (flagged). Caught and fixed an openpyxl `cell(value=None)`
no-op that had silently skipped viduarre's value clear (49/50 → re-ran from the pristine STEP-0 backup for
51/51). Gate confirmed only the specified cells moved; staged.

**Protocol v1.3 — narrowed CALL 8's stated-negative carve-out.** A stated negative counts as `reported`
only when it concerns *the bullet's own subject*; "we did not apply STC" is about a different step, so
agtzidis and ciric bullet 7 are `not_reported`, not `reported`. Contrast preserved (power's "rigid body
realignment" IS about the motion transform → bullet 2 `reported`) to keep the rule non-arbitrary; secondary
ground that both cells lack a verbatim (§6). Superseded carve-out text retained under CALL 8 with a
pointer, per amendment discipline. Result: bullet 7 is 0/19 across the corpus — the near-empty outcome
CALL 8 anticipated. v1.2 → v1.3.

**Two more label fixes under the new rule.** ciric b2 `reported` → `not_reported` (its verbatim was
func→struct BBR coregistration, a different D.3 row per CALL 2 — moved to Notes, same class as the poldrack
b2 fix); agtzidis reference-scan verbatim "mean" → the full sentence. Glossary synced to v1.3 with the
Labels sheet byte-identical (fingerprint c001ce → 93880b for the two label edits, then unchanged across the
Glossary write — proven by an in-script before/after diff).

**Staging slip, and its Option-A fix.** Intended a protocol-only commit but ran `git commit -m` without a
pathspec while the workbook was already staged at its 51-cell version, so the first attempt (70e47af,
since removed) mixed protocol v1.3 AND workbook@51-cell — the two things the two-commit structure was meant
to keep apart. Fixed the next sitting (2026-08-13), author-approved Option A: `git reset --soft 433b780`,
then re-committed by pathspec — protocol only (**82df9fc**), then the workbook carrying everything
(**1cfb8e8**: the 51-cell set + the v1.3 label edits + the two owed co-adjudicated flags) — and
force-with-lease pushed over the mixed commit (`70e47af...1cfb8e8 forced update`). The count was also
resolved: the labels message had claimed 12 co-adjudicated but the sheet held 11; agtzidis and braun —
owed across three turns under §7 and never landed — were added (agtzidis, where realignment was
reclassified from `absent` to motion correction in consultation; braun's wholesale deferral that became
CALL 6), taking the sheet-verified count to **13**, the figure used in the commit message. The slip is
recorded here, not tidied away.

Commits: 82df9fc (protocol v1.3 — narrow CALL 8) · 1cfb8e8 (motion_correction labels v1 — 19 papers, 13
co-adjudicated). Re-committed cleanly by pathspec after the 70e47af staging slip; force-with-lease pushed
2026-08-13. This DEVLOG entry committed separately, last.

## 2026-08-13

Hours: 20:05 - 20:49 ET

**v1.4 amendment applied (CALL 9) — six edits, verbatim, three paths.** Protocol
`ground-truth-protocol-motion_correction.md` v1.3 → v1.4: title, changelog, §5 header, and the CALL 9
body — the labelled unit is a preprocessing prefix, not an analysis (stream individuation by the paper's
own description with the labeller forbidden from creating one; the convergent / singly_attested /
divergent arms; divergence assessed on the bullet's ANSWER not the text; a deferring stream attests per
CALL 6; a pointer to the paper's own supplement is not a deferral but an UNREAD stream with no arm
assigned; `multi_target_unscoreable` as a scoring class distinct from `unreachable` — arity mismatch, not
vocabulary). tang_2025 ratified convergent on what tang wrote (both streams name SPM12 as the tool
performing the method; the CVR/FC value+quote mismatch reconciled); derosa_2025 ratified two-stream — RSA
is not individuated as a preprocessing prefix, since §2.4.3's DeRosa 2024 citation substitutes for the RSA
*method* and §2's Kim 2020 for *acquisition*, neither for preprocessing — FC stream unread, row
PROVISIONAL, three outcomes pre-registered before the supplement is read. K=0 divergent papers. New
tool-reference finding `docs/findings/dpabi-dparsf-spm-realign-equivalence.md` (byte-identical to the
drafted source): DPARSF's `Realign.mat` preset equals SPM12-master's realign defaults on all eleven
parameters, filed as a `version_default` KB candidate with both scope caveats in the doc — spm12 master
not a release tag, and the file read was `DPARSF/DPARSFA_run.m` not DPABI generally — and explicitly NOT
the basis for tang's label. Glossary CALL 9 row inserted at 29 (Recording convention → 30, Named vs
unnamed → 31). §7's co-adjudication list corrected from the 2 named papers (agtzidis, braun) to the 13
flagged in the instrument, derived live from Labels column Q at apply-time rather than transcribed from
the amendment; the derived set matched exactly — the check passed rather than tripped. Verification: the
five protocol hunks map 1:1 to the five text edits (3 deletions — old title, old §5 header, old §7
sentence — and 114 insertions; the stat bar's 117 is total changed lines), Labels sheet 0 cell diffs,
DVs and freeze J7 unchanged.

**C20 near-miss — a spec defect I authored, caught pre-commit by the transparency note and by no gate
item.** EDIT 6 told the applying agent to "replace `v1.3` with `v1.4`" in Glossary C20. I wrote that rule
against a 180-char-truncated read of the cell and therefore never saw that C20's only `v1.3` is a
historical fact about CALL 8 ("…narrowed v1.3 2026-08-12"), not a document version stamp — unlike B20,
C20 never carried a stamp of its own, so the rule presupposed one that does not exist. Applied verbatim
as specified, it produced "narrowed v1.4 2026-08-12": a false provenance claim, CALL 8 narrowed at a v1.4
date that did not yet exist, sitting in the labelling instrument's own legend. It surfaced because the
applying agent reported where the verbatim rule landed rather than only that it had applied; the defect
was identified from that flag in the design session and the author ratified the fix — revert the
substring, append "; CALL 9 added v1.4 2026-08-13" before the paren, mirroring B20. **The defect never
reached a commit** — a near-miss, not a retraction. Root cause is the recurring one: a claim asserted
from a partial view of the artifact rather than the artifact (here the claim was a rule, and the partial
view was my own truncated cell read). Note what did NOT catch it — Labels byte-identical, DVs, freeze,
CALL count 1–9, all three v1.4 strings, derived §7 list: every gate item green against a substitution
that was correctly applied and semantically wrong. The control that worked was
mechanical-rule-plus-report-where-it-landed, which is cheaper than a gate and catches a class gates
cannot.

**One unspecified action, named rather than passed silently.** The inserted CALL 9 Glossary row (B29/C29)
was given row 28's (CALL 8) cell style so it renders like its siblings. Benign and correct, but not in
EDIT 6 — logged because it is an unlogged change to a versioned artifact.

Commits: 7643d8a (protocol v1.4 — CALL 9) · 324d8fd (tool-reference finding: DPARSF realign ≡ SPM12
defaults) · 0475605 (Glossary v1.4 sync — CALL 9 row + header, C20 corrected before commit). Step 1 of
the motion arc (the multi-stream gap) closes here. This DEVLOG entry committed separately, last.

## 2026-08-17

Hours: 17:43 - 22:15 ET

**Protocol v1.5 applied — CALL 1 clarification + CALL 10.** Six edits, three paths, no label changes.
`ground-truth-protocol-motion_correction.md` v1.4 → v1.5. **(a) CALL 1 — the binding test.** The v1.1
package-vs-wrapper refinement excluded derosa ("the package-vs-wrapper rule does not decide its `method`")
without stating what governs it instead, so the reasoning lived in the instrument's Notes and not in the
protocol — the one place a second rater looks. The governing question is neither package-vs-wrapper nor
named-vs-unnamed but **binding**: does the paper attribute a named tool to THIS step, or only to the
enclosing procedure set? Bound → populates (agtzidis: "performed with SPM12 … The process comprised
realigning …", a one-to-one SPM12→Realign binding). Not bound → a package named as governing a procedure
set populates nothing, even named with a version. Bound but disqualified by another call → `described_only`
with a blank value. derosa carries it as the worked case: "using the FSL suite (version 5.0.10) …,
including motion correction via ICA-AROMA (version 0.3 beta)" — FSL bound to the procedure set, ICA-AROMA
the only tool bound to this step and routed elsewhere by CALL 4, nothing bound survives. The asymmetry
(versioned FSL yields blank, SPM12 yields SPM12) is binding, not specificity, and is stated as intended so
a rater does not read it as a labelling error. Written as a **positive test rather than a second
exclusion**, on the `temporal-firewall-fix` evidence that an exclusion-plus-near-miss stanza was overridden
by the model where a restructured ordered decision was not. **(b) CALL 10 — subject → role.** Ordered and
mandatory: subject before role, role before tool; a tool name is never the entry point. Axis 1 SUBJECT
restates CALL 2 as a gate. Axis 2 ROLE extends CALL 3 with **two** arms it does not contain — `APPLY`
(poldrack's `applywarp`, neither estimator nor nuisance consumer, in the same sentence as "head motion
correction") and `HOST` (MATLAB, Python) — alongside `ESTIMATE` (the only role that populates, and only
when bound per CALL 1) and `CONSUME`. Emission covers all five §3 states: `stated_not_performed` exits
before the decision rather than failing Axis 1's gate, since Axis 1 presupposes performance and a stated
negative names the operation and negates it. Seven worked cases with the wrong answer shown (poldrack,
ciric, cole, agtzidis, gordon, liu_2013, chen), the fitting-set limitation stated, and one clause noting
that the boundary between "an uncovered role" and "a role covered by another call" is itself a judgement —
derosa's ICA-AROMA is arguably an instance of the first hypothetical and is resolved by CALL 4, so the next
amendment will arrive here and should record which way it decided rather than adding an arm by default.
Glossary: C21 appended (756 chars), row 30 inserted with CALL 10 (1230 chars), `Recording convention` → 31,
`Named vs unnamed` → 32. Labels sheet 0 cell diffs, DVs and freeze `J7` unchanged. Workbook built on blob
`19497` — the corrected v1.4 C20 blob, not the pre-fix `19501` — verified from the blob, not from the
report.

**Gate item 6 near-miss — the gate carried the defect it was written to catch.** I wrote item 6 as
"B20, C20 and C21 each still contain `v1.1, v1.2, v1.3, v1.4` plus the new `v1.5`" — a **hardcoded literal
token list**. It holds for B20 and C20 and is false for C21, which contains only `v1.1`, because CALL 1 was
amended once and untouched at v1.2/v1.3/v1.4. Satisfying the assertion literally would have required
inventing version tokens for amendments CALL 1 never received: **fabricated provenance, inside the gate
guarding against fabricated provenance.** Replaced with a derived per-cell invariant — capture each cell's
`v1.\d` set before editing, assert post = pre ∪ {v1.5}, compare against no literal. Applied and verified:
B20 and C20 {v1.1–v1.4}→+v1.5, C21 {v1.1}→{v1.1, v1.5}. Root cause is an assertion written as a literal
where it should have been derived from the artifact — the same shape as the retracted "0/N report a
version" claim, which was a hardcoded constant in code; this was a hardcoded constant in a gate spec.
Third instance of that shape in this project.

**Three for three: both defects were caught by the applying agent reporting a mismatch, neither by a gate.**
On 2026-08-13 the C20 substitution rule was applied verbatim and the agent flagged **where the rule
landed**, and the false "narrowed v1.4 2026-08-12" stamp was caught from that flag. Today the agent
**stopped before applying** and reported the C21 mismatch rather than adapting to it — the better of the
two responses, since detection preceded the write. In both cases every gate item was green or would have
been: Labels byte-identical, DVs, freeze, CALL count, version strings, derived §7 list. The gates verify
that specified edits landed; they cannot verify that the specification was right. What has actually caught
both defects is **apply-verbatim-and-report-where-it-landed, plus stop-on-mismatch-rather-than-adapt** —
cheaper than a gate and catching a class gates structurally cannot. Worth treating as the primary control
rather than a courtesy. Three for three as of this entry — the third instance was a row index in this
entry's own open-item note, inferred from a list position rather than read from the sheet, and caught by
the same control it describes.

**Contamination arithmetic computed from the sheet, and it decides the framing.** CALL 10's axes were
derived with seven papers' committed labels in view, so any stanza built on it is prompt-fitted on them.
Against the 13 flagged `co-adjudicated`, the sets overlap on four (agtzidis_2020, chen_2015, ciric_2017,
poldrack_2015): contaminated union **16 of 19**, leaving **3** clean on both axes — liu_2005, tang_2025,
wheaton_2004 — and effectively **2**, since tang_2025's arm and value/quote reconciliation were adjudicated
in the session that produced the call. Two papers is not a figure. **No stratification of this corpus
yields an uncontaminated accuracy estimate**, so the `method` figure is **diagnostic, not evaluative**: it
establishes which error classes exist and roughly where, and does not measure extractor quality. Recorded
inside the protocol rather than deferred to the write-up. Consistent with how both prior arcs actually paid
off — base_pipeline's decomposition mattered more than 82.4%, target_space's more than 11/17.

**Pre-registration committed before the run (`ccf8a35`).** `described_only` reachability is the step-2
gate: four papers hold that state (derosa, liu_2013, power_2014, binder_1999) and the extractor must emit
`verbatim` with `resolved=None` for an unnamed operation rather than collapsing to `MISSING_FROM_PAPER`,
which would make four papers structurally unscoreable in the way binder's `native_volume` was — and would
surface **after** the state-map committed, the worst time. Probe: `motion_correction.method` only, six
papers with agtzidis as positive control and poldrack as APPLY control, **K=10** per `variance.md` and the
temporal finding's fixed→fixed 4/10 → 0/10, recording `verbatim`/`resolved`/`resolution`/span per draw.
derosa's readings pre-declared **four** ways, not three — `FSL` (binding violation), `ICA-AROMA` (CALL 4),
**six-motion-regressors §2.4.3 or mean-FD §2.4.9 (CONSUME leak, CALL 10 Axis 2)**, or the target. The
fourth is live precisely because the label's Notes record that realignment demonstrably occurred and only
its downstream use is stated, so motion-parameter text is the only tool-adjacent text available to the
model. Inferential asymmetry stated: one `verbatim=None` draw demonstrates unreachability, forty clean
draws are evidence for reachability and not proof. **The probe cannot validate CALL 10** — readings 1–3 are
extraction errors to record, not evidence against the call. All six probe papers are already inside the
contaminated union, so iterating stanza wording on probe results adds no new contamination; that licence
explicitly does not extend to liu_2005, tang_2025 or wheaton_2004, the only cells a held-out reading could
ever touch. Also pre-registered: a `span_role` column {estimate, apply, consume, host, out_of_scope}, with
a cell correct only when state, value **and** span_role match. ciric justifies it — MCFLIRT named three
times, once ESTIMATE and twice CONSUME, so a value-only scorer marks it correct while the extractor picked
the wrong mention. Both prior maps were value-only (`target_space_scoring_map.csv`: `resolved, resolution,
label_state, rationale`). The map's rationale must state that this makes the motion figure **stricter than
either prior field's and not comparable to 82.4% or 11/17** — a lower number is a harder rule before it is
a worse extractor.

**Open, found while computing the contamination arithmetic: the Labels sheet has a 20th populated column-A
row.** Row 21 is empty; row 22 is the green instructional footer ("GREEN = fill these in. Label from the
FULL paper …"), outside the DV ranges (`B2:B20`) but inside the used range (`max_row 22`). Any scorer
keying on "non-empty column A" reads **N=20** and scores a sentence fragment as a paper. Not fixed. The
scorer must iterate the 19 known paper_ids or stop at row 20, and hard-fail if the count is not 19.

**Step 1 of the motion arc closes here** — the multi-stream gap (CALL 9), the realignment-vs-nuisance
boundary made operational (CALL 10), and derosa's binding resolution, all pre-registered before any
extraction exists. Order from here: probe → interpret against the four pre-declared readings → `span_role`
into the map design → state-map pre-registered → stanza written against the committed protocol → K-draw
variance → and only then a number, decomposition first. The attestation table (bullets 2–7 across 19
papers, ~10 of 114 cells reported, bullet 7 at 0/19) depends on none of this and remains the Goal-2
deliverable.

Commits: b567e99 (protocol v1.5 — CALL 1 binding clarification + CALL 10) · ccf8a35 (pre-registration —
reachability probe + span_role) · ade9608 (Glossary v1.5 sync — CALL 1 clarification appended, CALL 10 row
inserted, per-cell version-token invariant held). This DEVLOG entry committed separately, last.

## 2026-08-18

Hours: 21:27 - 22:14 ET

**Attestation finding committed (`227e690`) — the Goal-2 deliverable, and it needs no extractor.**
`docs/findings/motion-attestation-table.md`: COBIDAS D.3 bullets 2–7 across the 19 papers, read from the
Labels sheet at v1.5 (`ade9608`). **9 of 114 cells `reported`, 64 `not_reported`, 41 `deferred`**; bullet 7
(`slice_to_volume`) is **0 of 19**; `not_applicable` never assigned; every one of the 9 `reported` cells
carries a verbatim quote, zero exceptions. Reporting is concentrated, not thin-but-even — the 9 cells fall
in 7 papers, 12 papers report nothing across 2–7, and no paper exceeds 2 of 6. The author's unexpected
result is **#4: deferral is wholesale.** Of the 7 papers whose *method* is `deferred`, 6 defer all six of
bullets 2–7 (braun, chen, oconnor, vanderwal, viduarre, weber) — 36 of the 41 deferred cells; exactly one
paper mixes (poldrack, 4 deferred / 2 reported), and the last deferred cell is cole's single one. That
gives CALL 7 (per-row deferral) an empirical justification it lacked: **it changes the answer for one paper
in nineteen** — poldrack's 2 reported cells, which a blanket rule would have swallowed, i.e. a fifth of the
headline number. CALL 6 (blanket deferral covers every bullet) is the common case the same data vindicates
in the other direction (the 36 cells). Labels are human-ratified, not extractor output, so this clears the
standing bar that unscored extractor output is never a literature finding; it stands whether or not the
method arc completes.

**Pre-commit review — three checks I ran because the author couldn't, three fixes.** (1) The doc pointed the
bullet-numbering + D.3 mapping at protocol **§2**; §2 is only the method-vs-attestation scope split — both
the seven-bullet enumeration and the "Mapping to spec fields" table are in **§1**. Repointed §2 → §1 (the
author also folded in a note that the doc's field names are the workbook column stems, cross-referenced by
bullet number). (2) Caveat 1 was **flattening §7**: it said the attestation table "does not escape" the
co-adjudication caveat, dropping §7's own finding that the table is "far less exposed" than the method
figure because attestation is a presence/absence read with little adjudication room. Restored the asymmetry.
(3) The no-CI decision was justified on its own terms but silently departed from base_pipeline's Wilson
[59, 94]; I proposed naming the departure, the author **sharpened it past my version** — the two figures are
different kinds of quantity: base_pipeline's 82.4% is an accuracy *rate* over repeatable trials, where an
interval describes extractor-behaviour uncertainty; this 9/114 is a **census**, a complete count with
nothing sampled and therefore no sampling error to describe. The departure is principled, and
base_pipeline's interval is not impugned by it.

**The gating check the author named: the two §7 quotes must match the source.** Caveat 1 now quotes §7 —
"far less exposed" and "largely independent of this limitation." Verified both against §7 at HEAD before the
commit: verbatim match. This is the quote-drift defect class the project keeps catching; here it was
pre-verified rather than caught after the fact, so it is not a fourth instance. (My first automated pass
flagged the second quote as a mismatch — a line-wrap in the matcher, not the text; re-checked wrap-tolerant,
clean.)

**Docs-only, one path, pushed.** No other file moved — the finding carries its own reasoning, so no protocol
or workbook change rode along.

**Open, parked to rule fresh:** `value_kind` on `FieldExtractionResult` — whether `described_only` gets a
discriminator so the state-map keys on it mechanically, versus the scorer re-applying CALL 1's binding test
to a free string. The author's read is the discriminator; left unruled deliberately, since the reachability
probe's pass condition, derosa's four pre-declared readings, and the state-map all wait on it.

Commits: 227e690 (finding — COBIDAS D.3 attestation, 9/114 reported, bullet 7 at 0/19, deferral wholesale in
6 of 7 deferring papers). This DEVLOG entry committed separately, last.

## 2026-08-19

Hours: 17:43 - 22:15 ET

*(Entry written retroactively on 2026-08-26 from the commits and the design session; the hours are the
work, not the writing.)*

**`value_kind` ruled: option (b) — the discrimination lives in the scoring map, not the LLM schema.** The
blocker was that `FieldExtractionResult`'s three statuses cannot separate two label states: `extracted`
requires both `value` and `verbatim_quote`, `missing` forbids both, so `described_only` and `named_tool`
are the *same* status, differing only in whether `value` holds an operation phrase or a tool name. Options
considered and declined: **(a)** a fourth status — blocked, `provenance.py` is FROZEN with three arms;
**(c)** a model-emitted `value_kind` — viable and additive, declined for now rather than change the LLM
output contract before the stanza exists; **(d)** keying on `SpecifiedTerm.resolved` — ruled out by that
type's own docstring, which records that `unrecognized` does not decide the grade (gordon "EPI template"
and power "atlas space" are both `unrecognized` and grade differently), and because a real tool missing
from the resolver vocabulary would resolve to `None` and read as `described_only`, the false-missing class
`SpecifiedTerm` exists to prevent. (b) has working precedent: `target_space_scoring_map.csv` already
discriminates two label states from one resolver verdict via a gesture heuristic on `verbatim`.

**Prereg amendment 1 (44f285f), append-only, v1 byte-identical (v1 was 38 lines; the file is now 162).**
Supplies the pass condition v1 left underdetermined. Six-row state map; `undecided` as a third heuristic
outcome that **halts** rather than defaulting, because defaulting toward either side silently biases and
destroys the only signal that would justify revisiting (c) — the `undecided` count *is* the measure of whether
(b) was adequate. A `value` matching both vocabularies (e.g. "motion correction via ICA-AROMA") halts rather
than resolving by precedence. `deferred` + `target_kind="supplement"` maps to **`unread`**, not `deferred`,
per CALL 9 — the extractor predates that call and its behaviour is correct (`extractor.py:602`, `:726` narrow
"supplement" → "paper" for the frozen `Deferral` while retaining the original in `DeferralRecord`); only the
label mapping diverged, so under (b) this is a map rule and not a code change. Correctness now requires
**state + value + `span_role == estimate`**, which makes the motion figure stricter than either prior field's
and not comparable to 82.4% or 11/17. `stated_not_performed` is recorded as **unreachable but unexercised** (0
of 19) — a known vocabulary gap, invalidating the map for that cell if a future corpus hits it. binder_1999 is
pre-declared as an expected `undecided`: its quote describes an algorithm in prose ("an iterative procedure
that minimizes variance in voxel intensity differences") and no closed vocabulary recognises that. The
heuristic vocabulary is enumerated before the run and may not be extended after seeing output; it was seeded
from the four `described_only` papers, all already inside the contaminated union, so it adds no new
contamination. derosa's four v1 readings are now evaluable: readings 1 and 2 both land `named_tool` and are
separated only by `value`; readings 3 and 4 both land `described_only` and are separated only by `span_role` —
neither distinction existed under v1.

**Validator guidance narrowed (37b21dd).** `status="extracted"`'s error text told the model to use
`missing` "if the field is stated but the exact sentence is unclear" — which invites bailing on
*uncertainty about field membership* rather than on *absence of a quotable sentence*. Now states that
`missing` applies only when no quotable sentence exists. One string literal; three statuses, all field
definitions and every other validator branch unchanged; ruff, mypy and the test suite pass. Lands before
the probe so the probe tests the corrected wording.

**Withdrawn: the `target_kind` round-trip "defect".** I reported that `FieldExtractionResult.target_kind`'s
`"supplement"` member could not map into the frozen `provenance.Deferral`. It maps fine, deliberately, at
two commented sites in `extractor.py`. I asserted it from reading `extraction_result.py` alone — **fourth
instance of assert-from-a-partial-view**, this time while instructing the author to verify. The second
reported defect (the validator message) survived but was substantially downgraded, from "inverted" to a
wording sharpening, once the `spans: min_length=1` grounding requirement made clear the forced choice is
real.

**Process cost, recorded as a cost.** Five flag-then-resolve cycles this arc — the C20 substitution rule,
the hardcoded gate-item-6 token list, the row-21/22 index, the withdrawn `target_kind` defect, the
downgraded validator message — four of them originating with me. Three were genuine and improved the
artifact; two were false alarms that cost design rounds. The honest metric is that **zero defects reached a
commit**, so the control works, but its false-positive rate is real and is paid in rounds rather than in
corrupted history. Three of the five came from reading one file and asserting about a system. Corrective,
adopted going forward: **no defect is reported until its handling site has been searched** — a single grep
of `extractor.py` would have killed the `target_kind` claim before it was written, at a cost of thirty
seconds against the round it actually took.

Commits: 44f285f (prereg amendment 1 — state map under ruling (b)) · 37b21dd (extraction_result — validator
guidance narrowed to quotability). Both committed 2026-08-19 and logged here on 2026-08-26; the DEVLOG
entry for that session was drafted but not committed at the time, which is itself the gap this entry
closes.

## 2026-08-26

Hours: 20:10 - 21:45 ET

**Two read-only assessments, and the largest scoping decision of the project: Track A (the COBIDAS
completeness checker) is the November deliverable; Track B (the motion extraction arc) continues off the
critical path.** No code was written today. The decision rests on what the assessments found rather than
on planning.

**Assessment 1 — the output generator is not immature; it is unwired.** `render.to_cobidas_coverage`
(render.py:607) already emits "COBIDAS asks N; the paper reports A, defers B, is silent on C", partitioned
mandatory/optional and assessable/not-assessable, over a real 16-row D.3 registry with `assess_coverage`
(cobidas.py:142). `_ADDRESSING_STATUSES = {EXTRACTED, DEFERRED_TO_CITATION}` only (cobidas.py:120), so an
inferred default never inflates compliance. All four provenance states render distinguishably
(render.py:147-157, 310-323, 490-505), pinned by tests/test_render.py:502-510, and MISSING_FROM_PAPER
renders at better than four-state resolution via the reason partition (render.py:411-435) separating "not
reported in source" from "not assessed by current extractor". **The critical safety property was already
solved deliberately:** `to_cobidas_coverage` takes its denominator from the static registry
(cobidas.py:154), not from `_assemble`'s step list, so a step with no extractor renders as "no fields
assessed by current extractor" and never as absent — pinned by tests/test_cobidas.py:115, with the intent
stated at cobidas.py:16-18. What does not exist is any caller: render.py's only importers are `tests/`;
batch.py never imports it; there is no `[project.scripts]` in either pyproject.toml; demo.py is text-in by
construction. Producing a report today requires hand-loading batch JSON in a REPL.

**Consequence, and the reason this reverses an earlier assumption: extraction coverage does not gate the
deliverable.** 15 of 19 spec steps have no extractor, and that is fine — "not assessed by current
extractor" is a true and useful statement to a reader, and each field Track B later extracts upgrades one
D.3 row from not-assessed to assessed. The extraction backlog is incremental value, not a prerequisite. An
earlier estimate that the tool was gated on the extraction backlog was wrong and is withdrawn.

**Assessment 2 — the volumetric distribution exists; the surface distribution does not exist at any
stage.** Volumetric, committed at docs/ground-truth-protocol-target_space.md:422 and DEVLOG.md:479-480,
503-504: `family_specified 10 / deferred 3 / native_volume 2 / study_specific 2 / canonical 1 / absent 1 =
19`, with a clean 19-row per-paper basis at ground_truth/target_space_labels_v1.csv and per-paper
adjudications at the protocol's Known-adjudications section (:406-423). It exists **only as inline prose**;
no table, CSV, or figure carries it and no committed code tallies it — score_target_space.py's sole Counter
(:159) is over error classes. The surface axis has nothing: no labelling instrument (the xlsx has no
surface sheet or column), no scoring-map rows, no labels, no counts. The protocol ratifies a
**two-distribution** deliverable (:269-276) and only one axis is built. Building the surface axis is a
labelling effort on the scale of the motion arc.

**The poster is reframed around the retraction, because the submitted abstract's headline IS the retracted
claim.** The abstract states "13 of 20 papers (65%) stated a normalization space that could not be resolved
to a canonical specification." docs/ground-truth-protocol-target_space.md:63-68 already records that this
was a single-draw, unscored extractor count conflating three reporting behaviours, and states the arc's
purpose as producing "the number presented in November" — so the correction was foreseen and its
replacement is built. **The correction is a stronger contribution than the original claim**, and squarely
on-theme for the accepted session (K.04.a, Ethical and policy issues; keywords Reproducibility,
Neuroimaging, Open science): an automated compliance auditor produced a number, the number was wrong, and
the reason it was wrong is that it collapsed distinct reporting behaviours into one bucket. Notably **two of
the 19 are `native_volume`** — papers that performed no normalization at all, a complete and correct methods
statement that the original number counted as a compliance failure — and three more were deferrals, where
the information exists in a citation. Only `absent` (1) is a reporting absence. The four-state provenance
model stops being an implementation detail and becomes the thesis, demonstrated on our own headline claim.
The abstract's title ("Bridging the gap between neuroimaging reporting guidelines and machine-readable
methods") promises an instrument connecting a standard to a representation, not an accuracy figure, so the
checker is the more faithful reading of what was submitted.

**Scope decisions.** (i) **Volumetric axis only** on the poster, stating that the surface axis is
labelled-pending rather than presenting one distribution as the whole finding; the joint statement
(:271-275) depends on the surface axis and defers with it. (ii) **No accuracy rate as a poster claim** —
not because it is contaminated (target_space's contamination is light: two non-blind worked examples,
ground_truth/target_space_README.md:108-109, giving blind 11/17 [41,83]), but because it answers a different
question than the poster asks. The poster's claim is about the literature's reporting completeness; an
extractor-accuracy rate is a claim about the tool. More pointedly, a poster arguing that a distribution over
reporting behaviours is the right output undercuts itself by leading with a rate. The rate's instability is
the useful part and belongs in the nondeterminism panel instead: v040_frozen gives 11/17, the 0.5.0
re-extraction 10/17, moved entirely by braun on model non-stationarity. (iii) **Pre-generated reports, not
a live demonstration** — a live run needs venue network, credentials, per-run cost, 30-90s latency, and
robustness to arbitrary PDFs (scanned, no text layer,
methods-finder misses), which is a separate and larger problem given the pypdf mangling already documented
in docs/findings/pdf-glue-false-missing.md. (iv) **Generate one paper's report twice, ahead of time, and
show both if they differ** — same input, two runs, two outputs is the documented temp-0 nondeterminism, and
it makes the case for reporting a distribution rather than a rate better than a sentence does. braun is the
candidate, being the case that flipped the accuracy rate between vintages. If the two runs come back
identical that is also worth knowing, as free evidence about attestation stability. (v) **No rendering or
figures until all computation is committed** — compute first, render once.

**Three traps recorded so they do not bite in October.** (1) The published volumetric distribution comes
from `target_space_labels_v1.csv` (19 rows), **never** from `target_space_labels_v1.xlsx`, whose 21 rows
include two `(EXAMPLE)` duplicates of oconnor and mueller that inflate `canonical` to 2 and
`study_specific` to 3; stripped at derive_target_space_csv.py:56-58. (2) **The "~7" does not exist.** Four
numbers attach to "MNI family" across the record — 7, 9, 10, 12 — counted at different stages (pre-label
audit, full-text enumeration, extractor grade, final label). Only the final label count of **10** has an
exact per-paper list (protocol :413-414). Cite 10; never cite 7. (3) **The accuracy figure has two
vintages**: v040_frozen gives blind 11/17, the 0.5.0 re-extraction gives 10/17, moved entirely by braun on
model non-stationarity (docs/findings/target_space-0.5.0-reextraction-prereg.md:141-145). Any quoted rate
must name its prediction vintage on its face.

**Track A scope committed** as docs/TRACK_A_SCOPE.md. Must-do, in order: **A2** make the
coverage-section guard structural — the property is currently held by one line (render.py:602), while
to_text (:350) and to_bullets (:379) iterate present steps only, and A1 creates the first non-test caller;
**A1** wire render into batch.py, which already holds a live Preprocessing (:213) and already writes
per-paper files (:279); **A3** fix the Software header/body disagreement (render.py:638-642 gates the
suffix on `mand_not_reported` while :667 gates the body on `software.addressed`, so they contradict each
other when base_pipeline is missing — verified divergent at HEAD, and which reading is correct is an
author's semantic call, not a fix); **A4** a PDF→report entry point. Should-do: **A5** a corpus-level
COBIDAS table, and two hardening items — a label-state tally in score_target_space.py and a file write in
that scorer, which is stdout-only (:1) so every published rate was hand-transcribed with nothing checking
the prose against a rerun. Deferred with reasons in the doc: rendering and figures, K-draw uncertainty
machinery (shared with Track B's pre-registered variance step — build once, for both), the sub-fields
dropped in rendering, the surface distribution, arbitrary-PDF robustness, the motion arc, and the three
stale-token defects in the instrument.

**Three of my own claims withdrawn this session.** I had carried `citation_resolver.py` as unbuilt; it exists
(9,463 bytes) and is wired into the extract path at batch.py:264, 276 and extractor.py:1127-1145, though it
has zero call sites in render.py. And "output generator maturity unassessed" undersold render.py at 31,663
bytes, the second-largest module in the extractor. Both were carried forward from summaries rather than
read — the same partial-view pattern the log has been accumulating, here costing a wrong strategic estimate
rather than a wrong defect report. Also: I stated the spec defines 20 preprocessing step classes.
`PreprocStep` (preprocessing.py:1233-1254) enumerates 19; the sentence was internally inconsistent, since 15
unextracted requires a denominator of 19 and I wrote 20. Caught by the applying agent, who also declined to
unilaterally edit the same sentence in the build contract — correctly, since a build scope and a log
disagreeing is worse than either being wrong alone.

**Open, unchanged.** The two 2026-08-19 commits and their DEVLOG entry precede this one. Track B: the
reachability probe is pre-registered (ccf8a35 + 44f285f) and unrun. Track A begins at A2.

Commits: e05c30d (Track A build scope). This DEVLOG entry committed separately, last.

## 2026-08-27

Hours: 20:38 - 22:00 ET

*(Entry written 2026-08-30 from the session record and the staged diff; the hours are the work.)*

*(The A2 work was staged Thursday 2026-08-27 and committed Sunday 2026-08-30; the hours are the work,
not the commit.)*

**Track A opened at A2 — the coverage-section guard — and the assessment found a second defect the item
was not scoped to fix.** The briefed risk was omission: `to_field_table` and `to_field_bullets` iterate
present steps only (render.py:350, :379), so a step with no extractor vanishes, and only render.py:602
staples the catalog section onto `to_protocol`. Real, and A2 addresses it. But `_fmt_field_text`'s MISSING
branch (render.py:317-318) returns `"not reported"` **consulting no reason at all**, while `to_protocol`
routes the same rows through `_REASON_LINE` (render.py:422-435) and says `"not assessed by current
extractor"`. On a real `_assemble` output that is **19 of 27 field rows asserting something false about the
author's manuscript** for fields the extractor never targeted, and the two surfaces contradict each other
about the same object. A coverage section fixes none of the 19. Omission and mislabelling are separate
defects; the second is filed as **D**, a sibling of A3, and deliberately not folded into A2 — a behaviour
change inside a structural guard is how one change becomes two under one review.

**Ruled: Option A, plus the surface-parametrized test; D characterises rather than declines.** Option A
(one sanctioned report surface, partials renamed to what they are) was chosen because the mistake is
*available* today for a documentable reason: render.py:13 and :327 both call `to_text` a "human report",
while the module docstring (render.py:3, "One flattener, three thin formatters") omits `to_protocol` and
`to_cobidas_coverage` entirely — a reader orienting from the top of the file learns the wrong thing.
Correcting the docs deletes the invitation. **Option B declined**: a required `coverage:` keyword costs the
same eight call sites, and `coverage=True` on a field view would wrap a coverage section around 19 false
statements — a guard that makes a wrong output look endorsed is worse than none. **Option C (a `Report`
return type) deferred, not rejected**: it is the only option with real enforcement and the natural
escalation if a second non-test caller appears after `batch.py`, but ~14 test assertions to guard one
caller before A1 exists is building ahead of need. Recorded in TRACK_A_SCOPE.md so it is not rediscovered.
For **D**, the ruling is *characterise, not decline*: route the MISSING branch through the existing
`_REASON_LINE` table. Omitting untargeted rows was considered and rejected — dropping them is silent
omission, the exact harm A2 prevents, relocated. Characterising costs nothing and buys accuracy, and it is
the same hallucination-versus-absence cut the project rests on, applied one surface down: `"not reported in
source"` versus `"not assessed by current extractor"` is `MISSING_FROM_PAPER` versus untargeted, made
visible. Having the reason table exist and not routing the partial views through it was an inconsistency,
not a design choice.

**A2 staged, with rendering proved byte-identical to HEAD rather than inferred from a green suite.**
render.py at HEAD was imported alongside the working-tree module and the same `_assemble` object rendered
through both: all six surfaces identical, including `to_report == HEAD to_protocol`. That is the direct
evidence for the no-behaviour-change constraint; a passing suite would only have been consistent with it.
`git diff --stat` on `cobidas.py` and `test_cobidas.py` is empty, so the :154 static-registry denominator
and the test_cobidas.py:115 pin — the property being protected — are untouched, and the A3 region
(render.py:638-642 / :667) appears zero times in the diff. Contents: module docstring rewritten into
REPORT / PARTIAL / structural sections; `to_report` added as the single sanctioned report surface, with
`to_protocol` retained as the implementation it delegates to (an alias-rename would have moved ~14 pinning
assertions and broken the behaviour-free constraint); `to_text` → `to_field_table` and `to_bullets` →
`to_field_bullets`, both docstrings now stating plainly that they are not completeness reports and omit D.3
rows for which the extractor produces no field rows; `REPORT_SURFACES = (to_report, to_protocol)` declared,
with the residual hole recorded in a comment — a surface not listed there is not sanctioned, and no
registry-based guard closes that. `to_protocol` was initially excluded on the grounds that `to_report`
reaches it; that was backwards, since it makes the guard depend on delegation continuing to hold, and
`to_protocol` is public, documented as a report, and holds every current caller. Listed in its own right,
so the parametrized test runs twice. Two internal comments the assessment had missed (render.py:71, :81)
were caught and updated. Three tests replace `test_to_protocol_includes_cobidas_section`, which asserted a
string in `to_protocol`'s output and would have passed while a new caller bypassed `to_protocol` entirely:
a surface-parametrized test keyed on the output and the registry rather than the call graph (header
present, `Mandatory rows: N` reconciled against the registry, assessed + not-assessed == N so a
catalog→present-steps switch fails, and "Motion correction" named); a negative counterpart asserting a
field view is *not* a report, which stops the obvious wrong move of bolting coverage onto the partials once
the rename lands; and a cross-surface consistency test marked **`xfail(strict=True)`** naming D. Strict was
the applying agent's improvement on the specification — a non-strict marker would let D's fix pass silently
and leave a stale marker behind, where strict makes the flip deliberate and fails if D is ever reverted.
One assertion the assessment correctly refused: "every mandatory aspect string appears in the report" would
fail on a well-reporting paper, because addressed rows are named in no section of `to_cobidas_coverage`
(render.py:688, :701) and only the header counts the full 14. Suite: 277 passed / 2 skipped / 1 xfailed;
ruff, ruff-format and mypy clean on both packages.

**Three diagnostics, and the finding was the opposite of the report.** I was told a `Co-Authored-By`
trailer had landed on two commits and asked how to handle it. **It never landed** —
`.local/hooks/commit-msg`, a gitignored one-line `sed`, had stripped it at commit time; the commits were
always clean. The applying agent had verified what it *sent* rather than what landed, which is a permanent
property of that hook rather than a slip: a `commit-msg` hook rewrites the message after handoff, so
anything read back from one's own input is stale by construction, and the same reasoning applies to
`pre-commit` reformatting files after staging. **The real finding is one layer up:** `~/.claude/settings.json`
had **no attribution key at all** — the setting was absent, not disabled, contrary to what I had recorded —
so for an unknown span of commits a gitignored one-line `sed` with no output on success was the *only*
thing keeping trailers out of the log. Single point of failure, invisible to anyone cloning the repo since
`.local/` is untracked. Closed at the source by adding `attribution: {commit: "", pr: ""}`; `pr` as well as
`commit`, since sole author-of-record is a convention about the record and not about one git verb. **Also
corrected: the convention is not "zero trailers in history."** `b6972ef` (2026-08-07) carries one,
predating the current setup; retained rather than rewritten, since it is pushed and DEVLOG footers cite
hashes. My argument for not rebasing had rested on the premise being unbroken — it was not, and the
conclusion survives on the better ground that rewriting published history to fix a provenance annotation
corrupts provenance records. An accurately-described exception is stronger than a premise that fails when
someone checks.

**Off-hours guard pinned; a stale interpreter had been running it.** `.local/hooks/pre-commit` and
`pre-push` both called bare `python3`, which resolved to an unrelated project's venv leaked in through
`VIRTUAL_ENV` — first on `PATH`, inherited by every subshell, and the cause of an unexplained import
failure earlier in the arc. The guard enforcing the IP-clearance commit window therefore depended on
another project's directory continuing to exist. Both hooks now call `"$ROOT/.venv/bin/python"`, verified
in three directions (passes now, still blocks at a simulated Wed 14:00 ET, override honoured).
`.venv/bin/python` **fails closed** on a fresh clone before `uv sync` — the correct failure mode for a
compliance control, which must not silently not-run; `/usr/bin/python3` was declined because it can be a
Command Line Tools stub, trading a legible failure for a confusing one.

**Process tally.** Fifth assert-from-a-partial-view instance, and the second in two days where the partial
view was the agent's own output rather than a file. The rule adopted from it, which generalises further
than the corrective it replaced: **a proposal about state should carry the verification of that state, not
defer it to whoever acts on the proposal.** That is the rule I broke in proposing a remedy for a trailer
neither of us had read back — and it applies to most recommendations in this project, since nearly all of
them rest on a state report I did not produce.

**A dating defect in the two committed entries, and a convention gap behind it.** Settled from git's
authoritative timestamps: `44f285f` and `37b21dd` are Wednesday 2026-08-19 20:35 EDT; `e05c30d` and
`41c2867` are Thursday 2026-08-27 21:02-21:03 EDT. Every date and weekday in both entries is correct, and
the sessions were 23 hours apart rather than spanning midnight. **The defect is elsewhere: both entries'
footers cite commits that did not exist during the session they document.** The 08-26 entry's
`Commits: e05c30d` names a commit made Thursday, 23 hours after that Wednesday session ended at 21:45; the
08-19 entry's footer says "logged here on 2026-08-26" while `41c2867`, the commit carrying it, is Thursday
the 27th. Neither is rewritten — they are pushed, DEVLOG footers cite hashes, and a later entry correcting
earlier ones is how this log has handled every other error. **The convention itself is the gap:** "DEVLOG
last with real hashes" silently implies same-session commits and produces this anachronism whenever a
session's work lands on a later day, which is the normal case here. **Adopted: the `Commits:` footer states
the commit date whenever it differs from the entry date.** Applied in this entry's own footer. Also noted:
`docs/TRACK_A_SCOPE.md:3` reads "Scoped 2026-08-26", which is accurate — the decision was Wednesday even
though the file landed Thursday.

**Open.** D is staged-adjacent but unrun; the `xfail(strict=True)` in the suite encodes the defect it will
fix, so nothing is lost by pushing A2 alone. Then A3 (the Software header/body disagreement, which carries
a semantic ruling on whether an unassessable Software row is a violation or an unknown), then A1. Also
open: `docs/TRACK_A_SCOPE.md:22-23` and `DEVLOG.md:1134` still name `to_text`/`to_bullets`; the DEVLOG line
is a historical record and stays, but the scope doc is a live build contract and should be updated — in a
docs pass, not under a code commit, so it stays clear which moved first. And the reason-string wording
review deferred into D: `"not assessed by current extractor"` reads as an admission where the useful
reading is *this row is unexamined, read the paper yourself*, and whether `"unclassified"` can reach a user
at all is unestablished.

Commits: d90507b (render — to_report as the only report surface; field views renamed and documented as
partial; coverage section pinned by a surface-parametrized test), committed 2026-08-30. This DEVLOG entry
committed separately, last, on 2026-09-01.

## 2026-09-07

Hours: to 19:40 ET. The start is not recorded; the earliest evidence is a `.git` mtime of
12:48.

**A1's acceptance run, and a gate that could not fail in the direction that mattered.** The
batch had never been run since `214b55c` added the per-paper report. Confirmed two ways before
spending anything: no `papers/*.md` anywhere in the tree, and no `render_error` column in any
on-disk `summary.csv` while `batch.py:65` defines one. The run
(`extractor_mvp/configs/batch_a1_acceptance_config.yaml`, 19 papers, model and paper list
identical to the v050 draws) wrote 19 `.md` and 19 `.json`, `render_error` empty on all 19 rows,
and 19 of 19 papers matched a partition derived from this run's own JSONs.

The acceptance test as I first specified it could not fail on the failure mode it existed to
catch. Both A3 criteria were `grep -c ... == 0`, so a regression suppressing the violation
section for *every* paper would have passed both, because the fix's whole content is conditional
suppression. The repair was the complement: assert the full partition, with the five
`MISSING_FROM_PAPER` papers as a negative control. All five emitted the section, and that is
what makes braun's and viduarre's absence readable as conditional rather than global. The two
greps are one signal and were reported as one: `render.py:753` and `:793` evaluate the same
predicate and fall silent together.

Defect D passed on all 19, with `not examined by the extractor` appearing 19 times per report
and `: not reported$` zero times corpus-wide. `liu_2005` came back `methods_not_found` with
`fallback_full_text`, and its report carries the slice warning, which incidentally proves
`214b55c`'s stated reason for rendering inside `_process_paper` where the `MethodsSlice` is
live.

**The verification corrective, second half.** The rule adopted on 08-27 was that a proposal
about state carries the verification of that state. It needs its other half stated: **a
verification that contradicts the belief it was testing halts the work.** Either the check is
wrong or the belief is, and both need resolving before the next action.

The instance: moving 22 batch configs, the agent ran a check for relative paths, got 22 of 22
immediately after asserting all paths were absolute, and proceeded into the move anyway. The
regex was wrong. But one config, `config_diag.yaml`, genuinely did have a relative `output_dir`,
and after the move it would have written run output into the tracked `configs/` tree. A 22-of-22
result should have been implausible on its face given the assertion it contradicted. The move
happened to be safe; that was luck, not method.

The asymmetry is the finding. Three of the agent's errors this session are instances: a title
line cited as `render.py:626` when it is 629, a pointer in `TRACK_A_SCOPE.md` to a `_tally`
item in a findings doc that does not contain one, and the 22/22 case. The first two were caught
by verification at the point of assertion and never reached a commit. The third was not caught,
because the contradicting result did not stop anything. Verification catches errors where it is
run; the rule has to say what a contradiction obliges.

**Sixth and seventh assert-from-a-partial-view instances**, both the agent's, both its own prior
output rather than a file, both caught before landing.

**Four predicate-from-consumer errors, three mine and one the agent's, against the same
function.** The split matters. Two parties independently making the same error against
`_software_coverage` is evidence about the code, not about either party.

- Mine: predicted the section partition from `render.py:793` alone, without reading
  `_software_coverage`. The predicted membership was exactly inverted, 5 present / 14 absent
  against the true 14 / 5, while the counts coincided.
- Mine: asserted the two A3 greps were independent confirmations.
- Mine: predicted `test_render.py`'s exact counts as the recoupling friction, reasoning from the
  string asserted rather than the fixture feeding it. Chen is `EXTRACTED`, routes to B3b, and
  the count cannot move.
- The agent's: reported the `INFERRED_DEFAULT` path as an A3-class defect after searching only
  its consumers. `rg 'inference=InferredDefault'` settles it in one command: nothing in the
  extraction path writes that arm, so the branch is a reader-side path with no producer.

`_software_coverage` is four branches behind a 33-line docstring, consumed at `render.py:793` by
a two-clause condition that reveals none of it. Anyone reasoning from the call site gets it
wrong. `0604877` §5 is the argued response: the full seven-branch table written down, with each
branch's source line and reachability.

The corrective generalises the 08-27 one from state to structure: **a claim about a predicate is
verified at its definition, and a defect is not reported until both its producer and its
consumer have been read.** The agent's `INFERRED_DEFAULT` report had a reader and no writer; the
superseded `test_software_addressed_iff_version_extracted`, named and explained at
`test_cobidas.py:112-116`, pinned a state `flatten()` cannot produce. Same shape, opposite ends.

**Collapsed buckets: three instances, and the third was introduced by a correct fix for the
second.** This is the finding, and it is not a repair narrative.

1. The retracted SfN abstract claim, `13/20 (65%) could not be resolved to a canonical space`,
   one bucket spanning distinct reporting behaviours. Ruled diagnostic rather than evaluative.
2. A3: the Software header and body disagreed because coverage keyed off the version row alone,
   so a citing paper was accused of an unconditional violation. `c9c2951` fixed it.
3. `addressed` spanning two questions, *did the paper say anything about software* and *did it
   give version and revision number*. `c9c2951` created this one by making the row addressed
   for a deferring paper.

Instance 3 was found this session, not shipped and detected later like the first two, and it is
**not fixed**. The ruling is ratified and recorded in `0604877`; no code implements it. A3's
diagnosis stands and only its repair is superseded, which is the honest reading: the false part
was the accusation wording, not the finding.

**Two surfaces for one fact: four instances, the same finding seen from the output side.** The
collapsed-bucket pattern is one predicate carrying two questions; this is two emitters
disagreeing about one fact. They are two faces of the same defect class.

- `addressed` versus what the Software row's mandatory content asks (`cobidas.py:13-14`).
- `n_deferred` reads 0 corpus-wide while two papers defer their base pipeline. `_tally`
  iterates `preprocessing.steps` only (`batch.py:111`), and `base_pipeline` and `steps` are
  sibling fields on `Preprocessing` (`preprocessing.py:1306-1307`), so it is structurally
  invisible to the tally, while its docstring says it buckets the targeted
  fields and `cobidas.py:161-162` says `base_pipeline` is always targeted. Classified as a code
  defect, deferred behind A5's design, which must first settle whether the fix widens `_tally`
  or narrows the docstring and has A5 read the JSONs.
- Three emitted strings carry "the extractor did not examine this row"
  (`render.py:476`, `:769`, `:784`), and a fourth wording survives only as a comment at `:782`.
- The console rollup says `19 successful, 0 failed` while `summary.csv` says 18 `success` plus
  one `methods_not_found`, because `batch.py:382` buckets the two together.

The `summary.csv` and report denominators disagree on all 19 papers. Derived from this run's
reports, which are not tracked: the CSV sums 7 targeted step fields every time, while the report
assesses 7, 8, or 9 depending on whether a version row exists. Where the totals coincide,
agtzidis and liu_2005, they coincide over different membership.

**The 0/19 version claim is retracted, and its stated mechanism no longer describes the code.**
COBIDAS §4.3 p. 10 supplies the criterion: the exact version, with `SPM12` and `FSL 5.0` named
insufficient against `SPM12 revision 6225` and `FSL 5.0.8`. `extractor.py:132-140` implements
that at the prompt. The code does not: `quote_supports_value` is whole-token containment with no
version-shape logic, so a model returning `SPM12` with a supporting quote would be recorded
`EXTRACTED`. Extraction status is a separateness predicate, not a compliance predicate, and
ground-truth labels for this field are to be assigned against §4.3 read directly.

`ground-truth-protocol.md:393-401`'s conclusion stands and its mechanism is stale in all three
clauses: `_build_version_pf` is a real extraction path, the prompt does ask for a version, and
`assess_coverage` reads a value that is no longer a constant. Three papers report separate
versions, named from the papers themselves at `ground-truth-protocol.md:397-398`. That
establishes the claim is false; it does not establish a rate, and the extractor's
`EXTRACTED` set converging on the same three is not independent confirmation.

**Two clean-clone failures the repository recorded nowhere, both now closed.** `hard_drop_audit.py`
and `retry_audit.py` are tracked and read a config that was never tracked, so both raised
`FileNotFoundError` on any fresh clone. And `import extractor_mvp` succeeds under both virtual
environments, resolving under the repository root as a namespace package with `__file__` set to
`None` and without `boto3`, so a batch run there dies at the first model call rather than at
import. The first is closed by `0982b84` and `21a40e7`, the second by `126ecd6`.

**Open.** The ruling is ratified and unimplemented. Next: the re-render script, built
reproduce-then-change so that re-rendering all 19 at HEAD produces 19 byte-identical files
before the predicate changes, since otherwise the two-paper diff is unattributable; then the
`test_cobidas.py` recoupling, which supersedes
`test_deferred_pipeline_is_not_a_software_violation` by name and flips row D of the state test.
`#8` sits behind A5's design. A4 and A5 are otherwise unchanged. No labelling has started for
`base_pipeline.version`, and the per-tool exactness rule is to be fixed before it does.

Commits: 7748e7b (docs — the §4.3 criterion and the 0/19 retraction) · 0982b84 (configs moved
out of the ignored results/ tree) · 21a40e7 (scripts — _V6_CONFIG repointed, load_batch_config
guarded) · ca47171 (config_diag.yaml deleted) · c90ac2d (docs — four report-surface
inconsistencies, Track A status) · 126ecd6 (CONTRIBUTING — the two-interpreter setup) · 0604877
(DELTA — a deferral does not address the Software row). All committed 2026-09-07. This DEVLOG
entry committed separately, last.

## 2026-09-11

Hours: ~21:00 - 01:30 ET, running past midnight; the four commits are stamped 2026-09-12.

**The re-render gate, and a self-test that could not fail.** The DELTA needed a harness that
could say which papers a predicate change alters, and say it attributably. Two designs were on
the table: compare today's render against a stored baseline, or compare two code versions over
one fixed input. The baseline framing collapsed on inspection — both the `.md` outputs and the
`.json` inputs live under the `*`-ignored `results/`, so "verifiable by anyone" was never
available, and a manifest of output hashes cannot separate "the render changed" from "the
inputs changed". The repository had already solved this once: A2 (`d90507b`) imported HEAD's
module alongside the working tree and rendered one object through both (`DEVLOG.md:1204`).
`814a1fc` takes that shape and fixes its hazard — A2's method needs two copies of
`extractor_mvp` importable at once, which is exactly the namespace shadow `126ecd6` documents,
so the gate runs the two renders as separate subprocesses with `PYTHONPATH` selecting a git
worktree. Both editable packages must be overridden or old `render.py` imports new
`fmri_repro`.

The first acceptance criterion I wrote for it was worthless. `--against HEAD` returning 19
identical is also what a silently failed `PYTHONPATH` override returns, because both
subprocesses then run working-tree code. The pass condition was satisfied by the failure it
existed to catch. The fix is the negative control now recorded in the script's own docstring:
`--against d31e8b7` (`c9c2951^`) must return 7 changed, the papers with no
`base_pipeline.version` row.

**A check must be able to fail for the reason it exists.** This is the session's corrective and
it generalises three shapes that had been tracked separately. Five instances, four of them
found here:

1. A3's two acceptance greps, both `grep -c ... == 0`, passed by the global suppression they
   were meant to catch (2026-09-07).
2. The relative-path regex returning 22 of 22 immediately after the opposite had been asserted,
   and the work continuing past it (2026-09-07).
3. A footer-hash verification whose loop emitted a spurious `DOES NOT RESOLVE`, and a second
   attempt whose per-hash column resolved `${h}^^^^{commit}` — the fourth ancestor, not the
   commit. Both the agent's; the decisive check was the sorted set comparison, which held.
4. A `python3` heredoc that failed on quoting so the fix never applied, paired with a `grep`
   written in the same breath that matched the wrong line and reported success. The agent's.
5. An assertion in `test_render.py` excluding the string `"No version reported by the paper."`
   from the deferral line — correct when written, vacuous one commit later once `f44771a`
   retired that string entirely. The agent's, caught before it landed.

The sharper statement, and the one worth carrying: **a check written alongside a change is not
independent of it.** It inherits the change's assumptions in the same breath. Instances 4 and 5
are that specifically; 1, 2 and 3 are the weaker "a check that cannot fail".

**Verify against the checker that will actually run.** `814a1fc` was rejected by the
pre-commit `mypy` hook on a `no-any-return` that a local `mypy` had passed. The hook runs with
`additional_dependencies: []` and therefore cannot see the package, so `to_report` resolves to
`Any`; the local run had it importable and saw a real `str`. Reproduced with
`--no-site-packages` before fixing, rather than guessing. Local green is not hook green. Same
family as `verify-what-landed-not-what-you-sent`, one step earlier in the pipeline.

**Fifth predicate-from-consumer error, mine.** I predicted the negative control would return 2
changed, on the grounds that A3 changed exactly braun and viduarre's Software section. The
section-level claim is right — `braun` goes 1 to 0, `binder` stays 1 to 1 — but `c9c2951` also
moved `covered`, so the Software row shifted from "Not assessed by AESPA" into "Assessed by
AESPA" in the header of all seven no-version-row papers. A section-level prediction against a
byte-level instrument under-counts. The harness returned 7 and was right; the expectation was
wrong. Recorded in the script's docstring so the next reader is not told to expect 2.

**The DELTA implemented, in two commits so each diff attributes.** `d8c97c6` rules the wording
that §8 left open, before any code: one heading retained, because every case is the same
COBIDAS finding and a second heading would imply a deferral carries a different status; four
lines, because Goal 1 is actionable guidance and the action differs. The fourth line is not
polish. **The predicate alone emits the wrong sentence** — `_base_pipeline_name` returns `None`
when no `PipelineRef` resolves, so both deferring papers receive the bare line written for a
paper that named no software at all, which is A3's original complaint in a quieter register.

`59e732b` is the predicate plus the deferral line: 2 reports change, braun_2015 and
viduarre_2017, verified against `d8c97c6`. `f44771a` is the other three lines: 14 change, and
braun and viduarre are not among them. Doing all four at once would have moved 16 of 19 in one
diff and attributed none of them. The expected identical set for the second gate — derosa,
liu_2013, oconnor plus the two settled in the first — was derived before running and met
exactly.

Also ruled: `DEFERRED_TO_CITATION` leaves `_ADDRESSING_STATUSES` untouched. It is read at a
second site for the other 15 rows, where a deferral remains a report per CALL 1, and narrowing
the frozenset would have reversed a ratified protocol call as a side effect of what looks like
a one-line edit.

**The gate paid for itself on something no test asserted.** First render of the deferral line
gave viduarre `deferred to Glasser et al..` — the ref already ends in a period and the line
appended one. No test asserted it, and no reviewer reading a diff would have seen it; a
byte-level comparison did. Pinned by `test_deferred_software_line_does_not_double_the_terminator`,
using viduarre's real ref rather than a hypothetical. The gate's value is not only attribution.

**`#8` is not blocked on A5, and the 2026-09-07 entry says otherwise.** That entry
(`DEVLOG.md:1401`) records the `_tally` denominator defect as "deferred behind A5's design,
which must first settle whether the fix widens `_tally` or narrows the docstring". The design
already settled it, before the question was asked: `docs/TRACK_A_SCOPE.md:126-129` states that
`SUMMARY_COLUMNS` carries no D.3 content and that `RowCoverage` is the right per-paper unit to
aggregate over. Traced at HEAD: `_tally`'s output reaches `summary.csv` (batch.py:273-280) and
`extraction_json["counts"]` (batch.py:253), **nothing reads `["counts"]` back**, and
`assess_coverage` consumes `flatten()` rows and never the tally. A5 therefore cannot inherit
the gap. `#8` is a small independent fix — `_tally`'s docstring claims it buckets the targeted
fields, `base_pipeline` is targeted (cobidas.py:171-172), and it iterates `preprocessing.steps`
only — and it can land any time.

**A documentation defect found by implementing the document.** The DELTA's §7 lists two
superseded test artifacts. There are three: `test_software_violation_surfaces_agree_for_every_base_pipeline_state`
(test_render.py:880) carried a case asserting a deferred pipeline produces no violation. §7 was
written before anyone searched `test_render.py`, so it listed what `test_cobidas.py` held. The
test keeps its name and purpose — header/body agreement is orthogonal to which way the
predicate rules — and only its expected value moved. §7 is left uncorrected here deliberately,
so the fix does not ride inside the wording commit.

Two smaller agent errors worth recording. It recommended A2's import-HEAD-alongside method four
days after writing the `126ecd6` section documenting that exact hazard, which is citing a
precedent without checking whether the precedent's method is safe in the new context. And it
seeded the word "committed" for the `.md` files into a subagent prompt, where it propagated
into that agent's findings until an adversarial pass checked tracking and found `git ls-files`
returns 0 for that directory.

**Open.** A4 is the remaining critical-path item and carries a decision to settle first: live
demonstration versus pre-generated example reports (`docs/TRACK_A_SCOPE.md`), which changes
whether A4 needs polish or merely needs to work. Target 2026-10-31, poster 2026-11-14. A5 is
SHOULD, not MUST. `#8` and the §7 correction are small and independent. No labelling has
started for `base_pipeline.version`.

Commits: 814a1fc (re-render identity gate) · d8c97c6 (design — the Software-row wording ruled)
· 59e732b (predicate — a deferral answers identity, not the version; deferral line) · f44771a
(the other three lines state the action). All committed 2026-09-12. This DEVLOG entry committed
separately, last.

## 2026-09-12

Hours: ~20:15 - 21:45 ET. `2990965` is also in this entry's footer: it landed at 01:30, in the
tail of the 09-11 sitting but after that entry was already committed.

**A4 shipped, and the premise it was scoped on had expired.** A4's "Why" claimed `batch.py` is
PDF-in and never imports `render`. A1 (`214b55c`) had made that false months of reasoning ago in
document time and five days ago in real time: `batch.py:34` imports `to_report`, and
`_process_paper` already ran the whole chain. Re-estimated by building it — **small, not
medium**, about 35 lines of body reusing eight functions untouched through one call. `2990965`
corrects the scope doc; `815ec2f` is the entry point.

`demo.py` is not the host, and the scope doc's reason was weaker than the real one: `demo.py:71`
calls `extract_preprocessing` while `batch.py:30` calls `extract`, so it sits on the older entry
point and was skipped by the migration that moved every other runner. `_process_paper` is
promoted to `process_paper` — one caller, so two lines — and gains the docstring that promoting
it to API required.

**The command was run against a real PDF rather than declared correct.** One paper, one billed
call, through the installed console script rather than the module fallback:

    aespa-report .../Agtzidis_2020.pdf --paper-id agtzidis_2020 --output <path>
    wrote <path>        exit=0        wall=12s

That settles three things at once. A4 works end to end. **Bedrock authorization works** — the
question recorded as untested is now tested, and the profile the record named (`bedrock-extractor`,
`DEVLOG.md:533`) being gone did not matter. And 12 s confirms the 9-15 s band measured from the
corpus run, against the scope doc's 30-90 s, which was wrong by 3-6x and was part of the stated
case for pre-generated reports. The recommendation survives; that reason for it does not.

**The report reproduced byte-identically, and that is an observation, not a stability claim.**
The live extraction five days later rendered identical bytes to a replay of the stored
2026-09-07 JSON. Under temp-0 that is the expected outcome; `docs/findings/variance.md` documents
the nondeterminism, so the finding is that this paper did not hit it, not that the extractor is
stable. One paper, one draw, one confirming direction — the same evidence shape as the three
version strings, which cannot establish a rate either. It is not to be cited as stability.

**`pypdf` was a dev extra, and that was a correctness bug rather than a packaging one.**
`c76d60e`. `load_pdf_text` is on the only PDF-in path, and `pdf_loader.py:22-28` imports pypdf
inside a `try` returning `("", "failed")`. Without the dev extras — which is what an install
plus a console script produces — every PDF fails with `"pypdf returned no text"`, a message
blaming the PDF rather than the install, and `pdf_creation_date` returns `None`, **silently
disabling KB version inference**. That last part is the report saying something different, not
an install failing. `command_survey.py:41` and `doi_date_resolver.py:48` import it unguarded and
would fail at import instead.

**The checker that actually runs has a blind spot, and it is its own corrective.** Moving pypdf staled
`extractor_mvp/uv.lock`. `uv lock --check` reported it; `uv sync --all-extras --frozen`, which is
what CI runs, did not — `--frozen` takes the lockfile as given, so it installs from the stale
lock and stays green. Previous instances of this family were a LOCAL checker being weaker than
the real one; this is the real one being structurally unable to detect the failure. `f1db6c6`
adds a separate `uv lock --check` step to both jobs, separate on purpose because folding
`--check` into the sync would change what CI installs. Verified by mutation rather than
asserted: adding a dependency without relocking makes `--check` fail while `--frozen` still
passes.

The rule this yields is not "verify against the checker that will actually run" — that one
assumes the real checker CAN detect the failure. **A checker that takes its input as given
cannot validate that input.** `--frozen` is defined as trusting the lockfile, so no amount of
running it more carefully would help; the fix has to sit beside it, not inside it. Filed
separately from the 09-11 rule for that reason.

**The ruling to track the demo reports was made on a distinction nobody had measured, and is
void.** `d2864d5`. I ruled that the `.md` are derived summaries while the `.json` carry the
verbatim quotes. Both carry quotes. Measured: `.json` 55 quotes / 1454 words / longest 86;
`.md` 50 quotes / 574 words / longest 17, every fragment capped at 80 characters by
`_SPAN_QUOTE_MAX` (`render.py:118`). The premise was one command from being checked and the
licence question had already been raised. That one is mine — I stated the premise and the agent
acted on it.

Parked rather than resolved, and nothing built is lost: `scripts/rerender_reports.py` regenerates
the reports on demand and the identity gate works on any machine holding the run. If the licence
question is taken up, it should be framed **for the reports** — scholarly quotation of capped
fragments with attribution adjacent, which may resolve across the whole corpus — and not as the
JSON question, which is verbatim sentences and probably splits by publication year over a
1999-2025 corpus.

Recorded in the same commit as a **standing condition rather than a task**: 16 of 19 stored
reports no longer match HEAD's renderer, nothing regenerates them automatically, and anyone
reaching for a demo report before 2026-10-31 gets output the tool no longer produces. The free
replay command is recorded with it, and was run as written before being recorded — a command in
a deferred list is read six weeks later by someone who will not check it.

**`#8` closed by scoping rather than widening** (`a0ba287`), and the widening priced. `_tally`'s
docstring claimed it buckets "the targeted fields"; `base_pipeline` is targeted and is a sibling
of `steps`, so the walk never reaches it. Widening is not a one-liner: 14 of the 31
base-pipeline-family rows in the corpus carry reasons `_tally` does not map — 5
`no_base_pipeline_named`, 6 `version_deferred_to_kb`, 3 version rows with no reason — and would
fall through uncounted. Giving them buckets decides what the summary columns mean and belongs
with A5. So the scope is made explicit, the consequence is stated where it will be read
(**`n_deferred` counts deferred step fields, not papers that defer**), and a test pins the
exclusion, verified by mutation to fire when the walk is widened.

**`§7` of the DELTA listed two superseded artifacts; there were three** (`18b67e1`). The third,
`test_software_violation_surfaces_agree_for_every_base_pipeline_state`, is in `test_render.py`,
and §7 was written before anyone searched that file. It surfaced during implementation as a test
failure rather than as a decision, which is the shape that document exists to prevent.

**Check correctives, continued from 09-11.** The rule there was *a check must be able to fail for
the reason it exists*. Three more this stretch, plus the `--frozen` rule above. Two from the
agent's errors:

- **A claim about what someone else can verify has to name what they hold.** Asserted twice on
  the same footing: first that a hash manifest would make the identity gate verifiable by
  anyone, then that tracking the reports would make it clone-checkable. Both wrong for one
  reason — the inputs are under the same ignore rule as the outputs, so a clone holds neither.
- **A fingerprint must be invariant to everything except what it fingerprints.** The
  baseline-integrity check hashed `stat` output including the path as spelled, so calling it with
  an absolute path instead of a relative one changed the hash with the data untouched. It read as
  the baseline having been written to. Halting was still right: a false positive costs one
  command, a false negative costs the baseline. A content-only hash is the fix.

And a third, from the `.md`-versus-`.json` error above: **a property asserted of one artifact has
to be measured on each artifact it is asserted of.**

**Open.** A5 (SHOULD, not MUST). The demo reports' tracked home and the licence question under
it. Their staleness, standing until someone regenerates. No labelling has started for
`base_pipeline.version`. Target 2026-10-31, poster 2026-11-14.

Commits: 2990965 (A4 re-estimated small; the pypdf blocker recorded) · c76d60e (pypdf to runtime)
· 815ec2f (A4 — the PDF-to-report entry point) · d2864d5 (demo reports deferred; staleness
recorded) · a0ba287 (_tally scoped, widening priced) · 18b67e1 (DELTA §7 — three artifacts, not
two) · f1db6c6 (CI — lockfile currency). All committed 2026-09-12. This DEVLOG entry committed
separately, last.

## 2026-09-12 (late)

Two things after the 09-12 entry, whose own footer says it was committed last. It was not, and
the convention that a `Commits:` footer is written before the sitting ends is what produced that
— worth knowing rather than fixing, since the entry is pushed and a later entry correcting an
earlier one is how this log handles it. It is also an argument about the footer's form: **a
`Commits:` footer should state what it commits, not its position in the sequence.** "Committed
separately, last" is a claim about the future, and the future gets two more commits in it.

**Pushed.** `214b55c..dcc8e8a`, 21 commits across three sittings, and the first push in eleven
days — `git reflog show origin/main` dates the previous one to 2026-09-01 21:57, thirteen seconds
after `214b55c` was committed. Verified against the remote rather than the local ref: `git
ls-remote origin main` returns `dcc8e8a`, matching local HEAD. For those eleven days the §4.3
retraction, the deferral ruling and its implementation, the identity gate and A4 existed only on
this machine. I had said twenty-five commits; it was twenty-one. The count came from
adding up sittings rather than asking git, which is the same shape as every other number in this
log that turned out to need checking.

Worth holding as a fact about the cadence rather than about this stretch. Neither the §4.3
retraction nor the deferral ruling was reconstructible from the conversation alone — both rest on
measurements taken against the tree, and the reasoning that produced them lives in the commits and
the design doc, not in anything recoverable elsewhere. Eleven days of that on one machine reads as
fine until it is not.

Before pushing, two things were checked because the session had just spent hours deciding what
not to publish: that nothing under `results/` was in the push set (only its `.gitignore`, which
is the rule and belongs there), and that no corpus span of 12 or more words appeared in any
changed file. Neither found anything. The `/Users/cwook/` paths in the configs were already
public at `214b55c` in 9 files, so the 313 new occurrences are volume, not disclosure.

**`bcb763c` — the published configs overclaim.** `0982b84` tracked them because "a config is the
input that makes a run reproducible". With an absolute path on every `path:` and `output_dir:`
line they make a run identifiable rather than reproducible, which is the weaker claim, and it is
now public. `load_batch_config` already resolves relative paths against the config file's own
directory (`batch_config.py:48`, `:52`, `:56-58`), so the fix needs no new code. Recorded with
its limit attached so the fix is not followed by a second overclaim: zero PDFs are tracked and
the corpus lives outside the repository, so relative paths buy portability of the config, not of
the run.

**Which corrective is load-bearing, corrected.** The agent's closing read of the session was that
the gate was specified three times, wrong three times, and that each correction came from reading
the definition rather than the call site. That is the visible half and it is the wrong half to
carry forward. Each correction arrived because something FIRED — the negative control, the 7-vs-2
partition, the byte-level diff. Nobody re-read more carefully the second time.

The distinction matters for what gets built. *Read the definition, not the call site* describes
what the fix turned out to be, but it is not a method: under deadline nobody reads more carefully
on request. **Make the check able to fail for the reason it exists** is a thing that can be built,
and it keeps working when attention does not. The 09-11 entry already has the ordering right —
that rule is its headline and predicate-from-consumer sits under it as a diagnosis — but the
ordering was accidental there and is deliberate here.

**A hedge is an assertion, and needs the same verification as the claim it replaces.** Writing
the push paragraph, the agent asserted the previous push date, hedged it to "not recoverable from
here", then checked and found `git reflog show origin/main` had it exactly — 2026-09-01 21:57,
thirteen seconds after `214b55c` was committed. The hedge was not the safe version of the claim; it
was a different claim, about the evidence, and it was false.

This is the fourth corrective and the first that is not about a check. The other three are about
checks that cannot fail. This is a claim that cannot fail: "not recoverable from here" is
unfalsifiable as stated and reads as epistemic caution. The failure mode is **"I don't know" used
to avoid a check rather than to report one** — and it is harder to catch than a bad assertion,
because hedging looks like the careful choice.

**Open, unchanged.** The poster-number hardening is next: `score_target_space.py` counts only
error classes and writes no file, so every published rate was hand-transcribed with nothing
checking it against a rerun, and those numbers reach a board on 2026-11-14. The two traps to
encode as assertions are already recorded — read the 19-row CSV and not the 21-row XLSX, and name
the prediction vintage on the face of any emitted rate. A5 is SHOULD, not MUST. The three parked
items stand: the demo reports' tracked home and the licence question under it, their staleness,
and the absolute paths above.

Commits: bcb763c (the configs overclaim recorded, with its fix bounded), committed 2026-09-12.
This DEVLOG entry committed separately, last, on 2026-09-13.

## 2026-09-13

Hours: 09:21 - 09:23, then 20:43 - 22:01 ET. Two blocks; the first was two minutes.

**`abe7be1` — the v050 predictions carry their provenance, and it is emitted rather than written in.**
The CSV had no header at all, so a rate computed from it could not say what produced it, and "name
the prediction vintage on the face of any emitted rate" is one of the two traps `TRACK_A_SCOPE.md`
already records against this work. The frozen CSV has a hand-maintained header and the v050 one
cannot: `score_v050_reextraction.py` opens it with `"w"`, so a hand-added block would be silently
lost on the next run. The two files look alike and are not the same kind of artifact.

What the header claims is scoped to what it can support. The model pin is read from the tracked
configs rather than hardcoded, so it cannot drift from them quietly. The load-bearing line is
recomputed at every emit — `k3_status` against the on-disk draws, 19/19 today, with a
content-derived fingerprint — and if the draws are absent it raises rather than emitting a line
claiming a check that did not run. The frozen header is not thin — it runs thirteen lines — but its
`Source commit of the batch: 70eed84` is hand-written and nothing recomputes it, which is the
difference this one is drawing. And the claim names what its reader must hold: reproducible on a machine holding the run,
not on a clone, because `results/` is ignored in full. 2619 bytes became 3570.

**Verification must not be able to damage what it verifies.** The first draft called
`_provenance_header` inside the `with OUT_CSV.open("w")` block. `open("w")` truncates on entry, so
the verification meant to protect the artifact destroyed it: a deliberately-failed check left an
empty file where the predictions had been, and the file came back from `git checkout`. This is a new
shape and does not reduce to the earlier check correctives. Those are about checks that cannot fail;
this one failed correctly and did damage on the way out. The fix is ordering — build the header
before opening the file (`score_v050_reextraction.py:229-232`) — and the rule generalises past this
file: a check must not sit inside the resource it is checking.

**A determinism check that passed because both runs crashed.** Confirming the emit was deterministic,
`cmp` compared the CSV to itself: both runs had died before writing, so the file was untouched and
trivially identical. Same family as items 1 and 4 of the 09-11 list — the acceptance test satisfied
by a global absence, and the heredoc `grep` that matched the wrong line and reported success — a
check reporting success from the absence of the thing it measures. What makes this family hard is
that the successful result and the no-op result are indistinguishable at the check's output. The
check has to assert that the thing happened, not only that the result matches.

The silent-strip hazard is handled by a test rather than a reader, because nothing reads the file
yet: forgetting the `#`-strip parses 32 rows instead of 19 without erroring. That is a landmine with
a known date — it fires when `score_target_space.py` moves to v050 — so its existing strip site now
carries a forward pointer naming the test, on the argument that the comment belongs where the next
person will be looking rather than where the hazard was found.

**`ebf8fb2` — the README's headline rate had no vintage, and the vintage was the wrong one.** The
0.5.0 re-extraction has been committed since 2026-08-06 and gives a different rate from the same
labels under the same map. An unlabelled number there was not a stale number; it was a number with
no vintage at all. The headline is now blind 10/17 = 58.8% [36, 78], named on its face, with the
command that regenerates it printed in the section, and both scorers named because
`score_target_space.py` still reads the frozen file.

Reachable-only is retired rather than recomputed. The exclusion was identified after seeing the
score and drops rows because of how they scored; a rationale found after the fact is not
distinguishable from a tuned one, and the excluded leaks are real defects.

**The totals are why this mattered.** Both vintages score 11 correct / 8 error over 19, and both
partition 5 / 2 / 1. braun went correct to error and mueller error to correct; braun is blind and
mueller is not, so the rate moved while every total held still. The sanity check anyone reaches for
— did the numbers move? — is structurally blind to the thing it is checking. That trap is now
written into the section rather than left in a scorer comment.

**Changing a describing word to a grading word changes what the sentence asserts, and the old
sentence's truth does not transfer.** The correct-list had read "the 8 bare-MNI-family papers
(agtzidis, derosa, gordon, …) + cole (Talairach)". Rewriting it for the new vintage, the agent made
it "the 8 `family_specified` papers … then cole (Talairach)", which is false: cole grades
`family_specified` too. "Bare-MNI-family" described the verbatims; `family_specified` names the
grade. They coincide on seven of the eight, which is why the edit read as a tidy-up rather than a
claim change — and gordon is the eighth, family_specified on "EPI template" by the gesture test and
not by anything MNI.

It was caught by the derivation, not by rereading. Every figure in that section was recomputed from
the committed CSVs rather than transcribed, and the recount came back 9 family / 1 absent / 1
study_specific against a sentence that said 8 + 1 + 1. This is the argument for deriving numbers even
when they are already known: the derivation catches the prose, not just the arithmetic. The same pass
found `## The real defect` describing the `value_not_in_literal` false-absence in the present tense
while the finding it links had recorded it fixed and demonstrated 11/12 five weeks earlier, and the
deferral capability finding standing at 1-of-3 when braun's fresh K=3 makes it 0-of-3.

**The disclosure has to be on the line.** `score_target_space.py` already printed a four-line NOTE
under reachable-only saying it was a post-hoc exclusion, and the README's headline was still an
unlabelled v040 figure. A number leaves a terminal by being copied, and a copy takes the line the
number sits on; a disclosure one line down does not travel with it. Both scorers now put the
qualifier inside the printed line — vintage on the presentable rate, `DIAGNOSTIC ONLY, DO NOT
PUBLISH` on reachable-only — so a figure pasted anywhere arrives carrying its own warning. The
diagnostic stays, because removing it would cost a working number to solve a transcription problem.

**Five untracked spreadsheets, one of them annotated by hand.** `git status` has listed five
`extractor_mvp/sfn_review*.xlsx` since June. I reported them as newly appeared, which was wrong and
sent the session down a sharper alarm than the facts warranted. They are outputs of the tracked
`generate_sfn_review.py`, never tracked, covered by no ignore rule, and four of the five carry
nothing a person typed. The fifth, `sfn_review_first_pass_review.xlsx`, holds 69 non-empty cells in
`review`/`correction`/`notes` — 64 distinct paper/step/field adjudications, none conflicting across
sheets — and the generator emits those three columns EMPTY (`generate_sfn_review.py:459-461`), so
nothing can regenerate them.

The mtime evidence I gave for "old, not new" was weak. 2026-06-17 15:10 is shared by **489 files**;
it is a bulk-copy stamp and says nothing about any one of them. The check that settles it was inside
the file the whole time: `docProps/core.xml` gives `dcterms:created` = `2026-06-07T17:31:05Z`, and
identically for `sfn_review.xlsx`, which makes the annotated copy a Save-As of it. The conclusion
held; the evidence for it did not, and a stamp was presented as a fact about a file.

That stamp also dates the review against the work it seems to have driven: the workbook was created
13:31:05 ET on 2026-06-07, and `30eed0b` — *atlas-space resolution_mm scoping* — was committed at
15:24:11 ET the same day. Ordering is consistent with the review having caused the fix and does not
establish it.

**A packaging bug is not a safeguard.** `pd.ExcelWriter` opens `mode="w"`, which truncates, so
pointing `--output` at the annotated workbook destroys all 69 cells silently. Nothing automated runs
the generator — no CI job, Makefile, hook or script invokes it, and both documented commands name a
different output — but the only thing that made the file *unclobberable* was `openpyxl` being
declared in neither pyproject and installed in neither venv, so the module died on import before
reaching any file. Treating that as protection couples the data's survival to a bug's survival: one
`uv sync` and one documented command and it is gone. The file was copied out of the repo before
either was touched.

`write_excel` now refuses when the target has non-empty review columns, naming the file and the
counts. Three properties, each chosen against a failure this log already records. The detector is
stdlib zipfile/ElementTree rather than openpyxl, because a guard that needs a missing dependency is
a guard that is not there. It **fails closed** — an unreadable workbook raises instead of reporting
"no annotations". And it runs before the truncating open, which is the provenance-header bug from
this same entry, one file over.

**A negative result requires evidence that the detector works.** Asked whether the other four
workbooks held hand data, I ran a parser that returned *no columns at all* for those four and
reported the answer as "no hand content". A failed detection was presented as a measured absence.
Rewritten to find the header row and handle both string encodings, the answer came back the same —
but that is luck, not method: the same output would have appeared if all five were full.

This is the sharpest of the session's correctives because it is the project's own subject matter.
AESPA exists to stop a system reporting absence when it has not looked, and the agent auditing it
did exactly that. It is also why the guard's tests lead with a **positive control** rather than
clean-workbook cases: neutering the detector to always return `{}` fails 3 of the 6 tests and leaves
both negative controls passing. A suite of negative controls would have shipped a guard that never
guards, green.

**A number produced to support an accepted conclusion gets less scrutiny than the conclusion did.**
Three invented numbers in three turns, between both of us: an untracked-file count of eleven that
reconciles with nothing; a "third instance" of a packaging-bug series whose second member does not
exist; and mine, "45 adjudication cells", which is not the sum of anything — the figure is 69, and
the guard produced it.

What they share is not carelessness. Each arrived *after* its conclusion was already settled and
agreed, as decoration on it, and not one of them would have changed anybody's mind had it been
right. A load-bearing number gets checked because the argument fails without it. A number that
merely illustrates a point already accepted is never load-bearing, so nothing pushes back, and it
goes in from memory. Hence the rule, which is the actionable form: **numbers that support what you
already believe need deriving, not recalling** — the opposite of where scrutiny naturally goes. The
one that was caught mechanically was caught because a tool computed it independently while reporting
on something else; the guard printed 69 on its way to refusing a write.

**The same shape in time claims, which read as observed and are not.** Today's Hours line is two
blocks — 09:21-09:23 and 20:43-22:01 — because the session transcript says so; the single range
09:21-22:01 would have been true at both ends and false about the 79 minutes between them. Two
earlier instances are in this log, and both are hedges rather than fabrications. `DEVLOG.md:1754`
records "not recoverable from here" about a push date that `git reflog show origin/main` had
exactly. And `DEVLOG.md:1301` states the 09-07 start "is not recorded", offering a `.git` mtime of
12:48 as mere circumstantial evidence — the session transcript's first event that day is **12:48**,
so the start was recoverable and the hedge was unnecessary. That Hours line can be firmed up; it is
left as written, with this as its correction, because that is how this log handles a superseded
entry.

**What the file is actually worth, checked rather than assumed.** A four-angle audit with an
adversarial pass over each finding established that the judgement is largely *already tracked*:
smith_2013's "not a real study with data" became the corpus drop recorded at
`sfn_batch_v4_config.yaml:3-5`, and all ten target_space corrections are committed labels in
`target_space_labels_v1.csv`. So "human judgement that exists nowhere else" was an overstatement I
made and then built on. What is genuinely single-copy is the residue: eleven accuracy verdicts on
fields with no answer key anywhere — `resolution_mm`, `target_surface`, `surface_registration`,
intensity `convention` and `value`, none of which have a labels file — plus one correction
(`agtzidis_2020 / resolution_mm = 3.0`) that sits only on sheet 3 and that I missed entirely.

Tracking it is ruled but not done, because the check attached to the ruling found the exposure in a
different column than expected. The corrections are clean against the repo's own 12-word threshold —
18 values, longest 11 words, none over. `notes` is not: 19 of 20 are over, the longest 532 words, and
they are hand-pasted paper text distinct from the tool's own spans. The generator's `verbatim_quote`
adds 14 more. A `review + correction` projection carries the whole residue and crosses nothing; the
cost is three notes that are commentary rather than quotation and would need lifting by hand.

**A larger exposure, found while looking at a smaller one.** `extractor_mvp/results/` is ignored by
a bare `*` and holds 57 analysis `.md` files, at least 26 of which are named in no tracked file. The
one backup archive on disk contains **zero** `results/` entries. By contrast `blindness_pilot/`,
flagged in the audit as single-copy, is fully backed up there — the investigator called one zip "the
only backup archive present" and its refuter found the files inside it byte-identical. Not acted on;
recorded because it is the same shape at ten times the size.

**Open.** The `results/` backup
question above. The tally with per-label state counts, then moving `score_target_space.py` to v050 —
which is when the silent-strip landmine fires, and why its strip site now carries a forward pointer.
A5 is still SHOULD, not MUST. The three parked items stand: the demo reports' tracked home and the
licence question under it, their staleness, and the absolute paths in the configs. Target
2026-10-31, poster 2026-11-14.

The tracking call is made: the projection, not the workbook. `ground_truth/sfn_first_pass_review_v1.csv`
carries 27 rows — 25 verdicts, 19 corrections — and three notes lifted by hand, liu_2005's truncated to
its commentary prefix so the paper text appended to that cell is not reproduced. Its header states what
the file is not, since a review of extractor output sitting in `ground_truth/` will otherwise be read as
a labels file and scored.

Commits: `abe7be1` (the v050 provenance emitter, its test, and the forward pointer) and `ebf8fb2` (the
README on the 0.5.0 vintage), both 2026-09-13; then `43c2b7a` (the qualifier on the line that carries
the number) and `55e3a2f` (the clobber guard and its six tests) on 2026-09-14. This DEVLOG entry and
the review projection are committed after them, the day after the work they record.

## 2026-09-14

Hours: 17:00 - 17:06, 18:48 - 18:53, 20:01 - 20:38 ET. Three blocks, 48 minutes active, eight
commits — four in the first block and four in the third. Track A's critical path has been finished
since A4; everything here is hardening, and the remaining poster risk now sits in numbers rather
than in code.

**`43c2b7a` — the qualifier belongs on the line that carries the number.** `score_target_space.py`
already printed a four-line NOTE under reachable-only saying it was a post-hoc exclusion, and the
README's headline was an unlabelled v040 figure for five weeks anyway. The NOTE was not the fix
because a number leaves a terminal by being copied, and a copy takes the line the number sits on. A
disclosure one line down does not travel with it. Both rates now carry their qualifier inline —
vintage on the presentable one, `DIAGNOSTIC ONLY, DO NOT PUBLISH` on reachable-only. The diagnostic
stays: removing a working number to solve a transcription problem is the wrong trade when a label
solves it.

**`55e3a2f` — a packaging bug is not a safeguard.** `sfn_review_first_pass_review.xlsx` held 69
hand-entered cells that `generate_sfn_review.py` writes empty, and `pd.ExcelWriter` opens `mode="w"`.
Nothing automated runs the generator and neither documented command names that file, so the workbook
was one deliberately-typed command from gone. What actually protected it was `openpyxl` being
declared in no pyproject and installed in no venv, so the module died on import before touching a
file. That is protection that ends the day someone runs `uv sync` — the data's survival coupled to a
bug's survival. The file was copied outside the repository first, before either change, which cost
one `cp` and removed the coupling in both directions.

The guard refuses when the target carries non-empty review columns, naming the file and the counts.
Its detector is stdlib `zipfile`/`ElementTree` rather than openpyxl, because a guard that needs a
missing dependency is not a guard; it **fails closed**, so an unreadable workbook raises instead of
reporting "no annotations"; and it runs before the truncating open, which is yesterday's provenance
bug one file over. Six tests, led by a positive control: neutering the detector to return `{}` fails
three of six and leaves both negative controls green. A suite of negative controls would have
shipped a guard that never guards, passing.

**`8f5c7b2` — the projection, not the workbook.** Most of the judgement in that workbook turned out
to be tracked already: smith_2013's "not a real study with data" is the corpus drop recorded at
`sfn_batch_v4_config.yaml:3-5`, and all ten target_space corrections are committed labels. What is
single-copy is the residue — eleven verdicts on fields with no labels file anywhere, plus one
correction that sits only on the All Fields sheet. So `review + correction` as a 27-row CSV, with
three notes lifted by hand and liu_2005's truncated to its commentary prefix. Tracking the workbook
would have committed roughly twenty pasted paper excerpts in order to preserve judgement that is
mostly committed already.

The header leads with what the file is **not**, because a review of extractor output sitting in
`ground_truth/` will be read as a labels file and scored — which would be scoring the extractor
against a reading of its own output. One cell clears the 12-word check: mueller's 21-word note, the
reviewer's own prose. Named in the header, so the hit is not mistaken for a miss.

**`7ea0cb8` — the tally, and per-label state counts.** The headline totals are invariant across
prediction vintages: 11 correct / 8 error in both, partitioned 5 / 2 / 1 in both, while the blind
rate moves six points. Anyone asking "did anything change?" of the totals sees nothing. The
per-label breakdown does not cancel — `deferred` goes 1/3 correct to 0/3, `study_specific` 0/2 to
1/2, and in v050 the `deferred` COLUMN disappears entirely because no paper is graded deferred at
all. The deferral capability finding, previously a sentence, is now a table that regenerates. The
label distribution regenerates too, instead of living only as inline prose, and `--out` writes the
file so no rate reaches a document by hand.

One reader strips the provenance headers, and **32** is the measured unstripped row count — the
number the forward pointer at `score_target_space.py:152` already predicted. Three tests hold it,
including an AST check that exactly one `DictReader` exists in the module and sits inside
`read_rows`. Mutation-checked: removing the strip fails 7 of 12, pointing the labels at the
22-data-row workbook fails 8 of 12.

**Four of those twelve tests failed on first run, and all four were the assertions, not the module.**
That is the right ratio to find. A suite where every assertion passes first try is usually pinning
what the code does rather than what it should do. One of the four is worth naming: the AST check
began as a regex and counted **two** `DictReader`s, the second being the module docstring's own
warning about bare DictReaders — prose confounding a check about code. And one was a guessed **31**
against a measured **32**, which is yesterday's rule firing again: a number produced to fill a slot
in something already believed correct.

**`b61a960` — six authored analyses out of an ignored directory.** `results/` is ignored by a bare
`*` and holds 483 files: 360 paid JSON draws, 24 generated summaries, 19 generated reports. All of
that is regenerable or licence-questionable and all of it stays ignored. Six files were neither —
authored prose, 312 lines, and of 56 distinctive sentences across the four with testable prose,
**none** appears in any tracked file. No backup archive on this machine holds a single `results/`
entry.

Two of them are why this outranked the workbook. `v7-attribution-diff-halted.md` records a
pre-registered corpus re-derivation being WITHHELD because the chen canary failed.
`sfn-v1-v2-delta-coercion.md` records that the v2 aggregate gains were largely coercion and states
plainly that they are not all honest. Both are findings against this project's own numbers. **An
untracked negative result is the shape that disappears quietly.** One corpus span was removed rather
than parked — four cells quoting agtzidis's normalization sentence now read `[span withheld]` with a
pointer — which dissolves the licence question instead of deferring it, the same move the projection
made.

**`c2627b5` and `83c0c61` — supersession, and saying which of three causes.** The tracked hard-drop
finding reports 10 silent drops across 6 papers and reads as current; the re-measure gives 2 across
1 at the same pin on the same corpus, and had sat in `results/` for two months. A dated block now
points at it with the original text retained — 48 lines added, one deleted, and that deletion is the
headline replaced in place with a pointer appended.

"The numbers differ" is not a supersession, so the block says which cause. **A fix landed between the
runs**, and the evidence is a same-day timeline to the hour: the measurement at 11:38, `b9e8a42`
shipping span-resolver tier 5 at 18:34, the re-measure at 21:05, `2560bb1` consuming the recoveries
at 22:09. The other two candidates were ruled out rather than dismissed — the file already records
9-vs-10 across two pre-fix runs, so ±1 is the expected variance and 10-to-2 sits far outside it; and
the denominators are comparable at 52 extracted fields against 50, so it is not a smaller sample.

The two survivors confirm the mechanism instead of merely surviving it. Both are agtzidis_2020, the
`×`→`/C2` glyph mangle that tier 5 **deliberately excludes**, naming agtzidis at
`span_resolver.py:16-20`. The one class the fix declines to handle is the one class still dropping —
the resolver's own source agreeing, not an inference from the counts.

`83c0c61` separates the count from the classifier, because the re-measure's partition comes from an
auto-classifier the older document overrode by hand. `silent_drop` is set at
`hard_drop_audit.py:159` **before** `_classify_failure` runs at `:160`, and the headline counts
`len(drops)` without reference to the bucket — so both 10 and 2 are mechanical and the fix-landed
conclusion rests on nothing classified. What does rest on it is the reason partition, where
"RECOVERABLE mangle: 0 · genuine-mismatch: 2" is contradicted twice: by the hand adjudication, and
by the resolver's note holding that those quotes ARE in the source.

**"Shipped inert" described the caller; the audit measures the callee.** The commit that landed tier
5 says "SHIPPED INERT", and read as a claim about the system that means nothing changed — which
would have made the 8-drop gap unexplained and pushed the reading toward nondeterminism. Inert
described only the CALLER not consuming the `recovered` marker until three and a half hours later;
`resolve_quote` itself grounded those quotes from 18:34, and grounding is precisely what the audit
measures. Same shape as yesterday's describing-word-to-grading-word error: **a term accurate about
one layer, read as a claim about the system.** It nearly hid the whole explanation.

**When a check disagrees with what you expect, suspect the check before the subject.** This is the
session's halt rule turned on the instrument rather than the belief, and it covers both directions
now. Yesterday's instances were absences that were not: a parser returning no columns reported as
"no hand content". Today's three were problems that were not. A corpus-span detector keyed on the
wrong JSON field names returned an empty reference set, which would have made six clean-looking
zeros meaningless — caught only because the check printed its own reference-set size. A
line-comparison that dropped every `>` line stripped `delta_vs_v1.md`'s own blockquote along with my
header and reported the COERCION warning as lost in the move. And a line-based `grep` reported the
`[span withheld]` pointer's target missing, because the CSV field it points at wraps across lines.
All three were the method being measured instead of the subject.

**A property measured on one member, asserted of the set.** Distinct from the above, because here
the detector worked and the sample did not represent. Checking whether the generated reports carry
paper text, I read braun_2015's, found no quotes — correctly; its pipeline is deferred, so the
report renders a deferral line rather than a quote — and stated it of all nineteen. Measured: spans
in **15 of 19**. That settles the parked demo-reports item against the framing that made it look
simple: the reports carry corpus text, so tracking them was always the same licence question as the
JSONs, narrower only because of the 80-character cap. Recorded in `TRACK_A_SCOPE.md` with the raw
total flagged as an upper bound on matches rather than a quote count, so October does not re-derive
it and does not mistake 58 for 50.

**Open.** A5 (SHOULD, not MUST) or the 12-of-14 COBIDAS rows, which are scoped after the report
tool. Whether the hard-drop finding's Phase-2 design consequences need revisiting now that tier 5
has landed. The three parked items stand: the demo reports' tracked home — now with a measured
answer under it — their staleness, and the absolute paths in the configs. Target 2026-10-31, poster
2026-11-14.

Commits, all 2026-09-14: `43c2b7a` (the qualifier on the line that carries the number), `55e3a2f`
(the clobber guard and its six tests), `8f5c7b2` (the review projection), `8871313` (the 2026-09-13
DEVLOG entry), `7ea0cb8` (the tally with per-label state counts), `b61a960` (six authored analyses
tracked out of `results/`), `c2627b5` (the hard-drop supersession) and `83c0c61` (count separated
from classifier). This entry is committed after them.

## 2026-09-14 (late)

Hours: 20:38 - 20:45, then 21:12 - 21:17 ET. The 09-14 entry's third block is recorded there as
closing at 20:38 because that is when the entry was committed; the block actually ran to 20:45.
Same handling as the 09-12 (late) entry — a second entry rather than an edit to a pushed one.

**Pushed, and the open item from the entry above is closed.** `c6cd3c2..59dfcc4`, eleven commits,
verified against the remote with `git ls-remote` rather than the local ref. The push set contains
zero files under `results/`. The cadence is now 09-12, 09-13, 09-14 — the eleven-day gap that
prompted the rule has not recurred, and the rule this time was applied before anything else in the
sitting rather than at the end of it.

**Phase 2 is mostly done, and not in the form it was designed.** A seven-angle fan-out with an
adversarial pass over each answer settled the question the supersession left open. Of the three
Phase-2 consequences in `span-resolution-hard-drop.md`: consequence 2 (value-support rather than
quote-presence) is DONE and wider than specified — unconditional on every extracted base_pipeline,
not gated on `recovered`, via `efbe14a` on 2026-07-23, a commit none of the three docs-of-record
names. Consequence 3 is done for three of its four artifacts, the `×`→`/C2` class being the
deliberate exclusion. Consequence 1 was never built as written: `span_unresolved` appears in **zero**
Python files, and the positive control on the same tool finds `span_recovered` in eight. v0.4.0 took
the opposite route — resolve more spans, mark the recoveries — rather than keeping EXTRACTED on an
unresolved one.

Two gaps remain and both are cheap. `_build_base_pipeline` still has no diagnostic channel, which
was the original finding's named "worst case": driven directly at HEAD, a base_pipeline whose name
extracted but whose quote cannot be grounded returns a bare `MissingFromPaper` indistinguishable
from the model having said nothing. And `span_recovered` has **no downstream consumer** — it rides
on the extraction and is invisible in reports, batch summaries and coverage. Neither needs a paid
re-extraction, which makes them the cheapest honest work available.

**The 12 COBIDAS rows: scoped, and declined.** Not on schedule grounds. Three measurements decide it.

`covered_by_extractor` **never reads the paper.** It is 0/19 or 19/19 on every row, because
`_assemble` emits its seven steps unconditionally (`extractor.py:874-882`); a row flips for all 19
papers the moment one field's targeting flag changes. Coverage is a property of the code, not of
what any paper reported.

Which means the cheap version makes the reports **less honest**, and that was verified by rendering
rather than argued: flipping one `nuisance_regression` field strips "(no fields assessed by current
extractor)" from derosa_2025 and moves "Artifact and structured noise removal" into the bare
unaddressed-mandatory list — against a paper that wrote "motion correction via ICA-AROMA (version
0.3 beta)". The distortion pair is worse: one spec kind serves **both** D.3 rows and
`assess_coverage` never reads `DistortionSource`, so a paper reporting only susceptibility
correction would be credited with gradient distortion correction. That is a decision to make before
those rows are lit, not after.

And all twelve are **conditional** — `software` is the only unconditional mandatory row and is
already covered — so none of the twelve can yield a new citable violation. The poster's citable
claim does not move.

The poster premise was also partly false. The tool prints `Assessed by AESPA: N` and
`Not assessed by AESPA: N` — counts, never a fraction. There is no "2 of 14" line to improve, and
putting one on a poster would reinstate a form this repository removed twice.

Cost, for the record, since it was measured. The twelve split unevenly: **three are targeting-only**
(brain_extraction, segmentation, artifact_structured_noise_removal — their kinds are already emitted
19/19), **nine need construction and wiring** as well. The dominant cost is not edits but a paid
re-extraction, which does not multiply per kind because one call per paper carries the whole schema.
The reason to refuse is that the call is demonstrably **not inert** under prompt changes — v1→v2
coerced five of seven MNI terms — and that prompt currently drives the poster's headline
`target_space` number on a model already measured as non-stationary at an identical pin.

**Open, and first.** The supersession block committed in `c2627b5` **understates the current
residue**. Its "2 drops across 1 paper" comes from a re-measure produced before `efbe14a`; the batch
the repo treats as ground truth has three unresolved-quote diagnostics across two papers plus two
undiagnosed base_pipeline drops. The causal claim in that block stands — a fix landed, and the
excluded glyph class is still the residue's core — but the count is a stale vintage, stated in a
pushed document, and should be corrected before it is quoted. Then the two Phase-2 gaps. A5 stays
SHOULD-not-MUST; the twelve rows are declined rather than deferred, with the reasons above recorded
so the decision is not re-litigated from scratch in October. Target 2026-10-31, poster 2026-11-14.

Commits: none this sitting — the work was a push of the eleven already recorded above, and a
read-only scoping pass that wrote nothing. This entry is committed on its own.

## 2026-09-30

Hours: 19:26 - 19:39, then 20:43 - 20:44 ET. Sixteen days since the 09-14 entry, and nothing moved in
between: HEAD was still `f3017ee` with the same six untracked files, 316 tests still passing, and
both published rates still regenerating from committed data. Thirty-one days to the internal target,
forty-five to the poster.

**`3356d03` — the first open item, closed, and half of it withdrawn rather than fixed.** The
supersession written on 09-14 reported the post-fix span-resolution residue as "2 silent drops across
1 paper". That figure is a 2026-07-13 measurement and predates `efbe14a` (2026-07-23). Its own
denominator table is the proof: it records `viduarre_2017 base_pipeline_name EXTRACTED`, where the
current batch has viduarre `DEFERRED_TO_CITATION` with reason
`citation_shaped_name_value_unsupported` — the efbe14a guard firing. The causal claim is unaffected;
only the count was stale, and it was stale in the flattering direction.

Measured over all 19 papers of the ground-truth batch: **three unresolved-quote diagnostics across
two papers** — agtzidis_2020 on `target_space` and `resolution_mm`, liu_2005 on `resolution_mm`.
`liu_2005` appears **nowhere** in the re-measure document, which is the single clearest sign the two
are different vintages rather than two readings of one run.

**A count withdrawn as unmeasurable, which is a shape this log has not recorded before.** Both the
09-14 (late) entry and the first draft of this correction said "plus two undiagnosed base_pipeline
drops". That number is not derivable and should never have been written. Five papers carry
`base_pipeline` `MISSING_FROM_PAPER` and **all five carry the identical reason**
`no_base_pipeline_named`, so how many are silent drops rather than genuine absences cannot be told
from the output at all — which is precisely the missing diagnostic channel the original finding named
as its worst case. Putting a count on it asserted a distinction the artifact does not make.

The honest form is a bound, not a count: **the missing diagnostic hides the true state of up to 5 of
19 papers' base_pipeline fields.** That is stronger than the withdrawn figure, not weaker, and it
re-prices the second Phase-2 gap: adding a diagnostic channel to `_build_base_pipeline` would turn
five indistinguishable rows into five readable ones.

Where this came from matters for how the next agent output gets treated. The "two undiagnosed drops"
figure originated in a workflow refuter's report on 09-14, was flagged in that entry as something to
fix, and was carried into a pushed document without my ever having measured it. The rule it breaks is
the one already in this log — **a number produced to support an accepted conclusion gets less
scrutiny than the conclusion did** — with a new wrinkle: the conclusion here was itself a correction,
and corrections arrive with their own air of rigour. The adversarial pass was right that the residue
figure was stale, and wrong about what replaced it; being right about the first half bought the second
half an unearned pass.

**Open.** The two Phase-2 gaps, now priced: a diagnostic channel on `_build_base_pipeline` (worth up
to 5 of 19 papers' base_pipeline states becoming readable) and `span_recovered` having no downstream
consumer. Neither needs a paid re-extraction. A5 stays SHOULD-not-MUST and the twelve COBIDAS rows
stay declined. The three parked items stand. And the question this sitting did not take up: with
numbers settled and 31 days to the internal target, whether the 2026-08-26 "compute everything first,
render once" deferral still holds or whether figures are now the critical path.

Commits: `3356d03` (the residue correction). This entry is committed after it, and both are pushed
with `f3017ee`, which had been sitting unpushed since 09-14.

## 2026-10-01

Hours: 00:28-00:35, 02:45-03:50, 06:27-06:30, 10:52-11:12, 11:48-11:52, 16:34-16:35, 16:57-17:22,
17:44-18:03, 19:58-20:05, 21:18-21:29 ET. Ten blocks, 163 minutes active, nine commits. The long block
is the base-arm implementation; the short ones are rulings arriving between other work.

**The day's finding is not any of the nine commits. It is that both published accuracy rates are
K=3 plurality collapses, and the entire vintage difference rests on one 2-1 vote.**

It surfaced from a question that looked procedural. The K-draw stability design doc asserted, as the
consequence of its opt-in ruling, that the SfN figures "are computed from single-draw artifacts". That
was checked rather than taken, and it is false. `score_target_space.py:173` reads `extractor_status`,
which the frozen CSV's own header line 4 calls `status = K=3 MAJORITY`;
`score_v050_reextraction.py:183-185` takes `Counter(statuses).most_common(1)`, resolves a three-way tie
toward `draw_1` by insertion order, and lets the **winning draw supply the value that is graded**. Both
rates are aggregates and neither said so.

Then the margin. **braun_2015 is the only paper in either vintage whose three draws disagreed** —
frozen `DEFERRED/MISSING/DEFERRED`, collapsed to `DEFERRED_TO_CITATION`, which is exactly what makes it
*correct* at 11/17. Its v050 draws are `MISSING` 3/3. Re-score the frozen vintage with that one
plurality the other way and it reads 10/17 — identical to v050. braun is blind, so a six-point
difference written into the README, the tally, the DEVLOG and a pre-registration turns on a single
vote with a margin of one draw.

**`20bbd2a` — the disclosure.** Every rate in the tally and the README now carries its aggregation
rule beside its vintage, pinned by a test that fails if a rate line is not followed by an aggregation
line. Naming the rule says a vote happened; it does not say where the margin was, so the tally also
emits a *Where the plurality vote actually decided something* section listing the contested cell, what
it collapsed to, and whether it is blind. The argument is the vintage rule's own, one layer in: a rate
stated without the step that produced it hides that step.

**`215de21` — and the correction to my own correction.** The prereg amendment narrowed the
non-stationarity attribution on braun and then overclaimed on the other mover, saying the finding
"survives" there. mueller's 0/3→3/3 gives Fisher **p = 0.100** — which is **the floor K=3 can reach**.
A measurement whose best possible outcome is non-significant cannot establish anything; it can only
fail to rule something out. And mueller was *selected as the most extreme of 19 papers*, so the nominal
0.100 overstates it.

**The multiplicity penalty cannot be quantified, and that is the same limit biting twice.** Correcting
0.100 for having looked at 19 papers needs the per-paper per-draw flip probability — which is precisely
what K=3 cannot bound (rule of three: zero flips in 3 draws bounds it at 3/3 = 1.0). Real,
unquantifiable from this data, and in the direction of weaker. The supportable statement: non-stationarity
is **suggested** by one paper at the maximum strength K=3 allows and **established by neither**.

Two things were being conflated and the record now separates them: **nondeterminism** is sampling
varying within a fixed distribution; **non-stationarity** is the distribution itself shifting between
dates. braun's frozen draws already contained one MISSING in three, so 1/3 vs 3/3 (p = 0.400) is fully
consistent with a stationary distribution. Neither "non-stationarity moved the rate" nor "nothing
moved" is supportable — **the two vintages are not distinguishable at K=3**.

**`c299c2e`, `2018bd3`, `fd8570e` — the base_pipeline diagnostic.** Four conditions reached one
byte-identical bare `MissingFromPaper`, so the report told all four "no base pipeline named in source",
true of exactly one. The fourth was hiding inside the first: a deferral whose sentence would not ground,
told it had named nothing while it had named a citation. Ruled Arm 1 — a reason, not a new state — on
the ground that case B is irreducibly ambiguous: `quote_not_found` means either the model fabricated a
sentence or the resolver cannot find one that is there, and nothing at that site distinguishes them, so
a "could not determine" state would assert a determination the evidence does not support.

The blocking condition was verified rather than assumed and held worse than stated: `cobidas.py:191`
reads the *status*, so a case B/C paper was counted an unconditional COBIDAS violation **and** told "No
software named in the source" — two false statements, on the project's only citable claim. Ruled
`covered=False` scoped to the unverifiable conditions, on `cobidas.py:166-173`'s own NotApplicable
reasoning. That created a new collapse and the ruling refused it: a third count, because
"never targeted" and "targeted but unverifiable" are two facts the tool can distinguish, and accepting
their collapse inside the fix for the same defect would turn an inherited bug into a stated position.

**A rule, for any future reason-base decision: enumerate by truth of the rendered line, not by table
economy.** A reason base exists to select a sentence an author reads. Reusing one because it costs
fewer dict entries ships a false sentence to save a key, which inverts the only thing the reason is
for. It earned itself immediately — it is what surfaced that the fourth condition's existing sentence
was already true of it verbatim, which table-economy reasoning had missed in both directions. The
author's own suffix ruling was reversed the same day under it.

**`20f3694` — a drifting expectation, fixed at the root rather than the number.** The re-render gate's
negative control disagreed with its recorded "7 changed", returning 16/3. The reconciliation was exact
(f44771a moved 14, 59e732b moved 2; the 3 identical are the three papers with version `EXTRACTED` and
so no Software section), but updating the number would have left the real problem: the control compares
one fixed ref against the **working tree**, so its expected value is a function of whatever HEAD is. The
docstring now says 16/3 *at this HEAD* with the derivation, names the drift as structural, and flags the
fix — a second ref argument pinning two fixed refs, where `d31e8b7` against `c9c2951` is permanently 7.

**`90dd9ee` — a miscount that touched nothing binding, which was the point of checking.** Both variance
documents say 3 of 24 field-cells flipped; the raw table shows **2 of 24, 22 stable**. The prereg's
`K = 10` cites that file — so the question was whether a committed pre-registration rests on a wrong
count. It does not: `motion-method-reachability-prereg.md:7-8` cites `variance.md` for the *existence*
of nondeterminism, which 2 flips establish as well as 3, and separately cites an independent K=10
observation. No amendment needed. The likely source of the 3 is a summary table that lists
`surface_registration` among the chen rows while marking it `stable ×15` — the kind of error a table
invites when it mixes headers with outcomes.

**`7307491` — a broad catch that converted code bugs into data.** `batch.py` recorded every exception
from `extract` as that paper's `extraction_failed`. Two kinds of failure want opposite handling: a
data failure is one paper's property and should be absorbed; a code defect affects every paper
identically, and recording it as a paper status misattributes a tool failure to the corpus **and** lets
a batch finish green with every row corrupted. Re-raise the defects rather than enumerate the data
failures, for two measured reasons — `batch.py` imports neither `instructor` nor `litellm` and
`instructor.exceptions` is already deprecated, and `issubclass(litellm.exceptions.AuthenticationError,
litellm.exceptions.APIError)` is **False** because two classes of that name sit in one MRO, so a
data-failure base list would silently miss siblings.

**A success message that is not downstream of the success.** A script of mine printed "added and wired
in" while its replacement never ran: the first anchor matched, so the `if` skipped the branch doing the
work, and the `print` was unconditional. Caught by reading the rendered artifact rather than the
script's account of it. Same family as the determinism check that passed because both runs crashed —
**a print that is not downstream of the work reports intent, not outcome.**

**And an environment fact that silently changes a result**, now in CONTRIBUTING beside the interpreter
trap: the shell's `grep` is a function that filters git-ignored paths on a recursive search from a
directory. `grep -rl X .` returns 0 under `results/` where `/usr/bin/grep` returns 106. Explicit paths
are not filtered, which is why it goes unnoticed — it bites a recursive search used to establish an
absence, and returns a clean zero with no error. Found by an agent whose positive controls came back 0.

**Open.** The version arm of the base_pipeline diagnostic (§10 — nine papers against the base arm's
five, and "complete" is not claimable until it lands). `multi_acquisition_batch.py:109`, the same broad
catch, untested and left for its own change. The two-fixed-ref argument on the re-render control.
`span_recovered` still has no downstream consumer. And the render question, still standing by default
with thirty days to the internal target — the only open item with a date attached.

Commits, all 2026-10-01 and all pushed through `215de21`: `c299c2e`, `2018bd3`, `fd8570e`, `20f3694`,
`20bbd2a`, `056369e`, `215de21`, then `90dd9ee` and `7307491` after the push. This entry is committed
after them.

---

## 2026-10-01 (very late)

**The render question is decided, and the entry above is wrong about it.** `DEVLOG.md:2371` says the
render question is "still standing by default with thirty days to the internal target". It was true
when written and is not true now: rendering happens in November, from whatever state exists then.
Recorded at `docs/TRACK_A_SCOPE.md`, which retains the superseded 2026-08-26 text above the ruling.
Corrected forward rather than edited, which is the whole reason the stale line is still up there.

The 2026-08-26 deferral was "compute everything first, render once" — a condition on a computation set
nobody ever declared finished, which is how a decision becomes a default. The ruling removes the
condition rather than satisfying it. Its source is recorded as my ruling in conversation, dated
2026-10-01 — **the day it was written down, not the day it was said.** A ruling that exists only in a
conversation is not checkable, and this stale DEVLOG line is the demonstration: the record contradicted
a live decision because the decision had no record to contradict it with.

**The constraint that came out of checking it, which is new.** Demo reports are regenerated by replay
from stored per-paper JSON, and the base arm (`2018bd3`) changes only what a NEW extraction records. So
replay reads the stored reason. Driven over all five missing-base papers at HEAD — binder_1999,
cole_2013, liu_2005, poldrack_2015, power_2014 — every one still prints `Base pipeline: no base
pipeline named in source — you must specify` from stored `no_base_pipeline_named`. For **poldrack_2015**
that sentence is false: `predictions_v040_frozen.csv` has it `EXTRACTED` 3/3 as "Washington University
pipeline". A replayed poldrack panel would put the exact false statement the base arm was built to
remove on the poster. Two ways out and only two — demo from outside those five, or re-extract what you
want to show, which is a paid run on a model this project has measured as non-stationary. Recorded
before panel selection instead of discovered during it.

**The version arm's position: behind K-draw stability, per the ratified sequence** (`056369e` §6).
Recorded in `DELTA_base_pipeline_diagnostic.md` §10 with its two reasons, both about what landing it
early cannot buy: it does not block labelling, and it cannot move a committed number, because the nine
papers' stored JSONs carry the old reasons exactly as the five do. Its value lands on the next paid
re-extraction. "Complete is not claimable until the version arm ships" is unchanged — deferred is not
fixed.

**Open**, unchanged from the entry above except that the render question leaves the list and the version
arm now has a stated position in the queue: `multi_acquisition_batch.py:109`, the two-fixed-ref argument
on the re-render control, `span_recovered`'s absent consumer. Next: the K-draw stability implementation.

**And the test invocation, found while verifying the above and now in CONTRIBUTING** beside the two
environment traps it belongs with. The suite runs under the **root** interpreter from `extractor_mvp/` —
the opposite interpreter from the documented batch command. Both other combinations fail at
*collection*: the extractor's own `.venv` has no `pandas` (which `generate_sfn_review.py` imports), and
the root `.venv` from the repository root cannot import `tests.test_batch`. A wrong invocation here
therefore reads as a broken repository, not a wrong interpreter — which is why "333 tests pass" is only
a meaningful claim with the invocation attached to it.

No code in this entry: four documents, five records — `TRACK_A_SCOPE.md` carries both the render
ruling and the replay constraint. Follows `e769541`.

---

## 2026-10-02

**CI had been red for twenty days and nothing in the record said so.** The `extractor-mvp` job
failed every run from 2026-09-13 to 2026-10-02 — six runs, 32 commits, six pushes. Last green run
`33581368897` @ `214b55c2`; first red `34731990637` @ `dcc8e8a5`; failing step `#10 Pytest (offline)`
in both the first red and the latest, the latest completing in 32s. Two independent collection
errors, `tests/test_report_cli.py:14` (`No module named 'tests'`, from `815ec2f`) and
`tests/test_sfn_review_clobber_guard.py:34` → `generate_sfn_review.py:22` (`No module named
'pandas'`, from `55e3a2f`). Fixed in `ac63ada`.

**One import, three checkers blinded — and each blindness looked like a different local problem.**
`from tests.test_batch import _patch` broke CI collection; it hid the outcome of
`test_tally_scope_is_step_fields_only`, which was added in `a0ba2872` *into an already-red suite*
and had therefore never run anywhere but a laptop; and it truncated mypy across the entire
repository with `Source file found twice under different module names: "test_assemble_v0_3_0" and
"tests.test_assemble_v0_3_0"`. A full pre-commit mypy run at `f59609a` stopped at that one error;
with the import gone it reaches **109 source files**. Three checkers, one cause, three unrelated-
looking symptoms.

**The fix is structural, not a path setting**, and the reason is a second package. `pythonpath =
["src", "."]` would have worked and was staged for a day; it was the symptom fix, and worse, it was
load-bearing for a *test outcome* rather than only for collection, because the second cross-test
import sat in a function body (`test_batch.py:248`) where no collection-time check could reach it.
Making `extractor_mvp/tests` a package was the other tempting option and is worse still: the
repository root has its own `tests/` package, with `__init__.py`. Measured — from the root,
`import tests` resolves to `/fmri-repro-agent/tests/__init__.py` and `tests.test_batch` then fails,
which is exactly the `No module named 'tests.test_batch'` that the CONTRIBUTING section written the
night before had filed as an interpreter quirk. Two importable packages with one name, resolution
decided by `sys.path` order, permanently. So: `_patch` and `_assembled` moved into
`tests/conftest.py` as the `canned_batch` and `assembled` fixtures, both imports deleted,
`pythonpath` unchanged at `["src"]`, collected count unchanged at 335.

**Mutation results.** `canned_batch` (12 dependent items): body made a no-op → 11 fail. The
survivor is `test_run_batch_skips_and_records_excluded`, legitimately — exclusion happens before any
PDF load, so its assertion never needed the stub; it declared the same dependency before the move.
`assembled` (4): returns a step-less `Preprocessing` → 4 fail. `assembled_with_deferred_base` (1):
extraction arm stops deferring → fails on the test's own guard, *"fixture must actually defer, or
this test pins nothing"*. **My first attempt at that third mutation passed**, and the fixture was
not at fault: I mutated `inference`, and `extraction_status` reads the `extraction` arm. A mutation
that fails to kill is a claim about the test only once you have checked it is actually a mutation.

**The exposure, which is the part that outlives the fix.** `DEVLOG.md:2207` (`28b9d35`, 2026-09-30)
states "316 tests still passing" — true of a laptop, not of CI, 18 days into the red window. Worse,
`CONTRIBUTING.md` as committed in `f59609a` *prescribed* the invocation that hid both errors and
listed CI's two failures as the symptoms of using the wrong one. That section was written the night
before, after measuring both errors by hand. The invocation was validated by the fact that it
produced a green number. Replaced in `ac63ada` with CI's own command, and the generalisation is now
a rule in that file: **verify against the checker that will actually run.** A number produced by a
harness nobody else uses certifies the harness, not the code.

**Push verification is now a step, not a principle.** `git ls-remote` confirms what arrived and says
nothing about whether it was good. CONTRIBUTING now requires reading the remote's verdict on the
pushed head — both jobs, by `gh run view` — and records that CI runs per push, not per commit: the
push that went red carried 21 commits, of which 15 rode in on an already-broken suite without ever
being tested on their own. The bisect that found `815ec2f` was work the run history could not do.

**Recorded, deliberately not fixed here.** Seven mypy errors are now visible that the truncation hid:
six `var-annotated` in `extractor_mvp/tests/test_render.py` (`:916`, `:925`, `:956`, `:988`, `:997`,
`:1020`) and `extractor_mvp/tests/test_report_cli.py:15` `Module "extractor_mvp" has no attribute
"report"`. The last one is why `ac63ada` was committed with **`SKIP=mypy`** — the narrow bypass, not
`--no-verify`; every other hook ran and passed. That rejection predates the change: identical at
`f59609a` at `:16`, the one-line offset being the import `ac63ada` deletes, and it has been failing
or bypassed since `815ec2f` added the file. The cause is a hook–CI mismatch: the hook runs mypy from
the repository root under the root `pyproject.toml`, where `extractor_mvp` resolves to the directory
instead of `extractor_mvp/src/extractor_mvp`, and four test files import a submodule by attribute.
`MYPYPATH` does not fix it; the hook's env is isolated.

**Next change: the hook runs what CI runs, and nothing more.** A hook that checks something CI does
not — or checks it from a different working directory — recreates precisely the local-green /
CI-red divergence this entry is about. Excluding `extractor_mvp/tests` and calling it a policy was
rejected: it would write the gap into config as though it were a choice. Whether `extractor_mvp`'s
tests should be type-checked at all is a real decision, and it goes into CI and the hook together,
after the seven errors above are addressed — not into either one alone.

**And the lesson landed a third time, inside the fix for it.** The green run reports `326 passed, 7
skipped, 2 deselected`; my reproduction had reported `331 passed, 2 skipped`, and I had written 331
into CONTRIBUTING as the expectation to check CI against. Cause: `tests/test_methods_finder.py:12`
skips on `Path("/Users/cwook/.../tested_lit/sfn_batch")` — an **absolute** path, so those five corpus
tests resolve the laptop's corpus from *any* checkout on this machine, and a git worktree gives no
isolation from them. The reproduction was faithful on the question it was built to answer — it matched
CI's collection output character-for-character at `dcc8e8a5` (`291 items / 1 error / 2 deselected /
289 selected`) and at `e769541` (`323 / 2 errors / 2 deselected / 321`) — and unfaithful on pass
counts, which I did not re-check before writing one down. Corrected in `252ea37`. A sandbox is only
isolated with respect to the paths it actually controls, and absolute paths in tests are outside all
of them.

**Also mine, this stretch.** I called the `pythonpath` change "the minimal root-cause fix" when it
was the symptom fix. I argued openpyxl should stay undeclared because its absence protects the 69
adjudication cells — the reasoning this repo had already rejected in
`tests/test_sfn_review_clobber_guard.py:6` ("A packaging bug is not a safeguard"), in a file I had
read that day; it stays out because it is outside a CI fix's attributable diff, and the real
protections are the backup outside the repository, the tracked projection, and the mutation-tested
guard. And I reported a commit as succeeding when `git log` had not moved, because I read `$?` after
a pipe into `tail` — the same shape as the print that was not downstream of the work.

Commits: `f59609a` (the three records and the DEVLOG forward correction), `ac63ada` (the CI fix), and
`252ea37` (the count correction above). `ac63ada` is the first green `extractor-mvp` since
`214b55c2` on 2026-09-02 — run `37098275269`, both jobs `success`. This entry is committed after them.

---

## 2026-10-03

**The hook now runs what CI runs, and the diagnosis is a tool asymmetry the old hook inherited
silently.** `76bd8bc` replaces the `mirrors-mypy` hook with two `repo: local` hooks that are
literally `ci.yml`'s lines — `uv run mypy src` from the repository root (`ci.yml:57-59`) and
`cd extractor_mvp && uv run mypy src` from `extractor_mvp/` (`:98-100`). Verified identical to CI on
the same tree: clean, both report `Success: no issues found in 17 source files` / `26 source files`,
matching CI's own commands; with `return "not an int"` appended to
`extractor_mvp/src/extractor_mvp/report.py`, hook and CI both report
`src/extractor_mvp/report.py:93: error: Incompatible return value type (got "str", expected "int")`
and `Found 1 error in 1 file (checked 26 source files)`, and the hook blocks a real commit — checked
by staging the mutation and confirming HEAD did not move. Repeated against the root package at
`src/fmri_repro/spec/preprocessing.py`.

**ruff needed no change, and the reason is the whole finding: one tool resolves configuration per
file and the other does not.** ruff discovers the nearest `pyproject.toml` for each file, so the
existing ruff hooks already honour `extractor_mvp/pyproject.toml`'s own `line-length` and its
`per-file-ignores` for `span_resolver.py` — verified on exactly that file. mypy has no equivalent
discovery: run from the repository root it takes the root `[tool.mypy]`, under which `extractor_mvp`
resolves to the **directory** rather than to `extractor_mvp/src/extractor_mvp`. A hook configuration
that treated the two tools the same therefore inherited the difference without stating it, and the
inherited failure — `Module "extractor_mvp" has no attribute "report"` — had been rejecting every
extractor_mvp test that imports a submodule by attribute since `815ec2f` on 2026-09-12. Which means
it was being bypassed or ignored, and a check in that state is not a check: `ac63ada` and `252ea37`
each needed `SKIP=mypy`; `76bd8bc` needed none.

**Two sub-decisions for K-draw stability are recorded before any code**, in
`DESIGN_kdraw_stability.md` §4b, with acceptance items 8 and 9. They arrived in an implementation
prompt rather than from the design doc, which is the same gap that let the render ruling sit
unrecorded while `DEVLOG.md:2371` said the opposite — so they are written down first. **Value
agreement is exact equality** of `Extracted.value` serialized with no normalisation, excluding
`spans` (span agreement is a separate unit, and `SpecifiedTerm.verbatim` is value content while the
quote is `Extracted.spans`, so this does not collapse the two), `confidence` (the uncalibrated
placeholder), and `span_recovered` (absent on 299 of 601 stored arms, so including it would read
absence as disagreement). Strictness is free because fork 2 keeps the full per-draw record, so every
looser rule stays computable without a re-run; between two numbers computable from one record, the
one that cannot understate movement is the one to publish.

**The artifact is run output, gitignored, beside its draws — and the premise for that needed
correcting.** "Stability is a property of a run, not a label" does not by itself exclude
`ground_truth/`, because that directory is **not labels-only**:
`ground_truth/predictions_v040_frozen.csv` is tracked and is not a label, its emitted header calling
it "a durable snapshot of a NON-reproducible run … the record the first Tier-A/Tier-B number was
computed against", while the run's own `predictions_v040.csv` sits untracked under `results/`
(`results/.gitignore:7` matches `*`) with a bare column row. So fork 4's prediction-CSV precedent is
**two-stage**: emit into ignored `results/`, promote to a tracked snapshot when a number is computed
against it. The ruling stands on the narrower ground that the default artifact of an opt-in mode
never yet run is run output — and it now carries the condition that **no stability number may be
published from a gitignored artifact**, plus a refinement that the provenance header is written at
emit time rather than only on promotion.

**Also recorded**, beside the 313-absolute-paths item in `TRACK_A_SCOPE.md`:
`test_methods_finder.py:12` hardcodes the corpus directory, so its five tests run on one machine
rather than on any machine holding a corpus. Their never running in CI is fine and is now stated in
CONTRIBUTING; the machine-lock is the defect, and an env var skipped when unset removes it while
keeping the CI skip.

Commits: `76bd8bc` (the hook) and this entry. CI green on both jobs at `76bd8bc`, run
`37099247685` — which is also Phase 2's gate, met.
