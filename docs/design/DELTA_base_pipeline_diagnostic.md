# DELTA — `_build_base_pipeline` cannot say why it failed

*Refinement of `extractor._build_base_pipeline` (`extractor_mvp/src/extractor_mvp/extractor.py:684-800`).
Follows the supersession in `docs/findings/span-resolution-hard-drop.md` and its 2026-09-30
correction, which named the missing diagnostic channel as the residue. **Nothing here is implemented.**
§4 was ruled by the author on 2026-10-01: **Arm 1**, with the blocking condition in §4a verified and
now part of this change. Drafted 2026-09-30, ruled and revised 2026-10-01; every locator verified at
HEAD `28b9d35`.*

---

## 0. Four premise corrections, before anything else

The brief this document was written against asserted several things the code contradicts. Each is
recorded here rather than silently worked around. Two make the change *smaller*; one (§4a) makes it
considerably larger.

1. **Two conditions collapse, not two — it is three.** Case C (quote grounded, value unsupported,
   not citation-shaped) also returns the identical bare `MissingFromPaper`. §2.
2. **The repo defines what `MISSING_FROM_PAPER` asserts — more than once, and incompatibly.** It
   was expected that it might never say. Three sources say something and two of them disagree: the
   frozen spec defines it *tool-side*, the emitter design doc defines it *paper-side*. That split is
   the fork's real shape, and an earlier draft of this document asserted only the paper-side half.
   §4.
3. **The headline wording needs no new plumbing.** It was expected that a reason alone would leave
   case C printing the wrong line. It does not: `_protocol_main` already routes that line through
   `_reason_detail`, so a different reason prints a different line automatically. §6 — and this is
   the main respect in which the Software-row precedent does *not* carry over.
4. **Case A is not homogeneous.** A *deferred ref* whose sentence fails to ground also falls into the
   bare-missing return, so a tool-side failure already hides inside the condition that reads as "the
   model said nothing". §2.

---

## 1. Scope, and what this is not

**The justification is a correctness defect in author-facing output.** In case C
(`extractor.py:753` false, then `:773` false) the model named a pipeline, the quote *grounded*
against the paper, and the value simply was not in that quote. The report then prints:

```
Base pipeline: no base pipeline named in source — you must specify
```

That is a false statement about the manuscript. The paper named something; the tool declined to
trust it. Saying "no base pipeline named in source" asserts an absence that was never measured —
the absence-versus-failure conflation this project exists to name, committed by the project, in the
sentence a replicator reads. Case B (quote did not ground at all) prints the same false line.

**What this is NOT: a way to read the five committed papers.** `batch_a1_acceptance` has five papers
whose `base_pipeline` is `MISSING_FROM_PAPER` — binder_1999, cole_2013, liu_2005, poldrack_2015,
power_2014 — and the 2026-09-30 correction records the bound: the missing diagnostic hides the true
state of **up to 5 of 19**. Those JSONs were written by code that carried no reason, so **no change
to the builder makes them readable.** Reading them requires a paid re-extraction, and a re-extraction
re-extracts `target_space` on a model this project has *measured* as non-stationary — braun moved
correct→error between vintages at an identical pin, taking the blind rate 11/17 → 10/17
(`ground_truth/target_space_README.md`, `docs/findings/target_space-0.5.0-reextraction-prereg.md`).
**That re-extraction is GATED and is not decided here.** This delta buys correct output on the next
paper processed, not retrospective insight into the nineteen.

Also out of scope: the `span_recovered` marker having no downstream consumer (a separate Phase-2
gap), and anything touching `_process_field`, which already behaves correctly (§4, A2).

**Scope growth, recorded as a decision rather than discovered later.** This began as a cheap
diagnostic fix needing no re-extraction. Verification (§4a) established that it is also a change to the
Software row's coverage semantics, reaching up to 14 of 19 papers on this project's only unconditional
citable COBIDAS claim, 31 days from freeze. That is growth by legitimate discovery, not drift — each
step was forced by a measurement, and §4b computes the effect rather than leaving it to be met in late
October. **Ruled 2026-10-01: proceed.** The warrant is §4b's bound: the citable claim's
confirmed-correct core is 7 of 19 and survives every admissible outcome, and the likely effect is one
paper.

---

## 2. The three collapsing conditions

One `return` statement, `extractor.py:794-800`, reached by three distinct conditions:

| | condition | locator | discriminator in scope at the return |
|---|---|---|---|
| **A** | the `:749` guard not entered — no name, or no value, or no quote | `:749` false | `name_result.status` / `.value` / `.verbatim_quote`; **`name_res` never bound** |
| **B** | name extracted, quote did not ground | `:751` false; comment `:786` | `name_res.failure_reason == "quote_not_found"` (or `"quote_ambiguous"`) |
| **C** | name extracted, quote grounded, value unsupported, `_parse_attribution_ref` → `None` | `:753` false then `:773` false | `name_res.failure_reason is None`, span set, value unsupported |

