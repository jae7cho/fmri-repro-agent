# DELTA — extending the value-in-quote check to the seven `_FIELD_SPECS` fields

*Design only. **No code is changed and this file is not staged.** Drafted 2026-10-26 against HEAD
`f0aba38`; every locator verified against the working tree; every count produced by a command over
the stored results, with no model calls. No quote text from any paper appears here. The three
held-out papers (liu_2005, tang_2025, wheaton_2004 — prereg C11/C26) are counted and never listed.*

---

## 0. What this follows

The motion post-check (`motion_guard.py`, commit `0621d71`) checks one field. The 2026-10-26 survey
(`docs/findings/value-support-survey-step-fields.md`) found one stored step-field value absent from its
own quote — liu_2013's `temporal_standardization.method` — and the author's reading was that this
cannot be accepted as a demotion: liu_2013 is that field's positive case, fixed in the design, and a
miss on it is the failure the design calls the worse one. The question this DELTA sets up is what
"supported by its quote" should mean for a field whose value is a canonical token that never appears
in prose.

## 1. Facts

### 1a. liu_2013's temporal method: the quote, the value, and the design's positive case

From `extractor_mvp/results/batch_a1_acceptance/papers/liu_2013.json` (not held out):

| | |
|---|---|
| extraction status | `EXTRACTED`, `span_recovered = False` |
| span | **4733–4884** of liu_2013's methods slice (section `None`) |
| raw value returned by the model (`resolutions` record) | `voxel_temporal_zscore` — the canonical token, `matched_alias = None` |
| SpecifiedTerm | `verbatim = voxel_temporal_zscore`, `resolved = voxel_temporal_zscore`, `resolution = resolved` |

**It is the positive-case sentence.** `DESIGN_temporal_standardization_build2.md:50-51` names the
positive set as Liu 2013, quoting the clause about each voxel's signal being temporally normalised
by subtracting its mean and dividing by its temporal SD; the stored span is the full sentence that
clause sits in (it opens with "Finally, for each voxel" and closes with the parenthesised "(SD)"),
and `normalize_with_offset_map` repairs the line-break hyphenation inside it (checked: the token
`normalized` is present after normalisation). `DESIGN_temporal_standardization_build3.md:134` says of
a positive-set paper failing to populate: *"this is the WORSE failure"*. So the survey's one `absent`
is the one cell the design singles out as must-not-miss.

**Why the value is not in the quote, by design.** The prompt instructs the model to return a canonical
value — `extractor.py:257-260`: *"Canonical values: voxel_temporal_zscore, other"* — so for this field
the model's own value is never prose. A value-in-quote test of the kind the motion check applies is
testing the wrong thing on this field.

### 1b. There is no synonym table for the temporal field; it resolves by exact Literal membership

- `synonym_resolver.py:268`, `SYNONYMS_BY_FIELD`, carries four keys — `target_space`,
  `surface_registration`, `target_surface`, `convention` — and no `method`. (`test_motion_method.py`
  asserts `SYNONYMS_BY_FIELD.get("method") is None`, for the bare-id collision with motion.)
- `extractor.py:532` looks the table up; with none, `extractor.py:549` takes the model's value as the
  resolved value when it is a Literal member: `resolved, res_status = fe.value, "resolved"  # no synonym
  table; exact member only`.
- Build 2 §4c (`DESIGN_temporal_standardization_build2.md:226-234`) proposed `TS_METHOD_SYNONYMS`
  **conditionally** — *"if the resolver is used for it"* — listing five phrasings; it was not built,
  because the build took the exact-member path instead. The only resolver comment about this value,
  `synonym_resolver.py:162-165`, is in `INTENSITY_CONVENTION_SYNONYMS` and records that
  `voxel_temporal_zscore` deliberately has no entry *there* (a z-score is not a magnitude convention) —
  a different table from the one §4c proposed.
- **If §4c's phrasings were built as literal aliases**, two of the five are in liu's sentence after
  hyphenation repair — `temporally normalized` and `temporal standard deviation` — and the three
  z-score phrasings are not; the fifth, written with an ellipsis, is a pattern rather than an alias
  and would need a gapped match to fire as written.
