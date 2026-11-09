"""The author's items 2 and 3 of 2026-11-09, applied to a STORED record with no model call.

* :func:`checker_supplied` -- item 2's second half: when the checking pass says WRONG on a field the
  extraction left unverifiable and gives a value, relying on the same quote the extraction gave, that
  value is recorded with provenance ``checker-supplied`` instead of the field staying unverifiable.
  The provenance contract (``fmri_repro.spec.provenance``, frozen) has no arm for a value the paper
  did not yield through the extraction, so the value travels beside the field, like the motion
  inference record, and the report renders it on the field's line.
* :func:`recheck_record` -- the new value-in-quote rules (item 2) and glyph normalisation (item 3)
  re-run on every field the stored record left unverifiable for a quote reason, through the same
  ``extractor._process_field`` the extraction uses, against the same methods slice of the same text
  layer. A field that now passes becomes EXTRACTED with its span; nothing else changes.
* :func:`unverifiable_fields` -- the fields counted as unverifiable: a MISSING field whose reason is an
  unverifiable gap base (``cobidas._UNVERIFIABLE_GAP_BASES``), less the checker-supplied ones.
"""

from __future__ import annotations

import copy
from typing import Any

from extractor_mvp.cobidas import _UNVERIFIABLE_GAP_BASES, _gap_base
from extractor_mvp.span_resolver import normalize_with_offset_map

#: The diagnostic reasons a re-check can change: the quote-support rejection (item 2) and an
#: unresolved quote (item 3's glyphs). The motion field is re-run with its own post-check.
RECHECK_REASONS: tuple[str, ...] = ("value_unsupported_by_quote", "extraction_quote_unresolved")
CHECKER_SUPPLIED = "checker-supplied"


def _norm(s: str | None) -> str:
    return " ".join(normalize_with_offset_map((s or "").lower())[0].split())


def same_quote(a: str | None, b: str | None) -> bool:
    """The checking pass's sentence and the extraction's quote are the same quote: equal after the
    span resolver's normalisation and whitespace collapse, or one contains the other (the checking
    pass often quotes the whole sentence around the extraction's clause)."""
    na, nb = _norm(a), _norm(b)
    return bool(na and nb) and (na == nb or na in nb or nb in na)


