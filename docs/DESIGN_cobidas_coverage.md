# DESIGN — COBIDAS coverage section (emitter-side)

*Grounds the `not covered by extractor` figure in the actual standard. No schema change, no `_assemble` change. Source: COBIDAS Report v1.0 (2016/5/19), Table D.3 "Preprocessing Reporting", pp. 53–58 — read verbatim.*

## Changelog

- **Base** (committed `9bba492`, authored earlier) — §0–§7 as originally written.
- **Amendment 1 (2026-08-07) — four-state compliance rendering** (see [§A](#a-amendment-1-2026-08-07--four-state-compliance-rendering)). Reason: the `motion_correction` arc forces the bare-`Report:` conditional/unconditional decision that §4 left open; the amendment DISSOLVES it by grounding performance in the paper's own text rather than the row's syntax. It **supersedes §4** (conservative rule) and **§5** (rendering), and **re-keys §2's** binary ADDRESSED/UNADDRESSED predicate to **four states**. Superseded sections are retained below, marked, not deleted. Preserved unchanged: §2's extraction-arm-only firewall and Software special case, §3's 16-row registry and the `cobidas_row`-not-1:1 warning, §5's tool-gap-vs-source-gap partition, and §0's absence-vs-hallucination-inside-the-standard observation.

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

> ⚠ **The binary predicate below is SUPERSEDED by Amendment 1 ([§A](#a-amendment-1-2026-08-07--four-state-compliance-rendering)) — re-keyed to four states.** The extraction-arm-only firewall and the Software special case in this section are RETAINED unchanged; only the ADDRESSED/UNADDRESSED binary is replaced. Original text retained:

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

> ⚠ **SUPERSEDED by Amendment 1 ([§A](#a-amendment-1-2026-08-07--four-state-compliance-rendering)).** The refined rule grounds non-compliance in source-established performance, not the row's syntax — a firewall statement, not an interpretation. Original text retained:

> Claim non-compliance **only** where the standard's language is unconditional.

So only `software` can be rendered as a violation. Every other unaddressed mandatory row renders as *"not reported whether performed"* — an honest gap. Bare-`Report:` rows (motion correction, coregistration, intersubject registration, structured-noise removal, volume censoring, intensity correction, segmentation) are treated as **conditional by default**: their language lacks an explicit universal obligation, and a paper cannot report a method for an operation it did not perform.

*(This is the one interpretive judgment in the design. It errs toward under-claiming. If the PI reads the bare-`Report:` rows as unconditional, the violation set widens — a decision to make explicitly, not by default.)*

---

## 5. Rendering

> ⚠ **SUPERSEDED by Amendment 1 ([§A](#a-amendment-1-2026-08-07--four-state-compliance-rendering)) — four-state rendering.** The *not covered by the extractor* partition (the paragraph after the code block) is RETAINED unchanged and remains load-bearing. Original rendering retained:

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

**Amendment 1 additions (four-state predicate — see §A):**

8. Performance from extraction-arm state ONLY: the row's name/method field with a resolved member, OR a verbatim term with `resolved=None` (described-but-unnamed), OR `DEFERRED_TO_CITATION` → **performed**; nothing → **indeterminate**. `INFERRED_DEFAULT` never establishes performance.
9. Four-state assignment per row: performed + every mandated sub-item addressed → `performed_fully_reported`; performed + ≥1 mandated sub-item unaddressed → `performed_underreported` (the assertible non-compliance); performance not established → `performance_indeterminate`; explicit "did not perform" → `stated_not_performed`.
10. `stated_not_performed` renders as compliant (nothing owed), NOT as a gap; assert it is labelable-but-not-extractable today (no step-level stated-negative representation exists yet, and the rendering says so).
11. The *Intersubject registration* row re-renders under the four states (power assessed on whether its text establishes registration occurred) — asserted as a **consequence of Amendment 1, dated 2026-08-07**, not a new finding about power.

---

*Verification boundary: D.3 transcribed from the report supplied by the PI. Row-scope exclusions (diffusion, perfusion, rs-feature, QC) are a design judgment, recorded in §3. The conditional/unconditional classification of bare-`Report:` rows is the single interpretive call, locked conservatively in §4.*

---

## A. Amendment 1 (2026-08-07) — four-state compliance rendering

*Merged from `AMENDMENT_cobidas_coverage_three_state.md`. Supersedes §4 (conservative rule) and §5 (rendering); re-keys §2's binary predicate to four states. Scope: rendering + compliance predicate ONLY — no schema change, no `_assemble` change, no change to the extraction firewall. The naming: three of the four states assess a step that WAS performed (`performed_fully_reported` / `performed_underreported` / `performance_indeterminate`, named in conversation before the fourth was added); `stated_not_performed` is a statement ABOUT performance, not an assessment of it — as a rendering partition it is four buckets. (§1's `extractor.py:645–725` line reference is stale: the current `_assemble` is ~803; preserved verbatim on the base commit `9bba492`, to be corrected by a later edit.)*

### Why this amendment exists

The committed design contains an explicit open decision (§4): bare-`Report:` D.3 rows are treated as conditional by default, and the doc records that this *"is the one interpretive judgment in the design. It errs toward under-claiming. If the PI reads the bare-`Report:` rows as unconditional, the violation set widens — a decision to make explicitly, not by default."*

The `motion_correction` arc forces the decision, because *Motion correction* is a bare-`Report:` row. This amendment resolves it — but not by choosing conditional or unconditional. **It dissolves the question.**

### The resolution: ground performance in the source, not in the row's syntax

*"If performed, report"* is satisfied or violated depending on whether the paper performed the step. Once performance is established **from the paper's own text**, the row's syntax stops mattering — the conditional and unconditional readings agree on every paper whose text establishes performance, and neither can adjudicate a paper that is silent.

Scope check on the corpus: for `motion_correction`, 16 of 19 papers state that motion correction occurred. Both readings treat those identically — performance established, the full seven bullets owed, unreported bullets are gaps. The readings diverge only on papers silent about the step, which is roughly one paper (braun and viduarre defer, a different state). The compliance finding does not depend on the interpretation.

#### The refined conservative rule (supersedes §4)

> **Claim non-compliance only where the paper's own text establishes that the step was performed.**

This replaces *"claim non-compliance only where the standard's language is unconditional."* It is strictly better as a principle because it is a **firewall statement rather than an interpretation** — it says non-compliance requires source evidence, which is the same discipline the extraction/inference firewall enforces everywhere else in AESPA.

Consequences:

- The bare-`Report:` versus *"If performed, report:"* distinction becomes moot. The seven-row bare-`Report:` list in §4 no longer needs to be verified, because nothing depends on it. *(Worth noting: a spot check suggested that list may not be uniform — segmentation and intensity correction read descriptively rather than imperatively. A global rule would have asserted a uniformity the source may not have.)*
- Non-compliance is now assertible where it previously was not: a paper that *states* it performed motion correction and reports no reference scan is **underreporting**, not merely "not reported whether performed." This is **stronger** than the status quo, not weaker.
- It is not assertible from a prior. "Every fMRI study realigns" is true and inadmissible; performance comes from the text.

### The four states (supersedes the binary ADDRESSED/UNADDRESSED predicate in §2)

Per D.3 row:

| state | condition | compliance meaning |
|---|---|---|
| **`performed_fully_reported`** | performance established from source AND every mandated sub-item addressed | compliant |
| **`performed_underreported`** | performance established from source AND ≥1 mandated sub-item unaddressed | **non-compliance, assertible** |
| **`performance_indeterminate`** | source does not establish performance | the standard cannot adjudicate, and neither can AESPA |
| **`stated_not_performed`** | the paper explicitly states the step was not performed | compliant — nothing is owed |

`stated_not_performed` is the reproducibility gold standard and should be rendered as such, not as a gap. Corpus exemplar (a different row): ciric — *"We did not apply slice timing correction during preprocessing, as recent data suggest that the interpolation that occurs may artificially reduce motion estimates."* A reconstructor is fully served by that sentence. AESPA currently has no representation for a stated negative at step level; until it does, this state is labelable but not extractable, and that limitation should be stated wherever the rendering appears.

#### The finding this preserves

The committed design's most valuable observation must survive the amendment and be carried into the rendering: the standard *itself* cannot distinguish "didn't do it" from "did it, didn't say" for conditional rows — *"the absence-vs-hallucination problem appearing inside the reporting standard itself… it should be stated as a finding, not engineered around."*

`performance_indeterminate` **is** that finding, rendered per row rather than resolved by fiat. Choosing the unconditional reading globally would have spent this observation to buy a larger violation count.

### Establishing performance from extraction state

Performance uses **extraction-arm state only** — no `INFERRED_DEFAULT`, no base-pipeline implication. Firewall unchanged from §2.

The operative signal is the row's primary "name of software/method" field:

- a **verbatim term with no resolved member** (e.g. `verbatim="motion correction"`, `resolved=None`) — the operation is described, the tool is not named → **performed**
- a resolved member → **performed**
- `DEFERRED_TO_CITATION` → **performed** (attributed, not absent)
- nothing at all → **indeterminate**

**Note this is enabled by the v0.5.0 `SpecifiedTerm` retype.** Before the retype, a described-but-unnamed operation was discarded to the diagnostic and recorded as `MissingFromPaper` — indistinguishable from a paper that said nothing. The retype makes "described but unnamed" a representable state, and that state is exactly what establishes performance. The retype was justified on provenance-correctness grounds; this is a second, independent payoff.

**Open implementation question:** a paper could establish performance through a sub-item while saying nothing about the method (e.g. stating a reference scan but never that realignment occurred). Whether performance should be established by *any* non-absent field on the step rather than by the method field alone is unresolved. Recommend: any non-absent extraction-arm field establishes performance; the method field is the usual carrier but not the only admissible one. Flagged rather than assumed.

### Rendering (supersedes §5)

```markdown
## COBIDAS D.3 coverage (preprocessing)

Rows where the source establishes the step was performed: 6
  · fully reported 1   · underreported 5
Rows where performance is indeterminate: 8
Rows explicitly reported as not performed: 1
Non-mandatory: 2   ·   Beyond COBIDAS (AESPA extensions): 2

### Performed and underreported (mandated items missing)
- **Motion correction** — performed (source: "realignment of all volumes to a selected reference
  volume using MCFLIRT"). Reported: software/method. NOT reported: reference scan (a "selected
  reference volume" is stated without identifying it), similarity metric, interpolation / combined
  transforms, non-rigid use, slice-to-volume.

### Performance indeterminate (the standard cannot adjudicate)
- Distortion correction · Despiking · Volume censoring · …
  (The paper is silent. COBIDAS requires reporting only for steps performed, so silence cannot be
  distinguished from non-performance from text alone — a limitation of the standard, not of this paper
  or of AESPA.)

### Explicitly reported as not performed (compliant; best practice)
- **Slice time correction** — "We did not apply slice timing correction during preprocessing, as
  recent data suggest that the interpolation that occurs may artificially reduce motion estimates."

### Not covered by the extractor
- Rows where AESPA targets no field: an unaddressed row where the extractor never looked is a TOOL
  gap, not a SOURCE gap. (reason-partition preserved from §5)
```

The *not covered by the extractor* partition from the committed §5 is retained unchanged and remains load-bearing: it must never be possible to read a tool gap as a reporting gap.

### Scope of this amendment

Changes the **rendering and the compliance predicate** only. No schema change, no `_assemble` change, no change to the extraction firewall. The `target_space` (*Intersubject registration*) row is re-rendered under the new predicate — power, previously "not reported whether performed," is now assessed on whether its text establishes that intersubject registration occurred. That re-rendering must be reported as a consequence of this amendment, dated 2026-08-07, and not presented as a new finding about power.
