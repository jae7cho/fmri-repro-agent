# PDF tool-citation glue produces false MISSINGs (misattributed as extraction failures)

**Finding (cole_2013, base_pipeline scoring, 2026-07-22).** The source text — as pypdf extracts it —
reads `AFNI48` / `Freesurfer49`: the tool name is fused to its citation superscript with no separator.
The model searched the right section (`fMRI preprocessing`), searched for "AFNI", and still returned
MISSING with no span attached — because it correctly did **not** recognize `AFNI48` as `AFNI`. This is
a **false MISSING on corrupted input**, not a model reasoning failure. In the Tier-A error
decomposition it must be attributed to the PDF→text layer, not the LLM.

## Same root cause, seen repeatedly this project

- **wheaton / `\bspm\b`** — SPM99 false-absence traced to surface-form corruption (the earlier session).
- **span mangling → tolerant recovery (tier 5, v0.4.0)** — the whole reason `span_resolver` needs a
  corrupted-source tolerant tier is pypdf whitespace-deletion / hyphenation / glyph mangles.
- **cole `AFNI48`** — citation-superscript glue, the newest variant.

These are all **PDF-extraction corruption**, upstream of the extractor.

## Why it matters (COBIDAS-relevant)

A meaningful fraction of apparent "extraction failures" may be **PDF→text failures, not LLM failures**.
On the scored base_pipeline set, of the 2 non-viduarre errors, **neither** is a model reasoning
failure: liu_2005 = slicing failure (`methods_not_found`), cole = PDF-glue failure. The
reproducibility bottleneck is partly in the **parsing plumbing**, not the extraction. Naming where
recovery effort should go: fixing the PDF layer may buy more than tuning extraction quality.

## Backlog

1. **Quantify corpus-wide** — how many MISSINGs are glue/mangle-caused vs genuine model misses? (Needs
   a deterministic sweep: for each MISSING base_pipeline, check whether a known tool token appears in
   the raw text glued to digits/punctuation.)
2. **Deglue/normalization pass before extraction** — split trailing citation digits from tool tokens
   (`AFNI48` → `AFNI 48`), repair hyphenation, at the `pdf_loader` boundary so the model sees clean
   surface forms. Weigh against the never-fuzzy invariant (must not merge distinct tokens).
3. This may be a **larger error source than LLM extraction quality** — measure before optimizing the
   model side.

Related: [`span-resolution-fix.md`](span-resolution-fix.md),
[`span-resolution-hard-drop.md`](span-resolution-hard-drop.md), the stage-partition's fourth class.