**A fourth route, inside case A.** `:714-718` resolves a deferred ref's sentence and only builds
`deferred_pipeline_field` when that span is not `None`. So a model that *correctly* reported a
deferral, whose deferring sentence the resolver could not ground, leaves `deferred_pipeline_field`
as `None`, skips `:790`, and lands at `:794` — printing "no base pipeline named in source" about a
paper that named a citation. Case A therefore mixes a genuine absence with a second tool failure,
and the implementation must decide whether that route gets its own reason or shares case B's. This
document does not choose; it records that the condition is not what its name suggests.

**Demonstrated, not asserted.** Driving `_build_base_pipeline` directly with constructed
`FieldExtractionResult` inputs (no model call), A, B and C all return

```
MissingFromPaper{status: MISSING_FROM_PAPER, searched_terms: ['base pipeline'],
                 sections_searched: ['full_text']}      deferral_record = False
```

— byte-identical across all three.

**The collapse is specific, per two controls.** D (name extracted, quote grounded, value supported)
returns `ProvenancedField` / `Extracted[PipelineRef]` with `inference = NOT_APPLICABLE`. E (value
unsupported but quote citation-shaped) returns `ProvenancedField` / `DeferredToCitation` with
`LeftMissing(reason="citation_shaped_name_value_unsupported")`. So the three-way collapse is a
property of the bare-missing path, not of the harness.

**The failure information is not lost.** `SpanResolution` carries `failure_reason`
(`span_resolver.py:162`) and `_build_base_pipeline` binds the whole object at `:750`. Nothing is
swallowed upstream; the value is in local scope at the return and never read.

---

## 3. The carrier problem

`MissingFromPaper` has no reason field — `status`, `searched_terms`, `sections_searched`, and nothing
else (`src/fmri_repro/spec/provenance.py:59-62`). It also has **no docstring**, unlike its siblings
`Deferral` (`:66`) and `DeferredToCitation` (`:74`). The reason is stamped by the *caller*, as a
constant, at `extractor.py:863-867`:

```python
if isinstance(base_pipeline, MissingFromPaper):
    base_pipeline_field = ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=base_pipeline,
        inference=LeftMissing(reason="no_base_pipeline_named"),
    )
```

So there is nowhere at `:794` to write a reason. **The minimal change is to the return contract**,
and the shape is already in the function: return the wrapped `ProvenancedField` carrying its own
`LeftMissing(reason=…)`, exactly as the two sibling gap branches do at `:785` and `:791`. The
caller's `isinstance(..., MissingFromPaper)` branch at `:863` then narrows to case A, or disappears.

**This is documented convention, not a discovery.** The module docstring states both halves —
`extractor.py:5-8`: a field "is ``MissingFromPaper`` with the reason recorded on the ``LeftMissing``
inference arm and (for non-trivial failures) in the diagnostics list"; and `:10-12`, under *Spec
note*: "``MissingFromPaper`` carries ``searched_terms`` / ``sections_searched`` (no ``reason``
field), so the per-field reason string lives on the coupled ``LeftMissing(reason=...)`` inference
arm." `_build_base_pipeline` is the one builder that does not follow it — it neither records a
per-failure reason nor emits a diagnostic.

Two implementation facts the design must carry:

- **`name_res` needs hoisting.** It is bound at `:750` inside the `if` at `:749`, so it does not
  exist on the case-A path. Any implementation must initialise it before the guard and tolerate the
  unbound/`None` case. This is a local-variable change, not new plumbing.
- **Adding `reason` to `MissingFromPaper` is the alternative, and it is a shared-spec change** in
  `src/fmri_repro/spec/provenance.py`, which `fmri_repro` owns and `render.py:13` treats as a frozen
  contract. Named here so the cheaper option is a choice rather than an oversight.

---

## 4. THE FORK — RULED 2026-10-01: Arm 1

### What `MISSING_FROM_PAPER` asserts, per the repo

Searched for a *definition* rather than a usage. The governing sentence is
`docs/design/DESIGN_protocol_emitter.md:95`:

> The `MISSING` vs `LEFT_MISSING` split is preserved deliberately: `MISSING` = paper didn't state
> it; `LEFT_MISSING` = paper didn't state it **and** the Configurator could not infer a default (no
> KB coverage, or the honesty ceiling refused). Same action ("you must specify"), different
> epistemic reason — that difference is the contribution.

Corroborating, same file `:91`, the rendering contract: `{param}: REQUIRED — not reported in source;
you must specify`. And `DESIGN_methods_finder.md:23`:

> **A false `MISSING_FROM_PAPER` is invisible to every honesty mechanism in AESPA** — the four-state
> model, reason partitioning, confidence ceilings and provenance chains all presuppose the extractor
> saw what was there.

A state that can be *false* is a claim about the world.

**But the frozen spec defines it the other way, and that is the fork.** `provenance.py:76`, inside
`DeferredToCitation`'s docstring — the state is defined by contrast, in a sibling class, which is why
it is easy to miss:

> Distinct from MISSING_FROM_PAPER (which means "we looked and found nothing"): here the paper
> *names* a citation.

"We looked and found nothing" is a statement about the **search**, not about the manuscript. A search
that looked and found nothing covers a quote that would not ground — the tool looked and came back
empty-handed. On the spec's definition, cases B and C belong under `MISSING_FROM_PAPER`. On
`DESIGN_protocol_emitter.md:95`'s definition, they do not.

A third source sides with the spec. `extractor.py:5-8`:

> A field is ``Extracted`` only when its value validates AND its quote resolves; otherwise it is
> ``MissingFromPaper`` with the reason recorded on the ``LeftMissing`` inference arm and (for
> non-trivial failures) in the diagnostics list.

That is the extraction-side reading stated as the module's contract: *quote does not resolve →
MissingFromPaper + reason*. It is also, verbatim, the design of Arm 1.

**So: two docs-of-record disagree, and the count is 2–1 for the tool-side reading** — the frozen spec
(`provenance.py:76`) and the extractor's own contract (`extractor.py:5-8`) against the emitter design
doc (`DESIGN_protocol_emitter.md:91`, `:95`). The class `MissingFromPaper` itself carries no
docstring (`provenance.py:59-62`), so the authoritative-looking location is silent and the definitions
live in a sibling's docstring and a module header. **This document does not pick between them.** Which
governs is the ruling in §4, and the disagreement is itself a defect worth recording separately:
whichever arm is chosen, one of these three sentences becomes wrong and should be amended rather than
left to be found again.

### Arm 1 — reason string only

B and C stay `MISSING_FROM_PAPER`, carrying distinct reasons; the render reads the reason. Cheapest;
no schema change; no frozen-boundary contact.

**For it — the precedent is shipped, and it is this exact shape.** `_process_field` already records a
tool-side failure under a `MISSING_FROM_PAPER` extraction arm. Demonstrated by driving it: a step
field whose quote does not ground returns `extraction = MissingFromPaper`,
`inference = LeftMissing(reason="extraction_quote_unresolved:quote_not_found")`, plus an
`ExtractionDiagnostic` (`extractor.py:546-568`; `_missing_pf` at `:440-445`). `_REASON_LINE:477`
renders it as *"value present in source but span unresolved (extractor limitation)"* — which names
the tool explicitly. Two further tool-side reasons live the same way:
`extraction_quote_missing` (`:548`, `_REASON_LINE:487-490`) and `deferral_quote_unresolved`
(`_REASON_LINE:491-494`), and `render.py:482-485` states their semantics outright:

> These three fire BEFORE (or instead of) quote validation, so nothing has confirmed the value is
> grounded in the source. They therefore describe what the EXTRACTOR did, and assert nothing about
> what the manuscript reports.

On that reading `base_pipeline` is the *inconsistent* path, and Arm 1 makes it match everything else.

**And base_pipeline is not the only offender in its own file.** `_build_version_pf`
(`extractor.py:640-681`) has a single MISSING return at `:677-681` reached by three conditions —
version absent, version quote unresolved, version value unsupported by its quote — all stamped
`version_deferred_to_kb`, which renders "version not reported in source — you must specify"
(`_REASON_LINE:472`). The same collapse, one function earlier, on a field that is the subject of this
project's one unconditional COBIDAS claim. **Not out of scope — it has its own item at §10**, by
ruling, so that "out of scope" does not become "not recorded".

**Against it.** The comment at `render.py:482-485` is a claim about three *reasons*; the state they
sit under is still the one `DESIGN_protocol_emitter.md:95` defines as "paper didn't state it". Arm 1
therefore extends an existing conflation rather than introducing one — recording a tool failure under
a state defined as a claim about the manuscript. That the project already does this everywhere is
either the strongest argument for Arm 1 or the clearest statement of a defect with four more
instances, and which it is is the fork.

### Arm 2 — a state or marker for "could not determine"

Honest about what is known: the tool did not establish absence, and says so in the state rather than
in a reason attached to the wrong state.

**Against it.** It touches the frozen provenance boundary in `src/fmri_repro/spec/provenance.py`.
`DESIGN_protocol_emitter.md:41` records `render.py:13` as the frozen contract's consumer-side line
and keeps changes off `fmri_repro` deliberately. A7 already records that boundary as a problem via
`Deferral.target_kind`, which `_build_base_pipeline:725-726` has to work around in shipped code:

```python
# provenance.Deferral.target_kind has no "supplement" (FROZEN) -> map to "paper".
tk = "paper" if ref_result.target_kind == "supplement" else ref_result.target_kind
```

So the cost of touching that boundary is known and non-trivial, and a second lossy workaround is the
alternative to paying it.

**For it — the repo already calls this exact path a defect, and an open one.**
`docs/findings/target_space-false-missing.md:13-18` separates the two false-missing routes and
records that only one was closed:

> the retype closes the `value_not_in_literal` path to false-missing (demonstrated); the
> `quote_not_found` path remains open.

`quote_not_found` → `MISSING_FROM_PAPER` is case B. A findings document of record therefore already
classifies the state Arm 1 would formalise as a **false missing**. That is the strongest single piece
of evidence for Arm 2, and it sits in tension with the spec's own "we looked and found nothing".

**A2's precedent is evidence, not a decision.** That a tool-side reason already sits under a MISSING
arm settles what the codebase *does*; it does not settle what it *should*.

### Ruling, 2026-10-01 — Arm 1, and NOT on the document count

**The 2–1 split did not decide it.** Docs-of-record disagreeing is not settled by majority; three
sentences in conflict means one of them is wrong, not that two outvote one.

