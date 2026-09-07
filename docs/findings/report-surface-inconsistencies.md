# Report-surface inconsistencies

**Scope.** Four observations about what `render.to_report` emits, recorded at HEAD on
2026-09-07 and verified against a 19-paper corpus run of the same date, configured by
`extractor_mvp/configs/batch_a1_acceptance_config.yaml`. None is fixed here.
Source line numbers were accurate when written and should be checked at HEAD before being
relied on.

## 1. No version stamp reaches report output

The report's only header is its title (`render.py:629`), which carries the paper id and
nothing else. `__version__ = "0.0.1"` exists at `extractor_mvp/src/extractor_mvp/__init__.py:14`
and `extractor_mvp/pyproject.toml:7`, and is referenced by neither `render.py` nor `batch.py`.

A report therefore cannot be traced to the code that produced it. Two reports for the same
paper generated from different commits are indistinguishable on their face, which matters
because the emitter's behavior has changed three times in the commits `d90507b`, `c9c2951`,
and `214b55c`.

## 2. `value_not_numeric` renders under a header that contradicts its own reason line

Four sites, two readings:

| Site | Text |
|---|---|
| `render.py:463` | bucket assignment: `value_not_numeric` → `unmappable` |
| `render.py:500` | header for that bucket: "reported but unmappable to controlled vocabulary" |
| `render.py:486` | per-field line: "extractor returned a non-numeric value for this field" |
| `render.py:482-484` | comment: these reasons fire before quote validation and "assert nothing about what the manuscript reports" |

The completeness header asserts the paper reported a value that could not be mapped. The
per-field line and the comment above it say nothing has confirmed the paper reported anything.
Both statements are about the manuscript and they disagree.

`extraction_quote_missing` and `deferral_quote_unresolved` share the same comment and bucket to
`not_covered`, where no such contradiction arises. Only `value_not_numeric` buckets to
`unmappable`.

## 3. Three emitted strings for one fact

For "the extractor did not examine this row", the report emits three different strings:

| Site | Surface | Text |
|---|---|---|
| `render.py:476` | per-field callout | "not examined by the extractor — check the source yourself" |
| `render.py:784` | COBIDAS row tag | "(no fields assessed by current extractor)" |
| `render.py:769` | COBIDAS header counter | "Not assessed by AESPA: N" |

A fourth string, "not assessed by current extractor", is not emitted anywhere. It survives as a
comment at `render.py:782` and in `DEVLOG.md` and `docs/design/DESIGN_anatomical_steps_v0_3_0.md`
as a description of output that no longer exists under that wording.

Unifying the three is not a free rename. `extractor_mvp/tests/test_render.py:981` asserts
`out.count("not examined by the extractor") == 8` and
`extractor_mvp/tests/test_assemble_v0_3_0.py:73` asserts `== 19`. Both count the bare string
globally across the whole report, and both pass only because the other two surfaces use
different words. Whether that divergence was chosen or fallen into is not recorded anywhere in
the repository.

## 4. `NotApplicable`: one value, two meanings, one constructor

`cobidas.py:167` states that `NotApplicable` "has TWO producers meaning opposite things". The
consequence it draws is correct and the wording is not.

At HEAD there is one production constructor of a `base_pipeline`-level `NotApplicable`:
`src/fmri_repro/kb_client/base_pipeline.py:139`, reached when `recognize()` does not know a
pipeline the paper did name. The from-scratch meaning arrives from authored spec input and is
exercised only by tests; `rg 'base_pipeline\s*=\s*NotApplicable'` finds no other non-test
construction site.

`render.flatten` consumes the value (`render.py:253`) and emits a display-state row
(`render.py:259`). It constructs nothing.

The reasoning at `cobidas.py:166-173` holds unchanged: the value cannot distinguish a
hand-rolled pipeline from an unrecognized named one, so `_software_coverage` returns
`(False, False)` and the report says nothing rather than accusing an author. What is imprecise
is only the count of producers, which matters because a reader looking for the second
constructor will not find one.
