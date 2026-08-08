# Design: `temporal_standardization` — BUILD 3 (live delta batch, discrimination validation)

**Prerequisites (all met):** Builds 1+2 committed, signed, pushed (fa6e674 / aa827b2 /
7919e8b), CI green on the 0.2.0 types. Schema has `temporal_standardization`; extractor
routes to it with the signal-vs-derived-product prompt discrimination.

**Repo:** `fmri-repro-agent`. Batch surface (confirmed by reading source):
- Config: YAML with `model:` + `papers: [{paper_id, path}]` (`batch_config.py`).
- `run_batch(config)` iterates `_process_paper` per paper; per-paper JSON →
  `output_dir/papers/{paper_id}.json` (`batch.py:247-284`).

---

## ⚠️ 0. THE MODEL-PIN CORRECTION — read this first

**There is NO `EXTRACTOR_MODEL` env override for the batch.** Confirmed: `EXTRACTOR_MODEL`
appears ONLY in tests, never in extractor/batch source. The batch reads `config.model`
from the YAML, full stop. So earlier session shorthand ("per-run EXTRACTOR_MODEL
override") is WRONG for the batch path.

**The model pin lives in the Build-3 config YAML's `model:` field.** Build 3 uses its OWN
config file — it does NOT edit the committed `batch_config.example.yaml` (which is on 4.6
and stays there). The 4.5 pin is in the Build-3 config only:
```yaml
model: bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0   # match v5 exactly; do NOT use 4.6
```
Rationale (unchanged): v5 was produced on 4.5. This delta batch must hold the model
constant so any difference is attributable to the temporal_standardization change +
synonym/numeric fixes, NOT a model shift. 4.6 is post-delta work.

---

## 1. What Build 3 is — and why it's different in KIND from Builds 1+2

Builds 1+2 were deterministic: offline tests pass or fail, green = correct. **Build 3's
acceptance is a SEMANTIC JUDGMENT by the LLM that cannot be asserted in advance, and a
PARTIAL result is a LIKELY outcome, not a bug.**

Build 3 runs a small live delta set to answer: does the LLM's object-discrimination
(§2 boundary) actually work on real papers? Specifically —
- **Positive set** (Liu, Cho): must POPULATE `temporal_standardization.method =
  voxel_temporal_zscore`.
- **Negative set** (Power, Gordon, Cole, Viduarre): must show
  `temporal_standardization.method = MISSING` with ZERO spurious `voxel_temporal_zscore`.

**A negative-set false-fire is not automatically a build failure — it may be a reportable
FINDING** that the signal-vs-derived-product boundary is too subtle for reliable LLM
discrimination (the Huang et al. self-correction-limits point, live, on this corpus).
Viduarre is the hardest case (post-decomposition ICA-component standardization — the
subtlest "signal vs. derived product" call) and the most likely false-fire. The doc's
job is to specify, per paper, the expected outcome AND what a deviation MEANS — because
on Build 3, deviation is informative, not an error to paper over.

---

## 2. The discrimination boundary being validated (carried from the design conversation)

**IN (populate the step):** standardization of the PREPROCESSED BOLD SIGNAL ITSELF.
**OUT (must stay MISSING):** standardization of anything DERIVED from the signal
(components, regressors, correlations, features) or any METRIC describing it (DVARS,
activation-map z). Verbatim corpus phrasings:
- Liu 2013 (IN): "for each voxel, the fMRI signal was temporally normalized by
  subtracting its mean and then dividing by its temporal SD."
- Cho 2021 (IN): "z-scoring the segments" — same per-voxel-temporal operation.
- Power 2014 (OUT): "regressors were standardized (zero-mean, unit variance)" — regressor.
- Gordon 2014 (OUT): "r values converted to Z-scores using Fisher's transformation" —
  connectivity.
- Cole 2013 (OUT): "across-feature normalization" — MVPA feature.
- Viduarre 2017 (OUT): "ICA-component time series standardized to mean 0 SD 1" —
  post-decomposition component (analysis product, NOT the signal). HARDEST CASE.

---

## 3. Build 3 config + run

### 3a. Locate Cho's PDF. Cho_2021 is NOT in the SfN-20 corpus (`tested_lit/sfn_batch/`);
it's in `tested_lit/multi_batch/Cho_2021.pdf`. Find it (ignore `._*` AppleDouble files;
`find <dir> -name '._*' -delete` first if they cause glob noise). Use `paper_id: cho_2021`.

