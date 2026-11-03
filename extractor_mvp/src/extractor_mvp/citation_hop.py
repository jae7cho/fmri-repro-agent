"""The citation hop: one hop into a paper the citing paper defers to.

``docs/design/DESIGN_citation_hop.md``, its forks ratified by the author on 2026-11-03. Case one is
gracia-tabuenca_2024 -> Hagler et al. (2019). The hop:

1. finds the deferral's entry in the citing paper's own reference list (:func:`parse_reference_list`,
   :func:`match_reference`), and stops on a ref that matches no entry or more than one;
2. resolves that entry to a local PDF by first author and year (:func:`resolve_local_pdf`); PubMed
   Central is the design's next tier and is not built for case one;
3. runs the same coverage calls T and S on the cited paper's methods, with a pinned addendum that
   names the fields asked and asks for per-variant values (:data:`HOP_ADDENDUM`), then the
   checking pass over that scoped draft;
4. returns a ``second_hop`` record, stored BESIDE the citing paper's record. Nothing here writes
   into the citing paper's ``Preprocessing``, so its COBIDAS assessment cannot see a second-hop
   value; the renderer shows them "as described in <ref>, cited by this paper".

One hop only: the cited paper's own deferrals are recorded and never followed.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from extractor_mvp.cobidas import assess_coverage, row_state
from extractor_mvp.coverage_extractor import (
    SPATIAL_PROMPT,
    TEMPORAL_VOLUME_PROMPT,
    CoverageExtraction,
    SoftwareMentionResult,
    _process,
    _process_software,
    _response_model,
)
from extractor_mvp.coverage_fields import CALL_S_SPECS, CALL_T_SPECS, CoverageFieldSpec
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.span_resolver import resolve_quote

# ---------------------------------------------------------------------------
# 1. The reference list
# ---------------------------------------------------------------------------

_REF_HEADING = re.compile(
    r"^[ \t]*(?:\d+\.?[ \t]*)?(references|bibliography|literature cited|works cited)[ \t]*:?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_NUMBERED_START = re.compile(r"[ \t]*\[?(\d{1,3})[\].][ \t]+\S")
_SURNAME = r"[A-Z\u00c0-\u00de][A-Za-z\u00c0-\u017f'\-]+(?:[ \-][A-Z\u00c0-\u00de][A-Za-z\u00c0-\u017f'\-]+)?"
_AUTHOR_START = re.compile(rf"[ \t]*(?P<surname>{_SURNAME}),[ \t]+[A-Z\u00c0-\u00de]")
_YEAR = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class RefEntry:
    """One reference-list entry, as offsets into the citing paper's own text."""

    start: int
    end: int
    text: str
    number: str | None
    first_author: str | None
    year: str | None
    doi: str | None


def _norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _surname_keys(first_author: str) -> set[str]:
    """The forms a first author's surname may take: the whole name and its first word, so a
    generational suffix does not hide it ("Hagler Jr" -> "hagler"; gracia-tabuenca_2024's reference
    list writes it so)."""
    words = first_author.split()
    return {_norm_name(first_author), _norm_name(words[0])} if words else set()


def parse_reference_list(text: str) -> list[RefEntry]:
    """The entries of the LAST reference heading's section, split at lines that start an entry
    (a number, or "Surname, I") after a line ending in a period, a DOI or a URL. Empty when the
    text has no reference heading."""
    headings = list(_REF_HEADING.finditer(text))
    if not headings:
        return []
    sec_start = headings[-1].end()
    starts: list[int] = []
    prev_line = "."
    pos = sec_start
    for line in text[sec_start:].splitlines(keepends=True):
        stripped_prev = prev_line.rstrip()
        boundary = (
            not starts
            or stripped_prev.endswith(".")
            or _DOI.search(stripped_prev.split(" ")[-1] if stripped_prev else "") is not None
            or stripped_prev.lower().startswith("http")
        )
        if line.strip() and boundary and (_NUMBERED_START.match(line) or _AUTHOR_START.match(line)):
            starts.append(pos + (len(line) - len(line.lstrip())))
        if line.strip():
            prev_line = line
        pos += len(line)
    entries: list[RefEntry] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        body = text[s:e].rstrip()
        e = s + len(body)
        num = _NUMBERED_START.match(body)
        author_body = body[num.end() - 1 :] if num else body
        auth = _AUTHOR_START.match(author_body)
        year = _YEAR.search(body)
        doi = _DOI.search(" ".join(body.split()))
        entries.append(
            RefEntry(
                start=s,
                end=e,
                text=body,
                number=num.group(1) if num else None,
                first_author=auth.group("surname") if auth else None,
                year=year.group(1) if year else None,
                doi=doi.group(1).rstrip(".,;)") if doi else None,
            )
        )
    return entries


