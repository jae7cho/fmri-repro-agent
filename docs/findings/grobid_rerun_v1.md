# GROBID re-run, corpus_grobid_v1 (2026-11-07)

Code: `4c3b4b4` (tier 5b citation regions, CRF the expected image, the hop's reference list from
pypdf text); the corpus run was made from a worktree pinned there. Scorer: `1488ffb`
(`scripts/score_motion.py`). GROBID: `lfoppiano/grobid:0.9.1-crf` (version 0.9.1). Model:
`bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Docker VM memory 16 GB. Numbers only.

## 1. The quote gate after tier 5b

Same quotes and method as `grobid_gate_v2.md` §4 (747 stored quotes, 67 label quotes); GROBID text
now carries each citation as a skippable region. Full and CRF images give identical counts on every
row.

| | quotes | found on pypdf | found on GROBID v2 | found on GROBID with 5b | lost v2 | lost with 5b | gained with 5b |
|---|---|---|---|---|---|---|---|
| three record sets | 747 | 690 | 663 | 701 | 52 | 14 | 25 |
| two label workbooks | 67 | 49 | 46 | 48 | 3 | 1 | 0 |

Lost with 5b, by cause (v2's labels): N 0 (was 14), R 0 (was 26), G 7 (agtzidis_2020, the
multiplication sign), F 6 (Silchenko_2023, prose filed as a figure), X 2 (held out, absent from the
TEI). Every N and R loss resolves.

Papers whose counts changed or that still lose a quote:

| set | paper | quotes | found on pypdf | found on GROBID v2 | found on GROBID with 5b | lost v2 | lost with 5b | gained with 5b | lost with 5b by cause |
|---|---|---|---|---|---|---|---|---|---|
| batch_coverage_v4 | agtzidis_2020 | 16 | 16 | 9 | 9 | 7 | 7 | 0 | G 7 |
| batch_coverage_v4 | cole_2013 | 15 | 14 | 7 | 14 | 7 | 0 | 0 |  |
| batch_coverage_v4 | poldrack_2015 | 36 | 29 | 35 | 36 | 1 | 0 | 7 |  |
| motion_correction_labels_v1.xlsx | cole_2013 | 2 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| motion_correction_labels_v1.xlsx | tang_2025 (held out) | 1 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| smoothing_filtering_labels_v1.xlsx | liu_2005 (held out) | 2 | 1 | 0 | 0 | 1 | 1 | 0 | X 1 |
| stress_v1 | Hermans_2024 | 37 | 37 | 15 | 37 | 22 | 0 | 0 |  |
| stress_v1 | Silchenko_2023 | 8 | 8 | 2 | 2 | 6 | 6 | 0 | F 6 |
| stress_v1 | Sims_2021 | 39 | 33 | 30 | 34 | 4 | 0 | 1 |  |
| heldout_sf_v1 | (held out, 3 papers, totals) | 56 | 40 | 35 | 39 | 5 | 1 | 0 | X 1 |
- One quote resolved in v2 and failed on the first 5b build: binder_1999's smoothing label quote,
  which needs both a citation and tier 6's ligature repair. Tiers 3 to 6 now read GROBID text with the
  delimiters dropped, as before 5b; it resolves again, and a test holds the case.
- Matching rule, as built: what a quote holds at a citation must be drawn from that citation (each
  run of digits within its digits, each run of letters within its letters), bounded by twice the
  citation's length plus 20 characters; separator-only text between two citations is one gap.
- Known GROBID limits, accepted (rulings 3): the multiplication sign (7 quotes) and Silchenko's
  paragraph filed as a `<figure>` (6 quotes).

Checks: suite 819 passed (835 with the motion scorer); render identity gate 49/49 identical vs
`ac6f998`, positive control 12/12 changed; 17 mutations on the matcher, flattener and hop, 16 killed,
1 equivalent (tier 5b's re-verification on the slice: disabling it changes none of the 69 per-paper
gate rows nor any test). pypdf's found count is 690 before and after, so pypdf resolution is
unchanged.

## 2. The corpus run

19 papers through `aespa-report --text-source grobid`. Every paper read GROBID text
(`grobid-0.9.1-crf`); no pypdf fallback; every hop read the reference list from pypdf text.

| paper | status | calls | cost (USD) | wall (s) | text source | fallback |
|---|---|---|---|---|---|---|
| agtzidis_2020 | success | 8 | 0.481 | 125.3 | grobid-0.9.1-crf | no |
| binder_1999 | success | 7 | 0.46 | 116.4 | grobid-0.9.1-crf | no |
| braun_2015 | success | 7 | 0.4171 | 112.4 | grobid-0.9.1-crf | no |
| chen_2015 | success | 8 | 0.6054 | 192.2 | grobid-0.9.1-crf | no |
| ciric_2017 | success | 16 | 0.834 | 296.6 | grobid-0.9.1-crf | no |
| cole_2013 | success | 12 | 0.7172 | 197.8 | grobid-0.9.1-crf | no |
| derosa_2025 | success | 15 | 0.8976 | 230.1 | grobid-0.9.1-crf | no |
| gordon_2014 | success | 8 | 0.5218 | 143.2 | grobid-0.9.1-crf | no |
| liu_2005 (held out) | methods_not_found | 7 | 0.3649 | 98.7 | grobid-0.9.1-crf | no |
| liu_2013 | success | 11 | 0.6413 | 204.5 | grobid-0.9.1-crf | no |
| mueller_2021 | success | 9 | 0.5058 | 142.8 | grobid-0.9.1-crf | no |
| oconnor_2017 | success | 13 | 0.7103 | 210.7 | grobid-0.9.1-crf | no |
| poldrack_2015 | success | 14 | 0.7886 | 208.2 | grobid-0.9.1-crf | no |
| power_2014 | success | 8 | 0.6064 | 188.0 | grobid-0.9.1-crf | no |
| tang_2025 (held out) | success | 9 | 0.5372 | 162.6 | grobid-0.9.1-crf | no |
| vanderwal_2016 | success | 8 | 0.5307 | 143.3 | grobid-0.9.1-crf | no |
| viduarre_2017 | success | 8 | 0.4565 | 134.2 | grobid-0.9.1-crf | no |
| weber_2024 | success | 9 | 0.5848 | 182.9 | grobid-0.9.1-crf | no |
| wheaton_2004 (held out) | success | 9 | 0.4813 | 137.6 | grobid-0.9.1-crf | no |
| **total** | | 186 | 11.1419 | 3,227.5 | | 0 |

Retries 3 and parse errors 3 (ciric_2017, cole_2013, derosa_2025, one each), all inside the metered
totals above.

**Unmetered attempts.** The machine slept from 16:12 on 2026-11-06. liu_2013 and mueller_2021 each
hung on an open connection to AWS; a first launch was stopped within a minute of starting
agtzidis_2020; and 20 watchdog-limited attempts on the last ten papers were killed while the machine
slept. None wrote a record. Each may have sent a model call before hanging; their cost is not in the
total above and is visible only in Bedrock's billing. The ten papers were then re-run awake, each on
its first attempt.

## 3. Side by side: pypdf vintage vs corpus_grobid_v1

- **pypdf vintage:** `results/batch_coverage_v4` (16 papers, batch path, code `a3908c3`) and
  `results/heldout_sf_v1` (liu_2005, tang_2025, wheaton_2004; aespa-report, code `35e4081`), the
  records scored before.
- **GROBID:** `results/corpus_grobid_v1` (aespa-report, code `4c3b4b4`).
- **The two arms differ in code as well as text source,** and each is one draw per paper.
- Columns: unverifiable = D.3 rows whose report state is `unverifiable` (`cobidas.row_state`);
  quote unresolved = the record's `n_missing_quote_unresolved` + `n_deferral_quote_unresolved`;
  `quote_not_found` = the record's diagnostics with that failure. Smoothing and filtering states from
  `score_smoothing_filtering.py`, one entry per label row ("not separable": a multi-stream paper, no
  `applies_to` yet); motion from `score_motion.py`, the record state with agree or disagree.
- Held-out papers: states and counts only.

| paper | status (pypdf / GROBID) | unverifiable D.3 rows | fields left missing, quote unresolved | `quote_not_found` diagnostics | smoothing state | filtering state | motion method state |
|---|---|---|---|---|---|---|---|
| agtzidis_2020 | success / success | 0 / 3 | 0 / 4 | 0 / 6 | agree / agree | agree / agree | label named_tool; described_only (disagree) / unverifiable (disagree) |
| binder_1999 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | disagree / disagree | agree / agree | label described_only; described_only (agree) / undecided (disagree) |
| braun_2015 | success / success | 0 / 1 | 0 / 0 | 0 / 0 | agree / disagree | disagree / disagree | label deferred; deferred (agree) / deferred (agree) |
| chen_2015 | success / success | 0 / 0 | 0 / 0 | 1 / 0 | not separable, not separable / not separable, not separable | not separable, not separable / not separable, not separable | label deferred; described_only (disagree) / described_only (disagree) |
| ciric_2017 | success / success | 1 / 0 | 2 / 1 | 2 / 1 | not separable, not separable / not separable, not separable | disagree / disagree | label named_tool; named_tool (agree) / named_tool (agree) |
| cole_2013 | success / success | 0 / 0 | 0 / 0 | 1 / 0 | agree / agree | disagree / disagree | label named_tool; described_only (disagree) / described_only (disagree) |
| derosa_2025 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label named_tool; named_tool (agree) / named_tool (agree) |
| gordon_2014 | success / success | 0 / 0 | 5 / 0 | 6 / 0 | agree / agree | disagree / agree | label named_tool; named_tool (agree) / named_tool (agree) |
| liu_2005 (held out) | methods_not_found / methods_not_found | 7 / 0 | 11 / 0 | 15 / 0 | agree / disagree | disagree / disagree | label named_tool; unverifiable (disagree) / absent (disagree) |
| liu_2013 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label deferred; described_only (disagree) / described_only (disagree) |
| mueller_2021 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label named_tool; described_only (disagree) / described_only (disagree) |
| oconnor_2017 | success / success | 1 / 1 | 0 / 1 | 0 / 1 | agree / agree | agree / agree | label deferred; described_only (disagree) / described_only (disagree) |
| poldrack_2015 | success / success | 2 / 0 | 4 / 3 | 7 / 3 | agree / agree | agree / agree | label deferred; deferred (agree) / described_only (disagree) |
| power_2014 | success / success | 2 / 1 | 5 / 3 | 5 / 3 | agree / agree | not separable, not separable / not separable, not separable | label described_only; described_only (agree) / described_only (agree) |
| tang_2025 (held out) | success / success | 0 / 0 | 1 / 2 | 0 / 1 | not separable, not separable / not separable, not separable | not separable, not separable / not separable, not separable | label named_tool; described_only (disagree) / described_only (disagree) |
| vanderwal_2016 | success / success | 1 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label deferred; deferred (agree) / described_only (disagree) |
| viduarre_2017 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | disagree / disagree | disagree / disagree | label deferred; deferred (agree) / deferred (agree) |
| weber_2024 | success / success | 1 / 1 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label deferred; described_only (disagree) / deferred (agree) |
| wheaton_2004 (held out) | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label named_tool; named_tool (agree) / named_tool (agree) |

### Totals

| | pypdf vintage | GROBID |
|---|---|---|
| unverifiable D.3 rows | 15 | 7 |
| fields left missing, quote unresolved | 28 | 14 |
| `quote_not_found` diagnostics | 37 | 15 |
| smoothing rows: agree / disagree / not separable | 14 / 2 / 6 | 12 / 4 / 6 |
| filtering rows: agree / disagree / not separable | 10 / 6 / 6 | 11 / 5 / 6 |
| motion method: agree / disagree | 10 / 9 | 8 / 11 |
| state agreements, all three scorers | 34 | 31 |

### Every record state that differs between the arms (scored rows)

| paper | row | label | pypdf record | GROBID record |
|---|---|---|---|---|
| agtzidis_2020 | motion method | named_tool | described_only | unverifiable |
| binder_1999 | motion method | described_only | described_only | undecided |
| braun_2015 | smoothing | deferred | deferred | not_reported |
| gordon_2014 | filtering | reported | unverifiable | reported |
| liu_2005 (held out) | smoothing | stated_not_performed | stated_not_performed | not_reported |
| liu_2005 (held out) | filtering | reported | unverifiable | not_reported |
| liu_2005 (held out) | motion method | named_tool | unverifiable | absent |
| poldrack_2015 | motion method | deferred | deferred | described_only |
| vanderwal_2016 | motion method | deferred | deferred | described_only |
| weber_2024 | motion method | deferred | described_only | deferred |

Agreement changes: gordon_2014 filtering and weber_2024 motion move to agree; braun_2015 smoothing,
liu_2005 smoothing, binder_1999 motion, poldrack_2015 motion and vanderwal_2016 motion move to
disagree. agtzidis_2020 motion and liu_2005 filtering and motion change state and disagree in both.

## 4. Cost

Corpus run, metered: **$11.1419** (186 calls, 19 papers). Unmetered: the interrupted attempts in §2.
