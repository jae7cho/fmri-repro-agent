"""Batch MVP runner over a folder of PDFs (PDFs only; no DOI fetching).

Per-paper status taxonomy:
    success            — extraction completed; n_extracted may be 0 (e.g. a paper
                         that defers preprocessing to a citation)
    pdf_parse_failed   — pypdf returned empty / errored
    methods_not_found  — methods heuristic fell back to full text; extraction STILL
                         ran (non-fatal). Manually review high-n_missing papers
                         with this flag — the wrong section may have been processed.
    extraction_failed  — the LLM call errored or returned malformed JSON

Per-paper errors are caught and logged; the batch continues. Spans in the JSON
output are given in BOTH forms: ``span_in_slice`` (offsets into the methods
slice the model saw) and ``span_in_full_paper`` (offsets into the full PDF text).
"""

from __future__ import annotations

import csv
import dataclasses
import json
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from extractor_mvp.batch_config import BatchConfig, load_batch_config
from extractor_mvp.batch_utils import build_citation_resolver
from extractor_mvp.corpus import EXCLUDED_PAPERS, is_excluded
from extractor_mvp.extractor import INSTRUCTOR_MODE, ResolutionRecord, extract
from extractor_mvp.fmri_gate import ask_fmri, to_not_fmri_report
from extractor_mvp.grobid_source import (
    PYPDF,
    GrobidUnavailableError,
    grobid_text,
    text_source_requested,
)
from extractor_mvp.methods_finder import (
    MethodsSlice,
    find_methods_section,
    find_supplement_mri_section,
)
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text, pdf_creation_date, reflow_one_word_lines
from extractor_mvp.render import to_report

if TYPE_CHECKING:
    from extractor_mvp.citation_resolver import CitationResolver

# Multi-acquisition heuristic: ≥2 distinct DATASET mentions flags likely-multi.
# Pipeline tools alone don't flag (most papers cite several tools).
_DATASET_NAMES = ("HCP", "HNU", "MSC", "ABIDE", "UKBB")
_IGNORE_REASON = "not_targeted_by_mvp"  # the untargeted filler fields

#: Exceptions that are NEVER a property of one paper, and so must NOT be recorded as a paper's
#: status. A batch has two kinds of per-paper failure and they want opposite handling:
#:
#:   * DATA failures — an unparseable PDF, a model refusal, a validation error the extractor cannot
#:     recover from. These ARE properties of one paper. Recording ``extraction_failed`` and
#:     continuing is correct, and is what the broad catches below exist for.
#:   * CODE defects — an AttributeError from a removed field, a TypeError from a changed signature.
#:     These affect EVERY paper identically. Recording one as a paper status is wrong twice: it
#:     misattributes a tool failure to the paper, and it lets a batch finish green with every row
#:     corrupted. The motivating case is real — ``citation_resolver.py:124`` reads
#:     ``pf.extraction.confidence``, so removing that field would turn a programming error into 19
#:     papers' ``extraction_failed``, and only the live test reaches those lines.
#:
#: RE-RAISED rather than enumerating the data failures, for two measured reasons. First, this module
#: imports neither ``instructor`` nor ``litellm`` — ``extractor.build_client`` imports them lazily on
#: purpose — and ``instructor.exceptions`` is already deprecated in favour of ``instructor.core``, so
#: naming their types here would add heavy module-level imports on a moving path. Second, the obvious
#: base class does not hold: ``issubclass(litellm.exceptions.AuthenticationError,
#: litellm.exceptions.APIError)`` is **False**, because two different classes named
#: ``AuthenticationError`` sit in that MRO. A list of data-failure bases would silently miss siblings;
#: this list is stdlib and stable.
#:
#: Deliberately NOT included: ``IndexError`` and ``KeyError``. Both can be data-shaped — a model
#: returning an unexpected key or an empty sequence — so re-raising them would convert a data failure
#: into an aborted batch, which is this defect's mirror image.
_CODE_DEFECTS: tuple[type[BaseException], ...] = (
    AttributeError,
    TypeError,
    NameError,
    ImportError,
)