_NOT_SURNAMES = frozenset({"ref", "refs", "see", "et", "al", "and", "in", "as"})


@dataclasses.dataclass(frozen=True)
class RefMatch:
    """One cited target behind a deferral's ref: its state and, when resolved, its entry."""

    part: str  # the author-year or the number the match was made on
    state: str  # resolved | reference_not_found | reference_ambiguous | no_reference_section
    entry: RefEntry | None = None


def match_reference(ref_string: str, entries: list[RefEntry]) -> list[RefMatch]:
    """The targets behind a deferral's ref. An author-year ref ("Hagler et al. (2019)") is matched on
    first author and year; a numbered ref ("45", "refs. 47 and 48") on each number, one target per
    number (fork C). Never picks between two matching entries."""
    if not entries:
        return [RefMatch(ref_string, "no_reference_section")]
    year = _YEAR.search(ref_string)
    words = [w for w in re.findall(r"[A-Za-z\u00c0-\u017f'\-]+", ref_string)]
    surname = next((w for w in words if w[0].isupper() and w.lower() not in _NOT_SURNAMES), None)
    if year and surname:
        part = f"{surname} {year.group(1)}"
        hits = [
            e
            for e in entries
            if e.first_author
            and _norm_name(surname) in _surname_keys(e.first_author)
            and e.year == year.group(1)
        ]
        return [_one(part, hits)]
    numbers = re.findall(r"\b\d{1,3}\b", ref_string)
    if numbers:
        return [_one(n, [e for e in entries if e.number == n]) for n in numbers]
    return [RefMatch(ref_string, "reference_not_found")]


def _one(part: str, hits: list[RefEntry]) -> RefMatch:
    if not hits:
        return RefMatch(part, "reference_not_found")
    if len(hits) > 1:
        return RefMatch(part, "reference_ambiguous")
    return RefMatch(part, "resolved", hits[0])


# ---------------------------------------------------------------------------
# 2. The target: a local PDF (PubMed Central is the design's next tier, not built for case one)
# ---------------------------------------------------------------------------


def resolve_local_pdf(entry: RefEntry, corpus_dirs: list[Path]) -> tuple[str, Path | None]:
    """``("local_pdf", path)`` when exactly one PDF in the corpus folders is named
    ``<FirstAuthor>_<year>.pdf`` (exact after lowercasing and stripping accents, the rule
    ``paper_fetcher.py`` states); otherwise a reported state and None."""
    if not entry.first_author or not entry.year:
        return "no_local_pdf", None
    want = {f"{k}_{entry.year}" for k in _surname_keys(entry.first_author)}
    hits = sorted(
        {
            p.resolve()
            for d in corpus_dirs
            if d.is_dir()
            for p in d.glob("*.pdf")
            if _norm_name(p.stem) in want
        }
    )
    if not hits:
        return "no_local_pdf", None
    if len(hits) > 1:
        return "local_pdf_ambiguous", None
    return "local_pdf", hits[0]


# ---------------------------------------------------------------------------
# 3. The scope (fork A) and the scoped calls
# ---------------------------------------------------------------------------