- **An instrument for this field already exists and is unwired.** `subject_validator.py` (INERT,
  "nothing in the four-state path imports this") is a deterministic check on the *quote* — whether
  the subject of the normalisation verb is the BOLD signal — built and measured for exactly this
  field. It is the (b)-shaped check the field already has.

### 1c. The seven fields, by how their value is typed and resolved

| field | type | resolved through | underspecified list |
|---|---|---|---|
| `spatial_normalization.target_space` | Literal (`TargetSpace`) | `TARGET_SPACE_SYNONYMS` (`synonym_resolver.py:34`) | yes (`:83`; bare `MNI`, `MNI152`, `standard space` …) |
| `spatial_normalization.resolution_mm` | number (`float`) | none | — |
| `surface_projection.surface_registration` | Literal | `SURFACE_REGISTRATION_SYNONYMS` (`:95`) | yes (`:117`) |
| `surface_projection.target_surface` | Literal | `TARGET_SURFACE_SYNONYMS` (`:125`) | no |
| `intensity_normalization.convention` | Literal | `INTENSITY_CONVENTION_SYNONYMS` (`:134`; aliases carry an `@<value>` context marker) | no |
| `intensity_normalization.value` | number (`float`) | none | — |
| `temporal_standardization.method` | Literal (`voxel_temporal_zscore` / `other`) | **none — exact member only** (`extractor.py:549`) | — |

For comparison, `motion_correction.method` is a Literal with the table lookup opted out
(`use_synonym_table=False`), and the model is told to return the paper's own words; that is why a
value-in-quote test fits it and does not fit the temporal field.

## 2. The fork — stated, not resolved

For canonical fields, "supported by its quote" can mean:

- **(a) value-in-quote** — the value's string, in some word form, appears in the quote (what the
  motion check does; numbers by numeric equality of a token);
- **(b) quote-resolves-to-value** — the quote resolves to the value through the field's synonym
  table: an alias of the resolved canonical appears in the quote; for an `underspecified` value, an
  alias of the field's underspecified list; for a field with no table, there is nothing to resolve
  through.

Each was computed two ways, because the matcher matters as much as the definition:

- **loose** — the motion check's `_stem_equivalent` as built: suffix-stripped stems, and one stem may
  be a prefix of the other;
- **tight** — the same, except a token containing a digit must match exactly (word forms are
  tolerated for alphabetic tokens only).

And (b) once with aliases split into first-use variants (as `quote_supports_value` splits a model
value) and once with aliases taken whole.

### 2a. Predicted demotions over the 19 stored results

32 EXTRACTED values on the 16 non-held-out papers; 3 on the held-out three.

| definition / matcher | demotions, 16 papers | which | held-out (counts only) |
|---|---|---|---|
| (a) loose | **7** | chen convention 4006–4143; liu_2013 temporal 4733–4884; mueller convention 4452–4573; poldrack surface_registration 28132–28556, target_surface 28899–29153, convention 25523–25671; power convention 3368–3528 | 3 values, 0 demotions |
| (a) tight | **8** | the seven above, plus chen target_surface 4713–4938 (a digit-bearing surface form the table knows and the tight matcher does not) | 0 |
| (b) loose, aliases split | **1** | liu_2013 temporal — no table, so (b) falls back to (a) there | 0 |
| (b) tight, aliases whole | **1** | liu_2013 temporal, same reason | 0 |

Per field under (a) loose: convention 4 of 5, surface_registration 1 of 3, target_surface 1 of 3,
temporal 1 of 1, target_space 0 of 12, both numeric fields 0. Under (b) every table-backed field has
zero demotions; the only demotion is the field with no table.

**So the whole difference between (a) and (b) on the record is six convention/surface values the
model returned in canonical form while the quote carries a known alias, plus the one field (b) cannot
reach.** Under (b), liu_2013 is demoted **only because the table §4c proposed was never built**; with
that table, and the two phrasings that are literally present, the prediction is zero demotions on the
16 papers and zero on the held-out three.

### 2b. Does each definition reject a value more specific than its quote?

Probed with synthetic quotes against the value `MNI152NLin6Asym` and the `target_space` table:

