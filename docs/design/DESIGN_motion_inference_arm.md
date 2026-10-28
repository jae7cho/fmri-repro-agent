# DESIGN — the inference arm of `motion_correction.method`: the realignment tool from a documented default

**Design only. Written 2026-10-28, after the corpus run (`3dc1ac4`), from the code, the knowledge
base and the stored results.** No code was changed, no model was called, nothing was written under
`results/`. Every fact carries its locator; every proposal is a fork for the author. The three
clean papers are named only by id, with field states; nothing else of theirs was read.

## 0. Rulings — 2026-10-28, by the author, recorded the day they were given

*Sourced to the author's message of 2026-10-28 (the first paste began at the containment line and
dropped them; they arrived with the second). Dated; not backdated.*

**The three rulings from the corpus run.**

1. **The derived level reads the sentence that contains the value token, not the whole span.** A
   code fix with a replay over the recorded draws; no new vintage (the records do not change, the
   projections are re-emitted).
2. **liu_2005 gets a recorder run on its de-interleaved slice**, K=10, under Amendment 14, reported
   beside the corpus result and never pooled with it; its clean cell is already spent.
3. **The wrapper-named shape (chen, oconnor, weber) is not a stanza item.** The inference arm handles
   it through `base_pipeline`.

**The one fact that changes the design, in the author's words.** The contract forbids an inferred
default beside an `EXTRACTED` field, and `described_only` is `EXTRACTED` because it carries the
paper's phrase in a tool-valued slot. That is a conflation — the paper asserting the step and the
paper naming the tool are two facts — and the structural fix is to split them into "performed" and
"method", a schema migration, not before 2026-11-09. For now the inference goes in as a diagnostic on
the processed layer for `described_only`, in the JSON with basis and source, rendered with the same
line; the real inference arm fills `deferred` and `missing`. Same wording either way: the reader
cannot tell the difference and the provenance can. The package basis reads `base_pipeline.name`,
which the main call already extracts (that is why SPM, FSL and AFNI appear there unrecognized), so
the frozen stanza need not express package attribution at all.

**The seven forks, ruled.**

- **F1, the contract.** `deferred`-with-pipeline-target and `missing` take the inference arm proper;
  `described_only` takes the same inference as a **diagnostic on the processed layer**, in the JSON
  with basis and source, rendered with identical wording. The split into "performed" and "method" is
  recorded as the structural fix, after SfN, with this conflation as the reason.
- **F2, precedence.** A recognized pipeline with a certain version wins; otherwise the package basis
  is primary and the pipeline default is an `alternative_inference`. The loser is always listed as an
  alternative.
- **F3, the pipeline basis.** `version_default` at its ceiling when the version is certain;
  `date_inferred_version` at 0.75 when the KB entry marks the realignment tool stable across the
  inferred range. The certain-version gate is relaxed **for this field only**, on that condition.
- **F4, the package basis.** `derived`, ceiling 0.70, `source_field_ids = ["base_pipeline.name"]`, a
  note naming package, program and source. No new basis type.
- **F5, FieldMeta.** `inference_applicable` flips to `True` with a dated catalog entry.
- **F6, C-PAC.** The no-defaults policy stands for parameters; the realignment tool is recorded per
  version range from the default pipeline config. Where a paper cites its own config file (oconnor's
  ref 64), that is a citation-hop target, noted.
- **F7, the package table.** It lives in the KB under `kb/tools` with a reader; the fallback's
  listed-package check reads the same table. One source.

**Pre-declared reach on `batch_motion_corpus_v1` under these rulings, per paper and per basis,
written before the build** (from §2.1 and the corpus findings; "arm" = the inference arm proper,
"diagnostic" = the processed-layer diagnostic of F1):

