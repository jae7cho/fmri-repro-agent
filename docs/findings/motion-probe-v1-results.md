# motion_correction.method — reachability probe v1, results

**DIAGNOSTIC. Not an evaluation.** This document records what the six probe papers returned, against
the readings declared before the run. It contains **no rate, fraction, percentage or accuracy figure**,
and none may be computed from it or from the projection that backs it. The probe asks one question —
*is `described_only` expressible by the extractor at all* — and that question is answered by whether a
state can be produced, not by how often it is produced correctly (prereg `:9-10`, `:158-159`).

- **Run date** 2026-10-21. **K** = 10 per paper, 6 papers, 60 draws.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`
  ([extractor.py:1199-1200](../../extractor_mvp/src/extractor_mvp/extractor.py#L1199)).
- **Stanza** `MOTION_METHOD_PROMPT`, sha256 `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a`,
  pinned by [test_prompt_pin.py](../../extractor_mvp/tests/test_prompt_pin.py).
- **Pre-registration** [motion-method-reachability-prereg.md](motion-method-reachability-prereg.md),
  v1 plus Amendment 2's five pre-run rulings.
- **Per-draw record** [ground_truth/motion_probe_v1_projection.csv](../../ground_truth/motion_probe_v1_projection.csv)
  — status, heuristic class, state-map row, span offsets. No quote text, no value text: the corpus is
  not in this repository for licensing reasons, and tracking the returned sentences would redistribute
  what the corpus withholds. The unprojected run is at `extractor_mvp/results/motion_probe/` (gitignored).
- **Reasks** 0 of 60. **Retries** 0 of 60 (`completion_attempts` = 1 throughout). **Wall time** 3.28 s
  min, 8.07 s mean, 19.83 s max per draw.

## The six results against their declared readings

| paper | declared reading | returned | verdict |
|---|---|---|---|
| **power_2014** | `described_only` candidate; the `verbatim=None` trigger would show unreachability | operation phrase, **state-map row 1 `described_only`**, 10 of 10; one span, resolved 10 of 10 | **matches.** The trigger never fired |
| **liu_2013** | `described_only` candidate | operation phrase, **row 1**, 10 of 10; spans resolved 10 of 10 | **matches** |
| **binder_1999** | the algorithm description without the operation word → **`undecided`**, "expected and the honest outcome" (`:113-118`) | the algorithm description, **row 3 `undecided`**, 10 of 10 | **matches the declared limitation branch** — the returned value is precisely the algorithm-description clause of the sentence the prereg quotes at `:113-114`, which is the branch it named |
| **derosa_2025** | four readings; 2 = `ICA-AROMA` → CALL 4 territory, "extraction error, different class" (`:14`) | `ICA-AROMA`, **row 2 `named_tool`**, 10 of 10 | **reading 2 on all ten draws.** No span adjudication needed — the value alone fixes the row |
| **poldrack_2015** | APPLY control → **must not yield `applywarp`** (`:7`) | three realign-family values across the draws, **row 1**, 10 of 10; `applywarp` never returned | **control criterion met** |
| **agtzidis_2020** | POSITIVE CONTROL → **`SPM12`** (`:6`) | an operation phrase on 9 draws, **row 1 `described_only`**; `SPM12` on 1; 7 draws discarded at span resolution | **control mis-specified** — the declared reading contradicted CALL 1 v1.5; 9 of 10 are consistent with the corrected label |

## The positive control was mis-specified, not failed

**This section has been corrected twice and the second correction reversed the first.** I reported
agtzidis as a failed positive control: 9 of 10 draws returned an operation phrase where the paper named
a tool. The author ruled on 2026-10-22 that **the control's declared answer was wrong, not the stanza's**.

agtzidis names `SPM12` once, two sentences before the step clause, governing "the fMRI data analysis" as
a whole, and binds no tool to the realignment. Under CALL 1 v1.5's binding test that is derosa's
procedure-set shape, so the correct extraction state is **`described_only`**, with SPM12 on the
inference arm. The protocol records this as a dated clarification keeping CALL 1 v1.5 and correcting its
worked example (`ground-truth-protocol-motion_correction.md` v1.6); the pre-registration records the
consequence in Amendment 3.

**So the 9 draws are consistent with the corrected label and the 1 `SPM12` draw is the outlier** —
the inverse of what I reported. The count did not change; its reading did.

**What the probe therefore cannot show.** With agtzidis moved to `described_only`, **no paper in the six
has a named tool as its correct answer.** The probe shows `described_only` is reachable — rows 1, 2 and 3
were all produced — but it cannot show the stanza emits a tool name when a tool name is correct. That arm
is **untested**. A replacement control will be named by the author and, being chosen after this run, must
be reported as such wherever its result appears (Amendment 3).

**The ruling was made after seeing this output**, which is recorded in the protocol and here rather than
smoothed over: a clarification that converts measured errors into measured successes cannot also be cited
as evidence the extractor performs well.

### The discarded draws are a separate matter, and are unaffected

7 of the 10 draws were discarded at quote resolution, the `SPM12` draw among them. This is independent of
everything above — the 9/10 count is computed from **raw values**, which do not depend on whether a quote
matched. All 10 draws quote the *same* passage, so the stanza located the right sentence every time; the
7 discarded ones returned a longer form extending into corrupt text:

```
model returned : ' into 3 × 3 × 3 mm3 voxels.'
pypdf produced : ' into 3 /C2 3 /C2 3m m 3 vo'
```

The page prints `×`; the model transcribed the page correctly. Quote resolution is character-exact, so a
faithful transcription of a corrupt text layer cannot match. The 3 draws that resolved returned a shorter
quote stopping before the corrupt region; nothing about them was better.

### This is a recorded exclusion, not a new defect

I called it a defect found in passing. It is a **decision already taken and written down**, and I should
have found it before describing it as new. [`span_resolver.py:16-20`](../../extractor_mvp/src/extractor_mvp/span_resolver.py#L16):

> NOT handled by tier 5: the font-specific multiplication-sign (U+00D7) -> `/C2` glyph mangle seen in a
> few papers (agtzidis/gordon/poldrack/wheaton). `/C<digit>` are font glyph codes that map to DIFFERENT
> glyphs across papers, so treating `/C2` as that glyph globally risks a WRONG match -- which would
> violate the never-fuzzy invariant. It is deliberately excluded; those dimension-quote drops stay
> unrecovered rather than risk a mis-attribution.

The same exclusion is recorded in the **tier-5 Phase-1 validation**,
[`span-resolution-fix.md:67-69`](span-resolution-fix.md#L67) — "**8 / 10 recover** with real, auditable
span text (oconnor, weber×3, viduarre, derosa×2, liu). agtzidis×2 (`×→/C2`) correctly stay unresolved" —
and at `:60`, "agtzidis's 2 dimension-drops stay unrecovered **by design**".

**One attribution has to be stated carefully, because I had it wrong and so did the brief I was working
from.** The v0.4.0 re-measure does *not* name these drops as the glyph mangle. Its own classifier labels
them the opposite way
([`span-resolution-hard-drop-v0.4.0-remeasure.md:25-28`](span-resolution-hard-drop-v0.4.0-remeasure.md#L25)):
"RECOVERABLE mangle (quote present + value in quote): **0** · … genuine-mismatch (quote absent,
hallucination-guard): **2**", listing both agtzidis drops under "GENUINE-MISMATCH (quote content absent
from source — must keep failing)". The `/C2` attribution comes from a later **hand-adjudication** in the
supersession block at
[`span-resolution-hard-drop.md:121-125`](span-resolution-hard-drop.md#L121), and `:133-138` records the
disagreement as "**A classification disagreement that is not a reclassification**" — both labels mean
`resolve_quote` failed. So the mechanism rests on hand adjudication that contradicts an automated
classifier, and the DELTA has to carry that rather than cite a clean agreement. The two drops are
agtzidis's `spatial_normalization.target_space` and `resolution_mm`, values `'MNI'` and `'3.0'`
(`span-resolution-hard-drop.md:168-169`).

**And the residue figure is itself stale.** `span-resolution-hard-drop.md:152-156` — "CORRECTION,
2026-09-30 — the residue figure above is itself a stale vintage" — supersedes "2 drops / 1 paper" with
**three unresolved-quote diagnostics across two papers** (`:163-170`): agtzidis's two, plus
**`liu_2005.spatial_normalization.resolution_mm`, `'3.0'`**. That third cell is on a held-out paper, so
whether a repair recovers it **cannot be determined here** without reading text C11/C26 forbids. Any
prediction a DELTA makes has to carry that cell as unknown.

**They are the same sentence as this one.** `resolution_mm` `'3.0'` is read from "resampling them into
3 × 3 × 3 mm3 voxels" — the identical clause that discarded the motion quote. One corrupt clause has now
cost agtzidis three field extractions across two separate measurement campaigns.

Because a repair reverses a ratified decision, it **starts as a DELTA**, not as a fix. The DELTA must
answer the recorded reason on its own terms rather than overriding it.

Scoped across the six probe papers (the three held-out papers were **not** loaded, not even to count
characters — prereg C11/C26; `span_resolver.py:17` names one of them, and that naming is taken from the
docstring, not verified against its text):

| paper | glyph leaks in methods text | span failures |
|---|---|---|
| power_2014, binder_1999, liu_2013, derosa_2025 | 0 | 0 |
| agtzidis_2020 | **6** (`/C0`, `/C2`, `/C19`) | 7 |
| poldrack_2015 | **31** (`/C0`, `/C2`, `/C15`, `/C176`) | 0 |

*(Counted with `/C\d+`. My first pass used `/[A-Z]\d{1,3}\b` and reported 5 and 21: the trailing `\b`
fails on a code followed by a letter, and agtzidis's `/C19` is followed by `e`. The under-count did not
change any conclusion, but the numbers above replace the ones I first gave.)*

poldrack carries four times agtzidis's leaks and lost nothing, because its quotes did not happen to cross
one. The exclusion bites only when a quote crosses a leak — which is why it can sit in two papers' text
and cost nothing in one of them.

## The ruling, and the evidence it rests on

**Ruled by the author, 2026-10-22, after seeing the probe output: CALL 1 v1.5 stands; agtzidis is
`described_only`.** Recorded in the protocol as a v1.6 clarification with agtzidis as a worked case
beside derosa. The label change is the author's; the labelling workbook is untouched by this document.

The evidence the run contributed was the full sentence, which the protocol's own citation elided. Every
draw quoted a passage running into "…into 3 × 3 × 3 mm3 voxels", a **resampling** step. The region reads
(whitespace collapsed, `/C2` shown as the `×` the page prints):

> The fMRI data analysis was performed with **SPM12** using Matlab 9.2. We initially followed a standard
> preprocessing pipeline for each recording (Poldrack et al., 2011). The process comprised **realigning**
> the functional data to the mean image of each session (without slice timing correction),
> **coregistering** them to the anatomical T1 scan, **normalizing** them to the MNI template, and
> **resampling** them into 3 × 3 × 3 mm3 voxels. Finally, we applied **smoothing** …

CALL 1 v1.5 had used agtzidis as its worked **Bound** example
([`:171-173`](../ground-truth-protocol-motion_correction.md#L171)), on the ground that "SPM12 → Realign
is a one-to-one binding", quoting *"performed with SPM12 … The process comprised realigning…"*. **That
ellipsis spans 121 characters containing two sentence boundaries**, and the quote stops immediately
before "coregistering … normalizing … resampling". The single SPM12 mention governs five steps; the word
"motion" never appears. One-to-one is one-to-five.

**The competing reading is recorded as defensible, not dismissed.** COBIDAS §4.3 p.10 models attribution
at the step level — "SPM's realign tool" — which read strictly would license treating a package named for
a pipeline as naming the tool for each step it enumerates. That sentence is framed for papers that
*combine* tools, where step-level attribution is the only way to say who did what; agtzidis names one
package for everything, which is the case the framing does not address. A rater reaching `named_tool` /
SPM12 is disagreeing about the scope of a COBIDAS sentence, not misapplying the protocol.

## Vintage

The probe's conclusions **do not depend on quote matching**, so a resolver change does not disturb them.
This is checkable in the projection rather than asserted: all 7 unresolved draws still carry a heuristic
class and a state-map row (rows 1 and 2), because a row is computed from `raw_status` and `raw_value`
only. binder's ruling-4 trigger is row 3 on all 10 draws from its value; its spans are incidental.

- **Resolver vintage of this run:** `span_resolver.py` at commit `3cb396e` (2026-07-16, the last commit to
  touch the file). Tier 5 itself landed in `b9e8a42` (2026-07-13 18:34, "span-resolver: tier-5
  tolerant recovery, built and validated, SHIPPED INERT"); `2560bb1` (22:09) is the later commit that
  *consumed* the recoveries, which is what `DEVLOG.md:30` describes. I had cited the consumption commit
  as the one that added the tier.
- **Stanza vintage:** `MOTION_METHOD_PROMPT` sha256 `56bc6305…b1e21a`.
- **Any re-run after a resolver change is a new vintage** and is reported as such, not merged into these
  draws.

**One carve-out, so the ruling is not over-claimed.** Reachability, the state-map rows and ruling 4's
trigger are span-independent. The prereg's *correctness* rule is not: `:32-33` requires `span_role` to
match for a cell to count correct. A future accuracy measurement therefore does depend on the resolver,
and would have to state which resolver vintage it ran under.

## Ruling 4's trigger fired

Amendment 2 ruling 4: *"if any `described_only` paper is `undecided` on 6 or more of its 10 draws,
option (c) — a model-emitted `value_kind` — is revisited."* binder_1999 is `undecided` on **10 of 10**.
The threshold is crossed and the trigger has fired.

Its ten values are identical, so **one adjudication covers all ten** — the count is ten draws of one
case, not ten cases, and ruling 4's threshold was written against draws. Recording both readings rather
than choosing between them: the threshold is met as written, and what it is evidence *of* is a single
repeated outcome.

**The option-(c) decision is held, not taken.** Revisiting `value_kind` on the strength of a positive
control that failed — and failed partly through a defect that has nothing to do with `value_kind` —
would be fixing the wrong thing. The decision waits on the agtzidis ruling.

## Status

- The stanza is **not** being iterated. Any iteration runs in a **fresh session**: the session that
  produced this document has seen held-out text (see the DELTA's §0), and C11/C26 compliance for stanza
  work means starting from a context that has not.
- `described_only` **is expressible**: rows 1, 2 and 3 were all produced, and the `verbatim=None` trigger
  never fired on power or binder. Per `:158-159` this is evidence and not proof.
- **Untested:** named-tool emission. With agtzidis corrected to `described_only`, no paper in the six has
  a tool name as its correct answer. A replacement control is the author's to name, and is post hoc by
  construction (Amendment 3).
- **Ruled 2026-10-22:** CALL 1 v1.5 stands; agtzidis is `described_only`; the competing COBIDAS §4.3
  reading is recorded as defensible. Protocol v1.6. The relabel is the author's; the workbook is untouched.
- **Ruled 2026-10-22:** width-not-identity answers the `/C<digit>` exclusion. See
  `docs/design/DELTA_glyph_leak_span_recovery.md`, which remains unimplemented.
- Held: option (c) under ruling 4.
- **2026-10-22, later:** the stanza WAS iterated, in a fresh session that had not seen held-out text,
  under C11 and on the probe papers only — one change made (the structured-noise row named in STEP 3),
  one proposed change held with its conflict reported. ciric_2017 was named as the replacement positive
  control, post hoc. Seven papers re-run at K=10 under the new hash as a **separate vintage**; nothing
  in this document moves. See prereg Amendment 4 and `motion-probe-v2-results.md`.
