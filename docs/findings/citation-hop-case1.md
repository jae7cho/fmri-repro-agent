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
