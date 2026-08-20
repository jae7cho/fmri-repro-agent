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

---

## Amendment 1 (2026-08-19) — the pass condition, under ruling (b)

**Why this is needed.** v1 pre-registered the probe but not a pass condition that could be evaluated. The
extractor's LLM output schema is `FieldExtractionResult` (three statuses: `extracted` / `missing` /
`deferred`), not `SpecifiedTerm`. `status="extracted"` requires both `value` and `verbatim_quote`;
`status="missing"` forbids both. So **`described_only` and `named_tool` are the same extractor status**,
differing only in whether `value` holds an operation phrase or a tool name. v1's four derosa readings were
therefore not mechanically distinguishable — readings 1 and 4 are both `status="extracted"`.

**Ruling (2026-08-19): option (b) — the discrimination lives in the scoring map, not in the LLM schema.**
Considered and declined: (a) a fourth status — blocked, `provenance.py` is FROZEN with three arms and a
fourth status has no arm to map to; (c) a model-emitted `value_kind` discriminator — viable and additive,
declined for now to avoid changing the LLM output contract before the stanza exists; (d) keying on
`SpecifiedTerm.resolved` — ruled out by that type's own docstring, which records that `unrecognized` does
**not** decide the grade (gordon "EPI template" and power "atlas space" are both `unrecognized` and grade
differently), and because a real tool absent from the resolver vocabulary would resolve to `None` and read
as `described_only` — the false-missing class `SpecifiedTerm` exists to prevent.

Precedent for (b): `ground_truth/target_space_scoring_map.csv` already discriminates two label states from
one resolver verdict using a "gesture heuristic" on `verbatim`. This is the same mechanism applied to a
different string.

### The state map

`value_kind` below is **derived by the heuristic**, not emitted by the model.

| # | `status` | derived `value_kind` | `target_kind` | → predicted label state |
|---|---|---|---|---|
| 1 | `extracted` | `operation_phrase` | — | `described_only` |
| 2 | `extracted` | `tool_name` | — | `named_tool` |
| 3 | `extracted` | **`undecided`** | — | **UNDECIDED — halt, adjudicate, do not default** |
| 4 | `deferred` | — | `paper` / `pipeline` / `dataset_doc` | `deferred` |
| 5 | `deferred` | — | `supplement` | **`unread`** — not `deferred` (see below) |
| 6 | `missing` | — | — | `absent` |

`stated_not_performed` has **no extractor state**. The three statuses cannot express a stated negative:
`extracted` would put the negation in `value`, which the heuristic would read as an operation phrase and map
to `described_only`. No motion paper carries this label (`absent` 0, `stated_not_performed` 0 across 19), so
it is **unreachable-but-unexercised** and is recorded as a known vocabulary gap rather than a scoring class.
If a future corpus exercises it, the map is invalid for that cell and must be amended before scoring.

**Row 5 rationale.** CALL 9 (protocol v1.4) ruled that a pointer to the paper's **own** supplement is not a
deferral — §6 step 1 makes the supplement part of the paper, so the stream is *unread* and no state is
assigned. The extractor predates that call and still emits `status="deferred"`, `target_kind="supplement"`
for this case; `extractor.py:602` and `:726` already narrow `"supplement"` → `"paper"` when constructing the
frozen `provenance.Deferral`, retaining the original in its own `DeferralRecord` so Fork B can skip
supplement targets. The extractor's behaviour is therefore correct and deliberate; only its *label mapping*
diverged when CALL 9 committed. Under ruling (b) this is a map rule, not a code change. `unread` cells are
excluded from both numerator and denominator, like `multi_target_unscoreable`.

### The operation-phrase heuristic

Applied to `value` when `status="extracted"`. **Enumerated here, before the run.** The vocabulary may not be
extended after seeing output; an extension is an amendment with a stated reason and both numbers reported.

**`operation_phrase`** — `value`, lowercased, contains any of:
`realign` · `motion correction` · `motion-correction` · `head motion` · `head movement` · `coregist` ·
`co-regist` · `rigid body` · `rigid-body` · `volume registration` · `image registration`

