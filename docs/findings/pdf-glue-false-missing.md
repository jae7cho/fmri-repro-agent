# pypdf tool-citation glue: incidence is real; its causation of cole's MISSING was REFUTED by test

**Status (2026-07-23): the original causation claim was tested and did not hold.** This doc first
asserted that pypdf tool-citation glue (`AFNI48`/`Freesurfer49`) *caused* cole_2013's base_pipeline
MISSING. A deglue causal test refuted it. The glue **incidence** finding stands; the **causation**
claim does not. Recorded here as a corrected finding — the assertion dissolved when demonstrated,
like several this project (wheaton "never states its tool", the guard that "handled viduarre", four
protocol rules).

## What glue is

As pypdf extracts it, cole_2013's methods read `AFNI48` / `Freesurfer49`: the tool name is fused to
its citation superscript with no separator. Reference cross-check confirms it is glue, not a version —
ref 48 = *"Cox RW. AFNI: software…"* (the AFNI paper), ref 49 = *"Desikan RS… automated labeling"*.

## Incidence sweep (deterministic, 19 corpus papers, cabral excluded)

Tool-token-immediately-followed-by-digits, with STEP-0 discriminators (reference-list cross-check,
adjacency, version-space, citation style). Result:

- **Tool-name glue is rare: 1 paper (cole_2013), 2 hits** (`AFNI48`, `Freesurfer49`).
- All **7** SPM+digit hits (agtzidis/derosa/gordon/mueller/tang×2/wheaton) are **real versions**
  (SPM {94,95,96,99,2,5,8,12,25}) — the discriminator prevented the version-inflation trap.
- **At-risk** (glued tool with no clean token in the slice): only **cole's AFNI** (the clean "AFNI"
  is in the reference list, out of slice). Freesurfer49 is *not* at risk — a clean "Freesurfer was
  used to…" appears in the slice (and FreeSurfer is anatomical, not the base pipeline).
- Citation-style population bound: **7/19 numeric-superscript** (glue-capable: chen, cole, gordon,
  oconnor, poldrack, tang, weber), **3/19 author-year** (glue-immune: binder, ciric, wheaton),
  9/19 low-signal. Glue is pervasive at the *word* level (79 glued tokens in cole, 95 in gordon) but
  materialized on a base_pipeline *tool* in only one paper.

## Causation test — REFUTED

Deglue cole's methods slice (`AFNI48 → AFNI 48`, `Freesurfer49 → Freesurfer 49`, 2 substitutions),
re-extract base_pipeline at K=3, same model pin. Control = the frozen glued run (MISSING 3/3).

**Result: MISSING 3/3 on the deglued slice.** And a second variant — **drop the number entirely**
(`AFNI48 → AFNI`, so the model sees *"Preprocessing was performed using AFNI and Freesurfer."*, K=3) —
also returned **MISSING 3/3**. So neither the glued surface form nor an adjacent numeric marker is what
blocked recognition: with a *fully clean* "AFNI and Freesurfer" the model still extracts no base
pipeline. cole's MISSING is a **genuine extraction failure on a bare two-toolbox mention**, robust to
both deglue forms.

This tested down a broader hypothesis, not just the glue one: if the drop-number form had recovered
AFNI while the space-split did not, a numeric superscript adjacent to a clean tool name would suppress
extraction — a much larger effect (7/19 papers, 79–95 glued tokens each). It did not; both variants
miss. Note the likely mechanism is a **D2 under-extraction**: the model does not treat a bare toolbox
pair ("AFNI and Freesurfer") as a *named base pipeline*, though D2 says a named toolbox counts as
REPORTED. That is a base_pipeline recall/definition gap, not a PDF problem.

Consequence for the scored set: cole is re-attributed from "INPUT-CORRUPTION (glue)" back to a genuine
EXTRACTION failure. Of the two non-viduarre base_pipeline errors, liu_2005 is upstream-input (slicing)
but **cole is a real model miss** — the set has two genuine model errors (cole miss, viduarre
fabrication), not one.

## Why a deglue pass must NOT ship (blast radius, measured)

A naive `word+digits → word digits` split touches **541 occurrences / 263 distinct tokens** corpus-wide;
only **1** (`AFNI48`) is the target. The rest are tokens where **the digit is the meaning**:

| bucket | count | examples |
|---|---|---|
| real tool version | 6 | `SPM12`, `SPM8` |
| template ID | 4 | `MNI152`, `fsaverage5`, `Conte69` |
| atlas/parcellation | 3 | `CC200`, `Power3`, `Craddock1` |
| "citation glue OR other" | 480 | incl. `BA44` (Brodmann), `AKT1`/`BACE1` (genes), `CO2`, `BET2` (FSL tool) |
| other/large | 47 | `MR750` (scanner), `ncomms9414` (article ID) |
| **software (target)** | **1** | **`AFNI48`** |

Naive precision ≈ **1/541 (0.2%)** — it destroys `MNI152`/`fsaverage5`/`SPM12`/`BA44`/`CC200` to fix
one `AFNI48`. **Non-starter.** Two safer options, both with real cost:

1. **Tool-allowlist** (non-integer-version tools + digits, SPM *excluded*): touches exactly `AFNI48`,
   `Freesurfer49` here (0 collateral), but carries generalization risk (`FSL5`, `BET2`).
2. **Allowlist + reference-index cross-check**: highest precision, but requires parsing the reference
   list inside `pdf_loader` (a dumb text extractor gains a dependency).

Both shift **every downstream character offset** (a space insertion moves all spans), invalidating the
frozen prediction spans, and both are **global transforms** whose correctness surface is the entire
corpus's alphanumeric tokens — not one field.

**The irony (the real content):** the same ambiguity that forced discriminators in the *measurement*
(is `word+digits` a version, an ID, or glue?) forces the identical discriminators in the *fix*. There
is no cheap version. And now that the causal test failed, the fix would not even recover cole.

## Backlog (revised)

1. Cole is a genuine extraction failure on a **bare multi-tool mention** ("AFNI and Freesurfer") — a
   base_pipeline recall/definition gap (the model does not extract a bare toolbox pair as a named base
   pipeline, though D2 says it should), NOT a PDF problem. Both deglue variants (space-split and
   drop-number) were tested and both miss 3/3, so this is closed as a model-side D2 under-extraction.
   Worth a corpus-wide check: does the extractor systematically under-extract bare toolbox mentions?
2. Glue's effect, if anywhere, is on **step-level fields** (parameters, atlas/method citations) in the
   7 glue-capable papers — unmeasurable for false-MISSING without labels for those fields.
3. **Do not ship a deglue pass.** If ever revisited, use the allowlist+ref-index gate, never the naive
   split; the numbers above are recorded so this is not re-derived.

Related: [`span-resolution-fix.md`](span-resolution-fix.md),
[`span-resolution-hard-drop.md`](span-resolution-hard-drop.md), the stage-partition's fourth class.
