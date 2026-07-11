# ADR: LLM `value` fields stay free strings; `max_retries=2` is retained

Status: accepted (records existing design; no change made)
Date: 2026-07 (session finding)
Harness: `extractor_mvp/scripts/retry_audit.py` — off by default; re-run to re-validate.

## Context

The extraction call uses instructor with `max_retries=2` (extractor.py:770), Mode.JSON. Instructor
reask is **feedback-driven**: on a pydantic `ValidationError | JSONDecodeError`, it appends the
model's failed response plus a user turn *"Correct your JSON ONLY RESPONSE, based on the following
errors: {exception}"* and re-calls (instructor 1.15.1, `providers/openai/utils.py::reask_md_json`).
That mechanism could, in principle, coerce a first-draft signal into a different value on retry.

The worry: an enum reask silently converting a `value_not_in_literal` signal (a paper term that is
not an allowed member) into a valid enum member — turning an honest "the paper said something
off-vocabulary" into a fabricated EXTRACTED value, with no trace in the final object.

## Decision / finding

The worry does not apply on the current design, on two independent grounds:

1. **Structural.** In `extractor_mvp/extraction_result.py`, every response-model field is a
   `FieldExtractionResult` whose **`value` is `str | None` — a free string, not a `Literal`.** The
   Literal / `value_not_in_literal` resolution runs in Python (`synonym_resolver.resolve_to_literal`)
   *after* instructor returns. So an out-of-vocabulary value is a valid first-draft response: it
   cannot raise a pydantic error and cannot trigger a reask. The only reask triggers are a bad
   `status`/`target_kind` Literal, the `enforce_status_constraints` model_validator
   (extracted-without-quote, missing-with-value, deferred-without-ref), malformed JSON, or a missing
   required field — structural coherence, not value coercion.

2. **Empirical.** Read-only instructor hooks over the v6 corpus (19 papers × N=5 = 95 calls,
   pinned model, temp 0): **0/95 calls fired any reask.** COERCED 0, DROPPED 0. No reported
   EXTRACTED/MISSING state owes itself to a reask. Raw log:
   `extractor_mvp/results/RETRY_AUDIT.md` (gitignored).

Therefore: keep `value` as a free string at the LLM boundary (it is what protects the
`value_not_in_literal` signal), and retain `max_retries=2` (inert on this corpus; harmless).

## Consequence / residual risk

This safety is conditional. It would break if either (a) any response-model `value` were tightened
to a `Literal` — that would route off-vocabulary values through the coercing feedback-reask — or
(b) a corpus/model produced malformed or status-incoherent first drafts. If that happens, the
durable safeguard is to log the first-draft response before the reask (the same
`completion:response` hook the audit uses is sufficient). Captured as an option, **not** taken now.

## Note

This ADR records why the free-string boundary is load-bearing, not incidental. A future refactor
that "types the value fields properly" as enums would silently re-open the coercion path — hence
this record, so that change is made deliberately, if at all.
