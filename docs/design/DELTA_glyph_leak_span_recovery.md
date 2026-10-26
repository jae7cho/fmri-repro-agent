# DELTA — the `/C<digit>` exclusion, answered by a one-character wildcard

*Proposes reversing a ratified decision: `span_resolver.py:16-20` deliberately excludes the
font-specific `×`→`/C2` glyph mangle from tier 5. **Nothing here is implemented. No code is written,
no test is added, and nothing is left blocking it.** What is recorded is the mechanism, a quantification
across every published vintage, and the one argument that answers the recorded reason without weakening
the never-fuzzy invariant. Drafted 2026-10-22 against HEAD `3fc366f`. Every locator verified against the
working tree; every number produced by a command reproduced in this document. Facts gathered by a
four-strand read-only pass, each strand adversarially verified by a second agent: 102 claims checked,
14 refuted and corrected. Three of those corrections were against claims this author had already written
into `docs/findings/motion-probe-v1-results.md` — a wrong tier-5 commit, a wrong attribution of the
`/C2` finding, and an under-count of the leaks — and all three are fixed there. Every number below was
then re-derived here by command rather than taken from an agent.*

**Predicted effect on published figures: no figure moves. What changes is what one figure MEASURES** —
`agtzidis.target_space` is currently graded correct from a diagnostic side-channel the report does not
show (§5a), and the repair would put it on the same footing as the other 16 cells. **Stored extractions:
30 records recover, all `agtzidis_2020`, all from one clause.** One cell —
`liu_2005.resolution_mm` — is **unpredictable here** and declared so rather than guessed (§0).

**Already implemented, because the safety argument required it:** `span_recovered` is now disclosed on
both per-field surfaces. Predicted `14 identical, 5 changed`; measured `14 identical, 5 changed`, same
five papers (§2a). **The glyph proposal itself remains unimplemented.**

---

## 0. Scoping constraint, before anything else

Three papers are held out by prereg C11/C26 — `liu_2005`, `tang_2025`, `wheaton_2004` — and their text
may not be read in any form. This bounds the DELTA in a way that cannot be engineered away:

