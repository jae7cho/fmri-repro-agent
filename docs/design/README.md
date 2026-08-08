# Historical design records

The documents in this directory were authored earlier in the Claude project, lived there uncommitted,
and were brought under version control on **2026-08-07**. They are **historical records of design
reasoning, not currently authoritative** — a document here is authoritative only where a committed
artifact (the spec, a ground-truth protocol, or `docs/DESIGN_cobidas_coverage.md`) explicitly references
it. Read them for *why* a decision was made, not as the current contract; the code and the spec are the
contract. They are committed **verbatim**, including claims that were true at authoring and have since
gone stale.

## Known-stale claims (flagged so no one re-derives from them)

- **`DESIGN_anatomical_steps_v0_3_0.md` contains a claim now known FALSE.** Its verification-boundary note
  states *"COBIDAS PDFs in the project are zipped page images (no text layer), so Table D.3's exact row
  titles were NOT read directly — row names follow the repo catalog."* **They are not page images — D.3
  reads fine.** That is exactly how the *Motion correction* seven-bullet row was quoted verbatim in
  `docs/ground-truth-protocol-motion_correction.md` §1 and `docs/DESIGN_cobidas_coverage.md` §3. Do **not**
  re-derive D.3 row titles from the repo catalog on the strength of that stale caveat.
- `docs/DESIGN_cobidas_coverage.md` (committed separately at `docs/`, not here) carries a stale `_assemble`
  line reference (§1: `645–725`; actual ~803), noted in its own Amendment 1.

## Contents

- **`DELTA_protocol_reason_partition.md`** — the reason-partitioned completeness rendering in `to_protocol`
  (`specified · inferred · deferred · not reported · unmappable · not covered by extractor`). **Load-bearing:**
  `docs/DESIGN_cobidas_coverage.md` §5 depends on this "reason-partition distinction one level up"; that
  dependency was dangling until this commit.
- `DESIGN_anatomical_steps_v0_3_0.md` — the v0.3.0 anatomical-target steps design (see the stale-claim flag above).
- `DESIGN_methods_finder.md` — the methods-section finder design.
- `DESIGN_protocol_emitter.md` — the `to_protocol` emitter design.
- `DESIGN_temporal_standardization_build1.md` / `_build2.md` / `_build3.md` — the temporal-standardization build arc.
- `DESIGN_v6_full20_attribution.md` — the v6 full-20 attribution design.
