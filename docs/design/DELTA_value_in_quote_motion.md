# DELTA — a value-in-quote check for `motion_correction.method`

*Design only. **Nothing here is implemented, and this file is not staged.** It records the facts the
2026-10-22 run and a code read established on 2026-10-25, and states four forks the author has to rule
on before anything is built. Every locator below was verified against the working tree on 2026-10-25;
every count was produced by a command over the per-draw records, by explicit path, and no quote or
value text is reproduced here.*

---

## 0. Scoping constraint

The three held-out papers (liu_2005, tang_2025, wheaton_2004 — prereg C11/C26) were not read, loaded or
searched. Every count below is on probe papers, all inside the contaminated union of 16, two of them
(derosa_2025, poldrack_2015) fitted by the stanza itself. Nothing here is an accuracy figure and nothing
may be derived into one.

## 1. The finding (Part B of the 2026-10-25 instruction)

### 1a. Fourteen tool-name draws returned a value their own quote does not contain

Over the 2026-10-22 run (stanza `378a294f…`, `extractor_mvp/results/motion_probe_v2/motion_probe/*.jsonl`),
for every draw whose raw value the frozen heuristic classes `tool_name`, exact substring of the raw
value in the raw `verbatim_quote`:

| paper | `tool_name` draws | value in its quote | not in its quote | where the quote sits |
|---|---|---|---|---|
| agtzidis_2020 | 10 | **1** — the one draw whose quote failed to resolve (its longer quote starts two sentences earlier, where the package is named) | **9** — all resolved; spans 7188–7308 ×5, 7210–7274 ×2, 7086–7308 ×2, i.e. the realignment clause the v1 run quoted for its operation phrases | the step clause; the package is two sentences away |
| binder_1999 | 5 | 0 | **5** — all span 11023–11180, the Cox 1996b sentence | the package is named ~1,600 characters later, for Talairach projection, cited to Cox 1996a |
| ciric_2017 | 10 | **10** | 0 | span 4410–4507, the ESTIMATE clause |
| derosa_2025 | 10 | **10** | 0 | span 8801–9045; the quote really does name ICA-AROMA |
| power, liu_2013, poldrack | 0 | — | — | — |

Normalised (whitespace-collapsed, case-folded) substring gives the same 14/0/10/10. A positive control
that the check is live: ciric's first draw finds its value at quote offset 64.

**So the author's prediction holds exactly:** a value-must-appear-in-quote rule rejects all 14 of the
agtzidis/binder tool draws that resolved, passes all 10 of ciric's, and passes all 10 of derosa's —
it cannot fix derosa, because derosa's quote does name ICA-AROMA. The one agtzidis draw the rule would
*pass* is the one span resolution already discards.

The same shape was present once in the v1 run: agtzidis's single `SPM12` draw on 2026-10-21 also
quotes a sentence that does not contain `SPM12` (and that quote did not resolve either).

### 1b. The motion call does not run the value-support guard the main call has

The repository already has this check. `extractor_mvp/src/extractor_mvp/span_resolver.py:400`
`quote_supports_value(value, quote)` — "True iff `value` (or a first-use variant) appears in `quote` as a
run of WHOLE tokens", NFKD + lowercase normalised, token-boundary not substring (the substring hole is
`docs/findings/value-support-guard-substring-hole.md`). It is imported at `extractor.py:68` and called in
exactly two places:

- `extractor.py:677`, in `_build_version_pf` (`:655`) — the paper-stated `base_pipeline.version`;
- `extractor.py:778`, in `_build_base_pipeline` — the pipeline name, with the scope stated at
  `:759-770`: *"the value-support check runs UNCONDITIONALLY on every extracted base_pipeline … Scope:
  base_pipeline only (step-field recoveries stay span_recovered-only, not value-guarded)."*

The motion call (`extract_motion_method`, `extractor.py:1186`) hands its `FieldExtractionResult` to
`_process_field` at `:1231-1243`. `_process_field` (`:481`) resolves the quote at `:569`
(`resolve_quote`), drops the field at `:574-583` only when the span is not found, and otherwise builds
`Extracted` at `:585`. There is no call to `quote_supports_value` between `:481` and `:590` (checked by
scanning that range; the two real calls at `:677` and `:778` are the positive control that the scan
finds calls where they exist). The omission is stated where it happens, `:571-573`:

