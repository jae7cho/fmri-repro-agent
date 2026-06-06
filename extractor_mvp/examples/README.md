# Example inputs — provenance

Provenance notes live here (not as headers inside the `.txt` files) so they
cannot pollute the extractor's text or be mistakenly "extracted" / span-matched.

## `schwartz_2018_methods.txt`
- Source: `tested_lit/Schwartz_2018.pdf` (the prompt's `.papers/Schwartz_2018.pdf`
  path was wrong; the PDF is under `tested_lit/`).
- Extracted with **pypdf** (the environment has no `pdftotext`/poppler), then
  **trimmed only** to the Methods section (no content hand-editing).
- Note: this paper's Methods are sparse on preprocessing parameters, so most MVP
  fields are expected to resolve to `MissingFromPaper` — a faithful real-paper case.

## `cho_2021_hcp_section.txt`
- Source: `Cho_2021.pdf`. **Contra the prompt's assumption, this PDF is NOT
  image-only** — it has a clean text layer, so this is a *real sliced excerpt*
  (the HCP data / preprocessing paragraph), not a hand-fabricated one.
- Manually sliced to one paragraph. **Fork C (multi-acquisition partitioning)
  will replace this manual slicing post-abstract.**
- Note: this paragraph *defers* the preprocessing description to prior
  publications ("the minimal preprocessing applied can be found in prior
  publications (Marcus 2013; Glasser 2013)"). That is a `DeferredToCitation`
  case; the MVP has no Deferred arm, so it correctly surfaces these as
  `MissingFromPaper` — illustrating exactly the limitation noted for the abstract
  (Fork B resolves it post-abstract).
