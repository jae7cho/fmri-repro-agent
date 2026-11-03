# The citation hop, case one: gracia-tabuenca_2024 -> Hagler et al. (2019) (2026-11-03)

The values read in Hagler et al. (2019) were withheld until the author recorded the key (the author's
instruction, 2026-11-03). The key was recorded the same day (`docs/findings/keys/hop1_case_key.txt`,
copied from the author's file with one change, a final newline added by the end-of-file hook;
co-adjudicated: the assistant located sentences and drafted values, and the author checked each line
against its sentence, before seeing the hop's output). The comparison is below the first run.

## The build

`citation_hop.py` and its script, per `docs/design/DESIGN_citation_hop.md` ("As built for case
one"). Tests: 613 extractor (not live), 235 root; hooks clean. Mutations, each with a non-empty
diff shown before the run:

| mutation | result |
|---|---|
| an ambiguous reference picks one entry | killed |
| the scope asks rows the citing paper reports | killed |
| a variant's quote is never checked | killed |
| a variant outside the scope is kept | **survived** first: the test's out-of-scope variant named no real field, so the check was never reached. The test now uses `spatial_smoothing.fwhm_mm`; killed |
| two matching local PDFs pick one | killed |
| fork E's filter removed | killed |
| the second-hop section not rendered | killed |
| a generational-suffix strip removed | **survived**: the first-word key already covers it, so the strip was removed as redundant |
| the first-word key replaced by the last word | killed |

Identity gate, derived first (no stored record carries a hop, and fork E changes extraction only,
so nothing changes): a1 19 identical, v2 19, v3 18, v4 18, against HEAD; negative control against
`d31e8b7`: 0 of 19 identical.

## The run

`results/hop_case1/` (gitignored): `gracia-tabuenca_2024.second_hop.json` and the report re-rendered
with the second-hop section. Model as coverage_v4.

- **First run (09:35 ET): `reference_not_found`, 0 model calls.** The first author parsed as
  "Hagler Jr" and the matcher compared the last word. Fixed as above.
- **Second run (09:36–09:38 ET):** reference entry resolved; target a local PDF
  (`tested_lit/sfn_batch/Hagler_2019.pdf`), with the entry's DOI found on the PDF; the cited
  methods slice found by its heading. The checking pass returned ok.

**Fields asked: 23**, plus the software list (fork A: the base pipeline is deferred to Hagler). One
because it is deferred to Hagler: `distortion_correction.method`. The rest because the citing paper
does not report the row: brain extraction (4 fields), slice-time correction (6), coregistration (6),
spatial smoothing (6). No asked row fell outside calls T and S.

| call | wall (s) | input tokens | output tokens | cost (USD, LiteLLM price table) |
|---|---|---|---|---|
| T | 10.7 | 19,931 | 971 | 0.0818 |
| S | 26.2 | 19,195 | 2,187 | 0.0994 |
| checking pass, first attempt | 43.9 | 17,957 | 3,591 | 0.1185 |
| checking pass, retry | 25.1 | 25,877 | 3,372 | 0.1410 |
| **all** | **107.3** (hop) | **82,960** | **10,121** | **0.4408** |

The checking pass took two model calls inside one `create()`. instructor makes a second call
(`max_retries=2`) when a response fails validation; the failed response itself was not recorded, so
the cause is inferred from the call count. Both calls are billed and both are counted.

## The key against the first draw (09:36 ET)

The hop's value is the field's extraction as the report renders it; the checking pass's verdict is
listed beside it and does not change the value. Agree means the same value or the same state.

| field | key | hop | |
|---|---|---|---|
| distortion_correction.method | reversing phase-encode polarity, then gradient-nonlinearity correction | not reported (the drafted value failed its quote check, `value_unsupported_by_quote`); checking pass: missed, its sentence not found | key-only |
| brain_extraction.performed, .method, .parameters, .manual_edits | not stated for fMRI | not reported; checking pass: missed on performed and method, from the sMRI FreeSurfer sentence | agree (4) |
| slice_time_correction (6 fields) | not stated | not reported | agree (6) |
| coregistration.performed | yes | not reported (quote not found) | key-only |
| coregistration.method | not stated (in-house) | not reported | agree |
| coregistration.transform | rigid, from the fMRI sentence | rigid, quoting the **dMRI** sentence; checking pass: wrong, for that reason | agree on the value |
| coregistration.nonlinear_transform_type | not applicable (rigid) | not reported | differ (state) |
| coregistration.cost_function | mutual information | not reported (quote not found) | key-only |
| coregistration.interpolation | not stated | not reported | agree |
| spatial_smoothing (6 fields) | not stated for fMRI | not reported | agree (6) |

**Fields, 23: agree 19, differ 1, hop-only 0, key-only 3.** One of the 19 (the transform) agrees on
the value but cites the dMRI section's sentence, not the fMRI one the key cites.

| software (fMRI preprocessing) | key | hop | |
|---|---|---|---|
| AFNI (3dvolreg) | no version | AFNI, no version | agree |
| FreeSurfer | 5.3 | 5.3 | agree |
| FreeSurfer mri_vol2surf | listed separately (FreeSurfer 5.3) | not listed | key-only |
| Multi-Modal Processing Stream (MMPS) | not listed | no version | hop-only |
| AtlasTrack | out of scope (dMRI) | no version; checking pass: not preprocessing | hop-only |

**Software, 5 entries across both: agree 2, differ 0, hop-only 2, key-only 1.**

The key's "Stated by Hagler, no field above" lines (motion, surface sampling, initial frames,
regression, notch filter, band-pass, censoring) are not fields the hop asks. The checking pass's
unplaced list names 7 such statements. One of them is "A total of 16 initial frames (12.8 s) are
discarded.", which resolves in Hagler's methods text. The key says the count is in footnote 4 and is
to be checked there.

The key's data-release lines had no hop field in the first draw. They are compared under the re-run.

**Why the three key-only fields were missed.** The second build keeps each call's raw reply. In the
re-run, call S quoted Hagler's dMRI sentence for coregistration.performed and .cost_function, a
paraphrase not found in the text. For distortion_correction.method it quoted the sMRI sentence
(gradient nonlinearity, `gradunwarp`), whose value its quote does not support. The quote checks
rejected all three, as designed. The cause is the model reading the dMRI and sMRI sections under the
BOLD-only scope paragraph of the pinned prompts. The first draw's raw replies were not kept, but its
three fields failed with the same reasons.

## Second build and re-run (2026-11-03, afternoon)

The author's requests of that day: fork A widened, the checking-pass retry fixed, and the data-release
field. `DESIGN_citation_hop.md` "As built, second round" has the build. Tests: 623 extractor (not
live), 235 root; hooks clean.

| mutation | result |
|---|---|
| M1 a resolved `other` counts as a tool | killed |
| M2 the scope asks a row whose method names a tool | **survived** first: the test's "N4" value was not in its quote, so the method was dropped as missing before the scope saw it. The fixture now quotes a sentence with N4, and asserts the method is EXTRACTED; killed |
| M3 a tool for a step not asked is kept | killed |
| M4 a tool never checked against its quote | killed |
| M5 a release equal to the latest described counts as later | **survived** first: no equal case was tested; added; killed |
| M6 no acronym match for dataset names | killed |
| M7 the "may differ" note never rendered | killed |
| M8 the parse-error hook not registered | killed |
| M9 a citing release shown without its check | **survived** first: no unchecked release was rendered in a test; added; killed |
| M10 a citing release with an unresolved quote compared | killed |
| M11 the cited text sent with its double quotes | killed |
| M12 only straight double quotes replaced | killed |
| M13 no possessive tolerance in the value-in-quote check | killed |
| M14 a tool that fails its check rendered as "no tool named" | killed |

Identity gate, derived first (no stored record carries a hop or a data release, both render
arguments default to None, fork E changes extraction only): a1 19 identical, v2 19, v3 18, v4 18,
against HEAD `44df086`; negative control against `d31e8b7`: 0 of 19 identical. As derived.

### Three draws of case one

| draw (ET) | out dir | calls | retry | wall (s) | in tok | out tok | cost (USD) |
|---|---|---|---|---|---|---|---|
| 12:17 | `hop_case1_v2` | T, S, checking pass x2, R | yes: invalid JSON at line 107 col 152, `finish_reason` stop | 135.1 | 91,310 | 11,750 | 0.4952 |
| 12:20 | `hop_case1_v3` | T, S, checking pass x2, R | yes: the same position | 144.4 | 90,979 | 13,456 | 0.5223 |
| 12:23 | `hop_case1_v4` (of record) | T, S, checking pass, R | no | 110.9 | 62,521 | 9,064 | 0.3559 |

**The retry's cause.** The checking pass copied Hagler's sentence on signal “drop-out” into
a JSON string with the curly quotes turned straight and unescaped. The first fix replaced straight
double quotes in the cited text; Hagler's methods have none (22 opening and 22 closing curly ones),
and the second draw failed at the same place. The second fix replaces every double quotation mark,
straight or curly, with an apostrophe, one character for one so offsets hold (`json_safe`, 44
replaced). The third draw made one checking-pass call. That is one draw; whether the fix holds on
other papers is not shown.

**Re-run values.** The 23 fields' values and quotes are identical to the first draw's, so the counts
above stand. The motion tool first failed its value-in-quote check ("AFNI 3dvolreg" against "AFNI's
3dvolreg") and rendered as "no tool named" beside a checking-pass "supported". The check now sets a
possessive aside (M13), and a tool that fails its check renders as unverified, never as "no tool
named" (M14). `hop_case1_v4_replay` re-applies the checks to the stored record with no model call;
only the motion tool's check changes, and the report outside the hop section is byte-identical.

| asked (re-run) | key | hop (replayed) | |
|---|---|---|---|
| motion_correction tool (this paper: "corrected for motion") | AFNI 3dvolreg (software table) | AFNI 3dvolreg; checking pass: supported | agree |
| intensity_correction tool (this paper: "B1-bias field estimation") | bias tools in-house and unnamed | "sparse spatial smoothing and white matter segmentation"; checking pass: wrong | differ |
| releases Hagler describes | ABCD Data Releases 1.0 to 2.0.1 | ABCD Data Release 2.0; ABCD Fix Release 2.0.1 | differ (the hop lacks 1.0) |
| this paper's releases (first hop) | ABCD 3.0 (NDA); ABCD-BIDS Community Collection 3165 | the same two, quotes checked | agree (2) |
| relation | 3.0 postdates 2.0.1; the FC matrices likely from another pipeline, to verify | 3.0: postdates, the "may differ" note rendered; collection 3165: undetermined | agree |

The intensity correction row is the citing paper's sMRI bias correction; the key puts structural
preprocessing out of scope.

## Third round: calls read Hagler's fMRI preprocessing section (2026-11-03, later afternoon)

The author's rulings of that day: scope the calls to the cited paper's fMRI preprocessing section,
two deterministic rules, fork G decided. `DESIGN_citation_hop.md` "As built, third round".

**Draw 13:06 ET** (`hop_case1_v5`, of record): section "2.7.1. fMRI preprocessing", characters 49973
to 51537 of the PDF's text (1,564 characters), ended at "2.7.2. Task-fMRI behavioral measures".
Calls T, S, checking pass, RD, R: one attempt each, no retry; 66.2 s; 35,460 tokens in, 6,396 out;
$0.2226, against $0.3559 for the second build's draw on the whole methods slice.

### The key against this draw (the same table)

| field | key | hop | |
|---|---|---|---|
| distortion_correction.method | reversing phase-encode polarity, then gradient-nonlinearity correction | not reported (`value_unsupported_by_quote`); checking pass: missed, its sentence resolved | key-only |
| brain_extraction (4 fields) | not stated for fMRI | not reported; checking pass: supported on all four | agree (4) |
| slice_time_correction (6 fields) | not stated | not reported | agree (6) |
| coregistration.performed | yes | yes, quoting the fMRI sentence | agree |
| coregistration.method | not stated (in-house) | not reported; checking pass: missed, proposing "mutual information" | agree |
| coregistration.transform | rigid, the fMRI sentence | rigid, the fMRI sentence | agree |
| coregistration.nonlinear_transform_type | not applicable (rigid) | not applicable, by rule `rigid_no_nonlinear` | agree |
| coregistration.cost_function | mutual information | mutual information | agree |
| coregistration.interpolation | not stated | not reported | agree |
| spatial_smoothing (6 fields) | not stated for fMRI | not reported | agree (6) |

**Fields, 23: agree 22, differ 0, hop-only 0, key-only 1** (first draw: 19, 1, 0, 3). The checking
pass's "missed" on coregistration.method proposes the cost function as the method; the key keeps
the method not stated.

| software (fMRI preprocessing) | key | hop | |
|---|---|---|---|
| AFNI 3dvolreg | no version | "AFNI's 3dvolreg", no version | agree |
| FreeSurfer | 5.3 | not listed: its version sentence is at character 33080, in §2.5.2, outside the section | key-only |
| FreeSurfer mri_vol2surf | (FreeSurfer 5.3) | not listed: at character 54998, outside the section | key-only |

**Software, 3 entries across both: agree 1, differ 0, hop-only 0, key-only 2** (first draw: 5
entries; agree 2, hop-only 2, key-only 1). MMPS and AtlasTrack no longer appear.

| asked | key | hop | |
|---|---|---|---|
| motion_correction tool | AFNI 3dvolreg | AFNI's 3dvolreg; checking pass: supported | agree |
| intensity_correction tool | in-house, unnamed | no tool named in Hagler | agree |
| releases Hagler describes | 1.0 to 2.0.1 | 2.0; 2.0.1; 1.0–2.0.1 (a range); 1.1 | agree (the range, with three releases inside it) |
| this paper's releases | ABCD 3.0; collection 3165 | the same two | agree (2) |
| relation | 3.0 postdates; 3165 to verify | 3.0 postdates (note rendered); 3165 undetermined | agree |

**What the slice traded.** Every field the key cites sits in §2.7.1, and the three fields the
whole-methods draws missed now read the fMRI sentences. The Software row lost FreeSurfer 5.3 and
mri_vol2surf, which Hagler names outside §2.7.1 (§2.5.2 and the fMRI analysis sections); the key
counts both as fMRI preprocessing software.

### MMPS (item 4)

The first draw's quote for MMPS opens "We used a collection of processing steps contained within the
Multi-Modal Processing Stream (MMPS)" and runs one sentence (the whole quote is in the stored
record, `results/hop_case1/gracia-tabuenca_2024.second_hop.json`). It resolves in the methods slice at characters 15958
to 16362 of the PDF's text, under "2.1. Overview". It does not resolve inside the fMRI section
(`quote_not_found`), and the section does not name MMPS.

### Build checks

Tests: 633 extractor (not live), 235 root; hooks clean. Mutations, each diffed against the
pre-mutation file before its run. The first run of N1 to N11 had a red baseline (one new test
failing), so every "killed" in it meant nothing; the failing test had found a slicer bug (each
heading pattern took only its first match, so a numbered sentence ending in a period hid the
heading after it). After the fix the baseline was green (27 passed) and all were re-run:

| mutation | result |
|---|---|
| N1 no fMRI heading ever found | killed |
| N2 numbered headings do not end the section | killed |
| N3 a numbered sentence ends the section | killed |
| N4 calls T and S read the methods slice | killed |
| N5 call RD reads the fMRI section | killed |
| N6 the rule fires for any transform | killed |
| N7 the rule overrides an extracted nonlinear type | killed |
| N8 a range keeps only its low end | killed |
| N9 a citing release compared with a range's low end | killed |
| N10 the rule not rendered | killed |
| N11 tool-calling mode maps to JSON | killed |
| N12 only the first match per heading pattern (the bug fixed) | killed |
| N13 a tool-calling reply's arguments not kept | killed |

Identity gate, derived first (the render changes sit inside the second-hop section; no stored
record has one): a1 19 identical, v2 19, v3 18, v4 18, against HEAD `069fe61`; negative control
against `d31e8b7`: 0 of 19 identical. As derived.

## Fourth round: every fMRI section, the software list from the whole paper (2026-11-03)

The author's correction: the third round cut the slice one section too narrow. Field calls read every
section whose heading names fMRI (dMRI and sMRI excluded); the software list reads the whole cited
paper and keeps a tool only when its quoted use is fMRI processing or feeds it. The key stays at
`docs/findings/keys/hop1_case_key.txt`, the only copy (the Downloads file, 12:07 ET, differs from it
only by the final newline the hook added; it holds the release lines and the not-stated notes).

**The slice.** "2.7. fMRI processing and analysis" and its subsections 2.7.1 to 2.7.5, characters
49939 to 65626 of the PDF's text (15,687 characters). It holds the rest pre-analysis processing
(§2.7.4), the surface sampling with mri_vol2surf and the initial-frame count (§2.7.3); no dMRI or
sMRI section.

**Four draws**, each after a build change, every one through the same gate (a1 19, v2 19, v3 18, v4
18 identical; control 0 of 19):

| draw (ET) | out dir | software rule | calls | wall (s) | cost (USD) |
|---|---|---|---|---|---|
| 13:26 | `hop_case1_v6` | the checking pass's yes/no use verdict | T, S, SW, checking pass, RD, R | 100.7 | 0.4191 |
| 13:31 | `hop_case1_v7` | a use quote found anywhere, naming the tool | the same | 100.5 | 0.4199 |
| 13:34 | `hop_case1_v8` | the use quote found in the fMRI sections, naming the tool (a first-use acronym counts) | the same | 101.9 | 0.4099 |
| 13:39 | `hop_case1_v9` (of record) | as v8, and a mention whose own quote is not found takes its use quote when that passed | the same | 97.2 | 0.4122 |

No call retried in any of the four. What each software rule did, in order:
- v6: the checking pass dropped FreeSurfer (its verdict reads the sMRI segmentation quote) though its
  own note says FreeSurfer is "used for surface sampling and ROI extraction". Its question is not
  the author's, so the rule was replaced.
- v7: kept MMPS (overview sentence), FreeSurfer (the sMRI sentence) and FIRMM (acquisition-time
  monitoring); dropped AFNI, whose listed name "Analysis of Functional NeuroImages (AFNI)" the check
  did not split. A quote anywhere naming the tool shows no fMRI use, so the rule was tightened.
- v8: AFNI's mention quote (a package list the text does not hold verbatim) failed, so no tool was
  listed; FreeSurfer's use quote was the sentence before the mri_vol2surf one, which does not name it.
- v9: below.

### The key against v9 (the same table)

| field | key | hop | |
|---|---|---|---|
| distortion_correction.method | reversing phase-encode polarity, then gradient-nonlinearity correction | not reported (`value_unsupported_by_quote`); checking pass: missed | key-only |
| brain_extraction (4) | not stated for fMRI | not reported | agree (4) |
| slice_time_correction (6) | not stated | not reported | agree (6) |
| coregistration.performed | yes | yes, the fMRI sentence | agree |
| coregistration.method | not stated (in-house) | not reported; checking pass: missed | agree |
| coregistration.transform | rigid | rigid, the fMRI sentence | agree |
| coregistration.nonlinear_transform_type | not applicable | not applicable, by rule | agree |
| coregistration.cost_function | mutual information | mutual information; checking pass: wrong | agree |
| coregistration.interpolation | not stated | not reported | agree |
| spatial_smoothing (6) | not stated for fMRI | not reported | agree (6) |

**Fields, 23: agree 22, differ 0, hop-only 0, key-only 1** (as the third round).

| software | key | hop | |
|---|---|---|---|
| AFNI (3dvolreg) | no version | AFNI, no version; use quote the 3dvolreg sentence (its mention quote failed and took the use quote) | agree |
| FreeSurfer | 5.3 | extracted, 5.3, but its use quote is the sMRI segmentation sentence, outside the fMRI sections: not listed | key-only |
| FreeSurfer mri_vol2surf | (FreeSurfer 5.3) | not named by call SW | key-only |

**Software, 3 entries: agree 1, differ 0, hop-only 0, key-only 2.** MMPS, FIRMM and AtlasTrack are
named by call SW and not listed (no use quote in the fMRI sections); none is in the key. The software
list did not recover. The use rule did what it states in every case; what it never received is
FreeSurfer's fMRI sentence ("derived from FreeSurfer's automated brain segmentation (aseg)", §2.7.4,
or the mri_vol2surf one, §2.7.3). Across v7 to v9 the model gave the sMRI sentence twice and the
sentence before the mri_vol2surf one once.

