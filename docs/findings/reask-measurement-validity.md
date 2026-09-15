> **Moved from `extractor_mvp/results/MEASUREMENT_VALIDITY.md` on 2026-09-14.** That directory is ignored by a
> bare `*`, so this analysis had no tracked home and appears in no backup archive. Of 15 distinctive sentences here, **none** appears in any tracked file.
> The run artifacts it was computed from stay ignored — only the prose moved.

# Measurement validity — does the reask corrupt the four-state distribution?

Scope: a validity check on the numbers AESPA reports, not a partition finding. Question: does
instructor's `max_retries=2` (extractor.py:770) silently repair or alter first-draft model
outputs in a way that corrupts the EXTRACTED / MISSING_FROM_PAPER / value_not_in_literal /
DEFERRED distribution. Diagnostic only; nothing changed.

## Answer: no. The concern is discharged on two independent grounds.

### 1. Structural — an out-of-enum VALUE cannot trigger a reask (from source)

- The create() call: `client.chat.completions.create(model, messages, response_model=`
  `PreprocessingExtraction, temperature=0.0, max_retries=2)` — extractor.py:765-771. Client is
  `instructor.from_litellm(completion, mode=instructor.Mode.JSON)` (extractor.py:405).
- Installed **instructor 1.15.1**. In `core/retry.py::retry_sync`, a retry fires ONLY on
  `ValidationError | JSONDecodeError | InstructorValidationError`; API/network errors take a
  different branch. On a validation failure it calls `handle_reask_kwargs`, which for JSON mode
  (`providers/openai/utils.py::reask_md_json`) appends the model's failed message plus a user
  turn: *"Correct your JSON ONLY RESPONSE, based on the following errors:\n{exception}"*. So the
  reask is **feedback-driven, not a blind re-roll** — the model is told which field failed and
  can correct it. That is the mechanism that COULD coerce a signal.
- BUT the response schema does not expose enums to that mechanism. In
  `extractor_mvp/extraction_result.py`, every targeted field is a `FieldExtractionResult` whose
  **`value: str | None` is a free string** — not a `Literal`. The Literal / `value_not_in_literal`
  resolution happens in Python (`synonym_resolver.resolve_to_literal`) AFTER instructor returns.
  Therefore an out-of-enum pipeline/space string is accepted as a valid first-draft response and
  **cannot raise a pydantic error and cannot trigger a reask.** The thesis-critical failure mode
  — an enum reask silently converting a `value_not_in_literal` signal into a valid member — is
  structurally impossible via the value fields on this schema.
- What *could* still trigger a reask: a bad `status` / `target_kind` Literal, the
  `FieldExtractionResult.enforce_status_constraints` model_validator (extracted-without-quote,
  missing-with-value, deferred-without-ref), malformed JSON, or a missing required field. Those
  are structural-coherence reasks, not value-coercion reasks.

### 2. Empirical — zero reasks fire on the corpus anyway (RETRY_AUDIT.md)

Read-only instructor hooks (`completion:response`, `parse:error`) over the exact v6 corpus,
19 papers x N=5 = **95 extraction calls**, model pinned, temp 0, schema/prompt unchanged:

- **0 / 95 calls fired any reask.** Every call parsed cleanly on the first attempt (attempts=1).
- Enum-triggered reasks: **0**. Structural: **0**. Parse: **0**.
- COERCED: **0**. DROPPED: **0**.
- **No reported EXTRACTED or MISSING state owes itself to a reask.** `max_retries=2` is inert on
  this corpus: the four-state distribution AESPA reports is the model's first-draft answer, full
  stop. The run-to-run variance measured earlier (VARIANCE_FINDINGS.md — e.g. chen
  temporal_standardization 10/5) is genuine sampling nondeterminism in the single call, NOT a
  reask artifact.

## Residual risk (a note, not an action)

The reask path is a **latent** validity risk, currently dormant only because (a) values are free
strings and (b) first-draft JSON is well-formed at temp 0 on this corpus. Two changes would wake
it: tightening any response-model `value` to a `Literal`, or a corpus/model that yields malformed
first-draft JSON or status/quote-incoherent drafts. If that happens, a feedback-reask could flip a
four-state outcome without leaving a trace in the final object. The durable safeguard, if the
concern ever returns, is to log the first-draft response before the reask (the
`completion:response` hook already used here is sufficient) — captured as an option, NOT taken now.

## Verdict

Both the structure and the corpus say the reask is not corrupting the distribution. No change is
warranted. `max_retries=2` may stay as-is; the audit harness (`scripts/retry_audit.py`) is off by
default and can re-run this check if the schema or corpus changes.