def _fields(record: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for step in (record.get("preprocessing") or {}).get("steps", []):
        kind = step.get("kind")
        for key, value in step.items():
            if isinstance(value, dict) and "extraction" in value and "inference" in value:
                out.append((f"{kind}.{key}", value))
    return out


def _unverifiable_reason(pf: dict[str, Any]) -> str | None:
    if pf["extraction"].get("status") != "MISSING_FROM_PAPER":
        return None
    reason = (pf.get("inference") or {}).get("reason")
    return reason if _gap_base(reason) in _UNVERIFIABLE_GAP_BASES else None


def checker_supplied(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Item 2b over a stored record: the unverifiable fields the checking pass judged WRONG with a
    value of its own, relying on the extraction's own quote. One entry per field."""
    verifier = record.get("verifier") or {}
    if verifier.get("status") != "ok":
        return []
    verdicts = verifier.get("fields") or {}
    quotes = {d.get("field"): d.get("raw_quote") for d in record.get("diagnostics") or []}
    out: list[dict[str, Any]] = []
    for path, pf in _fields(record):
        if _unverifiable_reason(pf) is None:
            continue
        v = verdicts.get(path) or {}
        better = v.get("better_value")
        if str(v.get("verdict", "")).lower() != "wrong" or not better:
            continue
        if not same_quote(v.get("relied_on"), quotes.get(path)):
            continue
        out.append(
            {
                "field": path,
                "value": better,
                "quote": v.get("relied_on"),
                "provenance": CHECKER_SUPPLIED,
                "reason": v.get("reason"),
            }
        )
    return out


def unverifiable_fields(record: dict[str, Any]) -> list[str]:
    """Dotted paths of the fields counted unverifiable (checker-supplied ones excluded)."""
    supplied = {c["field"] for c in checker_supplied(record)}
    return [
        path
        for path, pf in _fields(record)
        if _unverifiable_reason(pf) is not None and path not in supplied
    ]


def _spec_for(dotted: str) -> dict[str, Any] | None:
    from extractor_mvp.coverage_fields import COVERAGE_SPECS
    from extractor_mvp.extractor import _FIELD_SPECS

    for spec in COVERAGE_SPECS:
        if spec.dotted == dotted:
            return {
                "field_id": spec.field_id,
                "literal_type": spec.literal_type,
                "t": spec.t,
                "value_kind": spec.value_kind,
                "synonyms": (spec.synonyms, spec.underspecified)
                if spec.synonyms is not None
                else None,
                "use_synonym_table": False,
            }
    from extractor_mvp.extractor import _MOTION_FIELD_SPEC

    if dotted == _MOTION_FIELD_SPEC[2]:
        # the motion method: the same _process_field call as extract_motion_method, then its own
        # post-check (motion_post_check) in recheck_record
        _a, fid, _d, literal_type, t = _MOTION_FIELD_SPEC
        return {"field_id": fid, "literal_type": literal_type, "t": t, "use_synonym_table": False}
    for _attr, fid, d, literal_type, t in _FIELD_SPECS:
        if d == dotted:
            return {"field_id": fid, "literal_type": literal_type, "t": t}
    return None


def _intensity_value(record: dict[str, Any]) -> float | None:
    for step in (record.get("preprocessing") or {}).get("steps", []):
        if step.get("kind") == "intensity_normalization":
            ext = (step.get("value") or {}).get("extraction") or {}
            if ext.get("status") == "EXTRACTED":
                try:
                    return float(ext["value"])
                except (TypeError, ValueError):
                    return None
    return None


def _checker_kept_the_gap(rec: dict[str, Any], dotted: str, pf: Any, spec: dict[str, Any]) -> bool:
    """True when the re-checked value is one item 2 leaves to the checking pass (its support check
    returns None) and the stored checking pass judged the field ``supported`` (the gap is right) or
    ``wrong`` with a value of its own."""
    from extractor_mvp.quote_support import coverage_value_supported, step_value_supported

    if dotted == "motion_correction.method":
        return False  # its own literal post-check passed (motion_post_check), as for a tool name
    value = pf.extraction.value
    text = pf.extraction.spans[0].text
    check = (
        coverage_value_supported(dotted, value, text)
        if "value_kind" in spec
        else step_value_supported(dotted, value, text)
    )
    if check is not None:
        return False
    verifier = rec.get("verifier") or {}
    v = (verifier.get("fields") or {}).get(dotted) if verifier.get("status") == "ok" else None
    if not v:
        return False
    verdict = str(v.get("verdict", "")).lower()
    return verdict == "supported" or (verdict == "wrong" and bool(v.get("better_value")))


def recheck_record(record: dict[str, Any], text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-run items 2 and 3 on a stored record's quote-failed fields. ``text`` is the paper's text as
    the extraction read it (``batch.load_text`` then ``reflow_one_word_lines``); the methods slice is
    rebuilt from the record's stored offsets. Returns ``(new record, summary)``; the input is not
    mutated. A field whose re-check passes becomes EXTRACTED (its diagnostic is dropped); any other
    outcome leaves the field exactly as stored."""
    from extractor_mvp.batch import _translate_spans
    from extractor_mvp.extraction_result import FieldExtractionResult
    from extractor_mvp.extractor import _process_field
    from extractor_mvp.motion_guard import motion_post_check
    from extractor_mvp.quote_support import is_operation_word_only

    rec = copy.deepcopy(record)
    summary: dict[str, Any] = {"rechecked": [], "now_extracted": [], "unchanged": [], "skipped": []}
    methods = rec.get("methods") or {}
    start = int(methods.get("start_offset") or 0)
    end = int(methods.get("end_offset") or len(text))
    cut = rec.get("references_excluded_from")
    slice_text = text[start : min(end, cut) if cut else end]
    steps = {s.get("kind"): s for s in (rec.get("preprocessing") or {}).get("steps", [])}
    kept: list[dict[str, Any]] = []
    for d in rec.get("diagnostics") or []:
        dotted = str(d.get("field") or "")
        base = str(d.get("failure_reason") or "").split(":", 1)[0]
        kind = dotted.partition(".")[0]
        spec = _spec_for(dotted) if base in RECHECK_REASONS else None
        step = steps.get(kind)
        if spec is None or step is None:
            if base in RECHECK_REASONS:
                summary["skipped"].append(dotted)
            kept.append(d)
            continue
        current = step.get(spec["field_id"]) or {}
        # any field the extraction left MISSING for this quote reason, whatever its inference arm (a
        # stored KB-filled arm is what a fresh extraction would not have written once the quote resolves)
        missing = (current.get("extraction") or {}).get("status") == "MISSING_FROM_PAPER"
        if not missing or d.get("raw_value") is None:
            kept.append(d)
            continue
        summary["rechecked"].append(dotted)
        fe = FieldExtractionResult(
            status="extracted", value=str(d["raw_value"]), verbatim_quote=str(d.get("raw_quote"))
        )
        kwargs = {k: spec[k] for k in ("value_kind", "synonyms", "use_synonym_table") if k in spec}
        ctx = _intensity_value(rec) if dotted == "intensity_normalization.convention" else None
        pf, _diag, _deferral = _process_field(
            spec["field_id"], dotted, fe, spec["literal_type"], spec["t"], slice_text, ctx, **kwargs
        )
        value = getattr(pf.extraction, "value", None)
        if (
            pf.extraction.status == "EXTRACTED"
            and dotted == "motion_correction.method"
            and motion_post_check(fe.value, fe.verbatim_quote) is not None
        ):
            # the motion post-check rejects or routes the value: left as stored (the routing
            # fallback is the extraction's to apply, not a re-check's)
            summary["unchanged"].append(dotted)
            kept.append(d)
            continue
        if pf.extraction.status == "EXTRACTED" and _checker_kept_the_gap(rec, dotted, pf, spec):
            # a value item 2 leaves to the checking pass, which in this stored run judged the field
            # and either endorsed the gap or supplied its own value (checker_supplied): its judgement
            # stands, since no model call is made here to judge the restored value
            summary["unchanged"].append(dotted)
            kept.append(d)
            continue
        if pf.extraction.status == "EXTRACTED" and not is_operation_word_only(
            dotted, str(getattr(value, "verbatim", "") or "")
        ):
            step[spec["field_id"]] = pf.model_dump(mode="json")
            summary["now_extracted"].append(dotted)
            continue
        summary["unchanged"].append(dotted)
        kept.append(d)
    rec["diagnostics"] = kept
    supp = rec.get("supplement") or {}
    supp_slice = supp.get("slice") or {}
    _translate_spans(
        rec["preprocessing"],
        start,
        supp.get("start_in_extraction_text"),
        int(supp_slice.get("start_offset") or 0),
    )
    rec["rechecks"] = {"date": "2026-11-09", **summary}
    return rec, summary
