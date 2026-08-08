# DESIGN — Tool-Agnostic Replication Protocol Emitter (`render.to_protocol`)

*MVP target for the product/end-to-end track. Extends the existing render layer; `fmri_repro` stays contract-frozen. All claims below are grounded in the live tree (`extractor_mvp/src/extractor_mvp/render.py`, `src/fmri_repro/spec/{provenance,preprocessing}.py`) — file+line cited inline.*

---

## 0. Orientation — what problem this solves

`render.py` already has three formatters (`to_json`, `to_text`, `to_bullets`, render.py:9–11). All three are **extraction audits**: per-field "where did this value come from." They answer *did we extract correctly?*

The protocol emitter answers a different question — *how would I reproduce this preprocessing, and what can't the paper tell me?* Same data (`flatten()` output), different audience: a researcher re-running the pipeline, not an auditor of the extractor.

The design constraint that makes this honest rather than aspirational: on the corpus, mean **1.4 extracted fields/paper**, **0 fMRIPrep**, **0 inferred defaults** (verified last session). A replication artifact from these specs is ~90% holes. So the emitter's core job is to make the holes **actionable and honest**, not to pretend at a runnable config. This operationalizes what COBIDAS asks for — flagging unreported parameters against a controlled vocabulary rather than silently dropping them (Nichols et al. 2017).

---

## 1. What it is / is not

| Is | Is not |
|---|---|
| A fourth formatter in `render.py` over `flatten()` | A new module / subsystem |
| Structured **Markdown** procedure, tool-agnostic | Pseudocode (deferred), or an fMRIPrep/Slurm/container config |
| Holes rendered as explicit "you must specify" callouts | Silent omission or fabricated defaults |
| Inferred values marked distinctly + basis note visible | Inferred values shown as if extracted |
| Deterministic, no-LLM, unit-testable | Anything requiring a model call |

---

## 2. Locked decisions (rationale ≤3 sentences each)

**D1 — New formatter `to_protocol()` inside `render.py`, reusing `flatten()`. Not a new module.**
render.py's declared architecture is "one flattener, thin formatters" (render.py:3–8); a separate module would duplicate `flatten` and break the single-source-of-truth. Simple beats complex.

**D2 — Output = structured Markdown procedure. Pseudocode variant deferred.**
Markdown renders SPM/AFNI/CCS/XCP/C-PAC papers uniformly (0/20 corpus papers use fMRIPrep, so no tool-specific config syntax applies), and pseudocode implies an executability the ~90%-hole specs cannot honestly support. Prose carries "REQUIRED — unspecified" naturally; `# TODO` in fake code does not.

**D3 — Sequence = pipeline order (`steps` list order), `base_pipeline` first. COBIDAS row is a per-step tag, not the grouping axis.**
`flatten()` already guarantees list position = pipeline order (render.py:8, 226); a *protocol* must be procedural (do steps in order), and `cobidas_row` is reporting-taxonomy metadata (preprocessing.py:556), so it rides along as a tag and preserves the COBIDAS crosswalk without reordering the procedure.

**D4 — `FieldRow` gains one additive field: `basis: Basis | None = None`. Consumer-side only; `fmri_repro` untouched.**
Rendering the date-inference note needs `DateInferredVersionBasis.{tool, inferred_version, paper_date, note}` (provenance.py:93–99), but `_row_from_field` currently keeps only `basis_type` + `confidence` (render.py:172–174). Carrying the basis object is the minimal change and stays on the frozen contract's consumer side (render.py:13).

**D5 — Holes are actionable callouts, not flat "not reported".**
The artifact's purpose is reproduction, so every `MISSING_FROM_PAPER` / `LEFT_MISSING` field must read as a decision the replicator must resolve. This is COBIDAS's "flag the unreported" made machine-actionable (Nichols et al. 2017).

**D6 — A completeness header that separates absence from inference.**
The dissertation's headline claim is hallucination-vs-absence detection; the protocol leads with a four-way count — *specified in source · inferred · deferred to citation · require your input* — so the artifact itself surfaces the distinction rather than burying it.

