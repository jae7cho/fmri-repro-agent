# Tool reference: DPARSF's realign step calls SPM's Realign module with SPM12 master's default parameters

> **THIS IS A TOOL REFERENCE, NOT A CORPUS FINDING.** It records what a piece of software does. It is
> **not** evidence about any paper, and it was **not** used to decide any ground-truth label. It is filed
> here as a candidate `version_default` basis for the Defaults KB and the Pipeline Configurator, which is
> the only arm of the system permitted to consume tool behaviour.
>
> **It is explicitly NOT the basis for `tang_2025`'s `motion_correction.method` label.** That label rests
> on tang's own sentences naming SPM12 in both streams (protocol v1.4, CALL 9). Had the preset below
> deviated from SPM12's defaults, tang's text would be unchanged and so would the label. Letting tool
> behaviour decide a label breaches the extractor/configurator firewall
> (`PROJECT_DESCRIPTION.md`, key technical challenge 1) inside the ground truth itself.

**Read on:** 2026-08-13. **Sources read (exact):**
- `Chaogan-Yan/DPABI` @ GitHub default branch `master`, files `DPARSF/DPARSFA_run.m` and
  `DPARSF/Jobmats/Realign.mat`. Sparse checkout; no release tag pinned (the repo carries 1 tag).
- `spm/spm12` @ GitHub branch `master`, files `config/spm_cfg_realign.m` and `spm_defaults.m`.

---

## What was verified

### 1. DPARSF does not implement realignment; it calls SPM's Realign module

`DPARSF/DPARSFA_run.m:935–990` loads a preset SPM batch, fills SPM's own configuration namespace, and
executes it through SPM's job runner:

```matlab
%Realign
if (AutoDataProcessParameter.IsRealign==1)
    ...
    SPMJOB = load([ProgramPath,filesep,'Jobmats',filesep,'Realign.mat']);
    ...
    SPMJOB.matlabbatch{1,1}.spm.spatial.realign.estwrite.data{1,iFunSession}=FileList;
    ...
    spm_jobman('run',SPMJOB.matlabbatch);
```

A conditional branch loads `Jobmats/RealignUnwarp.mat` and fills `spm.spatial.realignunwarp` instead when
`FieldMap.IsFieldMapCorrectionUnwarpRealign` is set. Both paths terminate in `spm_jobman('run', …)`.

The repository README states DPABI "evolved from DPARSF" and contains DPABISurf, DPABIFiber, DPABINet and
BrainImageNet; the tree carries a `RedistributedToolboxes/` directory. The realign call site is therefore
a wrapper around SPM in the mechanical sense: SPM's `spm.spatial.realign.estwrite` module performs the
estimation and reslicing.

### 2. The shipped preset equals SPM12 master's realign defaults on all eleven parameters

`DPARSF/Jobmats/Realign.mat` decoded (`scipy.io.loadmat`) against
`spm_defaults.m` (SPM12 master; `spm_cfg_realign.m` confirms every field resolves through
`spm_get_defaults('realign.…')` rather than a hard-coded config value):

| SPM batch field | DPARSF `Realign.mat` | SPM12 `spm_defaults.m` | match |
|---|---|---|---|
| `eoptions.quality` | 0.9 | `realign.estimate.quality = 0.9` | ✔ |
| `eoptions.sep` | 4 | `realign.estimate.sep = 4` | ✔ |
| `eoptions.fwhm` | 5 | `realign.estimate.fwhm = 5` | ✔ |
| `eoptions.rtm` | 1 | `realign.estimate.rtm = 1` | ✔ |
| `eoptions.interp` | 2 | `realign.estimate.interp = 2` | ✔ |
| `eoptions.wrap` | [0 0 0] | `realign.estimate.wrap = [0 0 0]` | ✔ |
| `eoptions.weight` | `[]` | `weight.val = {''}` (`spm_cfg_realign.m:157`) | ✔ (both empty) |
| `roptions.which` | [2 1] | `realign.write.which = [2 1]` | ✔ |
| `roptions.interp` | 4 | `realign.write.interp = 4` | ✔ |
| `roptions.wrap` | [0 0 0] | `realign.write.wrap = [0 0 0]` | ✔ |
| `roptions.mask` | 1 | `realign.write.mask = 1` | ✔ |
| `roptions.prefix` | `'r'` | `realign.write.prefix = 'r'` | ✔ |

`rtm = 1` is register-to-mean (two-pass); `roptions.which = [2 1]` writes all images plus the mean.
DPARSF introduces **no parameter deviation** from SPM12 master's realign defaults.

---

## Caveats — the scope of the verified claim

Both caveats are stated here rather than downstream, because this doc is destined to become a
`version_default` basis and a KB entry that overstates its own scope is the version-provenance trap.
(Same shape as the still-open wheaton question in `ground-truth-protocol-target_space.md` §169–178: SPM's
bundled template differs by SPM version, and "traceable to a file" is not "resolvable to a value.")

1. **Version scope.** The comparison was against **spm12 `master`**, not any tagged SPM12 release, and
   not the release any given paper used. SPM12 shipped many patch updates. The verified claim is
   *"DPARSF's `Realign.mat` preset matches SPM12 **master**'s realign defaults on all eleven parameters"* —
   **not** that it matches what any paper ran. Likewise the DPABI side is `master`, not a release tag.
   Any KB entry derived from this must carry both version scopes on its face; resolving a specific
   paper's parameters requires pinning both the DPABI/DPARSF release and the SPM12 patch level, neither
   of which is established here.
2. **Component scope.** The file read was **`DPARSF/DPARSFA_run.m`**, inside the DPABI repository. Papers
   typically write "DPABI". DPABI contains DPARSF and DPARSF is its resting-state preprocessing engine, so
   the inference from DPARSF's behaviour to "DPABI's" is almost certainly sound — but it **is** an
   inference, and this doc asserts only what was read. A paper naming DPABI without naming DPARSF, or
   naming DPABISurf (a distinct component with its own pipeline), is not covered by this entry.

Neither caveat is resolvable from what was read. Both are resolvable by pinning releases and re-running
the comparison; that work is not done.

---

## Why this is useful anyway

For the Configurator's `version_default` basis (confidence ceiling 0.95 per the basis taxonomy), the
question "does naming a wrapper leave the underlying parameters underdetermined?" has a concrete answer
for this wrapper at these two versions: **no** — the wrapper reproduces the wrapped tool's defaults
exactly, so a `version_default` inference for SPM12 realign is not degraded by DPARSF sitting in front of
it. That is a narrower and more useful statement than "DPABI is a wrapper," and it is the kind of entry
the KB coverage metric is meant to accumulate.

It also supplies a concrete instance for the KB's wrapper-handling policy generally: **a wrapper must be
resolved to (wrapped tool, parameter deltas), not merely classified as a wrapper.** DPARSF's delta set is
empty at these versions. C-PAC's, FSL FEAT's, and fMRIPrep's are not, and must be established
independently rather than assumed by analogy from this entry.
