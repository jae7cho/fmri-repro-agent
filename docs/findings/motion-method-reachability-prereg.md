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

---

## Amendment 2 (2026-10-21) — five pre-run rulings, and three defects in the heuristic

**Append-only. Nothing above is edited; every superseded reading is quoted here and marked.** Ruled
by the author in conversation and written down 2026-10-21, before the probe runs. The run has still
not happened.

Four of these were raised as "tensions in the document" by a design pass; the fifth was added on
review, because the heuristic decides how the other four read and so had to be fixed first.

### Ruling 1 — the 40 clean draws cover **power and binder only**, so the number is **20**

v1 (`:22-24`) says: *"a single `verbatim=None` draw on power or binder demonstrates unreachability,
while 40 clean draws are evidence *for* reachability and not proof of it"*. The arithmetic does not
close: power + binder at K=10 is **20** draws. 40 is the four `described_only` papers × 10
(derosa_2025, liu_2013, power_2014, binder_1999 — `:120-121`), and v1 never says which set the 40
spans.

**Ruled: the symmetric claim covers power and binder only, and the number is 20.** derosa and
liu_2013 are reported **separately**, not pooled into it.

*Reason.* Draws counted as evidence *for* reachability must also be able to count *against* it, or
the test is one-sided. The unreachability trigger names power and binder; those are the two papers
where a single bad draw is decisive, so they are the two whose clean draws mean anything symmetric.
derosa has four pre-declared readings of its own and cannot contribute to a single bound, and
liu_2013 is the paper CALL 10's role axis was fitted to — its clean draws partly measure the fit.

### Ruling 2 — `verbatim=None` is mapped onto the raw layer, and three causes are reported apart

v1's trigger is `verbatim=None`; Amendment 1 (`:45-46`) states the LLM schema is
`FieldExtractionResult`, which has no `verbatim`. The mapping was never stated.

**Ruled.** The unreachability **trigger** is: the raw `status` is `missing`. A **clean** draw is:
raw `status` is `extracted`, its quote resolves against the text, and the heuristic returns
`operation_phrase`. Everything else is **neither**, and is reported as its own named line.

*Reason.* The processed `verbatim` is `None` in three different situations and only one of them is
about expressibility: (a) the model returned nothing — the real trigger; (b) the model returned a
value whose quote failed to match the text, which is a span-resolution failure, i.e. a TOOL failure;
(c) the model deferred, which is a different state, not an absent one. Folding (b) and (c) into the
trigger would let a tool failure read as "the state cannot be expressed". Each is a separate line in
the decomposition.

### Ruling 3 — every outcome the readings do not cover is declared **now**

v1 names binder as `undecided` only conditionally (`:113-118`) and derosa's four readings do not
cover a deferral. Any outcome not declared before the run is an outcome interpreted after it.

**binder_1999**
| raw output | outcome |
|---|---|
| value contains `coregist…` | **the target** — `operation_phrase` → `described_only`, matching its committed label |
| value is the algorithm description without the operation word | **`undecided`**, and expected: a closed vocabulary cannot recognise an algorithm described in prose (`:113-118`) |
| `status="deferred"` to Cox 1996b | **citation-routing error.** CALL 7: the Cox reference *supports* a described algorithm, it does not substitute for one, so this row is not deferred |
| a tool name absent from binder's own text | **extraction error** — a value the paper does not contain |

**derosa_2025** — in addition to v1's four readings: `status="deferred"` is an **error**, by the same
CALL 7 test (FSL is named as governing a procedure set, which is CALL 1's NOT BOUND case, not a
substitution). And if STEP 0's "use the main one" selects a stream CALL 9 marks **unread**, the
outcome is `unread` — excluded from numerator and denominator like row 5, reported as a named line.

### Ruling 4 — "high" is **≥ 6 of 10 draws undecided on any `described_only` paper**

`:107-108` makes the `undecided` count "the empirical measure of whether ruling (b) was adequate: a
high count is the argument for revisiting (c)" — and never defines high. A threshold chosen after
seeing the count is not pre-registered.

**Ruled: if any `described_only` paper is `undecided` on 6 or more of its 10 draws, option (c) — a
model-emitted `value_kind` — is revisited.** binder counts, because `:117-118` makes it the test of
whether `undecided` is rare.

*Reason.* If the map cannot classify a paper's output on most of its draws, the map has failed that
paper, whatever the corpus-wide average says.

### Ruling 5 — the heuristic's semantics, and three defects in its prose

`:94-111` as written has three problems. All three are fixed, and the fixed version is implemented
at `extractor_mvp/scripts/motion_value_kind.py` and calibrated below.

**Defect 1 — it contradicts itself.** `:101` requires `tool_name` to match when `value` *"contains
none of the above"* **and** is tool-shaped. That makes a both-lists match impossible. But `:110-111`
says *"Both sides are checked, and a `value` matching both is `undecided`, not a precedence
winner"*, and gives `"motion correction via ICA-AROMA"` as the string that must halt. Under the
prose as written that string returns `operation_phrase` and never halts.
**Ruled: the two tests are INDEPENDENT, and a double match is `undecided`.**

**Defect 2 — the version pattern catches plain numbers.** `\w+\s*v?\d+(\.\d+)*` — `\w` includes
digits, so any run of two or more digits is tool-shaped, including the `1996` inside binder's own
citation. **Ruled: restrict to letters followed by digits.** The pattern the implementation runs, quoted
exactly: `[A-Za-z]+\s*v?\d+(?:\.\d+)*`. (`(?:…)` is a non-capturing group; it matches identically to
`(…)` under `re.search`, and is written here in the form the code uses so the two cannot drift.)

**Defect 3 — common imaging acronyms read as tools.** "an initialism of ≥2 capitals" matches `EPI`
and `BOLD`, so any phrase mentioning either is tool-shaped. **Ruled: they are not tool-shaped.**
Implemented as a named exclusion set — `EPI, BOLD, MNI, TR, FD, RMS, ROI, FOV, SNR, CSF, GM, WM` —
rather than a narrower pattern, because the exclusions are the part a later reader needs to see and
argue with. `FD` and `RMS` are there on CALL 10's authority: they are CONSUME statistics, never the
value.

**This defect was load-bearing, not cosmetic.** Without the exclusion, binder's committed quote is
*both* an operation phrase and tool-shaped — because it opens "All EPI images…" — so it would halt
as `undecided`, on the one paper `:117-118` designates as the test of whether `undecided` is rare. A
heuristic that halts on its own test case cannot measure it.

### Calibration — inputs and outputs, recorded before the run

Run against the implementation at `scripts/motion_value_kind.py`; pinned as tests in
`extractor_mvp/tests/test_motion_value_kind.py`. **The implementation was fixed until each string
landed where this document says, not the reverse.** Every string is from this pre-registration or
from a probe paper's committed quote; no text from any paper outside the six was used.

| input | output | authority |
|---|---|---|
| `motion correction via ICA-AROMA` | **undecided** | `:110-111`, the string this document says must halt |
| `coregistered` | **operation_phrase** | `:98` (`coregist`) |
| binder's algorithm description *without* the operation word | **undecided** | `:113-118`, the known limitation |
| `SPM12` | **tool_name** | `:103` |
| `FSL` | **tool_name** | `:102` |
| `ICA-AROMA` | **tool_name** | `:103` |
| `applywarp` | **tool_name** | `:103` |
| `motion correction` | **operation_phrase** | `:98`; derosa reading 4's target |