- `span-resolution-hard-drop.md:163-170` records a third unresolved-quote diagnostic,
  `liu_2005.spatial_normalization.resolution_mm`, value `'3.0'`. **Its prediction has since been derived
  without reading the paper**, per the author's instruction, by a script that prints booleans and nothing
  else: `extractor_mvp/scripts/glyph_leak_prediction.py`. Result:

  ```
  text_carries_glyph_leak:        False
  quote_crosses_leak:             False
  recovered_by_one_char_wildcard: False
  ```

  **liu_2005's slice carries no `/C<digit>` leak at all, so this proposal does not touch that cell.** Its
  drop is a different mechanism, which remains undiagnosed and would need an author ruling to pursue.

  *The script was validated on both controls before being pointed at the held-out cell.* agtzidis returns
  `True/True` and poldrack — which carries leaks but whose drops are **not** this mechanism — returns
  `False/False`, so a leaky paper alone does not produce a positive. The positive control also caught a
  real defect in the matcher: stripping whitespace *before* detecting leaks merges a code with adjacent
  content (`3 /C2 3` → `3/C23`, where greedy `\d+` reads `/C23` and swallows the measurement's digit).
  Leaks must be marked in the original text, where the whitespace that delimits them still exists. That
  ordering constraint is a requirement on any implementation, not an artifact of the probe.
- `span_resolver.py:17` names `wheaton` among the affected papers. That naming is taken from the
  docstring. It was not verified against the paper.

**Two disclosures.** The investigating pass surfaced held-out material twice, and both are recorded
rather than quietly dropped. (1) A repo-wide `grep` for `/C2` printed one line of
`extractor_mvp/results/subject_corpus_sweep.txt:50`, which is a verbatim methods sentence of
`wheaton_2004`. It appeared in tool output, was not used for any finding here, and no held-out PDF was
opened. (2) A `grep -rl … | wc -l` over `results/` evaluated its pattern against held-out-named result
JSONs, printing a file count only and no content. **Both point at the same structural fact:
`ground_truth/liu_2005_deinterleaved_methods.txt` is a tracked file.** The hold-out is a discipline
observed by readers, not a property the repository enforces, and any recursive search can surface it.
That is worth a decision independent of this DELTA.

**Logged incidents (2026-10-22), in full:**

| # | what happened | what was exposed | used in a finding? |
|---|---|---|---|
| 1 | repo-wide `grep -rn "/C2"` by an investigating agent | one line of `extractor_mvp/results/subject_corpus_sweep.txt:50`, a verbatim `wheaton_2004` methods sentence, printed in tool output | no |
| 2 | `grep -rl quote_unresolved results \| wc -l` by an investigating agent | a file count only; the pattern was evaluated against held-out-named result JSONs, no content printed | no |

Neither opened a PDF. No held-out text informed any claim in this DELTA or in
`docs/findings/motion-probe-v1-results.md`.

**Mitigation, and what it does not cover.** `.rgignore` now excludes the three held-out ids,
`subject_corpus_sweep.txt`, and `ground_truth/liu_2005_deinterleaved_methods.txt` — the last listed
explicitly although it is already matched, because it is the one held-out artifact deliberately
**tracked**: it is a pipeline input (`run_pending_target_space.py:31` feeds it as liu_2005's methods
slice), so it stays in git and out of searches. **`.rgignore` is read by ripgrep and ignored by plain
`grep -r`, and both incidents above were `grep`.** This closes the `rg` path only; the rest remains
discipline, which is why the held-out ids are also refused in code
(`motion_probe.py` `_HELD_OUT`, before a client is built) and why this script prints booleans.

**Session hygiene.** The session that produced this DELTA has seen held-out text (incident 1). Per the
author's instruction, **any stanza iteration runs in a fresh session**, since stanza wording is the one
artifact a glimpse of held-out prose could contaminate.

## 1. What is proposed

**A `/C<digit>+` run in the *source text* may match exactly one character of the model's quote, with no
claim about which character it is.** Everything else stays as it is: substring-only, never fuzzy, spans
in original coordinates, re-verified fail-closed, fires only after every exact and near tier has failed,
and sets `recovered=True`.

That is the whole proposal. It is narrower than the thing the docstring refuses.

## 2. The recorded reason, and why a wildcard answers it

`span_resolver.py:16-20`, verbatim:

> NOT handled by tier 5: the font-specific multiplication-sign (U+00D7) -> `/C2` glyph mangle seen in a
> few papers (agtzidis/gordon/poldrack/wheaton). `/C<digit>` are font glyph codes that map to DIFFERENT
> glyphs across papers, so treating `/C2` as that glyph globally risks a WRONG match -- which would
> violate the never-fuzzy invariant. It is deliberately excluded; those dimension-quote drops stay
> unrecovered rather than risk a mis-attribution.

The reason is precise and it is correct: **`/C2` does not mean `×`.** It is a font-local code, and a
global `/C2 → ×` fold would assert a glyph identity the repository cannot know. Every word of that
survives this DELTA. The proposal does not fold `/C2` to `×`, or to anything.

It instead treats a leak as **a hole of known width and unknown content**. The two claims come apart:

| claim | status |
|---|---|
| "`/C2` is `×`" | **unknowable** — font-local, varies by paper. The docstring is right to refuse it. |
| "`/C2` occupies exactly one printed character" | **structural** — it is one glyph slot in the font, whatever glyph that is. |

The second claim needs no font table, no per-paper calibration, and no knowledge of the glyph. It is a
property of how the leak is produced: pypdf emits the glyph *name* where it cannot resolve the glyph, and
one name stands for one glyph. A wildcard asserts only the second claim.

> **RULED (author, 2026-10-22): width-not-identity answers `span_resolver.py:16-20`.** The exclusion was
> about *glyph identity*, and a one-character wildcard asserts none. The remaining risk — a wrong
> character at exactly a leak position — is confined to that character, and is now visible to the reader
> through the `span_recovered` marker wired in §2a. The recorded reason is satisfied rather than
> overridden.

This DELTA's §1 is therefore accepted in principle. What remains open is implementation and the items in
§7.

**What this costs, stated plainly.** One character per leak becomes unverified. If the page printed `÷`
and the model transcribed `÷`, the match succeeds and the span is right. If the page printed `÷` and the
model wrote `×`, the match also succeeds and that one character is wrong. The uncertainty is confined to
exactly the characters the text layer already destroyed — positions where the repository has *no*
ground truth and never did, under the current behaviour as much as under this one. The difference is that
today the whole quote is thrown away to avoid a one-character unknown, and the extraction with it.

### 2a. The disclosure this argument depends on — now built, because it was not

**An earlier draft of this DELTA argued the residual uncertainty was "flagged by the existing
`recovered=True` marker". That argument was false and is withdrawn.** `Extracted.span_recovered` shipped
in v0.4.0 (`provenance.py:55`) and **nothing read it**: it is set in `extractor.py`, round-tripped by the
spec, asserted in unit tests — and absent from `render.py` and `cobidas.py` entirely. No report, summary
or coverage surface showed it. A span located by repair was presented to the reader *identically* to a
clean character-exact match. **A provenance flag no surface reads is not a disclosure**, so the safety
argument had nothing to stand on.

It does now. `span_recovered` is wired to both per-field surfaces — `_protocol_main` (the report, via
`to_protocol`) and `_fmt_field_text` (the field table) — through one shared constant, so the two cannot
disagree about the same field. An EXTRACTED field whose span was recovered renders:

```
target_space = "MNI-152"   [from paper — quote matched after source-text repair]  «…»
```

**Gate prediction, derived before the change was written:** 9 stored fields in
`results/batch_a1_acceptance` already carry `span_recovered=True`, held by 5 of 19 papers — weber_2024
(3), liu_2013 (2), oconnor_2017 (2), derosa_2025 (1), mueller_2021 (1) — by field: `base_pipeline` 3,
`base_pipeline.version` 2, `target_space` 2, `target_surface` 1, `convention` 1. So the re-render gate
should report **14 identical, 5 changed**.

**Measured:** `14 identical, 5 changed`, and the five are derosa_2025, liu_2013, mueller_2021,
oconnor_2017, weber_2024 — the predicted set exactly. 377 tests pass; mypy clean on both jobs.

**agtzidis is not among those 5**, and that is the point: its quotes fail outright, so they never earn a
recovered span to mark. It gains markers only *if* this DELTA is implemented — at which point the
repair is disclosed on the field rather than silently improving a number.

The guard (`test_render.py::test_recovered_span_is_disclosed_on_both_surfaces_and_clean_spans_are_not`)
asserts the clean case beside the recovered one, because a render that tagged *every* extracted field
would disclose nothing while passing a one-sided test. Mutation-checked three ways — dropping the row
population, reverting the tag to the old unconditional `[from paper]`, and tagging every field — each
fails it.

**This closes the `span_recovered` item independently of whether the glyph proposal is accepted.** If the
author rejects §1, the disclosure wiring still stands on its own: it was a shipped field with no consumer
for three months.

**Why that is not the fuzzy matching the invariant forbids.** Edit-distance matching lets a quote differ
*anywhere* by *any* small amount. This lets a quote differ *only* at positions the source itself marks as
corrupt, by *exactly* one character each. A paraphrase, a wrong number, a dropped clause, a reversed
negation — none of them sits at a leak position, so none of them is reachable. §4 demonstrates this
rather than asserting it.

## 3. The mechanism, measured

All six probe papers were scanned; the three held-out papers were not loaded, not even to count
characters.

| paper | `/C\d+` occurrences | distinct codes | stored quote-unresolved drops |
|---|---|---|---|
| power_2014, binder_1999, liu_2013, derosa_2025 | 0 | — | 0 |
| agtzidis_2020 | 6 | `/C0`, `/C2`, `/C19` | 30 (see §5) |
| poldrack_2015 | 31 | `/C0`, `/C2`, `/C15`, `/C176` | 17, **none this mechanism** |

**poldrack carries five times agtzidis's leaks and loses nothing to them**, because its quotes do not
cross one. The exclusion is latent in the text and bites only at the intersection of a leak and a quote.

The divergence, in codepoints:

```
model returned : ' into 3 × 3 × 3 mm3 voxels.'          ×  = U+00D7
pypdf produced : ' into 3 /C2 3 /C2 3m m 3 vo'          /C2 = U+002F U+0043 U+0032
```

Three source characters stand for one printed character. The model transcribed the page correctly.

## 4. The demonstration, and the fail-closed controls

Substituting `×`→`/C2` in the model's quote and changing **nothing else** — which is what a
one-character wildcard would accept — resolves every failure, on the committed resolver:

```
unresolved motion-probe draws        : 7
resolved BEFORE substitution         : 0 of 7
resolved AFTER  substitution         : 7 of 7      (including draw 4, the SPM12 draw)
draw 4's recovered span              : start=7188 end=7445
```

The recovered span text is the full four-step sentence, in original coordinates.

**Fail-closed controls.** Five mutations of the substituted quote, each asserted to actually change the
string before testing, and each must still fail:

| mutation | result |
|---|---|
| `resampling` → `reslicing` | still fails |
| `3 mm3` → `4 mm3` | still fails |
| `3 /C2 3` → `3 /C2 4` | still fails |
| `anatomical` → `functional` | still fails |
| `without` → `with` (negation flipped) | still fails |

**Positive controls.** An invented sentence and a word-salad of real terms from the passage both fail to
resolve, as they must.

### 4a. The regression test must use the real quote and the real text

**A synthetic fixture carrying only the glyph would pass while the real case still failed.** The text
layer mangles this clause *twice*: it leaks the glyph **and** it splits the measurement token.

```
text  : '3 /C2 3 /C2 3m m3 voxel '
quote : '3 /C2 3 /C2 3 mm3 voxels'
```

Substituting `×`→`/C2` in the quote does **not** make it a literal substring of the text
(`sub in txt` → `False`). It resolves only because tier 5's **whitespace-DELETION** tolerance absorbs
`3 mm3` ↔ `3m m3` as well. So the proposal is not a standalone rule: it is a rule that must **compose**
with an existing tier, and only the real pair exercises the composition. A fixture containing a clean
`3 /C2 3` and nothing else would resolve under a glyph rule alone and prove nothing about agtzidis.

The test therefore needs the real mangled substring committed as a fixture — a short excerpt of one
clause, not the paper — and must assert the composition, not just the glyph. The fail-closed mutations in
§4 belong in the same test.

*A note on how this section was produced, because it bears on trust.* A first version of these controls
reported "a digit changed → RESOLVED (BAD)". That was a **no-op mutation**: the quote contains `3 mm3`,
not `3m m 3`, so `.replace()` changed nothing and the unmutated string was tested. The controls above
assert the mutation took effect before resolving. A guard that passes because it tests nothing is the
failure mode this repository has caught repeatedly, and it caught it again here.

## 5. Quantification across every published vintage

Five published vintages exist. The question for each is whether its number moves.

| # | vintage | figure | source | moves? |
|---|---|---|---|---|
| 1 | base_pipeline status agreement | 14/17 (82.4%); Tier-A 10/17, Tier-B 14/17 | `ground_truth/predictions_v040_frozen.csv` | **no** |
| 2 | target_space v040 blind | 11/17 (64.7%) | frozen snapshot | **no** |
| 3 | target_space v050 blind | 10/17 (58.8%), current headline | `target_space_predictions_v050.csv` | **no** |
| 4 | motion reachability probe, 2026-10-21 | counts only, no rate | `ground_truth/motion_probe_v1_projection.csv` | **no** |
| 5 | span-resolution hard-drop counts | 10/6 → 2/1 → 3/2 | the hard-drop findings | **yes, by construction** |

**Why 1–3 do not move.** Their scorers read status and value from committed snapshots; none reads a span
column. Re-scoring is therefore immune. The one row in a published target_space vintage whose quote
failed resolution is `agtzidis_2020` in v050 (`scoring_mode=fallback`, `quote_not_found`) — and running
the committed grader against the struct a repaired span would produce yields **the same grade,
`family_specified`**. The figure is unchanged even for the cell the repair touches.

### 5a. But the figure does not measure what the report shows — for exactly this cell

`ground_truth/target_space_README.md:115-118` already records this, and names this leak as the cause:

> The twelfth is agtzidis, and it is not a residue of this defect: it stays MISSING via
> `quote_not_found`, a pypdf mangling (`×` rendered as the literal `/C2`) documented in
> `span-resolution-hard-drop.md` whose fix is unbuilt. **agtzidis therefore still grades correctly only
> through the OLD diagnostic side-channel, not through the fix** — worth knowing before reading its row
> as evidence the retype worked.

Confirmed at the run level by `target_space-0.5.0-reextraction-prereg.md:129-131`: agtzidis "Stayed
`MissingFromPaper` via `quote_not_found` on **all 3 draws** … Graded `family_specified` via the
diagnostic raw — the OLD side-channel, **NOT the fix**."

**So the two surfaces disagree about this cell, and the published number follows the one the reader
cannot see.** The primary field — `extraction.status`, "the field the rest of the system reads"
(`target_space-false-missing.md:35-36`) — says `MISSING_FROM_PAPER`, and the report renders it as *not
reported in source*. The grader reads `ExtractionDiagnostic.raw_value`, finds `'MNI'`, and scores the
cell **correct**.

**Which of the two does the published 10/17 measure? For 16 of 17 cells, the report. For agtzidis, the
diagnostic.** The number is a mixture, and agtzidis is the last cell still scored that way: the retype
flipped 11 of the 12 side-channel cells to EXTRACTED, and this leak is the sole reason the twelfth did
not follow (`target_space_README.md:112-116`).

That reframes the repair. It does not raise the figure — the grade is `family_specified` either way — it
**makes the figure measure the same thing for all 17 cells**. Today one cell is graded on evidence the
tool declines to show its user. A reader auditing agtzidis's report would find no target space and
conclude the row was a miss; the scoreboard says it was a hit.

**This is the strongest argument in the DELTA, and it is not an accuracy argument.** It is that a
published number and a shipped report currently contradict each other on a cell, by exactly this
mechanism, and the repository has had the contradiction written down since the 0.5.0 re-extraction.

**The distinction that matters.** Re-*scoring* is immune; re-*extraction* is not. Extraction status
passes through the resolver at run time — `extractor.py:574-584` and `:839-852` turn a not-found quote
into `MISSING_FROM_PAPER` — so any re-extraction after this change produces a **new vintage** and is
reported as one, never merged into existing draws.

**Vintage 5 is the measurement of this defect**, so a repair changes it by definition. That is the point
of the repair, not a side effect.

**What recovers.** 78 stored quote-unresolved drops exist across 10 non-held-out papers, plus the 7
motion-probe draws. (Each drop is written to storage **twice** — once as a spec inference `reason`, once
as a `diagnostics.failure_reason` — so a naive scan of both keys returns 156. Counting one representation
gives 78 on each side, which is the drop count. Files whose names contain a held-out id were excluded
unopened.) Of those 78, the ones this mechanism explains:

- **`agtzidis_2020`: 30 records** — 23 stored (18 `resolution_mm`, 5 `target_space`) plus the 7
  motion-probe draws. Each fails on the current text and resolves after the substitution.
- **`chen_2015` (6) and `poldrack_2015` (17): not this mechanism.** All 23 already ground under the
  current resolver, and none of their quotes contains `×`.
- **`gordon_2014`:** carries leaks, 0 stored drops.
- **`liu_2005.resolution_mm`:** unknown, and unknowable here (§0).

**The honest headline is "one paper and one clause", not "silent corpus-wide loss".** All 30 agtzidis
records trace to the single resampling clause *"resampling them into 3 × 3 × 3 mm3 voxels"* — the same
clause that produced `resolution_mm` `'3.0'`, `target_space` `'MNI'`, and the discarded `SPM12` motion
draw. One corrupt clause, three fields, two measurement campaigns.

**A caveat that reduces the recovery further.** In 12 of the 18 batch files, `agtzidis.target_space`
fails on `value_not_in_literal` rather than on quote resolution. Those cells would **not** change: a
different guard stops them first.

## 6. What this does not do

- **It has no bearing on the motion control, which was retired for an unrelated reason.** The
  9-of-10 operation-phrase result is computed from raw values and never depended on quote matching. It
  is now moot in any case: the author ruled on 2026-10-22 that agtzidis is `described_only` (protocol
  v1.6), so the control's declared answer was wrong and its criterion is void as stated (prereg
  Amendment 3). Repairing the leak would recover the one discarded `SPM12` draw — which the corrected
  label makes the *outlier*, not the target. See `docs/findings/motion-probe-v1-results.md`.
