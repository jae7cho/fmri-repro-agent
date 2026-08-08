# DESIGN — `methods_finder` repair + slice diagnostics

*Highest-leverage component in AESPA: deterministic, no LLM/KB/network, and upstream of extraction, provenance, the four-state model, the emitter, and every published count. Grounded in `extractor_mvp/src/extractor_mvp/methods_finder.py` (67 lines) and empirical probes on the 20-paper corpus.*

---

## 0. Verified evidence

Current behaviour (`find_methods_section`): take the **earliest** match of any `METHODS_HEADERS` pattern; slice to the **first** subsequent `NEXT_SECTION_HEADERS` match, else end of text. No match → whole document, `found_via="fallback_full_text"`.

Measured on the corpus:

| paper | `found_via` | slice/full | cause (verified) |
|---|---|---|---|
| `chen_2015` | `fallback_full_text` | **1.00** (76,433 ch) | header is `Methods and Analysis` — no pattern covers `Methods and <X>`. **Vocabulary bug.** |
| `cabral_2017` | `fallback_full_text` | **1.00** | *"…: Models and mechanisms"* (NeuroImage) — a **review with no Methods section**. Fallback is **correct**. |
| `liu_2005` | `fallback_full_text` | **1.00** | Neuron 2005; extracted text is **column-interleaved**. Vocabulary + text-order corruption. |
| `oconnor_2017` | `header_match` | **0.63** (33,394 ch) | no `NEXT_SECTION` matched → slice ran to `References`, swallowing Results + Discussion + affiliations. |
| poldrack, binder, mueller | `header_match` | bloated | same end-boundary failure. |

**Downstream damage (verified):** `oconnor_2017` and `weber_2024` both name **C-PAC** cleanly inside the slice the extractor was given; both were recorded `base_pipeline = MISSING_FROM_PAPER`. Chen — the flagship fixture behind the protocol emitter, version-inference proof, and COBIDAS section — was extracted from the **entire document**, so its spans resolve against Introduction/Discussion/References and the "value came from Methods" guarantee does not hold.

**A false `MISSING_FROM_PAPER` is invisible to every honesty mechanism in AESPA** — the four-state model, reason partitioning, confidence ceilings and provenance chains all presuppose the extractor saw what was there.

---

## 1. Locked decisions

**D1 — Keep the `^…$` line anchor. Do NOT relax to line-initial.**
Chen line 91 is `"methods [22] are relatively less reliable than independent component analysis…"` — a body line beginning with `methods`. An unanchored line-initial pattern anchors the slice in the Introduction. The anchor is load-bearing; recall must come from vocabulary, not from weaker anchoring.