SUMMARY_COLUMNS = [
    "paper_id",
    "path",
    "status",
    "parser",
    "methods_found_via",
    "methods_header_matched",
    "likely_multi_acquisition",
    "n_extracted",
    "n_deferred",
    "n_deferral_quote_unresolved",
    "n_inferred_from_kb",
    "n_inferred_from_citation",
    "n_missing_not_stated",
    "n_missing_quote_unresolved",
    "n_value_not_in_literal",
    "error_message",
    # A render failure must reach the DURABLE record, not just stderr. On a 19-paper run a
    # RENDER-FAIL line exists only in scrollback; summary.csv/.md are what gets read after.
    # Safe to append: the one external reader (score_base_pipeline_tier_a.py) uses DictReader,
    # and multi_acquisition_batch.py carries its own separate column list.
    "render_error",
]


@dataclasses.dataclass(frozen=True)
class PaperResult:
    paper_id: str
    path: str
    status: str
    parser: str | None
    methods_found_via: str | None
    methods_header_matched: str | None
    likely_multi_acquisition: bool
    n_extracted: int
    n_deferred: int
    n_deferral_quote_unresolved: int
    n_inferred_from_kb: int
    n_inferred_from_citation: int
    n_missing_not_stated: int
    n_missing_quote_unresolved: int
    n_value_not_in_literal: int
    extraction_json: dict[str, Any] | None
    error_message: str | None
    #: The rendered COBIDAS completeness report (to_report). None on the error paths, and
    #: None if rendering itself failed — see ``render_error``, which is then set. Defaulted
    #: so the two early-return constructions above stay positional and unchanged.
    report: str | None = None
    render_error: str | None = None


def _count_distinct_datasets(text: str) -> int:
    return sum(1 for name in _DATASET_NAMES if re.search(rf"\b{name}\b", text))


def _tally(preprocessing: Any) -> dict[str, int]:
    """Bucket the targeted STEP fields by outcome (untargeted fillers ignored).

    Scope is ``preprocessing.steps`` only. ``base_pipeline`` is a sibling field of ``steps``
    on ``Preprocessing`` (``spec/preprocessing.py``), so it is outside this walk even though
    it IS a targeted field — ``_build_base_pipeline`` runs on every paper. The consequence is
    load-bearing and must not be read past: **``n_deferred`` counts deferred step fields, not
    papers that defer.** On the 2026-09-07 corpus it reads 0 for all 19 while braun_2015 and
    viduarre_2017 defer their base pipeline to a citation. Do not derive a corpus deferral
    rate from ``summary.csv``.

    Widening this to cover ``base_pipeline`` is NOT a one-line change and is deliberately not
    done here: 14 of the 31 base-pipeline-family rows in that corpus carry reasons this
    function does not map — 5 ``no_base_pipeline_named``, 6 ``version_deferred_to_kb``, and 3
    version rows with no reason at all — so they would fall through and be counted nowhere.
    Giving them buckets is a decision about what the summary columns mean, and belongs with
    A5. A5 itself is unaffected: it aggregates ``RowCoverage``, which comes from
    ``assess_coverage(flatten(...))`` and never touches this tally.
    """
    counts = {
        "n_extracted": 0,
        "n_deferred": 0,
        "n_deferral_quote_unresolved": 0,
        "n_inferred_from_kb": 0,
        "n_inferred_from_citation": 0,
        "n_missing_not_stated": 0,
        "n_missing_quote_unresolved": 0,
        "n_value_not_in_literal": 0,
    }
    for step in preprocessing.steps:
        structural = getattr(type(step), "STRUCTURAL_FIELDS", frozenset({"kind"}))
        for fname in type(step).model_fields:
            if fname in structural:
                continue  # ``kind`` and the structural pointers (distortion's intended_fieldmap)
            pf = getattr(step, fname)
            if pf is None:
                continue  # schema 0.5.2: an optional field absent from an older document
            # Inference-arm fills (orthogonal to the extraction buckets: a resolved
            # per-field deferral is both DEFERRED extraction and INFERRED inference).
            if pf.inference.status == "INFERRED_DEFAULT":
                basis_type = getattr(pf.inference.basis, "basis_type", None)
                if basis_type == "version_default":
                    counts["n_inferred_from_kb"] += 1
                elif basis_type == "prior_publication":
                    counts["n_inferred_from_citation"] += 1
            if pf.extraction.status == "EXTRACTED":
                counts["n_extracted"] += 1
                continue
            if pf.extraction.status == "DEFERRED_TO_CITATION":
                counts["n_deferred"] += 1
                continue
            reason = getattr(pf.inference, "reason", None) or ""
            if reason == _IGNORE_REASON:
                continue
            if reason.startswith("deferral_quote_unresolved"):
                counts["n_deferral_quote_unresolved"] += 1
            elif reason == "not_stated_in_text":
                counts["n_missing_not_stated"] += 1
            elif reason.startswith("extraction_quote_unresolved"):
                counts["n_missing_quote_unresolved"] += 1
            elif reason == "value_not_in_literal":
                counts["n_value_not_in_literal"] += 1
    return counts


