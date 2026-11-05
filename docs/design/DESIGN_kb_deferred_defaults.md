# DESIGN — KB pipeline defaults for fields a paper defers to its pipeline

Fix 3 of the author's list of 2026-11-05, after the stress run (`results/stress_v1`). Design first,
then build. Status: design written and committed before the build, by Claude, under the author's
list; the decisions marked **(Claude's call)** are open to the author's ruling.

## The gap

A field whose extraction arm is `DEFERRED_TO_CITATION` with target kind `pipeline` (the paper says
"preprocessed with fMRIPrep 20.2.0" and nothing more about, say, skull stripping) is left with an
empty inference arm in the `aespa-report` path. Only two KB routes fill anything today:

- `fill_dependent_defaults` (`src/fmri_repro/kb_client/base_pipeline.py`) fills seven fields
  (target space, resolution, target surface, surface registration, temporal band, intensity
  convention and value), and only when `base_pipeline` itself is deferred.
- `infer_motion_method` (`extractor_mvp/motion_inference.py`) fills `motion_correction.method`.

In stress_v1 this left 19 fields empty in Hermans_2024 (fMRIPrep 20.2.0), 11 in Ladouceur_2023
(fMRIPrep v1.5.3) and 11 in Sims_2021 (HCP minimal preprocessing). Hermans also has 3 CompCor
fields deferred to "fMRIPrep in the Supplementary Material" (target kind `supplement`, fix 4).

## The KB entries

Stored as `param_defaults` on the version records of `kb/pipelines/<id>.yaml`, the shape the seven
fields already use (dotted spec path → `value`, `proposed_confidence`, `source`). No schema change.
`get_param_defaults` returns only the paths it is asked for, so `fill_dependent_defaults`, which asks
for the seven paths only, is unaffected by the new entries.

**fMRIPrep 20.2.0 and 1.5.3, from each version's generated methods boilerplate.** The boilerplate
is the `__desc__` text of the workflows that build a run, in fMRIPrep and the packages it pins:
20.2.0 pins `smriprep ~= 0.7.0`, `niworkflows ~= 1.3.1`, `sdcflows ~= 1.3.2`; 1.5.3 pins
`smriprep ~= 0.4.0`, `niworkflows ~= 1.0.2`, `sdcflows ~= 1.0.1` (each tag's `setup.cfg`). The
entries are read at fMRIPrep's tag and at the lower bound of each pin; a later patch release inside a
pin is not read. The CLI default that decides a branch is read from the tag's parser
(`--bold2t1w-dof` 6, `--skull-strip-template` OASIS30ANTs, at both tags). Every entry's `source`
names the file, tag and line.

| field | value | 20.2.0 | 1.5.3 |
|---|---|---|---|
| `slice_time_correction.method` | `afni_3dtshift` | `bold/stc.py` | `bold/stc.py` |
| `brain_extraction.method` | `ants` (antsBrainExtraction) | smriprep `anatomical.py` | same |
| `brain_extraction.parameters` | the template, OASIS30ANTs | smriprep + CLI default | same |
| `segmentation.method` | `fsl_fast` | smriprep `anatomical.py` | same |
| `segmentation.tissue_classes` | CSF, WM, GM | smriprep `anatomical.py` | same |
| `intensity_correction.target` | `bias_field` (T1w INU) | smriprep `anatomical.py` | same |
| `intensity_correction.method` | `n4` | smriprep `anatomical.py` | same |
| `coregistration.method` | `bbregister` | `bold/registration.py` | same |
| `coregistration.transform` | `rigid` (six degrees of freedom) | registration + CLI default | same |
| `coregistration.cost_function` | `boundary_based` | `bold/registration.py` | same |
| `compcor.variance_threshold` | 0.5 | `bold/confounds.py` | same |
| `compcor.mask_source` | the masks, in words | `bold/confounds.py` | **differs** |

The CompCor masks differ between the versions (20.2.0: tCompCor from the top 2% variable voxels in
the brain mask, aCompCor from CSF/WM/combined masks less a GM mask, thresholded at 0.99; 1.5.3: the
top 5% in an eroded subcortical mask, aCompCor within its intersection with CSF∪WM). The coregistration
values hold for fMRIPrep's default run, with FreeSurfer surface reconstruction; with
`--fs-no-reconall` both versions use FLIRT with the BBR cost and nine degrees of freedom. The source
says so.

**Not entered, and why** (they stay "deferred — resolve by consulting the cited source"):

- distortion correction source, method, tool: the branch depends on the fieldmaps a dataset has
  (sdcflows' `pepolar`, `fmap`, `phdiff` or `syn` workflow), so no version default exists;
- slice timing reference and interpolation, coregistration interpolation: the boilerplate does not
  state them (3dTshift's own defaults are AFNI's, not fMRIPrep's text) **(Claude's call)**;
- brain extraction manual edits: not stated;
- CompCor `n_components`: not a fixed number; components are retained to 50% of variance.

**HCP minimal preprocessing, from Glasser et al. (2013), on both listed versions (v3.4.0, v4.1.3).**
The paper describes the pipelines; it predates both tags and is not checked against the scripts at
either tag, and every source says so.

| field | value | Glasser 2013 |
|---|---|---|
| `brain_extraction.parameters` | the atlas mask by inverse FLIRT+FNIRT; final mask from wmparc | PreFreeSurfer; PostFreeSurfer |
| `segmentation.method` | `freesurfer_recon_all` | FreeSurfer pipeline |
| `coregistration.transform` | `rigid` (6 DOF) | fMRIVolume |
| `coregistration.cost_function` | `boundary_based` | fMRIVolume |
| `coregistration.interpolation` | `spline` (one resampling step) | fMRIVolume |
| `intensity_correction.target` | `bias_field` | fMRIVolume (the structural bias field removed) |

Not entered: `brain_extraction.method`, `coregistration.method` and `intensity_correction.method`.
The schema's one-literal slots have no member for an atlas-mask extraction or a sqrt(T1w×T2w)
field, and coregistration is two programs in sequence (FLIRT BBR, then BBRegister). `other` would
say nothing **(Claude's call)**.

## The client: `fill_deferred_defaults`

`src/fmri_repro/kb_client/base_pipeline.py`, called from `_resolve_deferrals` after the seven-field
path and before the motion arm.

- **Which fields.** A step field whose extraction arm is `DEFERRED_TO_CITATION`, whose deferral
  record has target kind `pipeline`, and whose inference arm is `LEFT_MISSING`. Never the extraction
  arm; never a field the motion arm or another KB route already filled.
- **Which pipeline and version.** The base pipeline the paper names (`recognize`). The version is
  matched exactly, then with a leading "v" added or removed ("v1.5.3" is fMRIPrep 1.5.3).
- **Basis.** A certain version (stated, or KB `version_default`) gives `VersionDefaultBasis`, at
  most 0.95, with the KB source as its note. A version the KB only date-inferred (Sims_2021's HCP
  version) gives `DateInferredVersionBasis` at most 0.75. It fills only when the value is identical
  at the inferred version and every alternative. This is the stability rule the motion arm uses
  (DESIGN_motion_inference_arm.md F3). The author's list says "basis version_default". Applying it
  to a version the paper never states would overstate it, so the date-inferred case keeps the motion
  arm's basis **(Claude's call, a deviation from the list's wording)**.
- **Values.** Wrapped to the field's type: `SpecifiedTerm` (verbatim None, resolved the member), a
  list of them, or the bare value; validated through the field's own model. A value that does not
  validate fills nothing (fail closed).
- **Rendering.** A deferred field with an inferred value renders the paper's words first:
  "deferred to fMRIPrep … — not stated in this paper; AESPA infers bbregister (version_default,
  <source>)". This is the motion line's shape, now for every deferred field. The checking pass does
  not see the value and does not judge it (fix 1d).
- **Counting.** The header's "N inferred" counts them. COBIDAS coverage is unchanged: the extraction
  arm is what a row is addressed by, and a deferral already addresses it.

## The KB timeline

fMRIPrep 1.5.3 (released 2019-12-12, github.com/nipreps/fmriprep/releases/tag/1.5.3) is added to
the version list. A paper that does not state its fMRIPrep version and is dated 2019-12-12 to
2020-02-23 now date-infers 1.5.3 instead of 1.5.0. That changes no record in a1, coverage_v4 or
stress_v1 (to be confirmed by the gate).

## Checks

- KB: the validator and its tests; one test per new version record that every entry has a source
  naming a file or the paper.
- Agent: tests for each rule above, with the KB as installed; mutations of the field selection, the
  version normalization, the basis choice, the stability rule and the fail-closed validation.
- Gate: derived before running from the stored deferral records. Only reports with a deferral to a
  recognized pipeline change, so a1 and coverage_v4 are expected unchanged except where they hold
  one.
- Re-run Hermans_2024, Ladouceur_2023 and Sims_2021 with `aespa-report`; count the fields filled.
