# Text source A/B, same code (2026-11-08)

Arms: `results/corpus_pypdf_v1` (aespa-report `--text-source pypdf`, worktree pinned at `cdca5c9`)
and `results/corpus_grobid_v1` (aespa-report `--text-source grobid`, worktree pinned at `4c3b4b4`,
the run of `grobid_rerun_v1.md`). Between those commits the source tree differs only in which text
source is the default (`cdca5c9`); both runs name their source explicitly, so the extraction path is
the same. fmri-defaults-kb unchanged since `93199df` (2026-11-05). GROBID:
`lfoppiano/grobid:0.9.1-crf`. Model: `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`. One
draw per paper per arm. Held-out papers (liu_2005, tang_2025, wheaton_2004): states and counts only.
Numbers only.

## 1. The control run

19 papers, metered, under `caffeinate -i`, a 15-minute wall-clock watchdog and at most two attempts
per paper. 19 of 19 wrote a record on the first attempt; the watchdog killed nothing. Every record
says `text_source: pypdf`, no fallback, hop reference list from pypdf. liu_2005 is
`methods_not_found`, as on GROBID.

## 2. Side by side

Columns as in `grobid_rerun_v1.md` section 3: unverifiable = D.3 rows whose report state is
`unverifiable` (`cobidas.row_state`); quote unresolved = `n_missing_quote_unresolved` +
`n_deferral_quote_unresolved`; `quote_not_found` = diagnostics with that failure. Smoothing and
filtering from `score_smoothing_filtering.py` ("not separable": a multi-stream paper, no
`applies_to` yet); motion from `score_motion.py`. Cells read pypdf / GROBID.

| paper | status (pypdf / GROBID) | unverifiable D.3 rows | fields left missing, quote unresolved | `quote_not_found` diagnostics | smoothing state | filtering state | motion method state |
|---|---|---|---|---|---|---|---|
| agtzidis_2020 | success / success | 0 / 3 | 0 / 4 | 0 / 6 | agree / agree | agree / agree | label named_tool; unverifiable (disagree) / unverifiable (disagree) |
| binder_1999 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | disagree / disagree | agree / agree | label described_only; undecided (disagree) / undecided (disagree) |
| braun_2015 | success / success | 0 / 1 | 0 / 0 | 0 / 0 | agree / disagree | disagree / disagree | label deferred; deferred (agree) / deferred (agree) |
| chen_2015 | success / success | 0 / 0 | 0 / 0 | 1 / 0 | not separable, not separable / not separable, not separable | not separable, not separable / not separable, not separable | label deferred; described_only (disagree) / described_only (disagree) |
| ciric_2017 | success / success | 0 / 0 | 1 / 1 | 1 / 1 | not separable, not separable / not separable, not separable | disagree / disagree | label named_tool; named_tool (agree) / named_tool (agree) |
| cole_2013 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | disagree / disagree | label named_tool; named_tool (agree) / described_only (disagree) |
| derosa_2025 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label named_tool; named_tool (agree) / named_tool (agree) |
| gordon_2014 | success / success | 0 / 0 | 6 / 0 | 7 / 0 | agree / agree | disagree / agree | label named_tool; described_only (disagree) / named_tool (agree) |
| liu_2005 (held out) | methods_not_found / methods_not_found | 7 / 0 | 11 / 0 | 15 / 0 | agree / disagree | disagree / disagree | label named_tool; unverifiable (disagree) / absent (disagree) |
| liu_2013 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label deferred; described_only (disagree) / described_only (disagree) |
| mueller_2021 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | disagree / agree | label named_tool; described_only (disagree) / described_only (disagree) |
| oconnor_2017 | success / success | 0 / 1 | 0 / 1 | 0 / 1 | agree / agree | agree / agree | label deferred; described_only (disagree) / described_only (disagree) |
| poldrack_2015 | success / success | 3 / 0 | 13 / 3 | 16 / 3 | disagree / agree | agree / agree | label deferred; described_only (disagree) / described_only (disagree) |
| power_2014 | success / success | 3 / 1 | 8 / 3 | 9 / 3 | disagree / agree | not separable, not separable / not separable, not separable | label described_only; described_only (agree) / described_only (agree) |
| tang_2025 (held out) | success / success | 0 / 0 | 1 / 2 | 0 / 1 | not separable, not separable / not separable, not separable | not separable, not separable / not separable, not separable | label named_tool; described_only (disagree) / described_only (disagree) |
| vanderwal_2016 | success / success | 1 / 0 | 1 / 0 | 1 / 0 | agree / agree | agree / agree | label deferred; deferred (agree) / described_only (disagree) |
| viduarre_2017 | success / success | 0 / 0 | 0 / 0 | 0 / 0 | disagree / disagree | disagree / disagree | label deferred; deferred (agree) / deferred (agree) |
| weber_2024 | success / success | 1 / 1 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label deferred; described_only (disagree) / deferred (agree) |
| wheaton_2004 (held out) | success / success | 0 / 0 | 0 / 0 | 0 / 0 | agree / agree | agree / agree | label named_tool; named_tool (agree) / named_tool (agree) |

