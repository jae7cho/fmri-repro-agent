# target_space design resolution: verbatim-always typing (kills false-missing), CALL 7 → inference, step-absence held

**Status: design decision (2026-07-31), implementation sequenced below.** Supersedes the A-vs-B question
in [`target_space-false-missing.md`](target_space-false-missing.md) and the "unreachable by construction /
third question" framing in [`target_space-call7-unreachable.md`](target_space-call7-unreachable.md). These
are correctness decisions; the record is here so the reasoning survives (the conversation is not the
artifact).

## 1. The false-missing is a TYPE problem, not a vocabulary one

`target_space` is typed as a **closed `Literal`**. Any term outside the enum cannot be stored, so the
extractor has **nowhere to put "MNI" except the diagnostic side channel** — and the primary field asserts
`MissingFromPaper` (absence) for a paper that stated a target (presence). Both prior options leave that
intact:
- **(A) add family-level members** carries vocabulary into the enum one term at a time.
- **(B) add a completeness field** adds a second field.

Both **leave a closed vocabulary deciding whether a paper's own words are recordable.** That is the defect.

## 2. Resolution: the field carries the verbatim term ALWAYS, plus an optional resolved identifier

- oconnor → verbatim `"FSL's MNI152T1_2mm_brain.nii.gz"`, resolved `MNI152NLin6Asym`.
- bare-MNI paper → verbatim `"MNI"`, resolved `None`.
- a novel template nobody has mapped → verbatim preserved, resolved `None` — **no data loss, no enum churn.**

**Recording never depends on resolution**, so extraction becomes *structurally incapable* of the
false-missing defect. Resolution is a separate, optional enrichment.

## 3. This kills (B): completeness is derived, not independent

Given the value, completeness is **determined**: resolved-to-a-specific-template → `canonical`;
unresolved-but-names-a-family → `family_specified`; nothing → `absent`. A stored completeness field would
be a **second copy of a fact the value already carries**, with the usual drift risk. **Derive it in the
reporting layer**, where the reframe already computes it.

## 4. It extends the scalability convention downward

The versioning convention made *adding vocabulary* a patch bump. This makes *recording* need **no
vocabulary change at all** — resolution stays a resolver concern, which is exactly where the oconnor fix
already lives (the synonym resolver). New templates never touch the schema.

## 5. Honest cost

Retyping a field is **structural under the project's own boundary rule** — a real migration with a
doc-transform, **not a patch bump**, and bigger than (A). It touches the schema root, the extraction
model, the resolver, migrations, the scorer, and the labels/mapping. **Justified by the correctness
defect:** the spec currently asserts absence where there is presence, in the system whose entire thesis is
that distinction.

## 6. CALL 7 is a DIFFERENT problem — the guard is right, do NOT weaken it

`native_volume` for binder/chen is **not an extraction at all.** Nothing is stated; the conclusion comes
from reading an enumerated pipeline and observing that it **terminates without a volumetric target** — an
**inference from structural completeness of the description.** So it belongs to the **inference layer**,
with its own basis (`enumerated_pipeline_complete`) and a **confidence ceiling**, alongside
`version_default` and the rest.

- **Extraction stays `MissingFromPaper`** — truthfully (no volumetric target was *stated*).
- **The resolved value is `native_volume` with a stated basis** (`enumerated_pipeline_complete`).
- **Scoring compares against the resolved value.**

The value-support guard (the fabrication firewall) keeps doing its job untouched. This **supersedes** the
"unreachable by construction" framing: CALL 7 native_volume was never unreachable — it was **mis-located
in the extraction layer**. Moving it to inference makes it reachable *and* keeps the guard. (The two leaks
that currently ride on those rows — chen cross-axis, binder results-space — remain genuine extraction
defects and would then score against the resolved `native_volume`.)

## 7. The larger gap underneath both — HELD until it recurs

ciric states: *"We did not apply slice timing correction during preprocessing, as recent data suggest that
the interpolation that occurs may artificially reduce motion estimates."* That is a **stated negative with
a rationale** — quotable, extractable, and **currently unrepresentable.** AESPA can express "field not
reported" but not **"step deliberately not performed"**, so a stated skip **collapses into the same state
as silence.** For reproduction those are opposite: one tells you exactly what to do, the other tells you
nothing. This is the **hallucination-vs-absence thesis at the step level** rather than the field level, and
it will hit every step where papers report deliberate omissions — **slice-timing and smoothing especially.**

**HELD:** one corpus instance (ciric) is not enough to design against. Wait until a step where it recurs
(motion or smoothing will show the shape), then design the step-absence representation against real
recurrence.

## Sequencing

| item | layer | kind | when |
|---|---|---|---|
| **verbatim-always typing** | schema/extraction/resolver | correctness (structural migration + doc-transform) | **now / next focused session** |
| **CALL 7 → inference** (`enumerated_pipeline_complete` basis + ceiling) | inference | correctness | **now / next** |
| **step-absence representation** ("deliberately not performed" ≠ silence) | schema (step level) | correctness, but design-when-validated | **HELD** until it recurs (motion/smoothing) |

The first two are correctness fixes to record and execute; each is a focused change (a Literal→struct
retype and an inference-basis wiring), not an end-of-session patch. The third is held on purpose.

Related: [`target_space-false-missing.md`](target_space-false-missing.md),
[`target_space-call7-unreachable.md`](target_space-call7-unreachable.md),
`ground_truth/target_space_README.md`.