**binder_1999's FULL committed quote returns `operation_phrase`** — `is_operation_phrase=True`,
`is_tool_shaped=False` — and therefore state-map row 1, `described_only`, which **matches its
committed label**. Reported because it was not obvious, and because both of ruling 5's fixes are
load-bearing in reaching it: defect 3's exclusion keeps `EPI` from making the quote tool-shaped, and
defect 2's restriction keeps `(Cox, 1996b)`'s year from doing the same. So the `undecided` branch
`:113-118` anticipates requires the value to be the algorithm description *without* the operation
word — the row above — not the full sentence.

### Unchanged by this amendment

Everything in v1 and Amendment 1 except as superseded above: the probe tests reachability, not
accuracy, and no accuracy figure may be computed from or cited out of it; K=10; the six papers and
their two controls; the frozen vocabulary may not be extended after seeing output, and an extension
is an amendment with both numbers reported; the iteration licence covers the six contaminated probe
papers and does not extend to liu_2005, tang_2025 or wheaton_2004.

**One addition to C2/C21's enforcement.** The stanza is hash-pinned
(`extractor_mvp/tests/test_prompt_pin.py`) and the probe writes that hash into its provenance
header, so every draw names the stanza it ran under and a mid-probe edit cannot be passed off as the
pre-registered one. The stanza was revised twice on review before any run — six defects in total,
recorded at the constant and in the pin's dated note — and its hash at the time of this amendment is
`56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a`.

---

## Amendment 3 (2026-10-22) — the positive control was mis-specified; its criterion is void

**Written AFTER the run, which is exactly why it is written here rather than applied quietly.** The
2026-10-21 probe has been executed and its output read. This amendment does not change any pre-run
ruling, any state-map row, or any reported count. It records that one pre-registered criterion was
not sound when it was written, and retires it.

### What was wrong

`:6` specified `agtzidis_2020` as the positive control, "→ SPM12", on the strength of the
committed label `named_tool` / SPM12. **That label contradicted CALL 1 v1.5**, the binding test in
the governing ground-truth protocol. agtzidis names SPM12 once, two sentences before the step
clause, for "the fMRI data analysis" as a whole, and binds no tool to the realignment. Under the
test as written that is the *procedure set* case — derosa's FSL shape — so the correct state is
`described_only`, with SPM12 on the inference arm. The protocol records this as a dated
clarification at `ground-truth-protocol-motion_correction.md` v1.6 (2026-10-22), which keeps CALL 1
v1.5 and corrects its worked example.

So the control asserted an expected answer its own protocol did not license. **Its criterion is void
as stated**, and the probe's agtzidis result cannot be read as a stanza failure: the 9 of 10 draws
that returned an operation phrase are consistent with the corrected label, and the 1 draw that
returned `SPM12` is the outlier.

### What the probe therefore cannot show

**No paper in the six has a named tool as its correct answer.** power, binder, liu_2013, derosa and
poldrack are all `described_only` or controls for other things, and agtzidis has just moved to
`described_only` as well. The probe can show that `described_only` is reachable — rows 1, 2 and 3
were all produced — but it **cannot show that the stanza emits a tool name when a tool name is
correct.** That capability is untested, and no count in this run may be read as evidence either way.

This is a gap in coverage, not a failure. It is stated plainly so that the probe's conclusions are
not over-read: "`described_only` is expressible" stands; "the stanza distinguishes bound from
unbound tools" does not, and was never measured.

### The replacement, and its status

**A replacement positive control is required before any claim about named-tool emission.** It will be
named by the author. Two constraints bind it:

1. **It is chosen after seeing this run.** Any paper picked now is picked with knowledge of how the
   stanza behaved on six others, and a control selected post hoc is weaker evidence than one fixed in
   advance. This must be stated wherever the replacement's result is reported — not as a caveat in a
   footnote but in the same sentence as the number.
2. **It may not be liu_2005, tang_2025 or wheaton_2004** (C11/C26). Those three remain unread, and
   spending one as a control would cost the only uncontaminated cells left.

Until the replacement runs, the named-tool arm is **untested**, and the honest statement of the
probe's scope is: it measured reachability of `described_only` on five papers and one control that
turned out to be mis-specified.

### What is unchanged

Amendment 2's five pre-run rulings stand in full. Ruling 4's trigger (binder `undecided` on 10 of 10,
threshold 6) fired on raw values and is unaffected by any of this. The state map, the `verbatim=None`
trigger decomposition, the heuristic's wording and the stanza hash
`56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a` are all as pre-registered. No
count in `docs/findings/motion-probe-v1-results.md` moves; one label on one of them does.

---

## Amendment 4 (2026-10-22) — the replacement positive control, one C11 iteration, and a deferral line held

**Written BEFORE the seven-paper re-run and AFTER the 2026-10-21 run.** The two facts sit together on
purpose. Everything below that pre-declares an outcome was written before the re-run started; the
run's manifest names the stanza hash this amendment names, which is the checkable part. The commit
that carries this text lands after the run, because commits are blocked until 17:00 on weekdays; the
pre-run status of the text therefore rests on the session record and the manifest's timestamp, not on
commit order. Stated rather than implied.

**Held-out status of the session that wrote this.** No text of liu_2005, tang_2025 or wheaton_2004 was
read. `.rgignore` was in place, no recursive `grep` was run over `results/`, and the probe recorder
refused the held-out ids before a client was built (checked, not assumed). The workbook was read with a
filter that printed only the seven probe papers' rows.

### 1. The replacement positive control is ciric_2017 → `named_tool` / MCFLIRT

Amendment 3 (`:347-361`) required a replacement and bound it two ways. Both are met and both are
stated here so they travel with the number.

1. **Chosen after the run.** The author named ciric_2017 on 2026-10-22 with the six-paper output in
   view. It is post hoc by construction. **Every report of ciric's count must say so in the same
   sentence as the count**, not in a footnote.
2. **Not held out.** ciric_2017 is `co-adjudicated` (protocol §7) and one of CALL 10's seven fitting
   passages (protocol v1.5), so it is already inside the contaminated union of 16 and adding it spends
   no uncontaminated cell.

Its committed label (workbook, HEAD): `method_state = named_tool`, `method_value = MCFLIRT`, quote
*"(3) realignment of all volumes to a selected reference volume using MCFLIRT (Jenkinson et al.,
2002),"*. CALL 10's worked case records the trap: MCFLIRT is named more than once, once in the
ESTIMATE role and otherwise as the source of parameters that are consumed (regressors, RMS
displacement), so the right value with a CONSUME span is the case `span_role` exists to catch (v1
`:31-35`). Counted in its methods slice as the probe loads it: **four** MCFLIRT mentions, one in the
ESTIMATE clause and three in CONSUME sentences; **zero** `/C\d+` glyph leaks (same regex as the v1
scan), so a span failure on ciric cannot be attributed to the mangle that discarded agtzidis's draws.

**Pre-declared readings for ciric_2017**, each a named line:

| raw output | row | outcome |
|---|---|---|
| value `MCFLIRT`, quote = the "(3) realignment …" clause | 2 | **the target** — `named_tool`, value matches, `span_role = estimate`; all three correctness conditions hold |
| value `MCFLIRT`, quote = a sentence about regressors or RMS displacement | 2 | **right value, wrong span** — state and value correct, `span_role ≠ estimate`; the error class that justified the span column |
| an operation phrase ("realignment of all volumes to a selected reference volume" or similar) | 1 | **the failure the control exists to detect** — a bound ESTIMATE tool is present and the stanza did not emit it |
| `realignment … using MCFLIRT` (matches both lists) | 3 | `undecided` — halt, adjudicate by hand, count (`:110-111`) |
| `status="deferred"` to Jenkinson 2002 | 4 | **citation-routing error** — CALL 7: the citation supports a named tool, it does not substitute for one |
| another tool (FSL, FUGUE, boundary-based registration) | 2 | **extraction error** — a tool from a different step or row |
| `status="missing"` | 6 | reported as its own line; ciric is not in ruling 1's power/binder trigger set |

### 2. One stanza iteration under C11, made; its hash; who it fits

**Made.** STEP 3's "BOUND BUT ROUTED ELSEWHERE" was abstract, and on 2026-10-21 derosa_2025 returned
`ICA-AROMA` on 10 of 10 draws (reading 2, `:14`). It now names the row and the tools: COBIDAS D.3
lists CompCor, ICA-FIX and ICA-AROMA under *Artifact and structured noise removal* ("Name of
software/method used (e.g. CompCor, ICA-FIX, ICA-AROMA, etc.)", report p.57 — verified against the
report, not quoted from memory). The stanza says they belong to that row, supply nothing here, "EVEN
WHEN the text says 'motion correction via' one of them", and the value is the paper's own phrase for
the operation. STEP 4's first rule gained "and not routed elsewhere" so its two rules cannot both fire.

- **Stanza hash now** `378a294f94ca9f0fc6bd45bd42caf4646a007c7d705d05c8b5f584dd66ca8cab` (5,090
  characters). **Superseded** `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a`,
  which every 2026-10-21 draw carries and which stays on that run's manifest, projection and
  findings. The pin (`extractor_mvp/tests/test_prompt_pin.py`) carries the dated note.
- **The frozen heuristic is not extended** (C21). The stanza now mentions CompCor and ICA-FIX; the
  heuristic's tool-token list does not contain them, and it is not being changed after seeing
  output. Declared consequence: a `value` of `CompCor` or `ICA-FIX` would land **row 3 `undecided`**,
  not row 2, and be adjudicated by hand. `ICA-AROMA` is in the token list and stays row 2.

**derosa_2025 is now FITTED, not independent.** Correction 4 (2026-10-21) removed derosa's own case
from STEP 3 because naming a probe paper's case in the stanza makes that paper's result circular. This
iteration re-admits derosa's tool by name, by choice, under the C11 licence. Any derosa count under
`378a294f…` is a count on a paper the stanza was edited to handle, and is reported in those words.

**Pre-declared derosa outcomes under the new stanza:**