**D7 — Inferred values carry a visible "not from source" marker + basis specifics + confidence against its ceiling.**
The no-fabrication invariant requires an inferred value to be unmistakably distinguishable from an extracted one; the emitter renders the basis detail (for `date_inferred_version`: `paper_date`, `tool`, `inferred_version`, plus `basis.note` verbatim) and prints `confidence X / ceiling Y` so precision is never overstated. The emitter renders `basis.note`; it does **not** author it (the temporal-bound phrasing is the Configurator's responsibility, keeping the emitter a pure renderer).

**D8 — `alternative_inferences` shown only when non-empty, one line each; primary value is the protocol's stated value.**
The spec requires `alternative_inferences` on every `InferredDefault` (provenance.py:148; empty OK); listing them when present is honest about competing defaults, but MVP readability favors stating the primary and appending alternatives only if the list is non-empty.

---

## 3. `FieldRow` change (the only spec-adjacent edit)

```python
# render.py — import + one field
from fmri_repro.spec.provenance import Basis, NotApplicable, ProvenancedField  # add Basis

@dataclass
class FieldRow:
    ...
    basis_type: str | None = None
    confidence: float | None = None
    basis: Basis | None = None            # NEW — carries the full basis for note rendering
    ...

# in _row_from_field, the existing INFERRED_DEFAULT branch:
    if inf.status == "INFERRED_DEFAULT":
        row.basis_type = inf.basis.basis_type
        row.confidence = inf.confidence
        row.basis = inf.basis             # NEW
```

Existing formatters ignore `.basis` — no behavior change to `to_text`/`to_bullets`/`to_json`.

---

## 4. State → protocol rendering

`flatten()` yields five display states + the `BASE_NOT_APPLICABLE` sentinel (render.py:49–54). Rendering per state:

| Display state | Line rendered |
|---|---|
| `EXTRACTED` | `{param} = {value}   [from paper]` (+ optional ≤80-char quote) |
| `INFERRED_DEFAULT` | `{param} = {value}   [INFERRED — not stated in source]` then an indented basis note (see §4a) |
| `DEFERRED_TO_CITATION` | `{param}: deferred to {refs} — resolve by consulting the cited source` |
| `MISSING_FROM_PAPER` | `{param}: REQUIRED — not reported in source; you must specify` |
| `LEFT_MISSING` | `{param}: REQUIRED — not reported and no default available; you must specify` (+ `(reason: {reason})` if `LeftMissing.reason` set, provenance.py:168) |
| `BASE_NOT_APPLICABLE` | `Base pipeline: built from scratch (no named base pipeline)` |

The `MISSING` vs `LEFT_MISSING` split is preserved deliberately: `MISSING` = paper didn't state it; `LEFT_MISSING` = paper didn't state it **and** the Configurator could not infer a default (no KB coverage, or the honesty ceiling refused). Same action ("you must specify"), different epistemic reason — that difference is the contribution.

### 4a. Basis note rendering (per `basis_type`, all fields verified in provenance.py)

- `date_inferred_version` → `inferred from publication date {paper_date}: {tool} {inferred_version}` + ` — {note}` if `note` set. *(fields: provenance.py:93–99)*
- `version_default` → `{tool} {version} (version stated/confirmed)` + note. *(86–91)*
- `prior_publication` → `from cited work {citation}` + note. *(101–105)*
- `lab_prior` → `lab default ({lab_id})` + note. *(107–111)*
- `field_convention` → `field convention ({source})` + note. *(113–117)*
- `derived` → `derived from {source_field_ids}` + note. *(119–123)*

Every inferred line ends with `(confidence {confidence} / ceiling {BASIS_CEILINGS[basis_type]})` (ceilings: provenance.py:22–29). Dispatch on `basis_type` is exhaustive over the `Basis` union (provenance.py:125–133).

---

## 5. Faithful worked example — `chen_2015` (batch_v6_full)

Real extracted fields (5): `base_pipeline = CCS`; `surface_projection.target_surface = fsaverage5`; `surface_projection.surface_registration = freesurfer_recon`; `intensity_normalization.convention = fsl_grand_mean_10000`; `intensity_normalization.value = 10000.0`. Everything else `MISSING_FROM_PAPER`. COBIDAS tags are the real per-class values.

```markdown
# Replication Protocol — chen_2015

Base pipeline: Connectome Computation System (CCS)   [from paper]
  version: REQUIRED — not reported in source; you must specify

Completeness: 5 specified in source · 0 inferred · 0 deferred · 11 require your input

## Preprocessing steps (pipeline order)

### 1. spatial_normalization   (COBIDAS: intersubject_registration_volume)
- target_space:   REQUIRED — not reported in source; you must specify
- resolution_mm:  REQUIRED — not reported in source; you must specify
- method:         REQUIRED — not reported in source; you must specify
- warp:           REQUIRED — not reported in source; you must specify
- transform_type: REQUIRED — not reported in source; you must specify
- interpolation:  REQUIRED — not reported in source; you must specify
- regularization: REQUIRED — not reported in source; you must specify

### 2. surface_projection   (COBIDAS: surface_projection)
- target_surface       = fsaverage5         [from paper]
- surface_registration = freesurfer_recon   [from paper]
- vol2surf_sampling:  REQUIRED — not reported in source; you must specify
- cifti:              REQUIRED — not reported in source; you must specify

### 3. intensity_normalization   (COBIDAS: intensity_normalization)
- convention = fsl_grand_mean_10000   [from paper]
- value      = 10000.0                [from paper]
- scope:     REQUIRED — not reported in source; you must specify

### 4. temporal_standardization   (COBIDAS: DIVERGENCE)
- method:    REQUIRED — not reported in source; you must specify
```

### 5a. Synthetic illustration of the INFERRED / date-inference line

**No corpus paper produces an inferred row** (0 inferred defaults corpus-wide — the CCS `version` above is exactly where date-inference *would* fire in the final product, but CCS is git-commit-versioned so this specific case is weak). The following is **hand-constructed to show the format only**, not real output:

```markdown
- version = 25.2.5   [INFERRED — not stated in source]
    inferred from publication date 2015-03-01: fMRIPrep 25.2.5
    — latest release at/before publication; the study may have used an earlier version
    (confidence 0.75 / ceiling 0.75)
```

---

## 6. Test plan (extend `tests/test_render.py`, deterministic, no LLM)

1. **Pipeline order** — `to_protocol` renders `base_pipeline` first, then steps in `steps` list order (assert header positions).
2. **Each state → correct line** — build a `Preprocessing` with one field in each of EXTRACTED / MISSING / DEFERRED / LEFT_MISSING / INFERRED; assert the exact rendered substring per §4.
3. **Basis note dispatch** — one field per `basis_type` (6 cases); assert the specifics render (esp. `date_inferred_version` → `paper_date`, `tool`, `inferred_version`) and the `confidence / ceiling` suffix matches `BASIS_CEILINGS`.
4. **Hole callout wording** — `MISSING` vs `LEFT_MISSING` produce distinct lines; `LeftMissing.reason`, when set, appears.
5. **Completeness header math** — counts equal the flatten() state tally (E · I · D · M+L).
6. **base_pipeline variants** — named (EXTRACTED) with version sub-row; from-scratch (`NotApplicable` → `BASE_NOT_APPLICABLE` line, no version recursion); named-but-version-MISSING (the Chen case).
7. **Determinism** — two calls on the same spec are byte-identical.
8. **Faithful fixture** — load `results/batch_v6_full/papers/chen_2015.json` (or the frozen test fixture), assert the §5 structure (5 `[from paper]` lines, 11 `REQUIRED` lines, 0 inferred).

---

## 7. Out of scope for this MVP (explicit boundary)

- Pseudocode / code-shaped output (a later `to_pseudocode` variant).
- fMRIPrep config, container spec, Slurm — no corpus paper supports honest generation.
- CrossRef/DOI date sourcing (the date-inference feature's defensibility upgrade; network-gated, tied to the stubbed PaperFetcher tiers).
- Enabling date-inference on the corpus (dormant by KB-coverage reality; separate work).

---

## 8. Claude Code prompt

```
Extend the render layer in extractor_mvp with a fourth, deterministic (no-LLM) formatter
`to_protocol` that emits a tool-agnostic Markdown replication protocol. Do NOT touch the
`fmri_repro` package (it is contract-frozen). Reuse the existing `flatten()` — do not add a
new module.

FILE: extractor_mvp/src/extractor_mvp/render.py

1. Import change:
   from fmri_repro.spec.provenance import Basis, NotApplicable, ProvenancedField

2. Add one field to the FieldRow dataclass (after `confidence`):
       basis: Basis | None = None
   and in `_row_from_field`, inside the existing `if inf.status == "INFERRED_DEFAULT":`
   block, add:  row.basis = inf.basis
   Do not change any other formatter.

3. Add `to_protocol(preprocessing: Preprocessing) -> str`, reusing `flatten(preprocessing)`.
   Output structure (Markdown):
     - Title line: `# Replication Protocol — {source}` if a source is available, else
       `# Replication Protocol`. (There is no source field on Preprocessing; accept an
       optional `source: str | None = None` arg and title accordingly.)
     - `Base pipeline:` line from the base_pipeline row(s):
         * EXTRACTED/INFERRED named pipeline -> `Base pipeline: {name}   [from paper]`
           (or the inferred marker), then an indented `version:` sub-line rendered by the
           same per-state logic as any field.
         * BASE_NOT_APPLICABLE -> `Base pipeline: built from scratch (no named base pipeline)`.
     - `Completeness:` header — counts over flatten() states:
         `{E} specified in source · {I} inferred · {D} deferred · {M+L} require your input`
         where E=EXTRACTED, I=INFERRED_DEFAULT, D=DEFERRED_TO_CITATION,
         M+L = MISSING_FROM_PAPER + LEFT_MISSING.
     - `## Preprocessing steps (pipeline order)` then one `### {n}. {kind}   (COBIDAS: {cobidas_row})`
       section per step in list order, cobidas_row via getattr(type(step),"cobidas_row",None).
     - One `- ` bullet per field, rendered per the state table:
         EXTRACTED            -> `- {param} = {value}   [from paper]`  (+ ` «{≤80-char quote}»` if span_text)
         INFERRED_DEFAULT     -> `- {param} = {value}   [INFERRED — not stated in source]`
                                 then an indented basis-note line (see step 4) 
         DEFERRED_TO_CITATION -> `- {param}: deferred to {refs} — resolve by consulting the cited source`
         MISSING_FROM_PAPER   -> `- {param}: REQUIRED — not reported in source; you must specify`
         LEFT_MISSING         -> `- {param}: REQUIRED — not reported and no default available; you must specify`
                                 (+ ` (reason: {reason})` when the LeftMissing.reason is set)
       `{param}` is the field name (path after the first dot); `{value}` via the existing
       `_fmt_value`. Reuse `_truncate_quote` for the quote.

4. Basis-note rendering helper `_fmt_basis_note(row: FieldRow) -> str`, dispatching on
   row.basis.basis_type over the full Basis union (exhaustive):
       date_inferred_version -> f"inferred from publication date {b.paper_date}: {b.tool} {b.inferred_version}"
       version_default       -> f"{b.tool} {b.version} (version stated/confirmed)"
       prior_publication     -> f"from cited work {b.citation}"
       lab_prior             -> f"lab default ({b.lab_id})"
       field_convention      -> f"field convention ({b.source})"
       derived               -> f"derived from {', '.join(b.source_field_ids)}"
   Append ` — {b.note}` when b.note is set. End every note with
   ` (confidence {row.confidence} / ceiling {BASIS_CEILINGS[row.basis_type]})`
   (import BASIS_CEILINGS from fmri_repro.spec.provenance). Indent the note line under its bullet.

5. Keep it pure/deterministic: no I/O, no model calls, stable ordering. mypy-clean under the
   repo config, ruff-clean.

TESTS: extend tests/test_render.py with the 8 cases in the design doc §6 — pipeline order;
each state's exact line; per-basis_type note dispatch incl. date_inferred_version specifics and
the confidence/ceiling suffix; MISSING vs LEFT_MISSING distinct wording + reason surfacing;
completeness-header math equals the flatten() tally; the three base_pipeline variants
(named+version sub-row, from-scratch NotApplicable, named-but-version-MISSING); byte-for-byte
determinism on repeat calls; and a faithful-fixture assertion (5 `[from paper]`, 11 `REQUIRED`,
0 inferred) using the chen_2015 spec. Build synthetic InferredDefault fields in-test for the
basis cases (the corpus has none). Run `uv run pytest tests/test_render.py`, `uv run ruff check`,
and `uv run mypy src` and report results. Do not commit during 09:00–17:00 ET (the hook enforces
this); leave the working tree staged for me to commit.
```

---

*Verification boundaries: corpus statistics (1.4 fields/paper, 0 fMRIPrep, 0 inferred) are from last session's field-level walk of `batch_v6_full`. The §5a inferred row is explicitly synthetic. `basis` field names all confirmed at the cited provenance.py lines. The optional `source` arg is a design choice (Preprocessing has no source field) — flag if you want the title sourced differently.*