#: A supplement shorter than this has no usable text layer (an image-only PDF), and is not read.
SUPPLEMENT_MIN_CHARS = 500


#: GROBID's flattened body is implausibly short (the author's ruling of 2026-11-08, after liu_2005:
#: a well-formed TEI whose body was 3,196 characters against pypdf's 50,672, in 5 lines; every other
#: corpus paper's body was 27,507 or more). Under either bound the paper is read with pypdf.
GROBID_MIN_SHARE = 0.25  # of the pypdf text's length, same PDF
GROBID_MIN_CHARS = 5000


def grobid_output_short(n_grobid: int, n_pypdf: int) -> bool:
    """True when GROBID's body is under ``GROBID_MIN_SHARE`` of pypdf's text or under
    ``GROBID_MIN_CHARS``, and pypdf's text is the longer of the two (falling back to a shorter text,
    e.g. an image-only PDF that pypdf cannot read either, would only lose text)."""
    if n_pypdf <= n_grobid:
        return False
    return n_grobid < GROBID_MIN_CHARS or n_grobid < GROBID_MIN_SHARE * n_pypdf


def load_text(path: Path) -> tuple[str, str, dict[str, Any]]:
    """The text-layer interface (the author's request of 2026-11-06): ``(text, parser, provenance)``.
    GROBID's flattened TEI body by default (since 2026-11-08), falling back to pypdf when the server
    cannot give it or its body is implausibly short (:func:`grobid_output_short`); pypdf when
    ``AESPA_TEXT_SOURCE=pypdf``. ``provenance`` is recorded on every record: ``text_source``
    (``grobid-<version>-<image>`` or ``pypdf``) and, after a fallback, why
    (``text_source_fallback``) and the reason's code (``text_source_fallback_reason``:
    ``grobid_unavailable`` or ``grobid_short_output``, the latter with both lengths)."""
    prov: dict[str, Any] = {
        "text_source": PYPDF,
        "text_source_fallback": None,
        "text_source_fallback_reason": None,
    }
    if text_source_requested() == "grobid":
        try:
            got = grobid_text(path)
        except GrobidUnavailableError as exc:
            prov["text_source_fallback"] = f"grobid unavailable: {exc}"
            prov["text_source_fallback_reason"] = "grobid_unavailable"
        else:
            text, parser = load_pdf_text(path)
            n_grobid, n_pypdf = len(got.text), len(text)
            if not grobid_output_short(n_grobid, n_pypdf):
                return got.text, "grobid", {**prov, "text_source": got.text_source}
            prov.update(
                text_source_fallback=(
                    f"grobid_short_output: {got.text_source} body {n_grobid} characters, "
                    f"pypdf text {n_pypdf} characters"
                ),
                text_source_fallback_reason="grobid_short_output",
                grobid_chars=n_grobid,
                pypdf_chars=n_pypdf,
            )
            return text, parser, prov
    text, parser = load_pdf_text(path)
    return text, parser, prov


def supplement_marker(name: str) -> str:
    """The line that joins the methods text and the supplement in the text the model reads."""
    return f"\n\n[Supplementary material, read with the paper: {name}]\n"