_SPECS: dict[str, CoverageFieldSpec] = {s.dotted: s for s in CALL_T_SPECS + CALL_S_SPECS}
_HOP_ROW_STATES = frozenset({"not_reported", "deferred", "unverifiable"})


def hop_scope(
    preprocessing: Any, ref_string: str, verifier: dict[str, Any] | None = None
) -> dict[str, Any]:
    """What the hop asks the cited paper, for the deferrals to ``ref_string``.

    A field deferred to it is asked. A base-pipeline deferral to it reaches (fork A, ratified
    2026-11-03) every D.3 row the citing paper did not report itself -- rows in state not reported,
    deferred or unverifiable -- plus the Software row's versions. A row the citing paper reports is
    never asked. Rows whose kinds calls T and S do not carry are listed as outside the calls."""
    from extractor_mvp.render import flatten

    rows = flatten(preprocessing)
    deferred_here = {
        r.path
        for r in rows
        if r.state == "DEFERRED_TO_CITATION" and ref_string in (r.deferral_refs or [])
    }
    asked: dict[str, str] = {d: "field deferred" for d in sorted(deferred_here) if d in _SPECS}
    software = False
    outside: list[str] = []
    if "base_pipeline" in deferred_here:
        software = True
        excluded = frozenset(
            " ".join(n.lower().split())
            for n, use in ((verifier or {}).get("software") or {}).items()
            if use is False
        )
        version_row = next((r for r in rows if r.path == "base_pipeline.version"), None)
        coverage = assess_coverage(
            rows,
            version_row.extraction_status if version_row else None,
            preprocessing.software_mentions,
            excluded,
        )
        for rc in coverage:
            if not rc.row.mandatory or rc.row.row_id == "software":
                continue
            if row_state(rc, rows) not in _HOP_ROW_STATES:
                continue
            specs = [s for s in _SPECS.values() if s.kind in rc.row.spec_kinds]
            if not specs:
                outside.append(rc.row.row_id)
            for s in specs:
                asked.setdefault(s.dotted, f"row not reported: {rc.row.row_id}")
    return {
        "asked": [{"field": f, "why": w} for f, w in asked.items()],
        "software": software,
        "rows_outside_calls": outside,
    }


class HopVariant(BaseModel):
    """One per-variant value the cited paper gives for an asked field (design §3)."""

    field: str
    value: str
    verbatim_quote: str
    applies_to: str


HOP_ADDENDUM = """\
## This is a CITED paper, read for one hop
Another paper defers part of its preprocessing to this one. Answer ONLY these fields: [ASKED].
Every other field is "missing"; do not search for it. [SOFTWARE]
Variants: when this text gives DIFFERENT values for an asked field for different scanners, vendors,
sites, sequences, cohorts or datasets, put each one in `variants`: field (the field name exactly as
listed above), value, verbatim_quote (copied exactly from the text), applies_to (the text's own words
for the variant, e.g. a scanner vendor). The field itself then carries only a value the text gives
for all of its data, else "missing". Never choose one variant.

"""

_TEXT_MARKER = 'Text:\n"""'


def hop_prompt(base: str, attrs: list[str], software: bool) -> str:
    """``base`` (call T's or S's pinned prompt) with :data:`HOP_ADDENDUM` before its text block."""
    addendum = HOP_ADDENDUM.replace("[ASKED]", ", ".join(attrs) or "(none)").replace(
        "[SOFTWARE]",
        "List the software as the prompt asks." if software else "Return no software list.",
    )
    i = base.rindex(_TEXT_MARKER)
    return base[:i] + addendum + base[i:]


_VARIANTS: tuple[Any, Any] = (list[HopVariant], Field(default_factory=list))
HopTemporalExtraction: type[BaseModel] = _response_model(
    "HopTemporalExtraction", CALL_T_SPECS, {"variants": _VARIANTS}
)
HopSpatialExtraction: type[BaseModel] = _response_model(
    "HopSpatialExtraction",
    CALL_S_SPECS,
    {
        "software_mentions": (list[SoftwareMentionResult], Field(default_factory=list)),
        "variants": _VARIANTS,
    },
)