> Step fields are marked-only in this release (no value-support guard here; that guard is
> base_pipeline-scoped — see _build_base_pipeline).

**The reason the build recorded.** `docs/findings/span-resolution-fix.md:27-29`, the correction of
record for v0.4.0: *"(2) base_pipeline-scoped. … Step-field recoveries in `_process_field` are marked
`span_recovered=True` but NOT value-guarded (value-mislocalization was diagnosed only at
`base_pipeline`; derosa's `temporal_standardization` is a referent-binding problem handled by the
temporal firewall …)."* The guard shipped in `2560bb1` (2026-07-13; `DEVLOG.md:26`), scoped to
recovered spans; `efbe14a` made it unconditional on `base_pipeline` after viduarre's clean-span
fabrication (`DEVLOG.md:261-270`). The step-field exclusion was a scoping judgement from the evidence
then available — value-mislocalisation had been seen only on pipeline names — not a ruling that step
fields must stay unguarded. The motion probe is the first step-field evidence of the same failure.

### 1c. What the existing guard would do, applied unchanged to every motion draw

Run over every extracted draw of both runs (counts; "PASS" = `quote_supports_value` true):

| run | paper | class | PASS | REJECT | what the rejects are |
|---|---|---|---|---|---|
| v1 | agtzidis | operation_phrase | 8 | 1 | an inflected form of the quoted verb |
| v1 | agtzidis | tool_name | 0 | 1 | the `SPM12` draw |
| v1 | poldrack | operation_phrase | 9 | 1 | inflected form |
| v1 | binder, derosa, liu_2013, power | all | 10 each | 0 | — |
| v2 | agtzidis | tool_name | 1 | 9 | the cross-sentence `SPM12` draws |
| v2 | binder | tool_name | 0 | 5 | the cross-sentence `AFNI` draws |
| v2 | binder | undecided | 3 | 0 | includes the bare-citation value: token match passes it, substring would not |
| v2 | binder | operation_phrase | 1 | 1 | a nominalised form of the quoted verb |
| v2 | poldrack | operation_phrase | 5 | 5 | `realignment` against a quote that says `realigned` |
| v2 | ciric, derosa, liu_2013, power | all | 10 each | 0 | — |

Two things this table settles before any fork is argued. First, on **tool names** the existing guard
and the author's substring rule agree draw for draw (14 reject, 20 pass). Second, on **operation
phrases** the guard is not neutral: the stanza says the value is "copied from the text", the model
sometimes returns an inflection instead, and whole-token matching rejects those — **8** draws across the
two runs: poldrack 6 (v1 draw 7; v2 draws 1, 2, 4, 7, 10), agtzidis 1 (v1 draw 8), binder 1 (v2 draw
10, a nominalisation). *Corrected 2026-10-26: the first version of this paragraph, and the 2026-10-25
report built on it, said 6 and "5 of them poldrack's"; the table above always summed to 8, and the
prose had been written from memory of it.* That is the cost side of fork 3 below, measured rather than
guessed.

## 2. The four forks — stated, not resolved

### Fork 1 — a validator that reasks, or a post-check on the processed layer

- **Validator (pydantic, on `MotionMethodExtraction`):** an unsupported value fails validation, instructor
  reasks, the model gets a second completion. Changes the **raw output distribution** — reasks are
  counted per draw (`motion_probe.py` records `completion_attempts`), fork 1 of `DESIGN_kdraw_stability.md`
  — so every number after it is a **new vintage**, and the probe's "0 reasks" line stops being a
  property of the stanza alone.
- **Post-check in `_process_field` (or a motion-only wrapper):** the raw record is untouched; the
  processed layer demotes an unsupported value. The prereg's rows are computed from raw `status` and
  raw `value` (Amendment 2 ruling 2), so **state-map rows do not move**; what moves is the processed
  `Extracted`/`MissingFromPaper` arm and anything downstream of it (coverage, the report). This is the
  shape the `base_pipeline` guard has.
- Cuts across both: **what the rejected draw becomes.** `_build_base_pipeline` reclassifies an
  unsupported citation-shaped quote to a deferral (`:793-810`) and otherwise falls to MISSING. For motion
  the candidates are MISSING with a greppable reason (the honest minimum), or a `described_only`-shaped
  `Extracted` whose value is drawn from the quote — which would be the code choosing a value the model
  did not emit. Not decided here.

