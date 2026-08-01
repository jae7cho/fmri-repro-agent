# Pending target_space runs — outcomes PRE-COMMITTED (2026-07-31)

Two open items from scoring need a bedrock K=3 run (unavailable in the environment where the score was
computed). Both outcomes of both runs are committed **here, before the run**, so neither can be read
one-directionally. Harness: `extractor_mvp/scripts/run_pending_target_space.py` (model pin == the frozen
batch). Six calls total.

## Run 1 — liu_2005: is the target_space miss input-corruption?

**Setup.** Feed the reconstructed de-interleaved methods slice
(`ground_truth/liu_2005_deinterleaved_methods.txt`) directly as `ParsedPaper.text`, bypassing
`find_methods_section` — which on the real PDF triggers `methods_not_found → full-text fallback` and the
two-column interleaving that shreds the methods (see `pdf-glue-false-missing.md`). Frozen (corrupted)
result: target_space MISSING 3/3, `failure_reason=None`, raw=None — the "never saw an intact sentence"
signature.

**Slice-validity sanity check (must pass first).** The harness also reports `base_pipeline_name`. This
slice must recover **BrainVoyager**, matching the known-good base_pipeline 3/3 (2026-07-23). If
base_pipeline does NOT recover BrainVoyager, the reconstructed slice is wrong — **HALT and do not read the
target_space result.**

**Pre-committed outcomes (target_space, given the sanity check passes):**
- **Talairach appears (≥2/3):** input-corruption is DEMONSTRATED CAUSAL. liu_2005 moves out of the
  extraction-failure column into demonstrated-input-corruption (joins the demonstrated-causal set). The
  clean slice recovered a target the corrupted full-text hid.
- **Talairach does NOT appear:** the miss is GENUINE; the corruption hypothesis is REFUTED for this field.
  This is cole's outcome (glue looked causal, tested → refuted) and is **equally publishable** — a per-
  mechanism, per-paper claim tested, not inferred. liu_2005 stays a family-miss.

Either way the decomposition is honest; the run only decides which column liu_2005 sits in.

## Run 2 — binder: results-space leak, or conservative-miss?

**Setup.** Normal path (binder was never in the batch; its PDF is in the corpus). binder's methods contain
a statmap-projection sentence: *"Individual anatomical (SPGR) scans and SPMs were then projected into the
standard stereotaxic space of Talairach and Tournoux (1988)"* — Talairach applied to DERIVED maps, while
the timeseries stays native (label = `native_volume`, CALL 7(a)).

**Pre-committed outcomes:**
- **Extractor grabs Talairach** (EXTRACTED+Talairach → family_specified via the map): a **results-space
  leak** — the first LIVE instance of the CALL 7(a) failure mode (the extractor pulled a derived-map space
  into `target_space`). Scores ERROR vs `native_volume`.
- **Extractor returns MISSING** → maps to `absent`. **CORRECTION to the earlier framing:** this is NOT
  "binder scores correct." Under the committed map, MISSING → absent, and absent ≠ `native_volume`, so it
  scores ERROR. It surfaces a sibling of the family/absent gap: **`native_volume` is also unreachable via
  MISSING** — the extractor can't distinguish "kept in native space" (a positive choice) from "nothing
  found." More evidence for design (B) (split which-space from how-completely-specified).
- **Extractor emits EXTRACTED+native_volume:** would be correct — but **unreachable by construction.**
  binder's native is CALL 7(a)-inferred (no sentence states it; the evidence is an absence), and the
  value-support guard forbids an EXTRACTED value with no supporting quote
  (`target_space-call7-unreachable.md`). The extractor cannot produce this outcome.

So binder **cannot score correct** under the current architecture — it is one of the 2-of-19
unreachable-by-construction rows (capability-limited). The run does NOT test correctness; it tests **which
failure class** — results-space leak (grabs Talairach) vs the native_volume-via-MISSING gap — and closes
the denominator (18 → 19 with a prediction). Either way binder is capability-limited, not an accuracy error.

## After the runs

Update `ground_truth/target_space_README.md` (move liu_2005 to its resolved column; add binder's row and
class) and, if binder confirms the CALL 7(a) leak or the native_volume/MISSING gap, note it in
`target_space-false-missing.md` as a second axis of the same conflation.
