# DESIGN: the prompt and schema change after the 2026-11-24 card review

**Design, written 2026-11-24 before any build, from the code at HEAD `0d9122c`.** Part A is
read-only fact with locators. Part B is the proposed change, one section per item of the
extraction error list (DEVLOG.md, entry 2026-11-24 (5)). Part C lists the decisions put to the
author. Part D is the build order, the checks and the run. No prompt, schema, hash pin or code has
been changed for this note, and no model call has been made.

**Since then:** D1 and D1b (2026-11-24) and D2b (2026-11-25) are done; Part D says what each
found or built. D1 was read-only; D1b and D2b changed code, scripts and tests. No prompt, schema
or hash pin has changed, and no model call has been made.

The change is one vintage event. Every prompt it touches is re-pinned together, so the run after
it measures one prompt set, not a sequence of them.

## 0. Rulings, 2026-11-24, by the author

> C1-C5 "ok": the recommendations stand. Schema 0.8.0 for this change; multi-echo becomes 0.9.0.
> The intersubject partial rule extends to method and warp once they are extracted. Method fields
> stay the tool; labels naming a technique are relabelled. Rulings 8, 12 and 13 go in the
> inference arm. The audit patch's text cleanups are folded in, its effort switch left out.
> C6: "why does it cost so much? no run yet". No run is planned; the cost breakdown and the
> savings options are in C6.

**2026-11-25, by the author, on the three decisions D1 left (C7 to C9):**

> "C7 ok, C8 ok, C9 ok. start D2b"

- **C7:** the recommendation stands. The model returns the paper's term and the member it reads
  the term as, and the alias table checks that member. It is built in D3 (schema) and D4
  (prompts).
- **C8:** the main text wins over a supplement's generated summary (B13, in D4).
- **C9:** every addition is accepted. Two of its items gave two options and no recommendation,
  and stay open: "N3" as an alias of `n4` (keep or remove), and smoothing_approach (defined in the
  prompt, or left to the inference pass). They are listed again under C10.
- **D2b** is built (Part D). What it leaves for the author is C10 to C14.

## Part A: facts, read-only, at HEAD `0d9122c`

Abbreviations: EX = `extractor_mvp/src/extractor_mvp`, PP = `src/fmri_repro/spec/preprocessing.py`,
PIN = `extractor_mvp/tests/test_prompt_pin.py`.

### A1. Prompts and pins

- Model-facing prompts and their pins:

  | Prompt | Defined | Pin |
  |---|---|---|
  | EXTRACTION_PROMPT (includes VARIANT_RULES, QUOTE_RULES, PREPROCESSING_RULES) | EX/extractor.py:227-465 | PIN:39 |
  | PER_ACQUISITION_EXTRACTION_PROMPT (a prefix + EXTRACTION_PROMPT) | EX/extractor.py:1681 | PIN:48-50 |
  | TEMPORAL_VOLUME_PROMPT (call T; `_SHARED_RULES` 55-110, `_OUTPUT_STATUS` 112-135) | EX/coverage_extractor.py:137-254 | PIN:220 |
  | SPATIAL_PROMPT (call S) | EX/coverage_extractor.py:256-356 | PIN:257 |
  | VERIFIER_PROMPT (the checking pass; includes CHECKING_RULES) | EX/verifier.py:42-117 | PIN:268 |
  | MOTION_METHOD_PROMPT | EX/extractor.py:1870 | PIN:179; also frozen by `motion_probe.py:270` |
  | HOP_ADDENDUM + `_TOOLS_ASK`, RELEASE prompts, SOFTWARE_USE_PROMPT, FMRI_GATE_PROMPT | citation_hop.py, software_scan.py, fmri_gate.py | PIN:430-499 |

- **A pin** is `sha256(prompt.encode("utf-8"))` against a hard-coded hex in `_PINNED` (PIN:30-269).
  Three hashes are copied again at PIN:388-396.
- **A re-pin** is a new hash with a `#: UPDATED <date> (...; a vintage event, deliberate)` comment
  naming the superseded hash and "Not yet drawn". There is no vintage registry file.

### A2. What the prompts say now about the nine items

- **Inference forbidden:**
  - EX/extractor.py:237-238: "Do not infer values from the named pipeline. Do not fill in defaults
    you might know."
  - The FIREWALL at EX/extractor.py:289-294.
  - EX/coverage_extractor.py:80-85: no tool, value or performed from "your own knowledge of what a
    package does by default".
  - Rulings 8, 12 and 13 exist only in `scripts/merge_labels.py:170-175`.
- **Order:** EX/coverage_extractor.py:228-231 governs step_order only. Nothing lets a value follow
  from stated order.
