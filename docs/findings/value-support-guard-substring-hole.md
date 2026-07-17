# Bug: the v0.4.0 value-support guard is defeated by short pipeline names (substring hole)

**Severity:** fabrication guard hole in SHIPPED code (`extractor_mvp/span_resolver.quote_supports_value`,
introduced with the v0.4.0 value-support guard, commit `b396772`/`2560bb1`). **Latent** — needs a
tier-5-recovered `base_pipeline_name` span AND a short value — which is why the corpus never surfaced
it and the suites were green. Found as a side effect of the subject-validator corpus sweep (same bug
class as the validator's bare-`ICA` collision).

**The anecdote worth keeping (recorded while fresh, 2026-07-16).** A safety gate built for an INERT
component — the subject validator, which was measured and deliberately never wired — surfaced a live
fabrication hole in SHIPPED code it was not looking at: the v0.4.0 value-support guard, **defeated by
an author's own surname** (`ANTs ⊂ Avants`). The deterministic input-space enumeration that made the
validator's own limits cheap to falsify was the same instrument that found the production bug. One
generalizable lesson — *substring matching over whitespace-deleted text is unsafe for short names* —
now with two independent instances (the validator's bare-`ICA` collision and this guard).

## What it is

`quote_supports_value(value, quote)` is the firewall-clean check that gates the v0.4.0 base_pipeline
value-support guard: a tier-5-recovered pipeline name is promoted to `EXTRACTED` only if the model's
own value is present in its own quote; otherwise a citation-only ("…described by Glasser et al.")
quote is reclassified to `DeferredToCitation` instead of fabricating a name (the **viduarre** case).

The shipped implementation deleted all whitespace/hyphens and did a **raw substring** test. So a short
value matches *inside a longer word*, and the guard reports "supported" when the name is not there:

```
quote_supports_value("ANTs", "…the procedure described by Avants et al.") -> True   # ants ⊂ aVANTS
quote_supports_value("ANTs", "…participants were then scanned.")          -> True   # ants ⊂ participANTS
quote_supports_value("FIX",  "A fixation cross was presented…")           -> True   # fix ⊂ FIXation
```

The first is the whole failure: it is exactly the viduarre pattern — the model infers the pipeline
from a citation and quotes only the attribution — but with a short name (`ANTs`) the guard is
**defeated by the author's own surname** (Avants), does not fire, and emits a fabricated `EXTRACTED`
`base_pipeline = "ANTs"`. viduarre itself only stayed safe because "HCP minimal preprocessing pipeline"
is long enough not to collide. `FIX ⊂ fixation` is the same class in a corpus where "fixation cross"
appears in a large fraction of methods sections.

## The fix

Match on **whole-token boundaries**, not raw substring. Tokenize the NFKD+lowercased quote into
alphanumeric runs; a value is supported iff its alphanumeric core equals a **contiguous concatenation
of ≥1 whole tokens**. This keeps the surface-mangling tolerance the guard needs (hyphen/space mangling
that splits `C-PAC` into `c pac`, or `fMRI Prep`, still matches via token concatenation) while
forbidding mid-word matches (`ants` is not a whole-token run of `avants`/`participants`).

Behavior after the fix (regression-pinned in `tests/test_span_resolver_tolerant.py`):

| case | before | after |
|---|---|---|
| `ANTs` in "…described by Avants et al." | True (bug) | **False** |
| `ANTs` in "…participants were scanned" | True (bug) | **False** |
| `FIX` in "…fixation cross…" | True (bug) | **False** |
| `fMRIPrep` in "…followed fMRIPrep (Esteban 2019)" | True | True |
| `C-PAC` in "…(C-PAC) was used" | True | True |
| `fMRIPrep` in "…fMRI Prep…" (mangled) | True | True |
| `HCP minimal preprocessing pipeline` in "…Glasser et al." (viduarre) | False | False |

## Blast radius — verified no regression on the real population

`quote_supports_value` is called ONLY on tier-5-recovered `base_pipeline` spans
(`if (not recovered) or quote_supports_value(...)` short-circuits on clean matches), so its entire
production population is v0.4.0's recovered base_pipeline keeps. A stricter matcher can only move a
keep True→False (silently regressing an `EXTRACTED` to a deferral). Replayed old-vs-new over the
recorded population (`results/HARD_DROP_AUDIT.jsonl`, base_pipeline rows — 0 model calls):

| paper | value | old | new |
|---|---|---|---|
| liu_2013 | "FCP analysis scripts …" | True | **True** |
| oconnor_2017 | "…Connectomes (C-PAC)" (markers `[1]`,`[63]` around it) | True | **True** |
| weber_2024 | "C-PAC" | True | **True** |
| derosa_2025 | "FSL suite (version 5.0.10)" (parenthetical + URL-adjacent mangle) | True | **True** (via the `FSL suite` variant) |
| viduarre_2017 | "HCP minimal preprocessing pipeline" (citation-only) | False | **False** (intended deferral) |

No keep flipped. Pinned in `test_recovered_base_pipeline_keeps_unregressed`.

**Docs-of-record disagree on derosa's base_pipeline, and it is recorded here.** `HARD_DROP_AUDIT.jsonl`
(the hard-drop run) has derosa dropping only `target_space` + `temporal_standardization` — base_pipeline
did NOT drop that run. `adjudication-order-generalization.md` (a later run, the one that specified this
fix) has `derosa.base_pipeline` RAW-EXTRACTED 20/20 → FINAL MISSING (a recovered drop). Different runs
of a non-stationary field; both cannot be a stable count. The complete `quote_supports_value`
population is therefore **5 papers** (not 4) — derosa's recorded `(value, quote)` pairs
(`results/generalize_ab.jsonl`, `chen_fix_ab.jsonl`) were replayed old-vs-new and all hold True→True.

**Known limitation (accepted).** A citation marker interleaved *inside* an acronym — `C-P [1] A C` →
tokens `[c,p,1,a,c]` — now flips True→False vs the old marker-deleting matcher, because token-concat
cannot bridge the `[1]` token. It does **not** occur in the recorded population, and it errs toward
**deferral** (the safe direction: a recall loss, never a fabrication). Stripping citation markers
before tokenizing would restore it, but the marker-vs-content distinction (`[62]` vs a `0.4.0`
version) is not free, and no corpus case needs it.

## Lesson (applies in two places)

**Substring matching on whitespace-deleted text is unsafe for short names.** The same bug produced the
subject-validator's bare-`ICA` collision (`ica ⊂ anatomical`); see
[subject-validator](subject-validator.md). Both are now token-boundary matches. Any future
"tolerant" name/value matcher must match on token boundaries, not raw substring — pin it with a
short-name-inside-a-longer-word regression test.
