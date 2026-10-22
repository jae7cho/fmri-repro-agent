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
| **agtzidis_2020** | POSITIVE CONTROL → **`SPM12`** (`:6`) | `SPM12` on 1 draw; an operation phrase on 9; 7 draws discarded at span resolution | **failed — see below** |

## The positive control failed, by two independent mechanisms

**Correction to my earlier report.** I previously described this as "9 of 10 operation word, and the one
`SPM12` draw discarded on a span failure". The second clause understated the span failures by a factor of
seven: **7 of the 10 draws were discarded**, not one. The `SPM12` draw was among the seven. The two
mechanisms are separable and only one of them is about the stanza.

**Mechanism A — the value (a stanza matter).** 9 of 10 draws returned an operation phrase where the
paper names a tool. This is the behaviour the positive control exists to detect, and it is the finding.

**Mechanism B — the span (a parser/matcher defect, not a stanza matter).** All 10 draws quote the *same*
passage, so the stanza located the right sentence every time. 7 draws returned a longer form of that
quote which extends into a region where the PDF text layer is corrupt:

```
model returned : ' into 3 × 3 × 3 mm3 voxels.'
pypdf produced : ' into 3 /C2 3 /C2 3m m 3 vo'
```

`/C2` is a **raw glyph name leaking out of a non-standard font encoding** — the page prints `×`, and the
model transcribed the page correctly. Quote resolution is character-exact, so a faithful transcription of
a corrupt text layer cannot match it. The 3 draws that *did* resolve returned a shorter quote that stops
before the corrupt region; nothing about them was better.

**This destroyed the only draw that would have passed.** `SPM12` — the pre-declared correct answer —
carried the long quote and was discarded by mechanism B. So the control cannot be scored as a clean
mechanism-A failure: one of the two mechanisms deleted the single draw that satisfied the reading.

Scoped across the six papers (the three held-out papers were **not** loaded, not even to count
characters — prereg C11/C26):

| paper | glyph leaks in methods text | span failures |
|---|---|---|
| power_2014, binder_1999, liu_2013, derosa_2025 | 0 | 0 |
| agtzidis_2020 | 5 (`/C0`, `/C2`) | 7 |
| poldrack_2015 | 21 (`/C0`, `/C2`, `/C15`) | 0 |

poldrack carries four times agtzidis's leaks and lost nothing, because its quotes did not happen to cross
one. **The defect is latent, not paper-specific**: it discards a correct extraction whenever a quote
crosses a leaked glyph, silently, as `quote_not_found`. Whether it has been doing so in `base_pipeline`
and `target_space` is an open question this probe did not ask.

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

- The stanza is **not** being iterated. Pending a ruling on agtzidis.
- `described_only` **is expressible**: rows 1, 2 and 3 were all produced, and the `verbatim=None` trigger
  never fired on power or binder. Per `:158-159` this is evidence and not proof.
- Open: the agtzidis ruling (mechanism A); the glyph-leak discard (mechanism B), which needs its own fix
  and its own regression test, and is not a stanza change.
