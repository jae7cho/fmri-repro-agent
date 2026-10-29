# DESIGN — report v2: a looser format and a checking pass

**Design only. Written 2026-10-29, after two unseen papers were read
(`docs/findings/unseen-papers-2026-10-29.md`).** No code was changed, no model was called, nothing was
written under `results/`. Every fact carries its locator at HEAD `69a6152` plus the staged
2026-10-29 fixes. Every open choice is a fork for the author.

**Ratified by the author on 2026-10-29**, as written: all eleven forks as recommended in §6,
F2 included. In the author's words: *"leave the shared prompt alone and let the verifier flag those
cases. Re-vintaging `target_space`, a validated field, to fix one error the verifier can already
catch is the wrong trade."* Build order as ordered by the author: (1) schema 0.6.0 and the list
upgrade; (2) `software_mentions` and the rebuilt Software row; (3) temporal filtering on call T;
(4) the scope paragraph in both coverage prompts; (5) step order from the paper; (6) the verifier.
The author records their own reading of the two unseen papers before any verifier verdict on them
is shown.

## 0. The author's framing, 2026-10-29

Recorded from the author's message of that day. Five problems came from the format, not from the
model's reasoning:

- no temporal filtering field (coverage was scoped to D.3 rows, and D.3 has none);
- a fixed step order labelled as the paper's;
- single-value fields where papers list two;
- a Software row that reads only the base pipeline;
- hand-made phrase and alias tables ("every list we write is a list the model's reading can fall
  off").

Three were reasoning errors a careful reader catches: structural-MRI sentences filling functional
fields, the task GLM read as preprocessing, and the multi-pipeline warning firing on ciric's 14
benchmark models. The fix for those is a second, checking pass. **The quote rule stays; it is what
makes a check possible.** The caution also stays: Claude Code's review of two papers by a model of
AESPA's family is a bug list, not a measurement. The checking pass inherits the same caveat, so its
verdicts are spot-checked against the author's reading before anyone trusts them.

---

## 1. Schema loosening

### 1a. Temporal filtering on the temporal/volume call, marked "beyond COBIDAS"

**Facts.**
- The spec already has the class. `TemporalFiltering` (`src/fmri_repro/spec/preprocessing.py`) carries
  `effective_band_hz`, `method` (`butterworth_bandpass`, `highpass_only`, `wavelet_decomposition`),
  `low_hz`, `high_hz`, `order`, `cutoff`, `scale` and `nominal_band_hz`.
- It is a DIVERGENCE kind with no D.3 row (`cobidas.py`, `DIVERGENCE_KINDS`), and `_assemble` never
  emits it (`DESIGN_coverage_expansion.md` B6).
- Its model validator raises when `effective_band_hz` disagrees with `(low_hz, high_hz)`.
- `effective_band_hz` is one of the seven fields the KB fill may set
  (`kb_client/base_pipeline.py`, `SEVEN_DEMOTED_FIELDS`).

**Design.**
- Call T asks `performed` first and then these fields:
  - **`band_hz`**: low and high edges as stated; high-pass-only gives `(low, None)`.
  - **`method`**, using the existing Literal.
  - **`order`**: the filter order as an integer.
  - **`relative_to_regression`**: a new field, Literal `before | after | simultaneous`, the paper's
    stated order against nuisance regression.
  - **`applied_to`**: free text, with an example such as "motion covariates".
- The step is emitted between `nuisance_regression` and `despike` in the template. It renders under
  "Beyond COBIDAS" with the rows-section line `Temporal filtering [beyond COBIDAS] — …`. It is never
  counted in the 14.
- **The band-consistency validator is a fail point of the kind the author ruled out on 2026-10-29.**
  If the model returns a band and separate edges that disagree, `_assemble` raises and the paper
  fails. The coverage path therefore fills `effective_band_hz` only, leaves `low_hz`/`high_hz`
  untargeted, and adds a test that a disagreeing pair can never be constructed by the extractor.
- `relative_to_regression` overlaps `nuisance_regression.filtering_integrated`. The design keeps both
  for one vintage and has the verifier report disagreements between them.

**Forks.**
- **F1a:** The KB fill may set `effective_band_hz` once the step is emitted. Should that be allowed
  in report v2 (a `version_default` inference beside "not reported"), or held until R7's KB build?
  Recommended: held.
- **F1b:** Gracia-Tabuenca filters the data and, separately, the motion covariates. Should the step
  allow two filter records? Recommended: one record for the data, with the covariate filter in
  `applied_to` text. The schema keeps per-kind uniqueness.

### 1b. Lists where papers list

**Facts.** Each of these fields is a single Literal today. Each was seen listed in a paper, or the
D.3 wording allows several values:

| field | why it may hold more than one |
|---|---|
| `distortion_correction.source` | Gracia-Tabuenca: susceptibility and gradient nonlinearity |
| `distortion_correction.method` | e.g. topup plus gradunwarp |
| `scrub.criterion` | FD and DVARS are commonly combined |
| `nuisance_regression.physio_regressors` | RETROICOR and RVT |
| `ica_denoise.method` | FIX and AROMA are alternatives, but some papers run both |
| `compcor.variant` | aCompCor and tCompCor |

`tissue_classes` and `tissue_regressors` are already lists (`coverage_fields.py`, `term_list`).

**Design.**
- Retype the six fields to `list[SpecifiedTerm[X]]` and give them `term_list` value kind, with the
  existing every-item support check.
- This makes schema 0.6.0 (structural). The hop lifts a scalar to a one-item list. Stored records
  carry these fields only as fillers, except four contaminated v1/v2 cells, so the lift is checked by
  replay.
- `scrub.threshold` stays one number. A paper with two criteria and two thresholds loses the pairing,
  so the verifier flags it; this is held as **F1c** (a list of `{criterion, threshold}` pairs).
- `motion_correction.method` stays single. Its stanza is frozen under prereg C11.

### 1c. `software_mentions`: every piece of software the paper names

**Facts.**
- The Software row is computed from `base_pipeline` and `base_pipeline.version` only (`cobidas.py`,
  `_software_coverage`).
- Gracia-Tabuenca names FreeSurfer v5.3; Shen names SPM5 and BioImage Suite. Neither reaches the row.

**Design.**
- A record-level list on `Preprocessing`, a new optional field: `software_mentions:
  list[ProvenancedField[SoftwareMention]] | None`, where `SoftwareMention = {name, version: str |
  None, used_for: str | None}`.
- Each entry is extracted with its own quote and support-checked: the name and the version as
  digit-exact tokens, and `used_for` with the free-text matcher. A version fused into the name
  (`SPM5`) is recorded as the name with `version` None, the existing Q1 rule. Whether `SPM5` counts
  as a reported version for COBIDAS §4.3 stays open (`cobidas-version-criterion.md`).
- Asked once, on call S. The spatial call is the one that reads the registration and segmentation
  tools.
- **The Software row is rebuilt over the mentions:**
  - addressed when every mention carries a version;
  - **partially reported**, a new row state, when some do, listing the ones that do not;
  - not reported when none do;
  - the base pipeline joins the list as one mention.
- The "unconditional violation" line names the software that lack versions. It never accuses an
  author on a mention whose quote did not resolve, which stays unverifiable, the existing rule.

**Fork F1d:** Does a mention used only for analysis or statistics (R, MATLAB, a stats package) count
toward a *preprocessing* Software row? D.3 says "for each software used". Recommended: record all
mentions; count toward the row only those whose `used_for` the verifier marks as preprocessing; show
the rest.

### 1d. Step order from the paper, else the template with a note

**Facts.**
- `Preprocessing.steps` list position IS the order by contract (`preprocessing.py`, the model
  docstring: "list position IS the order — COBIDAS §4.3").
- `_assemble` emits a fixed list, and the report header says "Preprocessing steps (pipeline order)"
  (`render.py`, `to_protocol`).

**Design.**
- Call T asks `step_order`: the ordered list of step kinds the paper performs, in the paper's order,
  with the sentence(s) that state the order. The quote rule applies. An order read only from the
  sequence of sentences counts as stated if the paper narrates steps in sequence ("then", numbered
  lists, "followed by").
- `_assemble` places the stated steps in that order and the unstated ones after them in template
  order.
- The record carries `step_order_source: "paper" | "partial" | "template"` (schema 0.6.0, optional).
- The header reads either "Preprocessing steps (order as stated in the paper)", or "(template order —
  the paper does not state an order; a reader must not assume one)", or the partial form with the
  boundary marked.