class CallMeter:
    """Wall time and token use per model call, read from the raw responses (cost from LiteLLM's
    price table when it knows the model, else None)."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.label = ""

    def completion(self, *args: Any, **kwargs: Any) -> Any:
        from litellm import completion, completion_cost

        t0 = time.perf_counter()
        resp = completion(*args, **kwargs)
        usage = getattr(resp, "usage", None)
        try:
            cost: float | None = float(completion_cost(completion_response=resp))
        except Exception:
            cost = None
        self.calls.append(
            {
                "call": self.label,
                "wall_s": round(time.perf_counter() - t0, 3),
                "input_tokens": getattr(usage, "prompt_tokens", None),
                "output_tokens": getattr(usage, "completion_tokens", None),
                "cost_usd": cost,
            }
        )
        return resp

    def client(self) -> Any:
        import instructor

        return instructor.from_litellm(self.completion, mode=instructor.Mode.JSON)


def _create(client: Any, model: str, prompt: str, response_model: type[BaseModel]) -> Any:
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
        temperature=0.0,
        max_retries=2,
    )


def _variant_record(v: HopVariant, text: str) -> dict[str, Any]:
    span = resolve_quote(v.verbatim_quote, text).span
    value_in_quote = " ".join(v.value.lower().split()) in " ".join(v.verbatim_quote.lower().split())
    return {
        "value": v.value,
        "applies_to": v.applies_to,
        "verbatim_quote": v.verbatim_quote,
        "quote_resolved": span is not None,
        "value_in_quote": value_in_quote,
    }


def _draft(fields: dict[str, Any], software: list[Any]) -> str:
    """The scoped draft, one line per asked field, in the checking pass's line format."""
    from extractor_mvp.verifier import _fmt

    lines = []
    for dotted, pf in fields.items():
        ext = pf.extraction
        if ext.status == "EXTRACTED":
            state, value, quote = "extracted", _fmt(ext.value), ext.spans[0].text
        elif ext.status == "DEFERRED_TO_CITATION":
            state, value = "deferred", "deferred to " + ", ".join(d.ref for d in ext.deferrals)
            quote = ext.deferrals[0].span.text
        else:
            state, value, quote = "not reported", "-", ""
        reason = getattr(pf.inference, "reason", "") or ""
        lines.append(
            f'{dotted} | {state} | {value} | quote: "{" ".join(quote.split())}" | reason: {reason}'
        )
    for pf in software:
        if pf.extraction.status == "EXTRACTED":
            v = pf.extraction.value
            lines.append(
                f"software_mentions.{v.name} | extracted | version {v.version or 'not stated'}; "
                f'used for {v.used_for or "not stated"} | quote: "{" ".join(pf.extraction.spans[0].text.split())}" | reason: '
            )
    return "\n".join(lines)


