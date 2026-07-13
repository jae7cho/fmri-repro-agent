# Fix (staged, inert): tolerant span-resolution + the v0.4.0 gate it revealed

**Follows** [span-resolution-hard-drop.md](span-resolution-hard-drop.md) (Phase 1 diagnosis) and its
keep/reject partition (8 keep / 2 reject). This records what was built, what is deliberately held,
and why the honest completion is a v0.4.0 release — not a rushed end-of-session schema edit.

## What shipped (live but INERT — production output byte-identical to HEAD)

`span_resolver.py` gains **tier 5**, a corrupted-source tolerant match that fires ONLY after every
existing exact/near tier returns `quote_not_found`:

- Folds the three **general** pypdf mangles — whitespace-DELETION (run-together words / shattered
  `C-P A C`), injected citation markers (`[ 62]`), all hyphens — composed on top of the existing
  Unicode normalizer (so ligatures / curly quotes / split units are already handled).
- Substring-exact after normalization (**never** fuzzy / edit-distance), span in **original**
  coordinates, **re-verified fail-closed** (the recovered slice must re-normalize to the needle).
- A tier-5 match sets `SpanResolution.recovered=True`.
- **Excludes** the font-specific `×→/C2` glyph mangle: `/C<digit>` are font glyph codes that map to
  different glyphs across papers, so folding `/C2→×` globally risks a WRONG match — it fails the
  never-fuzzy invariant. agtzidis's 2 dimension-drops stay unrecovered by design.

**The builders (`_process_field`, `_build_base_pipeline`) treat a `recovered` span as unresolved for
now** — so tier 5's recoveries are computed but not consumed. Production output is identical to HEAD:
the full 229-test suite passes unchanged, and the 8 corrupted-source keeps remain a documented
false-MISSING lower bound rather than being silently promoted.

### Validation (on the Phase-1 drops)
- **8 / 10 recover** with real, auditable span text (oconnor, weber×3, viduarre, derosa×2, liu).
  agtzidis×2 (`×→/C2`) correctly stay unresolved.
- **arm (ii) — no currently-resolving span moves:** true by construction (tiers 1-4 untouched; tier 5
  unreachable when an earlier tier matches), pinned by `test_exact_match_not_recovered`, and proven
  by the unchanged suite.
- **arm (iii) — hallucination guard:** the corpus has **no natural hallucination case** (Phase-1: all
  drops trace to real mangled source), so it is verified **synthetically** —
  `test_hallucination_still_fails` asserts a fabricated quote still returns `None` after tier 5.
- Tests: `tests/test_span_resolver_tolerant.py` (9, incl. the ×→/C2 exclusion and ambiguity guard).

## What is DELIBERATELY held for a deliberate v0.4.0

Consuming tier-5 recoveries **honestly** requires marking them, and the marker cannot live on the
extraction without a schema change. This is the gate.

- **`span_recovered` must ride on `Extracted`** — not a diagnostic sidecar (detachable: a provenance
  marker that can silently drop from the value it qualifies) and never `confidence` (that launders a
  provenance fact
  into an epistemic claim about the value — a category error for a provenance tool). On-object is
  the only honest home, and `Extracted` is in the version-STABLE `provenance.py`.
- **The three pieces are inseparable:** tier-5 **un-masks** viduarre (its quote is corrupted —
  `usingthe`, verified — so tolerant resolve grounds it). Consuming that recovery without the
  attribution-guard would promote `viduarre → base_pipeline = HCP MPP, EXTRACTED` — a name
  **fabricated from a citation** ("described by Glasser et al."). So tier-5-consumption, the
  `span_recovered` flag, and the attribution-guard ship **together or not at all**. There is no
  "free standalone guard" — the guard only matters once tier 5 un-masks the case.
- **The attribution-guard** (verified constructible): before promoting a base_pipeline **name** to
  `Extracted`, if its quote is a bare attribution (`described by | following | as (described )in |
  procedure of … [Author]`) **and no pipeline name is present in the quote** (checked against the KB
  alias list — so "followed fMRIPrep (Esteban 2019)" is NOT swallowed), construct
  `DeferredToCitation` instead. Reuses the existing frozen state; the ref parses lexically from the
  quote; the span comes from tier 5. viduarre → `DeferredToCitation(Glasser et al.)`, which is the
  correct four-state answer the model should have produced.
