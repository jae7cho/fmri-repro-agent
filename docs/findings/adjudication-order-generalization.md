# Finding: the generalization test HALTED — base_pipeline failures are post-processing, not model

**Harness:** `extractor_mvp/scripts/chen_fix_ab.py` (raw capture) + a raw-vs-final gap check.
**Model (pinned):** bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0, temp 0.
Raw dump: `extractor_mvp/results/GENERALIZE_AB.md` + `generalize_ab.jsonl` (gitignored).
No prompt change was made; `extractor.py` is at HEAD; nothing committed.

## Why it halted

The experiment was designed to test whether "produce the status-discriminating fact before
assigning status" generalizes to the `base_pipeline` field, in two shapes (false-positive on derosa,
false-negative on the C-PAC papers). **The baseline measurement invalidated the premise of both
before any prompt change was worth running:** on `base_pipeline`, the model is not the failing stage.

Capturing the RAW model output (not the post-processed four-state) shows the model extracts the
pipeline **every time**, and a raw-vs-final gap check shows post-processing then drops it:

| paper | RAW base_pipeline_name (model) | FINAL four-state | `resolve_quote(model_quote)` |
|---|---|---|---|
| oconnor_2017 | **EXTRACTED:C-PAC** 20/20 | MISSING | **None** |
| weber_2024 | **EXTRACTED:C-PAC** 20/20 | MISSING | **None** |
| derosa_2025 | **EXTRACTED:FSL suite (v5.0.10)** 20/20 | MISSING | **None** |

The demotion is mechanical: `_build_base_pipeline` (extractor.py) returns EXTRACTED **only if**
`resolve_quote(name_result.verbatim_quote, text).span is not None`; otherwise it falls through to
`MissingFromPaper`. The model's quote fails to resolve, so the correct extraction is discarded.

## Root cause: pypdf mangles the text, the model silently repairs it, the quote can't match

The slice the model receives is corrupted by pypdf. oconnor's C-PAC sentence in the slice bytes:

```
Next, data was processed us-\ningadevelopmentversionoftheopen-source,Nipype-based[ 62]
ConfigurablePipelinefortheAnalysisofConnectomes[ 1](C-P A C\nversion 0.4.0
```

Note `C-P A C` (shattered), `ConfigurablePipelinefortheAnalysisofConnectomes` (spaces collapsed),
`us-\ning` (hyphenation + linebreak), `[ 1]` (injected citation marker). The model **reads through
the mangling** and emits a clean `verbatim_quote` ("...Configurable Pipeline for the Analysis of
Connectomes (C-PAC)"). That clean quote is byte-absent from the mangled slice → `resolve_quote` →
None → base_pipeline dropped to MISSING. weber and derosa fail the same way (weber's quote is a
reflow not present verbatim; derosa's full quote with the trailing URL hits a `( http` spacing
mismatch).

## The three questions, answered honestly

1. **Does the false-positive shape transfer to derosa's base_pipeline? — N/A (premise false).**
   derosa is not a model over-extraction: the model stably extracts FSL 20/20 (RAW). The loss is
   span resolution. A subject-first prompt cannot change a decision the model already makes
   correctly, nor fix a post-processing drop. The population is not a model-side failure, so the
   hypothesis is untestable on it.

2. **Does a false-negative shape recover the C-PAC misses? — NULL by mechanism (uninformative).**
   The model already extracts C-PAC 20/20; it is not failing to "look." "Enumerate every pipeline
   before concluding absent" fixes nothing, because the model already found it and post-processing
   discarded it. No prompt that operates on the model's decision can move this number.

3. **Does either restructuring destabilize already-correct fields? — N/A.** No prompt change was
   made or warranted, so the cross-check was not run.

## This corrects `docs/findings/stage-partition.md`

That finding classified oconnor/weber as "STAGE-3 (clean token in slice, model returned MISSING)"
and concluded "STAGE-1 (pypdf) = 0; the frontend is not the bottleneck; the binding constraint is
stage-3 extraction." **That is wrong for the C-PAC papers.** The classifier matched a *second, clean*
mention (in oconnor's "Software and availability" section) and declared the slice clean — but the
model quotes the *methods-body* mention, which is pypdf-mangled (`C-P A C`), and the loss is span
resolution, not model extraction. So the base_pipeline recall gap on these papers is a **stage-1
(pypdf) + span-resolution** problem, not a stage-3 model problem. (The stage-partition K=15 "flip"
on derosa was likewise the final state flipping as span resolution intermittently succeeded, not the
model wavering — the model is stable at RAW EXTRACTED.)

## The actual lever (not a prompt change; not taken here)

base_pipeline recall on these papers is bottlenecked downstream of the model. Candidate fixes, in
order of leverage:
1. **Tolerant span matching** — normalize whitespace/hyphenation/injected-citation-markers on BOTH
   the quote and the text before matching in `resolve_quote`. This directly recovers oconnor/weber/
   derosa.
2. **Don't hard-drop an EXTRACTED name on span-resolution failure** — keep the model's value with a
   `span_unresolved` flag rather than converting to MISSING; the value is correct, only the offset
   is unproven.
3. **Repair pypdf mangling upstream** (de-hyphenation, space reconstruction) — the stage-1 root, but
   broader and riskier.

All three are post-processing / frontend changes. None is a `base_pipeline` prompt change, which is
why this experiment could not proceed as designed.

## Caveats

- RAW capture is one session (K=20 baseline). The RAW-EXTRACTED / FINAL-MISSING gap is the load-
  bearing observation and is mechanism-backed (the code path is deterministic given the quote), not
  rate-dependent.
- The prompt-restructuring principle itself is not disproven — it worked on chen's temporal field
  (see [temporal-firewall-fix](temporal-firewall-fix.md)) because that WAS a model-side
  over-extraction. It simply does not apply where the model is already correct and the loss is
  downstream. Testing generalization requires a second *model-side* failure population, which
  base_pipeline on this corpus does not provide.
