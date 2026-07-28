# target_space extraction specificity-flattening: a one-off (oconnor), not systematic

**Finding (2026-07-25, inspection — EXTRACTOR OUTPUT, not scored; no target_space ground truth yet).**
The oconnor case raised the question: does the extractor systematically discard specificity the paper
*provided* — extract a bare family term ("MNI") when its own quote names a specific template file? A
deterministic value-vs-quote diff across all 20 papers (K=3, post-`study_specific`/resolver-fix run)
says **no: it is a single case.**

## The oconnor case

- **quote:** *"a 2-mm MNI brain-only template (FSL's MNI152T1_2mm brain.nii.gz, [59])"* — a specific,
  reproducible FSL template file.
- **extracted value:** `"MNI"` — the family term. The specific file was flattened away.
- Consequence: the resolver fix (FSL file forms → `MNI152NLin6Asym`, committed) is **correct but
  inert** here — it matches on `fe.value`, and `fe.value` is `"MNI"`, not the file name (which lives
  only in the quote). So oconnor stays **family-specified** in extraction despite being **canonical in
  the paper**.

## Is it systematic? Deterministic diff, all 20 papers (STEP 2)

Flag a paper FLATTENED iff its value is a bare family term (`MNI`/`MNI152`/`atlas space`/…) **and** its
quote contains a more specific signal the value dropped (a `.nii(.gz)` file, an `MNI152_T1_*mm` FSL
file, a `NLin6`/`2009c`/sym-asym variant, an `fsaverage#`/`Colin27`/`ICBM` named template).

- **FLATTENED: 1 of 20 — `oconnor_2017` only.**
- **No loss: 19 of 20.** The other family-specified papers (agtzidis, chen, liu_2013, tang, vanderwal,
  wheaton = "MNI"; derosa = "MNI-152"; weber = "MNI152"; gordon = "EPI template"; poldrack/power =
  "atlas space") have quotes that are themselves family-level — the paper genuinely did not name a
  variant, so the value matches the quote's specificity. The two resolved papers (binder, cole →
  Talairach) and the study_specific one (mueller) lost nothing; five papers are absent (no value).

So the **reporting-completeness gap (12 family-specified) is real, not an extraction artifact** — those
papers were family-level in the source. Only oconnor is an extraction miss.

### Verified against FULL TEXT, not just the model's quote

Because the model's `verbatim_quote` can be shorter than the paper, the diff above was re-run against
each family-specified paper's FULL PDF text (does a specific variant/file/template appear *anywhere*
that "MNI" flattened?). Every non-oconnor hit adjudicated to a NON-target_space context:

- **chen `fsaverage5`, weber `Conte69`** — SURFACE templates (`target_surface` / smoothing), not the
  volumetric target_space (which is bare "MNI"/"MNI152" in both).
- **liu_2013 `.nii.gz`** — a downloadable *results* map (`CAPs_30_2mm.nii.gz`), not a template;
  liu_2013 `asymmetric` — describes an *activation*, not a template.
- **power `symmetric`** — the temporal *filter*; **vanderwal `Symmetric`** — a *reference* title (ANTs
  SyN). Not templates.

Confirmed volumetric target_space forms, full text: agtzidis "MNI template", chen "MNI space", derosa
"MNI-152 template (12-dof linear)", liu_2013 "152-brain MNI template", tang "MNI standard space",
vanderwal "MNI space", weber "MNI152 space", wheaton "SPM MNI template", gordon "EPI template",
poldrack/power "atlas space" — all family-level, none a variant/file. **oconnor is the only paper that
named a specific resolvable template file (`FSL's MNI152T1_2mm brain.nii.gz`).** The 1/20 holds against
full text.

Borderline (named, not flattening): **wheaton "SPM MNI template"** is tool-generic — SPM ships a
specific historical template, but "SPM MNI template" names no canonical variant/file the way FSL's
`MNI152T1_2mm` does (SPM lineage is variant-ambiguous), so it correctly stays family-specified. A
candidate only if SPM-template synonyms are ever added.

## Cross-field spot check (STEP 3): flattening is not a general tendency

Checked `base_pipeline_name` and `resolution_mm` value-vs-quote across the 20-paper batch:

- **`base_pipeline_name`: no flattening.** Where a quote carried a version (derosa "FSL suite (version
  5.0.10)", oconnor "C-PAC version 0.4.0"), the version is now captured by the SEPARATE
  `base_pipeline_version` field (the Q1 change), not dropped from the name.
- **`resolution_mm`: no flattening.** All resolutions are isotropic (`3 × 3 × 3 mm` → `3.0`); the single
  value captures the quote. (An anisotropic voxel flattened to one number would be flattening — none
  present.)

Flattening is **not** a general extraction tendency; it is confined to the one oconnor target_space case.

## The two axes diverge only at oconnor

- **reporting-completeness** = what the paper *stated*. oconnor stated a specific FSL file → **canonical**.
- **extraction-accuracy** = what we *captured*. oconnor captured "MNI" → **family-specified**.

At oconnor these disagree: an **extraction miss masquerading as a reporting gap.** Everywhere else they
agree (the paper was family-level and we captured family-level).

## Implication for target_space ground truth (Stage B)

- Labels must capture **what the PAPER stated**, so **oconnor labels `canonical`** (the FSL file is
  NLin6Asym by established identity). Scoring will then surface the flattening as **one extraction
  error** (predicted family-specified vs. labeled canonical) — cleanly, not as a pervasive bias.
- **Recommendation: label around it — this is a one-off, not a systematic flattening.** No target_space
  extraction-prompt fix is warranted before seeding ground truth. If a future/larger corpus shows the
  file-form-in-quote / family-term-in-value pattern recurring, revisit a prompt nudge ("extract the
  most specific template identifier the sentence gives, including file names"); on this corpus it is
  1/20 and better handled as a single labeled case.

Related: [`pdf-glue-false-missing.md`](pdf-glue-false-missing.md) (another "measure before assuming
systematic" case), the target_space reframe in `generate_sfn_review.py`.