Tools and releases as the third round: motion tool AFNI's 3dvolreg (agree), intensity no tool
(agree), Hagler's releases including the 1.0–2.0.1 range (agree), the citing paper's two releases
(agree), ABCD 3.0 postdates with the note rendered, collection 3165 undetermined.

### Why distortion_correction.method misses

A value-support miss, not a skip. In every draw call S returned a value with a quote from Hagler's
fMRI distortion sentences:

| draw | value | quote |
|---|---|---|
| v5 (13:06), v7 | "topup, gradunwarp" | the reversing-polarity sentence through the gradient-nonlinearity sentence |
| v6, v8, v9 | "gradunwarp" | the gradient-nonlinearity sentence only |

Each value is the field's list of tool names (`topup, fugue, gradunwarp, sdc_fieldmapless, other`),
none of which the quote contains. The check that rejected it is the coverage value-in-quote check
(`quote_support.coverage_value_supported`, the list rule: each member's aliases must occur in the
quote; `topup` and `gradunwarp` have aliases only of their own names; `other` has none). The prompt
allows "verbatim otherwise"; a verbatim "reversing polarity method" passes the same check against the
same quote (tested directly). The checking pass flagged the miss in every draw with the method as
the better value.

### Instructor mode and the checking pass's retries (item 6)

