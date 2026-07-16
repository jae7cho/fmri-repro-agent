# Finding: a deterministic subject validator (INERT) — enforcement is bounded, coverage is not

**Module:** `extractor_mvp/src/extractor_mvp/subject_validator.py` · **Tests:**
`extractor_mvp/tests/test_subject_validator.py` · **Status: INERT** — nothing in the four-state
path imports it; production output is byte-identical to HEAD. Built and measured only. Consumption
is a separate, later decision (tier-5 precedent: built, validated, builders ignored it; wiring it
in was its own deliberate change).

## What it is

`derived_subject_term(quote)` returns the derived-product term bound as the SUBJECT of the first
normalization verb in a quote — and **which list it came from** — or `None`. It makes the
`EXTRACTION_PROMPT` DECISION RULE's *enumerated* derived-product exclusions deterministic. It does
not invent a rule.

- **Passive-voice heuristic.** For "X was normalized" the subject precedes the verb, so only the
  span BEFORE the first normalization verb is scanned. Text after is ignored, so *"the BOLD time
  series were z-scored before computing functional connectivity"* is a TRUE positive (the
  downstream FC mention does not flag it).
- **Firewall-clean.** The model's own quote against a fixed lexical list, compared under
  span_resolver's normalization (`_delete_with_map ∘ normalize_with_offset_map`) — the same
  instrument as `quote_supports_value`. No KB, no priors, no LLM.

## Two lists, measured separately — because the failures are two different classes

The arm-1 measurement (see [temporal-firewall-fix](temporal-firewall-fix.md)) surfaced two
derived-subject shapes the SFC prompt patch does not reach. They are **not** the same failure:

- **viduarre / ICA — an OVERRIDE failure.** The DECISION RULE explicitly names "ICA/PCA
  components." The model extracted anyway (4/10 under the fixed prompt). It was told and disobeyed.
- **derosa / activation-patterns — a COVERAGE failure.** "Activation patterns" appears nowhere in
  the DECISION RULE (the CRITICAL block's "activation tables" is a different referent). The model
  had no rule to override.

So the validator carries two lists:

- `_PROMPT_TAXONOMY` — lifted **VERBATIM** from the DECISION RULE (FC, SFC, ReHo, seed-connectivity,
  correlation/connectivity matrix, gradient, ICA/PCA components, nuisance regressors, classifier
  features, QC metrics, statistical map). Measures **ENFORCEMENT**: what deterministic checking
  buys on terms the prompt already names.
- `_DECLARED_EXTENSIONS` — **NOT** in the prompt. Declared, motivated additions, each citing the
  paper that forced it. `activation pattern` (derosa_2025) is the first and, so far, only entry.
  Measures **COVERAGE**: derived-subject shapes the prompt never named.

The mechanism ladder this makes explicit: **named + exemplified → converts 100%** (chen/SFC);
**named, not exemplified → ~60%** (viduarre/ICA, ~40% override residual); **not named → no effect
possible** (derosa). The temporal-firewall doc's "second derived-subject shape the near-miss
doesn't reach" is true of both but hides that only one (viduarre) was ever covered.

## Measurement (arm-1 recorded draws — NO new model calls; point estimates, one session)

Run over every EXTRACTED draw in the arm-1 raw dumps (`results/tempfw_*.jsonl` post-v0.4.0 +
`results/chen_fix_ab.jsonl` pre-v0.4.0 for viduarre, whose post-v0.4.0 baseline is 0/10). Slice
hashes asserted identical to arm-1 (chen `1a6d8afbec64e926`, viduarre `9809990c45a78488`, liu
`ee061645c158000b`, derosa `a08a71f9548c3bb0`) so this inherits arm-1's input controls.

| paper | EXTRACTED draws | flagged | by prompt | by extension |
|---|---|---|---|---|
| liu_2013 (true positive) | 30 | **0** | 0 | 0 |
| chen_2015 | 31 | 31 | **31** (SFC) | 0 |
| viduarre_2017 | 4 | 4 | **4** (ICA) | 0 |
| derosa_2025 | 19 | 19 | 0 | **19** (activation pattern) |

- **No true-positive regression:** liu 0/30 flagged. (A liu flag is a pre-declared STOP — design
  failure, not tuning.)
- **Enforcement** (prompt list, terms named independently of these failures): flags chen 31/31 and
  viduarre 4/4, 0 liu. This is the load-bearing number — roughly viduarre's ~40 override points made
  unoverridable on covered terms.
- **Coverage** (extension list): derosa 19/19 — but "activation pattern" was added *after* seeing
  derosa. Its recall on its own motivating case is trivially 100% and is **fit, not predictive**.
  Reported separately precisely so it is not mistaken for enforcement.

## Known holes (documented, tested as holes)

- **Active voice** — "we normalized the SFC map" puts the derived object AFTER the verb; not
  caught. Asserted explicitly in the tests as a fixed property.
- **Short-acronym substring** — FC/ICA/PCA match by aggregated substring and could over-match in
  principle; on the measured arm-1 slices they do not.
- **Heuristic fit to 4 cases** — the passive-voice scan and the extension list are fit to arm-1's
  four papers; generalization is unmeasured.

## The structural limit — the real result

A derived-product denylist is **UNBOUNDED**. Every paper can coin a new derived product — gradients,
eigenvector centrality, ALFF maps, beta series, parcel timeseries. derosa is the first proof,
arriving immediately, from a corpus of twenty. So the validator's honest claim shrinks to: **it
makes enumerated exclusions unoverridable, and it inherits the prompt's coverage gap exactly.** It
does not solve derived-subject false positives; it enforces the ones already thought of.

**Escalation criterion.** The **extension rate** is the measurement that decides
deterministic-vs-LLM. One extension (derosa) is not a trend. But every addition is logged in
`_DECLARED_EXTENSIONS`, so the rate is trackable at zero cost. If each new paper needs a new
extension, enumeration is the wrong instrument and the build plan's LLM Tier 2 — which can
generalize over "is this referent derived?" without a list — is indicated.

## Not done here (deliberately)

- **Not wired.** No import in the four-state path; production is byte-identical to HEAD. Consumption
  is a separate decision that needs this measured precision first.
- **The prompt is not changed.** Adding "activation pattern" to `EXTRACTION_PROMPT` would be a
  separate prompt change needing its own A/B against the hashed slice; bundling it into this inert
  build would confound both. The extension list is code, measured inert — no prompt A/B needed.