**Forks.**
- **F1e:** The quote rule cannot verify an order spread across five sentences. Should the order quote
  be a list of sentences, each resolved? Recommended: yes, with every sentence required to resolve.
- **F1f:** Shen applies detrending "to all signals" after smoothing, but D.3 puts detrend inside
  nuisance regression. Recommended: order is per kind, and a field-level ordering inside a kind is
  out of scope.

---

## 2. A scope rule in both coverage prompts

**Design.** One paragraph near the top of `TEMPORAL_VOLUME_PROMPT` and `SPATIAL_PROMPT`: *"Only the
preprocessing of the functional (BOLD) data. A sentence about the structural (T1/T2) image's own
preprocessing does not fill a functional field, except where a row is about the structural image
(brain extraction, segmentation, intensity correction of the structural image). Covariates of a
first-level statistical model (task regressors, motion or trend covariates entered in the GLM) are
analysis, not preprocessing: they do not fill nuisance regression or detrend. If the text describes
both, say which you took."* This gives two new hashes and a dated pin note.

**Fork F2 (important):** The Gracia-Tabuenca structural-sentence error in *intersubject registration*
came from the **shared** prompt (`target_space` lives in `EXTRACTION_PROMPT`, pinned at `31a050b2…`
since 2026-10-21, and re-vintaging it moves a validated field). Options:
- (a) leave the shared prompt and rely on the verifier to flag it;
- (b) add the scope paragraph to the shared prompt as a deliberate vintage event with the
  target_space labels re-scored;