- **#4 (derosa referent-binding)** resurfaces as a recovered EXTRACTED once tier 5 is consumed; it is
  handled at its own layer by the [temporal firewall](temporal-firewall-fix.md), not here.

### v0.4.0 cost — measured, and larger than the frozen-test-only estimate
The frozen-provenance tests absorb a new optional field cleanly (round-trip + substring `$defs`
checks, no byte-golden). But the full **version ceremony** is the real surface: bump
`Preprocessing.schema_version` Literal, add `v0_4_0.py`, add the `0.3.0→0.4.0` migration hop, and
update ~10 files referencing `0.3.0`, plus the version tests. That is a deliberate release, not a
half-day quick-add — so it is held for a focused change, consistent with "its own clean v0.4.0."

## v0.4.0 execution plan (ready to run — this doc is the spec of record)

Prerequisite already in place: tier 5 is in `span_resolver.py` and inert. The two builder call sites
to flip each carry a `v0.4.0-PENDING` code comment — `grep -rn "v0.4.0-PENDING"
extractor_mvp/src/extractor_mvp/extractor.py` locates them exactly.

1. **Schema + version ceremony.** Add `span_recovered: bool = False` to `Extracted` in
   `src/fmri_repro/spec/provenance.py`. Bump `Preprocessing.schema_version` Literal to `"0.4.0"`; add
   `src/fmri_repro/spec/v0_4_0.py` mirroring `v0_3_0.py`; add the `0.3.0->0.4.0` hop in
   `migrations.py` (an optional-default field is a near no-op migration that just re-stamps). Update
   the ~10 files/tests referencing `0.3.0`. The frozen-provenance tests are round-trip + `$defs`
   substring (no byte-golden), so an optional field slots in without breaking them.
2. **Builder flip.** At the two `v0.4.0-PENDING` sites (`_process_field`, `_build_base_pipeline`):
   consume a `recovered` span instead of treating it as unresolved, and construct
   `Extracted(..., span_recovered=res.recovered)` so a normalization-recovered extraction is never
   indistinguishable from a clean one.
3. **Attribution-guard** (in `_build_base_pipeline`, before promoting a base_pipeline NAME to
   `Extracted`): if the name's `verbatim_quote` matches the bare-attribution shape
   (`described by | following | as (described )in | procedure of ... [Author]`) AND no KB pipeline
   alias appears in the quote (build aliases from `fmri_defaults_kb` as the extractor already does),
   construct `DeferredToCitation` instead — ref parsed lexically from the quote, span from tier 5.
   Discriminator: "followed fMRIPrep (Esteban 2019)" has a name -> stays EXTRACTED; viduarre's
   "described by Glasser et al." has none -> `DeferredToCitation`. This is the anti-fabrication gate;
   without it, step 2 promotes viduarre to a fabricated `base_pipeline = HCP MPP`.
4. **Three-arm regression (the gate, corpus-wide).**
   (i) RECOVERY: the Phase-1 corrupted-source drops resolve; PRINT each recovered span's source text
       so a human sees it contains the mention (auditable, not asserted).
   (ii) NO SPURIOUS MOVE: every currently-resolving quote resolves to the BYTE-IDENTICAL span before
       vs after — a mechanical hard assertion, not eyeballed. Guaranteed by construction (tier 5 only
       fires after exact-fail); a failure here means the tier ordering broke and is a STOP.
   (iii) HALLUCINATION GUARD: a synthetic fabricated quote still fails after tolerant matching (the
       corpus has no natural case; keep `test_hallucination_still_fails`).
   Plus: viduarre -> `DeferredToCitation` (not EXTRACTED); the 8 keeps -> `EXTRACTED` with
   `span_recovered=True`; the 2 value-mislocalization cases (viduarre-class) must NOT become clean
   EXTRACTED.
5. **Verify.** Full suite (extractor_mvp + fmri_repro) green; re-run `scripts/hard_drop_audit.py` to
   confirm the keeps now recover flagged and the value-mislocalization cases stay out.

## Net
The hard part is de-risked: the tolerant matcher is built, validated (8/10, auditable), safe by
construction (arm ii), guarded against hallucination (arm iii synthetic), and shipped **inert** so
nothing regresses. What remains is the coherent v0.4.0 release above — "recover correct extractions
from corrupted-source spans, honestly marked with `span_recovered`, and reclassify citation-shaped
base_pipeline quotes as `DeferredToCitation`" — to be executed as a deliberate release from the plan
in this doc.
