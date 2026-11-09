# Configurable realignment and the C-PAC lookups (2026-11-09)

The author's list of 2026-11-09 (night). KB: fmri-defaults-kb, this document's KB commit. No model
call was made for anything here.

## 1. `realignment_tool.configurable`, per pipeline, with its source

| pipeline | versions | configurable | options (default first) | source of the choice |
|---|---|---|---|---|
| cpac | 0.3.2–1.6.1 | no | 3dvolreg | `CPAC/func_preproc/func_preproc.py` at every tag builds AFNI Volreg, no mcflirt; the default configs have no method key before v1.6.0; at v1.6.0–v1.6.1 the template's `motion_correction : ['AFNI']` (lines 570, 693) is read by no code |
| cpac | 1.6.2–1.8.7 | **yes** | 3dvolreg, mcflirt | default config at every tag (`dev/docker_data/default_pipeline.yml` 557–558 at v1.6.2 … `CPAC/resources/configs/pipeline_config_default.yml` 1081–1087 at v1.8.7); `func_preproc.py` reads the key and builds mcflirt (v1.6.2–v1.8.5) |
| hcp_minimal | v3.4.0 | no | **FLIRT** | `GenericfMRIVolumeProcessingPipeline.sh` 149–152 → `MotionCorrection_FLIRTbased.sh` 20 → `mcflirt_acc.sh` (FSL flirt per volume, lines 33, 50) |
| hcp_minimal | v4.1.3 | **yes** | MCFLIRT, FLIRT | `GenericfMRIVolumeProcessingPipeline.sh` 65, 501–509 (`--mctype`, default MCFLIRT); `MotionCorrection.sh` 101–106 |
| ccs | commit 2e41311 | no | 3dvolreg | `H1/ccs_01_funcpreproc.sh` line 63 |
| fcp_scripts | 1.1-beta | no | 3dvolreg | `scripts/2_funcpreproc.sh` line 62 (fcon_1000_scripts_ver1.1.tar.gz, NITRC 2628, sha256 `8453abe9…71d7d9be`); `templates/nuisance.fsf` sets `fmri(mc) 0` (line 81) |
| conn | v20.07.29–v25b | no | SPM Realign | `conn_setup_preproc.m`: every realignment step (`functional_realign`, `functional_realign&unwarp`, field-map variants; step list line 59 at v25b) builds an SPM job |
| dparsf | DPABI_V6.2_220915 | no | SPM Realign | `DPARSFA_run.m` 910–914: Realign.mat, or RealignUnwarp.mat with field-map correction; both SPM |
| abcd_daic | Hagler2019 | no | 3dvolreg | Hagler et al. 2019 §2.7.1 describes one method |
| abcd_bids | v0.0.0–v0.1.5 | no | MCFLIRT | `app/pipelines.py` line 65 (`mctype = 'MCFLIRT'`, a module constant); `app/run.py` exposes no option (v0.0.0, v0.1.5) |
| fmriprep | 1.0.0–25.2.0 | no | MCFLIRT | `fmriprep/workflows/bold/hmc.py` builds `fsl.MCFLIRT` and nothing else at all 21 versions |

**Two corrections to the KB of 2026-10-28.**
- **hcp_minimal.** The KB said MCFLIRT "in both listed tags". v3.4.0 runs FLIRT-based motion
  correction and has no MCFLIRT call at all; MCFLIRT is v4.1.3's default.
- **ccs.** The KB named `H1/ccs_02_funcpreproc.sh`, which does not exist at the listed commit. The
  script is `H1/ccs_01_funcpreproc.sh`.

**C-PAC's 0.3.x range is now verified.** Every 0.3.x tag builds 3dvolreg only, so the range is marked
`stable_across_range: true`. Until today it was marked unverified.

**Provenance rule (resolution call).** A pipeline that lets the user choose, at the versions that
apply, gives its default as INFERRED_MODEL ("pipeline default; the pipeline lets the user choose"),
never INFERRED_DEFAULT. A tool a hop read in a cited paper is EXTRACTED [C]. Which versions apply:
- a stated version the KB lists;
- a stated version the KB does not list: the listed releases either side of it;
- else the date-inferred version and its alternatives;
- else every version.

The KB-confirmed default (INFERRED_DEFAULT) is kept for a pipeline that offers no choice at those
versions, with the program verified across them. When the program differs across them, the result
is INFERRED_MODEL ("version-dependent").

## 2. Lookups

**a. NITRC download 9275 (oconnor ref 64): served.**
- It redirects to `fcon_1000.projects.nitrc.org/indi/hbn_ssi/pipeline_config_serial_scanning.yml`:
  text/plain, 23,797 bytes, sha256
  `7897a6f184bdc06fd5bd64c2c3caaed3bb396531801b003d265e4eba58f532af`.
- The file has **no motion-correction method setting**. Its motion lines are line 275 (`motion :  1`,
  a nuisance-regressor flag under the line-266 legend) and line 310
  (`runGenerateMotionStatistics :  [1]`).
- This is the pre-1.6 config format, in which C-PAC offered no choice of program. The config does
  not state a tool, so it does not give an EXTRACTED [C] value.

**b. Hong et al. 2019, Nat Commun 10:1022 (weber ref 49): not on disk.**
- DOI: `10.1038/s41467-019-08944-1` (CrossRef).
- Stopped there, as instructed. The stored hop for `[49]` is `reference_not_found`.

**c. vanderwal_2016.**
- Its one C-PAC sentence cites only Avants et al. 2008 (ANTs, for the MNI transformation).
- No configuration file, repository or NITRC link appears anywhere in the text. "Configurable" occurs
  only in the pipeline's name.
- The two Craddock citations in the body are the 2012 parcellation atlas.
- One fact beside the question: the reference list includes Craddock & Milham, "The healthy brain
  network serial scanning initiative" (a dataset reference). That is the dataset whose C-PAC config
  is NITRC 9275 (lookup a), which states no motion-correction program either.

## 3. What each resolves to (code path, no model call; the model's pipeline answer taken as C-PAC)

| paper | C-PAC version | versions read | realignment | provenance |
|---|---|---|---|---|
| oconnor_2017 | 0.4.0 stated (never released) | 0.3.9.1 and 1.0.0, the releases either side | afni 3dvolreg | INFERRED_DEFAULT (pipeline default; no choice at those versions) |
| weber_2024 | not stated; 1.8.7 inferred by date | 1.8.7, 1.8.5, 1.8.6 | afni 3dvolreg | **INFERRED_MODEL** ("pipeline default; the pipeline lets the user choose"; options 3dvolreg, mcflirt) |
| vanderwal_2016 | not stated; 0.3.9.1 inferred by date | 0.3.9.1, 0.3.8.1, 0.3.9 | afni 3dvolreg | INFERRED_DEFAULT (pipeline default; no choice at those versions) |

**vanderwal is not configurable-default.** Every C-PAC release before v1.6.2 builds 3dvolreg with no
option, and those are the releases that apply at its date. That gives the KB-confirmed default, not
the configurable-default the author asked to record. The same holds for oconnor. weber is the only
one of the three whose C-PAC versions let the user choose.
