# Project origins

## Intellectual provenance

**Empirical motivation.** Manual fMRI reproduction often fails at expert level — Bowring, Maumet & Nichols (2019), *Human Brain Mapping* 40(11):3362–3384, doi:10.1002/hbm.24603; with correction in *Human Brain Mapping* 42(5):1564–1578, doi:10.1002/hbm.25302. Analytic flexibility — Botvinik-Nezer et al. (2020), *Nature* 582:84–88, doi:10.1038/s41586-020-2314-9 (NARPS) — and pipeline/software heterogeneity is the norm — Carp (2012), *NeuroImage* 63:289–300.

**Gap targeted.** Paper → executable pipeline configuration is unaddressed end-to-end. NeuroBridge LLM-extraction work (Turner et al. 2025, *Frontiers in Neuroinformatics* 19:1609077, doi:10.3389/fninf.2025.1609077; NIDA R01 DA053028) achieves ~95% on 12 structural MRI scalar parameters. NARPS Open Pipelines (Empenn / INRIA Rennes).

**Architecture.** Multi-agent decomposition adapted from PaperCoder (Seo et al., arXiv:2504.17192) and AutoP2C (Lin et al., arXiv:2504.20115). Three-tier verification grounded in Gou et al. ICLR 2024 (CRITIC, arXiv:2305.11738 — self-critique works only when tool-grounded) and Huang et al. ICLR 2024 (arXiv:2310.01798 — LLMs cannot reliably self-correct; independent verifier required). Scientific RAG patterns from PaperQA2 (Future-House).

**Provenance schema.** Two-stage extraction/inference chain designed to map onto W3C PROV / BIDS-Prov / NIDM per Maumet et al. (2016), *Scientific Data* 3:160102, doi:10.1038/sdata.2016.102.

**Domain experience.** Pre-existing familiarity with BIDS, fMRIPrep, AFNI/FSL/SPM, and the test–retest reliability literature from prior research employment (see below).

## Prior public work

- **Cho, J.W.**, Korchmaros, A., Vogelstein, J.T., Milham, M.P., Xu, T. (2021). Impact of concatenating fMRI data on reliability for functional connectomics. *NeuroImage* 226:117549. doi:10.1016/j.neuroimage.2020.117549.
- Wang, X., Li, X.-H., **Cho, J.W.**, et al. (2021). U-net model for brain extraction: Trained on humans for transfer to non-human primates. *NeuroImage* 235:118001. doi:10.1016/j.neuroimage.2021.118001.
- Xu, T., Kiar, G., **Cho, J.W.**, Bridgeford, E.W., Nikolaidis, A., Vogelstein, J.T., Milham, M.P. (2023). ReX: an integrative tool for quantifying and optimizing measurement reliability for the study of individual differences. *Nature Methods* 20:1025–1028. doi:10.1038/s41592-023-01901-3.

## Timeline

- **Conceived:** 5/8/2026.
- **First commit:** 5/19/2026.
- **First eval-passing run:** [DATE PLACEHOLDER — first run meeting Chat-4 MVP thresholds: extraction precision ≥95%, hallucination rate <2%, MISSING-field detection ≥90%].
