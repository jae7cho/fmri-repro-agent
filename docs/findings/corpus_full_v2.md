# corpus_full_v2: the 45 papers re-run (2026-11-09)

Code `5dd74fa` (KB `2883fcb`), aespa-report, default text source (GROBID), metered, under
`caffeinate -i`, from a pinned worktree, into `extractor_mvp/results/corpus_full_v2` (gitignored). Each
paper's reconstructed preprocessing is in `<paper>.preproc.txt` there, and all 45 together in
[`preproc_all_45.txt`](preproc_all_45.txt). At the author's request this document and that file show
values and clipped quotes (80 characters at most) for every paper, the held-out three included.

## The run

- **Statuses:** 38 full reports, 5 `methods_not_found`,
  2 not-fMRI stops (cabral_2017, gao_2026). No paper is without a record.
- **Cost:** $31.3235 metered over 669 calls and 9235.2 s, the 45 final records.
- **Re-runs, at the same commit:**
  - glasser2016_nature. Both batch attempts failed: the model returned `base_pipeline_ref` as
    extracted with no quote three times, and validation rejected it. The paper's supplement was not
    beside it under the name the loader reads (`<stem>_supp.pdf`). The author's copy was placed there
    (sha256 `aeee0d64…`) and the paper re-run: success, supplement read (121,485 characters),
    $1.1705.
  - gracia-tabuenca_2024. The machine lost its network: attempt 1 stalled and the watchdog killed it
    after 2,090 s; attempt 2 failed at once on a DNS error. Re-run: success, $1.0592.
- **Not in the cost above** (billed, unmetered or superseded):
  - the first run at `1b9265e`, stopped after 8 papers for the `_hop_tool` fix (`5dd74fa`):
    $3.8094 metered, kept in `results/corpus_full_v2_aborted_1b9265e`, plus the ninth paper's
    calls, cut off mid-run;
  - glasser2016's two failed attempts and gracia-tabuenca's killed attempt.

## Pseudo-code tags and unverifiable fields, v2 against v1

Both columns are rendered with the current code; v1 is `results/corpus_full_v1` as stored.
**The v1 records carry no resolution call** (it did not exist at their extraction), so their [D] and
[M] are almost all absent by construction.

| tag | v1 | v2 |
|---|---|---|
| [E] | 469 | 648 |
| [D] | 7 | 68 |
| [M] | 11 | 89 |
| [C] | 80 | 61 |
| [?] | 1236 | 1146 |
| [x] | 12 | 15 |

| unverifiable fields | v1 | v2 |
|---|---|---|
| counted on the stored fields | 222 | 72 |
| less checker-supplied values | 211 | 70 |

## The three scorers, the 19 labelled papers

v1 baseline `results/corpus_grobid_v2`; v2 `results/corpus_full_v2_labelled19`, links to the 19 v2 records.

| scorer | v1 | v2 |
|---|---|---|
| motion, bullet 1 (agree / disagree) | 8 / 11 | 8 / 11 |
| smoothing (agree / disagree / not separable) | 13 / 3 / 6 | 13 / 3 / 6 |
| filtering (agree / disagree / not separable) | 11 / 5 / 6 | 11 / 5 / 6 |

The state counts did not change. Three rows changed below the state:
- agtzidis_2020's motion method is extracted ("realigning", described_only) where v1 had it
  unverifiable;
- ciric_2017's and vanderwal_2016's filtering pass type now has a value, which agrees with the label.

The motion scorer scores the paper's phrase (the extraction), not the resolution call.

## The motion row, all 45

