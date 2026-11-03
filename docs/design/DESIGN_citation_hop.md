# DESIGN: the citation hop (one hop into a cited paper)

**Status: design only, 2026-11-03.** No model calls were made for this document, and no cited paper
was opened. Case one is gracia-tabuenca_2024 → Hagler et al. (2019), whose PDF is at
`/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch/Hagler_2019.pdf` (3,382,421 bytes, present,
unread). The author set the scope on 2026-11-03; the rulings it rests on are dated 2026-11-02
(`docs/findings/coverage-v4-results.md`, "The author's rulings on the open items").

**A one-hop resolver already exists, and it has never run on a stored vintage.**
`extractor_mvp/src/extractor_mvp/citation_resolver.py` fetches a cited PDF, runs the full extractor
on its methods (`citation_resolver.py:224-229`), and writes each value it finds into the citing
paper's inference arm as an `InferredDefault` with `PriorPublicationBasis`, confidence
`min(source × 0.70, 0.60)` (`citation_resolver.py:45`, `src/fmri_repro/spec/provenance.py:25`).
`build_citation_resolver` returns None when `citation_cache_dir` is missing
(`batch_utils.py:16-28`), and that directory resolves against the config file's folder
(`batch_config.py:26`, `:55-58`): `extractor_mvp/configs/citation_cache` does not exist (`ls`: "No
such file or directory"). No stored record under `extractor_mvp/results/*/papers/` carries a
`prior_publication` basis (grep: no matches). The design below replaces that path for paper targets
rather than extending it, for the reasons given under 4.

## 1. When the hop runs

The hop runs on a field or a D.3 row the citing paper defers to a **paper** target
(`Deferral.target_kind == "paper"`, `extraction_result.py:33`). A "supplement" target is mapped to
"paper" in the schema (`extractor.py:826`), but the `DeferralRecord` keeps the original value
(`extractor.py:827-831`); the hop reads that and skips supplements, which are not a paper to fetch. A **pipeline** target stays with the KB (`_resolve_deferrals`,
`extractor.py:1973`, the base-pipeline branch at `:2005-2021`), unchanged.

Two shapes of paper deferral reach it.

- **A field deferral** (gracia-tabuenca_2024's `distortion_correction.method` → Hagler et al.
  (2019) in coverage_v4). The hop asks the cited paper for that field and nothing else.
- **A base-pipeline deferral to a paper** (gracia-tabuenca_2024's `base_pipeline` → Hagler et al.
  (2019)). The citing paper hands the reader the whole pipeline, so the hop's scope is the rows the
  citing paper did not report itself, plus the Software row's versions. A row the citing paper
  states is never asked of the cited paper. This is fork A below.

The hop runs after the checking pass, and only on deferrals whose sentence resolved (a deferral is
built only when its span resolves, `extractor.py:814-831`). It never runs on a not-reported field: a
paper that says nothing has deferred nothing.

## 2. Resolving the target

Three steps, in order; each ends in a recorded state.

1. **The reference entry from the citing paper.** The deferral's `ref` is author-shaped ("Hagler et
   al. (2019)", "Glasser et al. 40", "refs. 47 and 48", "45"). The hop finds the matching entry in
   the citing paper's own reference list and keeps it verbatim with its offsets, quote-checked like
   any other span. Numbered refs (braun's 47 and 48, poldrack's 45, viduarre's 40) match by number,
   and author–year refs by first author and year. No reference-list parser exists today:
   `methods_finder.py:46` uses "references" only as the end of the methods slice. This is the one
   new parser the hop needs. A ref that matches no entry is `reference_not_found`. A ref that
   matches two is `reference_ambiguous`, and the hop stops there; it never picks.
2. **A local PDF first.** The entry's DOI, when it carries one, and otherwise its first author and
   year, are looked up against the corpus folder (`tested_lit/sfn_batch/`, where Hagler_2019.pdf
   already lives) and the citation cache's index (`citation_cache/index.yaml`, one entry today,
   glasser_2013). Matching is exact after normalization, the rule `paper_fetcher.py:15` already
   states. The index's aliases miss viduarre's strings ("Glasser et al.", "Glasser et al. 40"),
   which is a further reason to match on the reference entry and not on the in-text ref.
3. **PubMed Central open full text.** DOI to PMCID through the ID converter, then the open-access
   full text. Tier 3 is a stub today (`paper_fetcher.py:115`). Only open-access text is fetched,
   and nothing behind a login.

A target none of the three reaches is **not retrievable**, a reported state with its reason
(`reference_not_found`, `reference_ambiguous`, `no_local_pdf_no_pmcid`, `pmc_not_open_access`,
`fetch_failed`). The report says so on the deferred line, so a reader can tell "the hop found
nothing in the cited paper" apart from "the hop never read the cited paper".

## 3. What runs on the cited paper

The same calls, on the cited paper's methods slice, scoped to the deferred fields: call T for the
temporal and volume fields among them, call S for the spatial ones and the software list, and the
checking pass over that scoped draft. A call none of whose fields is deferred is not made. The cited
paper is a paper like any other: the same span resolver, quote-support checks and scope rule. The
cited paper's own deferrals are recorded and never followed (one hop, see 4).

**A cited paper that covers several datasets reports its own variants, not one value.** Hagler et al.
(2019) describes ABCD, acquired across several sites and scanners, so a single value per field would
be a guess about which one the citing paper used. Each second-hop field carries a list of
`(value, quote, applies_to)` entries, where `applies_to` is the cited paper's own words for the
variant (e.g., a scanner vendor or an acquisition), quote-checked like the value. One entry with
`applies_to` = "all" is the ordinary case. The hop never chooses among variants on the citing
paper's behalf. When the citing paper itself states which variant it used, that sentence is the
citing paper's own report and belongs to the first hop. The scoped prompt asks "does the text give
different values for different scanners, sites, sequences or cohorts" per field, the same shape as
the record-level `multiple_pipelines` question.

## 4. Provenance

- **Second-hop values live beside the record, not in it.** A `second_hop` record is stored next to
  `verifier` (`batch.py:314`), keyed by the citing paper's dotted field path, with: the deferral's
  ref, the matched reference entry, the resolution state, the cited paper's identity (DOI or local
  path and its sha256), the scoped draft's fields with their quotes, the cited paper's checking-pass
  verdicts, and wall time. The citing paper's `Preprocessing` is not touched, so the identity gate
  stays a statement about the citing paper alone.
