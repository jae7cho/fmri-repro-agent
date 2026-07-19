# Backlog: KB citation index (curated DOI → pipeline / step-default map)

**Status: BACKLOG — scoped, not built.** Cannot be validated until base_pipeline ground truth exists
(see `docs/ground-truth-protocol.md`); a citation-index resolution is only checkable against a labeled
answer key. Do not build ahead of the labels. This doc records the design and, more importantly, the
firewall line it must not cross.

## Origin

Labeling viduarre_2017 for base_pipeline ground truth surfaced the pattern: consortium and
standard-method papers defer to a **small, stable pool of citations**, repeatedly. viduarre + ciric
alone produced six of the recurring ones. The pool is roughly:

| citation | resolves to | scope |
|---|---|---|
| Glasser 2013 (NeuroImage 80:105-124) | HCP Minimal Preprocessing Pipeline | base_pipeline |
| Smith 2013 (NeuroImage 80:144-168) | HCP resting-state methodology | base_pipeline |
| Salimi-Khorshidi 2014 / Griffanti 2014 | ICA-FIX denoising | step (nuisance) |
| Behzadi 2007 / Muschelli 2014 | aCompCor | step (nuisance) |
| Power 2012 (FD>0.2) / Power 2014 | scrubbing / motion censoring | step (nuisance) |
| Pruim 2015 | ICA-AROMA | step (nuisance) |
| Friston 1996 | 24-parameter motion expansion | step (nuisance) |

**NOTE — DOIs above are unverified (from memory).** They are placeholders. If this is ever built,
every DOI in the index is a curation decision that must be checked against the actual paper, not
recalled. Treat the specific strings as illustrative.

Today each such deferral is a `CitationResolver` fetch-and-re-extract: a network round-trip plus a
full Layer-2 extraction pass, for a citation whose target is already known and fixed. A curated index
turns the recurring subset into a lookup.

## What the KB already supports

The KB pipeline entries already carry curated, sourced provenance (`versions[].param_defaults[]` with
`source:` strings and `proposed_confidence:`). Adding a `citations:` block is the same curation
pattern:

```yaml
citations:
  - doi: "<verify>"          # Glasser 2013
    first_author: "Glasser"
    year: 2013
    role: base_pipeline      # this citation IS this pipeline's defining paper
  - doi: "<verify>"          # Smith 2013
    first_author: "Smith"
    year: 2013
    role: base_pipeline
```

A `DeferredToCitation(ref="Glasser et al. 2013")` resolves against the index (DOI, else exact
first-author+year) → the KB pipeline id, **without fetching the paper**. Firewall-clean: the index
lives in the KB and is consulted only in `CitationResolver` (inference stage), never in the paper-only
extractor.

## The non-negotiable constraint (this is the whole point)

A citation index makes the **viduarre fabrication trivially easy to commit** — resolve
`Glasser et al.` → "HCP MPP" and silently present the field as extracted. That is exactly what the
v0.4.0 value-support guard exists to prevent, relocated from the model into the KB. The line that must
hold:

- `base_pipeline` **status stays `DEFERRED_TO_CITATION`.** The paper deferred; that fact is immutable
  and belongs to the extractor, not the KB.
- The resolved pipeline is emitted as an **`INFERRED_DEFAULT` carrying a `basis`** — never as
  `EXTRACTED`, never overwriting the deferral status. `ProvenancedField` already couples
  `DeferredToCitation` for inference (rejects `NOT_APPLICABLE` on that arm), so this is the intended
  path.

The honest chain: *paper deferred to Glasser 2013 → Glasser 2013 is the HCP MPP paper
(KB-curated, DOI-matched) → INFERRED_DEFAULT: HCP MPP, basis=<see open question>.*

## Open question — new basis tier vs reuse `prior_publication`

The taxonomy (`provenance.py` `BASIS_CEILINGS`) already has `PriorPublicationBasis` (citation, ceiling
0.60). Two options:

