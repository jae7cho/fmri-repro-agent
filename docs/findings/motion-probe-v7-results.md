# motion_correction.method — stanza version 7, thirteen papers, results: the adoption rule applied; version 4 restored (2026-10-27)

**DIAGNOSTIC. Not an evaluation.** Thirteen papers at K=10 under stanza version 7, against the
readings pre-declared in prereg Amendment 11 (written before the edit and before any call). **No rate,
fraction, percentage or accuracy figure** appears here or may be computed from the projection behind
it (prereg `:9-10`, `:158-159`). Counts are counts of draws. **A new vintage**: never pooled with any
earlier run's draws.

- **Run** 2026-10-27, 16:25:50–16:51:46 UTC. **K** = 10, 13 papers, 130 draws, one session.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Stanza** sha256 `d353fb478cd1fbbe03d079a51b322c749c8b8a3431b58261745ac17b503d5a1d` (7,848
  characters): version 6 with the attribution level removed from the output. **Gate:** the manifest
  carries this hash and `motion_method_prompt_frozen_sha256` equal to it; checked before any record
  was read. No held-out id admitted (`held_out_admitted: []`, licence `None`).
- **Labels** are the v1.8 workbook as committed at `e624361` (sha256 `8cd9cbbb…`): `named_tool` 9,
  `deferred` 8, `described_only` 2; column R on the six `named_tool` probe papers.
- **Per-draw record** [ground_truth/motion_probe_v7_projection.csv](../../ground_truth/motion_probe_v7_projection.csv)
  — status, heuristic class, state-map row, span offsets, deferral target kind, `model_state`,
  `model_vs_heuristic`, and the derived `attribution`; **no quote or value text** (50 needles derived
  from the records by script, 0 present in the CSV). The unprojected run is at
  `extractor_mvp/results/motion_probe_v7/` (gitignored).
- **Reasks** 5 of 130 (binder 2, ciric 2, cole 1). **Errors** 1 (binder, the binding validator after
  reask). **Held-out:** liu_2005, tang_2025 and wheaton_2004 untouched; not in the probe set.
- **Fitted, by the record:** all thirteen. ciric is post hoc. No count below is independent.

## The stanza diff from version 6, quoted in full

Five hunks, every one a level word; nothing else moved.

```
46c46
< - PACKAGE-LEVEL ATTRIBUTION, the one exception to NOT BOUND: the text names, for its preprocessing
---
> - PACKAGE ATTRIBUTION, the one exception to NOT BOUND: the text names, for its preprocessing
49,50c49,50
<   does not count as one), and asserts the motion step -> that package is the method at the PACKAGE
<   level, and this decides the field: skip step 4. The list, closed: AFNI (3dvolreg), FSL (MCFLIRT),
---
>   does not count as one), and asserts the motion step -> that package is the method, and this
>   decides the field: skip step 4. The list, closed: AFNI (3dvolreg), FSL (MCFLIRT),
84,85c84,85
<   same tool); motion_correction_binding = "named_tool_step".
< - No tool bound to the step, but step 3's PACKAGE-LEVEL ATTRIBUTION holds -> status "extracted";
---
>   same tool); motion_correction_binding = "named_tool".
> - No tool bound to the step, but step 3's PACKAGE ATTRIBUTION holds -> status "extracted";
89c89
<   "named_tool_package".
---
>   "named_tool".
105,106c105,106
< "named_tool_step" when step 3 found a bound tool, "named_tool_package" when step 3's package-level
< attribution holds, "described_only" otherwise.
---
> "named_tool" when step 3 found a bound tool or its package attribution holds, "described_only"
> otherwise.
```

## The adoption rule, applied as written

Amendment 11: *version 7 is adopted if every `named_tool` paper returns `named_tool` with the label's
value on at least 8 of 10 (derosa at the processed layer), and no paper loses more than 2 matching
draws against its version-6 count; adopted → version 7 freezes; not adopted → `b0093774…` is restored
by amendment and freezes; either way, no further iteration before the corpus run.* The value match is
normalized exact equality (case, whitespace and hyphens folded). "Returns" is read at the raw layer,
as the probe has always scored it, except derosa, which the rule names at the processed layer.