| quote names | (a) loose | (a) tight | (b) aliases split | (b) aliases whole |
|---|---|---|---|---|
| only "MNI space" | reject | reject | reject | reject |
| only "MNI152 standard space" | **pass** | reject | **pass** | reject |
| "the FSL MNI152 template" | **pass** | reject | pass | pass |
| the identifier itself | pass | pass | pass | pass |

Three findings, each a property of a mechanism rather than of a definition:

1. **(a) as the motion check implements it does not reject a more specific identifier.** The prefix
   clause of `_stem_equivalent` lets `mni152` stand for `mni152nlin6asym`. The tight matcher closes
   that, and on the motion record it costs nothing: over the 160 resolved motion draws, loose and
   tight agree on every verdict. Tightening the motion check is therefore a free follow-up, proposed
   here and not made.
2. **(b) leaks the same way if first-use variant splitting is applied to aliases**: the alias
   `MNI152 (FSL)` splits into a bare `MNI152`, which then supports the specific template. Taken whole,
   the aliases reject bare `MNI` and bare `MNI152` (both are in the underspecified list, which resolves
   to no template).
3. **(b) accepts "FSL MNI152" for `MNI152NLin6Asym`, and that is the resolver's own ruling** — the
   table at `synonym_resolver.py:34` lists it as an alias, i.e. the vendor-default inference is made
   at resolution time already. A guard built on the table inherits that inference; a guard built on
   (a) tight does not. Whether the inference belongs in the resolver is not this DELTA's question, but
   it is where the CALL 7 concern lands under (b).

**CALL 7 under either definition.** An absence-evidenced `native_volume` (binder, chen) has no quote
containing the value or any `native_volume` alias, so both (a) and (b) reject it as an extraction —
which is the claim the two unedited documents make and nothing enforces today. A paper that states
"native space" explicitly is supported under (b) by the alias and under (a) by the words, as it should
be: that is a stated value, not an inferred one.

## 3. What each branch would commit the author to

- **(a) for every field** is one rule, the motion rule, applied seven more times. It demotes 7 (loose)
  or 8 (tight) stored values that are correct canonical extractions with a known alias in the quote,
  and it keeps the matcher's over-specificity leak unless tightened. It needs numeric equality for the
  two number fields either way.
- **(b) for table-backed fields** demotes nothing stored and rejects over-specific identifiers when
  aliases are matched whole, but it inherits every inference the tables already make, and it has no
  definition for the temporal field until a table or the subject check is wired. For that field the
  choice is between building §4c's five phrasings as literal aliases (two of which carry liu),
  wiring `subject_validator` as the quote-side check, or leaving the field on exact membership with
  no support check at all and saying so.
- **Numbers** are outside both definitions as written; a form-tolerant numeric equality (the survey's
  `number_form` class, four stored values) is the only rule that passes them.
- **Held-out:** no stored held-out value moves under any variant.

## 4. Open, for the author

1. (a) or (b) — or (b) where a table exists and (a) tight elsewhere, which is the only mixed rule the
   numbers above make coherent.
2. For the temporal field: build §4c's table, wire the subject check, or neither.
3. Whether first-use variant splitting applies to table aliases (it must not, for (b) to reject bare
   `MNI152`).
4. Whether to tighten the motion check's matcher now (zero change on the 160 resolved draws).
5. Whether "FSL MNI152 → MNI152NLin6Asym" stays a resolver inference; if it does, (b) will pass it and
   the survey's `target_space` 12 of 12 remains the number the poster can cite.
6. After the build, the dated notes for `target_space-call7-unreachable.md` and
   `target_space-pending-runs.md`: the routing held in the data before the check existed, and the
   check enforces it from that date on.

---

## 5. Rulings — 2026-10-26, by the author, recorded the day they were given

*Sourced to the author's instruction of 2026-10-26 (later the same day as §1–4), not backdated. The
fork in §2 is left as written; this is what was decided.*

