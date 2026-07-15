# Development log

Contemporaneous dated record of project sessions. Each entry: date, hours, what I worked on. Maintained as evidentiary record.

---

## 2026-05-19

Project repository initialized. Scaffolding created via Claude Code session.

---

## 2026-07-14

Hours: 21:24 ET

v0.4.0. Bumped `Preprocessing.schema_version` 0.3.0 -> 0.4.0 with the full version
ceremony: new live root `spec/v0_4_0.py`, `spec/v0_3_0.py` demoted to a bare
`SCHEMA_VERSION` constant, and a 0.3.0 -> 0.4.0 migration hop that is a pure re-stamp
(the sole delta is an optional-default field, so no document transform runs; the
migrator id is now generic). Added `Extracted.span_recovered` (optional, default
False) in the version-stable provenance layer — it marks an extraction whose
char-offset span was located only by the corrupted-source tolerant tier (span_resolver
tier 5), not a clean match. Consumed those recoveries: `_process_field` and
`_build_base_pipeline` now keep a tier-5 recovered span instead of dropping it, marking
`span_recovered=True`. Added the value-support guard (Option A) on `base_pipeline`:
before promoting a recovered pipeline name to EXTRACTED, it checks the model's own value
is tolerantly present in its own quote (firewall-clean, no KB at extraction); a
recovered-but-unsupported citation-shaped quote (e.g. "...described by Glasser et al.")
is reclassified to DeferredToCitation rather than fabricating a name. Committed as 2560bb1.
