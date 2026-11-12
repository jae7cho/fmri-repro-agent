"""Checker-supplied values (pre-rerun item 2, 2026-11-11).

A checking-pass verdict of MISSED or WRONG that carries a value (``better_value``) and a sentence
(``relied_on``, resolved by the checking pass) is run through the extraction's own path,
``extractor._process_field``: the same span resolver and the same value-in-quote check, against the
same methods text. If it passes, the field takes that value, marked ``checker_supplied`` (schema
0.7.3), and is counted like an extracted value; if not, the verdict stays a flag on the line.

- Only a field the extraction left without a value (MISSING_FROM_PAPER) is filled. A value the
  extraction produced and that passed its checks (EXTRACTED or VARIED) is never overridden; a
  deferral is the paper's own statement and is left as it is.
- A verdict naming per-part values ("0.9 mm for task-fMRI; 0.2 mm for rest-fMRI", or
  "0.9 [task-fMRI]; 0.2 [rest-fMRI]") creates parts: the field becomes VARIED, each part through
  the variant path (``_process_varied``), whose applies_to check is the extraction's.
- A verdict on one part's line (``field[part]``) is about a value the extraction produced, so it is
  never acted on here.
- "not reported" as the better value is no value.

Every verdict considered is logged in the checking pass's record under ``supplied``: the field, the
value and sentence, the parts, and whether it was filled or stayed a flag (and why). No model call.
"""

from __future__ import annotations

import re
from typing import Any

#: better_value words that mean "no value"
_NO_VALUE = frozenset({"not reported", "not stated", "none", "n/a", "na", ""})

_FOR = re.compile(r"^(?P<value>.+?)\s+(?:for|in)\s+(?:the\s+)?(?P<part>.+)$", re.I)
_BRACKET = re.compile(r"^(?P<value>.+?)\s*\[(?P<part>[^\]]+)\]$")
_COLON = re.compile(r"^(?P<part>[^:]+):\s*(?P<value>.+)$")


def parse_parts(better: str, text: str = "") -> list[tuple[str, str]] | None:
    """``[(part, value), ...]`` when the better value names parts, else None. Segments are split on
    ";"; each must read "<value> for <part>", "<value> [<part>]" or (with two or more segments)
    "<part>: <value>" for the whole to count as parts. A single "<value> for <part>" segment is a
    part only when the part's words are in ``text`` (``quote_support.locate_phrase``), so a value
    that merely contains "for" stays one value."""
    from extractor_mvp.quote_support import locate_phrase

    segments = [s.strip() for s in better.split(";") if s.strip()]
    if not segments:
        return None
    out = []
    for seg in segments:
        m = _BRACKET.match(seg) or _FOR.match(seg)
        if m is None and len(segments) > 1:
            m = _COLON.match(seg)
        if m is None:
            return None
        out.append((m.group("part").strip(), m.group("value").strip()))
    if len(segments) == 1 and not _BRACKET.match(segments[0]):
        if locate_phrase(out[0][0], text) is None:
            return None
    return out


def _field(prep: Any, path: str) -> tuple[Any, str] | None:
    kind, _, name = path.partition(".")
    step = next((s for s in prep.steps if getattr(s, "kind", None) == kind), None)
    if step is None or not name or not hasattr(step, name):
        return None
    return step, name


def promote(preprocessing: Any, verifier: dict[str, Any] | None, text: str) -> list[dict[str, Any]]:
    """Fill the fields the checking pass supplied a passing value for, in place. Returns the log."""
    from fmri_repro.spec.provenance import Extracted, Varied

    from extractor_mvp.extraction_result import StepFieldResult, VariantResult
    from extractor_mvp.extractor import _process_field
    from extractor_mvp.rechecks import _spec_for

    log: list[dict[str, Any]] = []
    if not verifier or verifier.get("status") != "ok":
        return log
    for path, v in (verifier.get("fields") or {}).items():
        verdict = str(v.get("verdict") or "")
        better = str(v.get("better_value") or "").strip()
        quote = v.get("relied_on")
        if verdict not in ("missed", "wrong") or "[" in path:
            continue
        if better.lower() in _NO_VALUE or not quote:
            continue
        entry: dict[str, Any] = {
            "field": path,
            "verdict": verdict,
            "value": better,
            "quote": quote,
            "parts": None,
        }
        log.append(entry)
        if v.get("relied_on_resolved") is not True:
            entry["outcome"] = "flag: the checking pass's sentence did not resolve"
            continue
        where = _field(preprocessing, path)
        spec = _spec_for(path)
        if where is None or spec is None:
            entry["outcome"] = "flag: not a field the extraction path checks"
            continue
        step, name = where
        current = getattr(step, name)
        status = getattr(getattr(current, "extraction", None), "status", None)
        if status != "MISSING_FROM_PAPER":
            entry["outcome"] = f"flag: the field is {status}, never overridden"
            continue
        parts = parse_parts(better, text)
        entry["parts"] = [{"applies_to": p, "value": val} for p, val in parts] if parts else None
        if parts:
            fe = StepFieldResult(
                status="varied",
                variants=[
                    VariantResult(value=val, verbatim_quote=quote, applies_to=p) for p, val in parts
                ],
            )
        else:
            fe = StepFieldResult(status="extracted", value=better, verbatim_quote=quote)
        kwargs = {k: spec[k] for k in ("value_kind", "synonyms", "use_synonym_table") if k in spec}
        pf, diag, _ = _process_field(
            spec["field_id"], path, fe, spec["literal_type"], spec["t"], text, None, **kwargs
        )
        ext = pf.extraction
        if isinstance(ext, Extracted):
            new_ext: Any = ext.model_copy(update={"checker_supplied": True})
        elif isinstance(ext, Varied):
            new_ext = ext.model_copy(
                update={
                    "variants": [
                        x.model_copy(update={"checker_supplied": True}) for x in ext.variants
                    ]
                }
            )
        else:
            reason = diag.failure_reason if diag is not None else "no value checked"
            entry["outcome"] = f"flag: {reason}"
            continue
        setattr(step, name, pf.model_copy(update={"extraction": new_ext}))
        entry["outcome"] = "filled"
    return log
