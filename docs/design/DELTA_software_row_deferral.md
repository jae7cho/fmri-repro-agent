# DELTA — a deferral does not address the Software row

*Refinement of `cobidas._software_coverage` (design doc: `DESIGN_cobidas_coverage.md`;
criterion: `docs/findings/cobidas-version-criterion.md`). Ratified 2026-09-07. Not implemented;
this document is the record the implementation follows.*

---

## 0. Scoping constraint, before anything else

`_ADDRESSING_STATUSES` (`cobidas.py:120`) is read at **two** sites:

| Site | Rows affected |
|---|---|
| `cobidas.py:181` | the Software row only, on the no-version-row fallback |
| `cobidas.py:205` | each of the other 15 D.3 rows |

**This delta changes `cobidas.py:181` only.** Its warrant is §4.3's *Software versions*
paragraph, which speaks to versions and says nothing about the other 15 rows.

Removing `DEFERRED_TO_CITATION` from the frozenset would look like a one-line edit and would
silently re-rule every conditional row. That reverses CALL 1, a ratified protocol call recorded
at `DEVLOG.md:642` ("deferred is not a reporting failure") and pinned by
`test_deferred_to_citation_addresses_row` (`test_cobidas.py:84-86`), where a deferred
coregistration field correctly addresses its row. For those 15 rows a deferral remains a
report. The Software row differs because its mandatory content is not "was this performed" but
version and revision number (`cobidas.py:13-14`).

## 1. What is ruled

A paper that defers its pipeline to a citation does **not** address the Software row. When the
`base_pipeline` arm is `DEFERRED_TO_CITATION` and no version row exists, `addressed` is `False`.

The report continues to say something about such a paper. What changes is the predicate, not
whether the paper is discussed.

## 2. Why: one boolean carrying two questions

`addressed` currently answers *did the paper say something about its software?* The row's
mandatory content asks *did the paper give the version and revision number?* A deferring paper
answers the first and not the second, and one boolean cannot hold both answers.

This is the same shape as the reason-partition problem `DELTA_protocol_reason_partition.md`
solved for the completeness header: a single bucket spanning categorically different states.

## 3. The warrant

`docs/findings/cobidas-version-criterion.md` records the criterion. Three points bear directly:

1. §4.3 states the version requirement for all tools involved in the analysis, with no
   deferral clause attached.
2. The one citation-like mechanism §4.3 raises under *Software versions* is the RRID, and it is
   recommended **in addition to** reporting the version. The standard has a way to say
   "citation instead of" and does not use it here.
3. The parenthetical permitting a peer-reviewed citation in place of explicit detail sits under
   *In-house pipelines & software* and is scoped to processing steps and operations, not to
   version identity.

Two prior repository statements agree and are restored rather than overturned:

- `docs/DESIGN_cobidas_coverage.md:55` already stated the rule as "the row is ADDRESSED iff
  `base_pipeline.version` is `EXTRACTED`", adding that an inferred version does not address it
  because "COBIDAS asks the author to report, not the tool to guess". A citation is likewise
  not the author reporting.
- `docs/findings/span-resolution-fix.md:38-39` ruled viduarre's deferral "COBIDAS
  §4.3-legitimate" for pipeline identity while stating that "what is actually missing is the
  *version*". That is exactly the split this delta encodes.

**Bounded negative.** §4.3 was read in full across pp. 10-11 and contains no passage licensing
citation-substitution for a version. The rest of the Report was not read, so this is a
statement about §4.3 rather than about the standard as a whole.

## 4. A3's diagnosis stands; its repair is superseded

`c9c2951` (A3) identified a real defect: the report accused braun_2015 and viduarre_2017, both
of which cite their pipelines, of an unconditional COBIDAS violation. That diagnosis is correct
and is not disturbed here.

A3 repaired it by making the row *addressed*. This delta holds that the row is unaddressed and
that the **accusation wording** was the false part. "Software: version and revision number NOT
REPORTED — COBIDAS D.3 requires this for each software used" is not a fair description of a
paper that cited a peer-reviewed pipeline. "Version not reported; pipeline identity deferred to
\<citation\>" is accurate, is what §4.3 supports, and is not an over-accusation.

Same evidence, same two papers, different repair.

## 5. The current decision table, made explicit

Recorded here because the predicate is not legible from its call site. `_software_coverage` is
four branches behind a 33-line docstring, and its consumer at `render.py:793` is a two-clause
condition (`software.covered_by_extractor and not software.addressed`) that reveals none of it.
Four separate errors during this design were made by reasoning from the call site rather than
the definition.

Section emitted iff `covered ∧ ¬addressed`.

