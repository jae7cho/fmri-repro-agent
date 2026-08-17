# Pre-registration: `motion_correction.method` reachability probe and `span_role` scoring map

**Pre-registration, committed BEFORE the run — the run has not happened.** This governs the reachability probe and the `span_role` scoring map (extraction and scoring), **not labelling**: the protocol governs labelling. On record before the probe runs, so the falsifiability is on file, not in conversation.

**Reachability probe (gates the state-map).** Build `motion_correction.method` only. Papers: power_2014,
binder_1999, liu_2013, derosa_2025, plus agtzidis_2020 (positive control → SPM12) and poldrack_2015
(APPLY control → must not yield applywarp). **K = 10** per paper, per `variance.md` and the temporal
finding's fixed→fixed 4/10 → 0/10. Record `verbatim`, `resolved`, `resolution`, span per draw. **Question:
is `described_only` expressible — not whether the extractor is accurate. No accuracy figure may be
computed from or cited out of this run.**

*derosa's four pre-declared readings:*
1. `FSL` → binding-test violation (CALL 1 v1.5). Extraction error.
2. `ICA-AROMA` → CALL 4 territory. Extraction error, **different class**.
3. Six-motion-regressors (§2.4.3) or mean-FD (§2.4.9) text → **CONSUME leak** (CALL 10 Axis 2).
   Extraction error, **third class**. Live because the label's Notes record that realignment demonstrably
   occurred and only its downstream use is stated.
4. `verbatim="motion correction"`, `resolved=None` → **the target**; demonstrates reachability.

*The probe cannot validate CALL 10.* It tests whether a state is expressible, not whether the call is
right. Readings 1–3 are **extraction errors to record**, not evidence against the call; reading 4 is
reachability, not correctness. The inference is also **asymmetric**: a single `verbatim=None` draw on power
or binder demonstrates unreachability, while 40 clean draws are evidence *for* reachability and not proof
of it, given the documented non-stationarity. State both directions before the run.

*Iterating the stanza on probe results adds no new contamination.* All six probe papers are already inside
the contaminated union of 16 — power_2014, binder_1999, derosa_2025, agtzidis_2020 and poldrack_2015 are
`co-adjudicated`; liu_2013 is in CALL 10's fitted seven. So the probe is a safe place to iterate stanza
wording. It is **not** a licence to extend that iteration to any of the three clean papers (liu_2005,
tang_2025, wheaton_2004), which are the only cells left that a held-out reading could ever touch.

**Span column in the scoring map.** Add `span_role` ∈ {`estimate`, `apply`, `consume`, `host`,
`out_of_scope`}; a cell counts correct only when **state, value and span_role** all match. ciric is the
case that justifies it — right value, wrong span, invisible to a value-only scorer, and both prior maps
(`target_space_scoring_map.csv` has columns `resolved, resolution, label_state, rationale` — no span) would
have scored it correct. **State in the map's own rationale that this makes the motion figure STRICTER than
either prior field's, so it is not comparable to base_pipeline's 82.4% or target_space's 11/17** — a lower
motion number is a harder scoring rule before it is a worse extractor.
