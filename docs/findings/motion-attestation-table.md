# Finding: COBIDAS D.3 attestation across 19 motion-correction papers — 9 of 114 cells reported

**Date:** 2026-08-18. **Source:** `ground_truth/motion_correction_labels_v1.xlsx`, sheet `Labels`, rows
2–20, at protocol v1.5 (`ade9608`). **Labels are human-ratified**, not extractor output — this clears the
project's standing bar that unscored extractor output is never a literature finding.

**Scope:** attestation only. These figures measure whether a paper *says anything* about a reporting item,
not whether what it says is correct, complete, or sufficient to reproduce. Bullet numbering and the mapping
from these field names to COBIDAS D.3's items are defined in
`docs/ground-truth-protocol-motion_correction.md` **§1** ("What COBIDAS actually requires" — the
seven-bullet enumeration and the "Mapping to spec fields" table; COBIDAS: Nichols et al. 2017); this
document does not restate them. Note that the names used here are the **workbook column stems**
(`nonrigid_transform`, `interpolation_combined`), which §1's table lists split (`nonrigid` /
`transform_type`, `interpolation` / `transforms_combined`) — cross-reference by bullet number.

---

## The table

Bullets 2–7 across 19 papers = **114 cells**. Bullet 1 (`method`) is reported separately below because it
uses a five-state vocabulary rather than the four-state attestation vocabulary.

| # | item | reported | not_reported | deferred |
|---|---|---|---|---|
| 2 | `nonrigid_transform` | 1 | 10 | 8 |
| 3 | `fieldmap_unwarping` | 3 | 10 | 6 |
| 4 | `reference_scan` | 2 | 10 | 7 |
| 5 | `similarity_metric` | 1 | 11 | 7 |
| 6 | `interpolation_combined` | 2 | 11 | 6 |
| 7 | `slice_to_volume` | **0** | 12 | 7 |
| | **total** | **9** | **64** | **41** |

`not_applicable` was assigned zero times.

**Bullet 1 (`method`), for context:** `named_tool` 8, `deferred` 7, `described_only` 4, `absent` 0,
`stated_not_performed` 0. Bullet 1 is answered in some form by every paper in the corpus; bullets 2–7 are
not.

Every one of the 9 `reported` cells carries a verbatim quote (checked; zero exceptions). No cell was
labelled `reported` on inference.

---

## What the numbers say

**1. Reporting is concentrated, not thin-but-even.** The 9 reported cells fall in **7 papers**; the other
**12 of 19 report nothing at all** across bullets 2–7. No paper reports more than **2 of 6** — poldrack_2015
(`fieldmap_unwarping`, `interpolation_combined`) and power_2014 (`nonrigid_transform`,
`interpolation_combined`). There is no well-reporting tail; the maximum observed is a third of the items.

**2. Bullet 7 (`slice_to_volume`) is 0 of 19.** Not one paper in the corpus states it, in any of the three
non-`reported` forms combined — 12 silent, 7 deferred.

**3. A third of all cells are `deferred`, not absent.** 41 of 114 (36%) point elsewhere rather than omit.
This is a materially different claim from "authors don't report": in a third of cases the information is
asserted to exist somewhere else, which is a resolvability problem rather than a reporting-absence problem.
Reporting only the 9 hides it.

**4. Deferral is wholesale in practice, and that is the structural result.** Of the 7 papers whose *method*
is `deferred`, **6 defer all six of bullets 2–7** (braun_2015, chen_2015, oconnor_2017, vanderwal_2016,
viduarre_2017, weber_2024) — 36 of the 41 deferred cells. Only **one** paper mixes: poldrack_2015 defers 4
and reports 2. The remaining deferred cell is cole_2013's single one. So a paper that defers its motion
method almost always defers the entire D.3 motion block, and the per-row exception occurs **once in 19
papers**.

**5. Bullet 5's single reported cell is binder_1999** — the oldest paper in the corpus is the only one to
state a similarity metric. At N=19 this cannot support a claim about reporting practice over time; it is
recorded because it is the observation, not because it is a trend.