def load_supplement(path: Path) -> tuple[dict[str, Any], str]:
    """Fix 4 (2026-11-05): "see Supplementary Material" is not a citation. A ``<stem>_supp.pdf``
    beside the paper is read as part of it; the record says whether one was found and read, and why
    not. Returns the record and the supplement's text ("" when not read)."""
    supp = path.with_name(f"{path.stem}_supp.pdf")
    rec: dict[str, Any] = {
        "path": str(supp),
        "present": supp.is_file(),
        "read": False,
        "n_chars": 0,
        "reason": None,
        "text_reflow": None,
        "text_source": None,
    }
    if not rec["present"]:
        rec["reason"] = "no supplement beside the paper"
        return rec, ""
    text, parser, rec["text_source"] = load_text(supp)
    # 2026-11-05 (third round, item 4): a one-word-per-line layer is reflowed before slicing
    text, rec["text_reflow"] = reflow_one_word_lines(text)
    rec["n_chars"] = len(text)
    if parser == "failed" or len(text) < SUPPLEMENT_MIN_CHARS:
        rec["reason"] = f"no usable text layer ({len(text)} characters)"
        return rec, ""
    rec["read"] = True
    return rec, text


def _translate_spans(
    prep_dump: dict[str, Any],
    start_offset: int,
    supplement_start: int | None = None,
    supplement_offset: int = 0,
) -> None:
    """Add ``span_in_slice`` / ``span_in_full_paper`` to every extracted span (and, from 0.7.x, every
    variant's spans and the spans locating its part, and the step-order parts' spans).

    The model's spans are offsets into the methods slice; add the slice's
    ``start_offset`` to recover full-paper offsets. Mutates in place. A span at or after
    ``supplement_start`` (fix 4, 2026-11-05) lies in the supplement read with the paper: it gets
    ``span_in_supplement`` (offsets into the supplement's text) and no full-paper offsets.
    ``supplement_offset`` is where the slice of the supplement the model read starts in the
    supplement's text (the author's list of 2026-11-05, third round, item 1).
    """

    def annotate(span: dict[str, Any]) -> None:
        s, e = span["start"], span["end"]
        if supplement_start is not None and s >= supplement_start:
            span["span_in_supplement"] = {
                "start": s - supplement_start + supplement_offset,
                "end": e - supplement_start + supplement_offset,
            }
            return
        span["span_in_slice"] = {"start": s, "end": e}
        span["span_in_full_paper"] = {"start": s + start_offset, "end": e + start_offset}

    for step in prep_dump.get("steps", []):
        for value in step.values():
            if not isinstance(value, dict):
                continue
            extraction = value.get("extraction")
            if not isinstance(extraction, dict):
                continue
            if extraction.get("status") == "EXTRACTED":
                for span in extraction.get("spans", []):
                    annotate(span)
            elif extraction.get("status") == "VARIED":
                # 0.7.x (Stage 2b): each variant's value spans and the spans locating its part
                for variant in extraction.get("variants", []):
                    for span in variant.get("spans", []) + variant.get("applies_to_spans", []):
                        annotate(span)
    for part in prep_dump.get("step_order_parts") or []:
        for span in part.get("spans", []) + part.get("applies_to_spans", []):
            annotate(span)


def _methods_record(methods: MethodsSlice) -> dict[str, Any]:
    """The methods slice's metadata as the paper JSON stores it (``text`` is not stored)."""
    return {
        "found_via": methods.found_via,
        "matched_header": methods.matched_header,
        "start_offset": methods.start_offset,
        "end_offset": methods.end_offset,
        "slice_ratio": methods.slice_ratio,
        "ended_at": methods.ended_at,
        "suspicious": methods.suspicious,
        # fix 1a (2026-11-05): stored so a re-render says why the slice is the full text
        "fallback_reason": methods.fallback_reason,
    }


