# DELTA — `unverifiable` for every row, not only Software

*Extends `DELTA_base_pipeline_diagnostic.md` §4a's unverifiable-gap rule from the Software row to
every row that maps to spec kinds. **Nothing here is implemented, and nothing is left blocking it.**
Six rulings are recorded — the precedence (§2) and the five that make it codeable (§3f), including the
classification of all twelve reason bases. Drafted and ruled 2026-10-19; every locator verified against
HEAD `290db8a` and the working tree, every number derived from files. Facts gathered by a
five-investigator read-only pass; all five returned, none silent.*

**Predicted re-render result: `17 identical, 2 changed` — `agtzidis_2020` and `liu_2005`.**

---

## 0. The finding that came first, and the ruling that answered it

**SUPERSEDED BY RULING 1 (§3f). The prediction is `17 identical, 2 changed`.** The analysis below is
retained because it is what made the ruling necessary and checkable, and because the path from one
prediction to the other is the content of this DELTA.

*As drafted:* under the classification the repository could defend before 2026-10-19, the proposed
precedence changed **0 of 304** rows across all 19 stored papers, predicting `19 identical, 0 changed`.

Two measured facts produce that:

1. **Step 1 of the precedence is the test the code already applies.** `cobidas.py:260` is
   `addressed = any(r.extraction_status in _ADDRESSING_STATUSES for r in mapped)` with
   `_ADDRESSING_STATUSES = frozenset({"EXTRACTED", "DEFERRED_TO_CITATION"})` (`:120`) — identical to
   the ruling's step 1.
2. **Step 2 never fires, because none of the three defensible could-not-verify bases occurs anywhere
   in the corpus.** Over 19 papers × 16 rows, the bases that actually occur are:

| base | occurrences | status |
|---|---|---|
| `not_targeted_by_mvp` | 361 | fits neither category (§3b) |
| `not_stated_in_text` | 95 | claim about the paper |
| `version_deferred_to_kb` | 6 | **open** |
| `no_base_pipeline_named` | 5 | claim about the paper |
| `extraction_quote_unresolved` | **3** | **open — and this is the one that matters** |
| `deferred_to_citation` | 1 | **open** |
| `citation_shaped_name_value_unsupported` | 1 | **open** |

`deferral_quote_unresolved`, `base_pipeline_value_unsupported` and `extraction_quote_missing` — the
three bases this pass could classify as could-not-verify without a ruling — occur **zero** times.

**So the entire effect of this DELTA on the committed corpus rested on one undecided question:** is
`extraction_quote_unresolved` a statement that the tool could not verify? **Ruling 1 (§3f) says yes**,
and exactly two papers change — agtzidis_2020 and liu_2005, each on Intersubject registration.

**And `19 identical, 0 changed` is precisely what a broken gate prints.** `rerender_reports.py:31-36`
records that a silently failed `PYTHONPATH` override also prints 19 identical. A zero-change
expectation therefore cannot distinguish "the change is a no-op here" from "the gate ran the same code
twice" — which is the strongest argument for ruling 1 that this analysis produced, and is why the
ruling's `17 identical, 2 changed` is a criterion that can fail for the right reason. The negative
control remains required (§5.2); it is no longer the *only* thing carrying the criterion.

---

## 1. Scope

**In scope.** Extend §4a's rule — a gap the extractor could not *verify* keeps a row silent rather than
counting as assessed — from the Software row to every row, and render the resulting state honestly.

**Why now.** Motion ruling C (`DESIGN_motion_correction_extraction.md` §4) makes this a precondition:
motion must not be turned on while a dropped quote on `motion_correction.method` would print
`- Motion correction` as a bare line, which states that the paper did not report motion correction.

**Not in scope.** The motion extraction itself; any change to the Software row's behaviour (§4.2 is
explicit that one reading of this ruling would change it, which is why that reading is flagged rather
than adopted); labelling; any figure.

---

## 2. The ruling, recorded

> **RULED 2026-10-19.** A row's state is decided by this precedence:
>
> 1. **addressed** — if any of the row's fields is `EXTRACTED` or `DEFERRED_TO_CITATION`;
> 2. otherwise **unverifiable** — if any field's reason is in the tool-could-not-verify set;
> 3. otherwise **not reported**.

*The reason, in one sentence:* **unverifiable outranks not-reported because the failed quote may be
exactly where the paper reported the step.**

*Source and date.* Ruled by the author in conversation, written down here on 2026-10-19, **not
backdated** — the record's date is the date it became checkable.

**What the ruling does not yet determine, and cannot be implemented without.** The precedence is
stated over "the row's fields". Two inputs to that phrase are undecided, and §4.1 and §4.2 hold them
open rather than guessing:

- **which reason bases are in the could-not-verify set** — 9 of 12 are unclassified (§3b);
- **what "the row's fields" means for the Software row**, whose `spec_kinds` is empty.

---

## 3. What exists

### 3a. Where coverage is computed

`RowCoverage` (`cobidas.py:156-165`) is a frozen dataclass with four fields, only the last defaulted:

```
156 @dataclasses.dataclass(frozen=True)
157 class RowCoverage:
158     row: CobidasRow
159     addressed: bool  # >=1 field on a mapped kind is EXTRACTED or DEFERRED_TO_CITATION
160     covered_by_extractor: bool  # the extractor targets >=1 field on a mapped kind
161     #: NOT covered because the extractor looked and could not VERIFY what it found — as distinct
162     #: from never having targeted the row. Two different facts, and the coverage header must not
163     #: collapse them (DELTA_base_pipeline_diagnostic.md §4a). Defaulted so the only construction
164     #: site stays the only thing that has to know about it.
165     unverifiable: bool = False
```

`assess_coverage` is `:237-273`. Its branch is the whole mechanism:

```
253     for cr in COBIDAS_D3_ROWS:
254         if cr.row_id == "software":
255             addressed, covered, unverifiable = _software_coverage(
256                 base_row, version_extraction_status
257             )
258         else:
259             mapped = [r for k in cr.spec_kinds for r in by_kind.get(k, [])]
260             addressed = any(r.extraction_status in _ADDRESSING_STATUSES for r in mapped)
261             covered = _row_covered_by_extractor(mapped)
262             # Only the Software row can be unverifiable today: every other row's coverage is pure
263             # targeting (_row_covered_by_extractor), which is a code property, not a per-paper one.
264             unverifiable = False
```

**Locator confirmed with one refinement:** the prompt gives `cobidas.py:253-264` for the hardcode.
`253-264` is the loop body's non-Software branch; the assignment itself is **`:264`**, and the comment
explaining it is `:262-263`. Supporting definitions: `_UNVERIFIABLE_GAP_BASES` at `:133-139`,
`_gap_base` at `:142-148`, `_row_covered_by_extractor` at `:168-171`, `_software_coverage` at
`:174-234`. `cobidas.py` and `render.py` are byte-identical to HEAD (`git diff HEAD` on both printed
nothing); the six staged files do not include either.

### 3b. Which reasons mean the tool could not verify — mostly undecided

An AST walk over the producible `LeftMissing(reason=...)` strings yields **12** bases. Classified
against the repository's two existing sources — `_UNVERIFIABLE_GAP_BASES` (`cobidas.py:133-139`) and
the `render.py:487-490` comment that certain reasons "assert nothing about what the manuscript
reports" — the result is:

| | bases |
|---|---|
| **could not verify** (3) | `deferral_quote_unresolved`, `base_pipeline_value_unsupported`, `extraction_quote_missing` |
| **claim about the paper** (2) | `not_stated_in_text`, `no_base_pipeline_named` |
| **OPEN** (9, listed in §4.3) | `extraction_quote_unresolved`, `value_not_numeric`, `version_deferred_to_kb`, `not_targeted_by_mvp`, `field_not_in_schema_version`, `deferred_to_citation`, `citation_shaped_name_value_unsupported`, and two free-text dynamic producers |

**Three-quarters of the set is open, and the most consequential base is in it.**
`extraction_quote_unresolved` is listed in `_UNVERIFIABLE_GAP_BASES` (`cobidas.py:135`) — so for the
Software row the code already treats it as unverifiable — but the `render.py:487-490` comment does not
name it among the reasons that assert nothing. That comment covers reasons firing *before* quote
validation; this one fires *at* it. The two sources are about different things rather than in direct
conflict, which is exactly why a ruling and not a reading is needed.

**Five defects found in the two sources while classifying them.** None blocks this DELTA; each is
recorded because the sources are what any implementer will reach for.

1. The "assert nothing" comment is at **`render.py:487-490`**. `report-surface-inconsistencies.md:29`
   and `DELTA_base_pipeline_diagnostic.md:219` and `:235` all place it at `482-484`. Stale.
2. `render.py:489-490` points at `tests/test_render.py::test_every_producible_reason_base_is_mapped`
   for "the semantics note". That test (`:716-757`) has no such note; it is at `test_render.py:598-599`,
   in a different test.
3. **`render.py` contradicts itself about `value_not_numeric`.** The `:487-490` comment says it asserts
   nothing about the manuscript; `:463` buckets it `unmappable`, whose header label (`:511`) is
   "reported but unmappable to controlled vocabulary" — a claim that the paper *did* report it.
4. `test_render.py:586` says "each of the 9 known base reasons" above a dict of **10** entries, one of
   which (`value_not_in_literal`) is produced by no current code — its producer was removed in
   `382795a`. It survives only in migrated ≤0.4.1 documents.
5. **The AST guard has a blind spot, and its docstring overclaims.** `test_render.py:717` says "No
   reason this codebase produces may fall through to the `unclassified` fallback." The scan walks only
   `extractor.py` and `migrations.py`. `kb_client/base_pipeline.py:150` has
   `LeftMissing(reason=str(exc))` and `:310-316` builds a reason by f-string; both are reachable from
   `extractor.py:1183-1185` and `:1197-1203`. Their bases are free text, so no enumeration can cover
   them and the guard cannot see them. Same family as the `consts` last-write-wins blind spot recorded
   on 2026-10-01.

### 3c. What the report would print — the header is generic, the body is not

The counters are `render.py:761-808`. The third count from `2018bd3` is emitted only when non-zero:

```
770     mand_unverifiable = [rc for rc in mand_not_assessed if rc.unverifiable]
771     mand_untargeted = [rc for rc in mand_not_assessed if not rc.unverifiable]
797     if mand_unverifiable:
798         lines.append(
799             f"  Not assessed by AESPA: {len(mand_not_assessed)}  →  "
800             f"never targeted {len(mand_untargeted)} · "
801             f"targeted but unverifiable {len(mand_unverifiable)}"
802         )
803     else:
804         lines.append(f"  Not assessed by AESPA: {len(mand_not_assessed)}")
```

**There are exactly two reads of `.unverifiable` in `render.py` — `:770` and `:771` — and neither is
filtered by `row_id`.** The only row_id-filtered use is `:813`
(`software_unverifiable = any(... == "software" ...)`), which picks which sentence goes in the
parenthetical. So **the header already handles a non-Software unverifiable row correctly**, without
any change.

**The body does not, and this is the part the DELTA must also fix.** Three sub-cases, and `RowCoverage`
has no `__post_init__`, so nothing forces `unverifiable=True` to arrive with `covered_by_extractor=False`:

| case | header | body |
|---|---|---|
| mandatory, `cov=False, unverif=True` (the convention `_software_coverage` uses at `:233`, `return False, False, True`) | counted correctly: `never targeted 12 · targeted but unverifiable 1` | falls into *Not reported whether performed* with the **same tag as never-targeted** — `_tag` (`:838`) reads only `covered_by_extractor` |
| mandatory, `cov=True, unverif=True` | **flag ignored entirely** — `:770-771` draw from `mand_not_assessed` only | bare line, no tag. Silent |
| non-mandatory, `unverif=True` | **dropped at `:761`** before any counter | prints under *Optional per COBIDAS* with the never-targeted tag. Silent |

And `_tag`'s own comment at `:837` says the tag means "no field on any mapping kind is targeted" —
**false** for an unverifiable row. An unverifiable Software row (`cov=False`) appears in no body
section at all.

So the honest answer to "handled already, or unhandled" is: **the header is handled, the three body
surfaces are not.**

### 3d. The gate result, derived before any code exists

19 stored JSONs in `results/batch_a1_acceptance/papers/` (gitignored; listed with Python), all
`schema_version` 0.5.1, each `paper_id` matching its stem. Current state over 304 rows: **22 addressed,
282 not reported, 0 unverifiable**; 57 covered — Software, Intersubject registration and Intensity
normalization on all 19 papers, the other 13 rows on none.

**Predicted result under the ruling, with A2's defensible set: `19 identical, 0 changed`** — verified
two ways, by row classification and by an in-memory render simulation that swapped
`render.assess_coverage` and compared `to_report` output byte for byte across all 19 papers.

**The sensitivity that matters.** If `extraction_quote_unresolved` is ruled could-not-verify, exactly
two rows flip to unverifiable, both `intersubject_registration`:

| paper | field(s) | reason |
|---|---|---|
| agtzidis_2020 | `spatial_normalization.target_space`, `.resolution_mm` | `extraction_quote_unresolved:quote_not_found` |
| liu_2005 | `spatial_normalization.resolution_mm` | `extraction_quote_unresolved:quote_not_found` |

**Contingency count:** 4 of 19 papers (agtzidis_2020, liu_2005, braun_2015, viduarre_2017) hang on an
open base; 19 of 19 if `not_targeted_by_mvp` is counted as open, which it formally is.

**Reconciliation with the "3 of 4 papers" finding.** That finding is in the staged
`DESIGN_motion_correction_extraction.md:680-684`, and it counts *files across batch families*, not the
19. Re-derived: 8 files, 4 papers — agtzidis_2020 (5 files), oconnor_2017, **marek_2022**, liu_2005.
It holds for agtzidis_2020, oconnor_2017 and marek_2022 (7 of 8 files); the exception is liu_2005 in
`batch_sfn_v3`, where `spatial_normalization.resolution_mm` is EXTRACTED so the row is addressed
anyway. **The doc's account is correct as measured.** Only agtzidis_2020 is among the 19, which is why
the corpus-wide effect is two papers and not four.

### 3e. Tests

| test | pins | verdict |
|---|---|---|
| `test_cobidas.py:280-293` `test_only_the_software_row_can_be_unverifiable` | `unverifiable` False for non-Software rows. Its input carries `extraction_quote_unresolved:quote_not_found` on a **motion_correction** row | **SUPERSEDED** — and its own docstring says it is meant to fail first in this case |
| `test_render.py:842-870` `test_report_surface_accounts_for_every_mandatory_d3_row` | the conditional list contains "Motion correction" | UNAFFECTED — membership (`render.py:891`) reads only mandatory, unconditional, addressed |
| `test_render.py:1152-1177` `..._keeps_never_targeted_and_unverifiable_apart` | third count == 1, and never + unverifiable == total | UNAFFECTED for its input; the sum check survives any renumbering. RE-NUMBERED only if a rule flags its addressed `spatial_smoothing` row |
| `test_render.py:1180-1193` `..._is_unchanged_when_nothing_is_unverifiable` | the third count is ABSENT when zero | UNAFFECTED for its input; its premise is SUPERSEDED only if a rule flags a non-Software row there |
| `test_render.py` chen fixture | `Assessed by AESPA: 2 → addressed 1 · not reported 1` | UNAFFECTED under the defensible set; RE-NUMBERED only if a rule makes `intersubject_registration` uncovered via a reason chen carries |
| `test_batch.py:90`, `test_registry_shape` | `Mandatory rows: 14` | UNAFFECTED — a registry constant |

