# The step-field quote-support check, replayed over the 19 stored results (2026-10-26)

**Acceptance record for `docs/design/DELTA_value_in_quote_step_fields.md` §5–6.** The check
(`extractor_mvp/src/extractor_mvp/quote_support.py`, applied at `extractor.py:601-606`) was replayed with
no model calls over every EXTRACTED value of the seven `_FIELD_SPECS` fields in
`extractor_mvp/results/batch_a1_acceptance/papers/*.json` by
[step_field_support_replay.py](../../extractor_mvp/scripts/step_field_support_replay.py), using the
stored raw value (the model's own) and the stored span's text (what the resolver located). **No quote or
value text appears here**; cells are named by paper, field and span offsets. The held-out three
(liu_2005, tang_2025, wheaton_2004) are counted and never listed.

## Result: 0 demotions, as predicted

| field | EXTRACTED values (16 papers) | pass | demote |
|---|---|---|---|
| `spatial_normalization.target_space` | 12 | 12 | 0 |
| `spatial_normalization.resolution_mm` | 4 | 4 | 0 |
| `surface_projection.surface_registration` | 3 | 3 | 0 |
| `surface_projection.target_surface` | 3 | 3 | 0 |
| `intensity_normalization.convention` | 5 | 5 | 0 |
| `intensity_normalization.value` | 4 | 4 | 0 |
| `temporal_standardization.method` | 1 | 1 | 0 |

Held-out papers, counts only: 3 values, 0 demotions.

liu_2013's temporal method (4733–4884), the survey's one "absent" value, passes through
`TS_METHOD_SYNONYMS` on the alias `temporally normalized`, which the resolver's normaliser exposes by
repairing the line-break hyphen in the stored span.

## What carries each stored Literal cell (16 papers; offsets only)

"member" = the canonical token itself is in the quote; "alias #n" = the n-th table alias; "family" = an
alias of the field's underspecified list (prefix-tolerant, the safe direction); "verbatim" = an
unrecognized value present whole.

| paper | field | span | resolution | carried by |
|---|---|---|---|---|
| binder_1999 | target_space | 12507–12690 | resolved | member |
| chen_2015 | target_space | 3558–3797 | underspecified | family #0 |
| chen_2015 | surface_registration | 3558–3797 | underspecified | family #3 |
| chen_2015 | target_surface | 4713–4938 | resolved | alias #3 |
| chen_2015 | convention | 4006–4143 | resolved | alias #7 |
| cole_2013 | target_space | 4782–5431 | resolved | member |
| derosa_2025 | target_space | 9046–9375 | underspecified | family #0 |
| gordon_2014 | target_space | 5861–6015 | unrecognized | verbatim |
| liu_2013 | target_space | 4114–4332 | underspecified | family #0 |
| liu_2013 | temporal method | 4733–4884 | resolved | alias #8 |
| mueller_2021 | target_space | 4059–4217 | resolved | alias #6 |
| mueller_2021 | convention | 4452–4573 | resolved | alias #6 |
| oconnor_2017 | target_space | 18943–19098 | underspecified | family #0 |
| poldrack_2015 | target_space | 26030–26312 | unrecognized | verbatim |
| poldrack_2015 | surface_registration | 28132–28556 | resolved | alias #7 |
| poldrack_2015 | target_surface | 28899–29153 | resolved | alias #2 |
| poldrack_2015 | convention | 25523–25671 | resolved | alias #7 |
| power_2014 | target_space | 3728–3893 | unrecognized | verbatim |
| power_2014 | convention | 3368–3528 | resolved | alias #2 |
| vanderwal_2016 | target_space | 3431–3698 | underspecified | family #0 |
| weber_2024 | target_space | 5236–5318 | underspecified | family #0 |
| weber_2024 | surface_registration | 3888–3978 | unrecognized | verbatim |
| weber_2024 | target_surface | 5400–5531 | unrecognized | verbatim |
| weber_2024 | convention | 4797–5068 | unrecognized | verbatim |

The four numeric cells pass by digit-exact numeric equality (two resolutions written "3" against a
stored 3.0, one "2", one intensity value), and the four `intensity_normalization.value` cells likewise.

## Mutations, the gate, and the suites

- An alias removed from its table (`normalized to a mode of 1,000`): 2 tests fail; the replay demotes
  poldrack's convention 25523–25671.
- Aliases split into first-use variants: 5 tests fail, the split-alias test among them (a bare "MNI152"
  would support `MNI152NLin6Asym`).
- A numeric tolerance of 1: 3 tests fail.
- The temporal table emptied: 6 tests fail; the replay demotes liu_2013's 4733–4884.
- The digit rule removed from the shared matcher: 9 tests fail, the motion leak regression among them.
- The motion replay is unchanged by the tightened matcher: 30 unsupported, 20 routed, 110 kept, 20
  untouched — 0 of 160 resolved draws moved.
- Identity gate against HEAD, derived first as 19 identical (the gate re-renders stored JSONs; the
  check runs at extraction; 0 stored JSONs carry the new reason): 19 identical. Negative control
  against `d31e8b7`: 0 identical, 19 changed, as derived.
- 447 passed in extractor_mvp (CI's two steps), 235 root; hooks and `ruff format --check` clean.