1. **Literal fields** — `target_space`, `surface_registration`, `target_surface`,
   `intensity_normalization.convention`, `temporal_standardization.method`: **supported means an alias
   of the returned value, taken whole, occurs in the repaired quote.** Reason: the prompt asks the model
   for canonical tokens (`extractor.py:260`, "Canonical values: voxel_temporal_zscore, other"), so a
   value-in-quote test rejects correct extractions — 7 to 8 on the stored record (§2a).
2. **Numeric fields** — `resolution_mm`, `intensity_normalization.value`: **the value's digits occur in
   the quote, digit-exact.** *Implemented as:* a number in the quote equals the value with no
   tolerance; "3" and "3.0" are one number, "1,000" is 1000, and "3" is not supported by "30" or
   "3.5". (A literal digit-string test would reject every stored resolution — the paper writes "3",
   the field stores 3.0 — which is the mistake ruling 1 forbids on the Literal fields.)
3. **The temporal field gets its synonym table** (build 2 §4c, never built), seeded from §4c's
   phrasings plus z-scored / z-scoring stems for Cho's wording. **The check runs on the span
   resolver's repaired text.** *Implemented as:* `TS_METHOD_SYNONYMS` (`synonym_resolver.py:278`), used
   by the check only and deliberately **not** added to `SYNONYMS_BY_FIELD` — that map is keyed on the
   bare field id, `method` is two fields', and the author's condition was that resolution and raw
   outputs stay as they are. The field still resolves by exact Literal membership (`extractor.py:549`).
4. **Aliases are never split into first-use variants for this check.** Split, "MNI152 (FSL)" yields a
   bare "MNI152", and a quote saying only MNI152 would support `MNI152NLin6Asym`.
5. **The motion matcher is tightened to digit-exact in the same change**; the replay must show 0 of 160
   resolved motion draws changing. (It shows 0: totals 30 / 20 / 110 / 20, unchanged.)
6. **A rejected value renders as unverifiable, never "not reported"**; its reason base,
   `value_unsupported_by_quote`, is in `_UNVERIFIABLE_GAP_BASES` (`cobidas.py`).

**Three decisions the build had to take inside ruling 1, recorded as this author's, not the ruling's:**

- **A Literal member with no aliases — `other` on every field — passes through unchecked.** "Other"
  names nothing a quote could carry; demoting it would be ruling 1's mistake again. A spurious `other`
  asserts no specific value. Known limit.
- **An `underspecified` family term may match the START of a longer identifier in the quote**
  ("MNI152" against a quote whose token is "MNI152NLin6Asym"). That is the safe direction — the value
  is less specific than its quote — and the reverse is never allowed (`quote_support.py`,
  `_prefix_or_equivalent`, used for family terms only).
- **An `unrecognized` value is its own only alias.** A free-text value the table does not know must
  occur in its quote, whole. This turns one 0.5.0 fixture's claim around: a value absent from its
  quote is now demoted, with `value_unsupported_by_quote` and the raw value retained on the
  diagnostic — never with `value_not_in_literal`, and never coerced. The fixture carries a dated note
  (`tests/test_temporal_standardization_routing.py`).

### CALL 7, quoted, and the alias at `synonym_resolver.py:38`

**CALL 7** (`docs/ground-truth-protocol-target_space.md`, the ratified section): *"`target_space`
records where the functional **timeseries** ends up volumetrically. Two corollaries follow. (a)
Normalization applied to derived statistical maps does not set `target_space`. … (b) A timeseries that
exits to the surface axis with no stated volumetric target is `native_volume` volumetrically."* And
from the changelog (`:12-15`): *"`target_space` is the terminal volumetric state of the functional
TIMESERIES: (a) normalizing derived statistical maps does not set it (binder → native_volume); (b) a
timeseries that exits to the surface axis with no stated volumetric target is native_volume
volumetrically (chen → native_volume)."*

**Does "FSL MNI152" → `MNI152NLin6Asym` conflict with CALL 7? No.** CALL 7 decides *which volumetric
state* the timeseries reaches — native, a named template, a surface exit — and says nothing about how
a named template resolves to a canonical token. A quote naming FSL's MNI152 as the target the
timeseries reaches is a named volumetric target under CALL 7 either way; the alias only decides which
token it becomes.

