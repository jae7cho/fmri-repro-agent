# DESIGN — `motion_correction` extraction, assembly, and the motion row

*Builds the extraction side of COBIDAS D.3's motion-correction row. **Nothing here is implemented.**
Two rulings are recorded (§2, and the five forks in §4); one question is left open and must be settled
in its own commit before motion goes live (§4.3). Drafted and ruled 2026-10-19; every locator verified
at HEAD `290db8a`, every number derived from files with its derivation shown. Facts gathered by two
read-only investigator passes — ten agents then four; all fourteen returned, none silent.*

---

## 0. Premise corrections, before anything else

Six things that scoping conversation and docs of record get wrong at HEAD. The first changes what
this document is about.

### 0.1 `MotionCorrection` already exists in the spec. The missing thing is extraction, not schema.

`src/fmri_repro/spec/preprocessing.py:692-717`. Ten data fields besides `kind`, and all four closed
Literals were already retyped to `SpecifiedTerm[X]` at 0.5.1:

```
697     method: ProvenancedField[SpecifiedTerm[MotionCorrectionMethod]]
698     reference_scan: ProvenancedField[SpecifiedTerm[MotionReferenceScan]]
699     similarity_metric: ProvenancedField[SpecifiedTerm[MotionSimilarityMetric]]
700     interpolation: ProvenancedField[SpecifiedTerm[MotionInterpolation]]
703     transforms_combined: ProvenancedField[bool]
704     nonrigid: ProvenancedField[bool]
705     transform_type: ProvenancedField[str]
706     fieldmap_unwarping: ProvenancedField[bool]
707     unwarping_method: ProvenancedField[str]
708     slice_to_volume: ProvenancedField[bool]
```

It is a member of the `PreprocStep` discriminated union, its `cobidas_row` ClassVar is
`"motion_correction"` (`:710`), its registry `MOTION_CORRECTION_FIELD_META` begins at `:149`, and the
import-time bijection guard is called at `:1211`. **So this is not "adding a new step kind."** It is
scenario T below — a kind already in the spec that the extractor does not emit — and that distinction
is worth roughly half the work (§3c).

Two consequences for the protocol document, which is a doc of record:

- `docs/ground-truth-protocol-motion_correction.md:66` locates the class at `preprocessing.py:687-706`.
  At HEAD it is `692-717`, with fields at `693-708`. **Stale locator.**
- `:75` marks `transforms_combined` **"(NEW)"** and `:78-79` says it "does not exist in the spec today
  — it is added as part of this arc". **False at HEAD:** it is at `preprocessing.py:703` and registered
  at `:170`. The spec comment at `701-702` already ties it to "COBIDAS D.3 bullet 6".

### 0.2 `migrations.py` asserts something false about committed documents

`src/fmri_repro/spec/migrations.py:184-189` says no committed document contains a `motion_correction`
step, calling it "a never-emitted step" whose fields "appear in zero documents".

- **The narrow claim is TRUE at HEAD:** `_assemble` never instantiates `MotionCorrection`.
- **The broad claim is FALSE at HEAD, and was false when written.** The tracked file
  `examples/spec.json` contains **2** `motion_correction` steps, constructed by
  `scripts/make_example_spec.py:705` and `:843`.

This matters beyond tidiness: `tests/.../test_examples_reproducible` byte-compares `examples/spec.json`,
so motion steps are already inside a byte-identity gate.

### 0.3 The "six fields" problem is a CODE inconsistency, not three wrong comments

*An earlier draft of this section said three comments "name the wrong set". That was wrong, and the
correction matters because it changes what may be fixed and how.*

Measured: `_FIELD_SPECS` has **7** targeted fields; `_LAYER2_FIELD_IDS` has **6**
(`convention, resolution_mm, surface_registration, target_space, target_surface, value`);
`field_diff._DIFF_FIELDS` has **6**. The missing one in both gates is
`temporal_standardization.method`. Every occurrence of the wording:

| site | says | annotates | verdict |
|---|---|---|---|
| `extractor.py:168` | "the six targeted Layer-2 fields below" | the **7** stanzas that follow it | **WRONG** — and it is *inside* `EXTRACTION_PROMPT` (`:111-334`), sent to the model at `:1075` and reused at `:966`. Editing it is a **prompt change**, not a comment fix |
| `extractor.py:1131` | "The six targeted Layer-2 step fields" | `_LAYER2_FIELD_IDS`, 6 members, immediately below | **correct** |
| `extractor.py:1146` | "any of the six targeted Layer-2 fields" | the same constant | **correct** |
| `field_diff.py:22` | "the 6 targeted preprocessing fields" | `_DIFF_FIELDS`, 6 entries | **correct** |
| `retry_audit.py:51` | "The 7 targeted response-model fields" | a list of **8** (it includes `base_pipeline_name`) | **WRONG**, and it is an ordinary comment |

So **one** of the three sites commonly cited is wrong, and it is the one that cannot be fixed as a
comment; two are accurate about the constants they annotate; and the genuinely fixable wrong one
(`retry_audit.py:51`) is usually not cited at all.

**The real defect is underneath the wording:** `temporal_standardization.method` is a targeted field
excluded from both the base-pipeline-fallback gate (`_LAYER2_FIELD_IDS`, feeding
`_any_step_fields_left_missing` at `:1145-1154` and the fallback at `:1205`) and the
multi-acquisition diff (`_DIFF_FIELDS`). Whether that exclusion is deliberate is not recorded anywhere
this pass could find. **An eighth field inherits the same silent exclusion**, which is the reason this
is in §0 rather than a footnote.

### 0.4 The "about six files and ten edits per kind" scoping number does not reproduce

Measured at HEAD, the count depends on which scenario is meant, and neither reading gives 6/10. See
§3c. The closest historical precedent, `7919e8b`, touched **3** files — and predates the
`test_assemble_v0_3_0.py` and `conftest.py` constraints that now bind.

### 0.5 Two binding documents carry a drifted locator

The prereg at `:86` and `DEVLOG.md:997` both cite `extractor.py:726` for the second
`"supplement" → "paper"` narrowing. At HEAD that narrowing is at **`:730`**; `:726` is now
`target_kind=ref_result.target_kind,` inside a `DeferralRecord`. `:602`, the first narrowing, is still
correct. The drift was introduced by `2018bd3`, after the amendment. **The behaviour both documents
describe is unchanged** — only the line moved.

### 0.6 The labels-sheet trap is real, and the record's bound is the right one

`ground_truth/motion_correction_labels_v1.xlsx`, sheet `Labels`, read with `zipfile` +
`xml.etree.ElementTree` because **openpyxl is not installed in `extractor_mvp/.venv`**
(`ModuleNotFoundError`). All cells are inline strings; there is no `sharedStrings.xml`.

| | |
|---|---|
| dimension | `A1:Q22` — 22 rows × 17 columns |
| `<row>` elements | 21: `r=1..20` and `r=22`. **There is no row-21 element at all** |
| real papers | **19**, rows 2–20 |
| row 22 | a single cell, the instructional footer, `ht="224"`, not merged |
| non-empty column A | **21** including the header, **20** excluding it |

So the recorded warning is correct in every particular, and the N=20 it warns about is the footer
being counted as a paper. **How a reader should bound it:** iterate the 19 known `paper_id`s, or stop
at row 20, and hard-fail if the count is not 19 — which is exactly what `DEVLOG.md:906-907` already
requires. Corroborated inside the instrument: both data validations stop at row 20
(`sqref="B2:B20"`, `sqref="E2:E20 G2:G20 ..."`), and `Start here!B13` says "One row per paper (19)."
Never key on non-empty column A, and never on the used range.