---

## Consequence for the protocol's own calls

CALL 6 (v1.1) establishes that a blanket deferral applies to *every* bullet, not only bullet 1. CALL 7
(v1.1) establishes that deferral is nonetheless assessed **per row**, because a citation's scope is set by
what it does in the sentence.

The corpus vindicates both, in different directions. CALL 6 is the common case: 6 of 7 deferring papers
defer all six bullets, and without CALL 6 those 36 cells would have been under-labelled. CALL 7 is the rare
case — it changes the answer for exactly **one paper**, poldrack_2015, whose 2 reported cells would have
been wrongly collapsed into the deferral had the rule been blanket-only. A call written for a single
observed case is easy to read as over-engineering; here it is the difference between 9 reported cells and
7, i.e. a fifth of the finding.

---

## Caveats — all three travel with any use of these figures

**1. Co-adjudication: 13 of 19 papers.** Candidate sentences were located and states proposed with LLM
assistance from the same model family as the extractor, with every state reviewed and ratified by the
author (protocol §7). The same instrument produces the method figure and the same 13 papers are flagged, so
this is not a fully clean human baseline. But the exposure is materially lower than for the method figure:
attestation is close to a presence/absence read — "did the paper state a similarity metric" leaves little
adjudication room — where the method labels turn on package-vs-wrapper, binding, and role judgements.
Protocol §7 records exactly this asymmetry, holding the attestation table "far less exposed" and "largely
independent of this limitation." The caveat travels with both figures but does not weigh on them equally.

**2. N = 19 is a convenience corpus, not a sampling frame.** The papers were assembled for methodological
coverage of the motion-correction step, not sampled from a defined population of fMRI publications. Every
figure here is a statement about **these 19 papers**. Confidence intervals are not reported because an
interval on a non-probability sample would imply a sampling frame that does not exist. Any generalisation
to "the fMRI literature" requires a different corpus and is not licensed by this document.

Confidence intervals are declined for a second and more basic reason, which also explains the **deliberate
departure from base_pipeline's Wilson [59, 94]**: the two figures are different kinds of quantity.
base_pipeline's 82.4% is an **accuracy rate** — agreements in a process with repeatable trials, where an
interval describes uncertainty about the extractor's behaviour. The 9 of 114 here is a **census**: a
complete count of every cell in the corpus, with nothing sampled and therefore no sampling error to
describe. An interval on a census would have to be an inference to a population, which returns to the
missing frame. The departure is principled rather than an inconsistency between the two documents, and
base_pipeline's interval is not impugned by it.

**3. derosa_2025's row is PROVISIONAL.** Its bullets 2–7 are all `not_reported`, but §2.4.4 points the FC
stream's preprocessing to Supplemental Materials, which is part of the paper (protocol §6 step 1) and has
not been obtained. Up to six cells could move. Under CALL 9 the paper is two-stream with the FC stream
unread and no arm assigned.

**4. Attestation is not correctness.** A `reported` cell means the paper states something. It does not mean
the statement is complete, unambiguous, or sufficient to reproduce the step. No accuracy claim of any kind
follows from this table.

---

## What this does and does not license

**Licensed.** "Across 19 papers describing a near-universal preprocessing step, 9 of 114 COBIDAS D.3
reporting cells (bullets 2–7) were answered; 12 papers answered none; one item was answered by no paper;
and a third of the remaining cells deferred to another source rather than omitting." With the three caveats
stated before the numbers, not after.

**Not licensed.** Any statement about the fMRI literature at large; any statement about whether reported
values are correct; any comparison to a reporting rate from another corpus without matching the sampling
procedure; any claim that reporting has improved or worsened over time.

**Independence.** This finding requires no extractor, no reachability probe, no scoring map, and no
resolution of the `FieldExtractionResult` vocabulary question that currently gates the method arc. It
stands whether or not the method arc completes, and it is the Goal-2 deliverable (helping reviewers and
authors meet COBIDAS reporting principles) in its own right.