- **Shown as "from Hagler et al. 2019, cited by this paper".** In the report, a second-hop value
  sits on its own line under the deferred field, after "deferred to Hagler et al. (2019)", with its
  quote from the cited text. The Software row adds "Hagler et al. 2019 reports: …" under the deferral
  line, so the citing paper's line ("deferred to Hagler et al. (2019); version not reported in this
  paper") stays as ruled.
- **Quote-checked against the cited text.** The same span path, against the cited paper's text. A
  quote that does not resolve leaves the value unverified, shown and not used, as on the first hop.
- **Never counted toward the citing paper's COBIDAS compliance.** `assess_coverage` reads the
  extraction arm only (`cobidas.py:410`), and the second-hop record never enters it. A test pins
  this: a second-hop exact version must leave the citing paper's Software row unaddressed and its
  violation in place.
- **One hop only.** The cited paper's deferrals are recorded as "the cited paper defers further to
  …" and not followed.

The existing resolver is retired for paper targets because it breaks three of these. It writes into
the inference arm, where a value reads as AESPA's inference rather than the cited paper's report.
It keeps no quote from the cited text (`PriorPublicationBasis` carries a citation string and a
note). It runs the full extractor on the cited paper, so it asks for every field rather than the
deferred ones. Its "first cited source wins" (`citation_resolver.py:206`) also collapses the variants
in 3 to one value.

## 5. Evaluation

**Case one, read by the author against both papers.** gracia-tabuenca_2024 → Hagler et al. (2019).
In coverage_v4 the citing paper defers two fields there: `base_pipeline` and
`distortion_correction.method`. Fork A sets how many more the hop asks for. The author reads both
papers and records the answer key before the hop's output is shown, as was done for the two unseen
papers on 2026-11-02: per scoped field, what Hagler reports, its variants, and the sentence.
Comparison is by field, by counts, with no rates.

