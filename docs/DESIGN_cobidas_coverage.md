# DESIGN — COBIDAS coverage section (emitter-side)

*Grounds the `not covered by extractor` figure in the actual standard. No schema change, no `_assemble` change. Source: COBIDAS Report v1.0 (2016/5/19), Table D.3 "Preprocessing Reporting", pp. 53–58 — read verbatim.*

---

## 0. What the source actually says (this changes the plan)

**`Mandatory = Y` means "reporting is mandatory *if the step was performed*."** Verbatim from D.3:

- Brain extraction — *"If performed, report:"* — `Y`
- Slice time correction — *"If performed, report:"* — `Y`
- Spatial smoothing — *"If this preprocessing step is performed, report:"* — `Y`
- T1 stabilization — *"(if not already performed by scanner)"* — `Y`
- Gradient distortion correction — *"(If not already described as part of motion susceptibility correction.)"* — `Y`

**Consequences:**

1. **Silence on a conditional row is NOT a COBIDAS violation.** A paper that never despiked owes no despiking report. Non-compliance is *unfalsifiable from text alone* for conditional rows — the standard cannot distinguish "didn't do it" from "did it, didn't say." That is the absence-vs-hallucination problem appearing inside the reporting standard itself, and it should be stated as a finding, not engineered around.
2. **Emitting a step full of "REQUIRED — you must specify" for an unaddressed conditional row is a false instruction** — it asserts an operation neither the paper nor the standard claims occurred.
3. **Exactly one row is unconditionally mandatory:** *Software* — *"For each software used, be sure to include version and revision number."* No conditional clause; conditional only on having used software, which is universal. (*Software citation* — URL/RRID — is `N`, so the bar is specifically **version and revision number**.)

**The citable claim:** 0/19 corpus papers naming a base pipeline report its version (all `version_deferred_to_kb`). A universal, unconditional, verifiable COBIDAS failure on the standard's most basic item — and the reason `date_inferred_version` exists at all.

---

## 1. Why `_assemble` must NOT change

`_assemble` (extractor.py:645–725) hardcodes 7 steps for every paper, unconditionally. Step presence carries **zero information**. And for the 12 never-emitted kinds the extractor targets **no field**, so "emit on evidence" can never fire — it would be identical to today.

Therefore: emission stays as-is; coverage accounting moves to the emitter, where the denominator (the standard) belongs. This also fixes the inversion where `_assemble` unconditionally emits `intensity_normalization`, the *only* non-mandatory row.

---

## 2. The predicate (forced, not chosen)

> A COBIDAS row is **ADDRESSED** iff ≥1 field, on any emitted step kind mapping to that row, has extraction status `EXTRACTED` or `DEFERRED_TO_CITATION`. Otherwise **UNADDRESSED**.

Only extraction-arm state. No `INFERRED_DEFAULT` (an inferred value is not a *report*), no base-pipeline implication. Firewall intact.

**Software row special case:** maps to `base_pipeline`, not a step. The mandatory content is *version and revision number*, so the row is ADDRESSED iff `base_pipeline.version` is `EXTRACTED`. A `date_inferred_version` does **not** address it — COBIDAS asks the author to report, not the tool to guess.

---

## 3. Row registry (fMRI-preprocessing scope; transcribed verbatim)

Rows for other modalities (Diffusion ×4, Perfusion ×2), derived features (*Resting state fMRI feature*), and *Quality control reports* are **out of scope** for a preprocessing protocol — record the exclusion explicitly rather than silently dropping them.

| row_id | D.3 Aspect | Mandatory | Conditional language | Spec kinds |
|---|---|---|---|---|
| `software` | Software | Y | **none — UNCONDITIONAL** | `base_pipeline` (version) |
| `software_citation` | Software citation | N | — | *(unmodeled)* |
| `t1_stabilization` | T1 stabilization | Y | "if not already performed by scanner" | `nonsteadystate_removal` |
| `brain_extraction` | Brain extraction | Y | "If performed" | `brain_extraction` |
| `segmentation` | Segmentation | Y | "For structural images" | `segmentation` |
| `slice_time_correction` | Slice time correction | Y | "If performed" | `slice_time_correction` |
| `motion_correction` | Motion correction | Y | bare "Report:" | `motion_correction` |
| `gradient_distortion_correction` | Gradient distortion correction | Y | "If not already described as…" | `distortion_correction` |
| `distortion_correction` | Distortion correction | Y | "Use of **any**…" | `distortion_correction` |
| `coregistration` | Function-structure (intra-subject) coregistration | Y | bare "Report:" (+ "might not be necessary if…") | `coregistration` |
| `intersubject_registration` | Intersubject registration | Y | bare "Report:" | `spatial_normalization`, `surface_projection` |
| `intensity_correction` | Intensity correction | Y | descriptive | `intensity_correction` |
| `intensity_normalization` | Intensity normalization | **N** | — | `intensity_normalization` |
| `artifact_structured_noise_removal` | Artifact and structured noise removal | Y | bare "Report:" | `ica_denoise`, `compcor`, `nuisance_regression` |
| `volume_censoring` | Volume censoring | Y | bare "Report:" | `despike`, `scrub` |
| `spatial_smoothing` | Spatial smoothing | Y | "If this preprocessing step is performed" | `spatial_smoothing` |