def process_paper(
    paper_id: str,
    path: Path,
    model: str,
    citation_resolver: CitationResolver | None = None,
    *,
    client: Any | None = None,
) -> PaperResult:
    """One PDF in, one :class:`PaperResult` out — the whole chain for a single paper.

    ``load_pdf_text`` → ``find_methods_section`` → ``ParsedPaper`` → ``extract`` →
    ``to_report``. Public because it is the unit both runners share: ``run_batch`` calls it
    per config entry, and ``extractor_mvp.report`` calls it once for a single PDF path.

    Depends on nothing batch-shaped. ``BatchConfig``, the papers list, the exclusion gate and
    the summary writers all live in :func:`run_batch`; ``citation_resolver`` is optional and
    defaults to None, which is the configuration every tracked batch config has run under
    (none sets ``citation_cache_dir``).

    Never raises for a bad paper. A parse failure, an LLM error and a render failure each
    come back as a populated field on the result — ``status``, ``error_message``,
    ``render_error`` — so a batch can continue. A single-paper caller has no batch to protect
    and should inspect ``report is None`` to decide its exit code.

    ``client`` (2026-11-05, fix 2): the one client every model call here uses (the fMRI gate, the
    extraction calls, the checking pass); None builds the default. ``full_report.run_paper`` passes
    a metered one.
    """
    text, parser, text_source = load_text(path)
    # 2026-11-05 (the author's list, third round, item 4): a one-word-per-line text layer is
    # reflowed before slicing; every offset below is into the reflowed text
    text, text_reflow = reflow_one_word_lines(text)
    if parser == "failed":
        return PaperResult(
            paper_id,
            str(path),
            "pdf_parse_failed",
            None,
            None,
            None,
            False,
            0,  # n_extracted
            0,  # n_deferred
            0,  # n_deferral_quote_unresolved
            0,  # n_inferred_from_kb
            0,  # n_inferred_from_citation
            0,  # n_missing_not_stated
            0,  # n_missing_quote_unresolved
            0,  # n_value_not_in_literal
            None,
            "pypdf returned no text",
        )

    methods = find_methods_section(text, text_source=parser)
    # fix 1b (2026-11-05): one cheap call first; a paper with no fMRI gets a report that says so and
    # no extraction. Only a "no" whose sentence resolves stops it (fmri_gate.py).
    fmri_gate = ask_fmri(text, model, client=client)
    if fmri_gate["stop"]:
        return PaperResult(
            paper_id,
            str(path),
            "not_fmri",
            parser,
            methods.found_via,
            methods.matched_header,
            False,
            0,  # n_extracted: nothing was extracted
            0,  # n_deferred
            0,  # n_deferral_quote_unresolved
            0,  # n_inferred_from_kb
            0,  # n_inferred_from_citation
            0,  # n_missing_not_stated
            0,  # n_missing_quote_unresolved
            0,  # n_value_not_in_literal
            {
                "methods": _methods_record(methods),
                "text_reflow": text_reflow,
                "text_source": text_source,
                "instructor_mode": INSTRUCTOR_MODE,
                "fmri_gate": fmri_gate,
            },
            None,
            to_not_fmri_report(paper_id, fmri_gate),
            None,
        )
    multi = _count_distinct_datasets(methods.text) >= 2
    # fix 4 (2026-11-05): a supplement beside the paper is read with it (first hop), after the
    # methods text and a marker line; the checking pass reads it too
    supplement, supp_text = load_supplement(path)
    # 2026-11-05 (the author's list, second round, item 2): the reference list is out of the text
    # the model reads, not only out of the software scan's. A slice that runs past the paper's last
    # reference heading (a full-text fallback) stops there; so does the supplement's text.
    from extractor_mvp.software_scan import _body_end

    body_end = _body_end(text)
    refs_cut = methods.start_offset + len(methods.text) > body_end
    extraction_text = (
        methods.text[: max(0, body_end - methods.start_offset)] if refs_cut else methods.text
    )
    full_text = text[:body_end]
    if supplement["read"]:
        supp_body = _body_end(supp_text)
        supplement["references_excluded_from"] = supp_body if supp_body < len(supp_text) else None
        supp_text = supp_text[:supp_body]
    # the author's list of 2026-11-05, third round, item 1: a supplement is sliced like a paper, to
    # its MRI and preprocessing sections; the whole supplement when it has no such heading
    supp_offset = 0
    if supplement["read"]:
        supp_slice = find_supplement_mri_section(supp_text)
        supplement["slice"] = _methods_record(supp_slice)
        supplement["n_chars_read"] = len(supp_slice.text)
        supp_text, supp_offset = supp_slice.text, supp_slice.start_offset
    supp_start: int | None = None
    if supplement["read"]:
        marker = supplement_marker(Path(supplement["path"]).name)
        supp_start = len(extraction_text) + len(marker)
        extraction_text = extraction_text + marker + supp_text
        full_text = full_text + marker + supp_text
    paper = ParsedPaper(
        text=extraction_text, source=paper_id, parser="pypdf", pdf_date=pdf_creation_date(path)
    )

    resolutions: list[ResolutionRecord] = []
    motion_inference: list[Any] = []  # the motion method's inference record (2026-10-28)
    coverage_out: list[Any] = []  # the coverage calls' record-level answers (item 5, 2026-10-28)
    verifier_out: list[Any] = []  # the checking pass's record (report v2 §3, 2026-10-29)
    # Wall time of ``extract`` alone -- the four model calls, assembly and deferral resolution; not
    # the PDF parse or the render (DESIGN_coverage_expansion.md B8). Stored as ``wall_time_s``.
    t0 = time.perf_counter()
    try:
        preprocessing, diagnostics, deferrals = extract(
            paper,
            model,
            # fix 2 (2026-11-05): one client for every call, so a caller can meter them all
            client=client,
            citation_resolver=citation_resolver,
            paper_date=paper.pdf_date,
            resolutions=resolutions,
            motion_inference_out=motion_inference,
            coverage_out=coverage_out,
            verifier_out=verifier_out,
            # fix 1a (2026-11-05): a suspicious slice is not trusted to hold what the checking pass
            # needs, so it reads the full text (on a fallback the slice is the full text already)
            verifier_text=full_text if methods.suspicious else None,
        )
    except _CODE_DEFECTS:
        # A tool defect, not this paper's problem. Let it abort the run loudly rather than write 19
        # rows of extraction_failed that blame the corpus for a bug. See _CODE_DEFECTS.
        raise
    except Exception as exc:  # LLM/transport/validation error -> recorded, batch continues
        return PaperResult(
            paper_id,
            str(path),
            "extraction_failed",
            parser,
            methods.found_via,
            methods.matched_header,
            multi,
            0,  # n_extracted
            0,  # n_deferred
            0,  # n_deferral_quote_unresolved
            0,  # n_inferred_from_kb
            0,  # n_inferred_from_citation
            0,  # n_missing_not_stated
            0,  # n_missing_quote_unresolved
            0,  # n_value_not_in_literal
            None,
            f"{type(exc).__name__}: {exc}",
        )

    # Rendered HERE, not in run_batch: to_report's suspicious-methods warning needs the live
    # MethodsSlice, and extraction_json["methods"] carries only its metadata — not `text` — so
    # run_batch cannot rebuild one. Rendering there would silently drop the warning on exactly
    # the papers most likely to be wrong.
    #
    # Narrowly guarded: to_report is pure and deterministic, but an exception escaping here
    # would discard a paid-for extraction before run_batch writes it. The failure is recorded
    # and printed, never swallowed.
    verifier = verifier_out[0] if verifier_out else None
    # F3a (2026-10-29): the multiple_pipelines answer comes from the checking pass now
    multiple_pipelines = (verifier or {}).get("multiple_pipelines")
    report: str | None = None
    render_error: str | None = None
    # 2026-11-09 (the author's item 2): the checking pass's value for a field the extraction left
    # unverifiable, when it relied on the same quote (rechecks.checker_supplied); no model call
    from extractor_mvp.rechecks import checker_supplied as _checker_supplied

    supplied = _checker_supplied(
        {
            "preprocessing": preprocessing.model_dump(mode="json"),
            "diagnostics": [dataclasses.asdict(d) for d in diagnostics],
            "verifier": verifier,
        }
    )
    try:
        supplement["fields_deferred"] = [
            d.field for d in deferrals if d.target_kind == "supplement"
        ]
        report = to_report(
            preprocessing,
            source=paper_id,
            methods_slice=methods,
            motion_inference=(motion_inference[0] if motion_inference else None),
            multiple_pipelines=multiple_pipelines,
            verifier=verifier,
            supplement=supplement,
            checker_supplied=supplied,
        )
    except _CODE_DEFECTS:
        # Same split, and sharper here: the comment above argues to_report is pure and
        # deterministic, so a code defect in it is identical on every paper by construction.
        raise
    except Exception as exc:
        render_error = f"{type(exc).__name__}: {exc}"

    wall_time_s = round(time.perf_counter() - t0, 3)

    counts = _tally(preprocessing)
    prep_dump = preprocessing.model_dump(mode="json")
    supplement["fields_deferred"] = [d.field for d in deferrals if d.target_kind == "supplement"]
    supplement["start_in_extraction_text"] = supp_start
    _translate_spans(prep_dump, methods.start_offset, supp_start, supp_offset)
    extraction_json = {
        "methods": _methods_record(methods),
        # 2026-11-05 (third round, item 4): line counts and one-word shares, or None if not reflowed
        "text_reflow": text_reflow,
        # 2026-11-06: which text layer the paper was read from (grobid-<version>-<image> or pypdf)
        "text_source": text_source,
        "supplement": supplement,  # fix 4 (2026-11-05): found, read, why not, and what defers to it
        # where the reference list was cut from the extraction text (an offset into the paper), or None
        "references_excluded_from": body_end if refs_cut else None,
        "fmri_gate": fmri_gate,  # fix 1b (2026-11-05): the gate's answer, also when it let the paper on
        "likely_multi_acquisition": multi,
        "instructor_mode": INSTRUCTOR_MODE,  # 2026-11-03: a vintage is prompts AND mode
        "wall_time_s": wall_time_s,
        "counts": counts,
        "preprocessing": prep_dump,
        "diagnostics": [dataclasses.asdict(d) for d in diagnostics],
        # The motion method's inference record (DESIGN_motion_inference_arm.md): both paths of F1
        # travel here with basis and source -- the arm proper is also on the field; the
        # described_only diagnostic lives ONLY here.
        "motion_inference": (motion_inference[0].as_dict() if motion_inference else None),
        # Item 5 (2026-10-28): the two calls' record-level answers -- whether the text describes
        # more than one preprocessing variant, with quote and count -- stored as dumped fields by
        # call so the renderer and the re-render script read one shape.
        "multiple_pipelines": multiple_pipelines,
        # report v2 §3 (2026-10-29): the checking pass, verdicts by field path; the extraction arms
        # above are untouched by it
        "verifier": verifier,
        # 2026-11-09 (item 2): values the checking pass supplied for unverifiable fields
        "checker_supplied": supplied,
        # SUCCESS-path capture: raw LLM value + resolved value/alias for each
        # successfully-extracted targeted field (diagnostic-only; see ResolutionRecord).
        "resolutions": [dataclasses.asdict(r) for r in resolutions],
        # Fork B reads deferred_fields to drive citation resolution without parsing
        # the provenance coupling. target_kind is the ORIGINAL LLM value (incl
        # "supplement"); pending_resolution flags fields awaiting Fork B.
        "deferred_fields": [dataclasses.asdict(d) for d in deferrals],
    }
    status = "methods_not_found" if methods.found_via == "fallback_full_text" else "success"
    return PaperResult(
        paper_id,
        str(path),
        status,
        parser,
        methods.found_via,
        methods.matched_header,
        multi,
        counts["n_extracted"],
        counts["n_deferred"],
        counts["n_deferral_quote_unresolved"],
        counts["n_inferred_from_kb"],
        counts["n_inferred_from_citation"],
        counts["n_missing_not_stated"],
        counts["n_missing_quote_unresolved"],
        counts["n_value_not_in_literal"],
        extraction_json,
        None,
        report,
        render_error,
    )