def run_hop(
    citing_text: str,
    preprocessing: Any,
    ref_string: str,
    corpus_dirs: list[Path],
    model: str,
    *,
    verifier: dict[str, Any] | None = None,
    client: Any | None = None,
    meter: CallMeter | None = None,
) -> list[dict[str, Any]]:
    """One ``second_hop`` record per cited target behind ``ref_string``. Never raises on a model or
    PDF failure: the record carries the state."""
    from extractor_mvp.methods_finder import find_methods_section
    from extractor_mvp.pdf_loader import load_pdf_text
    from extractor_mvp.verifier import run_verifier

    meter = meter or CallMeter()
    client = client or meter.client()
    scope = hop_scope(preprocessing, ref_string, verifier)
    out: list[dict[str, Any]] = []
    for m in match_reference(ref_string, parse_reference_list(citing_text)):
        t0 = time.perf_counter()
        n_calls = len(meter.calls)
        rec: dict[str, Any] = {
            "ref": ref_string,
            "part": m.part,
            "scope": scope,
            "reference": {"state": m.state},
            "target": None,
            "fields": {},
            "variants": {},
            "software_mentions": [],
            "cited_deferrals": [],
            "verifier": None,
        }
        out.append(rec)
        if m.entry is None:
            rec["status"] = m.state
            continue
        rec["reference"].update(dataclasses.asdict(m.entry))
        state, path = resolve_local_pdf(m.entry, corpus_dirs)
        if path is None:
            rec["status"] = "not_retrievable"
            rec["target"] = {"state": state}
            continue
        try:
            full, _parser = load_pdf_text(path)
        except Exception as exc:  # a bad cited PDF never fails the citing paper
            rec["status"] = "not_retrievable"
            rec["target"] = {"state": "fetch_failed", "error": f"{type(exc).__name__}: {exc}"[:300]}
            continue
        rec["target"] = {
            "state": state,
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "doi_confirmed": (m.entry.doi.lower() in full.lower()) if m.entry.doi else None,
        }
        methods = find_methods_section(full)
        text = methods.text
        rec["methods"] = {"found_via": methods.found_via, "chars": len(text)}
        asked = [a["field"] for a in scope["asked"]]
        t_specs = tuple(s for s in CALL_T_SPECS if s.dotted in asked)
        s_specs = tuple(s for s in CALL_S_SPECS if s.dotted in asked)
        processed = CoverageExtraction(fields={}, diagnostics=[], deferrals=[])
        raw_variants: list[tuple[HopVariant, dict[str, CoverageFieldSpec]]] = []
        try:
            if t_specs:
                meter.label = "T"
                raw_t = _create(
                    client,
                    model,
                    hop_prompt(TEMPORAL_VOLUME_PROMPT, [s.attr for s in t_specs], False).format(
                        text=text
                    ),
                    HopTemporalExtraction,
                )
                _process(raw_t, t_specs, text, processed)
                raw_variants += [(v, {s.attr: s for s in t_specs}) for v in raw_t.variants]
            if s_specs or scope["software"]:
                meter.label = "S"
                raw_s = _create(
                    client,
                    model,
                    hop_prompt(SPATIAL_PROMPT, [s.attr for s in s_specs], scope["software"]).format(
                        text=text
                    ),
                    HopSpatialExtraction,
                )
                _process(raw_s, s_specs, text, processed)
                if scope["software"]:
                    _process_software(raw_s, text, processed)
                raw_variants += [(v, {s.attr: s for s in s_specs}) for v in raw_s.variants]
        except Exception as exc:  # the hop can never fail the citing paper
            rec["status"] = "call_failed"
            rec["error"] = f"{type(exc).__name__}: {exc}"[:500]
            rec["calls"] = meter.calls[n_calls:]
            rec["wall_time_s"] = round(time.perf_counter() - t0, 3)
            continue
        fields = {
            f"{kind}.{fid}": pf
            for kind, by_id in processed.fields.items()
            for fid, pf in by_id.items()
            if f"{kind}.{fid}" in asked
        }
        rec["fields"] = {d: pf.model_dump(mode="json") for d, pf in fields.items()}
        for v, by_attr in raw_variants:
            spec = by_attr.get(v.field) or _SPECS.get(v.field)
            if spec is None or spec.dotted not in asked:
                continue
            rec["variants"].setdefault(spec.dotted, []).append(_variant_record(v, text))
        rec["software_mentions"] = [pf.model_dump(mode="json") for pf in processed.software]
        rec["cited_deferrals"] = [
            {"field": d.field, "ref": d.ref_string, "target_kind": d.target_kind}
            for d in processed.deferrals
        ]
        meter.label = "checking pass"
        rec["verifier"] = run_verifier(
            ParsedPaper(text=text, source=str(path), parser="pypdf"),
            None,
            model,
            client=client,
            draft=_draft(fields, processed.software),
        )
        rec["status"] = "ok"
        rec["calls"] = meter.calls[n_calls:]
        rec["wall_time_s"] = round(time.perf_counter() - t0, 3)
    return out
