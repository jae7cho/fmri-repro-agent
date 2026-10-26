# motion_correction.method — reachability probe v2, results

**DIAGNOSTIC. Not an evaluation.** Seven papers against the readings pre-declared in prereg Amendment 4,
under a stanza iterated once after the first run. **No rate, fraction, percentage or accuracy figure**
appears here, and none may be computed from this document or from the projection behind it (prereg
`:9-10`, `:158-159`). Counts are counts of draws.

**A new vintage, not a continuation.** The 2026-10-21 run (`motion-probe-v1-results.md`) ran stanza
`56bc6305…`; this run ran `378a294f…`. The two sets of draws are never pooled, and a change between
them is a change between two stanzas AND two days, which this run alone cannot separate (see
agtzidis below).

- **Run date** 2026-10-22. **K** = 10 per paper, 7 papers, 70 draws.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Stanza** `MOTION_METHOD_PROMPT`, sha256 `378a294f94ca9f0fc6bd45bd42caf4646a007c7d705d05c8b5f584dd66ca8cab`
  (5,090 characters), pinned by [test_prompt_pin.py](../../extractor_mvp/tests/test_prompt_pin.py)
  with a dated note naming the superseded hash.
- **Span resolver vintage** `span_resolver.py` at `3cb396e` (2026-07-16), working tree clean —
  recorded in the projection header, which the v1 projection lacked.
- **Pre-registration** [motion-method-reachability-prereg.md](motion-method-reachability-prereg.md),
  v1 plus Amendments 1–4. Amendment 4 was written before this run started.
- **Per-draw record** [ground_truth/motion_probe_v2_projection.csv](../../ground_truth/motion_probe_v2_projection.csv),
  emitted by [motion_probe_projection.py](../../extractor_mvp/scripts/motion_probe_projection.py) —
  status, heuristic class, state-map row, span offsets; **no quote text, no value text**. The
  generator was validated by regenerating the v1 projection byte-for-byte from the v1 run before it
  touched this one. The unprojected run is at `extractor_mvp/results/motion_probe_v2/` (gitignored).
- **Held-out status.** liu_2005, tang_2025 and wheaton_2004 were not loaded, searched or read; the
  recorder refused them by id before building a client; `.rgignore` was in place throughout.

## What changed between the two runs

**One stanza edit, under prereg C11, on the probe papers only.** STEP 3's "BOUND BUT ROUTED ELSEWHERE"
now names COBIDAS D.3's *Artifact and structured noise removal* row and the tools D.3 p.57 lists under
it — CompCor, ICA-FIX, ICA-AROMA — as belonging to that row, supplying nothing here, "EVEN WHEN the text
says 'motion correction via' one of them"; the value is the paper's own phrase for the operation. STEP
4's first rule gained "and not routed elsewhere". Nothing else in the stanza moved; the deferral arm is
as it was (written to CALL 7, correction 5).

**One proposed edit held.** The author's deferral line (poldrack `deferred`, liu_2013 `described_only`)
was checked against CALL 6, CALL 7 and CALL 2a before writing, as instructed. It conflicts with CALL 7's
enumeration criterion and does not separate its two anchors on the axis it names. The conflict is
reported in Amendment 4 §3 for the author's ruling and was not resolved by editing the stanza.