- (c) move `target_space` into call S.

Recommended: (a) for report v2, revisit with the verifier's evidence.

---

## 3. The verifier: one more call, a checking pass

**Input:** the same methods slice, plus a **compact draft**, not the Markdown report. One line per
targeted field: dotted id, state, value (paper's words and resolved member), the located quote in
full (untruncated, which avoids the misreading the author caught on chen), and the reason for a gap.
Untargeted fillers are omitted.

**Output, per field.**

| item | meaning |
|---|---|
| `verdict` | `supported`, `wrong` or `missed` |
| `reason` | one sentence |
| `relied_on` | the sentence it relied on, quote-checked through `resolve_quote` like everything else |
| `better_value` | for `wrong` and `missed` only: what the field should say |

The three verdicts:
- **`supported`**: the value or the gap is right.
- **`wrong`**: the value is not what the paper says for this field. This is where a structural
  sentence, a GLM covariate or a misread order is caught.
- **`missed`**: the draft says not reported, but the paper states it.

Plus one record-level question, replacing the coverage calls' `multiple_pipelines` (**F3a**: drop it
from calls T and S, which those calls' new hashes absorb): *"Does this paper preprocess its own data
in more than one way? A comparison or benchmark of denoising or preprocessing strategies run on the
same data is excluded; separate task and rest branches count."* It is answered with a count and a
quote.

**How a verdict lands.**
- The verifier never writes a value. A `wrong` verdict **demotes the field to a flag** in the report:
  the value stays, struck through as "AESPA drafted X; the checking pass says wrong: <reason>
  «sentence»". It is never silently replaced.
- In the JSON the extraction arm is untouched, so the provenance contract is unchanged. The verdicts
  travel as a side record (`verifier`), the `motion_inference` and `multiple_pipelines` idiom.
- A `missed` verdict renders as "the checking pass says the paper states: <better_value>
  «sentence»" beside the gap. It is not filled.
- A verdict whose `relied_on` sentence does not resolve is shown as "unverified verdict" and has no
  effect on the row.

**Rows (fork F3b).** A row whose every addressing field is `wrong`-flagged reads "flagged by the
checking pass", a new row state ranked above "reported". A row with any `missed` field gains a
"missed" note. Recommended as stated. The alternative is to leave row states to the drafting pass
and show verdicts only at field level.

**Failure modes.**
- The verifier gets **no validator** (the 2026-10-29 ruling).
- Malformed or partial output leaves the affected fields "not checked".
- A transport failure leaves the report rendered without a checking column and with a line saying so.
- The verifier can never fail a paper.

**The same-family caveat (fork F3c).** The verifier is a second draw from the same model family as
the drafter, so shared blind spots pass both. Options:
- (a) same model, a different prompt;
- (b) a different Claude model (larger) for the verifier;
- (c) a different provider.

Recommended: (a) for the first vintage, measured against the author's reading (§4), then (b) as an
arm if (a) agrees too readily with the drafter.

---

## 4. Evaluation plan

1. **Two unseen papers, three readers.**
   - Run the verifier on Gracia-Tabuenca 2024 and Shen 2013.
   - Tabulate per field the verifier's verdict, Claude Code's review (the eight findings, mapped to
     fields), and **the author's reading** (to be recorded before the verifier's verdicts are
     shown to the author).
   - Report counts of agreement and disagreement per pair of readers, never a rate (two papers).
   - The author's reading is the reference; the other two are the things checked.
