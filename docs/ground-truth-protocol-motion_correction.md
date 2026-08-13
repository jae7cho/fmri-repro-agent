# Ground-truth protocol — `motion_correction` (v1.3)

**Ratified 2026-08-07 (ET):** all five original definitional calls (§5, CALLs 1–5) ratified by the author; this protocol was committed as pre-registration — *before any label is written*.

**Changelog**
- **v1 (2026-08-07):** CALLs 1–5 ratified; pre-registered before any label.
- **v1.1 (2026-08-08):** rules surfaced during labelling, recorded before labelling continued — CALL 1 refined (a package whose *module* IS the method → `named_tool`; a pipeline wrapping an unnamed third-party tool → `deferred`); a new **CALL 6** (blanket deferral applies to every bullet, not only bullet 1); a new **CALL 7** (deferral is per-row — a citation's scope is set by whether it *substitutes* for a row's description or *supports* one that is present), with CALL 6 reconciled as its wholesale special case (braun confirmed, viduarre softened to a candidate pending its full text); and the §7 co-adjudication note revised to describe the actual working method (candidate states proposed with same-model-family LLM assistance, author-ratified) and its reporting consequences. **v1.1 also edits a RATIFIED call:** CALL 5's flat viduarre `deferred` is softened to a *default* "pending the full-text check", because CALL 7's new bullet-level override may flip that bullet if viduarre describes its own resampling — CALL 5 (ratified 2026-08-07) had pre-assigned a bullet the later rules leave open. And `derosa` is removed from CALL 1's SPM-family pointer list (CALL 4 establishes derosa's only motion statement is ICA-AROMA, a different D.3 row), with a note clarifying the list is a pointer, not an assignment.
- **v1.2 (2026-08-11):** CALL 8 added — bullet 7 concerns slice-to-volume registration or STC integration as properties of the motion correction, not the occurrence of STC; six labels written under the wider reading are to be revised by the author.
- **v1.3 (2026-08-12):** CALL 8's stated-negative carve-out narrowed — a stated negative must concern the bullet's own subject; labels written under the narrow reading. agtzidis and ciric bullet 7 → `not_reported`; bullet 7 is now 0/19 across the corpus. The superseded carve-out text is retained under CALL 8 with a pointer.

**Status: PRE-REGISTRATION.** To be committed before any label is written; labels committed after. The
signed commit order is the pre-registration. Amendments get a new version and a stated reason, never a
silent edit. Single-rater, author-labelled (Jae Wook Cho) — a stated limitation; inter-rater reliability
deferred and conditional, as in base_pipeline v1.3 and target_space v1.2.

**Corpus:** the 19 analysable papers (cabral excluded, per base_pipeline D10).

**What is different about this field, and why it matters methodologically:** `motion_correction` is
**not extracted today** — it is absent from the extraction model, from `_FIELD_SPECS`, from the prompt,
and from `_assemble`'s emitted step list. So these labels are written before any extractor output for
this field exists. That is a stronger blindness than target_space had, where the protocol's definitional
calls were partly shaped by auditing extractor output. Extraction will be built *to this protocol*
rather than the protocol being written around extraction's behaviour.

**Honest qualification:** a deterministic grep survey of the corpus was run during scoping (tool-name
terms, QC terms). It surfaced which papers name a tool. That is not extractor output and is not the
thing being validated, but the labels are not blind to it. Stated rather than claimed away.

---

## 1. What COBIDAS actually requires (the denominator)

COBIDAS Report v1.0, Table D.3 "Preprocessing Reporting", the *Motion correction* row (Mandatory = Y).
Seven bullets, quoted in substance:

1. Name of software/method.
2. Use of non-rigid registration, and if so the type of transformation.
3. Use of motion susceptibility correction (fieldmap-based unwarping), and the software/method.
4. Reference scan (e.g. 1st scan or middle scan).
5. Image similarity metric (e.g. normalized correlation, mutual information).
6. Interpolation type (e.g. spline, sinc), **and whether image transformations are combined to allow a
   single interpolation**.
7. Use of slice-to-volume registration methods, or integration with slice time correction.

**Mapping to spec fields** (`MotionCorrection`, preprocessing.py:687-706):