### Totals

| | pypdf (corpus_pypdf_v1) | GROBID (corpus_grobid_v1) |
|---|---|---|
| unverifiable D.3 rows | 15 | 7 |
| fields left missing, quote unresolved | 41 | 14 |
| `quote_not_found` diagnostics | 50 | 15 |
| smoothing rows: agree / disagree / not separable | 12 / 4 / 6 | 12 / 4 / 6 |
| filtering rows: agree / disagree / not separable | 9 / 7 / 6 | 11 / 5 / 6 |
| motion method: agree / disagree | 8 / 11 | 8 / 11 |
| state agreements, all three scorers | 29 | 31 |

The GROBID column reproduces the totals of `grobid_rerun_v1.md`. Both columns' smoothing, filtering
and motion counts equal the scorers' own CLI output on each directory (smoothing 12/4/6 and 12/4/6,
filtering 9/7/6 and 11/5/6, motion 8/11 and 8/11).

## 3. Every record state that differs between the two runs

12 scored rows differ. For each, every evidence quote the record carries for that step (the span
text of extracted and deferred fields, the raw quote of each unresolved-quote diagnostic; motion:
the `method` field only) is resolved with the current `resolve_quote` against the text its own run
read and against the other run's text (paper plus supplement when one was read, reflowed). "Present
in both" is yes when every quote that resolves in its own text also resolves in the other, and at
least one does.

| paper | row | label | pypdf record | GROBID record | pypdf evidence: n, resolves on pypdf, on GROBID | GROBID evidence: n, resolves on GROBID, on pypdf | evidence present in both texts |
|---|---|---|---|---|---|---|---|
| braun_2015 | smoothing | deferred | deferred (agree) | not_reported (disagree) | 6, 6, 6 | 0, 0, 0 | yes |
| cole_2013 | motion method | named_tool | named_tool (agree) | described_only (disagree) | 1, 1, 1 | 1, 1, 0 | no |
| gordon_2014 | filtering | reported | unverifiable (disagree) | reported (agree) | 4, 0, 4 | 3, 3, 0 | no |
| gordon_2014 | motion method | named_tool | described_only (disagree) | named_tool (agree) | 1, 1, 1 | 1, 1, 1 | yes |
| liu_2005 (held out) | filtering | reported | unverifiable (disagree) | not_reported (disagree) | 2, 0, 0 | 0, 0, 0 | no (no evidence quote resolves in either text) |
| liu_2005 (held out) | motion method | named_tool | unverifiable (disagree) | absent (disagree) | 1, 0, 0 | 0, 0, 0 | no (no evidence quote resolves in either text) |
| liu_2005 (held out) | smoothing | stated_not_performed | stated_not_performed (agree) | not_reported (disagree) | 1, 1, 0 | 0, 0, 0 | no |
| mueller_2021 | filtering | reported | not_reported (disagree) | reported (agree) | 0, 0, 0 | 6, 6, 6 | yes |
| poldrack_2015 | smoothing | reported | unverifiable (disagree) | reported (agree) | 5, 0, 0 | 5, 5, 5 | yes |
| power_2014 | smoothing | reported | unverifiable (disagree) | reported (agree) | 3, 0, 0 | 3, 3, 3 | yes |
| vanderwal_2016 | motion method | deferred | deferred (agree) | described_only (disagree) | 1, 1, 1 | 1, 1, 1 | yes |
| weber_2024 | motion method | deferred | described_only (disagree) | deferred (agree) | 1, 1, 1 | 1, 1, 1 | yes |

Present in both: yes for 7 rows (braun smoothing, gordon motion, mueller filtering, poldrack
smoothing, power smoothing, vanderwal motion, weber motion); no for 5 (cole motion, gordon filtering,
liu_2005 smoothing, filtering and motion). cole's GROBID quote does not resolve on pypdf text.
gordon's filtering quotes resolve only in the other run's text, in both directions. liu_2005's
smoothing quote resolves on pypdf only; its filtering and motion quotes resolve in neither text.

