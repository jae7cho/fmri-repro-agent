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