The 19 ids, in sheet order: agtzidis_2020, braun_2015, chen_2015, ciric_2017, cole_2013, derosa_2025,
gordon_2014, liu_2005, liu_2013, mueller_2021, oconnor_2017, poldrack_2015, power_2014, tang_2025,
vanderwal_2016, viduarre_2017, weber_2024, wheaton_2004, binder_1999. All unique; cabral absent, per
protocol `:37`.

**No document names this file authoritative.** It is the only motion label artifact — there is no
derived CSV (positive control: `base_pipeline_labels_v1.csv` and `target_space_labels_v1.csv` both
exist in the same directory) and no `ground_truth/README` section covers motion. Authority is an
inference from uniqueness, not a citation, and a design doc should not claim otherwise. The protocol
does bind one narrower thing (`:584`): "the per-row Notes flags in the workbook are authoritative, and
this list is derived from them, not the reverse".

Known defect, already recorded at `TRACK_A_SCOPE.md:339`: the row-22 footer still says "CALLs 1–8"
while the protocol is v1.5 with CALLs 1–10.

---

## 1. Scope, and what this is not

**In scope.** Build `motion_correction` extraction (LLM schema field(s), prompt stanza(s), span
resolution), assemble a `MotionCorrection` step in `_assemble`, and thereby turn on the
`motion_correction` COBIDAS row's coverage.

**It is NOT an accuracy figure, and four independent constraints say so.**

1. **The pre-registration forbids one outright.** `:9-10`: "**Question: is `described_only`
   expressible — not whether the extractor is accurate. No accuracy figure may be computed from or
   cited out of this run.**" Restated unchanged in Amendment 1 at `:158-159`.
2. **The labels are contaminated.** Union of **16 of 19** papers (§3h). The protocol's own conclusion
   at `:547-550` is that a motion figure is **diagnostic only, explicitly not evaluative** — and
   "evaluative" appears nowhere else in `docs/` at HEAD.
3. **It would not be comparable even if clean.** The `span_role` three-way match makes the motion
   figure stricter than either prior field's, so prereg `:36-38` requires stating that it "is not
   comparable to base_pipeline's 82.4% or target_space's 11/17". Amendment 1 extends this to the whole
   map (`:138-141`).
4. **Three cell classes are excluded from both numerator and denominator** — `unread` (row 5),
   `undecided` (row 3), and `multi_target_unscoreable` per CALL 9 — "each reported as a named line in
   the decomposition, never folded into an error rate" (`:134-136`).