- **It does not touch the motion stanza**, which is frozen pending the author's agtzidis ruling.
- **It does not disturb the probe's pre-registered conclusions.** The state-map rows, the `verbatim=None`
  trigger and ruling 4's threshold are computed from `raw_status` and `raw_value`; `value_kind()` takes
  only a value string. This is checkable in the projection: all 7 unresolved draws carry rows 1 and 2
  despite having no span at all.
  - **Resolver vintage of the probe run:** `span_resolver.py` at `3cb396e` (2026-07-16, the last commit
    to touch the file; unchanged at probe-time HEAD `b1442a1` and at `3fc366f`).
  - **The convention for recording this already exists and the probe did not follow it.**
    `ground_truth/predictions_v040_frozen.csv:6` carries `v040_span_recovery_commit: 2560bb1` in its
    provenance header, beside `source_commit` and `model`. The probe's manifest and
    `motion_probe_v1_projection.csv` record the stanza hash but **no resolver commit**. Adding one is a
    one-line change and is proposed here so the probe's vintage is self-describing rather than recorded
    only in prose. `docs/TRACK_A_SCOPE.md:187-188` already requires that "any emitted rate must name its"
    vintage, having been bitten by exactly this: target_space has two, 11/17 and 10/17.
  - **One carve-out:** the prereg's *correctness* rule (`motion-method-reachability-prereg.md:32-33`)
    requires `span_role` to match for a cell to count correct. A future motion **accuracy** figure does
    depend on the resolver and must name the vintage it ran under.
