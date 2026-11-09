# The realignment tool by precedence (2026-11-09, night 3)

Code `7d96e0b`; KB `8ea0350` (`recognize_program`). The 45 records of
`results/corpus_full_v2` were re-resolved with **no model call** into
`results/corpus_full_v2_reresolved` (gitignored), by `reresolve.py`.

## The rule

The first tier with a candidate wins; a lower tier never overrides it.

1. **A program the paper names for the step** (`recognize_program` on the method phrase): EXTRACTED,
   with the paper's quote (`program_named`). "Realign" counts only beside "SPM", because it is also a
   verb.
2. **A program a cited paper states** (a hop's tool answer, quote resolved): EXTRACTED [C]
   (`cited_program`).
3. **A package named for the step or for the preprocessing**: its default, INFERRED_DEFAULT
   (`package_named`). The package is the method phrase, or exactly one realignment-capable package
   among the mentions whose fMRI use is bound to the step, or to the preprocessing or analysis as a
   whole. A step-bound use outranks a whole-preprocessing one. An APPLY use (resampling) does not
   count. Two or more packages are not attributable (protocol v1.8).
4. **A pipeline**: its default, INFERRED_DEFAULT (`pipeline_default`), or INFERRED_MODEL when it is
   configurable, version-dependent or unverified.
5. **The model's answer**: INFERRED_MODEL; else UNKNOWN.

A lower tier that disagrees is kept, as "conflict: paper names X, pipeline default Y" (or package
default Y).

**The raw answers.** Records written before `7d96e0b` kept the interpreted resolution, not the
model's raw answer. The raw answer is therefore rebuilt from what each stored resolution kept: the
pipeline and the tool as answered, the basis and the sub-items. Its tool answer can be the KB's
value where the old code replaced the model's. From `7d96e0b` the raw answer is stored
(`resolution.answer`).

## The six papers, before and after

| paper | raw answer (rebuilt) | before | after |
|---|---|---|---|
| ciric_2017 | resolved_pipeline=none, realignment_tool=fsl | value=fsl, provenance=INFERRED_DEFAULT, kb_basis=package_named | value=fsl, program=MCFLIRT, provenance=EXTRACTED, basis=program_named; conflicts: conflict: paper names MCFLIRT, package default ants antsMotionCorr |
| derosa_2025 | resolved_pipeline=conn, realignment_tool=fsl | value=spm, provenance=INFERRED_DEFAULT, as_answered=fsl, kb_basis=pipeline_default | value=fsl, program=MCFLIRT, provenance=INFERRED_DEFAULT, basis=package_named, kb_basis=package_named; conflicts: conflict: paper names FSL, pipeline default spm Realign |
| glasser_2013_hcp_pipelines | resolved_pipeline=none, realignment_tool=fsl | value=fsl, provenance=INFERRED_DEFAULT, kb_basis=package_named | value=fsl, program=FLIRT, provenance=EXTRACTED, basis=program_named |
| greene_2022 | resolved_pipeline=hcp_minimal, realignment_tool=spm | value=fsl, provenance=INFERRED_DEFAULT, as_answered=spm, kb_basis=pipeline_default | value=spm, program=Realign, provenance=INFERRED_DEFAULT, basis=package_named, kb_basis=package_named; conflicts: conflict: paper names SPM12, pipeline default fsl FLIRT |
| hermans_2024 | resolved_pipeline=fmriprep, realignment_tool=fsl | value=fsl, provenance=INFERRED_DEFAULT, kb_basis=pipeline_default | value=fsl, program=MCFLIRT, provenance=EXTRACTED, basis=program_named |
| ladouceur_2023 | resolved_pipeline=fmriprep, realignment_tool=fsl | value=fsl, provenance=INFERRED_DEFAULT, kb_basis=pipeline_default | value=fsl, program=MCFLIRT, provenance=EXTRACTED, basis=program_named |

## Rows whose tool or provenance changed (18)

| paper | tool before | provenance before | tool after | provenance after |
|---|---|---|---|---|
| achuthan_2023 | spm → Realign | INFERRED_DEFAULT (pipeline_default) | spm → Realign | INFERRED_DEFAULT (package_named) |
| cattarinussi_2026 | AFNI's 3dvolreg | EXTRACTED (cited: 34) | afni → 3dvolreg | EXTRACTED (cited_program) (cited: 34) |
| ciric_2017 | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) | fsl → MCFLIRT | EXTRACTED (program_named) |
| derosa_2025 | spm → Realign | INFERRED_DEFAULT (pipeline_default) | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |
| dimitrova_2002 | spm → Realign | INFERRED_DEFAULT (package_named) | spm | INFERRED_MODEL |
| glasser2016_nature | fsl.FLIRT, fsl.MCFLIRT | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) | fsl | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) | display only (the version-dependent row now carries its package)
| glasser_2013_hcp_pipelines | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) | fsl → FLIRT | EXTRACTED (program_named) |
| gracia-tabuenca_2024 | AFNI's 3dvolreg | EXTRACTED (cited: Hagler et al. (2019)) | afni → 3dvolreg | EXTRACTED (cited_program) (cited: Hagler et al. (2019)) |
| greene_2022 | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) | spm → Realign | INFERRED_DEFAULT (package_named) |
| hagler_2019 | afni → 3dvolreg | INFERRED_DEFAULT (package_named) | afni → 3dvolreg | EXTRACTED (program_named) |
| hermans_2024 | fsl → MCFLIRT | INFERRED_DEFAULT (pipeline_default) | fsl → MCFLIRT | EXTRACTED (program_named) |
| ladouceur_2023 | fsl → MCFLIRT | INFERRED_DEFAULT (pipeline_default) | fsl → MCFLIRT | EXTRACTED (program_named) |
| liu_2005 | brainvoyager → 3D motion correction | INFERRED_DEFAULT (package_named) | brainvoyager | INFERRED_MODEL |
| poldrack_2015 | fsl.FLIRT, fsl.MCFLIRT | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) | fsl | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) | display only (the version-dependent row now carries its package)
| smith_2013 | fsl.FLIRT, fsl.MCFLIRT | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |
| smith_2013_rest_in_hcp | FLIRT | EXTRACTED (cited: Glasser et al., 2013) | fsl → FLIRT | EXTRACTED (cited_program) (cited: Glasser et al., 2013) |
| tang_2025 | spm → Realign | INFERRED_DEFAULT (pipeline_default) | spm → Realign | INFERRED_DEFAULT (package_named) |
| yang_2025 | FLIRT | EXTRACTED (cited: 67) | fsl → FLIRT | EXTRACTED (cited_program) (cited: 67) |

