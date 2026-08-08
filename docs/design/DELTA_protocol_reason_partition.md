# DELTA — Reason-Partitioned Completeness in `to_protocol`

*Rendering-level refinement of `render.to_protocol` (design doc: `DESIGN_protocol_emitter.md`). No `fmri_repro` change; no `_display_state`/coupling change. Reuses `flatten()`.*

---

## Problem (verified against corpus)

The single "require your input" count conflates categorically different things. Chen's 12 gap fields:

| `LeftMissing.reason` | n (Chen) | What it actually means | Assigned at |
|---|---|---|---|
| `not_targeted_by_mvp` | 8 | Extractor doesn't attempt this field | `extractor.py:653` (`_IGNORE_REASON`, `batch.py:40`) |
| `not_stated_in_text` | 2 | Paper genuinely silent (absence) | `extractor.py:456` |
| `version_deferred_to_kb` | 1 | Version unreported (date-inference target) | KB path |
| `value_not_in_literal` | 1 | Paper *stated a value + quote*; unresolvable to controlled vocab | `extractor.py:474–487` |

So the honest source-gap count for Chen is **4, not 12** — 8 are extractor coverage, which `batch.py` already excludes from its own metrics. Reporting 12 as "paper is silent, you must specify" is the exact tool-coverage-vs-source-absence conflation a reviewer attacks, and `value_not_in_literal` is the COBIDAS controlled-vocabulary gap (Nichols et al. 2017), not an absence.

## The distinction is the contribution, made observable

`MISSING`-vs-`LEFT_MISSING` (my earlier framing) is a raw-status split with no display contrast. The observable distinction is the **`reason` partition** — and it's already on `FieldRow.left_missing_reason`, so this is rendering, not a schema/design change.

## Buckets (base reason via `reason.split(":",1)[0]`, to absorb suffixes)

- `not_reported`: `not_stated_in_text`, `no_base_pipeline_named`, `version_deferred_to_kb`
- `unmappable`: `value_not_in_literal`
- `not_covered`: `not_targeted_by_mvp`, `extraction_quote_unresolved`
- `unclassified`: any unknown reason (shown literally; **never** folded into a source bucket)

## Header (non-zero buckets only, fixed order)

`specified in source · inferred · deferred · not reported in source · reported but unmappable to controlled vocabulary · not covered by extractor · unclassified`

Chen → `5 specified in source · 3 not reported in source · 1 reported but unmappable to controlled vocabulary · 8 not covered by extractor`.

## Per-field line wording (MISSING/defensive-LEFT_MISSING rows)

Replace flat "REQUIRED — not reported…" with reason-specific text; `not_targeted_by_mvp` and `extraction_quote_unresolved` must **not** say "not reported in source" / "you must specify (paper silent)".

## Deferred (out of scope here)

Showing the free text behind `value_not_in_literal` — it lives in the `ExtractionDiagnostic` channel, not in `Preprocessing`, so `to_protocol` can label the bucket but not display the phrase until diagnostics are passed in. Also deferred: omitting `not_targeted` fields from the body (kept inline, labeled) — a later polish, not needed for the honest count.

*See the Claude Code prompt in chat (or below) for exact constants + tests.*