- **It does not resolve the classifier disagreement it inherits.** The v0.4.0 re-measure's automated
  classifier labels agtzidis's two drops `genuine-mismatch` with "RECOVERABLE mangle: 0"
  (`span-resolution-hard-drop-v0.4.0-remeasure.md:25-28`), because its `_hard()` normalizer drops `×`
  but keeps the `c2` left behind by `/C2`. The `/C2` attribution is a later hand-adjudication
  (`span-resolution-hard-drop.md:121-125`), and `:133-138` calls the conflict "a classification
  disagreement that is not a reclassification". **This DELTA sides with the hand adjudication**, on the
  §4 evidence that the substitution resolves every one of the 30 records.

  The classifier is demonstrably wrong, and its own docstring says the opposite.
  `hard_drop_audit.py:104` claims the normalizer catches exactly this case — "Weaker normalizers miss
  real mangles (agtzidis's multiplication-sign renders as '/C2' …)" — but `:105` is
  `re.sub(r"[^a-z0-9]", "", s.lower())`, which **deletes** `×` and **keeps** the `c2`:

  ```
  norm("3 × 3 × 3 mm3")      = '333mm3'
  norm("3 /C2 3 /C2 3m m 3") = '3c23c23mm3'      substring match: False
  ```

  So the function cannot match a `/C2` mangle, while its docstring asserts it is the robust test for one.
  That is a second, smaller defect. It is named here and not fixed.

## 7. Open, for the author

1. **Does the one-character-wildcard reading answer `span_resolver.py:16-20`?** The docstring refuses a
   glyph identity claim; this makes a glyph *width* claim. If that distinction is not accepted, the
   proposal fails and the exclusion stands.
2. **Is a `recovered=True` span with one unverified character per leak acceptable output**, or should a
   leak-crossing quote resolve but be marked more strongly than the existing marker does?
3. **`liu_2005`.** Its cell cannot be predicted or verified without reading held-out text. Ruling needed
   before any re-run covers it.
4. **The tracked held-out text** (`ground_truth/liu_2005_deinterleaved_methods.txt`), which is a
   hold-out-integrity question wider than this DELTA.
5. **Ordering against the agtzidis ruling.** These are independent — this changes no value and no label —
   but a re-extraction would produce a new vintage, so the sequencing is the author's.