**The reason is that case B is irreducibly ambiguous.** `quote_not_found` means *either* the sentence
is not in the paper — the model fabricated it — *or* the resolver cannot find one that is: the
`×`→`/C2` class that `span_resolver.py:16-20` documents as deliberately unhandled. **Nothing at that
site distinguishes the two.** A "could not determine" state would assert that we know the failure was
the tool's, and we do not. That is a determination the evidence does not support, encoded in the
schema. **Arm 2 buys honesty about case C by inventing certainty about case B.**

**Arm 1's weakness is real, and the remedy is the render, not the state.** The false thing is the
*sentence*, not the record. `MISSING_FROM_PAPER` under the spec's own "we looked and found nothing"
is an accurate record of what happened; "no base pipeline named in source" is not an accurate
sentence about the paper. So the fix is wholly in the reason and the wording it selects.

**One reconciliation ships with this change, not after it.**
`docs/findings/target_space-false-missing.md:17-18` records "the `quote_not_found` path remains open"
as a false-missing. Under this ruling that path is *not* a false record — it is a correct record with
a false rendering, and the finding should say so once the `_REASON_LINE` entry lands. **Amending that
sentence is part of this change.** Leaving it would keep a findings document of record asserting a
defect the ruling has reclassified.

---

## 4a. BLOCKING CONDITION — verified at HEAD, and it holds

The ruling was issued conditional on this, reasoning from the ratified Software-row DELTA rather than
from HEAD. **Checked at HEAD, and it holds — worse than stated.**

`_software_coverage` (`cobidas.py:142-191`, read whole) ends:

```python
if version_extraction_status is not None:
    return version_extraction_status == "EXTRACTED", True
return base_row.extraction_status == "EXTRACTED", True
```

A case B/C base_pipeline is `MISSING_FROM_PAPER` and resolves no `PipelineRef`, so no version row
exists and `:191` governs: `addressed = False`, `covered = True`. The Software section is emitted iff
`covered ∧ ¬addressed` (`DELTA_software_row_deferral.md` §5), so it **is** emitted.

**Demonstrated on committed data, and the demonstration needs no new fixture.** Because A, B and C are
byte-identical in the record (§2), any of the five committed missing-base papers *is* a case-B/C
record. Rendering poldrack_2015 at HEAD:

```
  Assessed by AESPA: 2  →  addressed 1 · not reported 1 (incl. Software — unconditional violation)
  ...
  ### Not reported (mandatory, unconditional)
  - Software: version and revision number NOT REPORTED — COBIDAS D.3 requires this for each
    software used. (No software named in the source. Name the software, and give its version
    and revision number.)
```

So the consequence is **two** false statements and one false citable claim, not one:

1. The paper is counted an **unconditional COBIDAS violation** in the completeness header — and the
   header's own parenthetical calls the Software row "the one unconditional, citable COBIDAS claim
   here". The project's single citable finding, generated by a resolver failure.
2. The parenthetical asserts **"No software named in the source"** — false for case C outright, and
   unverified for case B. It is produced because `_base_pipeline_name(pre)` returns `None`
   (confirmed: `None` for poldrack_2015), which selects the unnamed-case variant at
   `render.py:793-805`.

**This is A3's defect with the cause moved one layer down**, exactly as predicted. `c9c2951` found the
report accusing a citing paper of an unconditional violation; here the accusation is produced by the
span resolver instead of by a deferral.

**The reason alone does NOT fix it.** `_software_coverage` reads `base_row.left_missing_reason` only
to test `_UNTARGETED_REASON` (`cobidas.py:187`); `:191` reads the *status*. So renaming the reason
leaves `addressed`/`covered` untouched and the section still emitted with the same sentence. **The
coverage consequence must be addressed in the same change** — the same ruling the Software-row DELTA
made when the predicate alone emitted the wrong sentence.

**Both sites have the reason already in scope, so no new plumbing.** `base_row` is a `FieldRow`
carrying `left_missing_reason` — `cobidas.py:187` already reads it — and `to_cobidas_coverage` holds
`rows` from `flatten` (`render.py:739`), so the violation-line builder can read the base_pipeline
row's reason the way `DELTA_software_row_deferral.md` §8 had it read `deferral_refs`.

### Ruled 2026-10-01 — `covered = False`, SCOPED to the unverifiable conditions only

**The warrant is `cobidas.py:176-183`'s own reasoning, applied one field over.** That passage refuses
to turn `NotApplicable` into a violation because the value cannot distinguish its two meanings, so the
tool cannot say what the paper reported, and silence is the honest output. Cases B and C are exactly
that shape: the extractor looked, found something, and could not verify it.

| condition | `covered` | consequence |
|---|---|---|
| **A** — nothing returned at all | **`True`** (unchanged) | genuine "we looked and found nothing"; violation stays, and it is true |
| **B** — quote did not ground | **`False`** | row goes silent; the tool cannot say what the paper reported |
| **C** — quote grounded, value unsupported | **`False`** | same |
| **4th** — deferral sentence did not ground | **`False`** | same; the model reported a deferral the tool could not verify |

**The split is only possible because the reason lands.** `_software_coverage` cannot distinguish these
today — it reads the *status* at `:191` — so the diagnostic's payoff arrives in the coverage layer, not
only in the render. That is the strongest single argument for doing the reason work at all.

