# Ground-truth protocol — `base_pipeline` (v1.1)

**Status: PRE-REGISTERED.** This document is committed to git **before any label is written**, and
the labels are committed before any scoring run. The signed commit order is the pre-registration: it
establishes that the rules predate the measurement and could not have been shaped to fit cases after
seeing extractor output. Amendments after labeling begins get a new version number and a stated
reason — never a silent edit.

**Field:** `base_pipeline` — the pipeline/tool **name(s)** only. Version is a separate field with its
own label (see D5). This protocol covers exactly one field of the ReplicationSpec.

**Corpus:** 20 PDFs in `tested_lit/sfn_batch`. Analysed denominator is **19** (see D10).

**Labeler:** author (single-rater — Jae Wook Cho) · **Date started:** 07/18/2026 ·
**Protocol version:** v1.1

---

## Provenance of this protocol (read first — it is the reason for several rules)

This protocol was drafted by adjudicating each question against the **actual paper text**, read
verbatim. An earlier LLM-filtered "shapes" screen of the same corpus produced a candidate set of
reporting patterns; **four proposed rules and one citable finding turned out to be artifacts of that
screen** and were discarded when the real text was read:

- a "predication" rule (built on wheaton "never stating its tool" — the paper says *"Data were
  analyzed using SPM99"*),
- a "genre-gesture" rule (built on agtzidis "naming no tool" — the paper says *"performed with
  SPM12"*),
- an exclusion of braun/liu_2005 as "no preprocessing" (both preprocess; liu_2005 names
  BrainVoyager),
- an "in-house scripts as distinct status" rule (built on mueller — the paper says *"Initial
  preprocessing was performed using … SPM12"*),
- the finding *"0/19 papers report a pipeline version"* (a restatement of a hardcoded constant; see
  the Version note at the end).

The operative lesson, which governs the labeling procedure below: **label against what the paper
says, verified deterministically, not against any filtered or model-produced summary of it.**

---

## Label vocabulary (per field, exhaustive, mutually exclusive)

- **`REPORTED`** — the paper names a base preprocessing pipeline or tool.
- **`DEFERRED_TO_CITATION`** — the paper points to another **work** for its preprocessing instead of
  naming a pipeline.
- **`NOT_REPORTED`** — the paper performs fMRI preprocessing but names no pipeline and defers to no
  work.
- Papers that perform **no fMRI preprocessing** are **EXCLUDED**, not labeled (D10).

The four states are exclusive **only within a single field** (D11): a paper may be `REPORTED` for
`base_pipeline` and `DEFERRED_TO_CITATION` for a step-level field simultaneously.

---

## The twelve decisions

### D1 — Citation-deferral → `DEFERRED_TO_CITATION`; no genre test
A citation-deferral for preprocessing is labeled `DEFERRED_TO_CITATION`. The **genre** of the cited
work does **not** change the label. Cases: viduarre (*"procedure described by Glasser et al."*), tang
(*"following the preprocessing steps described in previous studies"*), braun (*"preprocessed
according to standard protocols as previously described in refs. 47 and 48"* — Cao 2014, Plichta
2012).

> **Discarded sub-rule (recorded, not applied):** a "genre test" was considered — deferrals to a
> textbook/handbook (a *tertiary* source that surveys several standards and does not let a reader
> recover what was run) would be `NOT_REPORTED`, as a "genre gesture" rather than a real pointer. Its
> only candidate was agtzidis' citation of Poldrack et al. 2011 (the *Handbook of Functional MRI Data
> Analysis*). But agtzidis **names SPM12 in-text** and is therefore `REPORTED` regardless (D2) — it
> was never deferring. With no surviving case, the genre test is **not part of this protocol**.
> braun vs agtzidis is the illustrative pair: near-identical surface (*"standard protocols …
> described in refs"* vs *"a standard preprocessing pipeline (Poldrack 2011)"*), different labels,
> and the difference is decided by whether the paper **also names a tool**, not by the citation's
> genre.

**`CitationResolver` scope:** the label describes what **this** paper did. If a cited work itself
defers onward, chasing that chain is the resolver's job, not the labeler's. braun (defers to two
prior empirical studies) is the recursion case.

### D2 — Named software toolbox counts as `REPORTED`
A named software toolbox used to perform preprocessing (FSL, AFNI, SPM, BrainVoyager, FreeSurfer)
counts as `REPORTED`. **Basis:** `extractor.py`'s extraction prompt lists `"SPM12"` among the
`base_pipeline_name` examples, so the model was instructed that a toolbox counts; labeling toolboxes
`NOT_REPORTED` would score the extractor against a definition it never received. Cases: derosa (FSL
suite), gordon (SPM8), wheaton (SPM99), agtzidis (SPM12), mueller (SPM12), cole (AFNI + FreeSurfer,
see D4), liu_2005 (BrainVoyager).

**Predication requirement:** the tool must be stated as **performing the preprocessing** — *"analyzed
using SPM99"*, *"preprocessing … carried out using the FSL suite"*. A tool named only as part of
another object (e.g. *"the SPM MNI template"*) is **not** by itself `REPORTED`. (In this corpus every
toolbox mention is predicated; wheaton, initially thought to be template-only, in fact opens with
*"Data were analyzed using SPM99"*.)

> **Reproducibility caveat, carried as data not status (see `pipeline_specificity`):** naming a
> toolbox ("SPM", "FSL") identifies a package containing many possible pipelines and barely constrains
> what was run, unlike a named end-to-end pipeline (fMRIPrep 20.2.1). D2 makes it `REPORTED` because
> the paper named its tool; the reproducibility-relevance of that answer is recorded separately.

### D3 — (no separate "in-house" status)
**Discarded — no surviving cases.** An "in-house scripts as a distinct status" rule was considered
(mueller, poldrack, cole, liu_2005) and dissolved on inspection: mueller and liu_2005 name a tool
in-text (D2); cole's in-house software computes gPPIs (analysis, out of scope, D8); poldrack is a
citation-deferral (D1). In-house scripts that are the **only** base_pipeline statement, should any
arise, are `REPORTED` with `pipeline_specificity = in_house` (consistent with D2: the paper stated
what it did; reproducibility-relevance is data, not status).

### D4 — Value is a **list**; multiple named tools → the set
`value` is always a **list** of names (usually a singleton). When a paper names multiple tools for
preprocessing **as a whole** without a stated scope split, label the **set**. Scoring is set
membership: the extractor's value is correct if every element it names was named by the paper. Case:
cole → `{AFNI, FreeSurfer}`. An optional `primary_tool` annotation may record a domain judgment of
which is the functional workhorse, but it does **not** affect the score.

**Predication scoping (the "mueller clause"):** `base_pipeline` = the tool(s) predicated of
**preprocessing as a whole**. Tools predicated of a **specific step** are step-level fields, not
`base_pipeline`. Cases: mueller → `{SPM12}` (SPM12 does *"Initial preprocessing"*; ANTs does template
construction → spatial-normalization step; in-house MATLAB does *"Further preparation"* → nuisance
step); derosa → `{FSL suite}` (ICA-AROMA is a step within it). cole → `{AFNI, FreeSurfer}` (no
staging stated; both predicated of preprocessing as a whole).

**Wrapper rule (from the KB's own model):** a named pipeline that *"employs"* component tools →
label the wrapper, not the components (`ccs.yaml` lists FSL/AFNI as CCS components). Cases: liu_2013
→ `{FCP scripts}` (not AFNI/FSL); C-PAC wraps AFNI/FSL/ANTs.

### D5 — Version is **not** required for `REPORTED`
A bare name is `REPORTED`. Version lives in the separate `base_pipeline.version` field with its own
label; it is never a condition on the name's status. **Basis:** `PipelineRef` carries `name` and
`version` as distinct fields; `cobidas.py` treats `base_pipeline.version` as its own row. Requiring a
version would also make the metric degenerate given how rarely versions are separately stated.

### D6 — Label the **full paper**; the partition attributes the loss
The `REPORTED / NOT_REPORTED / DEFERRED` judgment is a property of the **paper**, read in full —
methods, figure captions, abbreviations list, data-availability statement, and **supplementary
material where present** — **not** of the methods slice the extractor sees (`find_methods_section`).
Labeling against the slice would encode the slicer's limitation as a fact about the literature — the
exact failure mode the version finding exhibits.

Attribution is then done by the **three-way partition** (free, once labels exist):

| paper reports it | supporting quote in the methods slice | class |
|---|---|---|
| yes | yes | **extraction failure** — the model had it and missed it |
| yes | no  | **slicing failure** — `find_methods_section` lost it; the model's MISSING is honest |
| no  | —   | **MISSING is correct** |

**Fourth class — corpus-construction failure (D6 sub-rule):** where a pipeline is named/deferred to
**supplementary material that is absent from the corpus PDF**, a MISSING is neither extraction nor
slicing — the artifact handed to the system was incomplete. In this corpus the SI body is absent from
**every** PDF (all SI headings are online pointers); the base_pipeline case is confirmed but rare:
**derosa** explicitly defers preprocessing to absent Supplemental Materials (*"Refer to the
Supplemental Materials for the preprocessing and denoising procedures"*) while naming FSL in-text
(so: `REPORTED` name + step params deferred to absent SI — the cleanest D11 case). Record a
`corpus_completeness` note (`main_text_only | includes_si`) at the paper level; do not fetch SIs.

> A `target_kind="supplement"` deferral state and a recognition A/B were scoped and **deferred** —
> the SI-Methods-vs-SI-figure discrimination is 2:77 in this corpus, so the population (~1–2 papers)
> does not warrant the schema change here. Revisit if a future corpus is SI-heavy (fMRIPrep-era,
> PLOS/eLife). Recorded as a trigger-conditioned backlog item, not a dropped idea.

### D7 — `base_pipeline` is the **functional** preprocessing pipeline
Where a paper uses different tools for anatomical vs functional preprocessing, `base_pipeline` is the
**functional** one. **Basis:** `Preprocessing` entries partition **functional** acquisitions
(`preprocessing.py`: *"every functional acquisition covered exactly once"*); anatomical work has its
own step kinds (`brain_extraction`, `segmentation`, v0.3.0). Cases: weber → C-PAC (not FreeSurfer
v5.1); ciric → XCP Engine (not ANTs Cortical Thickness); cole → AFNI (FreeSurfer → anatomical steps);
poldrack's recon-all → anatomical, excluded from base_pipeline.

**Domain-knowledge authorization:** assigning a named tool to anatomical vs functional scope may
require knowledge the sentence does not state (FreeSurfer = surface/anatomical; AFNI = volumetric/
functional). The labeler is authorized to use domain knowledge for this assignment; it is recorded so
a second rater applies the same basis. (This is the first rule not checkable from the sentence alone —
a likely source of inter-rater divergence; see D4's set-label, which keeps the *reproducible* judgment
in the primary score and the domain call in the optional annotation.)

### D8 — Preprocessing, not downstream analysis
Tools used only for **analysis** (CONN, DPABI, Brain-Connectivity-Toolbox, cole's gPPI software,
liu_2005's Psychophysics/Video Toolbox) are out of scope and do not make a paper `REPORTED`.
**Basis:** `extractor.py` — *"the base **preprocessing** pipeline"*.

### D9 — Methods-comparison papers
**Ruled (confirmed against ciric's verbatim methods paragraphs — STEP 1, v1).**
`ciric_2017` → **`REPORTED`**. `value = ["XCP Engine"]`. `pipeline_specificity = named_pipeline`
(an end-to-end preprocessing engine that invokes FSL/AFNI utilities internally — D4 wrapper logic:
label the wrapper). Quote: the *"processed using the XCP Engine"* sentence.
**notes:** XCP Engine cited as *"Ciric et al., In Preparation"* (named but unpublished at time — a
recoverability edge for `pipeline_specificity`, still `named_pipeline`). The 14 denoising models
(2P…AROMA+GSR) are the nuisance-regression FIELD's variants (D11), **NOT** `base_pipeline` — do not
let them bleed into `value`.

### D10 — Papers performing no fMRI preprocessing → EXCLUDED (the denominator)
A paper that performs no fMRI preprocessing is **EXCLUDED** via `corpus.py`'s `EXCLUDED_PAPERS` with a
written rationale — **never** labeled `NOT_REPORTED`. Labeling a modelling paper `NOT_REPORTED` and
counting the extractor's MISSING as "correct" is a free win that inflates the headline rate.
**Basis:** the exclusion registry's own principle (*"a vanished paper is the same provenance failure
AESPA exists to prevent"*) and its mandate that every aggregate state its denominator on its face.

**Verified deterministically (this corpus):** **cabral_2017** excluded (review/modelling; no Methods,
no preprocessing — confirmed by the tool-token sweep finding no preprocessing tool). **braun_2015 and
liu_2005 are NOT excluded** — both preprocess (braun defers to refs; liu_2005 names BrainVoyager with
explicit steps). **Analysed denominator = 19.** (The compromised screen had reported braun/liu_2005 as
"no preprocessing," which would have wrongly set N=17.)

### D11 — Labels are per-field
`REPORTED` and `DEFERRED_TO_CITATION` are exclusive only **within one field**. A paper may name its
base pipeline (`base_pipeline` = `REPORTED`) and defer its step parameters (step fields =
`DEFERRED_TO_CITATION`) at once. Cases: chen (names CCS + defers step details to [51]); derosa (names
FSL + defers procedures to absent SI — see D6).

### D12 — "HCP" token disambiguation (labeler instruction)
The token "HCP" / "Human Connectome Project" appears in multiple roles and only one bears on
`base_pipeline`. The labeler classifies each mention by role:
- **preprocessing provenance** → relevant (may support `REPORTED`/`DEFERRED`),
- **acquisition-protocol reference** (poldrack: *"a protocol patterned after the Human Connectome
  Project"*) → not base_pipeline,
- **comparison dataset** (power: *"our experience with HCP data"*) → not base_pipeline,
- **a named tool/command** (weber: *"the HCP Workbench … command"*) → a step-level tool, not
  base_pipeline.

**Ruled (confirmed against viduarre's printed hits — STEP 1, v1).**
`viduarre_2017` → **`DEFERRED_TO_CITATION`**. `value = ["Smith et al.", "Glasser et al."]` (BOTH
targets, verbatim — see multi-target rule). HCP is dataset-use only, **never** pipeline-provenance.
**notes:** refs 18/39/40 resolve to the HCP Pipelines (Glasser 2013 = HCP MPP; Smith 2013 = HCP
rs-fMRI); Griffanti 2014 = ICA-FIX, a denoising STEP not the base pipeline. The resolved names are
recorded here in notes **ONLY** — they are **NOT** in `value`; recording "HCP MPP" as the label would
score the model's citation-inference (the viduarre fabrication the v0.4.0 guard prevents) as correct.

---

## Value-matching — report **both** tiers

The Chat 4 gate is *hallucination < 5%*, and a hallucination is a **wrong value**. How strictly
`extractor.value` is compared to `label.value` **is** the hallucination rate, so it is reported at two
strictnesses and the gap between them is itself a finding.

**Label format:** `value` is a list (D4), recorded **verbatim** as the paper writes the name,
including version-fused forms (`SPM99`, not `SPM`). No substring matching is used anywhere in scoring
— normalize-then-**equals** on whole tokens, set membership for lists. (This is the session's
recurring lesson: substring matching over short/normalized names is unsafe in **both** directions —
`ants ⊂ Avants` over-matches; a strict `\b` misses `SPM99`; a greedy version-strip eats adjacent
names.)

**Multi-target deferrals (consortium-data pattern — HCP/ABCD/UK Biobank, recurs often):** for
`DEFERRED_TO_CITATION`, `value` lists **ALL** deferral targets verbatim; the resolved pipeline name
(what a domain reader knows the citation means) goes in `notes`, **NEVER** in `value` — the paper
deferred, the label records the deferral, and resolving the citation is `CitationResolver`'s job with
its own provenance. Scoring: the extractor's ref matches if it names **ANY** one of the paper's
deferral targets (set membership); flag multi-target deferrals (naming 1 of N citations is weaker than
the sole target and may warrant a partial-credit tier).

**Tier A — strict identity (defensible lower-bound hallucination rate).** Normalize (lowercase; strip
punctuation, whitespace, wrapper words `suite/software/pipeline/toolbox/package/version/release`) and
**strip the version** (including fused SPM digits: `SPM99/2/5/8/12 → spm`), then compare by set
membership.
- `SPM99` vs `SPM` → both `spm` → **MATCH** (ruling: name-matching is **version-insensitive**, so D5
  and value-matching do not contradict — the version field carries the difference; a consequence is
  `SPM8` and `SPM12` also match at the name level, which is **intended**, not a bug).
- `C-PAC` vs `CPAC` → **MATCH** (punctuation/whitespace normalized; see matcher note below).
- `FSL` vs `FSL suite (version 5.0.10)` → **MATCH** (wrapper + version stripped).
- `{AFNI}` vs `{AFNI, FreeSurfer}` → AFNI ∈ label → **MATCH** (set membership, D4).

**Tier B — alias-equivalent ("same pipeline, human-judged" rate).** Tier A, plus (a) KB `recognize()`
equivalence for the four KB pipelines (`"Configurable Pipeline for the Analysis of Connectomes"` ≡
C-PAC), and (b) a **pre-registered alias table** for toolboxes not in the KB (SPM/FSL/AFNI/FreeSurfer/
ANTs/BrainVoyager). The alias table is committed **before scoring**, minimal (only aliases forced by
real corpus collisions, each annotated with the paper that motivated it), and reviewed by the second
rater — an alias table grown to fit papers after scoring makes the hallucination rate tunable.

**Report:** Tier-A rate, Tier-B rate, and the **delta** (which decomposes apparent error into
surface/version variance [A→B] vs genuine wrong-pipeline [survives B]). Report the
`pipeline_specificity` distribution (counted **per tool**, across the parallel lists) as a
**standalone COBIDAS-facing count**, folded into neither rate.

> **Known matcher issues (to fix against real label/prediction pairs when the harness is built — do
> not tune in isolation now):** (1) `C-PAC` vs `CPAC` must match, which requires normalizing to a
> single string **before** tokenizing (tokenize-after-punctuation-strip yields `{c,pac}` ≠ `{cpac}`);
> confirm the staged matcher has an explicit test for this pair. (2) the version-strip regex
> `v?\d+(\.\d+)*[a-z-]*` is greedy on its trailing `[a-z-]*` and boundary-blind — safe on the current
> corpus only because names precede versions; harden it when real pairs exist.

---

## `pipeline_specificity` — reproducibility-relevance as data (carries the D2 caveat)

A separate labeled field recording how much each named base_pipeline constrains what was actually run.
It does **not** affect any match score.

For **`REPORTED`** rows, `pipeline_specificity` is a **list parallel and positionally aligned to
`value`**: `value[i]` carries `specificity[i]`, same length and same order, each drawn from
`{named_pipeline | toolbox_only | in_house}`. A single-tool value is a **one-element list** (`value =
[C-PAC]` → `[named_pipeline]`); a multi-tool value pairs each tool with its own specificity (`value =
[BrainVoyager, custom software]` → `[toolbox_only, in_house]`). The ordering constraint is
**binding**: the two lists must be the same length and order for `REPORTED` rows, so a downstream
reader or matcher can attach each specificity to its tool. For **`DEFERRED_TO_CITATION`** and
**`NOT_REPORTED`**, `pipeline_specificity` is **blank** — deferrals list citations in `value`, not
tools, and there is nothing to classify. Multi-tool-plus-custom is common in this corpus (liu_2005,
mueller, cole, ciric); a singular field would force flattening real structure into one label.

Example mapping: C-PAC/CCS/fMRIPrep/XCP Engine → `named_pipeline`; SPM99/FSL/AFNI → `toolbox_only`;
author scripts → `in_house`. This converts the D2 reproducibility caveat into a citable COBIDAS
finding — *"N/19 papers name only a toolbox, which does not determine the preprocessing performed"* —
pairing with the version finding.

---

## Labeling procedure

1. **Label blind.** Do **not** open extractor output, `batch_v7_full`, or any grep/sweep artifact
   before deciding a paper. The denominator must be independent of the system being measured;
   anchoring to model output makes the hallucination rate a measure of *agreement*, not accuracy —
   the same firewall the extractor is held to, applied to the labeler. (This session is the reason:
   an LLM-filtered screen produced five false absences.)
2. Read the **full paper** (main text; SI where present — SI is absent from every corpus PDF, which
   is itself a recorded `corpus_completeness` state, not a gap to fill).
3. For every `REPORTED`/`DEFERRED`, record a **verbatim** supporting quote. The validator asserts the
   quote is present in the paper text; a quote that will not verbatim-match is a labeling error.
4. Fill **three** fields per paper: `status`, `value` (list), and `pipeline_specificity` (for
   `REPORTED`, a list parallel and positionally aligned to `value`; blank for `DEFERRED`/
   `NOT_REPORTED`).
5. `UNCLEAR` is not a label. If a case is not covered here, the protocol is **incomplete**: amend,
   bump the version, re-commit, **then** label that paper. Never bend a rule to fit a case after
   seeing it.

---

## Rater scope and reliability (v1: single-rater, author-labeled)

v1 ground truth is **single-rater**, produced by the **author — the developer of the extraction
system being scored**. This is a stated limitation, recorded here before any label exists: the labels
are **not independent of the system under evaluation**, so v1 metrics (Tier-A/Tier-B hallucination
rates, the three-way partition) are **indicative, not an independent benchmark**, pending external
validation.

**Non-blind papers (author-adjudicated, named for honesty).** Eight papers were read verbatim and
several were *ruled on* while drafting this protocol, so their labels reflect prior reasoning rather
than a blind first read: **wheaton_2004, agtzidis_2020, ciric_2017, viduarre_2017, derosa_2025,
braun_2015, mueller_2021, cole_2013**. The remaining corpus papers are closer to a blind first read,
but are still author-produced and inherit the single-rater limitation above.

**Mitigation (the standing requirement).** Even for the named cases, the author labels **strictly
against this protocol, not from memory**, so every label is reproducible from the protocol by a future
rater. A **verbatim supporting quote is recorded for every `REPORTED`/`DEFERRED`** (labeling
procedure step 3) — this is what makes the three-way partition and a future rater's cross-check
possible.

**Upgrade path (conditional, not committed).** A second (or third) rater and inter-rater reliability
— Cohen's **κ** for one, Fleiss' **κ** for a panel — are **future work, undertaken only if
publication is pursued and if warranted**; they are **not a prerequisite for v1**. If added, raters
label from this protocol alone, **blind to the author labels and to any tool output**. No rater count
or timeline is committed here.

**Author-labeler:** Jae Wook Cho · **Second/panel rater:** <<FILL>> · **Status:** deferred
(conditional on publication)

---

## Version-extraction backlog (context for a reader; not part of labeling)

The claim *"0/19 corpus papers report a pipeline version"* is **false as a statement about the
literature**. `extractor.py` hardcodes `base_pipeline.version` to `MissingFromPaper` (*"version is
never paper-stated here"*) and the extraction prompt never asks for a version, so AESPA has extracted
**zero** versions corpus-wide; `assess_coverage` reads that constant back out as COBIDAS coverage. At
least oconnor (*"C-PAC version 0.4.0"*), derosa (*"FSL suite (version 5.0.10)"*), and liu_2013
(*"version 1.1-beta"*) report explicit separate versions, and four SPM papers report fused versions.
A separate scoped session will (a) add version extraction to the prompt and (b) decide whether a
fused `SPM99` counts as a reported version. Until then, the COBIDAS version reframe rests on a
constant and must not be published as a literature finding.

**Consortium-data provenance (spec-expressiveness backlog).** A base pipeline reached via citation to
a dataset's pipeline **plus** local denoising steps (viduarre: HCP MPP via Glasser + ICA-FIX via
Griffanti) is a composition neither `base_pipeline` nor a single step field represents cleanly.
Spec-expressiveness item; recorded, not actioned.

---

## Changelog

- **v1.1 (2026-07-18):** `pipeline_specificity` is a list parallel to `value` for `REPORTED` rows
  (positionally aligned); singletons are one-element lists; blank for `DEFERRED`/`NOT_REPORTED`.
  Reason: multi-tool + custom-software papers require per-tool specificity. (No labels existed at
  amendment time; amended before active labeling.)
- **v1 (2026-07-18):** initial pre-registration — the twelve decisions, Tier-A/Tier-B value-matching,
  single-rater author-labeled scope (commit `9eff653`).