- **Performed:** "yes" when "the text states the step was done", with the sentence that names the
  step (EX/coverage_extractor.py:59-62, 70-72). Nothing says whether a bare mention ("Denoised fMRI
  data") counts.
- **Method fields mean the tool:**
  - nuisance_method: "the tool named for the regression" (EX/coverage_extractor.py:203-204);
  - scrub_method: "the tool named for the censoring" (:177-178);
  - coregistration_method: "the TOOL that performed the registration" (:292-295);
  - stc_method: "the software/tool named FOR this step" (:159-160).
  - FieldMeta has no description field (src/fmri_repro/spec/refs.py:15-31).
- **Datasets in VARIANT_RULES:** "a dataset" appears in the sub-bullet at
  EX/prompt_rules.py:55, not in the trigger list at :50-52.
- **Pipeline defaults:** a step that followed a named pipeline is "deferred" with
  `target_kind="pipeline"` (EX/coverage_extractor.py:63-68, 76-78). schwartz_2018 in
  `corpus_full_v3` names CONN as base_pipeline with `deferred_fields: []`, so no KB fill ran.

### A3. Vocabulary resolution

- **Who resolves:** the model returns a string; code resolves it with `_resolve_term`
  (EX/extractor.py:1160-1186). In order: "other (phrase)" → `other`; then the field's alias table
  by substring and alias match (EX/synonym_resolver.py:227+); then an exact member; else
  `resolved=None`.
- **The 6param error is in the alias table:** `"6 parameters"` is a 6param alias
  (EX/coverage_fields.py:184-212). So "6 parameters and their first order derivatives" resolves to
  6param in code, whatever the model does. A model that returns the bare token "6param" also loses
  the paper's words.

### A4. Schema

- **Version:** `SCHEMA_VERSION = "0.7.4"` (PP:1591).
- **Convention** (src/fmri_repro/spec/migrations.py:21-37):
  - adding an enum value or an optional field is a patch bump with a re-stamp hop;
  - a type change is structural: a minor bump with a doc-transform hop.
- **Motion expansion:** `MotionExpansion = Literal["none", "6param", "friston24", "volterra"]`
  (PP:1214).
- **Spatial normalization:**
  - `method` (PP:1101-1103) and `warp` are bare Literals, not SpecifiedTerm, so an unmapped term
    cannot be recorded with its words;
  - both are hand-filled as `not_targeted_by_mvp` in `_assemble` (EX/extractor.py:1536-1544);
  - spatial_normalization is not in CALL_S_KINDS (EX/coverage_fields.py:73-80).
- **Multi-echo** is designed as schema 0.8.0 and not built (docs/design/DESIGN_multi_echo.md:12).
- **Inference arm:** the only inference status is `INFERRED_DEFAULT`, refused on a field whose
  FieldMeta has `inference_applicable=False` and, where `inference_requires_kb_source` is set,
  without a KB source (PP:807-812).

### A5. The prompt audit patch

`docs/findings/prompt_audit_fable52.patch` (untracked) removes dated provenance and "CRITICAL:"
framing from `_SHARED_RULES`, `_OUTPUT_STATUS`, EXTRACTION_PROMPT, VARIANT_RULES and
VERIFIER_PROMPT, condenses one list, and adds an `AESPA_EFFORT` switch. Arm C (B + the patch) and
arm B were identical on every label set (DEVLOG.md, 2026-11-15).

### A6. D1: where the vocabulary values come from (2026-11-24, at HEAD `0c8c700`)

Read-only; the project code made no model call. Scripts, inputs and every list are in
`extractor_mvp/results/d1_token_audit_2026-11-24/` (gitignored; REPORT.md). Held-out papers are
excluded by file name throughout. Every resolver result here was re-run with that folder's
`resolve_cli.py`, which calls `_resolve_term` and `resolve_to_literal`. The coders, finders,
verifiers and critic named below were Claude Code subagents (40, in one workflow): session usage,
not an extraction run. Their transcripts show reads of the resolver's source and its test file,
the prompts, the spec, the labelling rulings, this document and pre-extracted quotes of
non-held-out papers, and of nothing else in the repository (REPORT.md, section 4).

- **Both tokens are the model's, as the prompt instructs.**
  - `_SHARED_RULES`: "Typed fields: use the canonical value when the paper's term maps to one"
    (EX/coverage_extractor.py:102-105). Code stores the returned string as `verbatim`
    (EX/extractor.py:732, 743, 1180-1182). For a mapped value the paper's term is only in the
    quote, although the 0.5.0 rule reads "the paper's words always kept" (EX/extractor.py:1166).
  - **bold_pct is forced** (schwartz_2018, scrub criterion; arm S and `corpus_full_v3`). The quote
    reads "> 3 standard deviations of average signal or >.5mm framewise displacement"; the label
    reads "global signal change > 3 SD, or framewise displacement". The quote's own words resolve
    to no member, which is correct. Two gaps show: no criterion member for a global-signal
    threshold, and `threshold` holds one number (3.0 kept, 0.5 lost).
  - **fieldmap_less is not forced** (ladouceur_2023, distortion source; arms S, B and C). The
    supplement says '"Fieldmap-less" distortion correction was performed'; the main text says
    field maps were acquired "for correction of field distortions". The label follows the main
    text, the author's decision of 2026-11-19 for hermans_2024, recorded in the label notes only.
    hermans_2024 has the same shape in every arm: `performed` is no, quoting the supplement's
    "Susceptibility distortion correction (SDC) was omitted". No prompt carries the rule (B13).
- **Most values are tokens, so the alias tables have met few real wordings.**

  | Arm (24 papers) | Vocabulary values | Bare member token | In words | Words a table resolved |
  |---|---|---|---|---|
  | S | 407 | 323 | 83 | 20 |
  | B | 360 | 277 | 81 | 14 |
  | C | 365 | 282 | 83 | 13 |

  D1b's audit re-resolved stored wordings, so it could not see a wording the model had replaced
  by its token.
- **15 of 448 aliases do not resolve to their own member** (each alias given as the wording):
  - slice_time_correction.reference, 6: "first slice", "middle slice", "central slice",
    "centre slice", "center slice", "middle of the TR". `specific_slice` has the alias "slice" and
    `middle` has "middle", so two members match and the value stays unresolved;
  - coregistration.method, 3: "FLIRT BBR", "FLIRT with BBR", "FLIRT (BBR)" (`flirt` has "FLIRT");
  - distortion_correction.source, 2: "fieldmap-less", "field map-less"
    (`susceptibility_fieldmap` has "fieldmap" and "field map"); ambiguous since `86cba81`, the
    commit that added them;
  - surface_projection.target_surface, 2: "fsaverage 5", "fsaverage 6" (`fsaverage`'s alias; the
    containment rule at EX/synonym_resolver.py:254-274 drops the shorter alias only when a letter
    or digit follows it);
  - distortion_correction.method, 2: "blip-up/blip-down", "blip up/blip down". The list splitter
    cuts at "/" (EX/extractor.py:1137) before any alias is tried.
  - All 15 predate `ed97a8d`. Before it there were 16: the whole-word rule fixed "infinite impulse
    response", which had matched `fir`'s alias inside "infinite".
  - On distortion_correction.method the same word goes to the opposite member: "fieldmap-less"
    resolves to `fieldmap`.
- **`ed97a8d` cost the versioned tool names.** "SPM12", "SPM8", "SPM5" and "SPM99" resolved to the
  SPM members by substring. As whole words they resolve to nothing. No stored value moved: the 322
  stored wordings change in the same 13 places D1b reported. The quotes of maheu_2011, shen_2013
  and agtzidis_2020 name SPM this way.
- **Token trace: how each stored token is supported by its own quote.** A case is one (paper,
  field, token, quote) in arms S, B and C: 564 cases. Code settles 370: an alias of the token's
  member is in the quote, and no alias of a member the record did not also return. Two
  independent coders coded the other 194 from the quote and the field's definition; a third
  settled 18 disagreements; two codings were corrected afterwards, because the case file had
  listed their spans out of text order.

  | How the quote supports the token | S | B | C |
  |---|---|---|---|
  | An alias of the member is in the quote, none competing (code) | 202 | 195 | 191 |
  | A term names it, and that term resolves to the member | 16 | 24 | 27 |
  | A term names it, and that term does not resolve | 17 | 12 | 14 |
  | Described in other words (an order word, a stated band) | 13 | 11 | 14 |
  | Inferred: nothing is said | 21 | 10 | 8 |
  | Inferred: the order in which steps are listed | 12 | 7 | 9 |
  | Inferred: a convention (a named model, a bare "detrending") | 10 | 10 | 5 |
  | Inferred: a tool's default, or other outside knowledge | 12 | 3 | 3 |
  | Unsupported by the quote | 6 | 0 | 1 |
  | Contradicted by the quote | 4 | 0 | 0 |
  | Total | 313 | 272 | 272 |

  - **Named, not resolving (30 distinct cases):**
    - 6 are text artifacts that the quote check's repair removes and the resolver never sees:
      the "ﬁ" ligature in "ﬁeld map" (poldrack_2015), "B 0" (hagler_2019), "32 k fs_LR"
      (marek_2022). On the repaired text the resolver returns the member for all 6;
    - 2 the repair does not fix: a fused "phaseencode" (hagler_2019) and a term split across two
      spans;
    - 4 are the versioned SPM names above, and 2 are "Fieldmap-less";
    - 13 are wordings the tables lack: six for motion expansion ("6 motion estimates", "six head
      movement components", "six motion-related signals"), "gradient nonlinearity" on the method
      field (only the plural is an alias), "prior to confound regression", "customized", "remove",
      "grand 4D mean normalization to 10,000";
    - 3 are `other` for a tool or design outside the list (BioImage Suite, a Gaussian filter),
      which no alias can return.
  - **Inferred from nothing said (33 distinct):** `fixed_kernel` from a stated kernel size (17,
    in every arm). In arm S only: physio `none` (11) and motion `none` (3) from a regressor list
    that omits them, and `custom` (2) where no tool is named.
  - **Inferred from listing order (18):** slice timing before motion correction (6), filtering
    before or after regression (10), smoothing in template space (2). These are ruling 8's cases.
  - **Inferred from a convention (19):** 16 are ciric_2017's tissue regressors, read off "9
    regressors" or "36P"; 2 are `linear` for a bare "detrending".
  - **Unsupported or contradicted (11 distinct: arm S 10, B 0, C 1).** In arm S:
    - smoothing space `native_surface` where the quote names fsaverage, the grayordinate standard
      space or the 32k fs_LR surface (chen_2015, glasser2016_nature, poldrack_2015), or only
      "surface data" (marek_2022);
    - stc reference `first` for "the start of each volume" (power_2014);
    - `band_pass` with no filter in the quote (chen_2015), `other` as a scrub and a smoothing
      method with no tool named (ciric_2017), `bbregister` from a T1w-to-T2w sentence
      (glasser2016_nature), and bold_pct.
    - In arm C: surface registration `freesurfer_recon` with no tool in the quote (marek_2022).
- **Sweep: constructed wordings sent to the wrong member.** Seven finders probed 1,839 wordings
  over the 39 fields, written from how methods sections and tool boilerplates word each step and
  not taken from the corpus. They reported 60, and all 60 reproduce. Two verifiers judged each
  one. 52 hold under the field's definition and the dated rulings. For 18 of those, the second
  verifier also judged that a paper would word it so and the model would return it in that field
  (2 of the 18 repeat the 15 above). A critic then found 45 more failing probes that the finders
  had not tried, 28 of them in the list splitter and the "other" rule; all 45 reproduce. A
  wording that only stays unresolved was not counted, since that is the designed behaviour (B12).
  By cause, with examples:
  - **a one-word alias inside a longer term:**
    - "0.5 of slice acquisition range" (fMRIPrep's boilerplate) → `specific_slice`, through
      "slice";
    - "native cortical surface" and "subject's cortical surface" → `template_surface`, through
      "cortical surface";
    - "HD-BET" → `bet`; "fieldmap-free" → `fieldmap`; "non-rigid" → `rigid`;
    - "MNI152 2009c symmetric" → MNI152NLin2009cAsym; "fsaverage_sym" → `fsaverage`;
    - "FD-RMS" → `fd_power`; "Fourier basis set (SPM)" → `ideal_fft`;
    - "SynthSeg (FreeSurfer 7)" → `freesurfer_recon_all`; "MSM folding-based registration" →
      `freesurfer_recon`;
  - **an order word that ignores its subject:** "realignment was performed after slice timing
    correction" → `after`, where the field means slice timing relative to motion correction;
  - **a gap in today's TERM_RULES:** "six motion parameters and their first differences" →
    `6param` (the block list has "deriv", not "differ");
  - **an alias that names another tool:** "N3" is an alias of `n4` (EX/coverage_fields.py:433);
  - **the list splitter** (EX/extractor.py:1137-1157):
    - "ICA+FIX" → an unresolved "ICA" beside `fix`; "anatomical and temporal CompCor" loses `a`;
    - "SPM Realign and Unwarp" becomes two unresolved items;
    - "FD > 0.2 mm/TR" and a decimal comma split inside a number;
    - only the innermost of nested parentheses is protected (:1140), so "other (nonlinear
      registration to the T1w (SyN), without a field map)" yields `fieldmap`;
  - **the "other" rule** (EX/extractor.py:1143, 1170-1174):
    - only "other (X)" and "other: X" are recognised, so "other - CONN toolbox (SPM-based)" →
      `spm`;
    - coregistration_cost_function's prompt line offers "other" (EX/coverage_extractor.py:298) and
      the field has no such member, so "other (normalized correlation, not mutual information)" →
      `mutual_information`.

## Part B: proposed change

Each item names what changes, where, and what decides it. "Prompt" means a re-pin; "schema" means a
version bump; "code" means neither.

### B1. Six parameters plus derivatives (schema + code)

- **Schema:** add `"12param"` to MotionExpansion (the six and their first derivatives). Additive:
  patch bump 0.7.4 → 0.7.5, a re-stamp hop.
- **Code, done before the vintage (2026-11-24, the resolver audit):** `coverage_fields.TERM_RULES`.
  - six with derivatives and squares (or quadratic terms) resolves to friston24;
  - any derivative, square, quadratic, expansion or regressor count blocks 6param, so a wording
    no member fits keeps its words;
  - with 0.8.0, the rule "six with derivatives, without squares" resolves to 12param.
  - Stored records keep the member resolved at extraction, so a resolver change reaches them only
    through `scripts/reresolve_terms.py`. It does not reach them on re-read, as an earlier draft
    of this note said.
- **Prompt (call T):** nuisance_motion_expansion lists 12param.
- **Also:** the project vocabulary contract (tests/kb_client/test_vocab_contract.py) and the XCP-D
  and ABCD KB entries, which use friston24, are unaffected.

### B2. Method and warp for intersubject registration (schema + prompt)

- **Schema:** retype `SpatialNormalization.method` and `.warp` to `SpecifiedTerm[...]`, so an
  unmapped term keeps its words. This is structural (a type change), so a lift hop like 0.5.0's
  `_lift_to_specified_term` and a minor bump are needed. See C1 for the version number.
- **Targeting:** add spatial_normalization to call S, with `_spec("S", ...)` rows and alias tables
  for method (fnirt, ants, ants_syn, spm_normalise, dartel, other) and warp (rigid, affine,
  nonlinear). This follows ruling A (PIN:287-289): new fields go in a call, not in
  EXTRACTION_PROMPT.
- **Assembly:** replace the hand-built SpatialNormalization in `_assemble` (EX/extractor.py:1536)
  with `_build`. Target_space and resolution_mm stay in the shared call.
- **Prompt (call S):** two lines, worded like coregistration's: the tool that performed the
  normalization, and the transform class.
- **Touch-points:**
  - the intersubject partial rule (`cobidas.PARTIAL_FIELDS`), which then can include method
    (C2);
  - the hop field lists (EX/citation_hop.py:543, 857);
  - `kb_client/base_pipeline.py:67-88`;
  - `field_diff.py:24-25`.

### B3. One row per dataset (prompt)

- **VARIANT_RULES:** add "datasets, cohorts or samples" to the trigger list, which reaches
  EXTRACTION_PROMPT, call T, call S and the checking pass.
- **One sentence:** "A paper that preprocesses two or more datasets differently gives each dataset
  its own value for every field where they differ, even when one dataset's preprocessing is cited
  rather than stated."
- **Untouched:** the per-acquisition path, which is the separate multi-acquisition route.
- **Expected effect:** glasser2016_nature, marek_2022 and greene_2022 split where the text states
  the difference. Fields that stay unstated per dataset do not split; that is correct.

### B4. Method fields: tool or technique (decision first, C3)

The schema and every prompt define the method fields as the tool. B's "CONN", "clpipe" or
"DCANBOLDproc" follow that definition. The labels' "regression" or "GLM" name the technique, which
no field holds. This is a definition conflict, not a model error. The recommendation (C3) keeps the
tool and fixes the labels. The alternative is a new technique field. Either way:

- **freesurfer_recon is correct for recon-all** (corrected after the 2026-11-24 audit). recon-all
  runs FreeSurfer's spherical registration (`sphere.reg`), and "recon-all" is a deliberate alias of
  freesurfer_recon (EX/synonym_resolver.py:100-110). marek_2022's and ladouceur_2023's values are
  not errors; an earlier draft of this note said they were.
- **A pipeline is not a step's tool** unless the text says the step ran in it. clpipe or
  DCANBOLDproc for the whole analysis is base_pipeline, not nuisance_method. This restates
  EX/coverage_extractor.py:84-85 in each method line.

### B5. No forced vocabulary term (prompt + code)

- **Prompt (`_SHARED_RULES` and EXTRACTION_PROMPT):** "Return the paper's words. Do not return a
  canonical token unless the paper's words are that token or plainly name it; code maps the
  words." This removes the model's half of the 6param, bold_pct and fieldmap_less errors.
- **Code, done before the vintage (2026-11-24, the resolver audit):**
  - **The audit:** every stored wording of the 39 vocabulary fields (304 distinct field and
    wording pairs, held-out papers excluded) was re-resolved with the current code. Still wrong at
    HEAD `0d9122c`:
    - ten motion-expansion wordings resolved to 6param (B1);
    - "optiBET" resolved to bet through the alias "BET", matched inside a word;
    - two "outlier scans entered as regressors" wordings resolved to censor (debatable; kept).
  - **Older flags were stale:** "cubic" → quadratic, "linear, quadratic" → quadratic and
    native_surface → template_surface were stored by older resolvers; today's code does not
    produce them.
  - **Fixed:**
    - aliases match whole words only (a plural "s" allowed);
    - an exact member token is that member before another member's alias can claim it, unless a
      dated ruling sends it elsewhere (volterra → friston24, item 3 of 2026-10-28);
    - TERM_RULES for motion expansion (B1).
  - **After the fix:** 13 of the 304 pairs change, every one as intended (5 to friston24, 7 to
    unresolved, optiBET unresolved).
- **Traced (D1, 2026-11-24; A6):**
  - Both came from the model's token. bold_pct is forced, the case this sentence is written for.
    fieldmap_less is not forced; it is B13's case and leaves this item.
  - **The sentence leaves open what comes back for a value the paper does name.**
    - If the token (as now): the paper's term is still not recorded, and a forced token cannot be
      told from a named one.
    - If the words: the alias tables do the mapping. On the stored arms they carry the first two
      rows of A6's table (S 218, B 219, C 218 of 313, 272, 272). They lose the member of a value
      named in words they lack and of a value described without a term (S 30, B 23, C 28), and
      they bring in the faults of A6: the 15 aliases, the versioned SPM names, the wrong-member
      matches. No stored record shows those faults, because the model wrote tokens.
  - C7 puts a third shape to the author: the model returns the paper's term and its member, and
    code checks one against the other.

### B6. Rulings 8, 12 and 13: inference goes in the inference arm (prompt + code; decision C4)

The firewall stays, because it protects what the extraction arm means: what the paper states. The
rulings describe inference, and every ProvenancedField already has an inference arm beside the
extraction arm (the realignment and KB default fills use it). The proposal:

- **Extraction arm, unchanged:** the paper's words only.
- **A new inference pass (ruling 8, order and other steps):** runs after assembly, in code where
  the inference is mechanical. Examples:
  - stc relative_to_motion_correction from step_order;
  - segmentation performed when tissue signals are extracted;
  - smoothing space from the order of normalization and smoothing.
  Each fill is `inference_status="INFERRED_FROM_TEXT"` with the source fields named. No model
  call.
- **Ruling 12 (tool convention):** the KB carries per-tool conventions (SPM FWHM) and fills the
  inference arm, like `fill_deferred_defaults`. The model never infers it.
- **Ruling 13 (a cited method paper names the method):**
  - a table of method papers (Behzadi 2007 → acompcor; Power 2012 → fd_power; Jenkinson 2002 →
    MCFLIRT) fills the inference arm when the step's citation matches;
  - the citation hop already reads citations, so the match uses its references.
- **Schema needed:** the inference arm today allows only `INFERRED_DEFAULT`, refused on any field
  whose FieldMeta has `inference_applicable=False` (PP:807-812). B6 therefore needs:
  - two new inference statuses, `INFERRED_FROM_TEXT` (ruling 8) and `INFERRED_FROM_CITATION`
    (ruling 13), which are additive enum values;
  - a rule that these two are allowed on every field, since they rest on the paper, not on a
    default. The `inference_applicable` gate stays for `INFERRED_DEFAULT`.
  - It goes in the same schema bump as B1 and B2 (C1).
- **Scoring:** the scorers compare labels to the extraction arm. Labels whose notes say
  "inferred from" or "cited:" would be compared to the inference arm. That is a post-hoc scorer
  addition, reported in its own column like the containment column (C4).
- **What the stored arms hold today (D1; A6):** inferences sit in the extraction arm as extracted
  values: S 55, B 30, C 25 token values. Three groups are mechanical enough for the inference
  pass, each a yes or no for the author (C9):
  - order (ruling 8): slice timing relative to motion correction, filtering relative to
    regression, smoothing space; 18 distinct cases. The first and third are already listed above;
  - smoothing approach: `fixed_kernel` when a kernel FWHM is stated and no iteration wording is
    present; 17 cases;
  - a table of named confound models (9P, 24P, 36P) that gives the tissue regressors; 16 cases,
    all ciric_2017.
  - The rest are not inferences a rule should make: `none` from a regressor list that omits the
    regressor (arm S, 14), `linear` for a bare "detrending" (2). The prompt lines that offer
    `none` need "only when the text says so" (C9).

### B7. A step stated without detail counts as performed (prompt)

- **`_SHARED_RULES`:** "A sentence that names a step as done, without any detail ('the data were
  denoised', 'images were coregistered'), states that the step was performed: `<step>_performed`
  = yes with that sentence; its parameters are missing."
- **The checking pass** gets the same sentence in CHECKING_RULES.
- **Cases:** hermans_2024 (denoised), bakker_2012 and dimitrova_2002 (coregistration).

### B8. Deferral to a pipeline's defaults (prompt + KB)

- **`_SHARED_RULES`:** "When the text says preprocessing used a pipeline's default steps or
  settings ('the default preprocessing pipeline of CONN'), every parameter the text does not state
  is deferred to that pipeline (`target_kind="pipeline"`), and `<step>_performed` is yes for the
  steps the text names."
- **KB:** `fill_deferred_defaults` (kb_client/base_pipeline.py:459-520) then fills from the KB
  where an entry exists. CONN has realignment settings in the KB (2026-11-10). Its full default
  pipeline is a KB entry to write in fmri-defaults-kb, separately.
- **Case:** schwartz_2018.

### B9. Two smaller rules (prompt)

- **coregistration_transform:** "affine means 12 degrees of freedom. A stated count other than 6
  or 12 (9 DOF) is returned in the paper's words." Case: hermans_2024.
- **target_space:** "the template the data were registered to, not a coordinate system the
  results are reported in. When the text names both, return the template." Case: dimitrova_2002.

### B10. The prompt audit patch (decision C5)

- **What it changes:** wording only. Arm C showed no difference from B.
- **Proposal:** fold its text cleanups into this vintage, since every one of those prompts is
  re-pinned anyway, and leave the `AESPA_EFFORT` switch out. The run uses effort medium, as the
  2026-11-15 arms did, and the switch is a request setting, not prompt text.

### B11. An unmatched term says so in the report (code)

- **Now:** a term no member fits is shown in quotes, marked "[from paper]". That is the only
  signal that AESPA holds no vocabulary value for it, so no KB default, inference or pipeline
  setting applies.
- **Change:** the report says it plainly beside the paper's words: "not in AESPA's vocabulary".
  The pseudo-code marks it the same way.
- **Why:** a method released after the vocabulary was written comes through in the paper's words,
  which is correct for a reader reproducing it. The marker tells them that nothing downstream was
  filled for that step.
- **Gate:** a re-render change; old records change only where a term is unresolved, and every
  change is listed.

### B12. A list of unrecognized terms (code)

- **What:** `scripts/term_audit.py`, the 2026-11-24 audit made standing. For each vocabulary
  field, it lists every stored wording with its member, flags partial matches and exact tokens
  sent elsewhere, and lists unresolved wordings by how often they recur across papers.
- **When:** after every run, before scoring.
- **How the vocabulary grows:** a recurring unresolved wording (a new tool, "12-parameter") is the
  signal to add a member and its KB entry, as a dated change with tests. Aliases are not guessed
  ahead of the papers.
- **Privacy:** held-out papers are counted, never shown.
- **Added by D1 (A6):** two code checks join the audit.
  - **Table self-check:** every alias, given as the wording, resolves to its own member. This is
    a test; it fails today on 15 aliases.
  - **Token trace of a record set:** how many values are bare tokens, and for each whether an
    alias of its member is in its quote. Spans are put in text order first; stored order differs
    from text order in 20 of the 55 multi-span cases of D1.

### B13. The main text and the supplement disagree (prompt; decision C8)

- **Now:** no prompt ranks the two. For distortion correction every arm quotes the supplement's
  pipeline-generated summary: "SDC was omitted" for hermans_2024 and "Fieldmap-less" for
  ladouceur_2023. Both labels follow the main text (the author's decision of 2026-11-19).
- **Proposal:**
  - one sentence in the extraction prompts and CHECKING_RULES (EX/prompt_rules.py:33): "When the
    main text and a supplement's automatically generated pipeline description disagree about a
    step, report what the main text states, and quote the main text."
  - a span already records where it came from (`span_in_supplement`, EX/batch.py:318-326), so the
    report can mark a value quoted only from the supplement. No schema change.
- **Untouched:** a supplement that adds detail the main text does not state.

### Prompts re-pinned

- **Re-pinned:**
  - EXTRACTION_PROMPT and PER_ACQUISITION_EXTRACTION_PROMPT (B3, B5, B9);
  - TEMPORAL_VOLUME_PROMPT (B1, B5, B7, B8);
  - SPATIAL_PROMPT (B2, B4, B5, B7, B8, B9);
  - VERIFIER_PROMPT (B3, B7).
- **Not touched:**
  - MOTION_METHOD_PROMPT (frozen by the motion probe);
  - the hop, release, software, gate and resolution prompts.
- **If C7 to C9 are ruled in,** they change text inside the prompts already listed and add none
  to the list: `_SHARED_RULES` and EXTRACTION_PROMPT (C7, B13), the field lines of calls T and S
  (C9), CHECKING_RULES (B13).

## Part C: decisions for the author

- **C1. Schema version.**
  - The change: B1 is additive (0.7.5). B2 is structural (a minor bump).
  - The conflict: multi-echo is designed as 0.8.0 and not built.
  - Recommendation: this change is 0.8.0, and multi-echo becomes 0.9.0 when built.
  - Alternative: B2 without the retype keeps bare Literals with "other" and loses unmapped words
    (0.7.5 only).
- **C2. The intersubject partial rule after B2.**
  - Recommendation: once method and warp are extracted, extend the rule to {target_space,
    resolution_mm, method, warp} for volume.
  - Why: this matches the labels that are reported (glasser2016_nature) and partial (li_2024,
    schwartz_2018, dimitrova_2002).
  - Ruled 2026-11-24 over extracted fields, so the extension follows the same ruling.
- **C3. Method fields: tool or technique.**
  - Recommendation: keep the tool, the schema's definition since 0.3.0 and what the KB and
    software rows rely on.
  - The cost: relabel nuisance and scrub `method` values that name a technique ("regression",
    "GLM", "censoring") to the tool the paper names, or blank where none is named.
  - Alternative: add a `technique` field (structural, more labels).
- **C4. Rulings 8, 12 and 13.**
  - Recommendation: the inference arm (B6), not the extraction prompts, with a dated post-hoc
    column comparing "inferred from" and "cited:" labels to it.
  - Alternative: allow the model to infer in the extraction arm. This breaks the firewall, which
    the extraction results since 2026-10 are built on.
- **C5. The audit patch.** Recommendation: fold in its text cleanups; leave the effort switch out.
- **C6. The run.**
  - Recommendation: Fable 5.2 only, one arm, on the full corpus (the 17 newly labelled papers
    included), with every tested_lit folder as `--corpus`.
  - A Sonnet 5.5 arm would be priced separately before any run.
  - **Ruled: no run yet.**
  - **Measured cost:** arm B of 2026-11-15 metered $42.10 over 21 papers, $2.00 per paper. An
    earlier figure of $1.72 averaged arms B and C and is superseded. Per paper, about 8 calls each
    send the methods text (13,000 to 19,000 input tokens per call). The shares, from the stored
    call meters (`run.calls` in `results/fable_arms_bc/papers/B_*.json`):

    | Call | Share | Input / output tokens per call |
    |---|---|---|
    | Checking pass | 22.7% | 18,967 / 7,603 |
    | Call T | 21.9% | 18,943 / 7,171 |
    | Call S | 16.1% | 17,294 / 4,598 |
    | Shared extraction | 10.2% | 17,870 / 1,561 |
    | fMRI gate | 7.9% | 18,856 / 206 |
    | Motion | 6.8% | 13,113 / 786 |
    | Release, resolution, the software checks and the rest | about 14% | small |

    Input and output each make up about half the cost.
  - **Savings options:** a design addition; no model call is needed to build them.
    - **Replay unchanged calls:** the gate, motion, release and resolution prompts are not changed
      by this vintage (about 21% of the cost). A replay mode taking their outputs from the stored
      record saves about $0.40 per paper.
    - **A cheaper gate:** skip it for corpus papers already known to be fMRI, or send the abstract
      only. Saves about $0.15 per paper.
    - **Prompt caching:** unverified. Each call has its own tool schema, which may prevent a shared
      cached prefix; check the API's caching rules before counting on it.
    - **Effort:** low effort on the small calls only. The checking pass and calls T and S stay at
      medium.
  - **Estimates:**
    - with the first two options, about $1.45 per paper: 29 papers (the 24 with Fable records and
      the 5 missing) about $42, the 45-paper corpus about $65;
    - without them, about $58 and $90.

### Put to the author after D1 (2026-11-24); ruled 2026-11-25 ("C7 ok, C8 ok, C9 ok")

- **C7. What the model returns for a vocabulary field.**
  - The facts (A6): today the model returns the member's token and the paper's term is not
    recorded. B5's sentence leaves open which of the two comes back. If it is the words, the
    alias tables do a mapping they have so far done for 20 of arm S's 407 values.
  - Recommendation: both. The model returns the paper's term, copied from the quote, and the
    member it reads that term as (or none). `SpecifiedTerm.verbatim` then holds the paper's term
    for every value, which is what the 0.5.0 rule says it holds. The alias table checks the
    model's member instead of choosing it:
    - the table resolves the term to the same member: resolved, as now;
    - the table has no alias for the term: the model's member stands, marked as the model's
      mapping, and B12 lists the term as an alias candidate that came from a paper;
    - the table resolves the term to another member: the value is kept in the paper's words,
      flagged for the checking pass and listed by B12;
    - a member returned with no term from the quote is refused. That stops an inference from
      silence (physio `none`).
  - Cost: one more string per vocabulary value in calls T and S and the shared call (additive,
    in 0.8.0 with B1, B2 and B6), one more value of `resolution`, and the same re-pin.
  - Alternative A: B5 as written, with D2b's table fixes. A value the paper describes in words
    no alias holds loses its member until an alias is added.
  - Alternative B: keep today's contract and add only the rule against forced tokens. The
    paper's term stays unrecorded.
- **C8. The main text against the supplement (B13).**
  - Recommendation: the main text wins when the two disagree, as labelled since 2026-11-19.
  - Alternative: record both as variants, one per source.
- **C9. Smaller additions D1 points to.** Each is a separate yes or no.
  - Schema, in 0.8.0:
    - a scrub criterion member for a global-signal threshold (schwartz_2018);
    - one threshold per criterion, where today one number serves a list of criteria;
    - a fieldmap-less member on distortion_correction.method. Without it, D2b's block keeps
      "fieldmap-less" in the paper's words there;
    - `other` on coregistration cost function, which the prompt line already offers. The
      alternative is to drop "other" from the prompt line.
  - Table: "N3" as an alias of `n4`. Keep it (one family of methods) or remove it (a different
    algorithm, the one FreeSurfer's nu_correct runs).
  - Prompt, calls T and S:
    - `none` for physio regressors, motion expansion and detrend "only when the text says none
      was used";
    - smoothing_approach, either defined ("fixed_kernel: a kernel of a stated FWHM") or left to
      the inference pass (B6).
  - Inference pass (B6): the three mechanical groups listed there.

### Put to the author after D2b (2026-11-25); not ruled

Each fact below was run on 2026-11-25 under HEAD `f59372b` and under the D2b working tree with the
old-against-new resolver comparison of Part D; "both" means the two give the same result.

- **C10. The two items of C9 that had no recommendation.**
  - "N3" as an alias of `n4` (both: "N3" → `n4`). Recommendation: remove it. N3 is a different
    algorithm, and under C3 a method field is the tool, so the alias marks a wrong member
    resolved. The term then stays in the paper's words until an `n3` member is added.
  - smoothing_approach. Recommendation: the inference pass (B6). A paper that states a kernel
    size does not state the approach, and C4 put inference in the inference arm.
- **C11. "or" between two list items.**
  - Both: "FD > 0.2 mm or DVARS > 5%" is one item that names two members and stays unresolved.
  - HEAD resolved "FD > 0.2 mm/TR or DVARS > 5%" to `fd_power` and `dvars` only because the slash
    of "mm/TR" cut the item. D2b holds a unit ratio whole, so that wording is unresolved too.
  - Recommendation: make "or" a separator for scrub.criterion alone. There it joins two criteria
    that are both applied; in a tool or method list it joins alternatives of which one was used.
- **C12. "SPM" as a bare alias, and the release list.**
  - Both: "CONN toolbox (SPM)" → `spm` and "CAT12 (SPM)" → `spm_segment`. The alias matches
    "SPM" wherever it stands as a word, so a toolbox that runs on SPM becomes SPM's own tool.
  - A release is stricter since D2b: it resolves only as the whole wording. So "run in SPM 12"
    resolves (the alias reads "SPM") and "run in SPM12" does not.
  - Recommendation: give the bare alias the release's two rules (resolve as the whole wording,
    name the member elsewhere), together with C7. Once the model returns the paper's term and its
    member, a term the table does not resolve keeps the model's member, so the stricter table
    costs no value and stops the toolbox case.
  - The release list is 99, 2, 5, 8, 12 and 25, each with or without "b". "SPM96" and its
    neighbours name the member and do not resolve. Add them (94 to 97), or leave the list as it is.
- **C13. Terms the vocabulary holds under another wording.** Each is a yes or no.
  - Alias candidates from stored records: "24-regressor model of motion" (`friston24`; the table
    holds the plural "24 regressors") and "ICBM 152 Nonlinear Asymmetrical template version 2009c"
    (MNI152NLin2009cAsym). Section 3 of the audit lists the rest by recurrence.
  - Family names. D2b keeps the report's note off "fs_LR", "MSM", "CompCor", "Montreal
    Neurological Institute" and "ICBM" (`coverage_fields.FAMILY_NAMES`, read for the note only).
    They could become underspecified terms of their tables, as "MNI" is; that changes their
    resolution status from unrecognized to underspecified.
  - What may follow a mesh density. "fsaverage 6" resolves; "fsaverage 6 surface" stays
    unresolved, because a word after the number may be what it counts ("fsaverage 6 mm"). A short
    list of nouns (surface, space, template, mesh) could be allowed to follow.
  - The wrong-member matches of the D1 sweep that D2b did not take (both, unchanged):
    "non-rigid" → `rigid`; "MNI152 2009c symmetric" → MNI152NLin2009cAsym; "fsaverage_sym" →
    `fsaverage`; "FD-RMS" → `fd_power`; "Fourier basis set (SPM)" → `ideal_fft`; "SynthSeg
    (FreeSurfer 7)" → `freesurfer_recon_all`; "MSM folding-based registration" →
    `freesurfer_recon`; "realignment was performed after slice timing correction" → `after`.
- **C14. Three behaviours found while building, left as they are.**
  - Negation is not read. Both: "white matter and not the gray matter" → `white_matter` and
    `gray_matter`; "ROBEX (not BET)" → `bet`. D2b only stops a negated first item from borrowing
    a head noun. With C7 the model's member is checked against the term, which covers most of it.
  - The detrend rule of 2026-10-28 has two edges. It raises `none`: the value "none" with the
    quote "No linear detrending was applied" becomes `linear`. And it is not applied to a value
    the checking pass supplies, because `checker_promotion.promote` runs after it.
    Recommendation: leave `none` alone in the rule, and apply the rule inside `promote`.
  - The 2026-06 collapse still drops a shorter member named apart from its longer form:
    "fsaverage, then fsaverage5" reads as `fsaverage5` alone. The whole-word rule and the
    longer-alias rule now cover the case it was written for.

## Part D: build order, checks and the run

- **D1. Done 2026-11-24, read-only (A6).** B5's two unknowns are traced. The trace was widened to
  every stored token and every alias table, because the two cases turned out to be instances: the
  model writes tokens throughout, and "fieldmap-less" is one of 15 aliases that cannot resolve.
  It leaves three decisions with the author (C7 to C9) and a longer D2b.
- **D1b. Done 2026-11-24:**
  - the resolver fixes of B1 and B5, with `tests/test_resolver_audit.py`;
  - `scripts/reresolve_terms.py`, with its tests.
  - On the 2026-11-15 arms, the re-resolve changes motion expansion and optiBET values and no
    score. The as-stated scorers do not see a corrected member whose words differ from the label.
- **D2b. B11, B12 and the table faults of A6. Built 2026-11-25** (code and tests; no prompt, no
  model call; the author's go-ahead is in section 0). Three review rounds and a mutation gate
  shaped it. Where the build differs from the plan of 2026-11-24, the item says so.
  - **The longer alias wins** (`synonym_resolver.members_named`). An occurrence of an alias inside
    a longer occurrence of another member's alias does not count. All 15 aliases resolve to
    their own member; the self-check is a test (`tests/test_resolver_d2b.py`) and section 1 of
    the audit. An occurrence elsewhere still counts: "FLIRT, then FLIRT BBR" stays ambiguous.
    - Limit, added after review: an alias that ends in a digit wins only when its number ends the
      phrase. "fsaverage 6" is `fsaverage6`; "fsaverage 6 mm FWHM", "fsaverage 6 millimetre
      kernel", "fsaverage 5 subjects" and "fsaverage 6 surface" stay ambiguous, as at HEAD. With
      no limit the first three had resolved to the mesh, and no list of units can be closed.
    - With it: a digit-final alias is not matched before a decimal part or a thousands group
      ("fsaverage 5.3", "mode value of 1,000,000").
  - **SPM releases, differing from the plan.** The plan made the six releases aliases of each
    SPM member. As aliases they resolved "CONN toolbox (SPM12)", "DPARSF (SPM8)" and "CAT12
    (SPM12)" to SPM's own tool. A block list of toolboxes was tried, and the second review found
    six names it missed. Built instead as two field rules on the five SPM members:
    - a listed release that is the whole wording resolves ("SPM12", "the SPM99b software"). The
      list is the plan's six, each with or without the "b" of a beta, which the stored quotes of
      maheu_2011 ("SPM99b") and silchenko_2023 ("SPM12b") print;
    - "SPM" with a number inside a longer wording, or with a number the list lacks, names the
      member and does not resolve to it (`TermRules.named_by`). Another member cannot take the
      term ("SPM12 in MATLAB" was `custom`), the token trace finds the release in a quote, and
      the report makes no vocabulary claim about the term.
    - The bare alias "SPM" is unchanged (C12).
  - **Text repair, differing from the plan.** The resolver reads repaired text
    (`synonym_resolver.repair_text`): span_resolver's character table, five Unicode hyphens and
    six invisible characters, one character at a time. It is not `normalize_with_offset_map`,
    whose NFKD fold joins a trademark sign or a superscript to the tool name and whose
    split-measurement rule joins an article to a number ("a 24 parameter model"). A word split at
    a line break is rejoined only when the first reading names no member. The stored words are
    never changed.
    - "B 0" and "32 k fs_LR" went in as aliases from the papers that print them (hagler_2019,
      marek_2022). A general tolerance for a split token matched FAST's "-n 3" as "N3".
  - **TERM_RULES blocks**, as planned, each with its test:
    - `fieldmap` (method) and `susceptibility_fieldmap` (source) on "-less" and "-free" forms;
    - `bet` on "HD-BET";
    - `specific_slice` on "slice acquisition range";
    - `template_surface` on a native, subject's, participant's, individual or own "cortical
      surface";
    - `6param` on "differenc" (the plan said "differ").
    - Found on the way: the 2026-11-24 pattern "deriv" also matched "derived". It is now
      "derivat" or "deriv(s)" as a word. "six motion parameters derived from the realignment"
      resolves to `6param` (HEAD: unresolved), and "six motion parameters derived from MCFLIRT
      and their squares" no longer resolves to `friston24`.
  - **The list splitter:**
    - nested parentheses are one piece;
    - a comma or a slash between two digits does not separate, and a unit ratio ("mm/TR") is one
      token;
    - an "and" joined by a hyphen is part of a name ("Realign-and-Unwarp");
    - an alias that holds a separator ("blip-up/blip-down", "ICA+FIX") and the compound "Realign
      and Unwarp" are kept whole;
    - a coordination that shares its head noun is completed ("white and gray matter",
      "anatomical and temporal CompCor"), under three conditions that each keep a wrong member
      out: the next item resolved, the borrowed words alone name no member, and the item holds no
      negation word.
    - Holding the unit ratio ends an accident (C11).
  - **The "other" rule:** "other - X", "other, X" and a phrase with balanced parentheses of its
    own. Where the prompt offers "other" and the vocabulary holds no such member (the
    coregistration cost function, until C9's member), "other (phrase)" stays unresolved and no
    alias inside the phrase can claim a member.
  - **B11, narrower than written.** The note "not in AESPA's vocabulary" is in the report and the
    pseudo-code, and absent from the draft the checking pass is sent. It is printed only where
    no part of the term is a name the field's vocabulary knows
    (`coverage_fields.names_no_member`). An unresolved term that names two members, a blocked
    alias, a family term or name, a member token in another case, or an SPM release beside a
    toolbox is shown as before, without the note, because the claim would not be certain there.
    An inferred value is never marked.
    - On arm S the note is on 49 of the 63 unresolved terms; on arm B, 52 of 67.
    - The note is about the term. It is also on a term whose method the vocabulary holds under
      another wording ("24-regressor model of motion"); the audit lists each as an alias
      candidate (C13).
  - **B12.** `scripts/term_audit.py`: the table self-check, every stored wording with its member
    and flags, unresolved wordings by recurrence, the token trace, and held-out counts.
    `scripts/reresolve_terms.py` now covers the four shared fields and lists each change with
    `--show`; its per-field counts leave out held-out papers, which get one total.
    - Both resolve the detrend field as the extractor does: the term, then the highest order its
      quote names (2026-10-28), for a value the coverage call extracted. The 2026-11-24 script
      ran the first step only and wrote ciric_2017's "linear, quadratic" back unresolved. The
      DEVLOG entry of 2026-11-25 corrects the entry of 2026-11-24 (6) on this.
  - **Gates, run on 2026-11-25, HEAD `f59372b` against the working tree:**
    - Table self-check: 451 aliases, 0 that do not resolve to their own member.
    - Stored wordings: 1 of 322 resolves differently ("32 k fs_LR" → `fsLR_32k`).
    - The 17,920 wordings the three reviews probed: 16,204 resolve the same, 979 gain a member
      and 308 split into other items with the same members. 429 lose or change a member, and
      each is attributed to a rule named above.
    - `reresolve_terms.py` on six record sets (1,944 terms): it differs from HEAD's script in 3
      terms, all ciric_2017's detrend value. Held-out papers: 0 terms changed.
    - Re-render of five record sets: every changed line is the old line plus the note;
      batch_v7_full is identical; no held-out file changed.
    - The checking pass's draft (`verifier.compact_draft`): 148 of 148 byte-identical.
    - Mutation: 193 single-change mutants on a scratch copy, each diff shown non-empty before
      its run. 192 were killed; the one that survived (a space before the punctuation that ends
      a phrase) got a test and is killed on rerun.
    - Reviews: three rounds of read-only agents (13, 8 and 8), each finding re-checked by a
      second agent that had to reproduce it. They confirmed 38, 22 and 10 findings; all are
      fixed or, where the fix is the author's call, listed under C10 to C14.
    - Suites: extractor_mvp 1448 passed (2 live skipped), root 332; pre-commit clean on the
      second pass. Each planned commit passes on its own in a scratch export of HEAD.
- **D2. Code that changes no prompt:**
  - B1's alias order and B5's table fixes, with tests;
  - the re-render gate on the five record sets used on 2026-11-24 (old records identical, every
    change attributed).
  - A table fix may change stored records' resolved values on re-read; every such change is listed.
- **D3. Schema:**
  - B1's member and B2's retype, with the migration hops and tests;
  - C7's term-and-member return and C9's members, where ruled in;
  - `scripts/export_schema.py` for the new version;
  - the version pins in tests/spec.
- **D4. Prompts:**
  - B2-B9 and B10's cleanups in one commit, with B13 and the prompt lines of C7 and C9 where
    ruled in;
  - each re-pinned hash with its dated note and the superseded hash;
  - the copies at PIN:388-396;
  - a DEVLOG entry naming every changed prompt.
- **D5. Inference pass (B6):**
  - code and KB tables, tests;
  - the three groups D1 measured (B6), where ruled in;
  - a dry run on stored records with the fills listed, no model call.
- **D5b. Cost (C6):**
  - the replay mode for unchanged calls, and the gate skip for known-fMRI corpus papers;
  - tests, and a dry run on stored records showing which calls would replay, with no model call.
- **D6. Checks before any run:**
  - both suites (root and extractor_mvp);
  - pre-commit twice;
  - a mutation per rule, each diff shown non-empty;
  - CI green after the push.
- **D7. The run (after the author's say-so):**
  - from a worktree pinned at the vintage commit, under caffeinate, with GROBID, every tested_lit
    folder as `--corpus`;
  - scored with score_arms and the containment column against the 2026-11-15 arms.
  - The comparison is what the vintage changed, card by card, in counts.