| paper | motion extraction | base_pipeline → basis | path | expected |
|---|---|---|---|---|
| vanderwal_2016 | deferred to C-PAC (pipeline) | `cpac`, version date-inferred → P at 0.75 **if** the KB marks 3dvolreg stable across the inferred range | arm | filled by P, conditional on the range mark |
| agtzidis_2020 | missing (quote unresolved) | `SPM12` → T (SPM → Realign) | arm | filled by T, 0.70 |
| liu_2013 | described_only | `FCP analysis scripts`, version extracted → P at 0.95 once the FCP doc exists | diagnostic | filled by P |
| chen_2015 | described_only | `ccs`, date-inferred → P at 0.75 on the range mark | diagnostic | filled by P, conditional |
| oconnor_2017 | described_only | `cpac`, version extracted → P at 0.95; its own config file a citation-hop target, noted | diagnostic | filled by P |
| weber_2024 | described_only | `cpac`, date-inferred → P at 0.75 on the range mark | diagnostic | filled by P, conditional |
| mueller_2021 | described_only | `Statistical Parametric Mapping 12` → T | diagnostic | filled by T, 0.70 |
| derosa, gordon, ciric | named_tool | — | never | not filled |
| power, binder, poldrack, cole | described_only, no base pipeline on the record | — | none | not filled: nothing to infer from |
| braun, viduarre | deferred to papers | — | none | not filled |
| liu_2005 | no motion field (`methods_not_found`), no base pipeline | — | none | not filled |
| tang_2025, wheaton_2004 | described_only; a base-pipeline name, unrecognized | T if the name is a listed package | diagnostic | **filled-or-not only, reported as a count** |

Counts expected: arm 2 (P 1 conditional, T 1); diagnostic 5 (P 4, of which 2 conditional; T 1);
never 3; nothing to infer from 7 (the three clean rows counted only as filled-or-not). Both bases
apply to no paper on the record, so F2's precedence is not exercised here.

## 1. Scope

- **The field.** `motion_correction.method` is a `ProvenancedField[SpecifiedTerm[MotionCorrectionMethod]]`
  (`preprocessing.py:697`): an extraction arm and an inference arm, coupled by the frozen provenance
  contract. Today its inference arm is always `NOT_APPLICABLE` (extraction `EXTRACTED`) or
  `LEFT_MISSING` (extraction `MISSING_FROM_PAPER` or `DEFERRED_TO_CITATION`): nothing fills it.
