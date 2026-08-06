# CALL 7 native_volume is unreachable by construction — the fabrication guard forbids an absence-evidenced conclusion

**RESOLVED (2026-07-31): "unreachable" was mis-diagnosis — it was mis-located in the EXTRACTION layer.**
native_volume here is an *inference from structural completeness* (the enumerated pipeline terminates with
no volumetric target), not an extraction. Route it to the **inference layer** with a basis
(`enumerated_pipeline_complete`) + confidence ceiling: extraction stays `MissingFromPaper` (truthful), the
resolved value is `native_volume` with a stated basis, scoring compares the resolved value, and the
value-support guard is untouched. So it is reachable *and* the firewall holds. The analysis below (why the
guard blocks it in the extraction layer) still stands as the reason it must NOT be forced through
extraction. See [`target_space-design-resolution.md`](target_space-design-resolution.md).

**DECISION (0.5.0 retype — basis NOT built).** The verbatim+resolved retype shipped (v0.5.0); the CALL 7
inference *basis* did not. `enumerated_pipeline_complete` was proposed as an inference basis at ceiling
0.75, then **dropped**: it changes no output — nothing produces the inference, because detecting
enumerated-pipeline-completeness is an unbuilt capability, so adding the enum value now is unused schema
(the same YAGNI test applied elsewhere). What is retained is the **decision, not the code**: a CALL 7
`native_volume` conclusion belongs to the **INFERENCE arm with a stated basis, never to extraction** — the
value-support guard correctly forbids it as an extraction (its evidence is the ABSENCE of a volumetric
step, which no quote can support), and routing it to extraction would breach the firewall the guard
enforces. So chen and binder remain **unreachable-but-active-leaks** under 0.5.0: the retype does NOT make
`native_volume` reachable (it fixes the false-*missing*, a different axis). Build the detection first, then
add the basis; the reasoning is preserved here for whoever does.

**Finding (2026-07-31).** Two of the 19 target_space labels — chen and binder, both `native_volume` — are
**unreachable by the extractor as built**, and not for a reason any map or enum change can fix. Their
`native_volume` is a **CALL 7** reading: no sentence states a volumetric target; the label is inferred from
the *terminal state of an enumerated pipeline* (binder 7(a): only derived SPMs go to Talairach, timeseries
stays native; chen 7(b): the timeseries exits to the surface). **The evidence is an absence** — no paper
writes "we did not normalize."

## Why the guard blocks it

The v0.4.0 **value-support guard** (`span_resolver.quote_supports_value`, shipped after viduarre) promotes a
model value to `EXTRACTED` only if the value is present in its own verbatim quote; otherwise it reclassifies
rather than fabricate (viduarre: a citation-only quote must not become a named pipeline). That guard is
**correct** — it is the fabrication firewall. But it also **structurally forbids any conclusion whose
evidence is the absence of a step**: there is no quote that supports "native_volume via CALL 7," because the
supporting fact is that a volumetric-normalization step *never appears*. The same capability that prevents
fabrication prevents this legitimate reading. That is an **architectural tension, not a map gap.**

## Why this is deeper than the false-missing (enum-gap) result

They look similar (a label the extractor can't emit) but are opposite in mechanism:

| | family_specified false-missing | CALL 7 native_volume |
|---|---|---|
| what happened | info **captured, then discarded** (term sat in the diagnostic) | **no info to capture** — the evidence is an absence |
| recoverable? | YES — key the scoring map on `failure_reason` (done, map v2) | NO — nothing was captured; the guard forbids inventing it |
| root | a lossy status representation | the fabrication guard vs an absence-evidenced conclusion |

The enum-gap turned out to be a scoring artifact. This one is real and irreducible with the current
architecture.

## The CALL 3 vs CALL 7 split

- **CALL 3 native_volume** (functional data *explicitly stated* kept in native/subject space) is quotable →
  extractable. The guard passes; the value has support.
- **CALL 7 native_volume** (inferred from the terminal state) is **not** quotable → unreachable.

On this corpus **both** native_volume labels (chen, binder) are CALL 7, so **2 of 19 labels are unreachable
by construction.** A CALL 3 native_volume paper would score fine; none is present.

## This reclassifies chen's error

chen is counted as a **cross-axis leak** (the extractor pulled the surface template's MNI frame into the
volumetric field). That is true and worth fixing on its own terms. But **with a perfect cross-axis firewall,
chen emits MISSING → absent, still wrong against `native_volume`.** So the cross-axis fix **buys no scoring
improvement on that row** — the CALL 7 unreachability is the binding constraint. Worth knowing before the
cross-axis fix is prioritized on the strength of the number.

## Neither design option reaches it — it is a third question

`target_space-false-missing.md` weighs (A) a family-level enum value vs (B) a separate completeness field.
Both address *which space* and *how completely specified*. **Neither reaches "no volumetric normalization
occurred"** — that is a third, orthogonal question, and it is where CALL 7 native_volume lives. A real fix
would have to license an absence-evidenced conclusion (enumerate the pipeline; if no volumetric step, emit
native_volume) **without reopening the fabrication hole the guard closed** — and those are the same
capability, which is why it is hard.

## Near-term answer (recommended)

**Score CALL 7 rows as capability-limited, not accuracy errors.** The scorer (`score_target_space.py`) now
tags `native_volume` errors as capability-limited and reports the split (accuracy errors vs
capability-limited), so a cited number does not charge the extractor for a conclusion it is architecturally
forbidden to reach. Both chen and binder are now scored capability-limited (2 of 19). binder's run
(2026-07-31) confirmed it live: `EXTRACTED Talairach` 3/3 — a **results-space leak** (CALL 7(a)), Talairach
pulled from the derived-map SPM sentence — so binder is capability-limited AND exhibits the leak; the
native_volume it *should* carry stays unreachable regardless.

**"Capability-limited" is a scoreability tag, NOT a "no defect" tag.** Both chen and binder are ACTIVE
model errors (leaks); they are scoreless here only because the *label* is unreachable. The leak is
corpus-independent — binder's results-space grab yields the WRONG SPACE on any paper whose results-space
differs from its preprocessing space. So the scorer reports two denominators (all-blind and reachable-only)
and marks the exclusion as post-hoc: if design (B) makes native_volume reachable, these two leaks start
counting as accuracy errors with no new defect introduced. Do not let the unreachable bucket absorb them.

Related: [`target_space-false-missing.md`](target_space-false-missing.md),
[`value-support-guard-substring-hole.md`](value-support-guard-substring-hole.md),
[`target_space-pending-runs.md`](target_space-pending-runs.md).