### 3b. Write the Build-3 config `results/batch_v6_delta_config.yaml` (or similar; the
output_dir is gitignored). Paper set — 8 papers:

| paper_id | role | path source | expected temporal_standardization.method |
|---|---|---|---|
| liu_2013 | POSITIVE | sfn_batch/Liu_2013.pdf | voxel_temporal_zscore (EXTRACTED) |
| cho_2021 | POSITIVE | multi_batch/Cho_2021.pdf | voxel_temporal_zscore (EXTRACTED) |
| power_2014 | NEGATIVE | sfn_batch/Power_2014.pdf | MISSING (regressor std, not signal) |
| gordon_2014 | NEGATIVE | sfn_batch/Gordon_2014.pdf | MISSING (Fisher-Z connectivity) |
| cole_2013 | NEGATIVE | sfn_batch/Cole_2013.pdf | MISSING (MVPA feature std) |
| viduarre_2017 | NEGATIVE (hardest) | sfn_batch/Viduarre_2017.pdf | MISSING (post-decomp component) |
| marek_2022 | REGRESSION | multi_batch/Marek_2022.pdf | MISSING; AND intensity mode@1000 must NOT false-fire (numeric fix check) |
| chen_2015 | MACHINERY | sfn_batch/Chen_2015.pdf | MISSING; bare-MNI stays underspecified, grand-mean resolves (v5-parity check) |