### The new collapse this creates — do not let it in silently

`covered = False` routes the Software row into the **"Not assessed by AESPA"** bucket, which today
means one thing and would then mean two. Measured on poldrack_2015:

| | today | under the ruling |
|---|---|---|
| Assessed by AESPA | 2 | **1** |
| Not assessed by AESPA | 12 | **13** |

and the header's own explanatory sentence becomes false, verbatim at HEAD:

> (The 'not assessed' count is a TOOL gap — the extractor targets fields on only a few rows — not a
> statement about the paper. Silence on the rest is not measurable from text. **The one unconditional,
> citable COBIDAS claim here is the Software row.**)

Two falsehoods, not one. "the extractor targets fields on only a few rows" is false of Software, which
*was* targeted and came back unverifiable — a different fact. And the final clause names a citable
claim the paper no longer has. **This is the project's signature defect appearing inside the fix for
it: two facts in one bucket under a header describing only the first** — the third occurrence of that
pattern, and the second time inside a remedy for the first.

**REQUIRED, ruled 2026-10-01: a third count. Accepting the collapse is not an option.**

    assessed · not assessed (never targeted) · targeted but unverifiable

These are **three facts the tool can distinguish** — targeting is a code property, verifiability is a
per-paper outcome, and absence is neither. Collapsing distinguishable facts into one bucket under a
header describing only one of them is the defect this project exists to name. **Accepting it in
writing, inside the fix for the same defect, would be worse than the original instance: inherited
becomes documented.** An inherited collapse is a bug; a documented one is a position.

The third count also repairs the citable-claim clause on its own: a paper whose Software row is
targeted-but-unverifiable has no unconditional claim, and the header must stop saying it does.

---

## 4b. Corpus effect, computed before building

Asked for before implementation, and the headline is that **a point estimate is not computable from
committed data** — for the same reason the fix exists. Which mechanism produced each `MISSING` is
exactly what the record does not say. So: bounds, with every narrowing named.

**Today: 16 of 19 papers emit the unconditional Software violation.** Decomposed by what decides it:

| population | n | fate under the ruling |
|---|---|---|
| version arm `EXTRACTED` — derosa, liu_2013, oconnor | 3 | addressed; no section today, unchanged |
| base arm `DEFERRED_TO_CITATION` — braun, viduarre | 2 | **stays** — verifiable, and intended per the ratified Software DELTA |
| version arm `MISSING`, **fused SPM version** | **5** | **stays, and the violation is TRUE** — see below |
| version arm `MISSING`, no fused version — chen, ciric, vanderwal, weber | 4 | unknown; no discriminator exists |
| base arm `MISSING` — binder, cole, liu_2005, poldrack, power | 5 | unknown; the sentinel narrows it |

**The five fused-SPM papers are not at risk, and establishing that moved the ceiling from 14 to 9.**
agtzidis `SPM12`, gordon `SPM8`, mueller `Statistical Parametric Mapping 12`, tang `SPM12`, wheaton
`SPM99`. Their version row is `MISSING` **by prompt design**: `extractor.py:138-140` instructs
`status="missing"` for a version fused into the tool name, naming SPM12/SPM8/SPM99 explicitly. So the
model returned nothing because it was told to — case A, not a resolver failure. And the violation is
**true**, not false: `cobidas-version-criterion.md:28-29` holds that SPM requires a *revision* token
precisely because its major version is fused into the name, so `SPM12` alone does not meet §4.3.

> Counted **five**, where `ground-truth-protocol.md:398` says "four SPM papers report fused versions".
> The difference is mueller_2021, whose name is spelled out and contains no `SPM` substring — a count
> keyed on `SPM` sees four. `cobidas-version-criterion.md:59-61` already anticipates this, holding that
> the spelled-out form fails the same bar and "the count of fused cases does not depend on which
> surface form a paper uses". So the criterion doc is right and the protocol's four is the narrower
> count.
>
> **No amendment, but the two numbers now coexist with different warrants, and that is worth knowing
> before someone treats it as a discrepancy to reconcile.** `ground-truth-protocol.md:398`'s **four**
> is a count of papers whose base-pipeline name contains the `SPM` substring — true as written, and
> the basis of the 0/19 retraction. `cobidas-version-criterion.md:59-61`'s **five** is a count of
> papers whose version is fused into the name by any surface form — the §4.3-relevant population. Both
> are correct about different things. Neither is stale.

**Bounds, then:**

- **At-risk population: 9** (4 version-arm non-fused + 5 base-arm), not 14.
- **Ceiling: 9 go silent** → the section emits on 7 of 19.
- **Floor: 0 go silent** → unchanged at 16 of 19.
- **Evidenced estimate: 1** — poldrack_2015, the only paper with independent cross-vintage evidence of
  being case B/C (`predictions_v040_frozen.csv`, EXTRACTED 3/3 `"Washington University pipeline"`), so
  **15 of 19** is the single best point guess.
- **The citable claim's confirmed-correct core is 7 of 19** — the 5 fused-SPM plus the 2 deferrals —
  and that core is untouched by the ruling whichever way the other 9 fall.

**So the claim does not collapse under any admissible outcome.** The worst case moves it from 16/19 to
7/19 and leaves the 7 that are demonstrably true; the likely case moves it by one paper. That is the
answer to the proceed/defer question, and it is why proceeding is defensible 31 days from freeze.