**dimitrova_2002 and liu_2005 move to model-only.** Their software mentions name SPM and BrainVoyager
for uses that are neither this step nor the preprocessing or analysis as a whole, so the package tier
no longer applies to them.

## Pseudo-code tags, v2 against re-resolved

| tag | v2 | re-resolved |
|---|---|---|
| [E] | 648 | 653 |
| [D] | 68 | 61 |
| [M] | 89 | 90 |
| [C] | 61 | 61 |
| [?] | 1146 | 1147 |
| [x] | 15 | 15 |

## The motion row, all 45 (re-resolved)

| paper | the paper's phrase | resolved tool | provenance | conflicts |
|---|---|---|---|---|
| achuthan_2023 | "realigned and unwarped" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| agtzidis_2020 | "realigning" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| bakker_2012 | "three dimensional registration algorithm" | afni | INFERRED_MODEL |  |
| bassett_2011 | "FMRIB's linear image registration tool" | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |  |
| binder_1999 | "iterative procedure that minimizes variance in voxel intensity differences between images" | afni | INFERRED_MODEL |  |
| braun_2015 | deferred to refs. 47 and 48 | none | UNKNOWN |  |
| cabral_2017 | not-fMRI stop |  |  |  |
| cattarinussi_2026 | deferred to [3,][4] | afni → 3dvolreg | EXTRACTED (cited_program) (cited: 34) |  |
| chen_2015 | "corrected acquisition timing among image slices and head motion among image volumes" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |  |
| cho_2021 | deferred to HCP minimal preprocessing pipeline | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |  |
| ciric_2017 | "MCFLIRT" | fsl → MCFLIRT | EXTRACTED (program_named) | conflict: paper names MCFLIRT, package default ants antsMotionCorr |
| cole_2013 | "motion correction" | afni → 3dvolreg | INFERRED_DEFAULT (package_named) |  |
| derosa_2025 | "FSL" | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) | conflict: paper names FSL, pipeline default spm Realign |
| dimitrova_2002 | "rigid body transformations" | spm | INFERRED_MODEL |  |
| gao_2026 | not-fMRI stop |  |  |  |
| glasser2016_nature | "motion correction" | fsl | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) |  |
| glasser_2013_hcp_pipelines | "FLIRT" | fsl → FLIRT | EXTRACTED (program_named) |  |
| gordon_2014 | "SPM8" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| gracia-tabuenca_2024 | "corrected for motion" | afni → 3dvolreg | EXTRACTED (cited_program) (cited: Hagler et al. (2019)) | conflict: cited paper (Hagler et al. (2019)) names AFNI's 3dvolreg, pipeline default fsl MCFLIRT |
| greene_2022 | "SPM12" | spm → Realign | INFERRED_DEFAULT (package_named) | conflict: paper names SPM12, pipeline default fsl FLIRT |
| hagler_2019 | "AFNI's 3dvolreg" | afni → 3dvolreg | EXTRACTED (program_named) |  |
| hermans_2024 | "mcflirt" | fsl → MCFLIRT | EXTRACTED (program_named) |  |
| ladouceur_2023 | "mcflirt" | fsl → MCFLIRT | EXTRACTED (program_named) |  |
| li_2024 | "realignment" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| liu_2005 | not stated | brainvoyager | INFERRED_MODEL |  |
| liu_2013 | "image coregistration to correct for head motion" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |  |
| maheu_2011 | "corrections for slice timing and motion" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| marek_2022 | deferred to ABCD-BIDS pipeline | fsl → MCFLIRT | INFERRED_DEFAULT (pipeline_default) |  |
| mueller_2021 | "realigned and unwarped" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| oconnor_2017 | "motion correction" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |  |
| poldrack_2015 | "realigned" | fsl | INFERRED_MODEL (version-dependent: the pipeline's program differs across the versions that apply) |  |
| power_2014 | "rigid body realignment" | none | UNKNOWN |  |
| schwartz_2018 | "CONN functional connectivity toolbox" | spm → Realign | INFERRED_DEFAULT (pipeline_default) |  |
| shen_2013 | "SPM5" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| silchenko_2023 | deferred to ICA-FIX | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |  |
| sims_2021 | deferred to HCP minimal preprocessing pipeline | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |  |
| smith_2013 | "Realign each timepoint's image to a reference image" | fsl → MCFLIRT | INFERRED_DEFAULT (package_named) |  |
| smith_2013_rest_in_hcp | "registration to the single band reference image" | fsl → FLIRT | EXTRACTED (cited_program) (cited: Glasser et al., 2013) | conflict: cited paper (Glasser et al., 2013) names FLIRT, package default fsl MCFLIRT |
| tang_2025 | "head motion correction" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| vanderwal_2016 | "motion realignment" | afni → 3dvolreg | INFERRED_DEFAULT (pipeline_default) |  |
| viduarre_2017 | deferred to Smith et al. (18, 39) | fsl → FLIRT | INFERRED_DEFAULT (pipeline_default) |  |
| weber_2024 | deferred to C-PAC | afni → 3dvolreg | INFERRED_MODEL (pipeline default; the pipeline lets the user choose) |  |
| wheaton_2004 | "SPM99" | spm → Realign | INFERRED_DEFAULT (package_named) |  |
| yang_2025 | deferred to 67 | fsl → FLIRT | EXTRACTED (cited_program) (cited: 67) |  |
| yassa_2010 | not stated | afni → 3dvolreg | INFERRED_DEFAULT (package_named) |  |

## Motion labels: resolved_tool and the resolved scorer

`scripts/fill_motion_resolved.py` added `resolved_tool` and `resolved_basis` to
`ground_truth/motion_correction_labels_v1.xlsx`. It filled only the 9 named_tool labels, each of
whose own method_value names a program (1: MCFLIRT) or a package (8). The 10 others are blank for the
author. No existing cell changed.

`scripts/score_motion_resolved.py` on the re-resolved records (held-out papers show the outcome
only):

Records: `results/corpus_full_v2_reresolved`. Labels: `ground_truth/motion_correction_labels_v1.xlsx` (resolved_tool, filled by code where the label names a program or package). Counts only; no rates.

| paper | outcome | provenance group | label | record |
|---|---|---|---|---|
| agtzidis_2020 | agree | KB-confirmed | spm Realign | spm Realign |
| binder_1999 | label blank | model-only |  |  |
| braun_2015 | label blank | model-only |  |  |
| chen_2015 | label blank | KB-confirmed |  | afni 3dvolreg |
| ciric_2017 | agree | KB-confirmed | fsl MCFLIRT | fsl MCFLIRT |
| cole_2013 | agree | KB-confirmed | afni 3dvolreg | afni 3dvolreg |
| derosa_2025 | agree | KB-confirmed | fsl MCFLIRT | fsl MCFLIRT |
| gordon_2014 | agree | KB-confirmed | spm Realign | spm Realign |
| liu_2005 | disagree | model-only | (held out) |  |
| liu_2013 | label blank | KB-confirmed |  | afni 3dvolreg |
| mueller_2021 | agree | KB-confirmed | spm Realign | spm Realign |
| oconnor_2017 | label blank | KB-confirmed |  | afni 3dvolreg |
| poldrack_2015 | label blank | model-only |  |  |
| power_2014 | label blank | model-only |  |  |
| tang_2025 | agree | KB-confirmed | (held out) | (held out) |
| vanderwal_2016 | label blank | KB-confirmed |  | afni 3dvolreg |
| viduarre_2017 | label blank | KB-confirmed |  | fsl FLIRT |
| weber_2024 | label blank | model-only |  | afni 3dvolreg |
| wheaton_2004 | agree | KB-confirmed | (held out) | (held out) |

| group | agree | disagree | label blank |
|---|---|---|---|
| KB-confirmed | 8 | 0 | 5 |
| model-only | 0 | 1 | 5 |