| D.3 bullet | spec field(s) |
|---|---|
| 1 name of software/method | `method` |
| 2 non-rigid + transformation type | `nonrigid`, `transform_type` |
| 3 fieldmap unwarping + software | `fieldmap_unwarping`, `unwarping_method` |
| 4 reference scan | `reference_scan` |
| 5 similarity metric | `similarity_metric` |
| 6 interpolation + combined transforms | `interpolation`, **`transforms_combined` (NEW)** |
| 7 slice-to-volume / STC integration | `slice_to_volume` |

All seven bullets map. `transforms_combined` does not exist in the spec today — it is added as part of
this arc (COBIDAS-mandated, and attested in-corpus by poldrack).

**Labelling is at the BULLET level** (seven items), because the bullet is COBIDAS's unit of obligation
and the compliance table is the Goal-2 deliverable. The field mapping is recorded so extraction can be
built against it later.

---

## 2. Scope: label seven, build one

- **`method` (bullet 1) is labelled at full rigour** — state, verbatim value, supporting quote — because
  it is the only bullet getting extraction in this arc, and therefore the only one that will be
  **scored** against the extractor.
- **Bullets 2-7 are labelled as attestation only** — did the paper report this, with the verbatim if so.
  Most are absent (scoping survey: reference scan ~4/19, similarity metric ~0, interpolation ~0), so
  this is fast.

**These are different kinds of claim and must not be conflated.** The `method` labels support an
extractor-accuracy claim once extraction exists. The bullet 2-7 attestations support a **literature**
claim — item-by-item COBIDAS reporting completeness across the corpus — backed by author labels and
independent of any extractor. The second is arguably the more useful output for Goal 2, and it is
available without building six more extraction fields.

---

## 3. Label vocabulary

### `method` (bullet 1) — five states

- **`named_tool`** — a specific software or method is named: MCFLIRT, SPM realign, AFNI 3dvolreg, ANTs,
  INRIAlign, FLIRT.
- **`described_only`** — the operation is stated but no tool is named: "motion correction was
  performed", "rigid body realignment". Performance is established; the tool is not.
- **`deferred`** — the method is not stated but is attributed elsewhere: to a citation, or to a named
  pipeline whose motion step the paper does not itself describe. Consistent with base_pipeline v1.3's
  named-by-provenance rule.
- **`absent`** — the paper makes no statement about motion correction at all.
- **`stated_not_performed`** — the paper explicitly states it did not perform motion correction. (No
  corpus instance expected; the state exists because explicit negative reporting is the reproducibility
  gold standard and must be representable — see §5, CALL 5's sibling problem.)

### Bullets 2-7 — four attestation states

- **`reported`** — the bullet is addressed, **including an explicit negative**. "No fieldmap-based
  unwarping was applied" *satisfies* bullet 3; a stated negative is reporting, not silence. Record the
  verbatim.
- **`not_reported`** — silent.
- **`not_applicable`** — the bullet is malformed for this pipeline's design. See CALL 5 (one-step
  resampling and `interpolation`).
- **`deferred`** — addressed only by attribution to a citation or named pipeline.

---

## 4. Performance determination (feeds the compliance rendering)

The three-state compliance rendering (see the amended `DESIGN_cobidas_coverage.md`) needs performance
established **from the paper's own text**, never from a prior about which steps are universal.

- **performed** — `method` ∈ {`named_tool`, `described_only`, `deferred`}
- **not performed** — `method` = `stated_not_performed`
- **indeterminate** — `method` = `absent`

Note this is why `described_only` must be a distinct state rather than collapsing into `absent`: a paper
that says "motion correction" and nothing else has *established performance* while reporting no
parameters. That is the population where non-compliance is assertible.

---

## 5. The definitional calls (CALLs 1–5 ratified 2026-08-07; CALLs 6–7 added v1.1 2026-08-08; CALL 8 added v1.2 2026-08-11, narrowed v1.3 2026-08-12)

### CALL 1 — a citation that identifies the method is `deferred`, not `named_tool`
**RATIFIED: deferred.** oconnor states "motion correction" and cites Jenkinson et al. (the MCFLIRT paper).
The *paper* wrote "motion correction", not "MCFLIRT"; producing the tool name would require resolving
Jenkinson 2002 — which is the citation resolver's job, with its own provenance and confidence
(base_pipeline D1: citation-deferral → DEFERRED, no genre test for citations). Label what the paper
stated; resolution is resolution.

