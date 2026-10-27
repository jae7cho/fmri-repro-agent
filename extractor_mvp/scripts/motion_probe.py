#!/usr/bin/env python3
"""The `motion_correction.method` reachability probe recorder.

Pre-registered by ``docs/findings/motion-method-reachability-prereg.md`` (v1 + Amendments 1-4).
Ordered by ``docs/design/DESIGN_motion_correction_extraction.md`` ruling E: extraction and this
probe may precede the K-draw stability runner; SCORES may not.

Run history (each run is its own vintage, named by the stanza hash in its manifest):

* 2026-10-21 -- six papers, K=10, stanza ``56bc6305...``. Recorded in
  ``docs/findings/motion-probe-v1-results.md``.
* 2026-10-22 -- seven papers, K=10, stanza ``378a294f...``: ciric_2017 added as the REPLACEMENT
  positive control (Amendment 4), chosen after the first run and therefore post hoc by construction.
* 2026-10-25 -- the same-day control, agtzidis and binder under both stanzas (Amendment 5); the
  stanza was then reverted to ``56bc6305...`` and ciric_2017 run under it (Amendment 6).
* version 3 (Amendment 7): stanza rewritten from protocol v1.7 (CALL 11) with option (c) -- the
  model states the binding in ``motion_correction_binding``; recorded here as ``raw_binding`` beside
  the frozen heuristic's class, so the projection can count their disagreements.
* version 4 (Amendment 8): braun_2015, viduarre_2017 and vanderwal_2016 join the set for the three
  deferral shapes version 3 could not reach; ten papers.

**It makes ONLY the motion call.** Not ``extract``, not ``extract_preprocessing`` — just
``extract_motion_method``. Two reasons, both deliberate:

* the prereg scopes the probe to one field (``:5``, "Build ``motion_correction.method`` only"), and
  a full extraction would take incidental ``target_space`` draws on six papers that are not part of
  any pre-registered question. Those draws would exist, be stored, and invite later use.
* K=10 x 6 papers is 60 calls on one short prompt instead of 120 calls on two, half of them large.

**It cannot be pointed at a clean paper.** ``_PROBE_PAPERS`` is exactly the papers the prereg names
(six at v1, seven from Amendment 4), and any other id is refused before a client is built.
liu_2005, tang_2025 and wheaton_2004 are the only uncontaminated cells in the motion corpus; prereg
C11/C26 permit iterating the stanza on the contaminated probe papers and explicitly do not extend
that licence to those three. A probe run that touched one would spend a held-out cell that cannot
be recovered. ciric_2017 is already contaminated twice over -- `co-adjudicated`, and one of CALL
10's seven fitting passages -- so adding it spends nothing.

**The table is the whole corpus since 2026-10-26 (DESIGN_motion_full_corpus.md §2.1).** All 19
ids of ``configs/batch_a1_acceptance_config.yaml`` are in ``_PROBE_PAPERS``, written from ids and
file names only; no text was read to add them. The three held-out ids stay REFUSED: ``_HELD_OUT``
is checked before any client is built, and a held-out id is admitted only when ``--corpus-run``
equals ``_CORPUS_RUN_LICENCE``, which is None until the prereg amendment that licenses the
full-corpus run sets it in the same commit. A typo still cannot spend a cell, and neither can the
default paper list, which is the 13-paper probe set (``_PROBE_SET``, Amendment 10) and names no
held-out id; listing all 19 is refused until that licence exists.

**Records both layers, because one mapping is not yet ruled.** The prereg requires ``verbatim``,
``resolved``, ``resolution`` and span per draw (``:8``) — those are ``SpecifiedTerm`` fields, i.e.
the PROCESSED layer. But Amendment 1 (``:45-46``) states the LLM output schema is
``FieldExtractionResult`` (``status``/``value``/``verbatim_quote``), and the prereg never says how
its unreachability trigger ``verbatim=None`` maps onto that. Both layers are therefore recorded, so
the run has what it needs whichever way that is ruled, rather than needing a re-run.

**Distribution only, no winner** — ``DESIGN_kdraw_stability.md`` fork 3. This writes every draw and
computes no majority, no plurality, and no representative value.

Output: ``<results-dir>/motion_probe/<paper_id>.jsonl``, one object per draw, plus
``manifest.json`` carrying an emitted provenance header. Under ``results/``, which is gitignored:
stability and reachability are properties of a RUN (DELTA/stability §4b sub-decision 2). Publishing
any number from this requires promoting the artifact to a tracked snapshot first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fmri_repro.spec.preprocessing import SpecifiedTerm
from fmri_repro.spec.provenance import DeferredToCitation, Extracted

from extractor_mvp.extractor import (
    MOTION_METHOD_PROMPT,
    extract_motion_method,
)
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date

_MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # the v6/v7-pinned model
_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")

#: The papers the pre-registration names, and nothing else: six at v1 (prereg :5-7), plus
#: ciric_2017 from Amendment 4 (2026-10-22). The controls are marked because their expected
#: outcomes are pre-declared and must be checkable after the run.
_PROBE_PAPERS: dict[str, dict[str, str]] = {
    "power_2014": {"pdf": "Power_2014.pdf", "role": "described_only candidate"},
    "binder_1999": {"pdf": "Binder_1999.pdf", "role": "described_only candidate; undecided case"},
    "liu_2013": {"pdf": "Liu_2013.pdf", "role": "described_only candidate"},
    "derosa_2025": {"pdf": "DeRosa_2025.pdf", "role": "described_only candidate; 4 readings"},
    "agtzidis_2020": {
        "pdf": "Agtzidis_2020.pdf",
        # Was "POSITIVE CONTROL -> expect SPM12" at v1. Amendment 3 voided that criterion: the
        # committed label contradicted CALL 1 v1.5 and was corrected to described_only on
        # 2026-10-22 (protocol v1.6). Kept in the set as a described_only candidate.
        "role": "described_only candidate (ex-positive control; Amendment 3)",
    },
    "poldrack_2015": {
        "pdf": "Poldrack_2015.pdf",
        "role": "APPLY CONTROL -> must NOT yield applywarp; committed label deferred",
    },
    "ciric_2017": {
        "pdf": "Ciric_2017.pdf",
        # Named by the author on 2026-10-22 AFTER the first run (Amendment 4). Post hoc by
        # construction; every report of its result must say so in the same sentence as the count.
        "role": "REPLACEMENT POSITIVE CONTROL -> expect MCFLIRT, span = the ESTIMATE clause",
    },
    # Amendment 8 (2026-10-26): the three deferral shapes the version-3 run and the label pass found
    # the stanza could not reach. All three are co-adjudicated and outside CALL 10's seven, so the
    # contaminated union stays 16 of 19; they are FITTED from version 4, and every count says so.
    "braun_2015": {
        "pdf": "Braun_2015.pdf",
        "role": "deferred candidate -- wholesale deferral (CALL 6); fitted from version 4",
    },
    "viduarre_2017": {
        "pdf": "Viduarre_2017.pdf",
        "role": "deferred candidate -- wholesale deferral; FIX is not the value; fitted from v4",
    },
    "vanderwal_2016": {
        "pdf": "Vanderwal_2016.pdf",
        "role": "deferred candidate -- named, uncited pipeline; host-sentence risk; fitted from v4",
    },
    # The full corpus (2026-10-26, DESIGN_motion_full_corpus.md §2.1): the nine remaining papers of
    # configs/batch_a1_acceptance_config.yaml, ids and file names copied from it. NO TEXT WAS READ
    # to write these entries. Six are contaminated (co-adjudicated, or in CALL 10's derivation set)
    # and never ran under the motion call; three are the held-out clean cells, which stay refused
    # until a corpus-run licence admits them (see _CORPUS_RUN_LICENCE).
    "chen_2015": {"pdf": "Chen_2015.pdf", "role": "co-adjudicated; CALL 10; not probed"},
    # Amendment 10 (2026-10-26): the three join the probe set from version 6 (protocol v1.8's
    # attribution level); their v1.8 worked cases are on the record, so they are fitted from v6.
    "cole_2013": {
        "pdf": "Cole_2013.pdf",
        "role": "named_tool PACKAGE candidate (AFNI); probe from v6, fitted; CALL 10",
    },
    "gordon_2014": {
        "pdf": "Gordon_2014.pdf",
        "role": "named_tool STEP candidate (SPM8); probe from v6, fitted; CALL 10",
    },
    "mueller_2021": {
        "pdf": "Mueller_2021.pdf",
        "role": "named_tool PACKAGE candidate (SPM12); probe from v6, fitted; co-adjudicated",
    },
    "oconnor_2017": {"pdf": "OConnor_2017.pdf", "role": "co-adjudicated; not probed"},
    "weber_2024": {
        "pdf": "Weber_2024.pdf",
        "role": "co-adjudicated; not probed; likely_multi_acquisition flag (does not route)",
    },
    "liu_2005": {
        "pdf": "Liu_2005.pdf",
        "role": "HELD OUT -- clean cell; refused without a licence",
    },
    "tang_2025": {
        "pdf": "Tang_2025.pdf",
        "role": "HELD OUT -- clean cell; refused without a licence",
    },
    "wheaton_2004": {
        "pdf": "Wheaton_2004.pdf",
        "role": "HELD OUT -- clean cell; refused without a licence",
    },
}

#: Never a probe target. Named so a typo cannot silently spend a held-out cell (prereg C11, C26).
_HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})

#: The PROBE SET (prereg Amendment 10, 2026-10-26): the ten papers of Amendments 4 and 8 plus
#: cole_2013, gordon_2014 and mueller_2021, all contaminated, on which C11 licenses iterating the
#: stanza. The default --papers. The other six corpus papers run only when listed, and the held-out
#: three only under a corpus-run licence.
_PROBE_SET: tuple[str, ...] = (
    "power_2014",
    "binder_1999",
    "liu_2013",
    "derosa_2025",
    "agtzidis_2020",
    "poldrack_2015",
    "ciric_2017",
    "braun_2015",
    "viduarre_2017",
    "vanderwal_2016",
    "cole_2013",
    "gordon_2014",
    "mueller_2021",
)

#: The licence that admits the held-out three (DESIGN_motion_full_corpus.md §7 fork 1, 2026-10-26).
#: None until the prereg amendment that licenses the full-corpus run sets it to that amendment's id
#: in the SAME commit; then ``--corpus-run <id>`` must equal it exactly. Default-closed: while this
#: is None no flag value admits them, and the default paper list (all 19) is refused with a message
#: that says what to pass instead. The run that spends the three cells is one run; a second needs
#: a new licence, because it would be made after their first result was seen.
_CORPUS_RUN_LICENCE: str | None = None


def _refuse_unless_licensed(corpus_run: str | None, held: list[str]) -> None:
    """Raise before any client is built unless the held-out ids are licensed for this run."""
    if _CORPUS_RUN_LICENCE is None or corpus_run != _CORPUS_RUN_LICENCE:
        why = (
            "no corpus-run licence is recorded in this file"
            if _CORPUS_RUN_LICENCE is None
            else f"--corpus-run {corpus_run!r} does not match the recorded licence"
        )
        raise SystemExit(
            f"refused: {held} are HELD OUT -- the only uncontaminated cells in the motion corpus "
            f"(prereg C11, C26) -- and {why}. A draw against one cannot be undone. Pass --papers "
            "with the sixteen contaminated ids, or run under the amendment that licenses the "
            "full-corpus run."
        )


#: THE FROZEN STANZA (prereg C11; Amendment 9, adopted 2026-10-26). The sha256 of the stanza the
#: same-day A/B adopted. The recorder refuses to run under any other: a stanza change now needs a new
#: prereg amendment that names the new hash HERE, in the same commit, and the full-corpus run's
#: manifest must carry this value. A pin alone (test_prompt_pin.py) can be updated to make a test
#: pass; this constant stands between an edited stanza and a draw.
#:
#: MOVED to version 6, 2026-10-26 (late night), by prereg Amendment 10 -- a DEFINITIONAL CHANGE, not
#: tuning: protocol v1.8 gives named_tool an attribution level (step / package) that version 4 could
#: not express. Superseded value b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837
#: stays on every version-4 record. Version 6 freezes on adoption under Amendment 10's rule.
_FROZEN_STANZA_SHA256 = "8df070da9cc3f9628d6670c7285740155b05a06dd25972849f0711b056c8ef4f"


def _refuse_unless_frozen(live_sha256: str) -> None:
    """Raise before any client is built if the live stanza is not the frozen one."""
    if live_sha256 != _FROZEN_STANZA_SHA256:
        raise SystemExit(
            f"refused: MOTION_METHOD_PROMPT hashes to {live_sha256[:8]}..., but the stanza is FROZEN "
            f"at {_FROZEN_STANZA_SHA256[:8]}... (prereg C11, Amendments 9 and 10). No draw runs under an "
            "unfrozen stanza. A change needs a new amendment naming the new hash in this file."
        )


@dataclass(frozen=True)
class DrawRecord:
    """One draw. Every field the prereg asks for, plus the raw layer beneath it."""

    paper_id: str
    draw: int  # 1-based

    # --- raw layer: the LLM's own output (Amendment 1 :45-46) ---
    raw_status: str | None
    raw_value: str | None
    raw_verbatim_quote: str | None
    raw_ref_string: str | None
    raw_deferral_sentence: str | None
    #: option (c): the CALL 1 binding the MODEL states ("named_tool" / "described_only"), set only
    #: on an extracted draw. The heuristic's class is derived at projection time from raw_value and
    #: is the independent control; this field is what it is compared against.
    raw_binding: str | None

    # --- processed layer: what the prereg :8 names ---
    verbatim: str | None
    resolved: str | None
    resolution: str | None
    span_start: int | None
    span_end: int | None
    span_text: str | None
    span_section: str | None
    span_recovered: bool | None

    # --- the arm, and the deferral detail row 5 of the state map needs ---
    extraction_arm: str  # Extracted | DeferredToCitation | MissingFromPaper | other
    left_missing_reason: str | None
    deferral_target_kind_original: str | None  # DeferralRecord's, BEFORE supplement->paper
    deferral_target_kind_stored: str | None  # the frozen Deferral's, AFTER narrowing
    deferral_ref: str | None

    # --- fork 1: a draw is 1 or 2 completions; which, is recorded per draw ---
    completion_attempts: int
    reask_occurred: bool

    #: Wall time for THIS draw, seconds. Logged because this call's latency is unmeasured: the
    #: project's only per-call figure (11.87 s, DESIGN_kdraw_stability.md §3g) measures the SHARED
    #: 13,480-character call returning seven fields, and this prompt is 3,887 characters returning
    #: one. Borrowing it would assert a measurement nobody has taken. The first probe run takes it.
    wall_seconds: float

    error: str | None = None


class _CountingClient:
    """Wraps the instructor client and counts RAW completions per draw.

    ``max_retries=2`` means one draw is one or two completions (instructor reasks on a validation
    failure), so "did a reask occur" is not derivable from the draw's result — only from how many
    times the underlying completion ran. Ruling fork 1 requires it per draw, and
    ``reask-measurement-validity.md`` exists because a mixed measurement whose components are not
    separable is a confounded one. Counting here keeps them separable.
    """

    def __init__(self) -> None:
        import instructor
        import litellm

        self.attempts = 0

        def counting_completion(*args: Any, **kwargs: Any) -> Any:
            self.attempts += 1
            return litellm.completion(*args, **kwargs)

        self._client = instructor.from_litellm(counting_completion, mode=instructor.Mode.JSON)

    def reset(self) -> None:
        self.attempts = 0

    @property
    def client(self) -> Any:
        return self._client


def _paper(paper_id: str) -> ParsedPaper:
    """Load and slice exactly as ``batch.process_paper`` does, so the probe measures the same input."""
    path = _CORPUS / _PROBE_PAPERS[paper_id]["pdf"]
    if not path.is_file():
        raise SystemExit(f"corpus PDF missing: {path}")
    text, parser = load_pdf_text(path)
    if parser == "failed" or not text:
        raise SystemExit(f"pdf text extraction failed: {path}")
    methods = find_methods_section(text)
    return ParsedPaper(
        text=methods.text, source=paper_id, parser="pypdf", pdf_date=pdf_creation_date(path)
    )


def _record(
    paper_id: str,
    draw: int,
    pf: Any,
    deferral: Any,
    attempts: int,
    raw: Any,
    wall_seconds: float,
) -> DrawRecord:
    ext = pf.extraction
    arm = type(ext).__name__
    # raw is the whole MotionMethodExtraction since version 3; the field result sits inside it.
    binding = getattr(raw, "motion_correction_binding", None)
    raw = getattr(raw, "motion_correction_method", raw)
    val = getattr(ext, "value", None)
    term = val if isinstance(val, SpecifiedTerm) else None
    span = (getattr(ext, "spans", None) or [None])[0] if isinstance(ext, Extracted) else None
    stored_deferral = (
        (getattr(ext, "deferrals", None) or [None])[0]
        if isinstance(ext, DeferredToCitation)
        else None
    )
    return DrawRecord(
        paper_id=paper_id,
        draw=draw,
        raw_status=getattr(raw, "status", None),
        raw_value=None if raw is None or raw.value is None else str(raw.value),
        raw_verbatim_quote=getattr(raw, "verbatim_quote", None),
        raw_ref_string=getattr(raw, "ref_string", None),
        raw_deferral_sentence=getattr(raw, "deferral_sentence", None),
        raw_binding=binding,
        verbatim=term.verbatim if term else None,
        resolved=term.resolved if term else None,
        resolution=term.resolution if term else None,
        span_start=getattr(span, "start", None),
        span_end=getattr(span, "end", None),
        span_text=getattr(span, "text", None),
        span_section=getattr(span, "section", None),
        span_recovered=getattr(ext, "span_recovered", None),
        extraction_arm=arm,
        left_missing_reason=getattr(pf.inference, "reason", None),
        # The prereg's row 5 (supplement -> `unread`) needs the ORIGINAL target_kind. The extractor
        # narrows "supplement" -> "paper" when building the frozen Deferral and keeps the original
        # only on the DeferralRecord, so reading the stored Deferral alone would make row 5
        # unobservable. Both are recorded.
        deferral_target_kind_original=getattr(deferral, "target_kind", None),
        deferral_target_kind_stored=getattr(stored_deferral, "target_kind", None),
        deferral_ref=getattr(stored_deferral, "ref", None),
        completion_attempts=attempts,
        reask_occurred=attempts > 1,
        wall_seconds=round(wall_seconds, 3),
    )


def _provenance(k: int, papers: list[str]) -> dict[str, Any]:
    """Emitted, not hand-written, and recomputed at emit time."""
    return {
        "artifact": "motion_correction.method reachability probe — per-draw records",
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "generator": "extractor_mvp/scripts/motion_probe.py",
        "pre_registration": (
            "docs/findings/motion-method-reachability-prereg.md (v1 + Amendments 1-10; frozen)"
        ),
        "model": _MODEL,
        "k": k,
        "papers": papers,
        "corpus_run_licence": _CORPUS_RUN_LICENCE,
        "held_out_admitted": sorted(set(papers) & _HELD_OUT),
        # THE point of this header. prereg C2 ("committed BEFORE the run") and C21 ("the vocabulary
        # may not be extended after seeing output") are only checkable if every draw names the
        # stanza it ran under. C11 licenses iterating the wording on these six papers; doing so
        # changes this hash, so an iteration is visible in the record rather than invisible.
        "motion_method_prompt_sha256": hashlib.sha256(
            MOTION_METHOD_PROMPT.encode("utf-8")
        ).hexdigest(),
        "motion_method_prompt_chars": len(MOTION_METHOD_PROMPT),
        "motion_method_prompt_frozen_sha256": _FROZEN_STANZA_SHA256,
        "aggregation": (
            "NONE. Per-draw distribution only; no majority, no plurality, no representative value "
            "(DESIGN_kdraw_stability.md fork 3). Any aggregate is computed downstream and must "
            "name its rule."
        ),
        "no_accuracy_figure": (
            "The probe tests REACHABILITY, not accuracy. No accuracy figure may be computed from "
            "or cited out of this run (prereg :9-10, :158-159)."
        ),
        "held_out_never_touched": sorted(_HELD_OUT),
        "latency_note": (
            "This call's latency was UNMEASURED before the first run. Per-draw wall_seconds is "
            "recorded so it is measured here rather than borrowed from the shared call's 11.87 s "
            "(DESIGN_kdraw_stability.md 3g), which times a 13,480-char seven-field prompt; this "
            f"one is {len(MOTION_METHOD_PROMPT):,} chars (the template, before {{text}} is "
            "substituted) and one field. An earlier version of this note hard-coded 3,887, the "
            "length of the stanza two revisions before the first run; the figure is now computed."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__ or "", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--k",
        type=int,
        required=True,
        help="draws per paper. REQUIRED, no default: the prereg binds K=10 and a default is how a "
        "statistical choice gets made by whoever runs it first (stability fork 6).",
    )
    ap.add_argument(
        "--papers",
        nargs="*",
        default=list(_PROBE_SET),
        help="subset of the 19-paper corpus; default = the 13-paper probe set (Amendment 10). Any "
        "other id is refused; the three held-out ids are refused unless --corpus-run matches the "
        "recorded licence.",
    )
    ap.add_argument(
        "--corpus-run",
        default=None,
        metavar="AMENDMENT",
        help="admit the held-out ids: must equal _CORPUS_RUN_LICENCE, which the licensing "
        "amendment sets in the same commit. Refused while no licence is recorded.",
    )
    ap.add_argument("--results-dir", required=True, type=Path)
    args = ap.parse_args(argv)

    if args.k < 1:
        raise SystemExit("--k must be >= 1")
    _refuse_unless_frozen(hashlib.sha256(MOTION_METHOD_PROMPT.encode("utf-8")).hexdigest())
    refused = [p for p in args.papers if p not in _PROBE_PAPERS]
    if refused:
        raise SystemExit(
            f"refused paper id(s): {refused}. This probe accepts only the "
            f"{len(_PROBE_PAPERS)} papers of the corpus: {sorted(_PROBE_PAPERS)}."
        )
    held = sorted(set(args.papers) & _HELD_OUT)
    if held:
        _refuse_unless_licensed(args.corpus_run, held)

    out_dir = args.results_dir / "motion_probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    counting = _CountingClient()

    for paper_id in args.papers:
        paper = _paper(paper_id)
        rows: list[dict[str, Any]] = []
        for draw in range(1, args.k + 1):
            counting.reset()
            raw_capture: list[Any] = []
            started = time.perf_counter()
            try:
                pf, _diag, deferral = extract_motion_method(
                    paper, _MODEL, client=counting.client, raw_out=raw_capture
                )
                rec = _record(
                    paper_id,
                    draw,
                    pf,
                    deferral,
                    counting.attempts,
                    raw_capture[0] if raw_capture else None,
                    time.perf_counter() - started,
                )
            except Exception as exc:  # one draw's failure must not end the run
                rec = DrawRecord(
                    paper_id=paper_id,
                    draw=draw,
                    # keep whatever raw arrived before the failure: a draw that failed AFTER the
                    # model answered is a different event from one that failed before it, and the
                    # distinction is only recoverable here.
                    raw_status=getattr(
                        getattr(raw_capture[0], "motion_correction_method", None)
                        if raw_capture
                        else None,
                        "status",
                        None,
                    ),
                    raw_value=None,
                    raw_verbatim_quote=getattr(
                        getattr(raw_capture[0], "motion_correction_method", None)
                        if raw_capture
                        else None,
                        "verbatim_quote",
                        None,
                    ),
                    raw_ref_string=None,
                    raw_deferral_sentence=None,
                    raw_binding=None,
                    verbatim=None,
                    resolved=None,
                    resolution=None,
                    span_start=None,
                    span_end=None,
                    span_text=None,
                    span_section=None,
                    span_recovered=None,
                    extraction_arm="error",
                    left_missing_reason=None,
                    deferral_target_kind_original=None,
                    deferral_target_kind_stored=None,
                    deferral_ref=None,
                    completion_attempts=counting.attempts,
                    reask_occurred=counting.attempts > 1,
                    wall_seconds=round(time.perf_counter() - started, 3),
                    error=f"{type(exc).__name__}: {exc}",
                )
            rows.append(asdict(rec))
            print(
                f"{paper_id} draw {draw}/{args.k}: arm={rec.extraction_arm} "
                f"verbatim={rec.verbatim!r} resolved={rec.resolved!r} "
                f"attempts={rec.completion_attempts} wall={rec.wall_seconds}s"
            )
        dest = out_dir / f"{paper_id}.jsonl"
        with dest.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  -> {dest} ({len(rows)} draws)")

    manifest = out_dir / "manifest.json"
    manifest.write_text(
        json.dumps(_provenance(args.k, list(args.papers)), indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nprovenance header -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
