# Corpus, quotation, and what this public repository does and does not contain

*Written 2026-11-11 after a secret/exposure scan of both public repositories. The scan found **no
credentials of any kind** — not in the working tree and not in any of the 1,577 blobs across 428
commits. What it did find was third-party prose, which is a licensing and research-integrity
question rather than a security one. This file records the position, because the repository had
none.*

## What is never redistributed

**Zero corpus PDFs are tracked**, in either repository, in any commit. `extractor_mvp/results/` is
sealed by its own `.gitignore` of `*` (with `!.gitignore` so the rule stays visible to anyone
cloning), so no per-paper extraction output — which carries full model quotes — is published. The
corpus lives outside the repository and is resolved at runtime by
`extractor_mvp/src/extractor_mvp/corpus_paths.py`, from `$AESPA_TESTED_LIT` or `~/`.

## What IS published, quantified

Verbatim methods prose from the 19-paper corpus appears in the labelling artifacts, because the
label *is* a judgement about a specific sentence and the sentence is its evidence:

| artifact | verbatim content |
|---|---|
| `base_pipeline_labels_v1.csv` | ~3,227 words over 19 rows; longest single excerpt 411 words |
| `target_space_labels_v1.csv` | ~1,215 words over 19 rows; longest 277 words |
| 5 populated `*_labels_v1*.xlsx` workbooks | 31–58 prose cells of ≥120 chars each; longest cell 2,841 chars |
| `preproc_rows_labels_v1.xlsx` (added 2026-11-11, `4d779a3`) | empty today — but see below: nothing stops it becoming the sixth |
| `liu_2005_deinterleaved_methods.txt` | 140 words (a pipeline input: see `scripts/run_pending_target_space.py`) |

The newer per-draw artifacts (`motion_probe_*_projection.csv`) carry **no quote text at all** — only
status, derived class, state-map row and span offsets — so anyone holding the corpus can recover the
passage and anyone who does not, cannot. That is the pattern to extend, and it is why those files
are absent from the table above.

## The position on quotation

These are short excerpts of **methods descriptions** — the most functional, least creative part of a
scientific paper — quoted for meta-research about reproducibility, which is a different purpose from
the papers' own. They are a small fraction of each article, they are not a substitute for reading
it, and the tool exists to measure how completely those methods were reported. We consider this
ordinary scholarly quotation. It is recorded here rather than left implicit so that the judgement is
visible and can be challenged.

**If a publisher objects to a specific excerpt**, the fix is to shorten it or replace it with span
offsets in the manner of the projection files, not to delete the label: the label is our own.

## The hold-out, and what changed on 2026-11-11

Three papers are held out by pre-registration C11/C26 — `liu_2005`, `tang_2025`, `wheaton_2004` —
because reading their text destroys the only uncontaminated cells left in the motion corpus. Their
prose was sitting in the tracked label csvs under `supporting_quote` and `notes`, where any `rg` or
`git grep` for an ordinary methods term would surface it. That happened twice on 2026-10-22 (logged
in `docs/design/DELTA_glyph_leak_span_recovery.md` §0). `.rgignore` cannot prevent it: it matches
**paths**, and this text lived inside files named for the label set.

**Fixed:** both derivers now withhold `supporting_quote` and `notes` for held-out rows, so the csvs
carry none of it. The withholding happens at derive time, so the csv stays fully reproducible from
the workbook and the labeller's own evidence is untouched. `notes` is included because
wheaton_2004's target_space note embedded a verbatim passage of its own. `value` and the state
columns are **not** withheld: they are the label, they are short parameter values rather than prose,
and withholding them would destroy the ground truth the file exists to carry. Guarded by
`extractor_mvp/tests/test_heldout_quote_redaction.py`, with a positive control asserting that
non-held-out rows keep their evidence — without which a deriver that redacted everything would pass.

**NOT fixed, and this matters:** five of the six then-tracked workbooks contained held-out prose (untracked the same day, below).
Each of those five names all three held-out papers and holds dozens of prose cells. Cleaning the
csvs reduced the surface that casual searching hits; **it did not remove held-out text from this
public repository.** Closing that needs one of:

1. **Strip the held-out rows' prose columns in the workbooks** — touches the labelling instrument,
   which is the author's and is deliberately not edited by tooling.
2. **Untrack the workbooks** — but they are the declared single source of truth that makes the csv
   reproducible, so cloners would lose the ability to re-derive it.
3. **Accept it** — the papers remain unread *by the extractor and by the project*, which is what
   C11/C26 actually protects; publication of the prose does not by itself contaminate a future run.

**Ruled 2026-11-11 by the author: option 2, untrack.** The six `ground_truth/*.xlsx` workbooks were
removed from the index (`git rm --cached`; the files stay on the author's machine). `ground_truth/*.xlsx`
is now in `.gitignore`. Examples will be published later, deliberately, once labelling is finished.
The consequences, stated plainly:
- the derived csvs stay tracked, but a cloner cannot re-derive them;
- the tests that read the real workbooks skip in CI with that reason, and run where the workbooks
  exist;
- every merge test builds its own workbooks.

The workbooks remain in git history, like the csv prose (next section).

### The merge path would have dug the same hole

**Caught before any labelling.** `preproc_rows_labels_v1.xlsx` (commit `4d779a3`, 2026-11-11) was
empty, so it carried nothing. But `ground_truth/preproc_rows_walk_v1.csv` lists all 19 corpus papers
including `liu_2005`, `tang_2025` and `wheaton_2004` (ids only — that file is clean), and
`scripts/merge_labels.py` contained no held-out handling of any kind. Labelling those rows and
merging would have written held-out quotes and notes into a tracked workbook and into
`preproc_rows_progress_v1.csv`, reproducing in a new file exactly what the derivers had just been
changed to prevent.

**Closed the same day, before any labelling.** `scripts/merge_labels.py` now writes a held-out
paper's prose cells (`quote`, `notes`, and `method_quote` on the motion sheet) as a marker. It
appends the prose itself to `ground_truth/heldout_label_prose.local.jsonl`, which is gitignored.
States and values are written as for any paper, because they are the label.
`preproc_rows_progress_v1.csv` holds row counts only and never held prose. Guarded in
`tests/test_merge_labels.py`, with a positive control showing that a paper not held out keeps its
prose.

## Why the history is not being rewritten

The prose has been public since 2026-07-31, so removing it from `HEAD` does not unpublish it; only a
history rewrite would. **That rewrite is not recommended here, and the reason is specific to this
repository rather than general reluctance:**

- Three protocols state that **"the signed commit order is the pre-registration"**
  (`docs/ground-truth-protocol.md:4`, `-target_space.md:4`, `-motion_correction.md:87`). The commit
  graph is not incidental metadata; it is the evidence that labels were fixed before scoring.
- **606 hash citations** depend on it — 390 lines in `DEVLOG.md` and 216 across `docs/` — plus
  `ground_truth/predictions_v040_frozen.csv`'s `source_commit` provenance header.

A rewrite would change every SHA, invalidating all of it and destroying the pre-registration
mechanism, in exchange for unpublishing short methods excerpts that this file argues are legitimate
to quote. The trade is lopsided. Recorded as a decision, not an oversight.