2. **Spot check before trust.** The author reads three or four further papers outside the corpus
   (the author picks them); the verifier runs on each; every `wrong` and `missed` verdict is checked
   by the author. Until then, verdicts render with the tag "checking pass — unvalidated".
3. **The 16 contaminated papers as a regression set (vintage `report_v2`).**
   - Per-row table beside coverage_v2's.
   - Per paper: counts of fields the verifier marks wrong and missed.
   - The cells coverage_v2 already showed wrong, listed so the verifier can be checked against them:
     poldrack's stored threshold (unsupported before the 2026-10-29 fix), ciric's 14-model
     multi-pipeline, chen's slice timing (right; a false `wrong` here is a verifier error).
   - The held-out three run with the rest and are read as counts.
4. **The identity gate** derived before the run: the stored acceptance records carry none of the new
   fields, and the verifier record is a side record, so the gate should read 19 identical. The
   schema-0.6.0 lift must leave every stored scalar rendering the same (a one-item list renders as
   its item); this is derived by replay before the gate is run.

---

## 5. Costs

| | today (coverage_v2) | report v2 |
|---|---|---|
| model calls per paper, single-acquisition path | 4 (motion, T, S, shared) | **5** (+ verifier) |
| calls on the per-acquisition path | 1 | 1 (the verifier is not run there; fork **F5a**) |
| wall time per paper | 47–85 s (coverage_v2 `wall_time_s`; ciric's re-draw 85 s) | **unmeasured** |
| wall time over the 19 | 1,145.82 s summed, 20 min 40 s launcher | **unmeasured** |

- The verifier runs after the four calls, because it needs the draft, so it adds its own latency
  serially.
- Its input is the methods slice (8,743–50,672 characters across the 19; median 15,444) plus the
  compact draft (≈ 75 targeted fields with full quotes, likely 10–20 k characters).
- Its output is per-field verdicts with sentences, the largest output of any call.
- An estimate of +40–90 s per paper is stated as a guess, to be replaced by the first run's
  `wall_time_s`. The batch should record the verifier's time separately.
- Calls T and S each gain fields (temporal filtering, `step_order`, `software_mentions`), so their
  latency rises too.

## 6. Open forks, collected

| fork | question | recommended |
|---|---|---|
| F1a | KB defaults on `effective_band_hz` once emitted | hold until the KB build |
| F1b | two filter records (data and covariates) | one record, covariates in text |
| F1c | criterion/threshold pairs for scrub | hold; verifier flags |
| F1d | which software counts toward the row | all recorded; preprocessing-use counts |
| F1e | order quote as a list of resolved sentences | yes |
| F1f | order inside a kind | out of scope |
| F2 | the shared prompt's structural-sentence errors | verifier flags; no shared-prompt change yet |
| F3a | move `multiple_pipelines` from T and S to the verifier | yes |
| F3b | a "flagged by the checking pass" row state | yes |
| F3c | verifier model | same model first, a larger model as an arm |
| F5a | verifier on the per-acquisition path | not in v2 |

## 7. Not in this build

KB defaults for any of the new fields; labels or scoring for any row; the motion stanza (frozen);
replacing hand-made tables wholesale. The verifier is the answer to "a list the model's reading can
fall off": a table miss becomes a `missed` or a `wrong` verdict a reader sees, instead of a silent
gap. The tables stay as the first line, the verifier the second.