**D2 — Extend the methods vocabulary; only `Methods and <X>` is corpus-proven.**
Add a `methods? and \w+` / `\w+ and methods?` form (covers chen's `Methods and Analysis`, and `Methods and Materials`). Journal-convention headers (`Experimental Procedures`, `Online Methods`, `STAR Methods`) are **plausible but unverified** — the implementer must confirm each against a real corpus PDF before adding it, and must not add a pattern no corpus paper exhibits.
**Guard:** `Methods and <X>` must not swallow a NEXT header (`Results and Discussion` is a *next-section* header, never a methods header). Order matters — test it.

**D3 — Extend the next-section vocabulary, and treat "no end boundary" as a defect.**
`oconnor` proves the gap: a `header_match` whose slice ends at `References` (or at end-of-text) is a failure state, not a success. Candidate additions (verify each against a corpus PDF): `Results and Discussion`, `Data availability`, `Author contributions`, `Competing interests`, `Funding`, `Declaration of competing interest`, `Supporting information`, `Conclusion(s)`.

**D4 — Three outcomes, not two.** `fallback_full_text` currently conflates two very different things:
- *vocabulary miss* — a Methods section exists and we failed to find it (**chen**, **liu_2005**) → a bug;
- *no methods section* — the paper is a review and has none (**cabral**) → correct behaviour.

`find_methods_section` cannot reliably distinguish these, and **must not guess**. It reports diagnostics; adjudication is human.

**D5 — Slice diagnostics are first-class output, not a log line.**
Add to `MethodsSlice`: `end_offset`, `slice_ratio` (slice / full), `ended_at` (the matched next-header text, or `"end_of_text"`), and `suspicious: bool` (True when `found_via == "fallback_full_text"` **or** `slice_ratio > 0.6` **or** `ended_at == "end_of_text"`).

**D6 — Propagate diagnostics into the per-paper result artifact and surface them in `to_protocol`.**
A spec extracted from a whole-document fallback has different provenance semantics and must say so on its face. Minimal implementation: carry the diagnostics through `ParsedPaper` → the batch result JSON, and render a single warning line in the protocol header. *(Putting them on `Preprocessing` itself is a schema change → v0.4.0; out of scope, flagged.)*

**D7 — Never auto-truncate a slice to satisfy a ratio threshold.** Fabricating a boundary is worse than a bloated slice. Flag it; don't fix it silently.

---

## 2. Non-goals

- Fixing column-interleaved PDF text extraction (`liu_2005`). Separate concern; a better backend may be warranted, but it is not this change.
- Any change to the extractor, spec, KB, or emitter logic beyond the single warning line.
- Adjudicating the 54 suspected false absences — the slices are about to change; adjudicate **after** the re-run.

---

## 3. Test plan

1. **Anchor regression (the D1 guard):** the literal chen line `"methods [22] are relatively less reliable…"` must **not** match any methods header pattern.
2. `"Methods and Analysis"` matches; `"Results and Discussion"` does **not** match a methods pattern and **does** match a next-section pattern.
3. `chen_2015` → `found_via == "header_match"`, `slice_ratio < 1.0`, and the slice contains the extracted values' spans (`fsaverage5`, the grand-mean convention).
4. `oconnor_2017` → `ended_at` is a Results/Discussion-family header, **not** `References`; `slice_ratio` drops materially from 0.63; the slice still contains `"C-PAC"` and `"0.4.0"`.
5. `cabral_2017` → still `fallback_full_text`, `suspicious == True`. **This is correct behaviour, asserted as such.**
6. No corpus paper has `header_match` with `ended_at == "end_of_text"`.
7. `suspicious` is True for every fallback and every `slice_ratio > 0.6`.
8. Determinism; `start_offset` still translates slice-relative spans to full-text offsets (span round-trip test).

---

## 4. Mandatory follow-through (not optional)

1. **Re-run the full corpus.** Every number is provisional: `MISSING_FROM_PAPER = 300`, base pipelines named `9/20`, COBIDAS addressed rows, the `19` not-covered count, the KB intersection.
2. **Attribution diff** against the previous run (the established `citable-v6` practice). Any change to chen / poldrack / viduarre is a regression to explain, not to accept.
3. **Re-derive the KB intersection.** It was reported as `1/20` and attributed to KB coverage. That was wrong: C-PAC is now in the KB, and `oconnor` + `weber` name C-PAC but were missed by extraction. Achievable is **≥ 4/20** (chen/CCS, vanderwal/C-PAC, oconnor/C-PAC, weber/C-PAC). The intersection was bounded by **extraction recall**, not KB coverage.
4. **Corpus composition.** `cabral_2017` is a review with no Methods section. Its missing fields are *not applicable*, not underreporting. Either exclude it (denominator 19) or label it explicitly. Leaving it in silently inflates every underreporting statistic.

---

## 5. Caveats that must travel

- **Overfitting.** The 20-paper corpus is the dev set. Regexes tuned until it passes will look excellent on it and prove nothing about generality. Report the fix as "corpus-fitted, generality untested"; NARPS is the held-out check.
- **`liu_2005` may remain unfixable** by vocabulary alone (column interleaving). If so, say so — a persistent honest fallback beats a regex that "works" by accident.
- **`fallback_full_text` is not always a bug** (cabral). Any metric counting fallbacks as failures is wrong.

---

*Verification boundary: per-paper causes established by running the real `find_methods_section` over pypdf-extracted text. Journal-convention headers beyond `Methods and <X>` are unverified and must be confirmed against a corpus PDF before being encoded.*