**`2018bd3`'s Software tests are unaffected by a non-Software-only change**, with one stated condition:
`test_cobidas.py:226` and `:267`, all three `test_base_pipeline_extraction.py` additions,
`test_render.py:1196` and the `:611-616` dict entry are untouched; `test_render.py:1152` and `:1180`
are untouched **only if** the rule does not flag the addressed `spatial_smoothing` row in `_one_step`.
No test asserts the heading text, the closing parenthetical, or the `_tag` wording — so §4.1's wording
choice is unpinned and must be pinned by this change.

---

## 3f. RULED 2026-10-19 — the five rulings that unblock implementation

*Ruled by the author in conversation, written down here 2026-10-19, not backdated. §4 keeps each
question's evidence as it stood, so a later reader can see what was chosen against.*

### Ruling 1 — `extraction_quote_unresolved` means "the tool could not verify"

*Reason.* §4a already ruled this exact case for the Software row — a quote that did not match the text
— and `_UNVERIFIABLE_GAP_BASES` (`cobidas.py:135`) already lists it. The `render.py:487-490` comment is
**not a competing classification**: it describes reasons that fire *before* quote validation, which is
a different property of a reason, not a different verdict on this one. There was never a conflict to
resolve, only two lists that looked like one question.

*Therefore `_UNVERIFIABLE_GAP_BASES` is the single classification source*, and the `render.py:487-490`
comment is **reworded to point at it** rather than enumerating members, so it stops reading as a second
list. That rewording is part of this change's diff. (Not done in this document — this is design only.)

**The remaining eight bases, classified by name, one line each, no default.**

| base | ruling |
|---|---|
| `value_not_numeric` | **claim about the paper.** The paper gave a value; it did not parse. `render.py:463`'s `unmappable` bucket and its "reported but unmappable to controlled vocabulary" label (`:511`) are right, and the `:487-490` comment naming it is the error — fixed by the rewording above |
| `version_deferred_to_kb` | **claim about the paper**, as it stands. It is returned in *every* non-EXTRACTED case by `_build_version_pf`, so it conflates a quote failure with an absence — recorded as a known conflation to split when the version arm is built (`DELTA_base_pipeline_diagnostic.md` §10), not split here |
| `not_targeted_by_mvp` | **neither, and it must stay neither.** It is the one reason meaning the extractor never looked. `cobidas.py:161-163` keeps it deliberately apart from unverifiable, and `_row_covered_by_extractor` keys on it alone. Collapsing it into either category would destroy the distinction §4a exists to preserve |
| `field_not_in_schema_version` | **neither — the untargeted case.** CORRECTED 2026-10-19: an earlier draft of this table called it could-not-verify. `migrations.py:97-104` builds it with `MissingFromPaper(searched_terms=[], sections_searched=[])` — **empty** on both — and its own docstring says it "renders into the `not_covered` bucket" (`render.py:460`). The field was absent from the producing schema version, so the extractor never looked. The unverifiable tag would be **false** for it |
| `deferred_to_citation` | **not a gap reason.** It sits on a `DEFERRED_TO_CITATION` field (`extractor.py:472`, `:734`) and is already in `_UNREACHABLE_REASON_BASES` (`test_render.py:645`). Out of the set |
| `citation_shaped_name_value_unsupported` | **not a gap reason.** It sits on a `DEFERRED_TO_CITATION` field (`extractor.py:783`) and is already in `_UNREACHABLE_REASON_BASES` (`test_render.py:646`). Out of the set |
| the `KbAmbiguousError` message (`kb_client/base_pipeline.py:150`) | **could not verify.** The KB could not resolve the pipeline; nothing about the manuscript is asserted. Free text, so it cannot be enumerated — see the guard consequence below |
| the KB `not_applicable` message (`:310-316`) | **CORRECTED 2026-10-19 — neither. It is a NOT-APPLICABLE statement, and an earlier draft of this table called it a "claim about the paper", which is wrong.** Out of the gap set (correctly), but it must not land at "not reported" either. See §3g |

### The membership criterion, stated 2026-10-19 so the table cannot drift

**`_UNVERIFIABLE_GAP_BASES` holds GAP reasons only** — reasons that sit on a field whose
`extraction_status` is neither `EXTRACTED` nor `DEFERRED_TO_CITATION`. Everything else is out,
regardless of how it reads in prose.

*Why this is the right test, and why it also protects the Software row.* Step 1 of §2's precedence
consumes every `EXTRACTED`/`DEFERRED_TO_CITATION` field, so by the time step 2 consults a reason, **no
mapped field can be in either state**. A reason that only ever sits on a deferral is therefore
unreachable at step 2 by construction — keeping it out of the set is not tidiness, it is the removal
of a member that could never fire. And `_software_coverage:229` has no such guard: it reads
`base_row.left_missing_reason` on a row that may be `DEFERRED_TO_CITATION`. Admitting a deferral-only
base would have changed the Software row for `viduarre_2017`, whose `base_pipeline` is
`DEFERRED_TO_CITATION` with reason `citation_shaped_name_value_unsupported` — measured, and the reason
an earlier draft of this DELTA predicted 16/3 instead of 17/2.