**Refinement (v1.1) — package vs wrapper.** Naming a package whose *module* IS the method counts as
`named_tool`; naming a pipeline that *wraps* an unnamed third-party tool is `deferred`. agtzidis —
"performed with SPM12 … realigning the functional data to the mean image of each session" → `named_tool`:
SPM's Realign module *is* the method; nothing is hidden behind the package name. oconnor — "C-PAC … motion
correction" citing Jenkinson → `deferred`: C-PAC is a wrapper; the motion tool it calls is never named in
the paper. This governs the SPM-family papers (mueller, gordon, tang, wheaton) and the C-PAC/CCS
papers (oconnor, weber, vanderwal, chen), so it must be **explicit, not tacit**. This list is a **pointer**
to which papers the rule will likely govern, not an assignment — every paper is labelled from its own text.
(derosa is deliberately absent: CALL 4 establishes its only motion statement is ICA-AROMA, a different D.3
row, so the package-vs-wrapper rule does not decide its `method`.)

**`deferred` is not a reporting failure.** Under `DESIGN_cobidas_coverage.md` §2, a D.3 row is addressed
iff a field is `EXTRACTED` **or** `DEFERRED_TO_CITATION` — so oconnor satisfies D.3 bullet 1 by deferral
and counts as *reported* in the compliance table. Compliance and label state are different axes.

*Limitation:* the state does not distinguish deferral targets of very different reproducibility value —
oconnor's resolves to a specific tool, braun's ("as previously described in refs. 47 and 48") to another
paper's prose. The verbatim quote preserves *which* citation, so this is assessable downstream; recorded
as the deferral-reproducibility problem already tracked in `docs/findings/citation-index-backlog.md`. No
new state.

### CALL 2 — realignment described as "coregistration" is still `motion_correction`
**RATIFIED as drafted.** The discriminator is **what is aligned to what**, not the word used. EPI volumes
aligned to each other, or to a within-run reference → **`motion_correction`**. EPI aligned to the
anatomical → **`coregistration`**, a different step.

Worked cases: binder — "All EPI images were spatially coregistered using an iterative procedure that
minimizes variance in voxel intensity differences between images (Cox, 1996b)": "**between images**"
(plural, within the timeseries) is the operative phrase → `motion_correction`. The anatomical only enters
later, when the SPGR scans and SPMs are projected to stereotaxic space; binder describes **no func→anat
coregistration step at all** — so reading this sentence as coregistration would leave a paper that
realigned its timeseries with no motion correction anywhere. liu_2013 — "image coregistration to correct
for head motion" — the stated purpose is motion.
**CALL 2a — RATIFIED: binder = `described_only`.** The general test it establishes: *does the paper's own
text identify the method, or must the citation be read to know what was done?* Binder characterises the
algorithm in-paper (iterative, minimising variance in voxel intensity differences between images) →
`described_only`. oconnor gives only the operation name plus a pointer → `deferred`. So `described_only`
spans a range of detail — from cole's bare "motion correction" to binder's characterised algorithm — and
the difference lives in the verbatim quote, not in the state.

*Verification flag:* **Cox 1996b is not identified.** Cox 1996a is the AFNI software paper; 1996b is a
different work of the same year and has NOT been verified. Do not assume it is a volume-registration paper.

### CALL 3 — the realignment step is distinct from the motion parameters it feeds to nuisance regression
**RATIFIED as drafted.** Six papers describe both in one sentence (ciric, gordon, agtzidis, chen, poldrack, liu_2013).
- The **transform applied to the data** → `motion_correction.method`
- The **parameters used as regressors** → `nuisance_regression` (COBIDAS D.3 row *Artifact and
  structured noise removal*, which explicitly covers motion-parameter regressors and their expansion)

Worked case: ciric — MCFLIRT realignment → `motion_correction.method = named_tool (MCFLIRT)`; "six
realignment parameters returned by MCFLIRT" used as regressors → `nuisance_regression`, not here.
Friston-24 (ciric, chen) is nuisance, never motion_correction.