def run_batch(config: BatchConfig) -> list[PaperResult]:
    """Process all papers; per-paper errors are caught so the batch continues."""
    papers_dir = config.output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    citation_resolver = build_citation_resolver(config)
    results: list[PaperResult] = []
    total_present = len(config.papers)
    excluded_present: list[str] = []

    for paper in config.papers:
        # Excluded papers are skipped BEFORE extraction (saves LLM calls) but recorded, never
        # silently dropped — see extractor_mvp.corpus.EXCLUDED_PAPERS.
        if is_excluded(paper.paper_id):
            excluded_present.append(paper.paper_id)
            print(f"  SKIP {paper.paper_id}: excluded from corpus statistics")
            continue
        result = process_paper(paper.paper_id, paper.path, config.model, citation_resolver)
        results.append(result)
        if result.extraction_json is not None:
            (papers_dir / f"{paper.paper_id}.json").write_text(
                json.dumps(
                    {
                        "paper_id": result.paper_id,
                        "path": result.path,
                        "status": result.status,
                        **result.extraction_json,
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        # The completeness report, alongside papers/{paper_id}.json. Written AFTER the JSON so
        # a report write cannot cost the extraction it describes.
        if result.report is not None:
            (papers_dir / f"{paper.paper_id}.md").write_text(result.report, encoding="utf-8")
        elif result.render_error is not None:
            print(
                f"  RENDER-FAIL {paper.paper_id}: {result.render_error} "
                "(extraction kept; no report written)",
                file=sys.stderr,
            )
        # loud on failure, quiet on success
        if result.status in ("pdf_parse_failed", "extraction_failed"):
            print(
                f"  FAIL {paper.paper_id}: {result.status} — {result.error_message}",
                file=sys.stderr,
            )
        else:
            if result.status == "not_fmri":
                print(f"  stop {paper.paper_id}: no fMRI in this paper (fMRI gate)")
                continue
            flags = []
            if result.status == "methods_not_found":
                flags.append("methods_not_found")
            if result.likely_multi_acquisition:
                flags.append("likely_multi_acquisition")
            suffix = f" [{', '.join(flags)}]" if flags else ""
            print(f"  ok   {paper.paper_id}: {result.n_extracted} extracted{suffix}")

    _write_summary_csv(config.output_dir / "summary.csv", results)
    _write_summary_md(config.output_dir / "summary.md", results, excluded_present, total_present)
    _print_rollup(results, config.output_dir, excluded_present, total_present)
    return results


def _write_summary_csv(path: Path, results: list[PaperResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        w.writeheader()
        for r in results:
            w.writerow({k: getattr(r, k) for k in SUMMARY_COLUMNS})


def _write_summary_md(
    path: Path, results: list[PaperResult], excluded: list[str], total_present: int
) -> None:
    n_analysed = total_present - len(excluded)
    lines = [
        f"Corpus: {total_present} PDFs present · {len(excluded)} excluded · N = {n_analysed}",
        "",
    ]
    header = "| " + " | ".join(SUMMARY_COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in SUMMARY_COLUMNS) + " |"
    lines += [header, sep]
    for r in sorted(results, key=lambda r: (r.status, r.paper_id)):
        lines.append("| " + " | ".join(str(getattr(r, k)) for k in SUMMARY_COLUMNS) + " |")
    if excluded:
        lines += ["", "## Excluded papers", ""]
        for pid in excluded:
            lines.append(f"- **{pid}** — {EXCLUDED_PAPERS[pid]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_rollup(
    results: list[PaperResult], output_dir: Path, excluded: list[str], total_present: int
) -> None:
    ok = [r for r in results if r.status in ("success", "methods_not_found")]
    failed = [r for r in results if r.status in ("pdf_parse_failed", "extraction_failed")]
    x = sum(r.n_extracted for r in ok)
    d = sum(r.n_deferred for r in ok)
    y = sum(r.n_missing_not_stated for r in ok)
    z = sum(r.n_missing_quote_unresolved for r in ok)
    w = sum(r.n_value_not_in_literal for r in ok)
    print(
        f"Corpus: {total_present} PDFs present · {len(excluded)} excluded · "
        f"N = {total_present - len(excluded)}."
    )
    print(
        f"Processed {len(results)} papers ({len(ok)} successful, {len(failed)} failed). "
        f"Across successes: {x} fields extracted with spans, {d} deferred-to-citation, "
        f"{y} missing-not-stated, {z} quote-unresolved, {w} value-not-in-literal."
    )
    print(f"Summary: {output_dir / 'summary.csv'} , {output_dir / 'summary.md'}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", required=True, type=Path, help="batch config YAML")
    args = parser.parse_args(argv)
    if not args.config.is_file():
        print(f"ERROR: config not found: {args.config}", file=sys.stderr)
        return 1
    run_batch(load_batch_config(args.config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