**The resulting set** — `base_pipeline_value_unsupported`, `deferral_quote_unresolved`,
`extraction_quote_unresolved`, `extraction_quote_missing`, and the prefixed `kb_ambiguous` base from
ruling 6. Two additions over the current three.

**`_software_coverage` is unchanged in behaviour BY CONSTRUCTION, not merely on these 19 papers** —
checked 2026-10-19 rather than assumed, because the corpus-only version of this claim would have made
the DELTA's prediction contingent on the corpus:

- `extraction_quote_missing` is produced **only inside `_process_field()`** (`extractor.py:548-549`).
  An AST walk of `_build_base_pipeline` (`:684-861`) finds its reason literals to be exactly
  `base_pipeline_value_unsupported`, `citation_shaped_name_value_unsupported`,
  `deferral_quote_unresolved:base_pipeline_ref` and `extraction_quote_unresolved:base_pipeline_name:`
  — **no `extraction_quote_missing`**. So the `base_pipeline` field can never carry it.
- `kb_ambiguous` is written to `pipeline_ref.version` (`base_pipeline.py:149-151`), never to the
  `base_pipeline` field.

`_software_coverage:229` reads only `base_row.left_missing_reason`, where `base_row` is the row whose
`path == "base_pipeline"` (`cobidas.py:248-250`), and it is reached only when no version row exists.
Neither added base can appear there, so the Software row cannot move however the corpus changes.

The two KB bases are safe to classify this way for a structural reason, not a lucky one:
`base_pipeline.py:149-151` rewrites `pipeline_ref.version`, and `:327-330` rewrites a **step** field.
Neither ever writes the `base_pipeline` field itself, which is the only row `_software_coverage:229`
reads.

**A consequence of the last two that this ruling creates and does not solve.** Two bases are now
classified as free text, and `_UNVERIFIABLE_GAP_BASES` is a `frozenset` of literals matched by
`_gap_base` (`cobidas.py:142-148`) splitting on the first `":"`. A free-text reason cannot be a member.
So either those two producers get stable base prefixes, or the classification cannot reach them and
they fall to "not reported" by default — which is the behaviour §2's reason exists to prevent. Recorded
as a defect of the producers, not of this rule. It also means §3b defect 5's blind spot is now
load-bearing: the AST guard cannot see the two reasons whose classification matters.

### Ruling 2 — Software keeps its own rule (R1)

*Reason.* The extension applies only to rows that **map to spec kinds**. Software maps to none
(`spec_kinds=()`, `cobidas.py:51`) and is already special-cased by `row_id` at `:254`, and
`_software_coverage` already carries both §4a and the deferral ruling. **R2 is rejected** because it
would quietly undo `DELTA_software_row_deferral.md`; the positive re-test stays in acceptance (§5.4)
so that rejection is enforced rather than remembered. R0 is rejected with it — an interpretation under
which Software can never be addressed is not an extension of §4a but a repeal of it.

### Ruling 3 — an unverifiable row gets its own tag in the report body

*Reason.* As things stand it inherits the never-examined tag, which is **false for it**: `_tag`
(`render.py:838`) reads only `covered_by_extractor`, and its own comment at `:837` claims the tag means
"no field on any mapping kind is targeted". The wording is chosen **by what is true for each reason
base** — the repository's standing rule, enumerate by truth of the rendered line, not by table economy
— so a base-specific line, not one generic string, if the bases differ in what they license saying.

### Ruling 4 — enforce the invariant: unverifiable implies not covered

*Reason.* `RowCoverage` is a frozen dataclass with no `__post_init__` (`cobidas.py:156-165`), so today
a row marked both `covered=True` and `unverifiable=True` is **silently ignored** — §3c case (2):
`render.py:770-771` draw from `mand_not_assessed` only, so the flag is never read, the row counts as
assessed, and the body prints a bare line. Check the invariant in `RowCoverage.__post_init__` and
mutation-test it. A frozen dataclass can still validate: raise in `__post_init__`.

### Ruling 5 — optional rows follow the same rule

*Reason.* One rule for every row that maps to spec kinds. §3c case (3) is the defect this closes:
a non-mandatory row is dropped at `render.py:761` before any counter, so an unverifiable optional row
is silent today. `intensity_normalization` is the row that can reach that state.

### 3g. The KB `not_applicable` reason is a third kind of thing, and today it leaks

*Measured 2026-10-19, prompted by a check on ruling 1's table.*

**First, the replay question, because it is the one with the poster attached. The old free-text string
is in ZERO stored JSONs.** Scanned all **360** stored JSONs under `extractor_mvp/results/` with Python
(the tree is gitignored, so shell recursion would skip it): `does not apply this step` → 0,
`KB-marked not_applicable` → 0, `couple_stages forbids` → 0. Positive control on the same scan:
`not_targeted_by_mvp` → 355 files, `extraction_quote_unresolved` → 67. So the leak in §3g has never
reached a stored report, and **replay cannot resurrect it** — the fix being in the producer is
therefore sufficient, with no re-extraction required. Consistent with the resolver being disabled in
every tracked config.

