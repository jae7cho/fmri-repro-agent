# extractor_mvp

The minimum viable end-to-end Methods Extractor: parsed paper **text in**, typed
**`ProvenancedField` values out** with character-offset spans into the source text.
Single-pipeline, single-pass. The floor that proves the grounding loop closes.

## Loop

1. `ParsedPaper(text=...)` — canonical text (pdftotext/pypdf output or manual slice).
2. One LLM call returns `(value, verbatim_quote)` per field (Instructor + LiteLLM, JSON mode).
3. `resolve_quote()` string-searches the quote in `text` → `Span(start, end)` — so the
   span literally contains the value (Tier-1-consistent by construction).
4. Each field becomes `Extracted(value, spans=[span], confidence=0.8)` if value validates
   AND quote resolves; otherwise `MissingFromPaper` with the reason on the coupled
   `LeftMissing` inference arm (+ a diagnostic). Spans are never fabricated.

## Deliberately deferred (post-abstract Methods Extractor thread)

PDF parsing / Marker, multi-acquisition partitioning (Fork C), `DeferredToCitation`
reasoning (Fork B), self-critique iteration (Fork D), cross-validation (Fork A),
confidence calibration, section/table/figure handling. `bandpass` is also skipped
for the MVP. If a field is unstated, the MVP returns `MissingFromPaper`, **not**
`DeferredToCitation` — note this limitation when citing.

## Run

```bash
python -m extractor_mvp.demo --text examples/schwartz_2018_methods.txt \
  --model bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0 --output results/schwartz_2018.json
```