**`tool_name`** — `value` contains none of the above **and** matches a tool-shaped pattern: an
initialism of ≥2 capitals (`SPM`, `AFNI`, `FSL`, `CCS`, `CONN`, `DPABI`), a known package or program token
(`MCFLIRT`, `mcflirt`, `3dvolreg`, `Realign`, `FLIRT`, `applywarp`, `ICA-AROMA`, `align_epi_anat`,
`fMRIPrep`, `C-PAC`, `Freesurfer`, `SPM8`, `SPM12`), or a version-bearing token (`\w+\s*v?\d+(\.\d+)*`).

**`undecided`** — anything else. **Halt the cell.** Do not default to either side; record it, adjudicate it
by hand, and count it. The `undecided` count is the empirical measure of whether ruling (b) was adequate: a
high count is the argument for revisiting (c), and defaulting would destroy that signal.

**Both sides are checked, and a `value` matching both is `undecided`, not a precedence winner.** "motion
correction via ICA-AROMA" matches both lists; it must halt rather than resolve silently.

**Known limitation — binder_1999.** Its quote is *"All EPI images were spatially coregistered using an
iterative procedure that minimizes variance in voxel intensity differences between images (Cox, 1996b)."*
If the extractor's `value` is the algorithm description rather than the word "coregistered", it matches no
list and lands `undecided`. This is expected and is the honest outcome — a closed vocabulary cannot
recognise an algorithm described in prose. binder is the case that will show whether `undecided` is rare or
common.

**Contamination.** The vocabulary was seeded from the four `described_only` papers' committed quotes
(derosa_2025, liu_2013, power_2014, binder_1999). All four are already inside the contaminated union of 16 —
derosa, power and binder are `co-adjudicated`; liu_2013 is in CALL 10's fitted seven — so this adds **no new
contamination**. It does not license extending the vocabulary using liu_2005, tang_2025 or wheaton_2004.

### The correctness rule (distinct from the state map)

The state map yields a *predicted label state*. A cell counts **correct** only when all three hold:

1. predicted state == committed label state;
2. for `named_tool`, `value` matches the committed `method_value` (tool identity, not string identity —
   "SPM12" vs "SPM 12" is a match; "FSL" vs "MCFLIRT" is not);
3. `span_role == estimate` (per v1's `span_role` column).

Excluded from both numerator and denominator: `unread` (row 5), `undecided` (row 3), and
`multi_target_unscoreable` per CALL 10. Each reported as a named line in the decomposition, never folded
into an error rate.

**This makes the motion figure stricter than either prior field's** and therefore not comparable to
base_pipeline's 82.4% or target_space's 11/17 — a lower number is a harder rule before it is a worse
extractor. Restated here because v1 stated it only of the `span_role` column, and it now holds of the whole
map.

### derosa's four readings, restated as map outcomes

v1's readings were not distinguishable under the schema. Under this map they are:

| v1 reading | extractor output | map row | outcome |
|---|---|---|---|
| 1 — `FSL` | `extracted`, value `FSL` | 2 → `named_tool` | **error**: CALL 1 binding violation (label is `described_only`) |
| 2 — `ICA-AROMA` | `extracted`, value `ICA-AROMA` | 2 → `named_tool` | **error, different class**: CALL 4 row confusion |
| 3 — CONSUME leak (six motion regressors §2.4.3 / mean FD §2.4.9) | `extracted`, operation-ish value with a CONSUME span | 1 → `described_only` | **state correct, `span_role != estimate` → error**. This is the reading that only the `span_role` rule catches; a state-only scorer would mark it correct. |
| 4 — the target | `extracted`, value e.g. "motion correction" | 1 → `described_only` | **target**; demonstrates reachability |

Note reading 1 and reading 2 both land on row 2 and are distinguished only by `value`, and reading 3 is
distinguished from reading 4 only by `span_role`. Both distinctions are pre-registered here; neither was
evaluable under v1.

**Unchanged from v1:** the probe tests reachability, not accuracy; no accuracy figure may be computed from
or cited out of the probe run; one `verbatim=None` draw on power or binder demonstrates unreachability while
40 clean draws are evidence and not proof; K=10; all six probe papers are already contaminated so iterating
stanza wording on probe results adds no new contamination, and that licence does not extend to liu_2005,
tang_2025 or wheaton_2004.