**What a field carrying it prints today.** The message has **no colon before its prose**, so
`_gap_base` returns the entire string as the base. That base is in **neither** `_REASON_BUCKET` nor
`_REASON_LINE`, so it falls through at `render.py:524` to `unclassified` and renders via `:537` as:

> `unspecified (reason: CCS 1.0.0 does not apply this step (KB-marked not_applicable; couple_stages
> forbids Missing/Deferred + NotApplicable so encoded as LeftMissing))`

That is a raw internal token in author-facing output — **including the words "couple_stages
forbids"** — which is precisely the defect `test_every_producible_reason_base_is_mapped` exists to
prevent (`test_render.py:725-731` names `value_numeric`, `extraction_quote_missing` and
`deferral_quote_unresolved` as the original instances). The guard cannot see this one because the
reason is free text, so the leak has been live and unguarded.

**And "claim about the paper" would be wrong in the other direction.** If the prefixed base were
classified as a paper claim it would land at "not reported", making the report say the author omitted
something **the KB says does not apply to their pipeline**. Neither bucket is true: the field is not a
gap in the paper and not a failure of the tool. It is `NotApplicable`.

**The root cause is in the producer's own comment.** `base_pipeline.py:313-314` says
`couple_stages forbids Missing/Deferred + NotApplicable so encoded as LeftMissing` — a
not-applicable fact was smuggled through the gap arm because the spec's five legal pairs
(`provenance.py:191-201`) have no slot for it. So this base is a gap reason only in encoding, never in
meaning.

**Consequence for the build, and it is forcing.** Ruling 6's prefix makes the base enumerable, so
`test_every_producible_reason_base_is_mapped` will **fail** until the base is present in both
`_REASON_BUCKET` and `_REASON_LINE`. A line has to be chosen now; it cannot be deferred.

#### RULED 2026-10-19 — the KB not-applicable line

*Ruled by the author in conversation, replacing my reading. Written down 2026-10-19, not backdated.*

- **Say it comes from AESPA's knowledge base, and that the paper did not report it**, in the same form
  as the existing inferred-version line — "AESPA inferred one, the paper did not report it"
  (`render.py:876-879`).
- **Name the pipeline.** If the version in the message was itself inferred by AESPA, say so; do not
  print `CCS 1.0.0` as though the paper stated it.
- **No internal tokens.**

**Row coverage: no new state.** A KB verdict is not a report, so the row falls to "not reported whether
performed", which is true — the paper did not say.

*Both citations, and a retracted objection of mine.* The ruling rests on
**`docs/DESIGN_cobidas_coverage.md`** (at `docs/`, not `docs/design/`; tracked; modified by `7748e7b`;
cited at `:28` and `:55` throughout this project), whose `:53` reads: "Only extraction-arm state. No
`INFERRED_DEFAULT` (an inferred value is not a *report*), no base-pipeline implication. Firewall
intact." Its implementation is `cobidas.py:239`. **Cite both — §2 as the ruling, `cobidas.py:239` as
the code.**

**RETRACTED:** an earlier draft of this section claimed that document does not exist. It does. My
search was `git grep "not a report"`, and the source italicises the word — `not a *report*` — so a
literal match was impossible. **The search had no positive control**, which is the one rule that would
have caught it, and it is a rule this document asserts twice elsewhere. A negative result from an
unverified detector is not a finding, and I filed one as a correction to a ruling. The control that
settles it: `git grep -n 'inferred value is not a' docs/` → one hit, `:53`.

The claim never reached a commit — it existed only in this untracked file, so nothing needs forward
correction. (Checked: `git grep` over `docs/TRACK_A_SCOPE.md` at `4145d44` finds no such statement.)

*A second-order consequence, which stands:* the not-applicable verdict is encoded as `LeftMissing`,
not `InferredDefault`, so §2's sentence does not *literally* cover it — the arm it travels in is the
gap arm. `TRACK_A_SCOPE.md` A7a records that gap. The ruling's conclusion holds; reaching it takes one
step more than the citation implies.

### Ruling 6 — the two KB free-text reasons get stable prefixes

**RULED 2026-10-19.** The reasons produced at `kb_client/base_pipeline.py:150` (the `KbAmbiguousError`
message) and `:310-316` (the KB `not_applicable` message) are given **stable prefixed bases**, so that
`_gap_base` can match them and the reason scan can see them.

*Reason.* Ruling 1 classifies both. Without stable bases that classification cannot apply — a
free-text reason has no base for `_gap_base` (`cobidas.py:142-148`) to split out and no literal for
`_UNVERIFIABLE_GAP_BASES` to hold — so both would fall to "not reported", which is the outcome §2
exists to prevent. It also lifts the guard blind spot in §3b defect 5 from "known and tolerated" to
"fixed", since a prefixed base is enumerable.

*Source and date.* Ruled by the author in conversation, written down 2026-10-19, not backdated.

*Scope note.* The root package (`src/fmri_repro/kb_client/`) owns these producers, so this is a change
to `fmri_repro`, not to `extractor_mvp`, and lands in its own commit ahead of the coverage change.

### What ruling 1 does to the gate prediction

