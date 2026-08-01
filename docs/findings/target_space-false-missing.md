# target_space false-missing: the spec asserts absence for papers that stated "MNI"

**Finding (2026-07-31, surfaced while scoring target_space).** For 9 of the 18 audited papers the
extractor's SPEC records `spatial_normalization.target_space.extraction.status = MissingFromPaper` —
yet the paper explicitly **stated a bare MNI-family target** ("MNI", "MNI152", "MNI-152", "SPM MNI
template"). The core model is asserting **absence where there is presence**. That is a false provenance
claim inside the system whose entire thesis is distinguishing *absence* (nothing stated) from *presence*
(stated but under-specified, or deferred, or resolvable). This is a correctness defect in the core model,
distinct from — and more interesting than — any error rate.

## Mechanism

The synonym resolver classifies a bare "MNI"/"MNI152" as `value_not_in_literal:underspecified[MNI]` (it
matched the family but not a resolvable enum variant). `_process_field` then **relabels the field to
`MissingFromPaper`**, preserving the grabbed term as `raw_value` + `raw_quote` in the
`ExtractionDiagnostic`. So the paper's target survives in a *side channel* (the diagnostic), but the
field the rest of the system reads — `extraction.status` — says the paper stated nothing.

Affected (value_not_in_literal:underspecified[MNI], K=3-stable): agtzidis, chen, derosa, liu_2013,
oconnor, tang, vanderwal, weber, wheaton. (gordon/poldrack/power are `no_match`, a related but distinct
diagnostic.)

## Why it matters (it is AESPA failing at its own thesis)

`MissingFromPaper` is a load-bearing state: it is supposed to mean "the paper reported no target," which
is a *reproducibility fact* the whole project exists to measure. Here it instead means "the paper
reported a target I couldn't map to my enum." Conflating those two is exactly the absence/presence
confusion AESPA is built to prevent. The reporting layer papers over it — `generate_sfn_review.py` maps
`value_not_in_literal → Family-specified`, and `score_target_space.py` scores on the diagnostic, not the
status — but **the spec object itself is untrue**, and any consumer that reads `status` without the
diagnostic (a downstream tool, a second analysis, a future me) inherits the false claim.

Contrast the [specificity-flattening finding](extraction-specificity-flattening.md) (oconnor: a
resolvable file captured as bare "MNI"): that is a loss of *specificity within a captured value*. This is
a falsehood in the *status* — presence recorded as absence. Different defect, same root cause (the enum
has nowhere to put a family-level target, so the pipeline drops to MISSING).

## The design question (decide deliberately — do NOT default to the cheapest patch)

`TargetSpace` conflates two axes at once: **which space** (MNI152NLin6Asym, Talairach, native_volume) and
**how completely specified** (family-only, study_specific, native, deferred, absent). The false-missing
is a symptom of that conflation. Two fixes:

- **(A) Add a family-level enum value** (e.g. a bare `MNI152` / `MNI_family`). Honest *cheaply* under the
  additive-patch versioning convention — a bare "MNI" would extract as EXTRACTED+MNI_family instead of
  false-MISSING. But it **deepens the conflation**: one enum still carrying both axes, now with more
  values.
- **(B) Split completeness into its own field** (`target_space` = which space; a separate
  `target_space_completeness` = canonical/family/absent/deferred). Cleaner and structurally honest — it
  is the two-axis reality made explicit — but a **bigger** change (schema, prompt, resolver, scorer).

(B) is the honest structural fix; (A) is the tempting patch. This is worth an explicit decision, not a
default. **Not acted on here** — the defect is documented and the scorer reads the diagnostic so the
score is not corrupted; the fix is a deliberate design call for the author.

**Leaning: (B), and the scorer's own failure is the evidence.** The v1 scoring map (committed `7bca618`)
keyed on `status` and *could not express "named the family"* — it had to collapse those papers to
`absent`. That is the SAME conflation the enum has: a representation that carries only "which space" has
nowhere to put "how completely specified," so presence-without-a-variant becomes absence. The defect
reproduced itself one layer up, in the scorer. Splitting which-space (`target_space`) from
how-completely-specified (a `target_space_completeness` field) fixes both the spec's false-missing AND the
class of confusion that produced the v1 map — the same structural honesty, applied once. (A) would leave
the enum carrying both axes and would have to be *un-conflated* later anyway.

**SUPERSEDED (2026-07-31): neither (A) nor (B).** The defect is the field's TYPE (a closed `Literal`), not
its vocabulary — both options leave a closed vocabulary deciding recordability. The fix is **verbatim-always
typing** (the field always carries the verbatim term + an optional resolved identifier), making extraction
structurally incapable of the false-missing and making completeness *derived*, not stored (so (B) is moot).
See [`target_space-design-resolution.md`](target_space-design-resolution.md).

Related: [`extraction-specificity-flattening.md`](extraction-specificity-flattening.md);
`ground_truth/target_space_README.md` (the map correction + score).