**Further cases, if their targets resolve.** The ref strings below are coverage_v4's.

| case | deferral in coverage_v4 | target resolution, before any hop |
|---|---|---|
| braun_2015 | `base_pipeline` and 20 further fields → "refs. 47 and 48" | two numbered refs on one deferral; needs the reference list; two cited papers for one hop (fork C) |
| viduarre_2017 | 14 fields → "Glasser et al. 40"; 1 → "Glasser et al."; 1 → "Smith et al. (18, 39)" | Glasser 2013 is the one PDF in the citation cache; "Smith et al. (18, 39)" is two refs |
| poldrack_2015 | `motion_correction.method` → "45" | needs the reference list |
| mueller_2021 | **no deferral recorded** in coverage_v3 or coverage_v4 | the hop does not fire on it; Pritschet becomes a case only if the drafter records a deferral there, or the author rules that a dataset citation is one (fork D) |

Each case gets a per-case answer key before its output is seen. The held-out papers (liu_2005,
tang_2025, wheaton_2004) are not cases.

## 6. Costs and open forks

**Cost per hop**, from coverage_v4's measured wall time (`coverage-v4-results.md`, "Wall time per
paper"): a full paper ran 93.5 to 268.9 s, of which the checking pass took 42.0 to 204.6 s. A scoped
hop makes at most the same calls on one cited paper, so its ceiling is one paper's time; a hop with
one deferred field makes one drafting call and one checking pass. Retrieval adds the reference
match (no model call) and, for PMC, one network round trip. Case one is one hop. The four further
cases are at most six cited papers (braun 2, viduarre 3 refs, poldrack 1), each a hop at most once
per run, cached by DOI.

**Open forks, each with a recommendation.**

- **A. Scope of a base-pipeline deferral to a paper.** (i) Only the fields deferred explicitly;
  (ii) every D.3 row the citing paper did not report, plus the Software row's versions. The
  existing resolver does (ii) over LEFT_MISSING fields (`citation_resolver.py:144-206`).
  Recommended: (ii), since "preprocessing as in X" defers the pipeline as a whole, with each line
  marked as asked because of the base-pipeline deferral, not because of a field deferral.
- **B. The checking pass on the cited paper.** It roughly doubles the hop's time (42.0 to 204.6 s
  per paper in coverage_v4). Recommended: run it; a second-hop value with no check would be the
  least checked value in the report.
- **C. One deferral, two cited papers** (braun's "refs. 47 and 48", viduarre's "Smith et al. (18,
  39)"). Recommended: hop to each, show each source's values on its own line, never merge; a field
  the two report differently is shown as two values, like variants.