**Also not in scope:** labelling (prereg `:3`: this governs "extraction and scoring, **not
labelling**: the protocol governs labelling"), the `_build_version_pf` arm of
`DELTA_base_pipeline_diagnostic.md` §10, and any figure or panel work.

---

## 2. The 2026-10-19 ruling, recorded

> **Committed numbers stand as history under their named vintages, and the poster reports them
> alongside the progress made since.** A prompt change that alters future extraction is therefore
> acceptable — provided every number keeps its vintage on its face.

*Source and date.* Ruled by the author in conversation and written down here on **2026-10-19**.
Deliberately **not backdated** to the conversation: the record's date is the date it became
checkable. This is the same discipline as the render ruling (`TRACK_A_SCOPE.md:198`), and for the same
reason — a ruling nobody can find is not a ruling, which is how that one came to be contradicted by
the DEVLOG for three weeks. Recorded in parallel as a dated note beside the render ruling in
`docs/TRACK_A_SCOPE.md`.

**Why it is load-bearing here.** Fork A (§4.1) is whether motion shares the single extraction prompt.
If it does, the next `target_space` numbers are a **new vintage**, because the shared prompt changed.
Without this ruling, that cost blocks the fork; with it, the cost is a labelling obligation rather
than a veto.

**And the risk is measured, not hypothetical.** The v1→v2 prompt change coerced MNI terms:
**5 of 7** at the shipped `EXTRACTED` level. Measured more precisely during this pass, it was **6 of
7 at the raw LLM value level** — oconnor_2017's v2 raw value *was* `MNI152NLin6Asym` but failed span
resolution (`quote_not_found`), so it is not among the 5 shipped coercions. A prompt edit moves
values that were already being reported.

**The standing obligation this ruling leans on** is already in force: every published rate names its
aggregation as well as its vintage (`20bbd2a`). The ruling does not weaken it — it depends on it.

---

## 3. What exists

### 3a. The seven D.3 bullets, and the field for each

The protocol enumerates the bullets at `:54-64`, introduced as "Seven bullets, quoted **in
substance**" — so they are a paraphrase of COBIDAS, not a quotation, which matters for §4.2.

| # | bullet (protocol `:57-64`) | spec field(s) at HEAD |
|---|---|---|
| 1 | Name of software/method | `method` (`:697`) |
| 2 | Use of non-rigid registration, and if so the type of transformation | `nonrigid` (`:704`), `transform_type` (`:705`) |
| 3 | Use of motion susceptibility correction (fieldmap-based unwarping), and the software/method | `fieldmap_unwarping` (`:706`), `unwarping_method` (`:707`) |
| 4 | Reference scan (e.g. 1st scan or middle scan) | `reference_scan` (`:698`) |
| 5 | Image similarity metric | `similarity_metric` (`:699`) |
| 6 | Interpolation type, **and whether image transformations are combined to allow a single interpolation** | `interpolation` (`:700`), `transforms_combined` (`:703`) |
| 7 | Use of slice-to-volume registration methods, or integration with slice time correction | `slice_to_volume` (`:708`) |

**Every bullet maps at bullet granularity; none is unrepresented.** The doc's own table (`:68-76`)
agrees field-for-field, and `:78` says "All seven bullets map."

**One sub-clause gap.** Bullet 7 is a disjunction — slice-to-volume registration **or** integration
with slice time correction — and only `slice_to_volume` exists. No field name contains `slice_time`,
`stc` or `integration`. Every other sub-clause of bullets 2, 3 and 6 has its own field. Whether one
bool covers both disjuncts is a design question, not resolved here.

**And the protocol words bullet 7 two ways.** §1 `:64` has "or integration with slice time
correction"; CALL 8 at `:329` quotes it as "or integrated with slice time correction". CALL 8's own
title is "bullet 7 is about the MOTION CORRECTION, not the occurrence of slice-time correction", so
the distinction is live rather than cosmetic.

### 3b. The extraction path: ONE shared prompt, ONE call, all fields

This is the single most consequential fact for §4.1, so it is stated with the code.

`EXTRACTION_PROMPT` (`extractor.py:111-334`) is **one hand-written string literal**. Each field's
instruction is a stanza of prose typed into it. **No code generates, selects, or loops over per-field
stanzas.** The only runtime substitution is `{text}` — an offline `string.Formatter` parse returns
`['text']` as the sole placeholder.

```
111 EXTRACTION_PROMPT = """\
112 You are extracting preprocessing parameters from an fMRI methods text. For EACH
113 field below, decide its status (see "Output status for each field") and fill in
114 the corresponding fields.
...
330 Text:
331 """
332 {text}
333 """
334 """
```

One call, one user message, one response model covering every field (`extractor.py:983-990`), at
`temperature=0.0, max_retries=2`. The per-acquisition path does not escape this: it *concatenates* a
fixed prefix onto the same literal (`PER_ACQUISITION_EXTRACTION_PROMPT = """..."""  + EXTRACTION_PROMPT`,
`:948-967`), so it inherits every stanza change.

**The stanzas already cross-reference each other**, which is evidence about coupling rather than an
aesthetic point. The `intensity_convention` stanza steers the model away from a sibling field
(`:242-244`: "NOT this field: per-voxel z-scoring ... → that is `temporal_standardization_method`"),
and `:327` names two fields that are not in `PreprocessingExtraction` at all
(`smoothing_fwhm`, `intensity_normalization`). Separately, `subject_validator.py:41` records that its
taxonomy is "Lifted VERBATIM from EXTRACTION_PROMPT's DECISION RULE" — a second module holding a copy
of prompt text.

### 3c. Every site a motion step must touch, measured

The spec union has **19** kinds (`preprocessing.py:1233-1254`); `_assemble` emits **7**
(`extractor.py:935-943`). So 12 spec kinds exist that the extractor does not emit, motion among them.

**Scenario T — a kind already in the spec, newly emitted and targeted. This is motion's case.**
9 REQUIRED sites in 4 files; without each, code or an existing test fails:

| # | site | edit |
|---|---|---|
| R1 | `extractor.py:32-48` | add the step class to the `fmri_repro.spec.preprocessing` import block |
| R2 | `extractor.py:77-108` | add *k* `FieldExtractionResult` attributes to `PreprocessingExtraction` |
| R3 | `extractor.py:111-334` | add *k* stanzas to the shared `EXTRACTION_PROMPT` |
| R4 | `extractor.py:385-429` | add *k* 5-tuples to `_FIELD_SPECS` |
| R5 | `extractor.py:864-944` | build the step in `_assemble`, untargeted fields via `_missing_pf`, insert into `steps=[...]` |
| R6 | `tests/conftest.py:116-124` | `_PF_FIELD_IDS` — else `_build_assembled()` raises `KeyError` |
| R7 | `tests/test_assemble_v0_3_0.py:26-34` | the exact 7-kind step-list assertion changes |
| R8 | `tests/test_assemble_v0_3_0.py:62` | `assert out.count("not examined by the extractor") == 19` changes by the new step's untargeted-field count |
| R9 | `tests/test_batch.py:41` | `n_missing_not_stated == 5` changes |

Plus roughly **8 conditional / non-enforced sites** where omission is silent: `SYNONYMS_BY_FIELD`
(`synonym_resolver.py:268-273`, keyed on *bare* field_id), the `value_context` guard
(`extractor.py:1000`), `_LAYER2_FIELD_IDS` (`:1131-1142`), `field_diff._DIFF_FIELDS` (`:22-30`), the
cobidas registry (**not needed for motion — already mapped at `cobidas.py:59`**), and three audit
scripts with hand-kept field lists (`hard_drop_audit.py:41-49`, `retry_audit.py:51-61`,
`variance_probe.py:43-49`), plus the sfn glossary.

**Scenario N — a kind not yet in the spec** adds at least 4 enforced spec-side sites (step class +
`FieldMeta` registry, the `_check_step_bijection` line, the `PreprocStep` union, and `_STEP_CLASSES`
in `test_vocab_contract.py`, which *is* enforced by `test_step_classes_match_preproc_step_union`),
plus versioning (`SCHEMA_VERSION`, two `Literal` sites, a migration hop) and a generated schema JSON —
precedent `aa827b2` added a 14,535-line schema file.

**Motion is scenario T.** The spec-side cost in scenario N does not apply, and neither does a version
bump. One caveat worth noting: `_PF_FIELD_IDS` **moved** from `test_assemble_v0_3_0.py` to
`tests/conftest.py:116-124` in `ac63ada` (2026-10-03); any scoping note written before that date
points at the wrong file.

### 3d. Coverage: how the motion row would turn on

`cobidas.py:59`, verbatim:

```
CobidasRow("motion_correction", "Motion correction", True, False, ("motion_correction",)),
```

Per the dataclass field order (`cobidas.py:41-45`): `row_id="motion_correction"`,
`d3_aspect="Motion correction"`, `mandatory=True`, `unconditional=False` (i.e. mandatory-if-performed),
`spec_kinds=("motion_correction",)` — **exactly one kind.**

```
def _row_covered_by_extractor(field_rows: list[Any]) -> bool:
    """True iff the extractor targets any of these fields (a field is untargeted iff its
    LeftMissing reason is ``not_targeted_by_mvp``; extracted/deferred fields are targeted)."""
    return any(r.left_missing_reason != _UNTARGETED_REASON for r in field_rows)
```

with `_UNTARGETED_REASON = "not_targeted_by_mvp"` (`:121`). `mapped` is built at `:259` as
`[r for k in cr.spec_kinds for r in by_kind.get(k, [])]`, grouping on `r.group` (`:244-246`).

**So the row turns on the moment any one motion field is targeted** — even if every paper comes back
`MISSING_FROM_PAPER`, because a targeted-but-missing field has a reason other than
`not_targeted_by_mvp`. And by `any([]) == False`, a row whose kinds contribute no `FieldRow`s at all
is **not** covered, which is why the motion row is uncovered for every paper today.

### 3e. The double-credit hazard: checked, and it does not touch motion

**Motion maps to exactly one row.** Walking all 16 rows of `COBIDAS_D3_ROWS`, exactly one row's
`spec_kinds` contains `"motion_correction"`, with length 1. No other row lists it; no row lists any
kind containing "motion". The three multi-kind rows contain no motion kind:
`intersubject_registration` (`spatial_normalization`, `surface_projection`),
`artifact_structured_noise_removal` (`ica_denoise`, `compcor`, `nuisance_regression`),
`volume_censoring` (`despike`, `scrub`). A synthetic run with only `motion_correction.method`
EXTRACTED credits only the motion row.

**Two adjacency facts that look like hazards and are not:**

- `MotionCorrection.fieldmap_unwarping` and `unwarping_method` (`:706-707`) are *distortion*-adjacent
  in substance, but because they are grouped under kind `motion_correction` they can only ever credit
  the **motion** row — never either distortion row. That is a potential **under**-credit, the opposite
  hazard, and it is bullet 3's doing: COBIDAS puts susceptibility correction inside the motion row.
- `NuisanceRegression.motion_expansion` (`extractor.py:908`) is grouped under
  `nuisance_regression` and credits `artifact_structured_noise_removal`, not the motion row.

**On the asserted distortion hazard itself, two corrections.** The claim was "`assess_coverage` never
reads `DistortionSource`, so a paper reporting only one kind of distortion correction is credited with
both."

1. True for the source **value** — there is no `DistortionSource` reference and no `.value` access in
   `cobidas.py`. But the `distortion_correction.source` **field** is not ignored: `render.flatten`
   emits it as a `FieldRow` grouped under `distortion_correction` (`render.py:283`), so its
   `extraction_status` and `left_missing_reason` do feed both distortion rows' addressed/covered
   computation. The double credit is real; the stated mechanism is not the operative one.
2. **It is latent, not live.** `_assemble` emits no `distortion_correction` step, so in actual
   extractor output both distortion rows are uncovered and unaddressed for every paper. The present
   tense in the claim is wrong.

### 3f. The identity gate, derived from the code

Replay **never calls `_assemble` or the extractor** (`rerender_reports.py:129-145`); it reads stored
per-paper JSON and re-renders. Scanning `extractor_mvp/results/**/*.json` with Python (recursive shell
grep would skip this tree — `results/` is gitignored): across 57 stored v050 per-paper JSONs, **zero**
contain a `motion_correction` step. `flatten` and `assess_coverage` read only stored steps, so the
motion row stays `addressed=False, covered=False` under both refs.

**Derived expectation:** if the change touches only `_assemble`, `PreprocessingExtraction`,
`_FIELD_SPECS` and the prompt, the gate should show **19 identical, 0 changed**.

**It becomes conditional the moment the change touches code replay runs** — `cobidas.py`'s motion row,
any `render.py` wording, stored-step field order, or `MethodsSlice`. **Every stored report already
contains the motion row's conditional line**, so a render or cobidas wording change on that row hits
all 19 at once.

Three gate-mechanics caveats, from the script itself, that the acceptance criterion must survive:

- `19 identical` is **also** what a failed `PYTHONPATH` override produces (docstring, `:31-36`).
- `_differ` returns **exit code 0 whether or not reports changed** (`:252`), so the result must be
  read from stdout, never from `$?`.
- The gate compares **decoded text** (`read_text(encoding="utf-8")`, then `a == b`), not raw bytes;
  only the manifest mode hashes bytes via `_sha`. "Byte-identical" is a slight overstatement of what
  is checked, though for UTF-8 output the two agree.

A fourth, from `DESIGN_kdraw_stability.md:323`: that document says "`parse_any_version` strips
non-schema keys". **It does not.** `parse_any_version` and `migrate_to_current` never delete keys —
they return a deepcopy, and the migration path *adds* stamp keys. Unknown keys are dropped later, at
`Preprocessing.model_validate`, because `model_config` is `{}` and pydantic ignores extras by default.
The end state matches the doc's conclusion; the layer is wrong. **And an unknown step `kind` is not
stripped at all — it raises `ValidationError`.** Motion is safe on that count only because
`MotionCorrection` is already in the union (§0.1).

### 3g. The probe, and whether any runner is needed

`extractor_mvp/scripts/variance_probe.py` (156 lines, added in `7f0bdfd`, unchanged since) is the
harness `variance.md:3` and `variance-harness-findings.md:10` describe. Against the prereg's probe —
K=10 on `motion_correction.method` across six papers — item by item:

| requirement | status |
|---|---|
| K=10 | **works today** — `--n 10` |
| the six papers | **fails** — `--papers power_2014` raises `KeyError` at `:75` before any model call. All six PDFs *are* in the hardcoded `_CORPUS`, so this is a 6-entry dict addition |
| the field | **fails** — `('motion_correction','method')` is not in the hardcoded `_TARGETS`; a 1-entry list addition |
| per-draw recording | **does not meet the prereg.** `:8` requires `verbatim`, `resolved`, `resolution`, span per draw; the script records only `f"{status}:{value}"`, truncated to 40/120 chars by `render()`, with no per-draw rows, no `Extracted.spans`, and no deferral `target_kind` — which state-map rows 4/5 (`:73-74`) need |

**And even with those edits the result would be `ABSENT` on every draw**, because the extractor emits
no motion step — shown by applying the script's own `_field_state` to a stored artifact.

**The decisive finding: the probe has no technical dependency on the K-draw stability runner.** The
prereg contains **0** hits for `stability`, `flip`, `K-draw`, `runner`, `harness` and
`variance_probe`; its 2 `variance` hits are the `variance.md` citation (`:7`) and the word inside
binder's quote (`:114`). `DESIGN_kdraw_stability.md` says the same from its side (`:20`, `:40-43`).
The fixed-input, parameterised-K repeat pattern the probe needs **already exists twice**:
`variance_probe.py --n`, and `chen_fix_ab.py` with `--paper/--pdf/--k` writing per-draw JSONL — which
is the script that produced the K=10 temporal finding the prereg itself cites
(`temporal-firewall-fix.md:3`). `chen_fix_ab.py`'s limits: `--field` offers two values, and it captures
the raw `FieldExtractionResult`, not the post-processed `SpecifiedTerm` or spans.

**What the probe actually depends on is the extraction this document designs.** That is extractor
work, not runner work.

One peripheral correction: `DESIGN_kdraw_stability.md:32` gives "`variance.md` 4" as a positive-control
hit count; at HEAD `variance.md` has 3 case-sensitive and 5 case-insensitive `variance` hits. That
document states its locators were verified at `20f3694`, not at HEAD.

And a caveat on the harness's own provenance: the committed script would **not** reproduce
`results/VARIANCE_PROBE.md` byte-for-byte. The table's mtime (2026-07-10 16:58) precedes the script's
only commit by ~16 hours, and its separators (`×`, `·`) differ from HEAD's `render()` (`' x'`, `' / '`).
Since 0.5.0 several targeted fields are `SpecifiedTerm`, so HEAD would stringify
`verbatim=... resolved=... resolution=...` where the old table shows bare `EXTRACTED:fsaverage5`.

### 3h. The labels, and their contamination

19 papers, 17 columns, bounded as §0.6 sets out. Column headers pair a `_state` with a `_verbatim`
for bullets 2–7, with bullet 1 carrying `method_state`, `method_value`, `method_quote`. Bullet 6's
single state column is `interpolation_combined_state`.

Contamination, each figure checked at its source:

| figure | status |
|---|---|
| 13 co-adjudicated | listed **by name**, in §7 of the protocol |
| 7 prompt-fitted by CALL 10's derivation | listed **by name**, in the CALL 10 table |
| overlap 4 | listed **by name**, in the disclosure sentence |
| **union 16 of 19** | **asserted only** — no arithmetic shown, members not listed. Correct when recomputed (13 + 7 − 4 = 16), and 19 − 16 = 3 is consistent |
| 3 clean: liu_2005, tang_2025, wheaton_2004 | named as "clean on both axes" — **but the protocol immediately qualifies tang_2025** as "label-adjudicated in the session that produced this call" |

So the three constituent numbers are each derived but stated in three different places, the union is
asserted, and "three clean" is clean-in-the-sense-of-outside-both-counted-sets, not untouched. A
design doc should carry the qualifier with the number.

**The record's conclusion** (`protocol:547-550`): a motion figure is **diagnostic only, explicitly not
evaluative**.

---

## 4. The forks — RULED 2026-10-19

All five ruled on the same day, by the author in conversation, written down here the same day and
**not backdated**. The forks are kept in place below rather than collapsed into a spec, so a later
reader can see what was chosen against.

| fork | ruling |
|---|---|
| A — one call or two | **a separate call per new step kind; freeze `EXTRACTION_PROMPT` and pin its hash in a test** |
| B — which fields | **`method` only, per prereg `:5`; bullets 2–7 by amendment after the probe** |
| C — turning the row on | **turn it on with `method`, after the conditional-row consistency ruling (§4.3)** |
| D — scoring | **counts only, labelled diagnostic, exclusions listed by name, no rate** |
| E — order vs. the stability runner | **extraction and the probe may precede the runner; scores may not. Build the probe's per-draw recorder in the runner's record format** |

### Ruling A — a separate call per step kind, and a hash pin on the shared prompt

*Reason.* With one shared prompt, every new row disturbs every field already validated. That is
measured here, not assumed: the v1→v2 change coerced **5 of 7** MNI terms at the shipped level (6 of 7
at the raw value level, §2). It is also the general finding in the literature on prompt sensitivity —
Sclar et al., *Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design*
(arXiv 2310.11324; ICLR 2024), which measures how much performance moves across prompt variations that
are semantically equivalent. Separate calls keep each row's validation intact when the next row lands,
and the hash pin turns a new vintage into a deliberate act rather than a side effect.

*Costs, including two this document did not previously list.*

1. One extra call per paper per row. At the measured mean of **11.87 s** per call (§4.1), that is one
   more unit of that cost per row, not a rounding error — and it doubles the reask surface, since
   `max_retries=2` applies per call.
2. **The per-acquisition path gets no motion unless it is wired separately.**
   `PER_ACQUISITION_EXTRACTION_PROMPT` is built as `prefix + EXTRACTION_PROMPT` (`extractor.py:966`),
   verified at HEAD: `PER_ACQUISITION_EXTRACTION_PROMPT.endswith(EXTRACTION_PROMPT)` is `True`. A
   second call reached only from the single-acquisition path therefore leaves multi-acquisition papers
   with no motion extraction at all — silently, since nothing asserts parity between the two paths.
3. **The hash pin does not cover a known copy of the prompt's text.**
   `subject_validator.py:41` records that its taxonomy is "Lifted VERBATIM from EXTRACTION_PROMPT's
   DECISION RULE". A hash over `EXTRACTION_PROMPT` pins the prompt and not that copy, so the two can
   still drift apart in either direction without failing. If the pin is meant to protect the contract
   rather than just the string, it needs a second assertion tying the copy to its source.

*A benefit the proposal does not claim, and it resolves a real tension.* Prereg **C11** (`:28-30`)
licenses iterating stanza wording on the six already-contaminated probe papers. Under one shared
prompt that licence collides head-on with a hash pin — every licensed iteration would break the hash
and re-vintage `target_space`. With motion in its own prompt, the licence applies to a string that is
not pinned, and the two mechanisms stop fighting.

*Consequence to record:* `extractor.py:168`'s wrong "six" (§0.3) is inside the string this ruling
freezes. Fixing it becomes a deliberate prompt change under the pin, not a comment correction — which
is exactly the behaviour the pin exists to produce.

### Ruling B — `method` only, bullets 2–7 by amendment after the probe

*Reason.* The prereg already commits to it (`:5`, "Build `motion_correction.method` only"), and
`method` alone is enough to turn the row on (§3d). Bullet 7's two-part wording (§3a) and its missing
second-disjunct field wait until then, so the sub-clause question need not be settled to start.
Per-field cost sites (R2–R6, §3c) are paid once instead of seven times; the per-step sites (R7–R9) are
paid once either way.

### Ruling C — turn it on with `method`, after the consistency ruling

*Reason.* Motion runs through the existing step-field builder, which already records *why* a field is
missing — so the information needed to keep the row silent on a dropped quote is present at the point
of decision; it is simply not consulted for non-software rows today (§4.3). Ordering is therefore
substantive, not procedural: the §4a extension lands first, in its own commit with its own derived
gate expectation, or motion ships a known false line.

### Ruling D — counts only, diagnostic, exclusions by name, no rate

*Reason.* `protocol:547-550` concludes diagnostic and explicitly not evaluative, and the prereg
forbids an accuracy figure outright (`:9-10`, `:158-159`). This is the same rule as
`DESIGN_kdraw_stability.md` fork 6 — emit counts, and no fraction without its denominator — applied to
a second measurement for the same reason.

### Ruling E — extraction and the probe may precede the runner; scores may not

*Reason.* The dependency that appeared to force the other order does not exist (§3g): the prereg names
no runner, and the probe's need is the extraction this document designs. What survives untouched is
`DESIGN_kdraw_stability.md` §6's actual argument (`:479-485`) — a score computed from one draw of an
unstable field is a sample reported as a value. So **extraction and the probe go first; any motion
score waits on stability.**

*The build instruction that makes this once-only work.* Extend `variance_probe.py` to meet prereg
`:8` — `verbatim`, `resolved`, `resolution` and span **per draw** — and write those records **in the
K-draw runner's record format**, which is already specified even though the runner is not built:
`DESIGN_kdraw_stability.md` §4b sub-decision 1 (the comparison reads `Extracted.value` only, no
normalisation, excluding `spans`, `confidence`, `span_recovered`) and fork 2 (keep the full per-draw
field; status and value agreement as separate counts). That honours `TRACK_A_SCOPE.md:237-238`'s
"should be built once, for both" without waiting for the runner.

*Recorded in both places.* This ruling changes the order recorded at
`DESIGN_kdraw_stability.md:476-477`, so it is written there too, as a dated amendment with the
superseded text retained.

---

Each fork's evidence and costs, as they stood before the rulings, are kept below.

### 4.1 Fork A — one extraction call, or two. *This is the architecture decision for adding rows at all.*

Not a motion question. §3b establishes there is **one** shared hand-written prompt and **one** call for
every field, so this fork is decided once and inherited by smoothing and every row after it.

**One call (add stanzas to `EXTRACTION_PROMPT`).**
- Cost: the prompt changes, so **the next `target_space` numbers are a new vintage**. §2's ruling makes
  that acceptable, not free. The coercion evidence (§2) shows a prompt edit moves already-reported
  values.
- Cost: every future field is coupled to every other. The stanzas already cross-reference
  (`:242-244`) and a stanza already names fields that do not exist (`:327`), so coupling is present,
  not speculative.
- Benefit: no new call, no new cost. Per-paper wall time is unchanged.

**Two calls (a separate motion call on the same slice).**
- Isolation: a motion stanza cannot move `target_space`, so committed numbers keep their vintage
  without relying on §2.
- Cost: multiplies calls. §3g of `DESIGN_kdraw_stability.md` prices the existing shape at **mean
  11.87 s / median 11.35 s per paper**, N=162 gaps pooled over 9 draws; K=3 → 57 calls ≈ 11.3 min,
  K=10 → 190 calls ≈ 37.6 min, doubling if every call reasks. *Note:* that section measures and labels
  **per-paper** wall time and equates it with per-call by noting one `create()` per paper — so a second
  call per paper is a second unit of that cost, not a free addition.
- **Feasibility is settled, not open:** the methods slice is a **value passed in**, and nothing in the
  extraction path recomputes it. `find_methods_section` and `load_pdf_text` are never called from
  `extractor.py`; the caller computes them (`batch.py:231`, `:253`) and wraps the slice in a
  `ParsedPaper` (`:255-257`). And the N+1-calls-on-one-slice pattern **already ships**:
  `extract_multi_acquisition` (`multi_acquisition_extractor.py:41-85`) calls `discover_acquisitions`
  (its own `create()` at `acquisition_discovery.py:87`) and then
  `extract_preprocessing_for_acquisition` once per acquisition, all on one `ParsedPaper`, with no
  re-parse. `MethodsSlice` is `@dataclass(frozen=True)` and nothing in `src` assigns to
  `parsed_paper.text`.

So two calls costs calls, not re-parsing. The fork is a vintage-coupling question, not a plumbing one.

### 4.2 Fork B — field scope: `method` only, or all seven bullets

- **`method` only** is what the prereg scopes: `:5`, "Build `motion_correction.method` only." It is
  also the only field the probe needs, and the only one with a committed `method_value` column.
- **All seven bullets** is what the labels cover — `_state`/`_verbatim` columns exist for bullets 2–7
  (§3h), so the ground truth is already there for a wider build.
- Every bullet **has** a spec field (§3a), so field scope is not constrained by the schema. The one
  gap is sub-clause: bullet 7's "integration with slice time correction" disjunct has no field, and
  CALL 8 exists precisely to distinguish the two disjuncts.
- Cost asymmetry: R2–R6 in §3c are *per-field* (*k* stanzas, *k* tuples, *k* entries); R7–R9 are
  per-step and paid once either way. The protocol notes that bullets 2–7 are "attestation only"
  whereas `method` "determines performance" (labels footer, row 22) — so the two scopes are not merely
  different sizes, they measure different things. `TRACK_A_SCOPE.md:244-245` records the open empirical
  question that bears on this: "measuring stability on **attestation** judgements specifically ... since
  attestation may be far more stable than value extraction."

### 4.3 Fork C — what makes the motion row turn on

**Correction to an earlier draft of this section.** It said `covered ∧ ¬addressed` "emits the
violation section against the author". That is false for motion, and it overstated the stake.

**The violation section takes the Software row and nothing else**, by two hardcoded `row_id` checks —
`render.py:778` (`rc.row.row_id == "software"` for the header suffix) and `render.py:846`
(`software = by_id["software"]`). The code says so itself at **`render.py:840`**:
`# 1. Unconditional violation: only the Software row can appear here.`, and the docstring repeats it at
`:745-746`. Note the restriction is keyed on `row_id`, **not** on the `unconditional` flag — which is
read in exactly one place in all of `src` (`render.py:891`), to build the conditional list. `cobidas.py`
never reads it at all; it special-cases `row_id == "software"` at `:254`. Of the 16 rows, 14 are
mandatory and **exactly one** is unconditional (`software`); `motion_correction` is mandatory,
conditional (`cobidas.py:59`).

**So an assessed-but-not-addressed motion row lands in the honest-gap bucket**, under
`### Not reported whether performed (mandatory if performed)` (`render.py:894`), built at `:890-892`,
and the report disclaims violation in its own voice at `:897-901`:

> `(Silence is not a COBIDAS violation for these rows; the standard requires reporting only if the
> step was performed. Presence cannot be determined from the text.)`

with the code's framing at `:889`: `# 2. Conditional mandatory rows, unaddressed: honest gaps, not
violations.`

**What turning the row on actually changes, measured on a real report.** braun's stored report already
lists motion under that heading — `braun_2015.md:62`, `- Motion correction  (no fields assessed by
current extractor)`. The suffix comes from `_tag` (`render.py:838`):
`return "" if rc.covered_by_extractor else "  (no fields assessed by current extractor)"`. So the
change is narrow and exact: **the row loses that disclaimer** and becomes a bare `- Motion correction`,
moving from `Not assessed by AESPA` into the `Assessed by AESPA → not reported` numerator.

**The real risk, correctly sized.** Once the row is covered, a paper whose motion quote fails to
resolve renders as a bare `- Motion correction` — AESPA stating it looked and found no report, with the
hedge gone. **That is not an accusation, and it is still false** when the paper did report motion
correction and only the quote drop lost it.

#### The question this actually raises — settle it once for all conditional rows, before motion goes live

`DELTA_base_pipeline_diagnostic.md` §4a ruled that an unverifiable quote keeps a row **silent** rather
than counting as assessed. **That ruling was applied to the Software row only.** `assess_coverage`'s
branch (`cobidas.py:253-264`) sends only `row_id == "software"` to `_software_coverage`, which is the
only function that consults `_UNVERIFIABLE_GAP_BASES` (`:133-139`); every other row goes through
`_row_covered_by_extractor` with `unverifiable = False` hardcoded.

**And the mechanism is stronger than "a dropped quote counts as assessed".** For non-software rows,
coverage does not read the paper at all:

```
def _row_covered_by_extractor(field_rows: list[Any]) -> bool:
    return any(r.left_missing_reason != _UNTARGETED_REASON for r in field_rows)
```

A dropped quote yields the **same** `RowCoverage` as `not_stated_in_text` — both `covered=True`.
Measured over the stored corpus: the two coverable rows are covered on **359 of 359** stored specs, and
every other row on **0 of 359**. *Denominator, stated 2026-10-19 because a second pass disagreed with
it:* 359 is the number of `Preprocessing` blocks under `extractor_mvp/results/` that **validate** —
not a file count, which is why it exceeds the number of JSONs. 364 blocks are found in total; four
multi-acquisition files hold more than one (`batch_multi_acq/papers/`: cho_2021 ×4, greene_2022 ×3,
marek_2022 ×3, yang_2025 ×3). **5 blocks fail to parse**, all with
`MigrationError: document source schema 0.1.0 is below the migration floor 0.2.0`, in
`batch_reextract/papers/liu_2013.json`, `batch_sfn_v2/papers/viduarre_2017.json`,
`batch_sfn_v3/papers/liu_2013.json`, `batch_sfn_v4/papers/viduarre_2017.json` and
`batch_sfn_v5/papers/viduarre_2017.json`. 364 − 5 = 359. So the dropped quote never moves `covered`; it moves `addressed`. The
row is assessed because the field is *targeted at all*. **Extending §4a to conditional rows therefore
means making their coverage paper-dependent for the first time**, which is a larger change than the
Software precedent makes it look.

**The "settle once" set is exactly two rows today, and motion is the third.**

| row | mandatory | fed by | on a dropped quote |
|---|---|---|---|
| `intersubject_registration` | yes | `spatial_normalization.target_space`, `.resolution_mm`; `surface_projection.target_surface`, `.surface_registration` | covered, not addressed → bare line under the heading |
| `intensity_normalization` | no | `intensity_normalization.convention`, `.value` | covered, not addressed → bare `- Intensity normalization (N)` under *Optional per COBIDAS*. Real case: `batch_sfn_v5/papers/mueller_2021.json`, both fields `extraction_quote_unresolved:quote_not_found` |
| `motion_correction` | yes | *(would be)* `motion_correction.method` | **would become the third, and the second mandatory one** |

Every other conditional row is unreachable: `software_citation` has `spec_kinds=()`; nine rows have no
kind emitted by `_assemble`, so `mapped=[]` and `any([])` is False; and `brain_extraction`,
`segmentation` and `artifact_structured_noise_removal` have their step emitted but every field
`not_targeted_by_mvp`. `temporal_standardization.method` is targeted and does have dropped quotes in
stored data, but its kind is in `DIVERGENCE_KINDS` (`cobidas.py:106`) and maps to no D.3 row, so it
escapes.

**The claim that this already affects Intersubject registration holds, with one exception.** True for
**3 of the 4** papers carrying a `target_space` dropped quote (7 of 8 files); for liu_2005 in
`batch_sfn_v3` the row is `addressed=True` anyway, because `resolution_mm` is EXTRACTED and any one
addressing field is enough (`cobidas.py:260`, `_ADDRESSING_STATUSES = {"EXTRACTED",
"DEFERRED_TO_CITATION"}`).

**Two corrections to reason strings an earlier draft implied.** `value_not_in_literal` is **not
produced anywhere in `extractor.py` at HEAD** — it survives only in a docstring (`:492`) and a comment
(`:1179`), and it is not a quote failure. And `quote_not_found` / `quote_ambiguous` never stand alone;
they appear only as suffixes after `extraction_quote_unresolved:` or `deferral_quote_unresolved:`. The
dropped-quote reason to key on is `extraction_quote_unresolved:*`.

**Consequence for sequencing, and it is not optional.** Extending §4a to conditional rows **changes
stored reports** — every paper with a `target_space` dropped quote loses its Intersubject registration
line from the assessed bucket. So it is **its own commit, with its own derived gate expectation**, and
it cannot ride along inside the motion change without destroying that change's attributability. It
also lands *before* motion goes live, or motion ships the defect knowingly.

One locator note: `DELTA_base_pipeline_diagnostic.md` §4a cites `_software_coverage` at
`cobidas.py:142-191` with `:187` and `:191`. At HEAD the function is `174-234`, the untargeted check is
`:221`, the final return `:234`, and `:142` is now `_gap_base`. Drift in a historical design doc;
behaviour unchanged.

The mapping check itself is **clean**: motion maps to exactly one row, no shared kind, no double
credit (§3e).

### 4.4 Fork D — scoring

The `value_kind` ruling places the discrimination in the scoring map, not the LLM schema. Verbatim,
prereg `:51`: "**Ruling (2026-08-19): option (b) — the discrimination lives in the scoring map, not in
the LLM schema.**" `:66`: "`value_kind` below is **derived by the heuristic**, not emitted by the
model."

Recorded only in **two** places, and this is worth knowing: inside the prereg itself, and
`DEVLOG.md:980-991` — which is outside `docs/` and which says it was written **retroactively** on
2026-08-26. There is no separate ruling document. The two records also differ in wording ("not in the
LLM schema" versus "not the LLM schema").

The three declined alternatives bind the design (`:52-58`): (a) a fourth status is **blocked** —
`provenance.py` is contract-frozen with three arms (`provenance.py:4`, and the three are at `:51`,
`:60`, `:81`); (c) a model-emitted `value_kind` is "viable and additive, declined for now to avoid
changing the LLM output contract before the stanza exists"; (d) keying on `SpecifiedTerm.resolved` is
ruled out because "a real tool absent from the resolver vocabulary would resolve to `None` and read as
`described_only` — the false-missing class `SpecifiedTerm` exists to prevent."

**What a motion score must carry, given §3h:** the contamination union of 16 of 19 with tang_2025's
qualifier, the `diagnostic, not evaluative` label from `protocol:547-550`, the non-comparability
statement required by `:36-38`, and the three excluded classes as named lines (`:134-136`). What is
open is whether a motion *score* should be computed at all before the three clean papers can carry
anything, and that is a ruling, not a fact.

### 4.5 Fork E — order relative to the stability runner

**The technical half of this fork dissolves.** §3g: the probe has no dependency on the stability
runner; its dependency is on the extraction this document designs. So "stability before motion" cannot
be justified by the probe needing the runner.

**The rest of the fork does not dissolve.** `DESIGN_kdraw_stability.md:476-477` records the order as
"stability before further labelled rows — motion's extraction side, then smoothing", and §6 at
`:479-485` gives the reason: a score computed from one draw of an unstable field is a sample reported
as a value. That argument is untouched by the dependency finding — it is about trusting motion's
numbers, not about being able to produce them.

Pulling in the other direction, `TRACK_A_SCOPE.md:237-238` records that the trust question "**shares
machinery with** Track B's pre-registered K-draw reachability probe, and should be built once, for
both" — a recorded preference for one runner serving both. Against that: §3g shows two scripts already
implement the repeat pattern, so "built once" may describe work already done twice.

**Ruled: see ruling E above.** Extraction and the probe may precede the runner; scores may not; and
the probe's per-draw recorder is built in the runner's record format so the work is done once. The
change to the recorded order is written into `DESIGN_kdraw_stability.md` §6 as a dated amendment with
the superseded reading retained — because §2's own lesson is that a sequence existing only in
conversation gets contradicted by the record.

---

## 5. The pre-registered sequence, verified at HEAD, as constraints on implementation order

All 30 constraints below are quoted from `docs/findings/motion-method-reachability-prereg.md` at HEAD
(162 lines, v1 `ccf8a35` plus append-only Amendment 1 `44f285f`; `git diff 44f285f..HEAD` on the file
is **0 lines**).

**Scope and timing.** C1 `:3` — governs "extraction and scoring, **not labelling**". C2 `:3` —
"**Pre-registration, committed BEFORE the run — the run has not happened.**" C3 `:5` — the probe
"gates the state-map".

**What the probe builds and records.** C4 `:5` — "Build `motion_correction.method` only." C5 `:5-7` —
the six papers, with agtzidis_2020 as positive control → SPM12 and poldrack_2015 as APPLY control
"must not yield applywarp". C6 `:7-8` — "**K = 10** per paper, per `variance.md` and the temporal
finding's fixed→fixed 4/10 → 0/10." C7 `:8` — "Record `verbatim`, `resolved`, `resolution`, span per
draw." C8 `:9-10`, `:158-159` — no accuracy figure.

**Inference and iteration.** C9 `:20-22` — readings 1–3 are "extraction errors to record", not evidence
against CALL 10. C10 `:24` — "State both directions before the run." C11 `:28-30` — stanza iteration on
probe results is safe because all six probe papers are already contaminated, and is "**not** a licence
to extend that iteration to any of the three clean papers (liu_2005, tang_2025, wheaton_2004)".
C26 `:122-123` — the vocabulary may not be seeded from those three.

**Scoring.** C12 `:32-33` — add `span_role ∈ {estimate, apply, consume, host, out_of_scope}`; "a cell
counts correct only when **state, value and span_role** all match". C13 `:36-38` + `:138-141` — the
rationale must state the figure is stricter and not comparable to 82.4% or 11/17. C27 `:127-132` — the
three-part correctness rule, with tool identity not string identity. C28 `:134-136` — exclusions as
named lines. C29 `:151` — reading 3 "is the reading that only the `span_role` rule catches; a
state-only scorer would mark it correct."

**The ruling and the state map.** C14–C17 `:51-66` — option (b), the declined alternatives, `value_kind`
derived not emitted, and the `target_space_scoring_map.csv` precedent (its HEAD header is
`resolved,resolution,label_state,rationale` — confirming `:35`'s claim that it has no span column).
C18 `:68-75` — the six state-map rows. C19 `:77-81` — `stated_not_performed` has no extractor state, is
"unreachable-but-unexercised", and "if a future corpus exercises it, the map is invalid for that cell
and must be amended before scoring". C20 `:88-90` — a supplement deferral maps to `unread`; "under
ruling (b) this is a map rule, not a code change".

**The heuristic's frozen vocabulary.** C21 `:94-95` — "**Enumerated here, before the run.** The
vocabulary may not be extended after seeing output; an extension is an amendment with a stated reason
and both numbers reported." C22 `:97-99`, C23 `:101-104`, C25 `:110-111` — the `operation_phrase` and
`tool_name` lists, both checked, "a `value` matching both is `undecided`, not a precedence winner".
C24 `:106-108` — "`undecided` — anything else. **Halt the cell.** Do not default to either side."

**Ordering consequences for implementation.** C2 + C21 together mean the stanza wording and the
heuristic vocabulary are **frozen before the probe runs**, and C11 means the probe is the only place
stanza iteration is licensed. So the implementation order the prereg imposes is: build
`motion_correction.method` → freeze the stanza and vocabulary → run the probe on the six contaminated
papers → only then touch the state map. Iterating the stanza *after* seeing clean-paper output is
forbidden, so clean-paper extraction must not precede the probe.

### Three internal tensions in the prereg, flagged not resolved

These are the document's own, not this one's, and each needs an author ruling before scoring.

1. **The "40 clean draws" arithmetic does not close.** C30 `:159-160`: "one `verbatim=None` draw on
   power or binder demonstrates unreachability while 40 clean draws are evidence and not proof". But
   power + binder at K=10 is **20** draws. **40** is the four `described_only` papers (derosa_2025,
   liu_2013, power_2014, binder_1999 — `:120-121`) × 10. The prereg does not say which papers the 40
   span, and the asymmetric rule names only two of them. So "asymmetric, any-single-draw" is
   **any-single-draw on power or binder specifically**, not on any of the six.
2. **The unreachability trigger names a field the LLM schema does not have.** The trigger is
   `verbatim=None`. `FieldExtractionResult` has `value` and `verbatim_quote`
   (`extraction_result.py:27-28`); `verbatim` is a `SpecifiedTerm` field (`preprocessing.py:103`).
   Amendment 1 (`:45-46`) says the LLM output schema is `FieldExtractionResult`, but it does not revise
   `:8`'s recording list — which names the `SpecifiedTerm` fields — nor state how `verbatim=None` maps
   onto the state-map rows.
3. **The pre-declared `undecided` paper is conditional, not predicted.** binder_1999 is named, but only
   "if the extractor's `value` is the algorithm description rather than the word 'coregistered'". The
   prereg does not predict that binder lands `undecided` unconditionally. It also pre-declares a
   value-level `undecided` case ("motion correction via ICA-AROMA") tied to no paper.

A fourth, non-blocking: `:107-108` makes the `undecided` count "the empirical measure of whether
ruling (b) was adequate: a high count is the argument for revisiting (c)" — but **no number defines
"high"**, in either document.

---

## 6. Acceptance, stated now so it cannot drift

Any implementation must show all of these.

1. **The identity gate matches the derivation in §3f, not an assumption.** If the change touches only
   `_assemble`, `PreprocessingExtraction`, `_FIELD_SPECS` and the prompt: **19 identical, 0 changed**,
   read **from stdout**, because `_differ` returns exit 0 either way (`rerender_reports.py:252`). The
   run must also prove the `PYTHONPATH` override took effect, since a failed override produces `19
   identical` too (docstring `:31-36`). If the change also touches `cobidas.py`'s motion row or any
   `render.py` wording on that row, the expectation is **not** 19/19 — every stored report carries that
   row's line — and the new number must be derived before the run, not explained after it.
2. **No accuracy figure is computed from or cited out of the reachability probe** — prereg `:9-10`,
   `:158-159`. Not in a rate, not in a Wilson interval, not in an accuracy table.
3. **Any motion figure is labelled diagnostic, not evaluative, and carries the contamination finding**
   — `protocol:547-550`, with the union of 16 of 19, the three clean papers, and tang_2025's own
   qualifier (§3h). A7 supports exactly this and nothing stronger.
4. **Every new rate names its vintage and its aggregation rule** — the standing requirement from
   `20bbd2a`, which §2's ruling depends on rather than relaxes.
5. **The mapping check passes before the row turns on:** motion maps to exactly one row, no row shares
   its kind, and a synthetic single-field run credits only the motion row (§3e). Re-run at
   implementation time, because a row added to `COBIDAS_D3_ROWS` in between would invalidate it.
6. **The stanza wording and the heuristic vocabulary are frozen before the probe runs** (C2, C21), and
   stanza iteration touches none of liu_2005, tang_2025, wheaton_2004 (C11, C26).
7. **`undecided` cells halt and are counted, never defaulted** (C24), and `unread`, `undecided` and
   `multi_target_unscoreable` are reported as named lines, never folded into a rate (C28).
8. **If the implementation reports a stability number for motion, the prereg amendment is written
   first** — dated, append-only, superseded text retained, per `DESIGN_kdraw_stability.md:452-455` and
   §1's constraint 1.

---

## 7. Not settled here

- **The conditional-row consistency ruling (§4.3)** — whether §4a extends to conditional rows. Its own
  commit, its own derived gate expectation, before motion goes live.
- **Whether one `slice_to_volume` bool covers both of bullet 7's disjuncts** (§3a), and which of the
  protocol's two wordings of bullet 7 governs. Deferred by ruling B until after the probe.
- **Whether `temporal_standardization.method`'s exclusion from `_LAYER2_FIELD_IDS` and `_DIFF_FIELDS`
  is deliberate** (§0.3). Nothing found in this pass records a reason either way.

### Timing correction: three of these block the PROBE, not scoring

An earlier draft of this section said the prereg tensions "need a ruling before scoring, none blocks
extraction". That is wrong for three of them, and the error is the one pre-registration exists to
prevent.

- **The 40-draw arithmetic** (§5 tension 1) and **the `verbatim=None` trigger's mapping onto
  `FieldExtractionResult`** (tension 2) decide *how the probe's results are read*. A rule for reading
  an outcome, settled after the outcome is visible, is not a pre-registered rule. Both must be ruled
  **before the probe runs.**
- **What counts as a "high" `undecided` count** (`:107-108`): the prereg uses that count to judge
  whether ruling (b) was adequate, so a threshold chosen after seeing the count is not pre-registered
  either — the standard objection in Nosek et al., *The preregistration revolution* (PNAS, 2018). It
  needs a number, before the run.

Only **binder's conditional `undecided`** (tension 3) genuinely waits for scoring: it describes how one
cell is classified after the fact, not how the run is read.

### Stale and false statements — how each is handled, per the author's 2026-10-19 direction

Records are corrected **forward**; code comments must be **true at HEAD** and are fixed **in place**.

| statement | handling |
|---|---|
| `protocol:66` stale locator; `:75`, `:78-79` "`transforms_combined` is NEW / does not exist" (§0.1) | **forward.** The protocol is versioned and append-only — a dated correction, superseded text retained |
| prereg `:86` + `DEVLOG.md:997` cite `extractor.py:726`, now `:730` (§0.5) | **forward**, same reason; the prereg is append-only and the DEVLOG is corrected forward by standing practice |
| `migrations.py:181-193` — the false "NO committed document contains a motion_correction step" at `:184-186`, `:188-189` | **in place**, small commit. It describes current code and must be true at HEAD |
| `retry_audit.py:51` — "The 7 targeted response-model fields" above a list of 8 (§0.3) | **in place**, same commit |
| `DEVLOG.md:619-620` restates the same false claim, and commit `c297479`'s subject carries it | **forward.** And worth recording while correcting: `examples/spec.json` already contained the two motion steps at `c297479^`, so the claim was false when it was written, not merely stale |
| `extractor.py:168`'s wrong "six" | **neither.** It is inside `EXTRACTION_PROMPT`, so under ruling A it is a deliberate prompt change under the hash pin — not a comment fix, and not a correction that may ride along in a small commit |
| `extractor.py:1131`, `:1146`, `field_diff.py:22` | **nothing to fix.** Each is accurate about the constant it annotates (§0.3) |
| `DELTA_base_pipeline_diagnostic.md` §4a's `cobidas.py:142-191` locators, now `174-234` (§4.3) | **forward**, when §4a is next amended for the conditional-row ruling |
- **Whether `motion_correction` should be type-checked into the extractor's conditional sites** —
  `_LAYER2_FIELD_IDS` and `field_diff._DIFF_FIELDS` already omit the seventh targeted field (§0.3), so
  an eighth inherits an existing inconsistency rather than creating one.
