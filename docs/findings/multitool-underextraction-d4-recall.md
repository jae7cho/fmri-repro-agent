# Multi-tool under-extraction, and D4's recall-blindness that hides it

**Finding (base_pipeline, 2026-07-23).** The extractor reliably extracts **single-tool** base pipelines
and systematically **under-extracts multi-tool** ones — it never names all tools of a multi-tool label,
at best one of them. The D4 scoring rule (set membership, precision-only) hides this, so the concealment
is a protocol point, not just a model one.

## The pattern (N=17 blind, base_pipeline)

| label shape | papers | extracted |
|---|---|---|
| **single-tool** REPORTED | 11 (agtzidis, chen, ciric, derosa, gordon, liu_2013, mueller, oconnor, vanderwal, weber, wheaton) | **11/11 correct** |
| **multi-tool** REPORTED | cole `[AFNI, FreeSurfer]`, liu_2005 `[BrainVoyager, custom software]`, tang `[DPABI, SPM12]` | **never all; ≤ 1 of N** |

Per-paper, with the confounds tested out (K=3 each, 2026-07-23):
- **tang** → `SPM12` (1 of 2; DPABI missed). Status EXTRACTED.
- **liu_2005** → **both**: its frozen MISSING was **input-corruption** (two-column reference
  interleaving; see [`pdf-glue-false-missing.md`](pdf-glue-false-missing.md)), AND on a clean slice it
  extracts `BrainVoyager` only (1 of 2; "custom software" missed). So it joins the incomplete set —
  the MISSING and the incompleteness are separate facts, both true.
- **cole** → frozen MISSING, and a clean slice **still** MISSING (0 of 2). The outlier: the model
  won't extract the bare `"AFNI and Freesurfer"` construction at all (both deglue variants tested).

So the **incompleteness is 3/3** — every multi-tool paper fails to name all labeled elements — while
the **MISSING has two distinct causes** (cole = model, liu = corruption). Both statements hold; do not
let one erase the other.

## The dropped elements are not the same kind (sharpen before concluding)

"3 of 3 incomplete" over-counts the model's culpability, because what got dropped differs:

- **cole** dropped **AFNI *and* FreeSurfer** — two real named tools, from a maximally simple sentence
  (*"Preprocessing was performed using AFNI and Freesurfer"*). 0 of 2.
- **tang** dropped **DPABI** — a real named tool. 1 of 2.
- **liu_2005** dropped **"custom software written in Matlab"** — **not a named tool, a descriptor**. A
  model asked for a pipeline *name* arguably behaves correctly by not emitting it. The label includes
  it because the protocol (rightly) labels what the paper *predicates* — so this is a **label/prompt
  scope mismatch**, not necessarily a model miss.

So the evidence for **dropping coordinated *named* tools is 2 papers (cole, tang), not 3.** And **cole
is anomalous even within those two**: dropping *both* tools from "using AFNI and Freesurfer" is
stranger than dropping one of two. Note cole's next sentence scopes FreeSurfer to anatomy (*"Freesurfer
was used to identify ventricle, white matter, and gray matter"*), so D7 would exclude FreeSurfer from
the *functional* base_pipeline — but that makes extracting **nothing** stranger still, since AFNI (the
functional tool) remains and should extract. cole is a specific anomaly to probe, not proof of a broad
law.

## D4 hides it (the protocol point)

D4 scores value by **set membership**: *"correct if every element it names was named by the paper."*
That is **precision-only — no recall term**. So tang naming 1 of 2 tools scores as a **full match**
(`{SPM12} ⊆ {DPABI, SPM12}`). The Tier-B value-match 12/12 therefore partly conceals incomplete
multi-tool extraction: the number means **"never named a wrong tool," not "named all the right tools."**
Not wrong — but it must be stated that way, and a **recall-sensitive companion metric** (Jaccard, or
recall on multi-tool rows only) would surface what set-membership cannot.

## It does not revisit D2

D2 rested on the prompt listing `SPM12`, i.e. "the model was told toolboxes count." Single toolboxes
clearly landed (SPM12/SPM8/SPM99/FSL suite all extract). Coordinated *named*-tool sets extracted at
most partially (cole 0/2, tang 1/2). So the prompt/protocol alignment D2 relies on **holds for
singletons and is incomplete for coordinated named tools** — a **gap in the prompt** (it does not
elicit *all* tools of an "X and Y" conjunction), not a reason to revisit D2. The fix is prompt-side.

## Backlog

1. Recall-sensitive companion metric for multi-tool base_pipeline rows (report alongside the D4
   precision-only match).
2. **Mechanism probe (minimal, real text, no synthetic generalization):** vary cole's own sentence one
   way — *"…using AFNI and Freesurfer."* (known 0/2) vs *"…using AFNI."* (singleton). If the singleton
   extracts and the coordination does not, the "X and Y" construction is causal and the fix is
   prompt-side; if the singleton also misses, the sentence has another problem and multi-tool is the
   wrong frame for cole. ~6 calls (K=3 × 2). Add tang's variant only if cole's result is ambiguous.