| clause 1 paper | label value | `named_tool` with the value, of 10 | met |
|---|---|---|---|
| ciric_2017 | MCFLIRT | **10** | yes |
| agtzidis_2020 | SPM12 | **10** | yes |
| mueller_2021 | SPM12 | **10** at the raw layer — 7 quoted against the realignment sentence and demoted by the check, 3 quoted the SPM12 sentence and kept | yes |
| derosa_2025 | FSL | **10** at the processed layer, by the fallback (`ICA-AROMA` routed, the FSL sentence the quote) | yes |
| gordon_2014 | SPM8 | **7** (`SPM8` ×7; an operation phrase under a `named_tool` binding ×3) | **no** |
| cole_2013 | AFNI | **0** (`deferred` to its citation ×6, `described_only` on the step-list sentence ×4; the package rule never fired) | **no** |

| clause 2 paper | version-6 count | version 7 | change |
|---|---|---|---|
| liu_2013 | 10 | 5 | **−5** |
| poldrack_2015 | 8 | 4 | **−4** |
| cole_2013 | 4 | 0 | **−4** |
| gordon_2014 | 8 | 7 | −1 |
| binder_1999 | 8 | 8 | 0 |
| power, braun, viduarre, vanderwal, ciric | 10 | 10 | 0 |
| agtzidis_2020 | 6 | 10 | +4 |
| mueller_2021 | 8 | 10 | +2 |
| derosa_2025 | 0 | 10 | +10 |

**Outcome: clause 1 fails on two papers and clause 2 on three; version 7 is not adopted.** By the
rule as written, **version 4 (`b0093774…`) is restored by Amendment 12 and freezes**, and **there is
no further iteration before the corpus run.** The comparison crosses days, as Amendment 11 noted; the
losses are losses under the rule and are not attributed to version 7 alone.

## Each paper under version 7, against Amendment 11's readings

State-map rows from raw `status` and raw `value` only; the level derived in code from the resolved
span and compared with column R.