**16 rows; 14 mandatory, 2 non-mandatory.**

**Note the repo's `cobidas_row` ClassVars are NOT 1:1 with D.3 rows.** `spatial_normalization` (`intersubject_registration_volume`) and `surface_projection` (`surface_projection`) both realize the single D.3 row *Intersubject registration* — D.3 folds surface sampling into it (*"if projection from volume to surface space, how were voxels sampled…"*). So the registry maps kinds → true D.3 rows directly; do not derive the denominator from `cobidas_row` alone.

**Divergences (no D.3 row):** `temporal_filtering`, `temporal_standardization`. Report separately as "beyond COBIDAS", never counted in the denominator.

---

## 4. Conservative compliance rule (locked)

> Claim non-compliance **only** where the standard's language is unconditional.

So only `software` can be rendered as a violation. Every other unaddressed mandatory row renders as *"not reported whether performed"* — an honest gap. Bare-`Report:` rows (motion correction, coregistration, intersubject registration, structured-noise removal, volume censoring, intensity correction, segmentation) are treated as **conditional by default**: their language lacks an explicit universal obligation, and a paper cannot report a method for an operation it did not perform.

*(This is the one interpretive judgment in the design. It errs toward under-claiming. If the PI reads the bare-`Report:` rows as unconditional, the violation set widens — a decision to make explicitly, not by default.)*

---

## 5. Rendering

```markdown
## COBIDAS D.3 coverage (preprocessing)

Addressed in source: 4 / 16 rows   ·   Non-mandatory: 2   ·   Beyond COBIDAS: 2 steps

### Not reported (mandatory, unconditional)
- Software: version and revision number NOT REPORTED — COBIDAS D.3 requires this for
  each software used. (Pipeline named: CCS. Version inferred by AESPA, not reported by the paper.)

### Not reported whether performed (mandatory if performed)
- Motion correction · Slice time correction · Coregistration · Distortion correction ·
  Intensity correction · Volume censoring · Artifact and structured noise removal ·
  Spatial smoothing · Brain extraction · Segmentation · T1 stabilization
  (Silence is not a COBIDAS violation for these rows; the standard requires reporting
  only if the step was performed. Presence cannot be determined from the text.)

### Optional per COBIDAS
- Intensity normalization (N) · Software citation (N)

### Beyond COBIDAS (AESPA extensions)
- temporal_filtering · temporal_standardization
```

Rows **not covered by the extractor at all** (no targeted field on any mapping kind) must be flagged as such — an unaddressed row where the extractor never looked is a *tool* gap, not a *source* gap. This preserves the reason-partition distinction one level up.

---

## 6. Out of scope

- Any `_assemble` change; any schema change; step-presence provenance (`performed: ProvenancedField[bool]`) — the right end-state *if* you later want to extract whether a step ran, justified by wanting that claim, not by wanting a coverage number.
- Extractor targeting expansion (separate change; would make `evidence` meaningful for more rows).

---

## 7. Test plan

1. Registry completeness: 16 rows; 14 mandatory; `intensity_normalization` and `software_citation` are `N`.
2. `spatial_normalization` and `surface_projection` both map to `intersubject_registration` (one row, not two).
3. Predicate: a row with one `EXTRACTED` field → ADDRESSED; all-`MISSING` → UNADDRESSED; one `DEFERRED_TO_CITATION` → ADDRESSED; `INFERRED_DEFAULT` only → **UNADDRESSED**.
4. Software row: `base_pipeline.version` EXTRACTED → addressed; `date_inferred_version` → **violation** rendering.
5. Chen fixture: assert the exact addressed/unaddressed row sets (chen extracts `target_surface`, `surface_registration` → `intersubject_registration` ADDRESSED; `intensity_convention`, `intensity_value` → `intensity_normalization` ADDRESSED *but non-mandatory*).
6. Divergence steps never counted in the denominator.
7. Determinism; no `_assemble` behavior change (assert step list unchanged).

---

*Verification boundary: D.3 transcribed from the report supplied by the PI. Row-scope exclusions (diffusion, perfusion, rs-feature, QC) are a design judgment, recorded in §3. The conditional/unconditional classification of bare-`Report:` rows is the single interpretive call, locked conservatively in §4.*