- **D. A dataset citation that is not a methods deferral** (mueller's Pritschet). Recommended: no
  hop. The hop follows the citing paper's deferral and does not create one.
- **E. Retiring the existing resolver.** Recommended: disable it for paper targets in the same
  change that adds the hop, and keep the code until the hop has run on case one, so the two can be
  compared on the same deferrals.
- **F. Variants on a field the citing paper narrows.** If the citing paper says "Siemens data only"
  in its own text, the hop still shows every variant the cited paper reports, and the citing
  paper's own sentence sits on the first hop. Recommended as written; choosing a variant for the
  reader is a ruling for the author.

## The author's rulings (dated 2026-11-03, sourced to the author)

- **Forks A to F are ratified as recommended.** A: a base-pipeline deferral to a paper reaches every
  D.3 row the citing paper did not report, plus the Software row's versions. B: the checking pass
  runs on the cited paper. C: one deferral to two cited papers hops to each, and their values are
  never merged. D: a dataset citation that is not a methods deferral gets no hop. E: the existing
  resolver is disabled for paper targets in the change that adds the hop. F: every variant the
  cited paper reports is shown, and the citing paper's own sentence stays on the first hop.
- **Described vs applied.** A second-hop value renders "as described in <ref>": the cited paper
  describes a pipeline, and the citing paper's data may have been processed by a later version of
  it. The citing paper's data release, when it states one, is a first-hop field with its quote.
  When that release postdates the cited paper, the line notes that the described pipeline may
  differ from the one applied.
- **KB backlog: per-tool exact-version rules with sources**, replacing FreeSurfer's special case in
  `cobidas._EXACT_RELEASE_PARTS` (`docs/findings/kb-exact-version-rules-backlog.md`).

## As built for case one (2026-11-03)

`extractor_mvp/src/extractor_mvp/citation_hop.py`, `scripts/run_citation_hop.py`,
`tests/test_citation_hop.py`. Where the build differs from the sections above, it says so here.

- **Reference list.** `parse_reference_list` splits the last "References" section at lines that
  start an entry ("Surname, I" or a number) after a line ending in a period, a DOI or a URL.
  `match_reference` matches author-year on first author and year, and numbered refs one target per
  number. The first author is matched on the whole name and its first word: gracia-tabuenca_2024's
  list writes "Hagler Jr", and the first run of the hop matched on the last word and reported
  `reference_not_found` with no model call.
- **Target.** A local PDF only, named `<FirstAuthor>_<year>.pdf` in the corpus folder, with the
  entry's DOI checked against the PDF's text (`doi_confirmed`). PubMed Central is not built; a
  missing PDF renders "no local PDF (PubMed Central is not built yet)".
- **Calls.** The pinned T and S prompts unchanged, with `HOP_ADDENDUM` (pinned
  `a167221c…`) inserted before their text block: the fields asked by name, and the per-variant
  question. A call with no asked field is not made. The checking pass runs on a scoped draft through
  `run_verifier(..., draft=...)`.
- **Record and render.** The `second_hop` record is written to its own file beside the citing
  record, never into it. The report renders it as one section, "As described in cited papers",
  placed before the COBIDAS coverage, with each value "as described in <ref>" and its variants
  beneath it, rather than a line under each deferred field (§4). The Software row's second-hop
  versions sit in that section, marked not counted.
- **Fork E.** `_resolve_deferrals` no longer routes paper or supplement targets to the one-hop
  resolver (`extractor.py`, `_hop_kinds`).
- **Not built in this round.** The citing paper's data release as a first-hop field, and its
  "described vs applied" note. Built in the second round, below.

## The author's rulings (dated 2026-11-03, afternoon, sourced to the author)

- **Fork A widened.** Under a base-pipeline deferral to a paper, a row the citing paper reports
  without a tool (described_only) is asked for the tool too.
- **The checking-pass retry fix and the data-release field**, as the morning's rulings asked.
- **Released-derivatives state, design only** (the next section).
- **KB backlog:** dataset release to processing documentation (the ABCD release notes per release,
  the HCP minimal preprocessing pipelines), and tool facts such as "FreeSurfer recon-all includes
  skull stripping", each with a source (`docs/findings/kb-release-documentation-and-tool-facts-backlog.md`).

## Released-derivatives state (design only, 2026-11-03)

**A citing paper that analyses a dataset's released derivatives did not run the preprocessing
itself; the release's documentation is the record of what was run.** gracia-tabuenca_2024 takes
its functional connectivity matrices from the ABCD-BIDS Community Collection 3165 and its other
baseline MRI derivatives from ABCD 3.0, and defers its preprocessing to Hagler et al. (2019), which
describes Releases 2.0 and 2.0.1. The author's key notes that the matrices likely come from another
pipeline (DCAN's ABCD-BIDS), in which case Hagler does not describe their preprocessing at all.

**The first-hop field.** The data-release field built in the second round (`dataset`, `release`,
quote) gains what the citing paper takes from that release, quoted: `derivatives` (e.g.
"preprocessed functional connectivity matrices") and whether the BOLD analysis reads them. A
release with no derivatives quoted is a data source only, and the state below never fires on it.
When the paper names two releases and does not say which one feeds the BOLD analysis, the binding
is undetermined and nothing is inferred.

**The state.** For a release whose derivatives the BOLD analysis reads, the KB's entry for that
release (the backlog item) lists the documented pipeline's steps, each with its source. For a
mandatory D.3 row the citing paper does not report:

- a step the documentation includes: the documented value, on the inference arm, with basis
  `release_documentation` (release, document, section, source, date checked);
- a step the documentation does not include: **"not in the cited release's documented pipeline"**,
  on the inference arm, with the same basis. Never "not performed": a documentation's silence is
  not evidence that a step was skipped, and the extraction arm keeps the paper's own state.
- a release the KB has no entry for: no inference, and the report says the release is not in the
  KB, so a missing entry is visible.

**The citing paper's COBIDAS row is unchanged.** The coverage section counts what the paper reports;
an inference-arm value from a release's documentation is not the paper reporting it, the same rule
that keeps second-hop values out of the counts (§4).

**With the hop.** Both are shown. The hop's values stay "as described in <ref>"; the release's
documentation sits on the inference arm. When the release postdates what the cited paper describes,
the second round's "may differ" note already says so on the hop's lines.

**Tool facts.** A KB fact about a named tool ("FreeSurfer recon-all includes skull stripping") fills
the inference arm of the row it names with basis `tool_fact` and its source, only for the data the
fact covers. recon-all strips the T1w image, so the fact does not fill the BOLD brain-extraction row
gracia-tabuenca_2024 leaves unreported. The checking pass's two "missed" verdicts on Hagler's
brain extraction rest on that same sentence, and the key reads it as not stated for fMRI.

**Fork G (open): the inference arm's shape for "not in the documented pipeline".** It is a statement,
not a value, and the frozen provenance contract has no inference state for it.
- G1 (recommended): a new inference state carrying the basis, `NotInDocumentedPipeline`, in a schema
  minor version with its migration; old records read unchanged.
- G2: a `LeftMissing` reason `not_in_release_documentation`, with the basis kept beside the record.
  No schema change, but the basis is not on the field, which is the provenance rule's point.

**Evaluation.** Case one first: the author's key states the releases and their match. Each rendered
"not in the cited release's documented pipeline" line is checked by the author against the
document it cites. No rates.

**Cost.** No model call beyond call R (the derivatives question is asked there). The cost is KB
curation: one entry per release, checked against the release's own documentation.

## As built, second round (2026-11-03, afternoon)

- **Fork A widened.** `hop_scope` lists in `tools` every reported row whose `method` names no tool
  (`described_only`): a method value resolved to no member of the step's tool list, or only to
  `other`/`custom`, for the step kinds whose method literals name programs (`_TOOL_METHOD_KINDS`;
  temporal filtering is left out). Call S asks each listed step's tool, and each tool is checked as
  a variant is (quote found, tool in its quote, a possessive aside), and renders "<field> tool (this
  paper: "<its words>", no tool named) = <tool>, as described in <ref>". A tool that fails its check
  renders as unverified, never as "no tool named". Case one asks two: motion correction ("corrected
  for motion") and intensity correction ("B1-bias field estimation").
- **The checking-pass retry.** `CallMeter` keeps every attempt with its number, `finish_reason`,
  raw reply and, through instructor's `parse:error` hook, the parse error. The cause, read from the
  record: the checking pass copied Hagler's curly-quoted "drop-out" into a JSON string as straight,
  unescaped quotes. `json_safe` replaces every double quotation mark in the cited text with an
  apostrophe, one character for one. Replacing straight quotes only did not stop it (Hagler's methods
  have none). One draw since the fix made no retry.
- **The data-release field.** Call R (`RELEASE_PROMPT`, pinned `28518830…`) on the citing paper's
  methods returns each named release of the paper's own data, quoted; it is stored in
  `<paper>.data_release.json`, beside the record. Call S also returns the releases the cited paper
  describes. `release_relation` compares version numbers within the same dataset (a parenthesised
  acronym matches the name): later than every described release is `postdates`, which renders "the
  pipeline described there may differ from the one applied to this paper's data". A release that is
  not one version number, or of a dataset the cited paper does not describe, is `undetermined` and
  says so. Release dates are not known (the KB backlog); only version numbers are compared.
- **Pins.** `HOP_ADDENDUM` re-pinned with a dated note (`64d8979f…`, covering the addendum and its
  tools and releases asks); the T, S and checking-pass prompts unchanged.