| paper | v1.8 label | pre-declared | returned |
|---|---|---|---|
| ciric_2017 | `named_tool` / MCFLIRT / `step` | row 2, `MCFLIRT`, span 4410–4507 | **row 2 ×10, `MCFLIRT` ×10**; span 4410–4507 ×6 and a longer span 4204–4819 ×4 containing the clause; level `step` ×10 |
| agtzidis_2020 | `named_tool` / SPM12 / `package` | row 2, `SPM12`, the package sentence | **row 2 ×10, `SPM12` ×10**, span 7020–7085 ×10; level `package` ×10 |
| cole_2013 | `named_tool` / AFNI / `package` | row 2, `AFNI`, the package sentence | **`deferred` ×6 to ref 23** (CALL 11's reading of the step list), **row 1 ×4** on the step-list sentence 4992–5431; `AFNI` on no draw |
| gordon_2014 | `named_tool` / SPM8 / `step` | row 2, `SPM8`, span 4860–5140; level `step` | **row 2 ×7** (`SPM8`), row 1 ×3 (an operation phrase under `named_tool`), all at 4860–5140; level `step` ×7 |
| mueller_2021 | `named_tool` / SPM12 / `package` | row 2, `SPM12`, quote = the SPM12 sentence | **row 2 ×10, `SPM12` ×10**; the quote moved to the SPM12 sentence on **3** (3738–3893, kept, level `package`) and stayed on the realignment sentence on 7 (demoted, `motion_value_unsupported_by_quote`) |
| derosa_2025 | `named_tool` / FSL / `package`, processed | raw `ICA-AROMA` routed; processed `FSL` by the fallback | **raw `ICA-AROMA` ×10; processed `FSL` ×10** on the FSL sentence 8801–9045, reason `motion_value_routed_fallback_to_package:ica_aroma->FSL` ×10; level `package` ×10 by construction |
| liu_2013 | `deferred` | row 4 ×10 | **row 4 ×5** (the scripts), **row 1 ×5** on the operation sentence 3344–3658 |
| braun_2015 | `deferred` | row 4 ×10 | row 4 ×10 |
| viduarre_2017 | `deferred` | row 4 ×10 | row 4 ×10, all to Glasser et al. |
| vanderwal_2016 | `deferred` | row 4 ×10 | row 4 ×10, kind `pipeline` |
| power_2014 | `described_only` | row 1 ×10 | row 1 ×10 at 3112–3528 |
| binder_1999 | `described_only` | row 1 on most | row 1 ×8 at 11023–11180; **`deferred` ×1 to the algorithm citation**; 1 error (no binding after reask); no row 3 today |
| poldrack_2015 | `deferred`, reported as found | version 6's 8 of 10 noted | **row 4 ×4** (3 to ref 45, 1 to the pipeline), row 1 ×6 at 25523–25671 |

Rows over 130 draws: row 1 ×36, row 2 ×47, row 4 ×46, error ×1. Model binding against the frozen
heuristic: **80 agree, 3 disagree** (gordon's operation phrases under `named_tool`), 0 undecided.

## The level, derived in code, against column R — agreement counts, diagnostic

| paper | column R | agree | disagree | no level (row 1, or span unresolved) |
|---|---|---|---|---|
| ciric_2017 | step | 10 | 0 | 0 |
| agtzidis_2020 | package | 10 | 0 | 0 |
| derosa_2025 | package | 10 (by construction) | 0 | 0 |
| gordon_2014 | step | 7 | 0 | 3 |
| mueller_2021 | package | 3 | 0 | 7 |
| cole_2013 | package | 0 | 0 | 10 |

**40 agree, 0 disagree, 20 without a level.** Where the level could be derived it matched column R
every time; what version 6 asked the model for and got backwards on gordon and mueller, the quoted
sentence settles on its own.

## What was found that was not pre-declared

- **cole's package rule did not fire under version 7** after firing on 4 draws under version 6: the
  model read the step list under its citation (CALL 11) on 6 draws and in the paper's voice on 4.
- **mueller's quote moved to the package sentence on only 3 of 10**, so the check demoted 7 — the
  same shape as version 6, now without the level to blame.
- **liu_2013 fell to 5 of 10** after two runs at 10 (versions 5 and 6); **poldrack to 4** after 8. Both
  are the day-to-day movement the record has measured before, and both count under the rule.
- **The fallback worked as designed** on derosa: 10 of 10, the processed value FSL on the sentence that
  names it, the raw layer untouched.
- **binder deferred once** to the citation that names its algorithm — the first deferred draw this
  paper has produced in any run.

## Named lines

- Draws 130; reasks 5; errors 1 (binder); unresolved spans 0.
- Demoted on the processed layer: unsupported 7 (mueller); routed 0 (derosa's 10 fell back to the
  package instead); fallback 10 (derosa).
- Excluded by name: `undecided` 0; `unread` 0; `multi_target_unscoreable` 0.
- Wall time per draw, mean: power 4.42 s, binder 16.11 s, liu_2013 11.02 s, derosa 6.96 s, agtzidis
  4.27 s, poldrack 21.79 s, ciric 12.07 s, braun 11.14 s, viduarre 10.02 s, vanderwal 15.05 s, cole
  19.78 s, gordon 7.39 s, mueller 15.23 s.

## The restore and the freeze

By Amendment 12, the stanza constant is version 4 verbatim again, sha256
`b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837`; the pin and the recorder's constant
carry it with dated notes retaining the chain through `8df070da…` and `d353fb47…`. The code built since
— the matcher's ruling 5, the routing fallback, the derived level and the recorder's per-draw
diagnostic — stays, because it is not the stanza. **No further iteration before the corpus run.**

## Status

- Labels unchanged by this document.
- The corpus run runs under `b0093774…`, after the held-out release amendment, which waits on the
  held-out label checks: column R is filled on 2 of the 3 held-out rows.
