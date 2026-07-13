# Finding: chen · temporal_standardization.method is a referent-binding false positive

**Harness:** `extractor_mvp/scripts/chen_flip_probe.py` · **Model (pinned):** bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0, temperature 0 · **K=20** on byte-identical input (methods-slice sha256[:16] `1a6d8afbec64e926`).
Raw per-draw dump: `extractor_mvp/results/CHEN_FLIP_RAW.md` (gitignored).

## Two findings, read together

**1. The EXTRACTED state is a mis-binding (this K=20).** All 20 draws that extracted the field
cite the *same* sentence — about **SFC** (surface-based functional connectivity) being normalized,
NOT the BOLD signal. Binding it to `temporal_standardization.method = voxel_temporal_zscore` is a
**referent-binding error**: the prompt scopes this field to "standardization of the BOLD SIGNAL
ITSELF", and this sentence is about a derived connectivity metric. So when the field is EXTRACTED,
it is EXTRACTED *for the wrong reason*; the defensible answer for chen is arguably MISSING.

**2. The flip did NOT reproduce — the rate is not even stationary.** This K=20 returned
**20/20 EXTRACTED, 0 MISSING**. The earlier variance run (`docs/findings/variance.md`, N=15, a
different day) returned **10 EXTRACTED / 5 MISSING** on the same slice + model. Same bytes, same
temperature, and the EXTRACTED/MISSING split moved from 67% to 100%. The run-to-run flip is real,
but its *rate* drifts across sessions — so no single K characterizes it, and this sample cannot
explain the MISSING mechanism (there were no MISSING draws to inspect). What this run explains is
the EXTRACTED side; the MISSING side needs a session that actually produces MISSING draws (larger
K, or repeated across days).

Put together: the flip is the model **wavering on an incorrect binding** of the SFC sentence, and
how often it commits to that wrong binding is itself unstable across sessions.

## temporal_standardization.method across the draws

- EXTRACTED: **20/20** (100%) · MISSING: **0/20** (0%) — *this session; contrast N=15 → 10/5 earlier*

### EXTRACTED draws grouped by verbatim_quote (the key output)

| count | bucket | verbatim_quote |
|---|---|---|
| 11 | REFERENT-BINDING (ReHo/connectivity z-scoring) | 'Of note, this surface-based SFC was estimated using the same preprocessed rfMRI data as ReHo but normalized (0 mean and 1 variance).' |
| 9 | REFERENT-BINDING (ReHo/connectivity z-scoring) | 'This surface-based SFC was estimated using the same preprocessed rfMRI data as ReHo but normalized (0 mean and 1 variance).' |

### MISSING draws — searched_terms / sections_searched

_(no MISSING draws)_

### Cross-check: intensity fields on EXTRACTED-temporal runs (bleed test)

| run | temporal quote | intensity_convention | intensity_value | int_value quote |
|---|---|---|---|---|
| 1 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 2 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 3 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 4 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 5 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 6 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 7 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 8 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 9 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 10 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 11 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 12 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 13 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 14 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 15 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 16 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 17 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 18 | 'This surface-based SFC was estimated using the sam' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 19 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |
| 20 | 'Of note, this surface-based SFC was estimated usin' | extracted:fsl_grand_mean_10000 | extracted:10000 | 'The subsequent CCS functional pipeline discarded t' |

## base_pipeline_name value wobble (phrasing vs source ambiguity)

| count | value | verbatim_quote |
|---|---|---|
| 14 | 'Connectome Computation System' | 'The Connectome Computation System (CCS: https://github.com/zuoxinian/CCS) was developed to provide a multimodal image analysis platform for the discovery science of human brain function by integrating three main MRI data processing packages [ 48– 50] with our MATLAB implementations of various computational modules for image quality control, surface-based rfMRI metrics, data mining algorithms, reliability and reproducibility assessments and visualization.' |
| 6 | 'Connectome Computation System (CCS)' | 'The Connectome Computation System (CCS: https://github.com/zuoxinian/CCS) was developed to provide a multimodal image analysis platform for the discovery science of human brain function by integrating three main MRI data processing packages [ 48– 50] with our MATLAB implementations of various computational modules for image quality control, surface-based rfMRI metrics, data mining algorithms, reliability and reproducibility assessments and visualization.' |

base_pipeline distinct values=2, distinct quotes=1 → SAME sentence, different rendering (phrasing-only wobble).

## Diagnosis

**REFERENT-BINDING**, not field bleed. All 20 EXTRACTED draws cite the SFC-normalization sentence
("...surface-based SFC was estimated using the same preprocessed rfMRI data as ReHo but normalized
(0 mean and 1 variance)"). The 11/9 split between the two quote strings is a two-word boundary
wobble ("Of note, " prefix), not two different sentences — the driver is one sentence.

**Bleed hypothesis REFUTED.** On every EXTRACTED-temporal run, `intensity_convention` independently
returned `fsl_grand_mean_10000` / `intensity_value = 10000` citing a *different* sentence ("The
subsequent CCS functional pipeline discarded..."). intensity_normalization is not leaking into
temporal_standardization; the two fields bind to different sentences, both stably. So this is
referent-binding to the SFC sentence, not the grand-mean sentence bleeding across.

**base_pipeline value wobble is phrasing-only** (as hypothesized): 1 distinct quote, 2 renderings
("Connectome Computation System" ×14 vs "...(CCS)" ×6) — same source sentence, the model just
includes/omits the acronym. Not source ambiguity.

Implication for a future fix (NOT taken here): the lever is the field's *scope prompt* — tighten
the BOLD-signal firewall so an SFC/connectivity-normalization sentence cannot bind
temporal_standardization. That would likely convert chen's EXTRACTED draws to a (correct) MISSING,
and should be scored over K runs across sessions given the non-stationary rate above.

Caveat: K=20, one paper, one session; the EXTRACTED/MISSING split is a point estimate and drifts
across sessions (see the two-findings note above and [variance](variance.md)). The referent-binding
diagnosis is driven by the verbatim quote grouping, which was stable at 20/20.