**The rule the alias touches is CALL 2** (`:164-190`), quoted: *"canonical: names a specific
resolvable template — a variant identifier, or a template FILE that resolves by established identity
(oconnor's FSL file). family_specified: names the family via bare term OR via a tool, but not a
resolvable variant."* and *"**Rule:** canonical requires a reference that resolves to ONE specific
template (variant or file). A family term, or a tool-generic MNI reference, is family_specified. When
unsure whether a reference resolves, it is family_specified (canonical is the stricter claim; do not
over-credit)."* Under that wording the **phrase-form alias** "FSL MNI152" (`synonym_resolver.py:38`,
comment "FSL ships NLin6Asym unambiguously") is a tool-generic MNI reference and would label
`family_specified`, while the resolver returns `canonical`-grade `MNI152NLin6Asym` — the same shape as
CALL 2's own open question on wheaton's "SPM MNI template". The **file-form aliases** (`:44-49`,
`MNI152_T1_2mm` and kin) are CALL 2's oconnor case, "a template FILE that resolves by established
identity", and do not conflict. **Listed as open, not resolved here.** Under ruling 1 the phrase alias
passes the check for a quote that names FSL's MNI152, as the resolver's own inference.

**Is there a less specific MNI152 token the phrase could extract to instead?** No. `TargetSpace`
(`src/fmri_repro/spec/preprocessing.py:835-845`) is `MNI152NLin6Asym`, `MNI152NLin2009cAsym`,
`Talairach`, `native_volume`, `study_specific`, `other`. The representation the extractor already
uses for a family-level value is `SpecifiedTerm(resolved=None, resolution="underspecified")` — what
"MNI" and "MNI152" produce today — which the completeness derivation grades as family. So if the alias
moved to the KB, "FSL MNI152" would extract as underspecified with no token, not to a less specific
member; whether that is "the gap reported" is the author's call.

---

## 6. Built — 2026-10-26 (later)

`extractor_mvp/src/extractor_mvp/quote_support.py` — `tokens` (the resolver's normaliser, so
line-break hyphenation is repaired), `token_equivalent` (digit-exact; word forms for alphabetic tokens
only; a bare prefix is not equivalence), `phrase_in_quote` (whole, contiguous, no variant splitting),
`number_in_quote`, `literal_value_supported`, `step_value_supported`. Applied in `_process_field` at the
Extracted return (`extractor.py:601-606`) on `resolution.span.text`, with one literal reason the render
scan can see. `motion_guard` imports the shared matcher. `TS_METHOD_SYNONYMS` at
`synonym_resolver.py:278`. The reason is in `_UNVERIFIABLE_GAP_BASES` and both render tables.

**Replay over the 19 stored results (`scripts/step_field_support_replay.py`, no model calls): 0
demotions** — 32 values on the 16 non-held-out papers pass, liu_2013's temporal method through the new
table (its alias `temporally normalized`, after hyphenation repair); the held-out three: 3 values, 0
demotions, nothing else said. Which alias carries each stored Literal cell is recorded in
`docs/findings/step-field-support-replay.md`, offsets only.

**Mutations** (each must fail a named test; sources restored after each, suite green): an alias removed
from its table (`normalized to a mode of 1,000` from `global_mode_1000`) — 2 tests fail and the replay
demotes poldrack's convention cell 25523–25671; aliases split into first-use variants — 5 tests
fail, the split-alias test among them; a numeric tolerance of 1 — 3 tests fail; the temporal table emptied — 6 tests
fail and the replay demotes liu_2013's 4733–4884; the digit rule removed from the matcher — 9 tests
fail, among them the motion leak regression.

**Identity gate against HEAD, derived first: 19 identical** (the check runs at extraction; the gate only
re-renders stored JSONs, and 0 of them carry the new reason); measured 19 identical. **Negative control
against `d31e8b7`: 0 identical, 19 changed**, as derived. 447 passed in extractor_mvp, 235 root, hooks
and `ruff format --check` clean. No prompt, raw output, projection or committed number moves; the
processed layer is re-vintaged for the seven step fields, and on the stored record it changes nothing.

---

## 5a. Ratified — 2026-10-26, by the author

