# Finding (Phase 1): the span-resolution hard-drop is corpus-wide, across 6 fields

**Harness:** `extractor_mvp/scripts/hard_drop_audit.py` · **Model (pinned):**
bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0, temp 0, N=1 over the 19-paper corpus.
Raw dump + per-drop JSONL: `extractor_mvp/results/HARD_DROP_AUDIT.md(.jsonl)` (gitignored).
Measurement only — `extractor.py` untouched; nothing committed. **Phase 2 (the fixes) NOT run;
this is the Phase-1 report the brief requires before any code change.**

## Headline: it is NOT base_pipeline-only

A silent drop = the model returned `status=extracted` with a value and a quote, but
`resolve_quote()` failed to ground the quote, so `_process_field` / `_build_base_pipeline`
relabeled it `MISSING_FROM_PAPER`. This snapshot:

- **10 silent drops across 6 papers and 6 different fields.**
- By field: `base_pipeline_name ×4, target_space ×2, resolution_mm ×1, target_surface ×1,
  intensity_convention ×1, temporal_standardization_method ×1`.
- base_pipeline is the plurality but **less than half**. The pathology is **corpus-wide**, and it
  fires in **both** builders — `_process_field` (the 6 targeted step fields) and
  `_build_base_pipeline`. So a fix must touch both, not just base_pipeline.
- Note `_process_field` at least records an `ExtractionDiagnostic(extraction_quote_unresolved:…)`;
  `_build_base_pipeline` drops **silently, with no diagnostic** — base_pipeline is the worst case.

**The drop SET has run-to-run variance.** A first N=1 run produced 9 drops; this one produced 10,
overlapping but not identical — because the model's *quote* varies run to run (see
[variance](variance.md)). The post-processing is deterministic given a quote; the quote is not. So
"10" is one draw; the stable claim is *multi-field, corpus-wide*, not the exact count.

## Why the quotes fail to resolve — hand-adjudicated (the automated buckets undercounted)

The script's auto-classifier is unreliable and I did not trust it: it missed real mangles because
pypdf renders the multiplication sign `×` as the literal string `/C2` (so `×` deletes to nothing in
the quote but survives as `c2` in the source), and because a canonical value like
`voxel_temporal_zscore` is never literally in a quote. I hand-checked every drop against the source.

**All 10 dropped quotes trace to real source content — none is a hallucination this snapshot.**
The failures are pypdf corruption the model silently repaired in its quote:

| artifact | example (source bytes → model's clean quote) |
|---|---|
| whitespace-deletion / shattered token | `ConfigurablePipelinefortheAnalysisofConnectomes`, `C-P A C` → "Configurable Pipeline … (C-PAC)" |
| unicode mangle | `3 /C2 3 /C2 3m m 3` → "3 × 3 × 3 mm3" (agtzidis) |
| line-break hyphenation | `us-\ning` → "using" |
| injected citation marker | `Connectomes [ 1] (C-P A C` , `[ 62]` |

`resolve_quote` already handles Unicode-NFKD and whitespace-*collapse* (runs→single space), but not
whitespace-*deletion* (words with zero space between them), the `×→/C2` mangle, or mid-quote markers
— which is why these still fail.

## The class that must NOT be blindly recovered (the real guard)

The hallucination guard the brief anticipated is nearly empty here, but a **different** dangerous
class appears — **value-mislocalization**: the quote is present, but it does **not state the value**;
the model *inferred* the value. Recovering the span would let an inference masquerade as a
paper-stated extraction.

- **viduarre_2017.base_pipeline_name = "HCP minimal preprocessing pipeline"**, quote = *"Spatial
  preprocessing was applied using the procedure described by Glasser et al. 40."* The value is NOT
  in the quote — the model expanded "Glasser et al." → HCP MPP. This drop is arguably **correct**
  (the paper defers; it does not name HCP MPP). Recovering it would be an over-claim. This is the
  case the value/quote check must catch.
- Contrast **liu_2013.base_pipeline_name = "FCP analysis scripts (version 1.1-beta …)"**: initially
  looked like a fabrication (full quote with a URL didn't match), but `FCP analysis scripts` and
  `1.1-beta` both ARE in the slice — a real sentence, just mangled. **Not** a hallucination.

So the hand-adjudicated split of the 10 drops:
- **Recoverable pypdf-mangle** (quote present, value supported by quote): ~7 — agtzidis target_space
  & resolution_mm, oconnor/weber base_pipeline, weber target_surface, liu_2013 base_pipeline, etc.
- **Value-mislocalization** (quote present but value inferred, not stated — do NOT recover): viduarre
  base_pipeline; and weaker cases (oconnor's quote carries the name but not the "(C-PAC)" acronym;
  derosa temporal cites an "activation patterns were standardized" sentence — a referent-binding
  question, not the BOLD signal).
- **Genuine hallucination** (quote content absent from source): **0 this snapshot.**

## What this means for Phase 2 (design consequences, not yet built)

1. **Corpus-wide, both builders.** Fix A (flag-don't-drop) must be applied to `_process_field` AND
   `_build_base_pipeline`, not scoped to base_pipeline.
2. **The guard is value-support, not just quote-presence.** "Keep EXTRACTED + `span_unresolved`"
   must fire only when the value is actually supported by the (mangled) quote. The viduarre class —
   quote present but value inferred — must stay MISSING/DEFERRED, or the honesty fix would convert
   an inference into a fabricated extraction. A pure "flag on span failure" that ignores
   value-support would re-introduce the very over-claim AESPA exists to prevent.
3. **Tolerant-resolve (Fix B) must handle whitespace-deletion, `×→/C2`, mid-quote markers, and
   hyphenation** — the four artifacts above — and must still fail closed on genuine absence. The
   three-arm regression (recovery with verified span text, zero spurious moves, hallucination guard)
   is required; the value-mislocalization cases are the sharpest test of the guard.

**STOP — Phase 1 reported. Phase 2 (Fix A then Fix B) awaits go-ahead; the blast radius (corpus-wide,
both builders, plus a value-support guard that is more than a hallucination check) reshapes both
fixes from the brief's base_pipeline-scoped framing.**