```yaml
model: bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0
output_dir: results/batch_v6_delta   # gitignored
papers:
  - {paper_id: liu_2013,     path: <sfn_batch>/Liu_2013.pdf}
  - {paper_id: cho_2021,     path: <multi_batch>/Cho_2021.pdf}
  - {paper_id: power_2014,   path: <sfn_batch>/Power_2014.pdf}
  - {paper_id: gordon_2014,  path: <sfn_batch>/Gordon_2014.pdf}
  - {paper_id: cole_2013,    path: <sfn_batch>/Cole_2013.pdf}
  - {paper_id: viduarre_2017,path: <sfn_batch>/Viduarre_2017.pdf}
  - {paper_id: marek_2022,   path: <multi_batch>/Marek_2022.pdf}
  - {paper_id: chen_2015,    path: <sfn_batch>/Chen_2015.pdf}
```
(Use the real absolute paths; mirror how v5's config wrote them.)

### 3c. PREFLIGHT HARD STOP (before any extraction):
1. `python -c "import boto3; print(boto3.client('sts').get_caller_identity()['Arn'])"`
   → scoped IAM ARN, not root. If it raises → STOP.
2. Assert `config.model == "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"`
   (== v5's model). If NOT → STOP (this is the gate that caught the 4.6 mismatch on the
   Chen dry-run; do not run a model-shifted comparison).
3. One trivial live call on the config model to confirm the path works, THEN proceed.

### 3d. Run: `run_batch(load_batch_config(<the config>))`. Per-paper JSON lands in
`results/batch_v6_delta/papers/`. Capture wall-clock, any throttle/retry, token usage if
surfaced.

---

## 4. VALIDATION — the acceptance criterion, reframed for a semantic judgment (§4d)

For EACH paper, extract `temporal_standardization.method`'s extraction status + value
from its JSON, and report the table below. **This is not pass/fail — it's a per-paper
adjudication.**

### 4a. Positive set (Liu, Cho) — MUST populate:
- Report the extraction status + value + the grounding span.
- **Liu populates voxel_temporal_zscore** → the signal-standardization extraction works. ✓
- **Cho populates voxel_temporal_zscore** → the discrimination generalizes across phrasing
  ("z-scoring the segments" vs Liu's "temporal SD"). ✓
- **A positive-set paper FAILS to populate (MISSING)** → this is the WORSE failure: the
  LLM didn't recognize signal z-scoring even when present. Report the raw LLM output if
  captured; this means the positive-case extraction is unreliable, a prompt-refinement
  target. NOT "papered over" — flagged as a real gap.

### 4b. Negative set (Power, Gordon, Cole, Viduarre) — MUST stay MISSING:
- Report status for each. Expected: all MISSING, zero `voxel_temporal_zscore`.
- **A negative-set paper FALSE-FIRES (populates voxel_temporal_zscore)** → adjudicate,
  don't auto-fail:
  - Which paper? Viduarre false-firing is the EXPECTED-hardest case (component-vs-signal
    subtlety) — if ONLY Viduarre false-fires, that's a reportable finding about the
    boundary's subtlety, possibly a prompt-refinement target (sharpen the
    "post-decomposition components are OUT" instruction), NOT a build failure.
  - Power/Gordon/Cole false-firing would be MORE concerning (those are clearer cases —
    regressor / Fisher-Z / feature) → indicates the discrimination is failing on cases it
    should get right → prompt is under-specified → real problem.
  - For EACH false-fire, capture what the paper's sentence was and why the LLM may have
    mis-attributed it, so the finding is diagnostic.

### 4c. Regression checks:
- **Marek**: `temporal_standardization` MISSING (correct — Marek has no signal z-score),
  AND intensity convention = `global_mode_1000` (or MISSING) — the bare-word `mode@1000`
  false-fire from the numeric work must NOT have reintroduced. Confirm intensity didn't
  false-fire on Marek's "median sample size" / "default mode" statistics vocabulary.
- **Chen** (v5-parity machinery anchor): `temporal_standardization` MISSING; bare "MNI"
  stays underspecified (not coerced to a canonical variant); grand-mean-to-10000 resolves
  to `fsl_grand_mean_10000`. These should match v5 exactly — if they DON'T, something in
  Builds 1+2 disturbed unrelated extraction (a regression to investigate).

### 4d. THE ACCEPTANCE CRITERION (reframed):
**PASS = positive set populates AND negative set stays clean (zero spurious z-score),
AND the regression checks (Marek intensity, Chen parity) hold.**
**PARTIAL (likely, and INFORMATIVE) = Viduarre (only) false-fires, or a subtle boundary
case deviates** → report as a finding about discrimination limits, adjudicate whether it's
a prompt-refinement target or an accepted limitation. This is a legitimate scientific
outcome, not a failure to hide.
**FAIL (real problem) = a positive-set paper doesn't populate, OR a CLEAR negative case
(Power/Gordon/Cole) false-fires, OR a regression check breaks (Marek false-fires again /
Chen parity broken).**

---

## 5. STOP-and-report conditions

1. Preflight: STS fails, or `config.model != v5's 4.5 model` → STOP (§3c).
2. A positive-set paper fails to populate → STOP and report (this is a FAIL-class result;
   don't silently continue to full-20).
3. Power/Gordon/Cole (clear negatives) false-fire → STOP and report (FAIL-class:
   discrimination failing on cases it should get right).
4. Marek intensity false-fires again, or Chen parity breaks → STOP (regression from
   Builds 1+2 or the numeric work).
5. Viduarre-only false-fire → do NOT stop; report as the expected-hardest-case finding
   for adjudication.

---

## 6. What Build 3 does NOT do

- NOT full-20. Full-20 regeneration comes AFTER the discrimination is validated on this
  delta set. Running full-20 before knowing the discrimination works would produce 20
  papers of possibly-mis-discriminated output.
- NOT the KB-arm test (deferred — needs a confirmed pipeline-version-naming paper, which
  none of the current set provides; Chen doesn't name a pipeline live).
- Does NOT edit `batch_config.example.yaml` (own config; 4.6 example stays).
- Does NOT commit anything (results/ is gitignored; this is a validation run).

---

## 7. After Build 3

- If PASS or acceptable-PARTIAL → regenerate FULL-20 on 0.2.0 (own config, 4.5 pin), the
  labeling-delta review sheet. Note in methods: the v5→v6 delta reflects (a) the
  classify() labeling changes, (b) the synonym/numeric fixes, (c) the
  temporal_standardization step — model held constant at 4.5, so the delta is NOT
  model-confounded.
- If FAIL → fix the identified issue (prompt refinement for a clear-case false-fire, or
  the positive-case extraction gap) before full-20.
- KB-arm validation remains a separate future effort with a confirmed exemplar.
- The `(statistic, value)` intensity decomposition + `EXCLUDED_BY_PAPER` are later minors.