*Sourced to the author's instruction of 2026-10-26 (evening), not backdated.*

The three decisions §5 recorded as this author's are **ratified**:

- **A family term may match the start of a longer identifier, never the reverse** — follows from
  ruling 1: a value may be less specific than its quote but not more.
- **An unrecognized value is its own only alias** — a free-text value is checked the way motion's is:
  its own string must appear in the quote.
- **`other` passes through** — right as far as it goes, since there is no alias to test, with the
  stated consequence that the check cannot catch the model returning `other` where the quote names a
  canonical member. Whether `other` needs a contradiction test is decided on the count of such cells
  (§7, Part 3: zero on the record today).

**Rule for every future mutation test, from the same instruction:** *a mutation counts only once its
diff is shown to be non-empty before the run.* Reason: the split-alias mutation of 2026-10-26 first
ran against a stale anchor, changed nothing, and reported a pass; it was caught by reading the line,
not by the harness.

---

## 7. Facts gathered 2026-10-26 for the FSL MNI152 alias — no ruling

*Read-only; no code changed, no model calls. The author's position (the alias is a fact about what FSL
ships, not something the paper reported, and belongs on the inference arm with a basis, as the v1.4
motion amendment puts tool-behaviour evidence) is recorded here as a position, not a ruling. The
file-form aliases are not in question: a file name identifies the template (CALL 2's oconnor case).*

### 7.1 CALL 2, in full — `docs/ground-truth-protocol-target_space.md:164-188`

> ### CALL 2 — canonical vs family_specified: does the reference resolve to a SPECIFIC template?
> The boundary is resolvability to a specific variant/file, NOT how "official" the name sounds.
> - **canonical**: names a specific resolvable template — a variant identifier, or a template FILE that
>   resolves by established identity (oconnor's FSL file).
> - **family_specified**: names the family via bare term OR via a tool, but not a resolvable variant.
>   - wheaton "SPM MNI template" → **family_specified for now; OPEN QUESTION.** Author's position: a
>     user CAN trace SPM's MNI template (SPM99 + "MNI template" identifies the file SPM99 shipped), which
>     argues for canonical. Counter-consideration (UNVERIFIED, needs checking before promotion): SPM's
>     bundled template differs by SPM version, and older SPM templates may derive from the *linear*
>     ICBM152 rather than the nonlinear 6th-gen — for which `TargetSpace` currently has NO enum value.
>     Promoting wheaton to canonical therefore requires (a) verifying which template SPM99 actually
>     shipped and (b) possibly adding a linear-MNI152 enum value (an additive patch bump under the new
>     versioning convention). **Until verified, label family_specified and record the open question.**
>     Do not promote on the strength of "traceable" alone — traceable-to-a-file is not the same as
>     resolvable-to-an-enum-value.
>   - derosa "MNI-152 template, 12-dof linear" → **family_specified**. Names the family + the transform
>     d.o.f., but not a variant identifier or file.
>   - cole / liu_2005 "Talairach" (even citing "Talairach and Tournoux (1988)") → **family_specified**, NOT
>     canonical. Talairach is a coordinate SYSTEM realized by many digital templates (AFNI's TT_N27, the
>     original 1988 atlas, SPM's, …), so citing it names the family, not a resolvable digital variant.
>     (Supersedes the v1.1 canonical "Talairach with its atlas" clause — see changelog; liu_2005 was the
>     derivability-check trigger.)
> **Rule:** canonical requires a reference that resolves to ONE specific template (variant or file).
> A family term, or a tool-generic MNI reference, is family_specified. When unsure whether a reference
> resolves, it is family_specified (canonical is the stricter claim; do not over-credit).

### 7.2 Which committed cells resolved through the alias — none

Classified by the alias the resolver fired (`resolutions[].matched_alias` in the stored results; the
resolver re-run on the stored `verbatim` for v050; see 7.2's recoverability note for v040). Phrase
form = `synonym_resolver.py:38-40` (`FSL MNI152`, `FSL's MNI152`, `MNI152 (FSL)`); file form =
`:44-49`; identifier = the variant name itself.

| record | non-held-out `target_space` cells | via phrase alias | via file alias | via identifier | what the cells are |
|---|---|---|---|---|---|
| stored results (`batch_a1_acceptance`, 19) | 16 | **0** | **0** | **0** | Talairach ×2 (binder, cole), study_specific ×1 (mueller), the rest `resolved=None` |
| `target_space_predictions_v040_frozen.csv` | 16 | 0 | 0 | 0 | EXTRACTED Talairach ×2, DEFERRED ×1, MISSING ×13; **no `MNI152NLin6Asym` anywhere in the 19** |
| `target_space_predictions_v050.csv` | 16 | 0 | 0 | 0 | underspecified ×6, unrecognized ×3, Talairach ×2, study_specific ×1, MISSING ×4; **no `MNI152NLin6Asym` anywhere in the 19** |

Held-out papers (liu_2005, tang_2025, wheaton_2004), counts only: 3 cells per record, **0** on any
`MNI152NLin6Asym` path in all three records.

**What is not recoverable.** `v040_frozen` carries `extractor_value` — the resolved member, since the
pre-0.5.0 extractor discarded the raw string on success — and keeps a raw string only in
`raw_diagnostic` for the 10 non-held-out `value_not_in_literal` cells. For a v040 EXTRACTED cell the
alias path is therefore not recoverable in principle; it is moot here, because no v040 cell is
`MNI152NLin6Asym`. `v050` keeps `verbatim` on 13 non-held-out rows and its paths are recoverable.

**One more fact the table implies.** oconnor_2017 — the one labelled-canonical paper, which names an FSL
template *file* (`target_space_labels_v1.csv:47`) — was flattened by the model to the bare family term
in both vintages (`docs/findings/extraction-specificity-flattening.md:11,52`). So the file-form aliases
have never fired on a committed cell either; the alias question has so far been decided by no data.

### 7.3 How the scoring map treats `underspecified` — `ground_truth/target_space_scoring_map.csv`

| resolver verdict | scored state | vs `family_specified` label | vs `canonical` label |
|---|---|---|---|
| `resolved = MNI152NLin6Asym` | canonical | **error** (over-specific) | correct |
| `resolution = underspecified` (bare MNI / MNI152 / standard space) | family_specified | correct | **error** (under-specific) |
| `resolved = other` | family_specified ("catch-all; UNUSED on this corpus") | correct | error |

So moving the alias to the inference arm, with no family-level token, would score a paper that writes
"FSL's MNI152" as family_specified: correct under CALL 2's wording for that paper, an error only if its
label were canonical — and no committed label is canonical on a phrase form (oconnor's is on a file).

### 7.4 Can the KB carry it today — no

- `recognize(name)` (`fmri-defaults-kb/src/fmri_defaults_kb/registry.py:105-128`) resolves a name
  against **pipeline documents** only — `kb/pipelines/`: `ccs`, `cpac`, `fmriprep`, `hcp_minimal`.
  **FSL is not a recognized pipeline.** `kb/tools/` exists and is empty, and no code reads it.
- `fill_dependent_defaults` (`src/fmri_repro/kb_client/base_pipeline.py:176-220`) fills
  `SEVEN_DEMOTED_FIELDS` — **`spatial_normalization.target_space` is one of them** (`:65`) — only for a
  recognized pipeline whose version is *certain*, via `get_param_defaults(pipeline_id, version, …)`,
  wrapping each as `InferredDefault` with `VersionDefaultBasis` (ceiling 0.95). The path is
  pipeline-keyed and version-keyed; there is no tool-keyed path.
- Basis types (`src/fmri_repro/spec/provenance.py:88-125`): `version_default(tool, version)`,
  `date_inferred_version`, `prior_publication`, `lab_prior`, `field_convention(source)`, `derived`. The
  one that fits "FSL ships MNI152NLin6Asym" is **`version_default`**, whose schema already carries
  `tool` and `version` — if FSL were modelled as a KB pipeline document with a certain version. Without
  a version, the only tool-independent basis is **`field_convention`** (ceiling 0.40, `source` = FSL
  documentation / TemplateFlow), which under-states a fact that is not a convention.
- So today the inference cannot be carried: no FSL document, no tool-keyed path, and the pipeline-keyed
  path requires a certain version the paper may not state. Building it is an FSL pipeline document in
  the KB plus a `target_space` default keyed on its versions, or a new tool-keyed path — either is its
  own change.

### 7.5 What in the record depends on the phrase alias resolving canonical

| kind | locator | dependence |
|---|---|---|
| test | `extractor_mvp/tests/test_synonym_resolver.py:34-38` (`test_fsl_mni152_resolves_to_nlin6asym`, phrase "registered to the FSL MNI152 template") | **fails** if the alias moves |
| test | `extractor_mvp/tests/test_quote_support.py:143` (asserts the phrase-form quote supports `MNI152NLin6Asym` through the table's own alias) | **changes** if the alias moves |
| test | `extractor_mvp/tests/test_quote_support.py:179-180` (uses the string "MNI152 (FSL)" only as the whole-vs-split example) | needs a different example string; not a dependence on resolution |
| test | `extractor_mvp/tests/test_synonym_resolver.py:40-50` (file forms) and `:52-56` (bare MNI152 stays underspecified) | **unaffected** — file forms stay |
| committed number | target_space 11/17 (v040) and 10/17 (v050) | **none** — no committed cell resolved via the phrase alias, or via any `MNI152NLin6Asym` alias (7.2) |
| findings claim | `ground-truth-protocol-target_space.md:85`; `target_space_labels_v1.csv:47`; `target_space-design-resolution.md:22`; `extraction-specificity-flattening.md:11,52` | all **file-form** (oconnor); none rests on the phrase alias |
| the alias's own record | `synonym_resolver.py:38` ("FSL ships NLin6Asym unambiguously"); this DELTA §5; `DEVLOG.md:3163` | the statement itself and today's notes recording the question |

### 7.6 Part 3 — cells carrying `other`

Over the 19 stored results, across the five Literal fields and `motion_correction.method`: **0 cells
carry the value `other`**, so the number whose quote names a canonical member is 0. The same holds for
`v050`'s `resolved` column (0 of 19) and for the 180 recorded motion draws (0 raw values equal to
`other`); the scoring map already marks `other` "UNUSED on this corpus". There is nothing to count a
contradiction test against; the decision waits for the first `other`.

### 7.7 Ruling — 2026-10-26, by the author

*Sourced to the author's instruction of 2026-10-26 (evening), not backdated.*

**The phrase-form alias is removed; the file-form aliases stay.** A tool-generic MNI reference ("FSL
MNI152", "FSL's MNI152", "MNI152 (FSL)") resolves **family-level**, per target_space protocol CALL 2
(`:168`, `:186-188`): it names the family via a tool, not a resolvable variant. The template FSL ships
is a **tool fact for the inference arm** — the v1.4 motion amendment's principle, that tool-behaviour
evidence is a KB fact entering downstream through the inference arm with a basis, never through
labelling — and the resolver is part of the extraction arm, so the same applies. A file name identifies
the template (CALL 2's oconnor case), so `MNI152_T1_2mm` and its kin stay canonical.

**The KB side is backlog, not built.** Carrying "FSL ships MNI152NLin6Asym" needs a tool-keyed default
and a reader for `kb/tools`, which is empty and unread (§7.4). Until then a paper that writes "FSL
MNI152" extracts as `resolution="underspecified"`, which is what CALL 2 says it reported.

**What the removal cost: nothing on the record.** §7.2: no committed cell in the stored results or in
either prediction vintage resolved through the phrase forms, and no number or finding depends on them.
The replay over the 19 stored results after the removal: 0 cells change. Two tests moved with it —
`test_synonym_resolver.py` (the phrase now asserts `underspecified`) and `test_quote_support.py` (a
quote naming FSL's MNI152 supports the family-level value it now resolves to, not the specific
template). The resolver's comment at the former `synonym_resolver.py:38` records the removal and cites
this section.

**Side note, from §7.2, for the target_space stanza later:** oconnor_2017 names the template file and
the model returned the bare family in both vintages — a model under-claim, already scored as an error;
the file-form aliases have never fired on a committed cell.
