# Ground-truth protocol — `spatial_normalization.target_space` (v1.1 — all 5 calls ratified; CALL 4 dual-axis + CALL 5 `deferred` state resolved)

**Status: PRE-REGISTERED.** Committed before any label is written; labels committed before any scoring
run. The signed commit order is the pre-registration. Amendments get a new version + stated reason,
never a silent edit. Single-rater, author-labeled (Jae Wook Cho) — a stated limitation; inter-rater
reliability deferred and conditional, exactly as base_pipeline v1.

**v1.1 amendments (2026-07-27) — stated reason, per the never-a-silent-edit rule.** Three changes,
each ratified against independently-verified full-text evidence (poldrack read in full; base_pipeline
label + rule confirmed; Conte69 framing corrected):
1. **CALL 4 (dual-axis) RATIFIED** in its narrow form: completeness is reported PER AXIS, and a paper
   is exempt from a volumetric reporting-gap ONLY under the conjunction "volumetric target unnamed
   in-paper AND volumetric analysis units individually-defined." The headline is therefore TWO
   distributions plus a joint statement, not one number over 20 papers.
2. **CALL 5 RESOLVED to Option A**: a sixth state, **`deferred`**, is added — mirroring base_pipeline
   v1.3's named-by-provenance rule, so `absent` and `deferred` stay distinct reproducibility facts.
