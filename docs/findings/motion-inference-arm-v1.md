# motion_correction.method — the inference arm applied to the corpus vintage (2026-10-28)

**DIAGNOSTIC. Not an evaluation.** The inference arm of `DESIGN_motion_inference_arm.md`, built under
the author's rulings of 2026-10-28 and applied to the stored batch `batch_motion_corpus_v1` as a
**processed vintage, with no model call** — `batch_motion_corpus_v1_inferred`, under `results/`,
untracked as results/ always is. Per paper: filled or not, by which path and basis, at what
confidence, with what alternatives; compared with the reach pre-declared in the design doc §0 before
the build; **counts of papers filled per basis; no accuracy figure.** Evaluation is against
documentation, not labels: the inferred program is the documented default by construction, and
nothing here is compared with column C. The clean three: **filled-or-not only.**

- **Source vintage** `batch_motion_corpus_v1` (2026-10-27, HEAD `8099063`, stanza `b0093774…`).
- **Processed vintage** `batch_motion_corpus_v1_inferred`: the stored preprocessing re-parsed,
  `infer_motion_method` applied, re-rendered with the record; `manifest.json` names the source
  vintage, HEAD, the live stanza hash and `model_call: false`.
- **Projection**
  [ground_truth/motion_inference_v1_projection.csv](../../ground_truth/motion_inference_v1_projection.csv):
  path, basis name and type, confidence, alternatives, the inferred program (a knowledge-base value);
  **the clean three carry the path only.** No paper text.
- **The knowledge base** (`fmri-defaults-kb`, editable): `kb/tools/` (five packages, a program and a
  source each) and the `realignment_tool` ranges in the five pipeline documents, the FCP scripts
  document new; `recognize()` learns the FCP scripts; `recognize_tool()` learns the packages.

## Counts of papers, by path and basis

| path | basis | papers |
|---|---|---|
| inference arm proper | package (`derived`, 0.70) | **1** — agtzidis_2020 |
| diagnostic on the processed layer (F1) | pipeline, `version_default` 0.95 | **1** — liu_2013 |
| diagnostic | pipeline, `date_inferred_version` 0.75 (stable range) | **2** — chen_2015, weber_2024 |
| diagnostic | package (`derived`, 0.70) | **1** — mueller_2021 |
| never (`named_tool`) | — | **3** — derosa, gordon, ciric |
| none: nothing to infer from | — | **7** — power, binder, poldrack, cole (no base pipeline on the record); braun, viduarre (deferred to papers); vanderwal, oconnor (below) |
| clean three, filled-or-not only | — | liu_2005 **not filled**; tang_2025 **filled** (diagnostic); wheaton_2004 **filled** (diagnostic) — 2 of 3 |

Arm 1, diagnostic 5, never 3, none 7, over the sixteen; the clean three 2 filled, 1 not. Both bases
applied to no paper, so F2's precedence was not exercised; every filled paper has 0 alternatives.

## Against the pre-declared reach (design doc §0, written before the build)

| paper | pre-declared | found | as declared |
|---|---|---|---|
| vanderwal_2016 | arm by P at 0.75, **conditional on the range mark** | **none**: the date-inferred version is 0.3.9.1 with alternatives 0.3.8.1 and 0.3.9 — the whole range sits in C-PAC's 0.3.x range, which the KB marks **not** stable (F6: recorded, not verified per release); the motion sentence's deferral target `C-PAC` resolves, but with no usable version no pipeline basis exists, and `C-PAC` is not a package | yes — the condition failed, as the declaration allowed |
| agtzidis_2020 | arm by T, 0.70 | **arm by T, 0.70**: `SPM12` → Realign (`spm_realign`); the stored motion field was MISSING (quote unresolved), so the arm proper took it | yes |
| liu_2013 | diagnostic by P at 0.95 once the FCP document exists | **diagnostic by P, 0.95**: `FCP analysis scripts` → `fcp_scripts`, version `1.1-beta` extracted → 3dvolreg | yes |
| chen_2015 | diagnostic by P at 0.75, conditional | **diagnostic by P, 0.75**: `ccs`, version date-inferred `2015`, the range marked stable → 3dvolreg | yes |
| oconnor_2017 | diagnostic by P at 0.95 | **none**: the paper's extracted version string `0.4.0` is **not a listed C-PAC release** in the KB's tag-derived timeline (0.3.9.1 is followed by 1.0.0), so the lookup raises an unknown-version error and no pipeline basis exists; `C-PAC` is not a package. The KB gap, not the paper, is the cause; the paper's own configuration-file citation (ref 64) remains the citation-hop target F6 noted | **no** — a KB timeline gap, reported as found |
| weber_2024 | diagnostic by P at 0.75, conditional | **diagnostic by P, 0.75**: `cpac` 1.8.7 with alternatives 1.8.5, 1.8.6, all in the stable 1.x range → 3dvolreg | yes |
| mueller_2021 | diagnostic by T, 0.70 | **diagnostic by T, 0.70**: `Statistical Parametric Mapping 12` → Realign | yes |
| derosa, gordon, ciric | never | never | yes |
| power, binder, poldrack, cole; braun, viduarre | none | none | yes |
| liu_2005 | not filled | not filled | yes |
| tang_2025, wheaton_2004 | filled-or-not, a count | 2 of 2 filled, diagnostic | reported |

Fifteen of sixteen contaminated papers as pre-declared; one (oconnor) not, for a knowledge-base
reason recorded above. The expected counts were arm 2 / diagnostic 5; found arm 1 / diagnostic 5,
with vanderwal's conditional fill not firing and oconnor's missing.

## What was found that was not pre-declared

- **A version the paper states can be absent from the KB's release timeline** (oconnor's `0.4.0`): a
  certain version that the registry cannot look up yields no basis at all, not a lower-confidence
  one. Whether the timeline should carry pre-1.0 releases beyond the tagged ones is a KB question.
- **Every pipeline-basis fill was a diagnostic**, because every paper whose base pipeline resolves had
  a `described_only` motion extraction; the one arm-proper fill came from a package on a `missing`
  field. The contract conflation F1 names is the common case on this corpus, not the exception.

## The report line

Rendered identically on both paths: the paper's words, then *tool not stated; AESPA infers X (basis,
source)*. For the arm proper the clause is produced from the inferred default on the field and reads
the same with or without the record (the basis note carries the source); for the diagnostic the
clause is appended from the record beside the result and the field's own line is as before. A
`named_tool` line never carries it.

## The identity gate

Derived before the build as **19 identical** (the clause reaches only a motion row with an inferred
default or a diagnostic record; no stored acceptance JSON carries a motion step; the processed
vintage is written elsewhere) and run after it: `--against HEAD` 19 identical, 0 changed; the
negative control `--against d31e8b7` 0 identical, 19 changed.

## Status

- Labels unchanged. No stanza change (frozen at `b0093774…`). No model call.
- Held for the author: the KB timeline gap at C-PAC `0.4.0`; whether vanderwal's 0.3.x range should
  be verified so the conditional fill can fire; the structural split of "performed" and "method"
  after 2026-11-09, which F1 records as the fix for the conflation that makes the diagnostic path
  the common case.