**One paper added.** ciric_2017 (`named_tool` / MCFLIRT) is the replacement positive control, **named by
the author after seeing the first run** — post hoc by construction (Amendment 3's constraint 1), and
already contaminated twice over (co-adjudicated; CALL 10 fitting set), so it spends no clean cell.

**Who the stanza fits.** derosa_2025's own tool is now named in the stanza; its draws below are on a
paper the stanza was edited to handle — **fitted, not independent**. poldrack_2015's passage is one of
CALL 10's seven fitting passages and STEP 2's APPLY arm was written from it; its draws were never
independent, and would become fitted a second time if the held deferral line is ruled in.

## Labels read against

| paper | label | source |
|---|---|---|
| power_2014 | `described_only` | workbook, HEAD |
| binder_1999 | `described_only` | workbook, HEAD |
| liu_2013 | `described_only` | workbook, HEAD |
| derosa_2025 | `described_only` | workbook, HEAD |
| agtzidis_2020 | `described_only` | **the author's 2026-10-22 relabel** (protocol v1.6; Amendment 3); in the workbook working copy, uncommitted when this was written. HEAD still reads `named_tool` / SPM12 |
| poldrack_2015 | `deferred`; APPLY control | workbook, HEAD |
| ciric_2017 | `named_tool` / MCFLIRT | workbook, HEAD; **post hoc control** |

## The seven results against their labels

All counts are of draws out of 10. Rows are state-map rows (prereg Amendment 1), computed from raw
`status` and raw `value` only; span resolution is reported beside each and moves no row.

| paper | label read against | returned | against the label |
|---|---|---|---|
| **power_2014** | `described_only` | an operation phrase, **row 1**, 10 of 10; one span (3137–3402), resolved 10 of 10 | **matches on all ten.** The span is longer than v1's (3282–3356) — the whole sentence rather than clause (ii) — and is the same sentence |
| **binder_1999** | `described_only` | **row 2** on 5 (`AFNI` ×4, `MCW-AFNI` ×1); **row 3 `undecided`** on 3 (the algorithm description ×2, the bare citation ×1); **row 1** on 2 (the operation word kept with the description). All ten quote the same sentence (11023–11180), resolved 10 of 10 | matches on 2; `undecided` on 3; **mismatch on 5 — a new error class** (below). Ruling 4's trigger: 3 of 10, **below the threshold of 6** on this vintage; it fired at 10 of 10 on v1 |
| **liu_2013** | `described_only` | an operation phrase, **row 1**, 10 of 10; span resolved 10 of 10 | **matches on all ten** |
| **derosa_2025** | `described_only` | `ICA-AROMA`, **row 2**, 10 of 10; span resolved 10 of 10 | **the iteration did not take.** Reading 2 on all ten, as under v1, with the stanza now naming ICA-AROMA, the row, and the exact phrase "motion correction via". **Fitted, and still wrong** |
| **agtzidis_2020** | `described_only` — the author's 2026-10-22 relabel | `SPM12`, **row 2**, 10 of 10. Spans: 9 of 10 resolved across three quote forms, all stopping before the corrupt `×` clause; 1 unresolved (the long form) | **mismatch on all ten under the relabel**; under HEAD's superseded `named_tool` / SPM12 it would be the target on all ten. v1 returned `SPM12` on 1 of 10. Two candidate causes, not separable by this run (below) |
| **poldrack_2015** | `deferred`; APPLY control | an operation phrase, **row 1**, 10 of 10 (two surface forms, 5 and 5); `applywarp` never returned; one span (25523–25671, as v1), resolved 10 of 10 | **control criterion met; label mismatch on all ten** — pre-declared in Amendment 4 §3 as the outcome CALL 7's wording predicts for a paper that cites a pipeline and then enumerates in its own voice. The deferral arm was not changed between runs, and neither was poldrack's result |
| **ciric_2017** | `named_tool` / MCFLIRT — **post hoc control** | `MCFLIRT`, **row 2**, 10 of 10; one span (4410–4507), resolved 10 of 10 | **the target on all ten, on a control chosen after the first run.** The span is the "(3) realignment … using MCFLIRT (Jenkinson et al., 2002)" clause: it contains the ESTIMATE mention (offset 4475) and none of the three CONSUME mentions (5533, 6360, 9296), so state, value and `span_role` all match the correctness rule. The citation was not deferred to |

### Named lines, run-wide

- **Draws** 70. **Reasks** 0. **Retries** 0 (`completion_attempts` = 1 throughout). **Errors** 0.
- **Unresolved spans** 1 of 70 (agtzidis, the long quote form). v1 had 7 of 60, all agtzidis.
- **Wall time per draw** min 3.17 s, median 4.52 s, mean 12.11 s, max 195.91 s. The maximum is one
  derosa draw; derosa's other nine took 15–21 s, above every other paper's maximum, so derosa's slice is
  slow in itself and one draw ran roughly ten times longer with no retry recorded — a single long
  completion, not a reask.
- **Ruling 1 and 2 lines, power + binder, 20 draws.** The unreachability trigger (`status="missing"`)
  fired **0** times. *Clean* draws (extracted, quote resolved, heuristic `operation_phrase`): power 10,
  binder 2 — **12 of 20**. *Neither*: binder 8 (5 `tool_name`, 3 `undecided`). On v1 the same lines
  read 0 / 10 of 20 / 10 (binder `undecided` ×10). Reported side by side, not pooled.

## binder's five `AFNI` draws are a new error class, not the declared one

Amendment 2 ruling 3 declared, for binder, "a tool name absent from binder's own text → extraction error
— a value the paper does not contain". This is not quite that. `MCW-AFNI` **is** in binder's methods
text — about 1,600 characters after the coregistration sentence, in *"Individual anatomical (SPGR)
scans and SPMs were then projected into the standard stereotaxic space of Talairach and Tournoux (1988),
using the MCW-AFNI software package (Cox, 1996a)"*. That passage is an atlas projection of anatomical
scans and statistical maps, which STEP 1's gate sets aside, and its citation is **1996a**, not the
**1996b** of the coregistration sentence. Every one of the five draws quoted the 1996b sentence and
returned the package from the 1996a one.

So the model did what the protocol's own verification flag forbids — *"Cox 1996b is not identified. Cox
1996a is the AFNI software paper; 1996b is a different work of the same year and has NOT been verified.
Do not assume it is a volume-registration paper"* (CALL 2a) — and did it by carrying a package across
two passages and two citations on the strength of a shared surname. Under CALL 1 v1.5 the value is
unbound (named for a different step); under CALL 2a it is the inference the protocol declines to make.
It is recorded as its own line because the v1 run did not produce it at all: binder was `undecided` on
10 of 10 then, and a stanza that moved binder from "cannot classify" to "classifies wrongly on half the
draws" has not improved on binder.

## agtzidis moved from 1 of 10 to 10 of 10 `SPM12`, and this run cannot say why

Two things changed between the runs: the stanza (STEP 3 longer, STEP 4's first rule reworded) and the
day. The project has measured day-to-day movement at `temperature=0.0` before — the temporal finding's
fixed→fixed 4/10 → 0/10 that fixed K=10 in the first place — so neither cause can be ruled out from here.
The one experiment that separates them is a K=10 re-run of agtzidis **under the superseded stanza**
(`56bc6305…`) on the same day as this run. It is inside the C11 licence (agtzidis is a probe paper) and
costs ten calls. **It is proposed, not run**: it was not in the instruction for this session, and it
belongs beside the author's ruling on what agtzidis's label is, since the same ten draws read as ten
failures or ten successes depending on that ruling.

What can be said: the relabel (protocol v1.6) was made after seeing a run on which the stanza mostly
agreed with it; the next run disagrees with it on every draw. Neither run is evidence for the label,
and the label is the author's. The two runs together are evidence that **agtzidis's binding is the
case this stanza is least stable on**, which is a fact about the stanza worth more than either count.

## derosa: the routing edit changed nothing

The stanza now names ICA-AROMA, names the COBIDAS row it belongs to, and names the exact phrase
"motion correction via" as the trap. The model returned `ICA-AROMA` on 10 of 10 draws anyway, with the
same span as v1. This is the shape `docs/findings/temporal-firewall-fix.md` records — *"the baseline
failure is not a missing rule"*: the exclusion is in the prompt, explicit and near-verbatim, and is
overridden. That finding's remedy was structural (a mandatory subject-first decision), not a better
sentence. Whether derosa's case gets a structural home — a role arm at STEP 2, which CALL 10 says not to
add by default ("record which way it was decided and why, rather than adding an arm by default") — or
is accepted as the stanza's stable behaviour and scored as the CALL 4 error class, is a ruling, not an
edit. Either way derosa's draws under `378a294f…` are **fitted and wrong**, and are reported as both.

## What this run shows, and what it does not

- `described_only` remains **expressible**: rows 1, 2 and 3 were all produced and the trigger never
  fired on power or binder. Evidence, not proof (`:158-159`).
- **Named-tool emission is now exercised**, which Amendment 3 said the probe could not do: on ciric the
  stanza emitted the bound tool with its ESTIMATE span on 10 of 10. That is on a control **chosen after
  the first run**, on a paper in CALL 10's fitting set, so it is evidence that the arm is reachable and
  nothing about how often it is reached.
- The ICA-AROMA routing **did not work** (0 of 10).
- Three label mismatches: agtzidis on 10 (flips with the ruling), poldrack on 10 (the CALL 7 / CALL 10
  question, pre-declared), binder on 5 (new class).
- **No accuracy figure.** Nothing above is a rate, and the counts are on seven papers all inside the
  contaminated union — two of them fitted by this very stanza.

## Status

- **Held for the author:** the deferral line (Amendment 4 §3), with its CALL 7 conflict and the
  poldrack / liu_2013 anchors it does not separate.
- **Proposed, not run:** agtzidis K=10 under `56bc6305…` on the same day, to separate stanza from day.
- **Open:** derosa's routing — structural change or accepted error class; binder's cross-passage
  `AFNI` — whether STEP 1's gate needs to say that a package named for a set-aside passage is set aside
  with it.
- **Ruling 4 / option (c):** still held. The trigger is now **vintage-dependent** — fired on v1 (10 of
  10), not on v2 (3 of 10) — which is itself an argument that the `undecided` count measures the
  stanza's stability on binder as much as the heuristic's adequacy.
- **Vintage:** this run is `378a294f…` on resolver `3cb396e`. Any later run is its own.