Every client in the package is JSON mode (`extractor.build_client`, `CallMeter.client`). The
checking pass was run once per coverage_v4 paper in each mode (`scripts/measure_checking_pass_retries.py`;
the pinned prompt, the batch's methods slice and draft; no held-out paper among the 18), both modes
concurrently, 13:0x to 13:3x ET:

| mode | papers | status ok | papers with a retry | retries | attempts | tokens in | tokens out | cost (USD) |
|---|---|---|---|---|---|---|---|---|
| JSON | 18 | 18 | 1 (liu_2013) | 1 | 19 | 241,509 | 158,690 | 3.4154 |
| tool calling | 18 | 18 | 0 | 0 | 18 | 211,929 | 139,276 | 2.9974 |

liu_2013's retry is the case-one failure on the first hop: the reply copied `"align_epi_anat.py"`
with its double quotes unescaped (invalid JSON at line 293, column 162; finish reason stop). The
first hop has no `json_safe`. One draw per mode; the counts show no retry under tool calling on these
18 and do not establish a rate.

**Proposal (not built):** switch `build_client` and `CallMeter.client` to tool calling, after a
re-render gate on a vintage drawn under it, since the mode changes the request every call makes;
`json_safe` stays on the hop either way.

### Build checks

Tests: 635 extractor (not live), 235 root; hooks clean. Mutations, each diffed against the
pre-mutation file before its run, on a green baseline: S1 to S17 and N4 re-run on the final code,
all killed after three test fixes (S6 and S10 first survived because a test never reached the
case, S16 because no stub had a failed mention with a failing use quote; each test fixed and the
mutation re-run). The third round's N1 to N3 and N12 tested the narrow slicer, which is removed.