### liu_2005

- Fields whose evidence lost text in GROBID (resolves on pypdf, not on GROBID):
  `spatial_smoothing.performed`. No other.
- The pypdf record carries 12 evidence quotes: 1 resolves on pypdf (the field above), 11 resolve in
  neither text. The GROBID record carries none (`n_extracted` 0, `n_missing_quote_unresolved` 0,
  `n_missing_not_stated` 79; pypdf: 1, 11, 62).
- Both runs slice by `fallback_full_text`. GROBID's flattened text for liu_2005 is 3,196 characters
  in 5 lines; pypdf's is 50,672 in 507. No other paper's GROBID text is under 27,507 characters
  (GROBID text leaves out the reference list, figures and tables, so it is shorter on every paper):

| paper | pypdf characters | GROBID characters |
|---|---|---|
| agtzidis_2020 | 67,182 | 41,528 |
| binder_1999 | 74,302 | 52,282 |
| braun_2015 | 48,544 | 34,380 |
| chen_2015 | 76,730 | 41,568 |
| ciric_2017 | 92,879 | 65,384 |
| cole_2013 | 79,191 | 60,593 |
| derosa_2025 | 106,474 | 73,846 |
| gordon_2014 | 60,149 | 41,574 |
| liu_2005 (held out) | 50,672 | 3,196 |
| liu_2013 | 53,779 | 38,581 |
| mueller_2021 | 75,573 | 46,230 |
| oconnor_2017 | 53,191 | 30,348 |
| poldrack_2015 | 105,128 | 78,982 |
| power_2014 | 126,842 | 98,330 |
| tang_2025 (held out) | 53,942 | 27,507 |
| vanderwal_2016 | 67,060 | 41,294 |
| viduarre_2017 | 47,113 | 36,534 |
| weber_2024 | 76,293 | 40,724 |
| wheaton_2004 (held out) | 57,240 | 38,284 |

## 4. Cost

| paper | pypdf: calls, cost, wall | GROBID: calls, cost, wall |
|---|---|---|
| agtzidis_2020 | 9, $0.5070, 121.6 s | 8, $0.4810, 125.3 s |
| binder_1999 | 7, $0.5135, 135.3 s | 7, $0.4600, 116.4 s |
| braun_2015 | 7, $0.5546, 145.0 s | 7, $0.4171, 112.4 s |
| chen_2015 | 8, $0.5808, 173.8 s | 8, $0.6054, 192.2 s |
| ciric_2017 | 16, $0.7476, 250.1 s | 16, $0.8340, 296.6 s |
| cole_2013 | 11, $0.5457, 138.6 s | 12, $0.7172, 197.8 s |
| derosa_2025 | 15, $0.9612, 219.0 s | 15, $0.8976, 230.1 s |
| gordon_2014 | 8, $0.6932, 195.3 s | 8, $0.5218, 143.2 s |
| liu_2005 (held out) | 8, $0.7261, 140.8 s | 7, $0.3649, 98.7 s |
| liu_2013 | 11, $0.5692, 165.9 s | 11, $0.6413, 204.5 s |
| mueller_2021 | 9, $0.5557, 152.7 s | 9, $0.5058, 142.8 s |
| oconnor_2017 | 13, $0.6695, 162.1 s | 13, $0.7103, 210.7 s |
| poldrack_2015 | 19, $1.1092, 275.4 s | 14, $0.7886, 208.2 s |
| power_2014 | 8, $0.6158, 189.9 s | 8, $0.6064, 188.0 s |
| tang_2025 (held out) | 9, $0.5300, 142.7 s | 9, $0.5372, 162.6 s |
| vanderwal_2016 | 9, $0.6122, 167.0 s | 8, $0.5307, 143.3 s |
| viduarre_2017 | 8, $0.5333, 145.3 s | 8, $0.4565, 134.2 s |
| weber_2024 | 9, $0.6105, 181.0 s | 9, $0.5848, 182.9 s |
| wheaton_2004 (held out) | 9, $0.4947, 130.7 s | 9, $0.4813, 137.6 s |
| **total** | 193, $12.1298, 3232.2 s | 186, $11.1419, 3227.5 s |

- pypdf control: **$12.1298** metered, 193 calls, 3,232.2 s.
- GROBID (`grobid_rerun_v1.md`): **$11.1419** metered, 186 calls, 3,227.5 s; the attempts
  interrupted while the machine slept on 2026-11-06 are not in this figure.