3. **poldrack volumetric SUPERSEDED `absent` → `deferred`** (not a silent edit; the v1 `absent`
   ratification is explicitly retired in CALL 5 below). Its atlas is named only by provenance ("a
   pipeline developed at Washington University, St Louis⁴⁵") — deferred, identity unresolved.

Carry-forward (NOT acted on in v1.1): the weber "Conte69" surface flattening is logged for a later
synonym-resolver fix; independent verification corrected its earlier framing (it is NOT an enum gap and
NOT oconnor-class — see the Carry-forward section).

**Field:** `spatial_normalization.target_space` — the **volumetric** normalization target of the
functional pipeline. Reports the completeness with which a paper specified the stereotactic space its
functional data were normalized to.

**Corpus:** the same 20 PDFs. Denominator handling per base_pipeline (cabral excluded).

**Relationship to base_pipeline protocol:** this reuses that protocol's machinery — the status
vocabulary shape, verbatim-quote requirement, blind labeling, the three-way partition (extraction /
slicing / correct) — applied to a field with a SIX-state value space instead of a name.

---

## Why this field, and the stakes (read first)

The submitted SfN abstract's headline ("13/20, 65%, could not be resolved to a canonical
specification") was a single-draw, unscored extractor count that **conflated three different reporting
behaviors** into one "unresolvable" bucket. A full-text audit of the 20 papers decomposed it:
- ~2 genuinely vague ("atlas space", no template),
- ~7 named the MNI family without a machine-readable variant (era-standard, not vague),
- ≥1 (oconnor) named a specific resolvable template FILE that the extractor flattened to "MNI".

The reframe (committed) replaced "resolve/fail" with a **specification-completeness distribution**:
Canonical / Family-specified / study_specific / native_volume / Absent (the extractor's five output
buckets; the v1.1 LABEL vocabulary adds a sixth state, `deferred`, for provenance-named targets — see
CALL 5). This protocol builds the GROUND TRUTH that turns that distribution from extractor output into a
scored, defensible finding — the number presented in November. The evidence for every definitional line
below comes from the full-text audit, not assumption.

---

## The six states (label vocabulary)

Label the VOLUMETRIC target_space in exactly one state:

- **`canonical`** — the paper named a specific, resolvable template: a variant identifier
  (MNI152NLin6Asym, MNI152NLin2009cAsym), OR a specific template FILE that resolves to one by
  established identity (oconnor: "FSL's MNI152T1_2mm_brain.nii.gz" → MNI152NLin6Asym; FSL ships
  NLin6Asym — verified vs FSL docs + TemplateFlow + Lead-DBS), OR Talairach with its atlas.
- **`family_specified`** — the paper named the MNI family (or a tool-generic MNI reference) WITHOUT a
  resolvable variant: "MNI", "MNI152", "MNI standard space", "SPM's MNI template", "MNI-152 12-dof
  linear". Real, era-standard specification; adequate for typical cortical/large-scale analysis
  (nonlinear registration absorbs the variant difference — Dice separation across MNI152 variants
  ≤~0.02, largest only in small subcortical/midline structures); under-specified only for
  subcortical-precision/coordinate work. **Not a failure — a completeness tier.**
- **`study_specific`** — the paper normalized to a template CONSTRUCTED for this study
  (developmental/cohort/precision; mueller: "subject-specific anatomical template created using ANTs
  multivariate template construction"). A specified methodological choice, dataset-bound.
- **`native_volume`** — no volumetric normalization; functional data kept in each subject's own
  volumetric space (a deliberate choice, common in precision imaging). Distinct from study_specific
  (which DOES normalize, to a constructed template) and from Absent (which reports nothing). NB: a
  paper that resamples into an (even unnamed) common atlas grid is NOT native_volume — see CALL 4.
- **`deferred`** — the paper names no volumetric target itself, but attributes its pipeline (and thus
  its normalization target) to a cited work or a named-by-provenance pipeline, so the target plausibly
  lives in that citation — **identity UNRESOLVED**. Distinct from `absent` (nothing reconstructable
  anywhere) and from `canonical`/`family_specified` (which require an in-hand named target). Mirrors
  base_pipeline v1.3's `DEFERRED_TO_CITATION` under its named-by-provenance rule. poldrack: "a pipeline
  developed at Washington University, St Louis⁴⁵" → `deferred`, not `absent` (and possibly multi-hop —
  ref 45 is a motion-methods paper that may itself defer the atlas onward). A `deferred` label asserts
  NO specific template; do not resolve it — that is the citation-resolver's downstream job.
- **`absent`** — the paper states no reconstructable volumetric target at all AND does not defer to a
  cited pipeline for it: "atlas space" / "standard space" with no template named, or silence. Contrast
  `deferred` (the target is named only by provenance / in a cited work).

---

## The three definitional calls (the audit surfaced these; they are the hard lines)

### CALL 1 — target_space is VOLUMETRIC ONLY; surface targets are a separate field
`fsaverage5`, `Conte69`, `fsLR`, and other SURFACE templates are NOT target_space values — they are a
different normalization axis (`target_surface`). A paper can specify a volumetric target, a surface
target, both, or neither, independently.
- chen ("MNI space" volumetric + "fsaverage5" surface) → target_space = **family_specified** (on the
  volumetric "MNI"); its fsaverage5 is scored in `target_surface`, NOT here.
- weber ("MNI152 space" + "Conte69" surface) → target_space = **family_specified**; Conte69 → surface.
- The audit CONFIRMED this: fsaverage5/Conte69 were flagged as "specificity signals" but adjudicated to
  the surface axis — labeling them as target_space would misrepresent a surface template as a
  volumetric one.
**Rule:** target_space records ONLY the volumetric stereotactic target. Surface templates belong to
`target_surface` and are out of scope for this protocol. A surface-based paper that ALSO states a
volumetric target is labeled on that volumetric target; a purely-surface paper with no volumetric
target is `absent` (or `deferred`) on target_space (see CALL 3 for the native-vs-absent boundary if it
kept volume in native space).
**RATIFIED (author, verified):** `target_surface` IS a distinct spec field; surface templates route
there. **VERIFIED AT HEAD (2026-07-27, direct grep + 6-agent adversarial check): `target_surface` is
EXTRACTED, not schema-only.** All four legs are wired: (a) spec field
`target_surface: ProvenancedField[TargetSurface]` on the `SurfaceProjection` step
(`src/fmri_repro/spec/preprocessing.py:844`; `TargetSurface = Literal["native", "fsaverage",
"fsaverage5", "fsaverage6", "fsLR_32k", "fsLR_164k", "other"]`); (b) a REQUIRED (no-default)
extraction-model field `target_surface: FieldExtractionResult`
(`extractor_mvp/src/extractor_mvp/extractor.py:86`); (c) a prompt stanza asking for the surface target
(`extractor.py:221-228`); (d) genuine build-path population (`_FIELD_SPECS` 400-406 → extraction loop
929-941 → `_assemble` 827-832 builds `SurfaceProjection(target_surface=pf["target_surface"])`), with no
hard-coded default. K=3 cached inspection confirms it fires: poldrack → `fsLR_32k` (span: "164k fs LR …
downsampled to a 32,492 vertex surface (fs LR 32k)"), chen → `fsaverage5`. So **CALL 4's dual-axis
reporting IS computable.** (One surface-axis flattening — weber's "Conte69" — is logged in the
Carry-forward section, corrected: it is a synonym-resolver gap, not an enum gap.)

### CALL 2 — canonical vs family_specified: does the reference resolve to a SPECIFIC template?
The boundary is resolvability to a specific variant/file, NOT how "official" the name sounds.
- **canonical**: names a specific resolvable template — a variant identifier, or a template FILE that
  resolves by established identity (oconnor's FSL file).
- **family_specified**: names the family via bare term OR via a tool, but not a resolvable variant.
  - wheaton "SPM MNI template" → **family_specified for now; OPEN QUESTION.** Author's position: a
    user CAN trace SPM's MNI template (SPM99 + "MNI template" identifies the file SPM99 shipped), which
    argues for canonical. Counter-consideration (UNVERIFIED, needs checking before promotion): SPM's
    bundled template differs by SPM version, and older SPM templates may derive from the *linear*
    ICBM152 rather than the nonlinear 6th-gen — for which `TargetSpace` currently has NO enum value.
    Promoting wheaton to canonical therefore requires (a) verifying which template SPM99 actually
    shipped and (b) possibly adding a linear-MNI152 enum value (an additive patch bump under the new
    versioning convention). **Until verified, label family_specified and record the open question.**
    Do not promote on the strength of "traceable" alone — traceable-to-a-file is not the same as
    resolvable-to-an-enum-value.
  - derosa "MNI-152 template, 12-dof linear" → **family_specified**. Names the family + the transform
    d.o.f., but not a variant identifier or file.
**Rule:** canonical requires a reference that resolves to ONE specific template (variant or file).
A family term, or a tool-generic MNI reference, is family_specified. When unsure whether a reference
resolves, it is family_specified (canonical is the stricter claim; do not over-credit).

### CALL 3 — family_specified / native_volume / absent / deferred: the low-specification boundary
- Named the MNI family (bare) → **family_specified** (they told you the family).
- No volumetric template, functional data explicitly kept in native/subject volumetric space →
  **native_volume** (a stated choice — "no normalization" is itself specification).
- No template named in-paper, but the pipeline (hence the target) attributed to a cited/provenance-named
  work → **deferred** (the target lives in the citation; identity unresolved — see CALL 5).
- "atlas space" / "standard space" with NO template named and NO deferral, or silence → **absent**
  (nothing reconstructable; they gestured at normalization without saying to what).
  - power ("resampled in atlas space on an isotropic 3mm grid") → **absent**. "Atlas space" names no
    template — it is a gesture, not a target. The resolution (3mm) is a SEPARATE field
    (`resolution_mm`); do not let a stated resolution upgrade an absent target.
  - poldrack ("affine registration to atlas space", atlas never named, pipeline deferred to a cited
    WashU pipeline) → **deferred**, not absent (v1.1; see CALL 4 / CALL 5).
**Rule:** the boundary is whether a TEMPLATE (family or specific) was named, or DEFERRED to a citation.
Family named → family_specified. No template but native space stated → native_volume. No template but
pipeline attributed to a cited work → deferred. No template, no native statement, no deferral → absent.
A resolution or d.o.f. without a template does NOT make it family_specified — target_space is about the
SPACE, not the resolution.


### CALL 4 — DUAL-AXIS: report completeness PER AXIS; exempt a paper from an axis only where it demonstrably did not use that axis as its analysis target **[RATIFIED v1.1 — narrow form]**
A surface-based pipeline normalizes to a SURFACE template, not a volumetric one. Judging such a paper on
`target_space` alone can mark it `absent`/`deferred` and read as a reporting failure — when its actual
analysis target was specified exhaustively on the surface axis. But the exemption MUST be narrow, or it
degrades into "any surface specification excuses volumetric silence," which would wrongly excuse chen
and weber (below).

**The ratified rule.** Completeness is reported PER AXIS (`target_space` volumetric; `target_surface`
surface). A paper is exempt from a volumetric reporting-gap ONLY under the CONJUNCTION:
(i) its volumetric target is unnamed in-paper (so its volumetric label is `absent` or `deferred`), AND
(ii) its volumetric analysis units are individually-defined rather than read from a named volumetric
atlas (e.g. CIFTI grayordinates + subcortical regions selected from the subject's OWN FreeSurfer
segmentation). The warrant is the CONJUNCTION — never "surface-based / CIFTI paper ⇒ volumetrically
exempt." A paper that NAMES a volumetric template is `family_specified` volumetrically and earns NO
exemption regardless of also building CIFTI or using individual subcortical segmentation.

**poldrack_2015 is the worked case (full text read; warrant independently verified 2026-07-27):**
- *Volumetric*: registers each session to a prior session "previously … registered to … an atlas,"
  inverts the "session-to-atlas transform," and resamples to "the undistorted 3-mm isotropic atlas
  space" via FSL `applywarp`. **The atlas is never named**, and the pipeline is attributed by
  provenance ("a pipeline developed at Washington University, St Louis⁴⁵") → **`deferred`** on
  target_space (v1.1; supersedes v1's `absent` — see CALL 5). The 3mm is `resolution_mm`, not the space.
- *Surface (the analysis target)*: individual native surface → fsaverage → 164k fs_LR (Caret) → **32k
  fs_LR** (32,492 vertices); BOLD ribbon-sampled to native mid-thickness (Connectome Workbench 0.7),
  one-step resampled to 32k fs_LR, smoothed on-surface (σ=2.55). **canonical-grade surface
  specification.**
- *Why the conjunction holds*: the CIFTI subcortical/cerebellar grayordinates AND the 14 subcortical
  regions are **selected from the INDIVIDUAL subject's FreeSurfer segmentation/parcellation**, not from
  any atlas-space parcellation, and no reported analysis output depends on the unnamed atlas as a
  target. **Honest caveat (do not overstate):** the BOLD *is* resampled into the unnamed 3-mm atlas
  space as a common registration SUBSTRATE — poldrack did NOT stay in native volume (so it is NOT
  `native_volume`). The exemption is from the *reporting-gap*, reconciled by individually-defined
  volumetric units — NOT a claim that no volumetric normalization occurred.

So poldrack's honest record is **volumetric: `deferred` (identity unresolved) · surface: 32k fs_LR
(canonical)**, and it does not count as a volumetric reporting failure — because its volumetric analysis
units are individually defined, not because it "used a surface."

**Reporting consequence (ratified).** The headline CANNOT be a single number over 20 papers. It is TWO
distributions — a volumetric completeness distribution and a surface completeness distribution — PLUS a
joint statement, and papers appear in BOTH. chen ("MNI" + fsaverage5) and weber ("MNI152" + Conte69) are
`family_specified` on the volumetric distribution AND specified on the surface distribution; neither gets
credit-by-substitution across axes. The DEPENDENCY (is `target_surface` extracted?) is RESOLVED —
verified at HEAD to be genuinely extracted (see CALL 1) — so both distributions are computable now.

### CALL 5 — `deferred` state **[RESOLVED v1.1 — Option A: added]**
poldrack attributes its whole pipeline to provenance + citation ("a pipeline developed at Washington
University, St Louis⁴⁵"), which is why base_pipeline labeled it `DEFERRED_TO_CITATION` under its v1.3
named-by-provenance rule. The unnamed "atlas" plausibly lives in that citation (ref 45 = Power et al.
2014, the WashU/Petersen pipeline; possibly multi-hop; ref 46 = Jenkinson/FSL is only the `applywarp`
tool, not the atlas target). base_pipeline (committed) labels this same construct `DEFERRED` — so forcing
it to `absent` here would CONTRADICT a committed protocol on the same paper.

**Decision: Option A — `deferred` is added as the sixth state** (definition above). `absent` (nothing
reconstructable anywhere) and `deferred` (named only in a cited work) are different reproducibility
facts, and that distinction is the spine of the four-state provenance model AESPA is built on; a
target_space vocabulary narrower than base_pipeline's would be an inconsistency to explain rather than
one to want.

**Supersession (not a silent edit):** poldrack's v1 volumetric ratification of `absent` is RETIRED;
poldrack volumetric = `deferred` in v1.1. A `deferred` label asserts no specific template — resolving
the citation is the downstream citation-resolver's job, not a labeling state. `deferred` rests on
PLAUSIBILITY (the target lives in the cited pipeline), not on a resolved atlas identity; do not assert
MNI / Talairach / a specific WashU template for poldrack.

---

## Labeling procedure (mirrors base_pipeline)

1. **Label blind.** Do not open extractor output or the reframed distribution before deciding each
   paper. The denominator must be independent of the tool being measured.
2. Read the **full paper** (methods, captions, supplement where present) — the audit showed surface
   signals and specific files live outside the one sentence the model quoted.
3. Record a **verbatim quote** for every non-absent label (the sentence stating the volumetric target,
   or the sentence deferring the pipeline to a citation). For canonical, the quote must contain the
   specific variant/file. For absent, note the gesture ("atlas space") or that nothing was stated.
4. Fill per paper: `target_space_state` (one of the six), `value` (the verbatim target as written —
   "MNI", "FSL's MNI152T1_2mm_brain.nii.gz", "atlas space"; for deferred, the cited work/provenance),
   `supporting_quote`.
5. If a paper doesn't fit the six states, the protocol is incomplete — amend, bump version, re-commit,
   THEN label it. Do not force it.

## Known adjudications (from the full-text audit — pre-recorded so labeling is consistent)

canonical: oconnor (FSL file). study_specific: mueller (ANTs constructed template). family_specified:
agtzidis, chen, derosa, liu_2013, tang, vanderwal, weber, wheaton, gordon (bare/family/tool-generic MNI
or "EPI template"). absent (volumetric): power ("atlas space", no template named, no deferral).
deferred (volumetric): poldrack — atlas never named in-paper, pipeline attributed by provenance to a
cited WashU pipeline ("Washington University, St Louis⁴⁵"); v1.1 supersedes v1's `absent` (see CALL 5),
consistent with base_pipeline's `DEFERRED`. Per CALL 4, poldrack's surface target is canonical (32k
fs_LR) and it does NOT count as a volumetric reporting failure (its volumetric units are
individually-defined). [The remaining papers labeled per their full text; braun/cabral/ciric/liu_2005/
viduarre were the base_pipeline "missing/deferred" set — their target_space is labeled independently
here, likely absent or deferred depending on what they state.]

**Note the divergence oconnor creates:** oconnor's LABEL is canonical (the paper stated a resolvable
file), but the EXTRACTOR emits "MNI" (family_specified) — a flattening. So oconnor will score as a
single clean EXTRACTION ERROR (label canonical, extraction family_specified), NOT a reporting gap. This
is the reporting-completeness-vs-extraction-accuracy divergence, isolated to one paper (verified
1/20 against full text). Do not "fix" the label to match the extractor.

## Carry-forward (logged in v1.1, NOT acted on)

**weber "Conte69" surface flattening — a synonym-resolver gap, NOT an enum gap.** weber normalizes to
the "Conte69 surface template" (Van Essen et al. 2012, ref [79]; HCP `Washington-University/HCPpipelines`),
which the extractor flattens to `MISSING_FROM_PAPER` via `value_not_in_literal`. Independent verification
(2026-07-27) CORRECTED the initial framing: Conte69 is the Van Essen atlas defined ON the fs_LR mesh —
i.e. it IS the fs_LR space, which the `TargetSurface` enum already represents (`fsLR_32k`/`fsLR_164k`).
So this is **not** an "enum can't represent it" gap and **not** the same class as oconnor. Two distinct,
cheaper gaps: (a) a SYNONYM-resolver gap — no `Conte69 → fsLR` alias exists — and (b) a
resolution-granularity point — weber's mesh is 10,242 vertices/hemi (fs_LR "10k"), which neither
`fsLR_32k` (32,492) nor `fsLR_164k` covers exactly. The `value_not_in_literal` flattening is
MECHANICALLY analogous to oconnor (raw value/quote preserved in the `ExtractionDiagnostic`), but the
CLASS differs — oconnor is a canonical volumetric FILE mis-emitted against an EXISTING enum slot; Conte69
is a resolvable surface template lacking an alias. **Do NOT fix before labeling** — label around it and
let the score surface it; the fix (a synonym addition, possibly a `fsLR_10k`/bare-`fsLR` value) is a
cheap additive patch under the versioning convention. Worth watching as more fields are added:
enum/synonym coverage lagging real practice is the recurring pattern, now seen on two fields
(target_space oconnor, target_surface Conte69).

## Inter-rater reliability

Single-rater (author) for v1 — a stated limitation; the target_space labels are not independent of the
system's developer. A second/panel rater and Cohen's/Fleiss' κ are deferred, conditional on pursuing
publication, exactly as base_pipeline. If added, raters label from this protocol alone, blind to the
author labels and to extractor output.

## What this produces

NOT "65% underreported." Per CALL 4, the output is TWO scored distributions plus a joint statement, not
one number: (1) a VOLUMETRIC six-state distribution — canonical, family_specified (adequate for typical
cortical analysis, under-specified for subcortical precision — cited), study_specific, native_volume,
deferred, absent — and (2) a SURFACE completeness distribution; papers appear in both. oconnor is a
single extraction error (label canonical vs extractor family_specified), not a reporting gap; poldrack
is volumetric `deferred` (not an absent reporting failure) with a canonical surface target. Defensible,
reproducible, and it reframes the abstract's claim into an honest completeness finding that supports the
guideline↔machine-readable thesis rather than overstating it.