**What is still not knowable until a re-extraction runs:** which of the 9 are B/C. That is the
measurement the fix produces, and it cannot be obtained before the fix exists. Recorded so that
"compute the effect first" is not re-asked as though it had been skipped.

---

## 5. Reason names — enumerated by truth of the line

**The suffix ruling of 2026-10-01 was reversed the same day by its author.** It optimised table
surfaces; the criterion should have been *every condition gets a sentence that is true of it*. Reusing
`extraction_quote_unresolved` for case C ships "span unresolved" about a case where **the span
resolved** — replacing one false sentence with another, which defeats the change. Recorded as a
superseded ruling rather than silently replaced, since the reasoning is the transferable part.

> **RULE, for any future reason-base decision in this repository, not only this one:**
> **enumerate by truth of the rendered line, not by table economy.** A reason base exists to select a
> sentence an author will read. Reusing one because it costs fewer table entries ships a false sentence
> to save a dict key, which inverts the only thing the reason is for. Count surfaces *after* deciding
> which sentences are true, never before.

Applied here: four conditions, four sentences, and a shared base only where the shared sentence is
true. The rule earned itself immediately — it is what surfaced that the 4th condition's existing
sentence (`deferral_quote_unresolved`) is already true of it *verbatim*, which table-economy reasoning
had missed in both directions.

| condition | reason | new base? | why |
|---|---|---|---|
| **A** nothing returned | `no_base_pipeline_named` *(unchanged)* | no | The one case where the current sentence is true. Unchanged is what makes case-A papers byte-identical in §9. |
| **B** quote did not ground | `extraction_quote_unresolved:base_pipeline_name` | **no — suffix retained** | "value present in source but span unresolved (extractor limitation)" (`_REASON_LINE:477`) is **true** of B. Inherits both tables and `batch.py:154`'s `startswith`. The suffix should also carry the resolver's own `failure_reason`, mirroring `:560`. |
| **C** quote grounded, value unsupported | `base_pipeline_value_unsupported` | **yes** | No existing sentence is true of it. The span resolved; the value was not in it. Needs entries in both tables and its own line. |
| **4th** deferral sentence did not ground | `deferral_quote_unresolved:base_pipeline_ref` | **no — suffix** | `deferral_quote_unresolved` already exists and is already tool-worded (`_REASON_LINE:491-494`: "reported a deferral to another source but could not locate the deferring sentence"), which is **true** of this condition verbatim. Today it prints "no base pipeline named in source" about a paper that named a citation — false. |

So: **two suffixes and one new base**, chosen by which existing sentence is true rather than by how
few entries it takes. Only case C pays the `_REASON_BUCKET` + `_REASON_LINE` + AST-guard cost, and it
pays it because nothing in the tables says what happened to it.

All three non-A reasons take the **`not_covered`** bucket (`_BUCKET_HEADER`, `render.py:498-503`),
matching `extraction_quote_unresolved` and `deferral_quote_unresolved` — and consistent with §4a's
`covered = False`, which is the same judgement expressed in the coverage layer.

## 6. The headline wording

**Correcting the brief.** The printed line is *already* table-driven. `_protocol_main:588-591`:

```python
if st in (MISSING_FROM_PAPER, LEFT_MISSING):
    # Reason-partitioned callout: source-absence vs extractor-coverage.
    return f"{label}: {_reason_detail(row)}"
```

and the base-pipeline header calls exactly that (`render.py:651`). `no base pipeline named in source
— you must specify` is **not** a separate literal; it is `_REASON_LINE:471`, reached through
`_reason_detail`. Verified end-to-end on the committed cole_2013 JSON: the row carries
`left_missing_reason='no_base_pipeline_named'`, `_reason_detail` returns the string, and
`_protocol_main` prints `Base pipeline: no base pipeline named in source — you must specify`. The
same row with `left_missing_reason='extraction_quote_unresolved:quote_not_found'` prints
`Base pipeline: value present in source but span unresolved (extractor limitation)`.

**So a per-case variant IS reachable with no new plumbing.** The reason is on the `FieldRow`, the
construction site already consults it, and adding the `_REASON_LINE` entry *is* the wording change.

**How the Software-row precedent applies, and how it does not.** `DELTA_software_row_deferral.md`
§8 records that the predicate change alone emitted the wrong sentence, so the wording had to ship
with the predicate:

> The predicate change alone emits the WRONG sentence for both deferring papers … That is A3's
> original complaint in a quieter register, so the deferral line ships with the predicate.

The principle holds here — wording ships with the change — but the mechanism differs. There the
sentence was hand-composed in a dedicated builder (`render.py:793-805`), so wording was separate
work. Here the `_REASON_LINE` entry §5 already requires *is* the wording, so the requirement is
satisfied by doing §5 and cannot be forgotten separately. Proposed lines:

- B → *"a pipeline was named but its quote could not be located in the source (extractor limitation)"*
- C → *"a pipeline was named but the quoted sentence does not state it — check the source yourself"*

Neither may say "not reported in source". That is the defect.