1. **Reuse `prior_publication`.** Zero schema change. But 0.60 undersells a curated DOI match — a
   citation-index hit is not an inference *about* the paper, it is a lookup of a fixed, human-verified
   fact (this DOI = this pipeline's defining paper). Lumping it with generic prior-publication
   inference loses that.
2. **Add a `curated_citation` basis** (higher ceiling, e.g. ~0.85). More honest provenance and
   distinguishable in output/Tier-3 checks. Costs a schema addition + the version ceremony, and adds a
   `CuratedCitationBasis(citation, kb_pipeline_id, doi)` typed ref to the `Basis` union.

Decision needed before build. Draft lean: option 2, because the reliability difference is real and the
basis type is the thing a Critic would want to check ("does this DOI actually match this KB entry?").
Not decided here.

## The higher-value target: step-level citations, not base_pipeline

base_pipeline has only 4 KB pipeline entries; the base-pipeline index serves a handful of papers. The
**step-level** citations (ICA-FIX, aCompCor, scrubbing thresholds, ICA-AROMA, Friston-24) have **no KB
home at all today**, recur more often, and carry *parameters* (aCompCor: 5 WM + 5 CSF components;
Power scrubbing: FD>0.2). ciric's entire methods section is built from these. A citation index keyed to
**step defaults** is where this earns its keep — resolving "aCompCor (Behzadi et al., 2007)" to its
default nuisance config as `INFERRED_DEFAULT`, status untouched. Prioritize the step index over the
base-pipeline index.

## Deferral targets are not guaranteed reproducible

A cited work a paper defers to may itself name only a toolbox plus custom/in-house code — e.g.
Liu 2005 (in-corpus) labels as base_pipeline = `[BrainVoyager (toolbox_only), custom software written
in Matlab (in_house)]`. So a paper deferring to Liu 2005 resolves to something partly irreproducible
(unshared Matlab code), no more recoverable than a MISSING. Consequences for the citation resolver:

1. Resolution must distinguish "resolved to a recoverable pipeline" from "resolved to something no
   more reproducible than MISSING" — **deferral != recoverability** (the agtzidis/Poldrack
   genre-gesture problem, one hop deeper).
2. Multi-hop chains (paper X → Liu 2005 → BrainVoyager) must terminate correctly and, if a chain ends
   in another deferral or a genre gesture, return "deferred, unresolvable" rather than loop or
   fabricate.
3. Scoring the resolver requires **separate ground truth** for (a) the deferral (extractor's job:
   paper X defers to Liu 2005) and (b) the resolution target (Liu 2005's pipeline) — the current
   base_pipeline protocol captures only (a).

## Cautions (all learned the hard way this arc)

1. **Curation is where bias enters.** Every `citation → pipeline/step` mapping is a human assertion.
   Same discipline as the ground-truth labels and the value-match alias table: **commit the index
   before scoring**, keep it **minimal** (only citations the corpus actually produces, each annotated
   with the motivating paper), and have the **second rater review it**. An index grown to make papers
   resolve is tunable in exactly the way the alias table is.
2. **DOI/author-year matching is a matching problem — and matching has bitten this project three
   times** (`ants ⊂ Avants`, `\bspm\b` vs SPM99, greedy version-strip). Prefer DOI when the resolver
   has it; fall back to exact (first_author, year); **never substring on author names**
   (`Glasser` ⊂ ...). Needs its own small test set, including the bracketed-marker forms pypdf
   produces (`[40]`).
3. **Validate against ground truth, not intuition.** Whether a citation-index resolution is *correct*
   is only answerable once the labeled answer key exists. This is post-ground-truth work.

## Relationship to other backlog items

Consortium-data items now share one theme — consortium papers defer to a small fixed citation pool,
and the KB could hold it:

- **version extraction** (`base_pipeline.version` is hardcoded to MissingFromPaper; the "0/19 report a
  version" claim is a constant, not a literature finding — see `ground-truth-protocol.md`),
- **consortium composition** (a base pipeline reached via citation *plus* local denoising —
  viduarre: HCP MPP via Glasser + ICA-FIX via Griffanti — is a shape neither base_pipeline nor a single
  step field represents cleanly),
- **deferral reproducibility** (above),
- **this citation index**.

Consider scoping them as one "consortium-data provenance" session after the ground truth lands.
