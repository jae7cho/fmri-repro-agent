# Finding: the base_pipeline recall gap is a stage-3 (model) problem, not a frontend one

**Harness:** `extractor_mvp/scripts/stage_partition.py`
**Model (pinned):** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`
**Population:** the 9 non-cabral papers whose `base_pipeline` is `MISSING_FROM_PAPER` in
batch_v6_full. Raw table + per-paper context windows:
`extractor_mvp/results/STAGE_PARTITION.md` (gitignored — regenerate with the harness).

## Claim

Every `base_pipeline` miss except one is a **clean pipeline token that is present in the exact
methods slice the model received** — the model simply failed to extract it. The pypdf frontend and
the methods_finder slice are **not** the binding constraint. A future proposal to "swap the PDF
parser" or "widen the slice" to fix base_pipeline recall is aimed at the wrong stage.

## Evidence

Partition of the 9 misses by where the failure lives:

| class | count | meaning |
|---|---|---|
| STAGE-1 (token shattered by pypdf) | **0** | — |
| SLICE-BOUNDARY (token cut out by methods_finder) | **0** | — |
| NOT-A-MISS (paper names no pipeline; MISSING correct) | 1 | liu_2005 |
| STAGE-3 (clean token in slice, model returned MISSING) | 8 | the prompt-addressable population |

Then K=15 repeats on the 8 stage-3 papers (temp 0, fixed input) to test whether the model miss is
deterministic:

- **Deterministic MISSING 15/15 (6 papers):** oconnor, weber (C-PAC, explicit usage), binder,
  liu_2013, poldrack, power.
- **Flips (2 papers):** derosa MISSING×8 / EXTRACTED:FSL×7; viduarre MISSING×11 / EXTRACTED:HCP-MPP×4.

## Caveats

- "STAGE-3-clean = 8" is a **mechanical** count (a clean tool/pipeline token is present). It is not
  a claim that all 8 *should* extract to a base pipeline: binder/liu_2013 name a tool inside a
  citation-deferred description, and poldrack/power name a *component tool* (FSL/FreeSurfer) inside
  an explicitly custom pipeline — for those, MISSING is defensible. High-confidence
  prompt-addressable: **4** (oconnor, weber — clean deterministic baselines; derosa, viduarre —
  proven extractable because the model succeeds on some runs).
- The K=15 flip rates share the variance caveat: N=15, magnitude uncharacterized. See
  [variance finding](variance.md).
- Measured on the batch_v6_full corpus; the classifier's aliases are built from `fmri_defaults_kb`
  (4 pipelines) plus a hand list of non-KB toolboxes, so a pipeline named by neither would read as
  NOT-A-MISS. Corpus-specific.

## Consequence

The lever for base_pipeline recall is the extractor's prompt/model, not the parser or the slice.
oconnor and weber are the clean experimental targets: deterministic 0/15 on explicit C-PAC usage,
so a prompt change scores against a fixed baseline. Any such experiment must be scored over K runs
(derosa/viduarre flip), or a nondeterministic gain will masquerade as signal.