**The prediction becomes `17 identical, 2 changed` — agtzidis_2020 and liu_2005, each on its
Intersubject registration row.** This supersedes §0's and §3d's `19 identical, 0 changed`, which held
only under the un-ruled set.

**And that change makes the prediction self-validating, which the old one was not.** §0 records that a
silently failed `PYTHONPATH` override also prints `19 identical`
(`rerender_reports.py:31-36`). A prediction of 19/0 is therefore indistinguishable from a broken gate.
A prediction of **17/2, with two named papers**, is not: a broken gate prints 19 identical and fails
the expectation immediately. Ruling 1 converts the acceptance criterion from one that could not fail
for the right reason into one that can.

---

## 4. The questions as they stood before §3f's rulings

### 4.1 The wording of the unverifiable line, in the body and the counters

Chosen by **whether the rendered line is true**, which is this repository's rule (`DESIGN_motion…` §5
records it as "enumerate by truth of the rendered line, not by table economy"), and explicitly not by
how few table entries it costs. Three surfaces need wording, per §3c: the conditional-list line (which
today reuses the never-targeted tag, and `_tag`'s comment at `:837` is false for this case), the
optional-rows line, and whether a `cov=True, unverif=True` row is reachable at all. Nothing pins any of
these today, so whatever is chosen is new text that must be asserted.

### 4.2 Whether the Software row keeps its own rule — and the reading that would silently overturn it

The precedence speaks of "the row's fields". **Software's `spec_kinds` is empty** (`cobidas.py:51`), so
three literal readings give three different gate results:

| reading | Software's fields | gate result | note |
|---|---|---|---|
| **R0** | `spec_kinds` = `()`, so nothing maps | `16 identical, 3 changed` — derosa_2025, liu_2013, oconnor_2017 | Software can never be addressed |
| **R1** | keep `_software_coverage`, swap only its base set | **`19 identical, 0 changed`** | the reading §0 and §3d use |
| **R2** | every row in the `base_pipeline` group | `8 identical, 11 changed` | **contradicts `cobidas.py:186-198`** |

**R2 would overturn the documented Software rule** — that a `DEFERRED_TO_CITATION` base_pipeline does
*not* address the row, and that the version arm answers it when a version row exists. That rule is
`DELTA_software_row_deferral.md`'s whole content. A DELTA framed as *extending* §4a must not silently
replace it, so this is the second thing that blocks implementation.

Also undecided and not assumed: when a step row becomes unverifiable, does it leave `covered` (and so
the *Assessed by AESPA* count) the way Software does? §3d's simulation assumed yes; on these 19 papers
the assumption never fires, so it is untested either way.

### 4.3 The nine unclassified reason bases

Listed, not assigned. `extraction_quote_unresolved` and the Software reading are the two that block;
the rest can be ruled later without re-running anything.

| base | why open |
|---|---|
| `extraction_quote_unresolved` | in `_UNVERIFIABLE_GAP_BASES` but not in the `render.py` "assert nothing" set; the two sources are scoped differently. **Decides this DELTA's entire corpus effect** |
| `value_not_numeric` | `render.py` contradicts itself (§3b defect 3); `cobidas.py` is silent |
| `version_deferred_to_kb` | `_build_version_pf` returns it in *every* non-EXTRACTED case, including quote failures, so one base covers conditions of both kinds |
| `not_targeted_by_mvp` | fits neither: the extractor never looked. `cobidas.py:161-163` deliberately keeps it apart from unverifiable. Formally makes all 19 papers contingent |
| `field_not_in_schema_version` | neither source names it; produced by `migrations.py:97-104`; its line is about the schema version, not the manuscript |
| `deferred_to_citation` | always paired with a `DeferredToCitation` extraction; `test_render.py:641-647` marks it unreachable for gap callouts |
| `citation_shaped_name_value_unsupported` | produced at `extractor.py:792` from a guard's inference, not a declared deferral; also marked unreachable for callouts |
| the `KbAmbiguousError` message | free text (`kb_client/base_pipeline.py:150`), not enumerable, invisible to the AST guard |
| the KB `not_applicable` message | free text (`:310-316`), same |

Deliberately excluded: `value_not_in_literal` is not produced by any current code (producer removed in
`382795a`) and survives only in migrated ≤0.4.1 documents.

---

## 5. Acceptance

1. **The re-render result is `17 identical, 2 changed`, and the two changed papers are `agtzidis_2020`
   and `liu_2005`** — the count *and* the explicit paper list, **read from stdout**, because `_differ`
   returns exit 0 either way (`rerender_reports.py:252`). A result of `19 identical` fails this
   criterion, whether it comes from a no-op implementation or a broken gate. Any other combination of
   rulings re-derives the number *before* the run, never explains it after.
2. **The negative control returns what the script's docstring records at that HEAD.** Still required,
   though ruling 1 removes the reason it was load-bearing: the expectation is no longer the string a
   broken gate prints (§0), so the control now guards against a different failure than the gate result
   itself does.
3. **A mutation test at each precedence level fails when that level is broken** — three mutations, each
   killing its own level and nothing else: break step 1 (an addressed row stops being addressed), break
   step 2 (an unverifiable row reads as not-reported), break the ordering (step 2 consulted before
   step 1, so an addressed row with one unverifiable field reads unverifiable).
4. **The Software row's behaviour is unchanged and pinned.** `test_cobidas.py:226` and `:267` pass
   untouched, and `DELTA_software_row_deferral.md`'s rule is re-asserted — not merely unbroken but
   positively tested, because §4.2's R2 reading would break it silently.
5. **`test_cobidas.py:280-293` is replaced rather than deleted**, by a test asserting the new rule on
   the same non-Software input it already carries. A superseded guard that simply disappears leaves the
   property it protected unguarded.
6. **The three body surfaces in §3c are each asserted** — the conditional-list line, the optional-rows
   line, and `_tag`'s behaviour for an unverifiable row — since no test pins any of them today
   (rulings 3 and 5).
7. **The invariant is enforced and mutation-tested** (ruling 4): constructing a `RowCoverage` with
   `covered_by_extractor=True, unverifiable=True` raises, and a mutation removing the check fails a
   test. Without the mutation the check is unguarded, and §3c case (2) shows that state is currently
   silent rather than loud.
8. **Every classified reason base is asserted against its classification** (ruling 1's table), so a
   base cannot be silently reclassified by editing one `frozenset`. **Both prefixed KB bases are
   produced, classified per the DELTA's verdicts, matched by `_gap_base`, and visible to the reason
   scan** (ruling 6) — not merely recorded as unreachable.
9. **The demo reports are regenerated by replay after this lands**, per `TRACK_A_SCOPE.md`'s standing
   condition. They are already 16/19 stale, and this change alters the coverage block, so leaving them
   is leaving a known-wrong artifact that a reader may meet.

---

## 6. Not settled here

- **Nothing in §4 blocks implementation any more.** §3f's rulings close §4.1 (ruling 3), §4.2
  (ruling 2) and §4.3 (ruling 1 plus the eight-base table). §4 is kept as the evidence each was ruled
  against.
- **Whether the KB producer may rewrite a field the extractor never targeted.** OPENED 2026-10-19,
  checked, no fix in this build. `_apply_param_result` (`kb_client/base_pipeline.py:287-331`) guards
  only on `if current_pf.extraction.status == "EXTRACTED": return` (`:301`) — there is **no** guard on
  the inference arm, verified by AST walk: zero guards in that function mention `not_targeted_by_mvp`
  or the inference arm at all. An untargeted field is `MISSING_FROM_PAPER`, so the guard does not fire
  and the producer replaces its inference. The reason then stops being `not_targeted_by_mvp`, and
  `_row_covered_by_extractor` (`cobidas.py:171`) returns True — **so the row reads as covered on a KB
  inference alone, for a field the extractor never looked at.** Unexercised in the corpus (the resolver
  is disabled in every tracked config), which is why it is an item and not a blocker.
- **Whether a deferral the `extractor.py:792` guard INFERS from an unsupported citation-shaped value
  should count as a deferral at all.** OPENED 2026-10-19 by the membership criterion above. The guard
  turns a value it could not support into a `DEFERRED_TO_CITATION` extraction, which step 1 then reads
  as a report — so `viduarre_2017`'s Software row is "addressed-shaped" on the strength of an
  inference, not of a deferral the model declared. Keeping `citation_shaped_name_value_unsupported`
  out of the gap set is correct *given* that the field is a deferral; whether it should be one is a
  separate question, and ruling on it would change `viduarre_2017`. Not settled here, and it does not
  block this DELTA.
- **Whether an unverifiable step row leaves `covered`** (§4.2, last paragraph). Unexercised by the 19.
- **Whether optional rows get the same treatment.** §3c shows they are dropped at `render.py:761`
  before any counter, so today an unverifiable optional row is silent. `intensity_normalization` is the
  one that can reach this state.
- **The corpus-size discrepancy: RECONCILED 2026-10-19, and 359 is correct.** Re-measured directly:
  **364** `Preprocessing`-shaped blocks exist under `extractor_mvp/results/`, **359 validate**, and
  **5 fail** — all `MigrationError: document source schema 0.1.0 is below the migration floor 0.2.0`,
  in `batch_reextract/papers/liu_2013.json`, `batch_sfn_v2/papers/viduarre_2017.json`,
  `batch_sfn_v3/papers/liu_2013.json`, `batch_sfn_v4/papers/viduarre_2017.json` and
  `batch_sfn_v5/papers/viduarre_2017.json`. 359 is a count of **blocks, not files**, which is why it
  exceeds the 347 JSONs carrying a top-level `preprocessing`: four multi-acquisition files hold several
  (`batch_multi_acq/papers/`: cho_2021 ×4, greene_2022 ×3, marek_2022 ×3, yang_2025 ×3). The earlier
  **340** was a glob artifact and its "11 failures" was wrong; the denominator is now stated at
  `DESIGN_motion_correction_extraction.md:659`.
- *(Closed by ruling 6: the two KB bases get stable prefixes, in their own commit.)*
- **The five defects in §3b.** They are in the two sources an implementer will consult, and they are
  recorded here rather than fixed, since three of them (the stale locators, the self-contradiction about
  `value_not_numeric`, the overclaiming guard docstring) are corrections to other documents' and tests'
  text.