### Fork 2 — exact or normalised match

- **Exact substring** (the author's statement of the rule): rejects the 14, passes 20; also rejects
  binder's bare-citation value because of punctuation.
- **Whole-token normalised** (`quote_supports_value` as it exists): same 14/20 on tool names; passes the
  bare-citation value; rejects inflections. Reuse means one guard with one hole-history
  (`value-support-guard-substring-hole.md`) rather than two.
- Neither matches an inflection to its stem, and the stanza's "copied from the text" instruction is the
  thing an inflection violates — so fork 2 and fork 3 are not independent.

### Fork 3 — tool names only, or every motion value

- **Tool names only** (gate on the heuristic's `tool_name` class, or on the resolver's `named_tool`
  side): catches the 14, touches no operation phrase, leaves the 6 inflected phrases as they are. Couples
  the guard to the frozen heuristic (C21), which was written as a *scoring* instrument, not an
  extraction-time gate.
- **Every value:** one rule, no coupling to the heuristic, and the 6 inflected phrases are demoted —
  arguably correctly (the stanza asked for a copy), arguably not (the paper did perform the step and
  the phrase is a paraphrase of its own words). poldrack moves from 10 row-1 draws to 5 processed
  extractions either way the row is read; on the raw layer nothing moves.
- `undecided` values (binder's algorithm description, the bare citation) pass both ways as the
  guard stands.

### Fork 4 — whether the same check routes the D.3 structured-noise tools

- **No, by construction:** derosa's quote names ICA-AROMA, so any value-in-quote check passes it
  (10 of 10 in both runs). Routing CompCor / ICA-FIX / ICA-AROMA off the method is a **different
  mechanism** — a row-routing table keyed on COBIDAS D.3 p.57's list — not a stricter support check.
- **The prompt already says it and the model overrode it** (v2: 10 of 10 after the STEP 3 edit), which
  is the `temporal-firewall-fix.md` shape; a post-hoc table would be the first time this project
  routes a value by name in code rather than by instruction, and CALL 10 says not to add a role arm by
  default. Whether that table is the right home, or derosa is accepted as the CALL 4 error class and
  scored as such, is the author's call and sits beside Amendment 4's held deferral line.
- If both a support check and a routing table existed, their **order** matters: route first and the
  routed draw becomes `described_only`-shaped with a value the code chose (fork 1's third bullet);
  check first and derosa passes into the router unchanged.

## 3. What a build would have to carry, whichever way the forks go

- A dated note at `extractor.py:571-573` superseding "marked-only", citing this DELTA and the two runs.
- Tests on the 14/20 partition **without quoting paper text** — the fixture strings must be synthetic,
  as `test_motion_value_kind.py` does with prereg strings.
- A vintage statement: fork 1's validator path re-vintages every motion number; the post-check path
  leaves the raw layer and the state-map rows as they are and re-vintages the processed layer only.
- A re-read of the v1 and v2 records under the chosen rule, reported as counts beside the originals,
  never replacing them.

---

## 4. Rulings — 2026-10-26, by the author, recorded the day they were given

*Sourced to the author's instruction of 2026-10-26, not backdated. The forks in §2 are left as written
above so the alternatives stay visible; this section is what was decided. No build yet.*

**Ruling 1 — a post-check on the processed layer; no reask.** A reask that tells the model "the value is
not in the quote" invites it to quote the host sentence instead ("performed with SPM12 …"), which passes
the guard with the binding still wrong. That outcome is already in the record: **three agtzidis draws
quote text containing `SPM12`** — v2 draw 6, and A/B `378a` draws 1 and 10 — all three the long quote
form that begins at the sentence naming the package, all three unresolved. Checking after the fact also
leaves the raw outputs untouched, so v1, v2 and the same-day A/B stay comparable with whatever comes
after. The reask option in fork 1 is closed.

**Rulings 2 and 3 — every motion value, with an inflection-tolerant match.** A tool-names-only scope
would need the scoring heuristic's lists (`scripts/motion_value_kind.py`) at extraction time; the guard
and the scorer would then share one list's blind spots, and a tool absent from the list would pass both.
So the check runs on every motion value, and the match tolerates word forms (`realignment` against a
quote that says `realigned`). **Acceptance, to be met by a replay over all 170 recorded draws** (v1 60,
v2 70, A/B 40):

- it **rejects the 30 cross-sentence carries** — the resolved tool-name draws whose value is not in
  their quote: v2 agtzidis draws 1, 2, 3, 4, 5, 7, 8, 9, 10; v2 binder 1, 2, 3, 4, 6; A/B `378a`
  agtzidis 2–9; A/B `378a` binder 1, 2, 3, 4, 6, 7, 8, 9. (A 31st, v1 agtzidis draw 4, is the same shape
  but unresolved, so span resolution already drops it; it is listed so the count is checkable.)
- it **passes every inflected operation phrase** — the **8** known, listed in §1c (not the 6 the
  2026-10-25 report said; corrected above);
- it **lists any other change** across the 170, each by run and draw id.

**Ruling 4 — route CompCor, ICA-FIX and ICA-AROMA off the motion method, in code, with their own
reason.** COBIDAS D.3 p.57 lists them under *Artifact and structured noise removal*. The prompt cannot
steer the model off them: the STEP 3 edit of 2026-10-22 named them and derosa returned `ICA-AROMA` on
all 20 draws across both stanzas (v2 and the A/B are not derosa runs; the count is v1's 10 under `56bc`
plus v2's 10 under `378a`). **derosa is the fitted case** — the stanza was edited to handle its tool and
the code rule is written against the same paper — and every derosa count under the rule is reported as
fitted, not independent.

**Both new reasons are classified under the conditional-row rule, deliberately.** The reason strings the
two rules emit go through `cobidas.py`'s coverage precedence — addressed, then unverifiable, then not
reported (`cobidas.py:297-298`) — and a gap reason **not** in `_UNVERIFIABLE_GAP_BASES`
(`cobidas.py:150-162`; membership criterion `:133-148`, ruled 2026-10-19) renders the row as *not
reported*. So each reason is placed in or out of that set on purpose when it is built, never by default.
Recorded as this author's reading, not a ruling: both are "the extractor looked, found something, and
could not credit it", which is the set's definition; leaving derosa's routed reason out would render its
motion row *not reported* while the paper asserts the operation, the overclaim the rule exists to stop.

**Recorded limit.** The guard cannot catch a tool quoted from its own host sentence — a quote of
"performed with SPM12 …" supports `SPM12`, binding or no binding. That remains CALL 1's job (the
binding test, protocol v1.5/v1.6), and no value-in-quote rule reaches it.

**Status.** No build yet. When built: the dated note at `extractor.py:571-573`, synthetic test strings,
the 170-draw replay reported as counts beside the originals, and the vintage statement from §3 — under
ruling 1 the raw layer and the state-map rows do not move, and only the processed layer re-vintages.

---

**Ruling 5 — 2026-10-26 (late night), by the author, before the version-6 commit: a letter-ending
value may be followed by a digit run in the quote; under-claim only.** The text layer attaches
citation numbers to the word before them (`AFNI48`, `Louis45`), so a package-level value such as
`AFNI` against the sentence that names the package would fail the digit-exact matcher of rulings 2–3
and demote a correct cole report. The rule, in `quote_support.token_equivalent` (shared with the
step-field check): a token ending in a letter is matched by the quote's token when that token is the
value plus a digit run. It only ever lets a value under-claim (`AFNI` / `AFNI48`, `SPM` / `SPM12`);
the reverse is never tolerated, and a value that ends in a digit still matches exactly (`SPM8` is not
`SPM12`; `mni152` is not `mni152nlin6asym`). Recorded here because it is the motion check's rule;
the step-field DELTA carries a dated note under its ruling 5.

**Ruling 6 — 2026-10-27, by the author (prereg Amendment 11): the routing fallback, and the
attribution level derived on the processed layer.** Ruling 4 routes CompCor, ICA-FIX and ICA-AROMA
off the method and leaves the field `MissingFromPaper`. From version 7, when the routed tool's **own
quote names exactly one listed package** (protocol v1.8's realignment-capable list, by token; a
digit run after the name tolerated as in ruling 5; SPM keeps its version digits, the others return
the bare name) **the processed value is that package**, on the same span, attribution `package`, and
the diagnostic carries its own reason, `motion_value_routed_fallback_to_package:<tool>-><package>`.
The raw layer is untouched; the field stays `EXTRACTED`, so no new gap reason enters
`cobidas._UNVERIFIABLE_GAP_BASES`. With it, the attribution level that version 6 asked of the model
is **derived in code**: `attribution_from_quote` returns `step` if the quoted sentence carries one of
the frozen heuristic's eleven operation phrases, else `package`; a fallback draw is `package` by
construction. Reported against the labels' column R as agreement counts, diagnostic, never scored.
Replay over every recorded draw: §5.

## 5. Built — 2026-10-26

Implemented as `extractor_mvp/src/extractor_mvp/motion_guard.py` (pure functions:
`quote_supports_value_inflected`, `structured_noise_tool`, `motion_post_check`), applied in
`extract_motion_method` after `_process_field` returns, with two literal-prefixed reasons so
`test_render.py`'s reason scan sees both; both bases are in `cobidas._UNVERIFIABLE_GAP_BASES` and in
render's bucket and wording tables; the dated note sits at `extractor.py:571-573`'s comment. Tests:
`tests/test_motion_guard.py` (synthetic strings only), mutation-checked on eight paths. Acceptance: the
180-draw replay (`scripts/motion_guard_replay.py`; `docs/findings/motion-value-in-quote-replay.md`)
rejects the 30 carries, routes derosa's 20, keeps ciric's 20 and the 8 inflected phrases, and lists
no other change. Identity gate against HEAD: 19 identical (no stored JSON carries a motion step);
negative control against `d31e8b7`: 19 changed, as derived beforehand. The vintage statement of §3
holds: raw outputs and state-map rows are untouched; the processed layer is re-vintaged for motion.

**Ruling 5 built — 2026-10-26 (late night).** `token_equivalent` gained the directional digit-run
clause; `scripts/motion_guard_replay.py` now lists every recorded run (nine: v1, v2, the 2026-10-25
A/B's two arms, ciric, v3, v4, and the 2026-10-26 A/B's two arms — 550 draws; its totals line
reports the real count instead of a hard-coded 180). Replay before and after the change, byte for
byte: **identical** — 20 routed, 30 unsupported, 267 kept, 233 untouched, no draw moves. The
step-field replay over the 19 stored results: identical (0 demotions; held-out counts only, pass 3,
demote 0). The value survey: identical. The only cell the rule can move is a cole-type one, and no
recorded draw is of that type. Tests: nine parametrized cases in `test_quote_support.py` (`spm` /
`spm12` flips from False to True by this ruling; the reverse and the digit-ending cases stay False)
and one synthetic case in `test_motion_guard.py`; one mutation (the clause disabled, diff shown)
fails five of them.

**Ruling 6 built — 2026-10-27.** `motion_guard.listed_package_in_quote` (exactly one listed
package, by token, ruling 5's digit run tolerated, SPM keeping its version digits) and
`attribution_from_quote` (step iff an operation phrase from the frozen list, copied with a test
holding the copy equal to `motion_value_kind._OPERATION_PHRASES`); the fallback in
`extractor.extract_motion_method` after the routing verdict, the field re-built `EXTRACTED` on the
same span with the package as the `SpecifiedTerm`'s verbatim and `resolved=None`, the diagnostic's
reason `motion_value_routed_fallback_to_package:<tool>-><package>`; the recorder stores the
diagnostic's reason per draw (`diagnostic_reason`, absent from earlier records), and the projection
derives the level into an `attribution` column emitted only for records that carry that key.
**Replay (`scripts/motion_fallback_replay.py`) over all ten recorded runs, 680 draws, 503 extracted:
routed 70, all derosa_2025 (ICA-AROMA), and the fallback yields `FSL` on every one of the 70; no
other paper has a routed draw, so the fallback fires nowhere else.** For the record, 23 extracted and
NOT routed draws have a quote naming exactly one listed package (agtzidis 9, cole 4, gordon 10 — the
package-sentence quotes of versions 2, 5 and 6); the fallback does not apply to them, since nothing
is routed. Tests: the frozen-list copy; six level cases; ten package-finder cases; the fallback
through `extract_motion_method` with a stub client (FSL on the same span, the raw layer untouched)
and two no-fallback cases (no package; two packages).