### CALL 4 — label by what the operation IS, not what the paper calls it
**RATIFIED as drafted.** derosa describes "motion correction via ICA-AROMA". ICA-AROMA is ICA-based denoising — the spec has
`ica_denoise`, and COBIDAS files it under *Artifact and structured noise removal*. It is not
realignment. So derosa's ICA-AROMA does not populate `motion_correction.method`; whether derosa's
`method` is `described_only` or `absent` depends on whether realignment per se is stated anywhere in its
full text (the scoping survey found it "not clearly stated" — **read the full methods before
labelling**).

### CALL 5 — one-step resampling: `interpolation` is `not_applicable`, `transforms_combined` is `reported`
**RATIFIED as drafted.** Where a pipeline composes motion, distortion, and registration transforms into a single interpolation,
there is no motion-specific interpolation to report — the question is malformed for that design, which
is different from silence.
Worked case: poldrack — "The transforms for head motion correction and affine registration to atlas
space were combined with the field-map-based distortion correction to resample the data … in a single
step using FSL's applywarp tool." → bullet 6: `interpolation` = `not_applicable`,
`transforms_combined` = `reported`. Note this makes poldrack *more* compliant on bullet 6 than a paper
that reports neither.
HCP-lineage papers (Glasser 2013 §fMRIVolume: all transforms concatenated, "a single spline
interpolation, minimizing interpolation-induced blurring") behave the same; viduarre defers to Glasser
and therefore defaults to `deferred` rather than `not_applicable`, pending the full-text check (CALL 6).
**This is the third field in which not-applicable and absent have had to be distinguished**
(after target_space's CALL 7 and the study_specific/native_volume split). Recorded as a recurring
structural need, not a motion quirk.

### Why named vs unnamed is labelled, even if the tools are near-equivalent

COBIDAS bullet 1 asks for the **name of software/method**, so a protocol that collapsed `named_tool` and
`described_only` would make bullet 1 unreportable and remove the first row of the compliance table.

Separately, tool identity is not only an image-similarity question: implementations differ in cost
function, interpolation kernel, and reference-volume default, so the **estimated motion parameters**
differ — and six corpus papers feed those parameters into nuisance regression, with FD derived from them
driving censoring thresholds. Different estimates → different regressors and different frames censored,
even where the realigned volumes look alike. This is why D.3 asks for similarity metric and interpolation
as separate bullets. (Mechanism, not magnitude — no specific comparison study is cited, as none has been
verified.)

### CALL 6 — blanket deferral applies to every bullet, not only bullet 1
**Added v1.1 (2026-08-08).** Where a paper defers preprocessing wholesale without describing any step,
every D.3 bullet for that row is `deferred` — **not** `not_reported`. This is the **special case of CALL 7**
in which the citation substitutes for *every* row — nothing is described anywhere in the paper.

Rationale: the label records **what the paper did**. braun ("Data were preprocessed according to standard
protocols as previously described in refs. 47 and 48") did not omit the similarity metric; it pointed
elsewhere for all of it. Marking bullets 2–7 `not_reported` would make braun indistinguishable from a
paper that described its preprocessing and omitted those items — a different reporting behaviour. Whether
a blanket deferral *satisfies* COBIDAS is a compliance question for the rendering layer
(`DESIGN_cobidas_coverage.md` §A), not a labelling one — consistent with the project's discipline of
labelling what was stated and leaving adequacy to interpretation. `deferred` is already a bullet-state
value (§3); this call states when it applies to the whole row.

**Confirmed instance:** braun — verified wholesale: no preprocessing step is described in the paper's own
voice, and everything after "After preprocessing" is analysis.

**Candidate (not confirmed):** viduarre — its "the procedure described by Glasser et al." defers the
pipeline rows, but whether the paper describes anything in its own voice has not been checked against its
full text. To be determined when viduarre is labelled; **do not pre-assign**.

### CALL 7 — deferral is per-row; a citation's scope is set by what it does in the sentence
**Added v1.1 (2026-08-08).** Deferral is decided **per D.3 row**, not per paper, and a citation's scope is
set by what it does in the sentence.

**The test: does the citation SUBSTITUTE for a description of that row, or SUPPORT one that is present?**
- **Substitutes** → that row is `deferred`.
- **Supports** → not a deferral; label from the description.

Worked cases (all from corpus text):
- **agtzidis, dataset citation:** "we used the publicly available studyforrest data set … for full
  experimental details, we refer to the paper presenting the original data set (Hanke et al., 2016)"
  substitutes for **acquisition** and design, not preprocessing — agtzidis describes its own preprocessing
  in its own voice. The motion row is **not** deferred. *A citation's scope does not extend to rows the
  paper describes itself.*
- **agtzidis, supporting citation:** "we initially followed a standard preprocessing pipeline (Poldrack
  et al., 2011). The process comprised realigning…" — the citation supports an enumerated pipeline, so
  `named_tool` stands. Had the paper **not** enumerated, the same phrasing would substitute.
- **binder:** the Cox (1996b) reference supports a described algorithm → `described_only`, per CALL 2a.
- **braun:** "preprocessed according to standard protocols as previously described in refs. 47 and 48"
  substitutes for **every** preprocessing row — the wholesale case CALL 6 governs.
- **Pipeline citations do double duty.** Glasser 2013 describes both a dataset and a preprocessing
  pipeline, so "HCP minimally preprocessed data (Glasser 2013)" substitutes for the minimal-pipeline rows
  — motion included. This is why the test cannot key on what **kind** of work is cited (dataset vs
  pipeline) but only on what the citation is *doing*.
- **Mixed case, the general form:** "HCP minimal preprocessing (Glasser 2013), then nuisance regression
  following Power et al." → the motion row is `deferred` to Glasser; the artifact/noise row is deferred to
  Power, or `named_tool` if the paper describes the method. Two rows, two independent scopes, one paper.
- **Do not conflate on a shared name:** "HCP minimal preprocessing plus ICA-FIX" defers motion to Glasser
  while naming a method for artifact/noise removal. "HCP" appears in both; the rows are unrelated. Same
  discipline as CALL 4 (label by what the operation IS).

**Bullet-level override:** when a row is `deferred`, its bullets default to `deferred` — but a bullet the
paper states explicitly is `reported`, overriding the row default (e.g. a paper deferring to HCP that
nonetheless names its reference scan).

### CALL 8 — bullet 7 is about the MOTION CORRECTION, not the occurrence of slice-time correction
**Added v1.2 (2026-08-11).** D.3 bullet 7 reads: *"Use of any slice-to-volume registration methods, or
integrated with slice time correction."* Both clauses are properties **of the motion correction**:
(a) was motion estimated **per-slice** rather than per-volume (slice-to-volume registration); or
(b) were motion correction and STC solved as **one integrated operation** rather than sequentially.
**Whether the paper performed STC at all is a different D.3 row** (`slice_time_correction`), with its own
bullets. A sentence listing STC and motion correction as separate sequential steps addresses **neither**
clause of bullet 7.

Worked cases (all currently mislabelled `reported`):
- **cole:** "we performed slice timing correction, motion correction, …" — a list of steps performed; says
  nothing about slice-level estimation or integration → `not_reported`.
- **gordon:** "Images were then slice-time corrected," → `not_reported`.
- **chen:** "corrected acquisition timing among image slices" → `not_reported` (two sequential operations,
  no integration stated).

**The narrow exception — a stated absence of STC forecloses integration:** *(SUPERSEDED by the v1.3
amendment below — agtzidis and ciric are `not_reported`, not `reported`. Text retained for the record.)*
- **agtzidis:** "(without slice timing correction)" and **ciric:** "We did not apply slice timing
  correction during preprocessing…" → `reported`. If no STC was performed there is nothing to integrate,
  so clause (b) is settled by the paper's own statement — consistent with the protocol's existing rule
  that a stated negative counts as `reported`.

*Expectation:* slice-to-volume registration is a rare technique (fetal/infant work); the scoping survey
found **zero** corpus instances. This bullet is expected to be near-empty — that near-emptiness is a
**finding about the standard**, not a labelling failure. A high `reported` rate on bullet 7 is a signal
the bullet is being **misread**.

**Amendment (v1.3, 2026-08-12) — the stated-negative carve-out is narrowed.** The exception above is
superseded. The stated-negative rule applies only when a paper states a negative **about what the bullet
asks**. Bullet 7 asks about properties of the **motion correction** — slice-level estimation, or fusion
with STC. "We did not apply slice timing correction" is a statement about a **different step**
(`slice_time_correction`); that its absence leaves nothing to integrate is an **inference** from the
statement, not the statement itself. Bullet 7 is therefore **`not_reported`** for agtzidis and ciric.

Contrast, to keep the rule non-arbitrary: power_2014's "rigid body realignment to correct for head
movement" **is** a direct statement about the motion correction's own transform type — exactly what
**bullet 2** asks — so it is correctly `reported`. The distinction is whether the statement is **about the
bullet's subject**, not whether an answer can be *derived* from it.

Secondary ground: agtzidis and ciric carry **no verbatim** for bullet 7, so `reported` would fail §6's
verbatim requirement regardless of the reading.

**Result:** bullet 7 is **0/19** across the corpus — the near-empty outcome CALL 8 already anticipated.
COBIDAS asks whether motion correction used slice-to-volume registration or was integrated with STC; **no
corpus paper addresses either**.

---

## 6. Labelling procedure

1. **Label from the full paper** — methods, figure captions, supplement. Do **not** rely on term search.
   The scoping survey missed wheaton's "motion correc-tion" (pypdf hyphenation across a line break) and
   would have recorded a false absence. Same pypdf-mangle family as the agtzidis `/C2` and cole `AFNI48`
   defects.
2. Label `method` first (it determines performance), then bullets 2-7.
3. Record a **verbatim quote** for every `named_tool`, `described_only`, `deferred`, and every
   `reported` bullet. For `not_applicable`, record the quote establishing the design (poldrack's
   single-step sentence).
4. `Value` column convention (inherited from target_space v1.2): the **verbatim term** when the paper
   names one; blank otherwise, with Notes carrying the adjudication.
5. If a paper does not fit these states, the protocol is incomplete — amend, bump the version, re-commit,
   *then* label. Do not force it.

## 7. Inter-rater reliability

Single-rater (author). The labels are not independent of the system's developer, and this is a stated
limitation, not a resolved one. A second or panel rater and κ are deferred, conditional on pursuing
publication. If added, raters work from this protocol alone, blind to author labels and to extractor
output.

### Co-adjudication (v1.1)

Candidate sentences were located and states **proposed with LLM assistance of the same model family as the
extractor** (claude-sonnet-4-5); the **author reviewed and ratified every state**. The papers worked through
jointly so far are **agtzidis_2020, braun_2015**.

This is a **stronger contamination risk** than clarification-only assistance, and is **stated rather than
mitigated**. Ground truth partly produced by the model under evaluation inflates agreement in a way no
downstream check can detect. It is the same limitation target_space v1.2 recorded for its pre-registered
adjudications — stated, not resolved.

**Consequence for reporting:** the `method` accuracy figure must carry this caveat **prominently, not in a
footnote** — it is materially weaker evidence than the base_pipeline figure, whose labels were
author-produced.

The **bullet 2–7 attestation table is far less exposed**: "did the paper state a similarity metric" is
close to a factual read with little adjudication room. That table — the item-by-item COBIDAS
reporting-completeness finding — is the **Goal-2 deliverable** and stands largely independent of this
limitation.

**Per-row `co-adjudicated` flags in Notes remain required**; name **every** paper worked through jointly,
not only the contested ones.

## 8. What this produces

Two distinct outputs, not to be merged:

1. **An item-by-item COBIDAS reporting-completeness table** for the *Motion correction* row across 19
   papers — a literature finding, backed by author labels, independent of extractor accuracy. Expected
   shape from the scoping survey: bullet 1 attested densely, bullets 4-7 sparsely or not at all.
2. **A scored `method` accuracy figure** once extraction is built — with Wilson intervals, an error
   decomposition by named class, and the reachability/corruption partitioning established in the
   target_space arc.

Neither is a compliance *verdict*. Non-compliance is asserted only where the paper's own text
establishes the step was performed and a mandated sub-item is unreported — the *performed and
underreported* state in the amended coverage design.