| paper | the paper's phrase | resolved tool | provenance |
|---|---|---|---|
| achuthan_2023 | "realigned and unwarped" | spm → Realign | INFERRED_DEFAULT (pipeline_default) |
| agtzidis_2020 | "realigning" | spm → Realign | INFERRED_DEFAULT (package_named) |
| bakker_2012 | "three dimensional registration algorithm" | afni | INFERRED_MODEL |
| bassett_2011 | "FMRIB's linear image registration tool" | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |
| binder_1999 | "iterative procedure that minimizes variance in voxel intensity differences between images" | afni | INFERRED_MODEL |
| braun_2015 | deferred to refs. 47 and 48 | none | UNKNOWN |
| cabral_2017 | not-fMRI stop |  |  |
| cattarinussi_2026 | deferred to [3,][4] | AFNI's 3dvolreg | EXTRACTED (cited: 34) |
| chen_2015 | "corrected acquisition timing among image slices and head motion among image volumes" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |
| cho_2021 | deferred to HCP minimal preprocessing pipeline | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |
| ciric_2017 | "MCFLIRT" | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |
| cole_2013 | "motion correction" | afni → 3dvolreg | INFERRED_DEFAULT (package_named) |
| derosa_2025 | "FSL" | spm → Realign | INFERRED_DEFAULT (pipeline_default) |
| dimitrova_2002 | "rigid body transformations" | spm → Realign | INFERRED_DEFAULT (package_named) |
| gao_2026 | not-fMRI stop |  |  |
| glasser2016_nature | "motion correction" | fsl.FLIRT, fsl.MCFLIRT | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) |
| glasser_2013_hcp_pipelines | "FLIRT" | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |
| gordon_2014 | "SPM8" | spm → Realign | INFERRED_DEFAULT (package_named) |
| gracia-tabuenca_2024 | "corrected for motion" | AFNI's 3dvolreg | EXTRACTED (cited: Hagler et al. (2019)) |
| greene_2022 | "SPM12" | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |
| hagler_2019 | "AFNI's 3dvolreg" | afni → 3dvolreg | INFERRED_DEFAULT (package_named) |
| hermans_2024 | "mcflirt" | fsl → MCFLIRT | INFERRED_DEFAULT (pipeline_default) |
| ladouceur_2023 | "mcflirt" | fsl → MCFLIRT | INFERRED_DEFAULT (pipeline_default) |
| li_2024 | "realignment" | spm → Realign | INFERRED_DEFAULT (package_named) |
| liu_2005 | not stated | brainvoyager → 3D motion correction | INFERRED_DEFAULT (package_named) |
| liu_2013 | "image coregistration to correct for head motion" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |
| maheu_2011 | "corrections for slice timing and motion" | spm → Realign | INFERRED_DEFAULT (package_named) |
| marek_2022 | deferred to ABCD-BIDS pipeline | fsl → MCFLIRT | INFERRED_DEFAULT (pipeline_default) |
| mueller_2021 | "realigned and unwarped" | spm → Realign | INFERRED_DEFAULT (package_named) |
| oconnor_2017 | "motion correction" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |
| poldrack_2015 | "realigned" | fsl.FLIRT, fsl.MCFLIRT | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) |
| power_2014 | "rigid body realignment" | none | UNKNOWN |
| schwartz_2018 | "CONN functional connectivity toolbox" | spm → Realign | INFERRED_DEFAULT (pipeline_default) |
| shen_2013 | "SPM5" | spm → Realign | INFERRED_DEFAULT (package_named) |
| silchenko_2023 | deferred to ICA-FIX | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |
| sims_2021 | deferred to HCP minimal preprocessing pipeline | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |
| smith_2013 | "Realign each timepoint's image to a reference image" | fsl.FLIRT, fsl.MCFLIRT | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) |
| smith_2013_rest_in_hcp | "registration to the single band reference image" | FLIRT | EXTRACTED (cited: Glasser et al., 2013) |
| tang_2025 | "head motion correction" | spm → Realign | INFERRED_DEFAULT (pipeline_default) |
| vanderwal_2016 | "motion realignment" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |
| viduarre_2017 | deferred to Smith et al. (18, 39) | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |
| weber_2024 | deferred to C-PAC | afni → 3dvolreg | INFERRED_MODEL (pipeline default; the pipeline lets the user choose) |
| wheaton_2004 | "SPM99" | spm → Realign | INFERRED_DEFAULT (package_named) |
| yang_2025 | deferred to 67 | FLIRT | EXTRACTED (cited: 67) |
| yassa_2010 | not stated | afni → 3dvolreg | INFERRED_DEFAULT (package_named) |