- **What this design fills.** The inference arm with **the realignment tool** — the program — when the
  extraction arm carries no tool: (a) `status = deferred` with a **pipeline** target; (b) `status =
  missing`; (c) binding `described_only` (the paper's own words, a phrase, not a tool). **Never when
  the binding is `named_tool`.** **Never changing the extraction arm.** The report says what the
  paper said and then what AESPA infers, never presenting the inference as reported.
- **What it does not do.** It does not score; it does not touch the stanza (frozen at `b0093774…`,
  Amendment 12); it does not change the labels; it does not read a held-out paper's text. Its
  evaluation is against documentation, as counts of papers filled per basis, with no accuracy figure.

## 2. Facts the design rests on (Part A)

### 2.1 `base_pipeline` in the two batch runs — identical in both (acceptance `batch_a1_acceptance`, 2026-09-07; `batch_motion_corpus_v1`, 2026-10-27)

| paper | base_pipeline extraction | name (the model's) | `recognize()` | version: extraction / inference |
|---|---|---|---|---|
| power_2014 | MISSING | — | — | — |
| binder_1999 | MISSING | — | — | — |
| liu_2013 | EXTRACTED | `FCP analysis scripts` | **None** | EXTRACTED / NOT_APPLICABLE |
| derosa_2025 | EXTRACTED | `FSL suite` | **None** | EXTRACTED / NOT_APPLICABLE |
| agtzidis_2020 | EXTRACTED | `SPM12` | **None** | MISSING / LEFT_MISSING |
| poldrack_2015 | MISSING | — | — | — |
| ciric_2017 | EXTRACTED | `XCP Engine` | **None** | MISSING / LEFT_MISSING |
| braun_2015 | DEFERRED (paper) | — | — | — |
| viduarre_2017 | DEFERRED (paper) | — | — | — |
| vanderwal_2016 | EXTRACTED | `C-PAC` | `cpac` | MISSING / INFERRED_DEFAULT (`date_inferred_version`) |
| cole_2013 | MISSING | — | — | — |
| gordon_2014 | EXTRACTED | `SPM8` | **None** | MISSING / LEFT_MISSING |
| mueller_2021 | EXTRACTED | `Statistical Parametric Mapping 12` | **None** | MISSING / LEFT_MISSING |
| chen_2015 | EXTRACTED | `Connectome Computation System` | `ccs` | MISSING / INFERRED_DEFAULT (`date_inferred_version`) |
| oconnor_2017 | EXTRACTED | `C-PAC` | `cpac` | EXTRACTED / NOT_APPLICABLE |
| weber_2024 | EXTRACTED | `C-PAC` | `cpac` | MISSING / INFERRED_DEFAULT (`date_inferred_version`) |
| liu_2005 | MISSING (inference LEFT_MISSING) | — | — | — |
| tang_2025 | EXTRACTED | *(not read)* | *(counted below)* | MISSING / LEFT_MISSING |
| wheaton_2004 | EXTRACTED | *(not read)* | *(counted below)* | MISSING / LEFT_MISSING |

Held-out, counts only: 2 of 3 carry an extracted base-pipeline name, **0 of 3 recognized**.
**`recognize()` knows pipelines, not packages:** `C-PAC`/`CPAC` → `cpac`, `CCS` and the full name →
`ccs`, `fMRIPrep` → `fmriprep`, `HCP minimal preprocessing` → `hcp_minimal`; `SPM`, `SPM12`, `FSL`,
`AFNI`, `HCP`, `DPARSF`, `CONN`, `FCP analysis scripts` → `None` (`registry.py:105-132`: id,
display name and aliases, with the `Full Name (ACRONYM)` convention and an ambiguity guard). Four
of the sixteen name a recognized pipeline (vanderwal, oconnor, weber: `cpac`; chen: `ccs`); five
name a package the registry does not know (agtzidis, gordon, mueller: SPM; derosa: FSL; liu_2013:
the FCP scripts — a pipeline absent from the KB); ciric names a pipeline absent from the KB.
**A certain version** (`certain_version`, `base_pipeline.py:249`) exists for liu_2013, derosa and
oconnor (extracted); vanderwal's, chen's and weber's are `date_inferred_version` (confidence 0.75) and
would not pass the gate — so under the seven-field rule none of the three recognized pipelines whose
version is only date-inferred would be filled, which is what F3 is about.

### 2.2 The knowledge base

- **The four pipeline docs** (`fmri-defaults-kb/kb/pipelines/{ccs,cpac,fmriprep,hcp_minimal}.yaml`)
  **carry no motion or realignment default today**: no line mentions motion, realignment, MCFLIRT or
  3dvolreg; `component_tools: []` in all four. Their `param_defaults` paths are: ccs — five
  (`intensity_normalization.convention`, `.value`, `spatial_normalization.resolution_mm`,
  `.target_space`, `surface_projection.surface_registration`); hcp_minimal — seven (those plus
  `surface_projection.target_surface`, `temporal_filtering.effective_band_hz`); fmriprep — one
  (`surface_projection.surface_registration`, a conditional); cpac — **none, by a stated policy**
  (`cpac.yaml` notes: a configure-from-template pipeline shipping ~10 presets, so no default is
  asserted). The schema (`schemas/pipeline_registry.schema.json`) names no motion path.
- **`ParamResult`** (`registry.py:77-86`): `value` (a concrete default, the `NotApplicable` sentinel,
  or an unresolved `ConditionalParam`), `basis_type` (`"version_default"` or `"derived"`),
  `proposed_confidence`, `source`, `alternative_candidates`.
- **Basis types and ceilings** (`provenance.py:22-29`, "reasoned, not measured"): `version_default`
  0.95 · `date_inferred_version` 0.75 · `prior_publication` 0.60 · `lab_prior` 0.50 ·
  `field_convention` 0.40 · `derived` 0.70. The union is a frozen discriminated `Basis`
  (`:125-133`); `InferredDefault` validates its confidence against the ceiling (`:153-163`).
- **`kb/tools`: 0 entries**, confirmed by a directory count; unread, since there is nothing in it.
  fMRIPrep's per-flag inventory is deferred to it by the docs' own notes.

### 2.3 The fill path, and what adding the motion method touches

- **`fill_dependent_defaults`** (`base_pipeline.py:176-213`) fills the seven KB-backed fields only
  when `recognize(name)` resolves **and** the version is **certain** — extraction `EXTRACTED`, or
  inference `INFERRED_DEFAULT` with basis `version_default` (`certain_version`,
  `:249`); a `date_inferred_version` never fills ("we don't stack params on a merely inferred
  version"). It is called from the extractor's **base-pipeline deferral branch only**
  (`extractor.py:1711-1725`), with a paper date; for an *extracted* base pipeline only the version is
  inferred (`:1700-1707`, deliberately not the fill). The replay gate never calls it.
- **`SEVEN_DEMOTED_FIELDS`** (`:64-72`): seven `(step_kind, attribute)` pairs over four step kinds
  (`_KIND_TO_CLASS`, `:74-79`). **Adding `("motion_correction", "method")` touches:** that tuple and
  its name; `_KIND_TO_CLASS` (+ `MotionCorrection`); `_apply_param_result` (`:291`), which
  writes the KB's raw value and would have to build a `SpecifiedTerm` for this field; the KB's
  `get_param_defaults` field paths and the four pipeline docs (+ a `motion_correction.method`
  path, which the schema does not yet name); and the call site, since the base-pipeline branch
  that runs the fill today is the *deferral* branch, while the motion case needs the extracted-name
  branch too.
- **`MotionCorrection`'s `method` FieldMeta** (`preprocessing.py:150`): `justification_axis="both"`,
  **`inference_applicable=False`**, `source="derived"`. The flags "come from
  `docs/spec/preprocessing_catalog_v0.1.0.md`; the conservative bias is extracted-or-missing unless
  a base pipeline supplies a defensible default" (`:115-118`). Turning the arm on flips this flag
  by a catalog ruling, not by code alone.
- **`couple_stages`** (`provenance.py:192-202`): **`EXTRACTED` requires inference `NOT_APPLICABLE`**
  ("Configurator must not touch extracted values"); `MISSING_FROM_PAPER` and `DEFERRED_TO_CITATION`
  require `INFERRED_DEFAULT` or `LEFT_MISSING`. So when the extraction arm is `EXTRACTED` with
  binding `described_only` — the paper's phrase, a valid extraction — **the contract forbids an
  `INFERRED_DEFAULT` beside it.** `_apply_param_result` returns early on an extracted field for the
  same reason (`:306`). Scope item (c) is blocked by the frozen contract as the field stands.

### 2.4 The corpus run's deferral targets (recorder, 190 draws)

| paper | deferred draws | target kind | `ref_string` | recognized |
|---|---|---|---|---|
| vanderwal_2016 | 10 | pipeline | `C-PAC` | `cpac` |
| liu_2013 | 4 | pipeline | `FCP analysis scripts (version 1.1-beta)` | None |
| poldrack_2015 | 5 | paper ×3, pipeline ×2 | `45` | None |
| braun_2015 | 10 | paper | `47 and 48` / `refs. 47 and 48` | None |
| viduarre_2017 | 10 | paper | `Smith et al. (18, 39)` / `Glasser et al.` | None |
| held-out three | 9 (tang 7 paper, wheaton 2 pipeline) | — | *(not read)* | **0 of 9** |

One recognized pipeline target in the whole run: vanderwal's. The base-pipeline field is the
richer source (§2.1): the recorder's deferral carries the pipeline only when the motion sentence
itself defers to it.

### 2.5 Documented realignment defaults, with a source each — proposed for the author's check

| pipeline or package | realignment program | source | status |
|---|---|---|---|
| fMRIPrep | FSL `MCFLIRT` (head-motion estimation) | Esteban et al. (2019), *Nature Methods* 16:111–116; the fMRIPrep documentation, "Head-motion estimation" | sourced |
| HCP minimal (fMRIVolume) | FSL `MCFLIRT` via `MotionCorrection.sh` (FLIRT-based) | Glasser et al. (2013), *NeuroImage* 80:105–124; the HCP Pipelines scripts | sourced |
| C-PAC | AFNI `3dvolreg` as the shipped default; `mcflirt` selectable | the C-PAC user documentation (functional preprocessing, motion correction) and the default pipeline configuration | **documentation, version-dependent: pin the version at the author's check** |
| CCS | AFNI `3dvolreg` | Xu et al. (2015), *Science Bulletin* 60:86–95; the CCS functional preprocessing script | **script-sourced: the paper's statement to be verified** |
| FCP scripts (1000 Functional Connectomes) | AFNI `3dvolreg` | Biswal et al. (2010), *PNAS* 107:4734–4739; the NITRC `fcon_1000` preprocessing scripts | **script-sourced: not cited from the paper; to be verified** |
| SPM (any version) | `Realign` (`spm_realign`) | Friston et al. (1995), *Human Brain Mapping* 3:165–189; the SPM12 Manual | sourced (protocol v1.8's list) |
| AFNI | `3dvolreg` | Cox (1996); Cox & Jesmanowicz (1999), *Magn. Reson. Med.* 42:1014–1018 | sourced (v1.8) |
| FSL | `MCFLIRT` | Jenkinson et al. (2002), *NeuroImage* 17:825–841 | sourced (v1.8) |
| ANTs | `antsMotionCorr` | the ANTs source distribution, `Examples/antsMotionCorr.cxx` | sourced (v1.8) |

Marked: C-PAC (version-dependent), CCS and the FCP scripts (script-level evidence, no page to cite).
Nothing here was read from a paper in the corpus.

## 3. The two bases — forks for the author

**Basis P — a recognized base pipeline.** `recognize(base_pipeline.name)` (or the motion deferral's
pipeline target) resolves to a KB pipeline whose document carries a `motion_correction.method`
default. The KB today has none (§2.2); the four docs would gain one each, with a source (§2.5), and
the FCP scripts would need a document of their own. *Version-aware where the paper gives one:*
the default is looked up at the certain version when the paper pins one; when the version is only
date-inferred the realignment program is, for these pipelines, the same across the versions the KB
lists, and the fork is whether that stability licenses a fill the seven-field path refuses.

**Basis T — a package-attributed tool.** The paper names a listed package (protocol v1.8's list)
for its preprocessing as a whole — on the record as the base pipeline's name (agtzidis, gordon,
mueller: SPM; derosa: FSL) or as column R's `package` — and the package → program table (§2.5)
supplies the tool. The registry knows no package today; the table is new, and where it lives is a
fork (a `kb/tools` entry per package, or a small table in `kb_client`).

| fork | options | my recommendation, for ratification |
|---|---|---|
| **F1 — the contract for `described_only`** | (i) narrow the scope to `deferred`-to-pipeline and `missing`, where `couple_stages` allows `INFERRED_DEFAULT`; (ii) carry the inference for a `described_only` extraction somewhere other than the field's inference arm — a render-time line computed from `base_pipeline`, with no provenance object; (iii) amend the frozen contract so a `described_only` `EXTRACTED` motion method may carry an inference | (ii) for the report, (i) for the field: the extraction arm is untouched by construction, the contract stays frozen, and the paper's words still head the line. (iii) is the only option that gives the inference a provenance object, and it is a contract change |
| **F2 — which basis wins when both apply** (a recognized pipeline *and* a named package, e.g. a paper naming C-PAC and FSL) | pipeline first, package as `alternative_inferences`; or package first | pipeline first: the pipeline fixes the program it calls; the package is the broader claim |
| **F3 — the basis type and ceiling for P** | `version_default` (0.95) only at a certain version, as the seven fields do; or allow `date_inferred_version` (0.75) for this field because the program is version-stable; or `prior_publication` (0.60) citing the pipeline paper when no version is certain | `version_default` at a certain version; `prior_publication` otherwise, citing §2.5's source — no new basis type, so the frozen union stands |
| **F4 — the basis type and ceiling for T** | `prior_publication` (0.60, the package's realignment paper); `field_convention` (0.40); a new type | `prior_publication` at 0.60: it is a documented program, not a field convention |
| **F5 — the `inference_applicable` flag** | flip `method` to `True` by a catalog ruling; or leave it and gate the fill elsewhere | flip it, with the catalog line that today justifies `False` superseded by a dated note |
| **F6 — C-PAC's "no defaults" policy** | keep the KB's policy and fill C-PAC papers from basis T only when a package is also named (none of the three is); or carve out `motion_correction.method` as the one C-PAC default with a stated reason | carve out, version-pinned, with the reason that the program is not a preset choice |
| **F7 — where the package table lives** | `fmri-defaults-kb/kb/tools/<package>.yaml` (the deferred Sub-A home); or `kb_client` in this repo | the KB repo: it is a documented default, which is what the KB holds |

## 4. The report line

The paper's words first, then the inference, never presented as reported:

> *"<the paper's own words, or the deferral target, or "not stated">"* — tool not stated; **AESPA infers
> `<program>`** (<basis>, <source>).

Three cases: `described_only` — the phrase, then the inference (via F1); `deferred` to a pipeline —
"deferred to <pipeline>", then the inference from that pipeline's documented default; `missing` —
"not stated", then the inference from the base pipeline or the package. For `named_tool` the line is
unchanged: no inference is offered. The COBIDAS row's status does not move: an inferred program is
not a reported one, so the row stays as the extraction arm leaves it (addressed by extraction or
deferral, or the unverifiable-gap wording), with the inference as an appended clause. `render.py`
already carries the `INFERRED_DEFAULT` state and its `basis_type` (`:182`, `:195`, `:221-222`,
`:360`); the motion row's line is the new wording.

## 5. Evaluation — against documentation, not labels

- **The question** is reach and basis, not correctness: for each paper, *was the inference arm filled,
  from which basis, and does that basis have a citable source* (§2.5). The inferred program is the
  documented default by construction; nothing is compared with column C, and no accuracy figure is
  computed. Counts of papers filled per basis, by contamination class, the clean three as states and
  counts only.
- **Applied to `batch_motion_corpus_v1` as a processed vintage, with no model call:** the stored
  JSONs are read, the fill is applied, and the result is written as a new vintage
  (`batch_motion_corpus_v1_inferred`, under `results/`, untracked), re-rendered, and projected
  without text. The three clean cells are not re-spent by a processed pass; their rows are still
  read as states and counts.
- **Expected reach on that vintage, from §2.1 and the batch projection**, pre-declared as a design
  expectation and not a result: under the contract as it stands (F1-i), **vanderwal** (basis P, C-PAC,
  if F6 carves the default out; its motion field is deferred to the pipeline) and **agtzidis** (basis
  T, SPM → Realign; its motion field is `MISSING` with an unresolved quote) — 2 papers; with F1
  resolved for `described_only`, also **chen** (ccs), **oconnor** and **weber** (cpac) by P and
  **mueller** by T — 6 papers; **liu_2013** only once the FCP scripts have a KB document. **derosa,
  gordon, ciric** carry `named_tool` and are never filled. **power, binder, poldrack, cole** name no
  pipeline and no package on the record: nothing to infer from. braun and viduarre defer to papers,
  not pipelines. The held-out three: 0 recognized pipelines, so basis P fills none; basis T is a
  count to be reported, not pre-declared here.
- **The identity gate, derived before any build:** the processed pass writes a new vintage and
  touches no stored acceptance JSON, so `--against HEAD` on `batch_a1_acceptance` is **19 identical**
  *if* the new report wording is reachable only through an `INFERRED_DEFAULT` on the motion method —
  no acceptance JSON carries a motion step, so none can reach it — and nothing else in `render.py` or
  `cobidas.py` moves. If the motion row's wording changes for rows *without* an inference, every
  stored report changes, and the expected number must be re-derived before the run (design doc §3f;
  the `d31e8b7` negative control runs either way).

## 6. Open forks — not settled here

F1–F7 above, and:

8. **The vintage statement.** A processed pass that fills the inference arm re-vintages the motion
   field only; the other fields of `batch_motion_corpus_v1` stay as written. The results document
   names both vintages.
9. **The FCP scripts as a KB pipeline**, and `XCP Engine`, which the registry does not know either.
10. **Version-pinning C-PAC's default** across the versions the KB lists (0.3.2 to 1.5.0 and later).
11. **The held-out three under basis T**: whether a package-attributed fill on a clean paper is reported
    by id as a state, or only in the clean line's counts.
12. ~~The three rulings of 2026-10-28~~ — recorded in §0 on 2026-10-28, and in the corpus findings.
