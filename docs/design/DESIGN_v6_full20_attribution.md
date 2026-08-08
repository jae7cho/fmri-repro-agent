# Design: v6 full-20 regeneration + v5→v6 auto-attribution diff

**Prerequisite:** committed at `e3a43fe` (all 5 units: synonym/numeric, schema 0.2.0,
routing, span de-hyphenation, + earlier CI/config). CI green on 0.2.0 types. The
`temporal_standardization` discrimination is validated on the delta set (Liu clean
positive end-to-end; clear negatives clean; Viduarre the documented hard-boundary
finding; Cho removed as mislabeled exemplar).

**Goal:** regenerate the full-20 v6 review sheet on the 0.2.0 schema (4.5-pinned to match
v5), and produce a v5→v6 field-level diff that AUTO-ATTRIBUTES each change to a known
cause — so the delta is defensible ("the v5→v6 changes are exactly these attributable
changes") and reviewable (each changed field shows its grounding quote as the receipt).

---

## 0. Key finding that shaped this design (no extractor change needed)

The grounding quote is ALREADY captured and rendered — confirmed by reading
`generate_sfn_review.py`:
- **Successful fields:** `classify()` (line ~369-371) pulls `spans[0].text` into the
  `verbatim_quote` column.
- **Failed fields:** `build_df()` (line ~428-433) fills `verbatim_quote` from the
  diagnostic's `raw_quote`.
- v5 JSONs ALSO carry `spans[0].text` (the span mechanism predates v6), so the diff can
  compare quotes across versions.

**Consequence:** NO extractor change to "store the quote." The earlier "raw-value capture
for successful fields" gap is already closed by the span mechanism (the span IS the
retained quote). This design is 3 pieces, not 4: generator extension, full-20 run,
attribution diff.

---

## 1. Piece 1 — extend `generate_sfn_review.py` for `temporal_standardization`

The generator's `build_df()` iterates ALL steps generically (`for step in ...steps`), so
`temporal_standardization`'s `method` field WILL render as a per-field row automatically —
VERIFY this by running the generator on the delta-batch output and confirming a
`temporal_standardization / method` row appears.

The ONE hardcoded thing that won't auto-update: the `GLOSSARY` list. Add:
```python
    (
        "temporal_standardization",
        "method",
        "Per-voxel temporal standardization of the BOLD signal (z-score over time) "
        "as a terminal preprocessing step",
        "voxel_temporal_zscore | other",
        "",
    ),
```
No other generator change. Do NOT alter `classify()` (it already handles the quote and the
reason_map is current). Confirm the delta-batch sheet shows Liu's
`temporal_standardization / method = voxel_temporal_zscore` with its quote.

---

## 2. Piece 2 — the full-20 run

### 2a. Config: own YAML `results/batch_v6_full_config.yaml` (gitignored output). Mirror
v5's `sfn_batch_v5_config.yaml` EXACTLY for the 20-paper set and paths — same paper_ids,
same PDF paths under `tested_lit/sfn_batch/`. The ONLY difference from v5's config is the
output_dir (new gitignored dir, e.g. `results/batch_v6_full`).
```yaml
model: bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0   # == v5 exactly; NOT 4.6
output_dir: results/batch_v6_full
papers:  # the same 20 as sfn_batch_v5_config.yaml — copy that list verbatim
  ...
```

### 2b. PREFLIGHT HARD STOP (before extraction):
1. `python -c "import boto3; print(boto3.client('sts').get_caller_identity()['Arn'])"`
   → scoped IAM ARN, not root. Raises → STOP.
2. Assert `config.model == "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"` (==v5).
   Not 4.5 → STOP. (This is the gate that caught the 4.6 mismatch on the Chen dry-run.)
3. Confirm HEAD is `e3a43fe` (or later) and `git status` clean — the run must validate
   COMMITTED code, not a working-tree change. If not → STOP.
4. One trivial live call on the config model, THEN proceed.

### 2c. Run `run_batch(load_batch_config(<config>))`. 20 papers → per-paper JSON in
`results/batch_v6_full/papers/`. Capture wall-clock, throttle/retry, any per-paper FAIL
(the batch catches per-paper errors and continues — report any that failed).