## Hops

17 hop records.

| paper | citation | status | target | file |
|---|---|---|---|---|
| braun_2015 | refs. 47 and 48 | no_reference_section | None |  |
| cattarinussi_2026 | 34 | ok | local_pdf | Hagler_2019.pdf |
| cattarinussi_2026 | [3,][4] | not_retrievable | no_local_pdf |  |
| cattarinussi_2026 | [3,][4] | not_retrievable | no_local_pdf |  |
| chen_2015 | [51] | not_retrievable | no_local_pdf |  |
| cho_2021 | Marcus et al., 2013; Glasser et al., 2013 | not_retrievable | no_local_pdf |  |
| cho_2021 | Marcus et al., 2013; Glasser et al., 2013 | not_retrievable | no_local_pdf |  |
| gracia-tabuenca_2024 | Hagler et al. (2019) | ok | local_pdf | Hagler_2019.pdf |
| mueller_2021 | Pritschet et al. (2020) | not_retrievable | no_local_pdf |  |
| smith_2013_rest_in_hcp | Glasser et al., 2013 | ok | local_pdf | Glasser_2013_HCP_pipelines.pdf |
| tang_2025 | [9,][25] | not_retrievable | no_local_pdf |  |
| tang_2025 | [9,][25] | not_retrievable | no_local_pdf |  |
| viduarre_2017 | Glasser et al. 40 | no_reference_section | None |  |
| viduarre_2017 | Smith et al. (18, 39) | not_retrievable | local_pdf_ambiguous |  |
| viduarre_2017 | Smith et al. (18, 39) | not_retrievable | local_pdf_ambiguous |  |
| weber_2024 | [49] | ok | europepmc_fulltext | 10.1038_s41467-019-08944-1.europepmc.xml |
| yang_2025 | 67 | ok | local_pdf | Glasser_2013_HCP_pipelines.pdf |

What the hops show:
- **cattarinussi_2026 → hagler_2019.** The step-wide citation "34" (main text, b33) is a cited
  sentence on motion with a deferral cue. It resolves to `Hagler_2019.pdf` on disk, which names AFNI's
  3dvolreg with a resolved quote, so cattarinussi's tool is EXTRACTED [C]. The supplement's
  "[3,][4]" (b2, b3) has no PDF on disk and no Europe PMC full text.
- **weber_2024 [49] → Hong et al. 2019,** via Europe PMC (PMC6399265; the DOI found by CrossRef from the
  reference text; JATS cached beside weber's PDF,
  `tested_lit/sfn_batch/10.1038_s41467-019-08944-1.europepmc.xml`). Hong's sentence says processing was
  based on C-PAC and included head motion correction, with **no program named**. weber's tool stays
  INFERRED_MODEL, C-PAC's configurable default.

## Provider-applied steps

Marked `applied_by=data_provider` (the field's quote names the paper's data release and says it was
preprocessed): greene_2022, sims_2021.

## Observations, not fixed

- **The motion stanza did not get the new rules.** `MOTION_METHOD_PROMPT` is the pre-registered probe
  stanza, and the probe recorder refuses any other. The co-registration rule reaches the motion row
  only through the extraction prompt, the coverage calls and the checking pass.
- **A pipeline's default is preferred over a package the paper names for this step.**
  - glasser_2013_hcp_pipelines: the phrase is "FLIRT", but the resolution gives fsl → MCFLIRT
    (package named, FSL's program).
  - greene_2022: the phrase is "SPM12", but the resolution gives fsl → FLIRT (the HCP pipeline's
    default).
  - derosa_2025: the phrase is "FSL", but the resolution gives spm → Realign (a pipeline's default).
- **Version-dependent:** glasser2016_nature, poldrack_2015 and smith_2013 resolve to HCP Pipelines
  with no version, so FLIRT or MCFLIRT.
- **Unknown tool:** braun_2015 and power_2014.
