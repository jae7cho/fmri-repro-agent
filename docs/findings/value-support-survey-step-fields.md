# Would the value-support guard pass the seven step fields? A read-only survey of the stored results

**Measured 2026-10-26, no model calls, nothing changed.** Part D of the 2026-10-25 instruction
established that `span_resolver.quote_supports_value` runs on two fields only — `base_pipeline.version`
(`extractor.py:677`) and the pipeline name (`extractor.py:778`) — and that the seven `_FIELD_SPECS` step
fields get the span check alone (`_process_field`, `extractor.py:569-585`): the quote is confirmed to
exist in the paper, not to support the value. Before that guard is extended to those fields, this
survey asks what it would do to the values already stored. Generator:
[value_support_survey.py](../../extractor_mvp/scripts/value_support_survey.py), over
`extractor_mvp/results/batch_a1_acceptance/papers/*.json` (19 papers; gitignored).

**What is compared.** For every EXTRACTED value of the seven fields: the model's own raw value (the
stored `resolutions` record; the SpecifiedTerm's `verbatim` or the number as written when no record
exists) against the resolved span's text, with `quote_supports_value` unchanged — whole-token,
NFKD-normalised, no inflection tolerance. A failure is classed as `synonym_in_quote` when an alias of
the resolved canonical value (`synonym_resolver.SYNONYMS_BY_FIELD`) is in the quote, `number_form` when
the number is in the quote in another surface form, else `absent`.

**Held-out status.** liu_2005, tang_2025 and wheaton_2004 are counted and not listed: no field, offset
or class for them appears here, and none of their text was read. Counts only: **pass 2, fail 1**
across all three.

## Per field — the 16 non-held-out papers

| field | EXTRACTED values | guard would pass | would fail |
|---|---|---|---|
| `spatial_normalization.target_space` | 12 | **12** | 0 |
| `spatial_normalization.resolution_mm` | 4 | 0 | **4** |
| `surface_projection.surface_registration` | 3 | 2 | 1 |
| `surface_projection.target_surface` | 3 | 2 | 1 |
| `intensity_normalization.convention` | 5 | 1 | **4** |
| `intensity_normalization.value` | 4 | 4 | 0 |
| `temporal_standardization.method` | 1 | 0 | 1 |

## The eleven failures — paper, field, span offsets, class (no quote text)

| paper | field | span | class |
|---|---|---|---|
| chen_2015 | `surface_projection.target_surface` | 4713–4938 | synonym_in_quote |
| chen_2015 | `intensity_normalization.convention` | 4006–4143 | synonym_in_quote |
| liu_2013 | `spatial_normalization.resolution_mm` | 4617–4732 | number_form |
| liu_2013 | `temporal_standardization.method` | 4733–4884 | **absent** |
| mueller_2021 | `intensity_normalization.convention` | 4452–4573 | synonym_in_quote |
| oconnor_2017 | `spatial_normalization.resolution_mm` | 18943–19098 | number_form |
| poldrack_2015 | `spatial_normalization.resolution_mm` | 26030–26312 | number_form |
| poldrack_2015 | `surface_projection.surface_registration` | 28132–28556 | synonym_in_quote |
| poldrack_2015 | `intensity_normalization.convention` | 25523–25671 | synonym_in_quote |
| power_2014 | `spatial_normalization.resolution_mm` | 3728–3893 | number_form |
| power_2014 | `intensity_normalization.convention` | 3368–3528 | synonym_in_quote |

## Reading

- **`target_space`, the headline field, passes on every stored value** (12 of 12 on the 16 papers).
  The committed target_space rates are not exposed to the carry that hit motion.
- **Ten of the eleven failures are surface-form, not fabrication.** Four are numbers the guard's
  whole-token rule cannot match across forms ("3.0" against "3 × 3 × 3" or "3mm"); six are values the
  model returned in a canonical or synonym form whose alias *is* in the quote. The guard as it stands
  would demote all ten; a form-tolerant match of the kind the motion post-check uses would keep them.
- **One value is absent from its quote outright:** liu_2013's `temporal_standardization.method`. That
  is the only stored step-field value in the 16 papers that is not backed by its own quote in any form,
  and it is the one the poster would have to name if the claim "every value is in its quote" were made.
- **The three held-out papers contribute 1 failure in 3 values**; which paper, which field and which
  class are not stated here (C11/C26).

## What this licenses

Nothing is changed by this survey. If the check is extended to the seven fields, the rule must be
form-tolerant (otherwise ten correct extractions demote) and a replay over these 19 stored results is
the acceptance test, with liu_2013's temporal method pre-declared as the one expected demotion. Until
then the honest description is the author's: **every value's quote is found in the paper; for the
pipeline name and version the value must also appear in its quote; motion has that check as of
2026-10-26; the seven step fields do not yet.**