**§5's reversal removes the suffix-aware-lookup problem entirely.** Because case C takes its own base,
`_reason_detail` keeps consulting `_REASON_LINE` by base only (`render.py:526` via
`_reason_base:506-508`) and every condition still gets a true sentence. No change to the single source
of gap wording that every surface routes through (`render.py:517-519`) — which an earlier draft had as
the implementation's first decision, and which the reversal makes moot. One new base is cheaper than a
suffix-aware lookup, and it was also the only option that could be true.

---

## 7. The `searched_terms` sentinel — a deliberate decision

Today the only thing separating the five committed papers is an accident. `extractor.py:796-797`:

```python
searched_terms=name_result.searched_terms or ["base pipeline"],
sections_searched=name_result.sections_searched or ["full_text"],
```

`FieldExtractionResult.searched_terms` defaults to `[]` (`extraction_result.py:36-37`), and a model
result with `status="extracted"` populates value and quote rather than search terms. So the
`or`-fallback fires on the B/C fall-through and not on a model-reported `missing` that listed terms.
That splits the five 3 / 2: binder_1999, liu_2005 and power_2014 carry model-supplied terms;
cole_2013 and poldrack_2015 carry exactly `['base pipeline']` / `['full_text']`.

It is **suggestive, not conclusive** — it cannot separate a B/C fall-through from a model-reported
missing that listed nothing, which is demonstrably what cole_2013 is (`predictions_v040_frozen.csv`
has cole MISSING 3/3 with an empty value, while poldrack is EXTRACTED 3/3 as
`"Washington University pipeline"`).

**The decision to record.** Once B and C carry explicit reasons the sentinel becomes redundant for
new runs, and the reason supersedes it as a *designed* discriminator rather than an emergent one.
The implementation should **leave `:796-797` alone**: changing it buys nothing, and the fallback is
load-bearing for the `MissingFromPaper` contract (`searched_terms` is required with no default,
`provenance.py:61`). Stated so that it is given up as redundancy, not destroyed by accident. The
already-committed JSONs are files on disk and nothing here touches them; the sentinel remains the
only discriminator for those five forever.

---

## 8. Surfaces a new reason base touches

**The AST guard reads two files only.** `tests/test_render.py:704-707`:

```python
sources = [
    Path(render.__file__).with_name("extractor.py"),
    Path(migrations.__file__),
]
```

A producer added in `extractor.py` *is* seen, so the proposed reasons are covered and
`test_every_producible_reason_base_is_mapped` (`:692-733`) will fail until both tables have entries
— the guard working as designed. The blind spot is a producer introduced in a *third* source file;
widening the list costs one line plus whatever newly-visible bases it surfaces. **The implementation
must not widen it as a side effect** — that is its own change with its own blast radius.

**`batch.py` counts reasons by a closed chain with no catch-all** (`batch.py:150-157`). A new base
falls through all four branches and is counted in no `SUMMARY_COLUMNS` column — silently, since
there is no `else`. Note `:154` tests `startswith("extraction_quote_unresolved")`, which is why the
§5 suffix variant would be counted automatically and a fresh base would not. **The implementation
must either add a column or record in this document that the new reasons are deliberately
uncounted** in the batch summary, with the reason. Not author-facing, but it is the surface that
produced the `_tally` scoping correction already in `DEVLOG.md`.

A third surface, for completeness: `_REASON_BUCKET` and `_REASON_LINE` currently map 10 bases each
and **agree exactly** — nothing in one and not the other. `value_not_in_literal` is mapped in both
and producible by nothing (retired in 0.5.0 per `generate_sfn_review.py:404`). The implementation
should not "tidy" that dead entry while here.

---

## 9. Acceptance

**The re-render identity gate should show 19 of 19 byte-identical. Exact, and derived.**

`scripts/rerender_reports.py` replays stored per-paper JSON through the current renderer. The stored
JSONs carry `inference.reason = "no_base_pipeline_named"` for all five missing-base papers — verified
on cole_2013 — and `flatten` reads `left_missing_reason` straight off that stored value. The builder
change runs only during extraction, so **a re-render cannot exercise it at all.** The only
render-side change is adding entries to two dicts for keys that appear in no stored JSON.

So the gate's job here is purely negative, and it is sharp:

- **19/19 identical** → the render-side change touched nothing it should not.
- **Any non-zero diff** → a new `_REASON_LINE`/`_REASON_BUCKET` entry collided with an existing key,
  or existing wording was edited. Not a partial success; a leak.
- In particular **the five missing-base papers must be identical too**, not just the fourteen. The
  brief anticipated case-A papers holding still and B/C papers moving; that expectation is wrong for
  a re-render, because no stored JSON carries a new reason. A diff on *any* of the five means the
  change leaked past its new branches.

**Seeing the new reasons requires a re-extraction**, which §1 gates. If that is ever approved, the
pre-registration should state per-paper expectations before the run, per this repo's practice — and
note that poldrack_2015 is the one paper with independent cross-vintage evidence of being case B or C
(`predictions_v040_frozen.csv`, EXTRACTED 3/3 `"Washington University pipeline"`), making it the
single strongest prediction available in advance.

Unit-level acceptance, which needs no run and no spend: `_build_base_pipeline` driven with the five
constructed cases of §2 must return three *distinguishable* gap results for A, B and C, with D and E
unchanged. That is the whole correctness claim, and it is testable for free.