| raw value | row | outcome |
|---|---|---|
| `motion correction` (the paper's phrase) | 1 | **the target**, reading 4 |
| `motion correction via ICA-AROMA` | 3 | `undecided` — the heuristic's own named halt case (`:110-111`); adjudicate, count |
| `ICA-AROMA` | 2 | reading 2 — **the iteration did not take** |
| `FSL` | 2 | reading 1 |
| an operation phrase with a §2.4.3 / §2.4.9 span | 1 | reading 3 — CONSUME leak, caught only by `span_role` |
| `deferred` | 4 | error, Amendment 2 ruling 3 |
| `missing` | 6 | named line; derosa is not in the power/binder trigger set |

### 3. The second proposed iteration is HELD, and the conflict is reported, not resolved

The author proposed a second line for the deferral arm, to be checked against CALL 6, CALL 7 and
CALL 2a before writing, with any conflict reported instead of resolved. Quoted as given:

> Deferral: a paper that only names the operation under a cited pipeline defers; one that describes
> how the method works in its own words (algorithm, transform type, reference) does not. poldrack
> (deferred) and liu_2013 (described_only) mark the line.

**CALL 6 — no conflict.** CALL 6 governs bullets 2–7 under a wholesale deferral. Its method-row
instance (braun: "preprocessed according to standard protocols as previously described in refs. 47
and 48") describes nothing, so both CALL 6 and the proposed line defer it.

**CALL 2a — consistent, with one caveat.** CALL 2a's test — *does the paper's own text identify the
method, or must the citation be read to know what was done?* — and its two poles (oconnor's operation
name plus a pointer → `deferred`; binder's characterised algorithm → `described_only`) are the proposed
line's own shape. The caveat: CALL 2a also places a *bare* operation name in `described_only` ("from
cole's bare 'motion correction' to binder's characterised algorithm"). The proposed line agrees only
because no cited pipeline stands behind cole's phrase; the qualifier "under a cited pipeline" is
carrying the distinction.

**CALL 7 — CONFLICT.** CALL 7's test is what the citation *does*: substitute for the row's description
→ `deferred`; support a description that is present → not a deferral. Its agtzidis worked case makes
**enumeration** sufficient for "support": *"the citation supports an enumerated pipeline, so
`named_tool` stands. Had the paper **not enumerated**, the same phrasing would substitute."*
poldrack_2015 cites and then enumerates in its own voice — *"All fMRI data were preprocessed according
to a pipeline developed at Washington University, St Louis45. Data were realigned to correct for head
motion and normalized to a mode of 1,000 …"* — so under CALL 7 as worded, ref 45 **supports** and the
motion row is **not deferred**. That is exactly what the 2026-10-21 stanza returned on poldrack: its
deferral arm was written to CALL 7 (correction 5), and it produced row 1 on 10 of 10 draws. The
committed label is `deferred`, reached through CALL 10 ("APPLY → `deferred`, blank; ESTIMATE deferred
to ref 45"). The proposed line sides with the label by adding a criterion CALL 7 does not contain —
under a cited pipeline, a bare operation name is not a description — which narrows the reach of CALL
7's own enumeration example. That is a protocol question (CALL 7 versus CALL 10 on poldrack), and it
is not settled by editing the stanza.

**The two anchors are not separated by the axis the line names.** The line's axis is whether the paper
"describes how the method works (algorithm, transform type, reference)". In the methods text as the
probe loads it:

| paper | the clause | algorithm | transform type | reference volume | cited pipeline over it |
|---|---|---|---|---|---|
| poldrack_2015 | "realigned to correct for head motion" | no | no | no | "according to a pipeline developed at Washington University, St Louis45" |
| liu_2013 | "image coregistration to correct for head motion" | no | no | no | "FCP analysis scripts (version 1.1-beta, …) (Biswal et al., 2010), which employs AFNI (Cox, 1996) and FSL (Smith et al., 2004) … were used to pre-process the fMRI signals (with minor modifications, described below)" |

Both are an operation name plus its purpose, under a cited pipeline. Applied literally the line defers
both or neither; it cannot put poldrack on one side and liu_2013 on the other. What does differ in the
two texts is the **form of the citing sentence** — poldrack's "preprocessed *according to* a pipeline
… 45" against liu's "scripts … *were used* … with minor modifications, *described below*" — which is a
CALL 7 what-the-citation-does distinction, not a how-it-works distinction. Noted alongside, because it
bears on the same anchor: CALL 1 v1.1's wrapper rule (oconnor's C-PAC, tool unnamed → `deferred`)
would read liu_2013's FCP scripts the same way, against the committed `described_only`. These are
observations about the protocol and its labels, reported for the author's ruling.

**Consequence for the re-run.** The deferral arm runs as it stood at `56bc6305…`, i.e. to CALL 7.
poldrack_2015 is read against its committed label (`deferred`) and its APPLY criterion. A row-1 result
is a **pre-declared mismatch with the label that CALL 7's wording predicts**; a row-4 result matches
the label; `applywarp` fails the control. poldrack's draws are not independent either way — its
passage is one of CALL 10's seven fitting passages and STEP 2's APPLY arm was written from it. **If the
author rules the deferral line in**, poldrack becomes fitted a second time, by the stanza edit, and its
results after that edit are reported as fitted, not independent, in the same words used for derosa
above.

### 4. The re-run, and what each paper is read against

Seven papers at **K = 10** under stanza `378a294f…`, same model, `temperature=0.0`, `max_retries=2`.
**A new vintage**: never pooled with the 2026-10-21 draws, reported in
`docs/findings/motion-probe-v2-results.md` and backed by `ground_truth/motion_probe_v2_projection.csv`
(status, heuristic class, row, span offsets; **no quote or value text**). Counts only; no rate.

| paper | label read against | expected under this stanza | what counts as a mismatch |
|---|---|---|---|
| power_2014 | `described_only` | row 1 | `missing` fires ruling 1's trigger; row 2 or 4 is an error |
| binder_1999 | `described_only` | row 3 (declared limitation) or row 1 if the value carries `coregist…` | ruling 3's table |
| liu_2013 | `described_only` | row 1 | row 2 (a tool from "employs AFNI and FSL" or `align_epi_anat`) or row 4 |
| derosa_2025 | `described_only` | row 1, value the paper's phrase | §2's table |
| agtzidis_2020 | `described_only` — **the author's 2026-10-22 relabel**, in the workbook working copy and uncommitted at the time of writing (protocol v1.6, Amendment 3) | row 1; span failures on the long quote are expected and are the recorded `/C2` exclusion, not a stanza fact | `SPM12` is row 2, the mismatch |
| poldrack_2015 | `deferred`; APPLY control | row 1 (CALL 7's wording) or row 4 (the label) — both pre-declared, §3 | `applywarp` fails the control; row 1 is a label mismatch recorded as such |
| ciric_2017 | `named_tool` / MCFLIRT — **post hoc control** | row 2 with the ESTIMATE span | §1's table |

Rows are computed from raw `status` and raw `value` only (Amendment 2 ruling 2), so span failures do
not move a row; they are reported as their own line per paper.

### 5. Unchanged

Amendment 2's five rulings in full — ruling 1's number is still 20 (power + binder); ruling 2's
three-way split of a `None` verbatim; ruling 3's declared outcomes; ruling 4's threshold of 6 of 10;
ruling 5's heuristic, not extended. Amendment 3's retirement of the agtzidis criterion. The probe
tests reachability, not accuracy; **no accuracy figure may be computed from or cited out of this
run**; the iteration licence covers the seven contaminated probe papers and does not extend to
liu_2005, tang_2025 or wheaton_2004.

---

## Amendment 5 (2026-10-25) — same-day control: did the stanza move agtzidis and binder, or did the day?

**Written BEFORE the run it governs, on the day of that run.** Between the 2026-10-21 run (stanza
`56bc6305…`) and the 2026-10-22 run (stanza `378a294f…`) two papers moved, and two things changed
between those runs — the stanza and the day. The project has measured day-to-day movement at
`temperature=0.0` before (the temporal finding's fixed→fixed 4/10 → 0/10), so neither cause can be
read off the two runs. This amendment pre-registers the one experiment that separates them.

### What moved, and the shared shape the author identified

| paper | 2026-10-21 under `56bc` (v1) | 2026-10-22 under `378a` (v2) |
|---|---|---|
| agtzidis_2020 | operation phrase (row 1) on 9, `SPM12` (row 2) on 1; spans resolved 3 of 10 | `SPM12` (row 2) on 10; spans resolved 9 of 10 |
| binder_1999 | the algorithm description, `undecided` (row 3) on 10 | `AFNI`/`MCW-AFNI` (row 2) on 5, `undecided` on 3, operation phrase (row 1) on 2 |

The author matched the v2 projection's offsets back to both texts: on every resolved agtzidis draw
the quote is the realignment clause (7188–7308, the span v1 quoted for its operation phrases) and
`SPM12` is two sentences away; on every binder draw the quote is the Cox 1996b sentence (11023–11180)
and `AFNI` occurs only in the Talairach sentence. **Both papers moved toward naming a tool that is not
in the quoted sentence.** The other four v1 papers (power, liu_2013, derosa, poldrack) gave the same
answer type on all 40 draws across the two runs — derosa among them, the paper the edit was for. That
pattern points at the edit, and only a same-day control can rule the day out.

### Design

- **Arms.** Two stanzas: `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a` and
  `378a294f94ca9f0fc6bd45bd42caf4646a007c7d705d05c8b5f584dd66ca8cab`. Two papers: agtzidis_2020,
  binder_1999. **K = 10** per stanza per paper — **40 calls**, run back to back in one session on
  2026-10-25, the `56bc` arm first (agtzidis, binder), then the `378a` arm (agtzidis, binder). Same
  model id, `temperature=0.0`, `max_retries=2`.
- **The `56bc` arm runs from a git worktree at `3fc366f`**, the last commit at which the pin reads
  `56bc6305…` (the stanza iteration is not yet committed as this is written; `3fc366f` is HEAD, and
  its `extractor.py` blob hashes to `56bc6305…` when evaluated). That arm uses the recorder and the
  extractor module **as of that commit**; the `378a` arm uses the working tree's. The recorder inserts
  its own `../src` at the head of `sys.path`, which is what makes the two arms import different
  modules from one interpreter. Checked before writing this: the worktree path imports a module whose
  stanza hashes to `56bc…`, the working-tree path one that hashes to `378a…`.
- **Gate, applied before any per-draw record is read:** each arm's `manifest.json` must carry its own
  hash in `motion_method_prompt_sha256`. An arm whose manifest carries the other hash is **void** and
  is re-run after the import path is fixed — a wrong path would run `378a` twice and manufacture a
  "day effect". No draw from a void arm is reported.
- **Projection and results doc as for v2.** Two projections (one per arm), no quote or value text;
  one results document. Counts only; no rate.

### Pre-declared readings

Compared per paper, on the heuristic class of the raw value (state-map row), against the earlier run
under the same stanza and against the other arm. "Reproduces" means the modal row is the same as the
earlier run's modal row for that paper; the count of the modal row is reported beside it, and no
threshold is set on it — K=10 is too few for one, and no rate may be computed in any case.

1. **Stanza effect:** each arm reproduces its own earlier run — `56bc` gives agtzidis mostly row 1 and
   binder mostly row 3; `378a` gives agtzidis mostly row 2 and binder a row-2-led mix — **and** the two
   arms differ from each other on that paper.
2. **Day effect:** the two arms give the same modal row as each other on that paper, whichever row it
   is. (Then at least one arm departs from its own earlier run, and the departure is the day's.)
3. **Anything else** — the two papers splitting (one reads as 1, the other as 2); an arm reproducing
   neither its earlier run nor the other arm; a row neither earlier run produced — is **reported as
   found**, not classified into 1 or 2.

Span offsets are reported beside the rows, because the author's finding is about the quote staying
put while the value moves: whether each arm quotes the same clause as its earlier run is part of what
"reproduces" means here, and is stated separately from the row.

### Unchanged

Labels as Amendment 4 reads them. No stanza edit and no label change accompany this run. agtzidis and
binder are probe papers already inside the contaminated union; this spends no clean cell. The
held-out three are not touched. No accuracy figure may be computed from or cited out of this run.

---

## Amendment 6 (2026-10-26) — the replacement control under the restored stanza

**Written BEFORE the run it governs.** Amendment 5's same-day control attributed the agtzidis and binder
movement to the 2026-10-22 stanza edit, and the edit had fixed nothing it was made for (derosa:
`ICA-AROMA` on all 20 draws across both stanzas). The author therefore ruled on 2026-10-26 that the
stanza is **reverted to `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a`** — a version
already measured on six papers, so no new vintage is created by the revert. One gap remains: ciric_2017,
the post hoc replacement control, has run only under `378a294f…` (Amendment 4; v2: `MCFLIRT` on 10 of
10 with the ESTIMATE span). It does not count as a control for the restored stanza until it has run
under it.

### Design

- ciric_2017, **K = 10**, under `56bc6305…`, from the working tree **after** the revert commit; same
  model, `temperature=0.0`, `max_retries=2`. Ten calls.
- **Gate, before any per-draw record is read:** the run's `manifest.json` carries `56bc6305…` in
  `motion_method_prompt_sha256`. A manifest carrying any other hash voids the run.
- Projection and results document as for v2: `ground_truth/motion_probe_ciric_2026-10-26_56bc_projection.csv`
  (no quote or value text) and `docs/findings/motion-probe-ciric-56bc.md`. Counts only; no rate.

### Pre-declared reading

**The control passes if every one of the 10 draws returns `MCFLIRT` with the ESTIMATE span, as under
`378a`.** "The ESTIMATE span" is a resolved span that contains the ESTIMATE mention of MCFLIRT (offset
4475–4482 of the methods slice as the probe loads it; the v2 span was 4410–4507) and none of the three
CONSUME mentions (5533, 6360, 9296). **Anything else is reported as found** — a CONSUME span, an operation
phrase, a deferral to Jenkinson 2002, another tool, `missing`, a both-lists `undecided`, or an unresolved
quote — as its own named line, against Amendment 4 §1's table, and not classified into pass.

### Unchanged

ciric_2017 is post hoc and already contaminated (Amendment 4 §1); every report of its count says so in
the same sentence. Labels unchanged. The held-out three untouched. No accuracy figure.

---

## Amendment 7 (2026-10-26) — version 3 of the stanza: rule A and option (c), one new vintage

**Written BEFORE any draw under this version. The run has not happened; the stanza is on review.**
Ruled by the author on 2026-10-26: the deferral rule (A) and the model-emitted binding (option (c) of
Amendment 1) are adopted together, so one new prompt version carries both rather than two.

### What changed

- **Protocol v1.7, CALL 11** (`docs/ground-truth-protocol-motion_correction.md`): with no bound ESTIMATE
  tool, a paper that names the operation under a cited pipeline or method and states none of the
  algorithm, transform type, reference image or cost function **defers** to that citation; stating any
  one of the four makes it `described_only`, whatever it cites; citing nothing and binding no tool is
  `described_only` on the paper's own assertion. CALL 7's enumeration criterion is narrowed; CALL 10's
  liu_2013 row is superseded.
- **Stanza version 3**, sha256 `ea7b0084255454fd38a6de566a5cccf2936b67b09910f6ffa15a79d01c5734a7`
  (5,369 characters), written from v1.7 and not from any paper's text. Superseded: `56bc6305…`, which
  stays on the 2026-10-21 run, the A/B's `56bc` arm and the ciric control; `378a294f…` stays on the
  2026-10-22 run and the A/B's `378a` arm. STEP 4 carries CALL 11 as ordered steps; STEP 5 sets the new
  field. Pinned (`extractor_mvp/tests/test_prompt_pin.py`) with a dated note.
- **Option (c):** `MotionMethodExtraction.motion_correction_binding ∈ {named_tool, described_only}`,
  set only when `status == "extracted"` and then always; `deferred` and `missing` keep the existing
  status path. A validator enforces both directions, so a missing or stray binding is a reask the
  recorder counts (`completion_attempts`), never a silent default.
- **The frozen heuristic keeps running as the independent control.** The recorder stores the model's
  binding as `raw_binding`; the projection carries `model_state` beside `heuristic_class` and
  `model_vs_heuristic ∈ {agree, disagree, undecided}`; **disagreements are counted and listed by draw**.
- **Amendment 2 ruling 4 is superseded.** Its trigger (`undecided` ≥ 6 of 10 on a `described_only`
  paper) measured whether the heuristic alone was adequate; with (c) adopted, the heuristic's
  `undecided` count is reported as a named line and compared with the model's binding, and it no
  longer gates anything.
- **Unchanged and in force on the processed layer:** the value-in-quote post-check and the
  structured-noise routing (`motion_guard.py`); the span resolver at `3cb396e`.

### Pre-declared readings — K = 10, seven papers, 70 draws

| paper | label read against | pre-declared |
|---|---|---|
| power_2014 | `described_only` | `described_only` ×10 (model binding and heuristic class agree) |
| liu_2013 | **both**: `described_only` at HEAD; `deferred` pending the author's relabel under CALL 11 | **`deferred`, target = the FCP citation** (Biswal 2010 / the scripts). Reported against both labels |
| poldrack_2015 | `deferred` | **`deferred`, target = ref 45** — the first test of whether `deferred` is reachable at all: 0 of 180 draws have returned it |
| agtzidis_2020 | `described_only` (relabel of 2026-10-22) | `described_only`, value = the paper's phrase. **Any `SPM12` is a check failure**: the quoted clause does not contain it, so the post-check demotes it (`motion_value_unsupported_by_quote`), and it is counted as such |
| binder_1999 | `described_only` | `described_only` (the algorithm). The heuristic's `undecided` count is reported beside the model's binding |
| derosa_2025 | `described_only` — **fitted** | the check routes `ICA-AROMA` off the method whatever the model says; model state and value reported as found |
| ciric_2017 | `named_tool` / MCFLIRT — post hoc control | `named_tool`, `MCFLIRT` ×10, with the ESTIMATE span |

**Anything else is reported as found**, as its own named line — a deferral whose target is not the one
named, a binding that disagrees with the heuristic, a reask, an unresolved span. **No rates.** Rows,
bindings and classes are computed from the raw layer; the post-check's demotions are reported on the
processed layer beside them, never folded in.

### One risk, pre-declared before the first call (2026-10-26, the author's)

poldrack_2015's methods slice contains, immediately after the realignment sentence the earlier runs
quoted (span 25523–25671), a sentence that registers each session to a single reference session —
a link in the paper's session-to-atlas registration chain, not the realignment. It is EPI-to-EPI, so
STEP 1 keeps it, and it names a reference. STEP 4's detail (c), the reference image, may read it as a
stated reference image and return `described_only` on that sentence instead of `deferred`. The label
keeps poldrack on the deferred side because that reference belongs to the atlas chain, not to the
motion estimate. **If poldrack returns `described_only` on that sentence, the reading is fixed now:
detail (c) needs a within-run / within-session scope, and the next iteration adds it.** It is not
fixed before the run, which would fit the stanza to poldrack before seeing the data.

### A limitation logged, not fixed

STEP 1 folds "the step is stated as NOT performed" into `status="missing"`. COBIDAS counts a stated
negative as a report, so this under-credits a paper that says it skipped the step. The label
vocabulary has `stated_not_performed` (protocol §3); the raw status does not, and Amendment 1's state
map already records the state as unreachable-but-unexercised. No corpus paper carries it.

### Unchanged

The probe tests reachability, not accuracy; no accuracy figure may be computed from or cited out of it.
The seven papers are contaminated (derosa and poldrack fitted; ciric post hoc); liu_2005, tang_2025 and
wheaton_2004 are not touched. The vocabulary of the heuristic is not extended. The run follows the
author's review of the stanza, which was given on 2026-10-26; the run precedes this amendment's commit
only because commits are blocked until 17:00, and the manifest's timestamp orders the two.

---

## Amendment 8 (2026-10-26) — three deferral shapes join the probe; version 4 pre-declared

**Written BEFORE any edit to the stanza and before any call.** Ruled by the author on 2026-10-26 after
the version-3 run and the label pass over the deferred rows (protocol v1.7.1).

### Why the probe set grows

The version-3 run reached `deferred` on liu_2013 (10 of 10) and not on poldrack, and the author's pass
over the seven `deferred` rows found three citation shapes the stanza does not reach: a **bare numbered
citation** beside the operation (poldrack, already in the probe); a **wholesale deferral with no
operation named** (braun, viduarre — STEP 1 keeps no passage and returns `missing` by construction, CALL
6's case); and a **named but uncited pipeline** (vanderwal). Leaving the three papers out would make the
full-corpus run show two or three `deferred` mismatches by construction — a known stanza gap presented as
a result. So braun_2015, viduarre_2017 and vanderwal_2016 **join the probe set**, and the stanza is
iterated once with three general instructions, none naming a paper.

### Contamination status, from the record

All three carry the `co-adjudicated` flag in the workbook (protocol §7, v1.7.1: the 14 flagged include
braun_2015, vanderwal_2016 and viduarre_2017), and none is in CALL 10's seven fitting passages. They are
therefore already inside the contaminated union of **16 of 19**, which does not change; the clean three —
liu_2005, tang_2025, wheaton_2004 — are **unchanged** and are not touched. What changes is that the
stanza becomes fitted to three more of the sixteen it was already fitted to, and that is stated here and
wherever their counts are reported: **braun, viduarre and vanderwal are fitted, not independent**, from
this version on, as derosa and poldrack already are.

Their committed labels, read from the workbook (states and values only): braun_2015 `deferred`, value
blank; viduarre_2017 `deferred`, value blank; vanderwal_2016 `deferred`, value `CPAC`.

### Version 4 — three edits, general, written from CALL 6 and CALL 11

a. **Citation forms.** A citation may appear as author-year, as a bare number attached to a word in the
   text layer (the PDF layer writes "as described previously12"), or as a named pipeline. A named
   pipeline is a deferral target with or without a reference beside it (`target_kind = "pipeline"`).
b. **Wholesale deferral (CALL 6).** When STEP 1 keeps no passage but the text defers its preprocessing
   as a whole to a citation or a named pipeline, the output is `status="deferred"` with that target, not
   `"missing"`. Kept passages take precedence; this applies only when none is kept.
c. **STEP 4's trigger** reads: under a cited pipeline, a cited method, a cited paper, or a named pipeline.

The new hash is pinned in `extractor_mvp/tests/test_prompt_pin.py` with a dated note retaining
`ea7b0084…`, and the recorder writes it into every manifest. **Regression stays on all ten papers**:
the 2026-10-22 edit moved papers it was not aimed at, so every paper is re-read, not only the three.

### Pre-declared readings — version 4, K = 10, ten papers, 100 draws

| paper | label | pre-declared |
|---|---|---|
| braun_2015 | `deferred` | `deferred`, target = refs 47 and 48 (CALL 6; no operation named in the text) |
| viduarre_2017 | `deferred` | `deferred`, target = Smith et al. / Glasser et al.; **FIX is not the value** (a structured-noise tool; the check routes it if returned) |
| vanderwal_2016 | `deferred` | `deferred`, target = C-PAC. **Risk:** `ANTs` returned as `named_tool` from the same sentence — the host-sentence limit the value-in-quote check cannot catch (DELTA §4, recorded limit); reported as found if it happens |
| poldrack_2015 | `deferred` | `deferred`, target = the Washington University pipeline (ref 45), through edit (a) |
| power_2014 | `described_only` | unchanged from version 3: `described_only` ×10 |
| agtzidis_2020 | `described_only` | unchanged: `described_only`, the paper's phrase; any `SPM12` is a check failure |
| liu_2013 | `deferred` (v1.7.1) | unchanged: `deferred`, target = the FCP scripts |
| binder_1999 | `described_only` | unchanged: the `AFNI` carry reported as found and demoted by the check |
| derosa_2025 | `described_only` — fitted | unchanged: routed by the check; model state and value reported as found |
| ciric_2017 | `named_tool` / MCFLIRT — post hoc | unchanged: `MCFLIRT` ×10 with the ESTIMATE span |

**Anything else is reported as found**, as its own named line. The model's binding is reported beside
the frozen heuristic's class, disagreements counted (Amendment 7). **No rates.**

### Unchanged

The probe tests reachability, not accuracy, and no accuracy figure may be computed from or cited out of
it. The post-checks run on the processed layer; the raw layer and the state-map rows are computed as
before. The run follows the author's review of version 4; no call is made before it.

---

## Amendment 9 (2026-10-26) — version 5 against version 4, same day, with an adoption rule; then freeze

**Written BEFORE any edit to the stanza and before any call.** Ruled by the author on 2026-10-26 after
the version-4 run (Amendment 8).

### What version 4 settled, and what it left

`deferred` is reachable on the motion row: four papers return it on all ten draws (braun, viduarre,
vanderwal, and liu_2013 on 7 of 10), after 0 of 180 draws before version 3. Edit (a) did not reach
poldrack, so its shape is now exact: **an unnamed pipeline cited by a bare number, in the sentence that
introduces the procedure set, followed by an operation sentence STEP 1 keeps** — the model reads the
operation sentence alone. That shape is the standard numbered-reference form ("were preprocessed as
previously described12, followed by a step list"), and the tool currently credits such a paper with
describing its method when it deferred, which is the wrong direction for a compliance auditor.

### Design — one more iteration, controlled, then freeze

- **Same-day A/B, all ten papers, K = 10 per arm — 200 calls, back to back in one session.** Arm 1:
  version 4, `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837`, run from a git
  worktree at the last commit that pins it (`d1292f6` as this is written) with that commit's recorder.
  Arm 2: version 5, from the working tree. **Each arm's manifest is gated on its own hash before any
  record of either arm is read**; a mismatch voids the arm.
- **Version 5 is one general edit** in STEP 4, from CALL 6 and CALL 11, naming no paper: read each kept
  passage together with the sentence that introduces the procedure set it belongs to; a citation or a
  pipeline in that introducing sentence, named or unnamed, governs the operation sentences that follow
  it until the text begins a new procedure set; the four-detail rule and STEP 3 still decide first — a
  bound tool or any stated detail wins. The nine other papers short-circuit before the edit applies.
- **The `ea7b0084…` arm is not run**: version 3 is superseded, and the question is what version 4
  costs, not why.

### Pre-declared

- **Adoption rule.** Version 5 is adopted if **poldrack returns `deferred` to ref 45 on at least 6 of
  10** and **no other paper loses more than 2 matching draws against its same-day version-4 arm**;
  otherwise version 4 freezes and poldrack's shape is recorded as unreached. "Matching" is against the
  paper's label as Amendment 8 reads it; a draw matches on its state-map row (and, for ciric, its span).
- **liu_2013.** Its version-4 arm today decides whether 7 of 10 was version 4's cost or within-run
  variation at temperature 0: 10 of 10 today means variation; 7 again means version 4's cost, and
  version 5 is judged against that number.
- **All other readings as Amendment 8**, including the vanderwal risk and agtzidis's check-failure rule.
- **Anything else is reported as found.** Model binding against the heuristic reported per arm;
  disagreements counted. **No rates.**

### Then freeze

The adopted version is **the frozen stanza under prereg C11**, with no further iteration before the
full-corpus run. Its hash is the one the full-corpus run's manifest must carry.

### Unchanged

Reachability, not accuracy; no accuracy figure may be computed from or cited out of either arm. The
contaminated union is 16 of 19 (Amendment 8); the clean three are not touched. The run follows the
author's review of version 5; no call is made before it.

## Freeze (2026-10-26, late night) — the adoption rule applied as written; version 4 is the frozen stanza

> **Lifted and moved (Amendment 10, 2026-10-26, late night).** The freeze below stands as the record of
> how version 4 was adopted. It is lifted once, for a **definitional change, not tuning** — protocol
> v1.8 gives `named_tool` an attribution level that version 4 cannot express — and re-applied to
> version 6 on adoption under Amendment 10's rule. Nothing in this section is tuned by that.

**Written AFTER the same-day A/B, from records read only after each arm's manifest passed its gate.**
Counts of draws; no rate. The run is reported in
[motion-probe-v5-ab-results.md](motion-probe-v5-ab-results.md).

- **Gates.** Version-4 arm (worktree at `d1292f6`, that commit's recorder): manifest
  `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837`, 6,402 characters. Version-5
  arm (working tree at `2f0fe2e`): `fb5735fba39457a0f67aebe95fa4668f1df7ae55568f3ad86d1274563863e6d2`,
  6,809 characters. Both checked before any record of either arm was read. Neither arm void.
  23:15:50–23:29:33 and 23:29:33–23:41:25 UTC, back to back.
- **Clause 1 not met.** poldrack returned `deferred` to ref 45 on **3 of 10** under version 5
  (`described_only` on the realignment sentence, 25523–25671, on the other 7). The rule requires at
  least 6.
- **Clause 2 not breached, reported because the rule names it.** Matching draws by state-map row,
  version-4 arm today → version-5 arm: liu_2013 5 → 10; poldrack 0 → 3; binder_1999 6 → 8 by row
  (4 heuristic-`undecided` draws today, 0 under version 5), and 10 → 8 by the model's own state,
  because 2 version-5 draws ended in error at the binding validator after reask; every other paper
  10 → 10. No paper lost more than 2 on either reading.
- **Outcome, as written: version 4 freezes.** The rule is a conjunction; the second clause does not
  rescue the first.
- **liu_2013's pre-declared reading.** Version 4 today: `deferred` **5 of 10**, `described_only` on
  the operation sentence 5 — neither of the two branches written above (10 means variation; 7 again
  means version 4's cost). A second day gives a second count below 10, so the loss recurs under
  version 4 and is **recorded as the frozen version's cost**, not as within-run variation. Version 5
  returned `deferred` 10 of 10 on this paper; that is on the record and does not change the outcome.

### The frozen stanza

- **Hash:** `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837` (version 4; 6,402
  characters). The five version-5 lines were removed from STEP 4 and the constant is version 4
  **verbatim** (its diff against `d1292f6` is comment lines only; the live hash was checked after the
  edit). Version 5's hash stays on its arm's records and projection only and is never pooled.
- **Three guards, one value.** `extractor_mvp/tests/test_prompt_pin.py` pins the hash with a dated
  note. `extractor_mvp/scripts/motion_probe.py` carries it as `_FROZEN_STANZA_SHA256` and **refuses
  to draw under any other stanza** before building a client; its manifest now also writes
  `motion_method_prompt_frozen_sha256`. `extractor_mvp/tests/test_motion_probe_freeze.py` holds the
  three values equal and the refusal live (positive control: a hash one character off is refused;
  the held-out refusal still precedes any client).
- **Rule under C11 from this note on:** no stanza change without a new amendment that names the new
  frozen hash in the recorder, in the same commit as the edit. The full-corpus run's manifest must
  carry `b0093774…`.

### Unreached, and recorded

- **poldrack's shape remains unreached under the frozen stanza:** an unnamed pipeline cited by a
  bare number in the sentence that introduces the procedure set, followed by an operation sentence
  STEP 1 keeps. 0 of 10 under version 4 on both days it ran; 3 of 10 under version 5's
  introducing-sentence rule, which is on the record as the first draws ever to defer this paper and
  was not adopted.
- **liu_2013's loss is a cost, not a shape:** its shape (a named, versioned pipeline cited beside an
  operation sentence) is reached, on 7 of 10 and then 5 of 10 under the frozen stanza.
- **binder_1999 under version 5** lost 2 draws to the response schema, not to the text: the model
  returned `status="extracted"` without `motion_correction_binding` on 7 of 10 first attempts, and 2
  draws did not recover on reask. 0 reasks under version 4 today. Recorded; version 5 is not adopted
  for other reasons.
- No other shape from the label pass remains: braun, viduarre and vanderwal deferred on 10 of 10 in
  both arms.

### Unchanged

Reachability, not accuracy. The contaminated union is 16 of 19; the clean three were not loaded,
searched or read. The full-corpus run — 19 papers under `b0093774…`, the held-out three entering for
the first time — is the next design question and is not pre-registered here.

## Amendment 10 (2026-10-26, late night) — the freeze lifted for a definitional change; version 6; the 13-paper probe set; adoption rule

**Written BEFORE any call under version 6, after the stanza edit was drafted from the protocol's text
and before it ran.** Ruled by the author on 2026-10-26; drafted by Claude Code from the author's
rulings; ratified by commit.

### Why the freeze is lifted, and why this is not tuning

Protocol **v1.8** amends CALL 1: `named_tool` carries an attribution level, `step` (the v1.5 binding
test) or `package` (exactly one package from a closed realignment-capable list named for the
preprocessing or analysis as a whole, no step-level tool, the motion step asserted). This changes the
**label vocabulary**. A stanza that cannot express the vocabulary the labels are written in measures
nothing about those labels: the four papers the v1.8 worked cases move or settle (agtzidis, derosa,
cole, mueller) would be scored against a state the frozen stanza has no way to return. The freeze was
pre-declared to end iteration on wording; it was not pre-declared to bind the stanza to a superseded
definition. So the freeze is **lifted once, for this definitional change only**, and re-applied to
version 6 under the rule below. Every place the freeze is cited carries a dated note saying so.

### Version 6

- **Two edits, both from the protocol's text, no other change from `b0093774…`:** STEP 3 gains the
  package rule after NOT BOUND — the list verbatim (AFNI (3dvolreg), FSL (MCFLIRT), SPM any version
  (Realign), ANTs (antsMotionCorr), BrainVoyager; FreeSurfer not on it), the unlisted-package
  instruction (not attributed, continue to STEP 4), the two-or-more rule, the pipeline/wrapper rule;
  STEP 5 gains the output rules for both levels. **A package-level draw quotes the sentence that
  names the package** (the value must appear in it), so the value-in-quote check holds on it, and its
  span is the package sentence, not the realignment sentence — consistent with `span_role` being
  evaluated for ciric only.
- **Response model:** `motion_correction_binding` ∈ {`named_tool_step`, `named_tool_package`,
  `described_only`}; the validator is unchanged in shape. The projection folds both `named_tool_*`
  values to `named_tool` for the state comparison with the frozen heuristic and carries the level in
  a new column, `model_attribution`, emitted only for version-6 records; every earlier projection
  regenerates byte-for-byte.
- **Hash:** `8df070da9cc3f9628d6670c7285740155b05a06dd25972849f0711b056c8ef4f` (7,934 characters). Pinned with a dated
  note retaining `b0093774…`; `_FROZEN_STANZA_SHA256` moved to it in the same commit.
- **The frozen heuristic is not extended (C21).** It classes `ANTs` and `BrainVoyager` as `undecided`
  (not tool-shaped in its frozen vocabulary): a draw returning either lands on row 3 — halt, count,
  never default. Recorded as a known gap, not amended; no probe paper is expected to return either.

### The probe set: 13 papers

cole_2013, gordon_2014 and mueller_2021 join the ten of Amendments 4 and 8. All three are inside the
contaminated union (cole and gordon in CALL 10's derivation set; mueller co-adjudicated), and the v1.8
worked cases for cole and gordon were proposed with LLM assistance and ratified by the author, so both
carry the `co-adjudicated` flag once the workbook is edited: the co-adjudicated list becomes 16, the
union stays **16 of 19**, the clean three are **unchanged** and are not in the probe set. The recorder's
default `--papers` is this set (`_PROBE_SET`); the held-out guard is unchanged. **K = 10, 130 draws,
one session; the manifest gated on version 6's hash before any record is read.** All 13 are fitted
by construction: the stanza's package rule is the protocol's, and the protocol's worked cases name
them.

### Pre-declared readings — version 6, K = 10

"Label" is the v1.8 label; the workbook edits for agtzidis, derosa, cole, gordon and mueller follow the
protocol commit and precede the run. "Row" is the state-map row from the raw layer; "level" is the
model's `motion_correction_binding`. The version-4 count is the matching-draw count by row on the
2026-10-26 same-day A/B's version-4 arm (`motion_probe_ab_2026-10-26_b009_projection.csv`).

| paper | v1.8 label | pre-declared under v6 | v4 count | clause |
|---|---|---|---|---|
| agtzidis_2020 | `named_tool` / `package` / SPM12 | row 2, value `SPM12`, level `package`; the quote moves to the package sentence, which may resolve where the realignment sentence (`/C2`) did not — reported | 10 under the old label | 1 |
| cole_2013 | `named_tool` / `package` / AFNI | row 2, value `AFNI`, level `package`. The text layer attaches the citation number to the package name (the protocol's `AFNI48` note); under the matcher's ruling 6 (2026-10-26, before commit) a letter-ending value is supported by such a quote, so the draw is **not** demoted — a demoted cole would have been wrong, and the replay over every recorded draw moved nothing else | — | 1 |
| mueller_2021 | `named_tool` / `package` / SPM12 | row 2, value `SPM12`, level `package`. Risk: the paper's earlier deferral of its preprocessing to a prior paper read as STEP 4 — a `deferred` draw is the mismatch to name | — | 1 |
| derosa_2025 | `named_tool` / `package` / FSL, ICA-AROMA routed | row 2, value `FSL`, level `package`, quote = the FSL sentence. A draw returning `ICA-AROMA` is routed by the check as before and is **not** the level: reported as found | 10 routed under the old label | 1 |
| gordon_2014 | `named_tool` / `step` / SPM8 | row 2, value `SPM8`, level `step`; CALL 10's attractors (MATLAB = HOST, RMS = CONSUME) are the mismatches to name | — | 1 |
| ciric_2017 | `named_tool` / `step` / MCFLIRT (post hoc) | row 2, `MCFLIRT`, level `step`, span 4410–4507 | 10 (reported, not a clause-2 count) | 1 |
| power_2014 | `described_only` — **confirmed by the author from the text** (no listed package named anywhere; one MATLAB mention, in a figure caption) | row 1 ×10 at 3112–3528, level `described_only`; a package-level return would be an over-reach, recorded | 10 | 2 |
| binder_1999 | `described_only` — **confirmed by the author from the text**: MCW-AFNI is named once, for projecting anatomical scans and statistical maps into Talairach space, a different step, so the "for its preprocessing as a whole" condition fails | row 1 on most draws, row 3 on some (excluded by name), level `described_only`; **a `named_tool`/`package`/AFNI return is an over-reach of that condition, recorded as such** | 6 by row | 2 |
| liu_2013 | `deferred` (two listed packages under the scripts → not attributable) | row 4 to the scripts, target kind `pipeline`, on 5 to 10 of 10 (the recorded cost); below 5 is a new finding | 5 (7 on the earlier v4 run; both reported) | 2 |
| poldrack_2015 | `deferred` | row 1 ×10 at 25523–25671 (the unreached shape; the pipeline is unnamed, so the package rule does not apply) | 0 | 2 (cannot lose) |
| braun_2015 | `deferred` | row 4 ×10, target kind `paper` | 10 | 2 |
| viduarre_2017 | `deferred` | row 4 ×10 to one of the two pre-declared citations | 10 | 2 |
| vanderwal_2016 | `deferred` (C-PAC is a wrapper) | row 4 ×10, target kind `pipeline`; `ANTs` host-sentence risk unchanged, and an `ANTs` value would land on row 3 (above) | 10 | 2 |

**power_2014 and binder_1999, confirmed.** Both were checked by the author from their text, not the
model's output, before this commit: power names no listed package anywhere; binder names MCW-AFNI once
for a different step. Both stay `described_only`, and the over-reach readings in the table are
pre-declared so that neither is written after a value is seen.

### Adoption rule

**Version 6 freezes if every `named_tool` paper** — agtzidis, cole, mueller, derosa at the `package`
level; gordon and ciric at the `step` level (clause 1 covers every `named_tool` paper, the author's
adjustment of 2026-10-26; neither gordon nor ciric has a clause-2 count) — **returns its level on at
least 8 of 10** — level means the raw `motion_correction_binding` equal to the label's level with the
raw value on row 2 — **and no other paper loses more than 2 matching draws against its version-4
count** (power, binder, liu_2013, poldrack, braun, viduarre, vanderwal, by state-map row; liu_2013
against 5, with 7 reported beside it). **Otherwise: report and stop.** The value match (normalized exact
equality, the author's scoring ruling of 2026-10-26) and the level are reported per paper as separate
counts and do not enter the rule beyond the level clause.

**Pre-declared limitation.** There is no same-day version-4 arm this time; the comparison crosses
days, and liu_2013's 7 → 5 across two days is the measured size of that movement. A loss within that
range is reported as a loss under the rule as written and is not attributed to version 6 alone.

### Precondition carried from `DESIGN_motion_full_corpus.md` §5.0

The cole, gordon and mueller label check is settled by v1.8's worked cases, pending the workbook
edits. The held-out three's v1.8 check, by the author alone, is a precondition of the **full-corpus**
run, not of this 13-paper probe, which does not touch them.

### Unchanged

Reachability, not accuracy; no accuracy figure may be computed from or cited out of this run. Counts
only, no rates. The clean three are not loaded, searched or read. The run follows the protocol commit
and the workbook edits; no call is made before them.