### 2d. Generate the v6 sheet: `python generate_sfn_review.py --results-dir
results/batch_v6_full --output sfn_review_v6.xlsx` (after Piece 1's Glossary edit).

---

## 3. Piece 3 — the v5→v6 auto-attribution diff (the one new script)

New script `extractor_mvp/diff_v5_v6.py` (or a scratch script — it's analysis, not shipped
code; decide whether it's worth keeping). Loads both batches' per-paper JSONs and diffs
the TARGETED fields + `temporal_standardization.method` per paper.

### 3a. Scope (confirmed): the 6 targeted fields + `temporal_standardization.method`:
```
spatial_normalization.target_space, spatial_normalization.resolution_mm,
surface_projection.surface_registration, surface_projection.target_surface,
intensity_normalization.convention, intensity_normalization.value,
temporal_standardization.method   # new — absent in v5
```
Untargeted fields are NOT diffed per-field (they're `not_targeted_by_mvp` in both, can't
change on extraction). Their LABEL shifted uniformly under classify() — noted ONCE
globally (§3d), not enumerated.

### 3b. For each (paper, field), extract from BOTH v5 and v6 JSONs:
- extraction status (EXTRACTED / MISSING_FROM_PAPER / DEFERRED_TO_CITATION)
- resolved value (if EXTRACTED)
- the grounding quote: `spans[0].text` if EXTRACTED, else the diagnostic `raw_quote` for
  that field path (same lookup `build_df` uses)
- inference reason (for the labeling attribution)

### 3c. AUTO-ATTRIBUTION rules — classify each change by cause. **Quote comparison is
NORMALIZED** (strip line-break hyphens `-\n`, collapse whitespace) before comparing, so
PDF-extraction jitter between runs does NOT masquerade as a different quote. Rules, in
order:

| v5 → v6 change | attributed cause |
|---|---|
| field absent in v5 (temporal_standardization) | NEW STEP (schema migration) — report v6 status separately (populated=Liu / missing=rest); NOT a "change" |
| v5 `quote_not_found` → v6 resolved (EXTRACTED) | SPAN-RESCUE (de-hyphenation fix) |
| status/value identical, only inference REASON/label differs | LABELING (classify() change) |
| value changed, **normalized quote identical** | CODE FIX (synonym/numeric/z-score-removal) — same sentence, different resolution = a resolver/schema change did it |
| value/status changed, **normalized quote DIFFERENT** | LLM NONDETERMINISM — the model read a different sentence (cf. Chen surface_registration v5→v6 flip, no code change) |
| intensity convention was `voxel_temporal_zscore` in v5, now MISSING/other in v6 | Z-SCORE REMOVAL (build 1) — the member left the intensity Literal |
| no change | (omit) |

**Honesty caveat baked into the rules:** "same quote → code fix" is only sound because the
quote is the evidence the LLM read the same sentence. If quotes are byte-different only due
to PDF jitter, normalization collapses that; if they're genuinely different, it's
nondeterminism. This is the distinction the JSONs-alone couldn't make and the quote
resolves — but it depends on the normalized-quote comparison being correct. If a change
can't be classified by ANY rule → label `UNATTRIBUTED — INVESTIGATE` and STOP (§5).

### 3d. Output: a table (per paper × field) of CHANGED fields only, columns:
`paper_id | field | v5(status,value) | v6(status,value) | v5_quote | v6_quote |
attributed_cause`. Plus:
- A global note: "All untargeted-MVP fields relabeled uniformly by classify() (e.g.
  Missing→'Not targeted (out of MVP scope)'); this is a labeling change, not an
  extraction change — not enumerated per-paper."
- A summary count per cause: N span-rescues, N labeling, N code-fix, N nondeterminism, N
  new-step-populated, N z-score-removal, N unattributed.

### 3e. The two secondary results (report explicitly):
- **temporal_standardization coverage**: which of the 20 populate `method` (expected: Liu;
  possibly others if any state signal z-scoring — report the actual set + their quotes).
- **span-rescue count**: how many fields flipped `quote_not_found`→resolved (the general
  win from de-hyphenation — expected agtzidis and possibly others per the offline probe).

---

## 4. Acceptance / what "done" means

- Full-20 runs, ≤ expected per-paper failures (report any FAIL).
- Every changed field is auto-attributed to a known cause (span-rescue / labeling /
  code-fix / nondeterminism / new-step / z-score-removal). **Zero UNATTRIBUTED changes** —
  any unattributed change is a STOP-and-investigate (it may be a regression from builds
  1-5).
- The two secondary results reported (temporal_standardization coverage, span-rescue
  count).
- The v6 sheet (`sfn_review_v6.xlsx`) shows temporal_standardization rows with quotes.

**This is NOT a pass/fail on extraction quality** — it's a regeneration whose delta is
fully attributed. A field changing is fine IF attributed; the failure mode is an
UNATTRIBUTED change (unexplained by any known cause = possible regression).

---

## 5. STOP-and-report conditions

1. Preflight: STS fails / model != v5's 4.5 / HEAD not clean → STOP (§2b).
2. Any v5→v6 change that NO attribution rule classifies → `UNATTRIBUTED — INVESTIGATE`,
   STOP and report the field + both quotes (possible regression from builds 1-5, or a
   rule gap).
3. A CLEAR-negative paper (Power/Gordon/Cole) now populates temporal_standardization
   (they were clean in the delta set) → STOP (discrimination regressed on the full run).
4. Chen v5-parity breaks (bare-MNI no longer underspecified, grand-mean no longer
   resolves) → STOP (regression).
5. Per-paper batch FAILs beyond what v5 had → STOP and report which/why.

---

## 6. What this does NOT do

- Does NOT edit `batch_config.example.yaml` (own config; 4.6 example stays).
- Does NOT change the extractor (quote already captured — §0).
- Does NOT commit the results (gitignored) — the diff/sheet are analysis artifacts.
- Does NOT touch the KB arm (deferred; Cho is the future exemplar — 3 datasets, 3
  pipeline-deferral patterns).
- Does NOT prompt-sharpen Viduarre (hold the finding; decide on sharpening only if the
  full-20 shows the component-vs-signal boundary trips MORE than Viduarre — sharpening on
  n=1 risks over-suppressing real signal z-scores).

---

## 7. After this

- Review `sfn_review_v6.xlsx` + the attribution table by hand (the goal: internalize the
  20 papers' extractions over a run or two).
- If all changes attributed + secondaries sane → v6 is the citable sheet; methods can
  state "v5→v6 delta = [labeling + synonym/numeric + temporal_standardization +
  span-rescue], model held at 4.5, no model confound."
- Viduarre prompt-sharpening: separate, evidence-gated decision.
- KB-arm validation: separate effort, Cho exemplar.
- `(statistic, value)` intensity decomposition + `EXCLUDED_BY_PAPER`: later minors.