---

## 10. `_build_version_pf` — the same defect, on the larger population

**By ruling, 2026-10-01: an item, not a scope exclusion.** The field is `base_pipeline.version`, which
carries this project's one unconditional COBIDAS claim and the retracted 0/19 claim, so "out of scope"
would have become "not recorded".

`_build_version_pf` (`extractor.py:640-681`) has a single MISSING return at `:677-681`. Driving it
with constructed inputs, **four** conditions collapse onto one record — one more than
`_build_base_pipeline`:

| condition | result |
|---|---|
| no version field supplied (`None`) | `MissingFromPaper` + `version_deferred_to_kb` |
| model reported `missing` | `MissingFromPaper` + `version_deferred_to_kb` |
| version quote did not ground | `MissingFromPaper` + `version_deferred_to_kb` |
| quote grounded, value not in it | `MissingFromPaper` + `version_deferred_to_kb` |
| *control:* quote grounded, value in it | `Extracted[str]` |

`version_deferred_to_kb` renders "version not reported in source — you must specify"
(`_REASON_LINE:472`) — a claim about the paper, for what may be a resolver failure, on the field whose
absence is the citable finding.

**And this is the LARGER half, measured.** `_software_coverage:189-190` reads the *version* row's
status whenever a version row exists, so the version arm decides the Software row for every paper
whose pipeline name extracted. Over the 19-paper acceptance batch:

| route | status that decided it | n | Software section emitted |
|---|---|---|---|
| version arm | `MISSING_FROM_PAPER` | **9** | yes |
| base arm | `MISSING_FROM_PAPER` | **5** | yes |
| base arm | `DEFERRED_TO_CITATION` | 2 | yes — intended, per the ratified Software DELTA |
| version arm | `EXTRACTED` | 3 | no |

**16 of 19 papers carry the unconditional-violation section, and 14 of those 16 are decided by a
collapsed record** — 9 by the version collapse, 5 by the base collapse. Only the 2 deferral cases are
decided by a record that says what it means.

So §1's framing understated this delta's reach. The base_pipeline fix addresses 5; the version fix
addresses 9.

### Sequencing, ruled 2026-10-01

**One design document, two commits, base_pipeline first.** The Software-row DELTA split its own change
precisely so each diff stayed attributable (`DELTA_software_row_deferral.md` §8, "Sequencing, to keep
each diff attributable"), and the same reasoning governs: a single commit moving both arms moves up to
9 papers' Software row at once, in which no paper's change is attributable to a cause.

**"Complete" is not claimable until the version arm lands.** The base commit fixes the smaller half.
Until the second commit ships, any statement that the base_pipeline diagnostic defect is fixed is
false for 9 of the 14 affected papers — and the field it leaves unfixed is the one behind the retracted
0/19 claim. Recorded here because "out of scope" became "not recorded" once already in this document's
own first draft (§0), and a two-commit split is the same hazard with a schedule attached.

The same §4a question applies here and is not decided: a version row whose quote did not ground
currently produces an unconditional COBIDAS accusation against the author.

---

## 11. A note on how this document was produced

Three of its premise corrections (§0) came from a seven-agent gathering pass in which **the agent
assigned the central question — what `MISSING_FROM_PAPER` asserts — stalled on all six attempts and
returned nothing.** Every correction to §4 arrived from a different agent reaching outside its brief.

Recorded because the failure mode is not "an agent failed": **a silent investigator leaves its question
looking answered.** An earlier draft of §4 answered it confidently from a search that found
`DESIGN_protocol_emitter.md:95` and stopped, and nothing in the run's output marked that question as
unexamined — the missing report and a complete-looking answer are indistinguishable at the point of
reading. The overlap saved it. The general form, for the next fan-out: **a question with no returned
investigator needs the same treatment as a returned negative — a positive control that the question
was actually asked.**

---

## 12. Carried forward — what this document displaced

**This was item 1 of three, and it grew into a change to the Software row's coverage semantics.** The
growth is recorded as legitimate in §1 and bounded in §4b. What is not recorded anywhere else is the
cost of the attention it took.

Untouched, in the order they were queued:

1. **`span_recovered` has no downstream consumer.** Set on every extraction at `extractor.py:571`,
   `:673`, `:763`; read by nothing — `git grep span_recovered -- render.py batch.py cobidas.py` returns
   nothing, against a positive control that finds `extraction_quote_unresolved` in render.py and
   batch.py. Still re-run-free, still small.
2. **The render question**, which is the one with a deadline. Figures and panel layout have been
   deferred since 2026-08-26 under "compute everything first, render once" — a decision taken while the
   numbers were moving. The numbers have since settled and regenerate on demand
   (`ground_truth/target_space_tally.md`). **That deferral is now standing by default rather than by
   decision**, with 31 days to the internal freeze.

**Ruled 2026-10-01: look at the render decision before the version arm, not after.** The version arm
(§10) is the larger half of this defect and will still be there; the render deferral is the only open
item with a date attached to it, and the one whose cost of being wrong rises every week it stands. This
document's own §1 argues that a decision made explicitly beats one met in late October — that argument
applies to the render deferral at least as strongly as it applied here.