| # | Condition | Source | covered | addressed (now) | addressed (ruled) | Section (ruled) |
|---|---|---|---|---|---|---|
| B1 | `base_pipeline` is `NotApplicable` (no `extraction` key; sentinel row carries no status) | `cobidas.py:175-176` | False | False | unchanged | absent |
| B2 | `left_missing_reason == "not_targeted_by_mvp"` | `cobidas.py:177-178` | False | False | unchanged | absent |
| B3a | version row exists, version status `EXTRACTED` | `cobidas.py:179-180` | True | True | unchanged | absent |
| B3b | version row exists, version status not `EXTRACTED` | `cobidas.py:179-180` | True | False | unchanged | PRESENT |
| B4a | no version row, base `EXTRACTED` | `cobidas.py:181` | True | True | unchanged | absent |
| **B4b** | **no version row, base `DEFERRED_TO_CITATION`** | `cobidas.py:181` | True | **True** | **False** | **PRESENT** |
| B4c | no version row, base `MISSING_FROM_PAPER` | `cobidas.py:181` | True | False | unchanged | PRESENT |

A version row exists iff the outer arm resolves a `PipelineRef`, which is `EXTRACTED` extraction
or `INFERRED_DEFAULT` inference (`render.py:265-271`, `render.py:187-193`). B4a is therefore
unreachable outright rather than merely unobserved: `base_pipeline` is typed
`ProvenancedField[PipelineRef] | NotApplicable` (`preprocessing.py:1306`), so an `EXTRACTED`
extraction arm always carries a `PipelineRef` and always produces a version row, routing to B3.
B2 is documented unreachable at `cobidas.py:161-164`.

Note the reader-side path with no writer: nothing in the extraction path sets `base_pipeline`'s
own inference arm to `INFERRED_DEFAULT`, so a deferred-base paper cannot currently reach B3 by
that route. `_get_pipeline_ref` (`kb_client/base_pipeline.py:221-233`) reads the possibility;
the only `InferredDefault[PipelineRef]` construction in the tree is a hand-authored example
script. That also makes the `NotApplicable` demotion at `kb_client/base_pipeline.py:139`
unreachable from a batch, since it requires the same arm.

## 6. Blast radius

Two of 19 papers change: braun_2015 and viduarre_2017, both B4b. The other 17 route through
B3a, B3b, or B4c and are untouched. The predicted partition for the corpus moves from 14
present / 5 absent to **16 present / 3 absent**.

Two is this corpus's count, not the change's extent. The rule is general: any paper whose base
pipeline is deferred and whose version row is absent moves to PRESENT, and A4's PDF-to-report
entry point will apply it to papers outside the corpus.

**No re-extraction is required.** `to_report` is deterministic and pure, and the four
`MethodsSlice` fields `to_protocol` reads (`suspicious`, `found_via`, `slice_ratio`,
`ended_at`, at `render.py:632-642`) are all persisted in `extraction_json["methods"]`
(`batch.py:244-250`). A re-render from the stored per-paper JSON reproduces a report exactly,
so this delta costs a re-render and no model calls.

The re-render tool is to be built reproduce-then-change: re-rendering all 19 at HEAD **before**
the predicate changes must produce 19 byte-identical files. Until that identity check passes, a
two-paper diff after the change is not attributable to the change.

## 7. Superseded artifacts

Both are in `extractor_mvp/tests/test_cobidas.py`. Neither was wrong when written; both were
correct under A3's ruling.

**`test_deferred_pipeline_is_not_a_software_violation` (`test_cobidas.py:155`)** is superseded
in full, including its name, which asserts the ruling being reversed. Its docstring records the
diagnosis that still stands:

> Regression guard for shipped behaviour: keying software coverage off the version row alone
> left a deferral unaddressed, so the report accused a citing paper of an unconditional COBIDAS
> violation. It fired on real corpus papers (braun_2015 … also viduarre_2017).

The successor states the ruling positively so it cannot be mistaken for the old assertion under
a new body: **`test_deferred_pipeline_addresses_identity_not_version`**.

**`test_software_coverage_over_every_base_pipeline_state` (`test_cobidas.py:109`)** keeps its
name and its six rows. Row D (`test_cobidas.py:135`), the `DEFERRED_TO_CITATION` case, has its
expected `addressed` flip from `True` to `False`. Rows A, B, C, E, and F are unchanged.

`test_render.py:981` and `test_assemble_v0_3_0.py:73` are **not** affected: their fixtures are
chen_2015 (B3b) and an `_assemble` output with a `MissingFromPaper` base (B4c), neither of which
routes through B4b.

## 8. Not settled here

- The exact replacement wording for the deferral case, and whether it is reported under the
  existing `### Not reported (mandatory, unconditional)` heading or a new one. The heading
  currently carries a single sentence written for the unnamed-software case.
- Whether `Pipeline named:` versus the bare `No version reported by the paper.` variant
  should also diverge by author action. A paper that named no software at all is currently told
  its version is missing, when the action it needs is to name the software. A separate wording
  question recorded against Goal 1.
