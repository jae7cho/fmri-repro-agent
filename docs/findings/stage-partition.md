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

---

## CORRECTION (2026-07-13)

The conclusion above — "STAGE-1 (pypdf) = 0; the frontend is not the bottleneck; the binding
constraint is stage-3 extraction" — is **wrong for the C-PAC papers (oconnor, weber)**, and by
extension the "prompt/model is the lever" consequence does not hold for them.

**What overturned it.** A later investigation captured the RAW model output (not the
post-processed four-state) and compared raw vs final. The model extracts C-PAC on **every** draw
(oconnor/weber `base_pipeline_name` EXTRACTED 20/20; derosa FSL 20/20). The final `MISSING_FROM_PAPER`
is introduced **downstream in post-processing**: the model emits a clean `verbatim_quote`, but
`resolve_quote()` cannot ground it against the pypdf-mangled source (oconnor's C-PAC appears as
`C-P A C` with run-together words and injected `[ 1]` markers), so `_build_base_pipeline` hard-drops
a correct EXTRACTED to MISSING.

**Why the original analysis missed it.** The classifier matched a *second, clean* C-PAC mention (the
"Software and availability" line) and declared the slice clean → "STAGE-3." But the model quotes the
*methods-body* mention, which is pypdf-mangled. So the loss is **span-resolution + stage-1 (pypdf
corruption)**, not stage-3 extraction.

**Corrected understanding.** For the C-PAC papers, base_pipeline recall is bottlenecked by span
resolution over corrupted source, not by the model or a prompt. Evidence and mechanism:
[adjudication-order-generalization.md](adjudication-order-generalization.md) (raw-vs-final) and
[span-resolution-hard-drop.md](span-resolution-hard-drop.md) (the corpus-wide blast radius). The
"STAGE-1 = 0" figure held only because the classifier tested a different mention than the one the
model quoted. The stage-3 reading remains correct for the referent-binding case (chen temporal), a
genuine model-side error.
