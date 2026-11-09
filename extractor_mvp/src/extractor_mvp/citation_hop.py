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
import itertools
import re
import time
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from extractor_mvp.cobidas import assess_coverage, mapped_rows, row_state
from extractor_mvp.coverage_extractor import (
    SPATIAL_PROMPT,
    TEMPORAL_VOLUME_PROMPT,
    CoverageExtraction,
    SoftwareMentionResult,
    _process,
    _response_model,
)
from extractor_mvp.coverage_fields import CALL_S_SPECS, CALL_T_SPECS, CoverageFieldSpec
from extractor_mvp.motion_guard import is_tool_shaped_frozen
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
#: An NIH author manuscript's entry (PubMed Central's reference style; fix 5, 2026-11-05): the
#: surname, then the initials in capitals with no comma between ("Adachi Y , Osada T, ...",
#: "Alexander-Bloch AF, ..."). Sims_2021 (stress_v1) parsed to 5 entries without it.
_AUTHOR_START_NIH = re.compile(rf"[ \t]*(?P<surname>{_SURNAME})[ \t]+[A-Z]{{1,4}}[ \t]*,")
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
    #: the GROBID ``<biblStruct xml:id>`` the entry was read from (:func:`resolve_targets`); None
    #: for an entry parsed from the text layer's reference list
    bibl_id: str | None = None


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
            # such an entry closes with its PubMed identifier ("[PubMed: 21893683]", sometimes
            # broken over two lines), not a period (fix 5, 2026-11-05)
            or stripped_prev.endswith("]")
        )
        if (
            line.strip()
            and boundary
            and (
                _NUMBERED_START.match(line)
                or _AUTHOR_START.match(line)
                or _AUTHOR_START_NIH.match(line)
            )
        ):
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
        auth = _AUTHOR_START.match(author_body) or _AUTHOR_START_NIH.match(author_body)
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
# 1b. The entry through GROBID's ref target (the author's list of 2026-11-09, item 4)
# ---------------------------------------------------------------------------

#: How a hop found its reference entry, recorded on every hop as ``ref_resolution``.
GROBID_REF_TARGET = "grobid_ref_target"
MARKER_TEXT = "marker_text"

_TOKEN = re.compile(r"[^\W_]+")


def _tokens(s: str) -> list[str]:
    return [t.casefold() for t in _TOKEN.findall(s)]


def _bibl_ref_entry(b: Any, label: str) -> RefEntry:
    """A :class:`grobid_source.BiblEntry` as the :class:`RefEntry` the on-disk lookup reads, its
    ``bibl_id`` prefixed by its TEI's label when that is not the paper's ("supplement:b3"). It has
    no offsets in the citing text (start and end are -1)."""
    head = ", ".join(b.authors)
    text = " ".join(
        x for x in (head, f"({b.year})" if b.year else "", b.title or "", b.doi or "") if x
    )
    return RefEntry(
        start=-1,
        end=-1,
        text=text,
        number=None,
        first_author=b.authors[0] if b.authors else None,
        year=b.year,
        doi=b.doi,
        bibl_id=b.bibl_id if label == "paper" else f"{label}:{b.bibl_id}",
    )


#: The TEIs a citing paper's text was read from, each with its label ("paper", "supplement"): a
#: deferral in a supplement cites the supplement's own reference list.
Teis = Sequence[tuple[str, "bytes | str"]]


def grobid_ref_matches(
    ref_string: str, teis: Teis, sentences: Sequence[str]
) -> tuple[list[RefMatch] | None, str]:
    """The targets behind a deferral's ref read from the TEI: the ``<ref type="bibr">`` elements of
    the deferring sentence whose own text is made of ``ref_string``'s words and numbers ("[3,]" and
    "[4]" for "[3,][4]"), each followed by its ``target="#bNN"`` to the ``<biblStruct>`` of the
    same TEI. The sentence is looked for verbatim in every TEI first
    (:func:`grobid_source.refs_in_sentence`, detail ``<label>:sentence_exact``), then by its words
    around the refs (:func:`grobid_source.refs_near_sentence`, detail
    ``<label>:sentence_word_overlap=<share>``). Returns ``(matches, detail)``, or ``(None, why)``
    when the marker text must be used instead: no sentence given or found in any TEI, no ref of the
    sentence is the deferral's, or one of those refs has no target or a target outside its TEI's
    reference list."""
    from extractor_mvp.grobid_source import bibliography, refs_in_sentence, refs_near_sentence

    if not sentences:
        return None, "no_deferral_sentence"
    want = set(_tokens(ref_string))

    def deferrals(text: str) -> bool:
        own = _tokens(text)
        return bool(own) and set(own) <= want

    found_sentence = False
    picked: list[tuple[str, Any]] = []
    details: list[str] = []
    for sentence in sentences:
        hit: tuple[str, list[Any], str] | None = None
        for label, tei in teis:
            refs = refs_in_sentence(tei, sentence)
            if refs is not None:
                hit = (label, [r for r in refs if deferrals(r.text)], "sentence_exact")
                break
        if hit is None:
            for label, tei in teis:
                near = refs_near_sentence(tei, sentence, deferrals)
                if near is not None:
                    hit = (label, near[0], f"sentence_word_overlap={near[1]}")
                    break
        if hit is None:
            continue
        found_sentence = True
        details.append(f"{hit[0]}:{hit[2]}")
        picked += [(hit[0], r) for r in hit[1]]
    if not found_sentence:
        return None, "sentence_not_in_tei"
    if not picked:
        return None, "no_ref_in_sentence"
    if any(r.target is None for _label, r in picked):
        return None, "ref_without_target"
    bibls = {label: bibliography(tei) for label, tei in teis}
    if any(r.target not in bibls[label] for label, r in picked):
        return None, "target_not_in_bibliography"
    out: list[RefMatch] = []
    seen: set[tuple[str, str]] = set()
    for label, r in picked:
        if (label, r.target) in seen:
            continue
        seen.add((label, r.target))
        out.append(RefMatch(r.text, "resolved", _bibl_ref_entry(bibls[label][r.target], label)))
    return out, "; ".join(dict.fromkeys(details))


def resolve_targets(
    ref_string: str,
    citing_text: str,
    *,
    teis: Teis = (),
    sentences: Sequence[str] = (),
) -> tuple[list[RefMatch], str, str]:
    """The targets behind a deferral's ref and how they were found: through GROBID's ref targets
    (:func:`grobid_ref_matches`) when the paper's TEI is given, else, or when that finds none, by
    parsing the marker text against ``citing_text``'s reference list (:func:`match_reference`).
    Returns ``(matches, ref_resolution, detail)``: for the ref targets, where and how the sentence
    was found; for the marker text, why the targets were not used."""
    if not teis:
        why = "text_source_not_grobid"
    else:
        try:
            matches, why = grobid_ref_matches(ref_string, teis, sentences)
        except Exception as exc:  # a TEI that does not parse leaves the marker text
            matches, why = None, f"tei_unreadable: {type(exc).__name__}"
        if matches is not None:
            return matches, GROBID_REF_TARGET, why
    return match_reference(ref_string, parse_reference_list(citing_text)), MARKER_TEXT, why


# ---------------------------------------------------------------------------
# 2. The target: a local PDF (PubMed Central is the design's next tier, not built for case one)
# ---------------------------------------------------------------------------


#: How far into a cited PDF its own DOI is looked for (the first page and a half, where journals
#: print it).
_PDF_DOI_CHARS = 10_000
_CROSSREF_CACHE: dict[str, tuple[str, str] | None] = {}


def _pdf_dois(path: Path, read_text: Any) -> set[str]:
    """The DOIs printed near the start of a PDF, lower-cased, trailing punctuation stripped."""
    text, _parser = read_text(path)
    head = " ".join(text[:_PDF_DOI_CHARS].split())
    return {m.group(1).rstrip(".,;)").lower() for m in _DOI.finditer(head)}


#: The client name CrossRef sees. The author's ruling of 2026-11-05: a generic client name and no
#: email in the request (no "mailto" polite-pool parameter, no contact header).
CROSSREF_USER_AGENT = "aespa-citation-hop (fmri-repro-agent)"


def crossref_author_year(doi: str) -> tuple[str, str] | None:
    """The first author's family name and the year CrossRef records for ``doi``; None when the call
    fails or the record lacks either. One HTTP GET per DOI per process (cached); no user data is
    sent, only the DOI (2026-11-05)."""
    if doi in _CROSSREF_CACHE:
        return _CROSSREF_CACHE[doi]
    import json
    import urllib.parse
    import urllib.request

    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_USER_AGENT})
    out: tuple[str, str] | None = None
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            msg = json.loads(resp.read().decode("utf-8"))["message"]
        family = (msg.get("author") or [{}])[0].get("family")
        parts = (msg.get("issued") or msg.get("published") or {}).get("date-parts") or [[None]]
        year = parts[0][0]
        if family and year:
            out = (str(family), str(year))
    except Exception:  # a failed lookup leaves the PDF unconfirmed, never fails the paper
        out = None
    _CROSSREF_CACHE[doi] = out
    return out


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", t).lower()).strip()


def crossref_doi(entry: Any, *, fetch: Any = None) -> str | None:
    """The DOI CrossRef records for a bibliography entry that carries none (2026-11-09): one
    bibliographic query with the entry's reference text; the top hit is accepted only when its first
    author's family name and its year equal the entry's and its title occurs in the reference text
    (all normalised). Only the reference text is sent. None on any doubt or failure."""
    import json
    import urllib.parse
    import urllib.request

    ref = str(getattr(entry, "text", "") or "")
    year = str(getattr(entry, "year", "") or "")
    author = str(getattr(entry, "first_author", "") or "")
    if not ref or not year or not author:
        return None

    def default_fetch(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body: bytes = resp.read()
            return body

    q = urllib.parse.quote(" ".join(ref.split())[:300])
    try:
        msg = json.loads(
            (fetch or default_fetch)(
                f"https://api.crossref.org/works?query.bibliographic={q}&rows=1"
            )
        )["message"]
        item = (msg.get("items") or [None])[0]
    except Exception:
        return None
    if not item:
        return None
    hit_title = _norm_title(" ".join(item.get("title") or []))
    family = _norm_title(str((item.get("author") or [{}])[0].get("family") or ""))
    parts = (item.get("issued") or item.get("published") or {}).get("date-parts") or [[None]]
    if not hit_title or hit_title not in _norm_title(ref):
        return None
    if family != _norm_title(author) or str(parts[0][0]) != year:
        return None
    doi = item.get("DOI")
    return str(doi).lower() if doi else None


#: The client name Europe PMC sees (2026-11-09): generic, no email, as for CrossRef.
EUROPEPMC_USER_AGENT = CROSSREF_USER_AGENT
_EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def europepmc_cache_name(doi: str) -> str:
    """The cache file's name for a DOI, beside the citing paper."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", doi.lower()) + ".europepmc.xml"


def jats_text(xml: bytes) -> str:
    """A JATS article's body as text, one section title per line before its paragraphs, so the
    methods finder can find a "Methods" heading as in a PDF's text."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml)
    body = root.find(".//body")
    if body is None:
        return ""
    lines: list[str] = []

    def walk(el: Any) -> None:
        for child in el:
            tag = child.tag.split("}")[-1]
            if tag == "sec":
                title = child.find("title")
                if title is not None:
                    lines.append(" ".join("".join(title.itertext()).split()))
                walk(child)
            elif tag == "p":
                lines.append(" ".join("".join(child.itertext()).split()))

    walk(body)
    return "\n".join(x for x in lines if x)


def europepmc_fulltext(
    doi: str, cache_dir: Path | None, *, fetch: Any = None
) -> tuple[str, Path, str] | None:
    """The open-access full text of ``doi`` from the Europe PMC REST API as ``(text, cached file,
    sha256)``; None when Europe PMC has no full text for it or a call fails (2026-11-09, the author's
    item 2). The JATS XML is cached in ``cache_dir`` (beside the citing paper) and read from there
    on a later run. Only the DOI is sent."""
    import json
    import urllib.parse
    import urllib.request

    def default_fetch(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": EUROPEPMC_USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body: bytes = resp.read()
            return body

    fetch = fetch or default_fetch
    cached = cache_dir / europepmc_cache_name(doi) if cache_dir is not None else None
    try:
        if cached is not None and cached.is_file():
            xml = cached.read_bytes()
        else:
            q = urllib.parse.quote(f'DOI:"{doi}"')
            hits = json.loads(fetch(f"{_EUROPEPMC}/search?query={q}&format=json&resultType=lite"))
            results = (hits.get("resultList") or {}).get("result") or []
            pmcid = next((r.get("pmcid") for r in results if r.get("pmcid")), None)
            if not pmcid:
                return None
            xml = fetch(f"{_EUROPEPMC}/{pmcid}/fullTextXML")
            if cached is None:
                return None
            cached.write_bytes(xml)
        text = jats_text(xml)
    except Exception:  # a failed lookup leaves the reference not retrievable, never fails the paper
        return None
    if not text or cached is None:
        return None
    return text, cached, hashlib.sha256(xml).hexdigest()


#: 2026-11-09 (the author's item 3): the words that put a sentence on a step, and the cue that it
#: hands the step to its citation. A sentence needs both, and a bibliography ref, to be followed.
STEP_WORDS: dict[str, tuple[str, ...]] = {
    "motion_correction": ("motion", "realign"),
    "slice_time_correction": ("slice-tim", "slice tim", "slice acquisition"),
    "distortion_correction": ("distortion", "field map", "fieldmap", "unwarp", "topup"),
    "spatial_normalization": ("normaliz", "normalis", "template", "mni"),
    "spatial_smoothing": ("smooth",),
    "temporal_filtering": ("filter", "band-pass", "bandpass", "high-pass", "low-pass"),
    "nuisance_regression": ("nuisance", "regress", "confound"),
    "segmentation": ("segment",),
    "coregistration": ("coregist", "co-regist", "registered to the"),
    "brain_extraction": ("skull", "brain extraction"),
}
_DEFERRAL_CUE = re.compile(
    r"preprocess|pipeline|as described|described (?:in|previously|elsewhere)|detail|"
    r"following|according to|\bsee\b|as in\b",
    re.IGNORECASE,
)
_TEI = "{http://www.tei-c.org/ns/1.0}"


def step_citations(teis: Teis, kinds: Sequence[str]) -> list[tuple[str, str, str, str]]:
    """Every citation a step is handed to, across the paper's and the supplement's TEI (2026-11-09):
    ``(tei label, kind, marker text, sentence)`` for each bibliography ref in a sentence that names
    one of ``kinds`` (:data:`STEP_WORDS`) and carries a deferral cue. One entry per (tei, target)."""
    import xml.etree.ElementTree as ET

    out: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for label, tei in teis:
        try:
            root = ET.fromstring(tei)
        except Exception:
            continue
        for p in root.iter(_TEI + "p"):
            parts: list[tuple[str, str | None, str]] = [(p.text or "", None, "")]
            for ch in p:
                if ch.tag == _TEI + "ref" and ch.get("type") == "bibr" and ch.get("target"):
                    parts.append(("".join(ch.itertext()), ch.get("target"), "".join(ch.itertext())))
                else:
                    parts.append(("".join(ch.itertext()), None, ""))
                parts.append((ch.tail or "", None, ""))
            text = ""
            refs: list[tuple[int, str, str]] = []
            for chunk, target, marker in parts:
                if target:
                    refs.append((len(text), target, marker))
                text += chunk
            bounds = (
                [0] + [m.end() for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z])", text)] + [len(text)]
            )
            for a, b in itertools.pairwise(bounds):
                sentence = " ".join(text[a:b].split())
                low = sentence.lower()
                if not _DEFERRAL_CUE.search(sentence):
                    continue
                for kind in kinds:
                    if not any(w in low for w in STEP_WORDS.get(kind, ())):
                        continue
                    for at, target, marker in refs:
                        if a <= at < b and (label, target) not in seen and marker.strip():
                            seen.add((label, target))
                            out.append((label, kind, marker.strip(), sentence))
    return out


def _stem_matches(stem: str, keys: set[str], year: str) -> bool:
    """``<surname>_<year>`` exactly or followed by ``_``/``-`` and more ("Glasser_2013_HCP_pipelines")."""
    for k in keys:
        base = f"{k}_{year}"
        if stem == base or stem.startswith(base + "_") or stem.startswith(base + "-"):
            return True
    return False


def resolve_local_pdf(
    entry: RefEntry,
    corpus_dirs: list[Path],
    *,
    read_text: Any | None = None,
    lookup: Any | None = None,
) -> tuple[str, Path | None, str | None]:
    """A local PDF for a reference entry (the author's ruling, 2026-11-05): candidates by first
    author and year from the file name (``<FirstAuthor>_<year>`` exactly, or followed by ``_``/``-``
    and more), each confirmed by the DOI printed in its own text: equal to the entry's DOI when the
    entry carries one; otherwise the DOI's CrossRef record has the entry's first author and year.
    Returns ``(state, path, confirmed_by)``: ``local_pdf`` with exactly one confirmed candidate;
    ``no_local_pdf`` (no candidate), ``local_pdf_unconfirmed`` (candidates, none confirmed) or
    ``local_pdf_ambiguous`` (more than one confirmed), with no path. Before 2026-11-05 the file had
    to be named ``<FirstAuthor>_<year>.pdf`` exactly and nothing was confirmed."""
    if not entry.first_author or not entry.year:
        return "no_local_pdf", None, None
    keys = _surname_keys(entry.first_author)
    candidates = sorted(
        {
            p.resolve()
            for d in corpus_dirs
            if d.is_dir()
            for p in d.glob("*.pdf")
            if _stem_matches(_norm_name(p.stem), keys, entry.year)
        }
    )
    if not candidates:
        return "no_local_pdf", None, None
    if read_text is None:
        from extractor_mvp import pdf_loader

        read_text = pdf_loader.load_pdf_text
    lookup = lookup or crossref_author_year
    confirmed: list[tuple[Path, str]] = []
    for c in candidates:
        dois = _pdf_dois(c, read_text)
        if entry.doi:
            if entry.doi.rstrip(".,;)").lower() in dois:
                confirmed.append((c, "entry_doi_in_pdf"))
            continue
        for d in sorted(dois):
            meta = lookup(d)
            if meta and _norm_name(meta[0]) in keys and meta[1] == entry.year:
                confirmed.append((c, "crossref_author_year"))
                break
    if not confirmed:
        return "local_pdf_unconfirmed", None, None
    if len(confirmed) > 1:
        return "local_pdf_ambiguous", None, None
    return "local_pdf", confirmed[0][0], confirmed[0][1]


# ---------------------------------------------------------------------------
# 2b. The cited paper's fMRI sections (the author, 2026-11-03: every section whose heading names
#     fMRI; dMRI and sMRI sections excluded)
# ---------------------------------------------------------------------------

#: A numbered heading line ("2.7.4. Resting-state fMRI analysis"): short, capitalised, and not a
#: sentence (the caller drops a match that ends in a period).
_NUMBERED_HEADING = re.compile(
    r"^[ \t]*(?P<num>\d+(?:\.\d+)+)\.?[ \t]+(?:[A-Z]|[a-z]{1,3}MRI\b)[^\n]{0,78}$", re.MULTILINE
)
#: An unnumbered heading line that names an imaging modality: at most eight words, capitalised (or
#: opening with "fMRI"/"sMRI"/"dMRI"), no punctuation inside, no closing period or hyphen. Only these, the numbered headings and the methods finder's own headings bound a
#: section in a paper without numbered headings.
_MODALITY_HEADING = re.compile(
    r"^[ \t]*(?=[A-Z]|[a-z]{1,3}MRI\b)[^\n.,;:]{0,60}"
    r"(?i:\bf(?:unctional[ \t-])?MRI\b|\bBOLD\b|\bdMRI\b|\bsMRI\b|diffusion|structural|anatomical)"
    r"[^\n.,;:]{0,40}$",
    re.MULTILINE,
)
_HEADING_WORDS = 8
#: A heading names fMRI ("fMRI", "functional MRI", "BOLD", "resting-state", "rs-fMRI"); the dMRI and
#: sMRI sections never do.
_NAMES_FMRI = re.compile(
    r"\bf(?:unctional[ \t-])?MRI\b|\bBOLD\b|resting[- ]state|\brs-?fMRI\b", re.IGNORECASE
)
_NAMES_OTHER = re.compile(r"\b[ds]MRI\b|diffusion|structural|anatomical", re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class FmriSections:
    """What the hop's field calls read: the fMRI-headed sections, joined in order. ``sections``
    holds each one's heading and its offsets in the cited paper's full text."""

    text: str
    sections: tuple[tuple[str, int, int], ...]
    found_via: str  # headings | methods_fallback (no heading names fMRI)


def _headings(methods_text: str) -> list[tuple[int, str, str | None]]:
    """Every heading in the methods slice: (offset, heading, its number or None)."""
    from extractor_mvp.methods_finder import _METHODS_RE, _NEXT_RE

    found: dict[int, tuple[int, str, str | None]] = {}
    for rx in (_NUMBERED_HEADING, _MODALITY_HEADING, *_METHODS_RE, *_NEXT_RE):
        for m in rx.finditer(methods_text):
            head = m.group(0).strip()
            if head.endswith((".", "-")) or m.start() in found:
                continue
            if rx is _MODALITY_HEADING and len(head.split()) > _HEADING_WORDS:
                continue
            num = m.groupdict().get("num") if rx is _NUMBERED_HEADING else None
            found[m.start()] = (m.start(), head, num)
    return sorted(found.values())


def find_fmri_sections(methods_text: str, methods_start: int = 0) -> FmriSections:
    """The cited paper's fMRI sections, by heading as the methods finder slices: each section runs
    from its heading to the next heading. Kept: a section whose heading names fMRI and no other
    modality, and every numbered subsection of a kept numbered section (Hagler et al. (2019):
    "2.7. fMRI processing and analysis" keeps 2.7.1 to 2.7.5, so the rest regression under
    "2.7.4. Resting-state fMRI analysis" is read). No heading names fMRI: the whole methods slice,
    recorded as ``methods_fallback``."""
    heads = _headings(methods_text)
    kept: list[tuple[str, int, int]] = []
    parents: list[str] = []
    for k, (start, head, num) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(methods_text)
        own = bool(_NAMES_FMRI.search(head)) and not _NAMES_OTHER.search(head)
        child = num is not None and any(num.startswith(p + ".") for p in parents)
        if own or child:
            kept.append((head, start, end))
            if num is not None and own:
                parents.append(num)
    if not kept:
        return FmriSections(
            methods_text,
            (("(whole methods section)", methods_start, methods_start + len(methods_text)),),
            "methods_fallback",
        )
    merged: list[tuple[str, int, int]] = []
    for head, start, end in kept:
        if merged and merged[-1][2] == start:
            merged[-1] = (merged[-1][0], merged[-1][1], end)
        else:
            merged.append((head, start, end))
    return FmriSections(
        "\n\n".join(methods_text[a:b] for _, a, b in merged),
        tuple((h, methods_start + a, methods_start + b) for h, a, b in merged),
        "headings",
    )


# ---------------------------------------------------------------------------
# 3. The scope (fork A) and the scoped calls
# ---------------------------------------------------------------------------

_SPECS: dict[str, CoverageFieldSpec] = {s.dotted: s for s in CALL_T_SPECS + CALL_S_SPECS}
_HOP_ROW_STATES = frozenset({"not_reported", "deferred", "unverifiable"})


def hop_scope(
    preprocessing: Any,
    ref_string: str,
    verifier: dict[str, Any] | None = None,
    step_fields: Sequence[str] = (),
) -> dict[str, Any]:
    """What the hop asks the cited paper, for the deferrals to ``ref_string``.

    A field deferred to it is asked. A base-pipeline deferral to it reaches (fork A, ratified
    2026-11-03) every D.3 row the citing paper did not report itself -- rows in state not reported,
    deferred or unverifiable -- plus the Software row's versions. A row the citing paper reports is
    never asked for its fields; widened 2026-11-03, a reported row whose method names no tool
    (:func:`described_only`) is asked for the tool, in ``tools``. Rows whose kinds calls T and S do not carry are listed as outside the calls."""
    from extractor_mvp.render import flatten

    rows = flatten(preprocessing)
    deferred_here = {
        r.path
        for r in rows
        if r.state == "DEFERRED_TO_CITATION" and ref_string in (r.deferral_refs or [])
    } | set(step_fields)  # 2026-11-09: a step's deferred fields, for a citation found step-wide
    asked: dict[str, str] = {d: "field deferred" for d in sorted(deferred_here) if d in _SPECS}
    software = False
    tools: dict[str, dict[str, Any]] = {}
    # a deferred method field calls T and S do not carry (motion_correction.method: case two,
    # poldrack_2015 -> ref 45, 2026-11-03) is asked as the step's tool, the question call S carries
    for d in sorted(deferred_here):
        kind = d.split(".", 1)[0]
        if d not in _SPECS and d == f"{kind}.method" and kind in _TOOL_METHOD_KINDS:
            tools[d] = {"field": d, "row": kind, "described_as": [f"deferred to {ref_string}"]}
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
            state = row_state(rc, rows)
            if state in ("reported", "partially_reported"):
                for r in mapped_rows(rc, rows):
                    if (
                        r.path == f"{r.group}.method"
                        and r.group in _TOOL_METHOD_KINDS
                        and r.extraction_status == "EXTRACTED"
                        and r.path not in tools
                        and described_only(r.value)
                    ):
                        tools[r.path] = {
                            "field": r.path,
                            "row": rc.row.row_id,
                            "described_as": _verbatims(r.value),
                        }
                continue
            if state not in _HOP_ROW_STATES:
                continue
            specs = [s for s in _SPECS.values() if s.kind in rc.row.spec_kinds]
            if not specs:
                outside.append(rc.row.row_id)
            for s in specs:
                asked.setdefault(s.dotted, f"row not reported: {rc.row.row_id}")
    return {
        "asked": [{"field": f, "why": w} for f, w in asked.items()],
        "software": software,
        "tools": list(tools.values()),
        "rows_outside_calls": outside,
    }


#: The step kinds whose ``method`` is a list of tools (the spec's ``*Method`` literals name programs:
#: ``mcflirt``, ``bbregister``, ``afni_3dtproject``...). ``temporal_filtering.method`` names filter
#: shapes and is left out.
_TOOL_METHOD_KINDS = frozenset(
    {
        "motion_correction",
        "slice_time_correction",
        "brain_extraction",
        "segmentation",
        "coregistration",
        "distortion_correction",
        "intensity_correction",
        "spatial_normalization",
        "spatial_smoothing",
        "despike",
        "scrub",
        "nuisance_regression",
        "ica_denoise",
    }
)
_NOT_A_TOOL = frozenset({"other", "custom"})


def _terms(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else [value]


def _verbatims(value: Any) -> list[str]:
    return [str(getattr(t, "verbatim", None) or t) for t in _terms(value)]


def described_only(value: Any) -> bool:
    """Fork A widened (the author, 2026-11-03): an EXTRACTED method value that names no tool -- the
    paper's own words ("corrected for motion"), resolved to no member of the step's tool list or
    only to ``other``/``custom``. The motion arm's ``described_only``, for every tool-list step."""
    return not any(
        getattr(t, "resolution", None) == "resolved"
        and str(getattr(t, "resolved", "")) not in _NOT_A_TOOL
        for t in _terms(value)
    )


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
[TOOLS]

"""

_TOOLS_ASK = (
    "Tools: for each of these steps, put the software program this text names as performing it in "
    "`tools`: field (exactly as listed here), tool (as written), verbatim_quote (copied exactly from "
    "the text). A step for which the text names no program: leave it out. Steps: {fields}."
)

_TEXT_MARKER = 'Text:\n"""'


def hop_prompt(base: str, attrs: list[str], software: bool, tools: Sequence[str] = ()) -> str:
    """``base`` (call T's or S's pinned prompt) with :data:`HOP_ADDENDUM` before its text block.
    ``tools`` are asked on call S only (its response model carries them). ``software`` is kept for
    the signature; the software list comes from the KB scan (software_scan.py, 2026-11-03), never
    from a call, so the addendum always says "Return no software list."."""
    addendum = (
        HOP_ADDENDUM.replace("[ASKED]", ", ".join(attrs) or "(none)")
        .replace("[SOFTWARE]", "Return no software list.")
        .replace(
            "[TOOLS]",
            _TOOLS_ASK.format(fields=", ".join(tools)) if tools else "Return no `tools`.",
        )
    )
    i = base.rindex(_TEXT_MARKER)
    return base[:i] + addendum + base[i:]


class HopTool(BaseModel):
    """The program the cited paper names for a step the citing paper describes without one."""

    field: str
    tool: str
    verbatim_quote: str


class DataRelease(BaseModel):
    """A named release of a dataset: the citing paper's own data (first hop) or a release whose
    processing the cited paper describes."""

    dataset: str
    release: str
    verbatim_quote: str


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
        "tools": (list[HopTool], Field(default_factory=list)),
    },
)


def _tool_arguments(message: Any) -> str | None:
    """A tool-calling reply's arguments, the raw reply in that mode (its content is empty)."""
    calls = getattr(message, "tool_calls", None) or []
    return "\n".join(str(c.function.arguments) for c in calls) or None


class CallMeter:
    """Wall time and token use per model call, read from the raw responses (cost from LiteLLM's
    price table when it knows the model, else None).

    Every attempt is one entry, numbered within its call. An attempt whose response instructor
    could not parse carries ``parse_error``, and its raw text and ``finish_reason`` are kept, so a
    retry is read from the record, never inferred from a call count (case one's checking pass,
    2026-11-03, made two billed calls and the first response was not kept)."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.label = ""

    def completion(self, *args: Any, **kwargs: Any) -> Any:
        from litellm import completion, completion_cost

        if not self.label:
            # fix 2 (2026-11-05): a call made with no label set (the first hop's, inside
            # process_paper) is labelled by its response model's tool name, "first:<name>"
            tools = kwargs.get("tools") or []
            name = (tools[0].get("function") or {}).get("name") if tools else None
            label = f"first:{name or 'unlabelled'}"
        else:
            label = self.label
        t0 = time.perf_counter()
        resp = completion(*args, **kwargs)
        usage = getattr(resp, "usage", None)
        try:
            cost: float | None = float(completion_cost(completion_response=resp))
        except Exception:
            cost = None
        choice = (getattr(resp, "choices", None) or [None])[0]
        message = getattr(choice, "message", None)
        self.calls.append(
            {
                "call": label,
                "attempt": 1 + sum(1 for c in self.calls if c["call"] == label),
                "wall_s": round(time.perf_counter() - t0, 3),
                "input_tokens": getattr(usage, "prompt_tokens", None),
                "output_tokens": getattr(usage, "completion_tokens", None),
                "cost_usd": cost,
                "finish_reason": getattr(choice, "finish_reason", None),
                "raw": getattr(message, "content", None) or _tool_arguments(message),
                "parse_error": None,
            }
        )
        return resp

    def on_parse_error(self, error: Exception) -> None:
        """instructor's ``parse:error`` hook: the attempt just made is the one that failed."""
        if self.calls:
            self.calls[-1]["parse_error"] = f"{type(error).__name__}: {error}"[:2000]

    def client(self, mode: str = "tools") -> Any:
        """``mode`` "tools" (the default, as :data:`extractor.INSTRUCTOR_MODE` from 2026-11-03) or
        "json" (the earlier mode, kept for the retry measurement)."""
        import instructor

        client = instructor.from_litellm(
            self.completion,
            mode={"json": instructor.Mode.JSON, "tools": instructor.Mode.TOOLS}[mode],
        )
        client.on("parse:error", self.on_parse_error)
        return client


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


_DOUBLE_QUOTES = str.maketrans({'"': "'", "\u201c": "'", "\u201d": "'"})


def json_safe(text: str) -> str:
    """The cited text with every double quotation mark, straight or curly, replaced by an apostrophe,
    one character for one, so every offset holds. A sentence the model copies into a JSON string
    then has no double quote to escape. Case one's checking pass (2026-11-03) copied Hagler's
    'signal \u201cdrop-out\u201d' with the curly quotes turned straight and unescaped; the reply
    failed to parse and instructor's retry was a second billed call. Replacing only straight quotes
    did not stop it (Hagler's methods have none; the model straightens the curly ones)."""
    return text.translate(_DOUBLE_QUOTES)


_POSSESSIVE = re.compile(r"['\u2019]s\b")


def _in_quote(value: str, quote: str) -> bool:
    """The value's words in the quote, case and spacing aside, and a possessive "'s" aside ("AFNI
    3dvolreg" is in "AFNI's 3dvolreg", case one's motion tool, 2026-11-03)."""

    def norm(x: str) -> str:
        return " ".join(_POSSESSIVE.sub("", x.lower()).split())

    return norm(value) in norm(quote)


def _quoted(quote: str, value: str, text: str, *, key: str = "tool") -> dict[str, Any]:
    """A value with its quote, checked as a variant is: the quote found in the text, the value
    found in the quote."""
    return {
        key: value,
        "verbatim_quote": quote,
        "quote_resolved": resolve_quote(quote, text).span is not None,
        f"{key}_in_quote": _in_quote(value, quote),
    }


def _draft(
    fields: dict[str, Any],
    software: list[Any],
    tools: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
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
    for field, found in (tools or {}).items():
        for t in found:
            lines.append(
                f"tool.{field} | extracted | {t['tool']} | "
                f'quote: "{" ".join(t["verbatim_quote"].split())}" | reason: '
            )
    for t in software:
        if t.get("kept"):
            lines.append(
                f"software_mentions.{t['display_name']} | extracted | version "
                f"{t.get('version') or 'not stated'}; used for {t.get('use') or 'not stated'} | "
                f'quote: "{" ".join((t.get("use_quote") or "").split())}" | reason: '
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
    teis: Teis = (),
    deferral_sentences: Sequence[str] = (),
    cache_dir: Path | None = None,
    europepmc: Any = None,
    step_fields: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """One ``second_hop`` record per cited target behind ``ref_string``. Never raises on a model or
    PDF failure: the record carries the state. With the citing paper's GROBID ``teis`` and the
    deferring sentences, the targets are read through the TEI's ref targets (:func:`resolve_targets`);
    each record says which way in ``ref_resolution`` and, in ``ref_resolution_detail``, how the
    sentence was found or why the marker text was used."""
    from extractor_mvp.methods_finder import find_methods_section
    from extractor_mvp.pdf_loader import load_pdf_text
    from extractor_mvp.verifier import run_verifier

    meter = meter or CallMeter()
    client = client or meter.client()
    scope = hop_scope(preprocessing, ref_string, verifier, step_fields)
    out: list[dict[str, Any]] = []
    matches, resolution, detail = resolve_targets(
        ref_string, citing_text, teis=teis, sentences=deferral_sentences
    )
    for m in matches:
        t0 = time.perf_counter()
        n_calls = len(meter.calls)
        rec: dict[str, Any] = {
            "ref": ref_string,
            "part": m.part,
            "ref_resolution": resolution,
            "ref_resolution_detail": detail,
            "scope": scope,
            "reference": {"state": m.state},
            "target": None,
            "fields": {},
            "variants": {},
            "software_mentions": [],
            "software_scan": None,
            "tools": {},
            "releases_described": [],
            "cited_deferrals": [],
            "verifier": None,
        }
        out.append(rec)
        if m.entry is None:
            rec["status"] = m.state
            continue
        rec["reference"].update(dataclasses.asdict(m.entry))
        state, path, confirmed_by = resolve_local_pdf(m.entry, corpus_dirs)
        epmc = None
        if path is None:
            # 2026-11-09 (the author's item 2): no PDF on disk -> Europe PMC's open full text by DOI
            # (the entry's own DOI, else the one CrossRef records for its title and year)
            doi = m.entry.doi or crossref_doi(m.entry)
            if doi:
                rec["reference"]["doi_used"] = doi
                epmc = (europepmc or europepmc_fulltext)(doi, cache_dir)
        if path is None and epmc is None:
            rec["status"] = "not_retrievable"
            rec["target"] = {"state": state}
            continue
        if epmc is not None:
            full, xml_path, sha = epmc
            rec["target"] = {
                "state": "europepmc_fulltext",
                "path": str(xml_path),
                "sha256": sha,
                "doi_confirmed": True,  # Europe PMC was queried by the entry's DOI
                "confirmed_by": "europepmc_doi",
            }
        else:
            assert path is not None
            try:
                full, _parser = load_pdf_text(path)
            except Exception as exc:  # a bad cited PDF never fails the citing paper
                rec["status"] = "not_retrievable"
                rec["target"] = {
                    "state": "fetch_failed",
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                }
                continue
            rec["target"] = {
                "state": state,
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "doi_confirmed": True,  # resolve_local_pdf confirms by the PDF's DOI (2026-11-05)
                "confirmed_by": confirmed_by,
            }
        methods = find_methods_section(full)
        fmri = find_fmri_sections(methods.text, methods.start_offset)
        text = json_safe(fmri.text)
        whole = json_safe(full)
        rec["methods"] = {
            "found_via": methods.found_via,
            "chars": len(methods.text),
            "start": methods.start_offset,
            "end": methods.start_offset + len(methods.text),
        }
        rec["fmri_sections"] = {
            "found_via": fmri.found_via,
            "sections": [{"heading": h, "start": a, "end": b} for h, a, b in fmri.sections],
            "chars": len(fmri.text),
            "double_quotes_replaced": sum(fmri.text.count(q) for q in '"\u201c\u201d'),
        }
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
            tool_fields = [t["field"] for t in scope.get("tools") or []]
            meter.label = "S"
            raw_s = _create(
                client,
                model,
                hop_prompt(SPATIAL_PROMPT, [s.attr for s in s_specs], False, tool_fields).format(
                    text=text
                ),
                HopSpatialExtraction,
            )
            _process(raw_s, s_specs, text, processed)
            raw_variants += [(v, {s.attr: s for s in s_specs}) for v in raw_s.variants]
            if scope["software"]:
                # the software list (the author, 2026-11-03): a deterministic scan of the whole
                # cited paper for KB package names, then one scoped question per mention
                from extractor_mvp.software_scan import ask_uses, scan, tool_list

                uses = ask_uses(scan(whole), model, client=client, meter=meter)
                rec["software_scan"] = {"mentions": uses, "tools": tool_list(uses)}
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
        for t in raw_s.tools:
            if t.field in tool_fields:
                rec["tools"].setdefault(t.field, []).append(
                    {
                        **_quoted(t.verbatim_quote, t.tool, text),
                        "tool_shaped": is_tool_shaped_frozen(t.tool),  # recorded; render decides
                    }
                )
        rec["rules"] = apply_rules(fields)
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
            draft=_draft(fields, (rec.get("software_scan") or {}).get("tools") or [], rec["tools"]),
        )
        rec["releases_described"] = described_releases(
            json_safe(methods.text), model, client=client, meter=meter
        )
        rec["status"] = "ok"
        rec["calls"] = meter.calls[n_calls:]
        rec["wall_time_s"] = round(time.perf_counter() - t0, 3)
    return out


# ---------------------------------------------------------------------------
# 4. The citing paper's data release (a first-hop field; "described vs applied", 2026-11-03)
# ---------------------------------------------------------------------------

RELEASE_PROMPT = """\
You are reading the methods of a neuroimaging paper. List each named release of a dataset that THIS
paper's own data come from (e.g. a dataset's release number, a data collection's number). For each:
dataset (the dataset's name as written), release (the release or collection as written),
verbatim_quote (copied exactly from the text). Only releases the text names. A dataset named with no
release: leave it out. None named: an empty list.

Text:
\"\"\"
{text}
\"\"\"
"""


class CitingReleases(BaseModel):
    releases: list[DataRelease] = Field(default_factory=list)


def extract_data_release(
    citing_text: str,
    model: str,
    *,
    client: Any | None = None,
    meter: CallMeter | None = None,
    text_source: str = "pypdf",
) -> dict[str, Any]:
    """The citing paper's own data release(s), each with its quote, from one call (``R``) on its
    methods. A first-hop field: it is read in the citing paper, never in the cited one. Never
    raises: a failed call is a state."""
    from extractor_mvp.methods_finder import find_methods_section

    meter = meter or CallMeter()
    client = client or meter.client()
    text = find_methods_section(citing_text, text_source=text_source).text
    meter.label = "R"
    try:
        raw = _create(client, model, RELEASE_PROMPT.format(text=text), CitingReleases)
    except Exception as exc:
        return {
            "status": "call_failed",
            "error": f"{type(exc).__name__}: {exc}"[:500],
            "releases": [],
        }
    return {
        "status": "ok",
        "releases": [
            {"dataset": r.dataset, **_quoted(r.verbatim_quote, r.release, text, key="release")}
            for r in raw.releases
        ],
    }


_VERSION = r"\d+(?:\.\d+)*"
#: A release as a version or a range of versions ("2.0.1"; "1.0 \u2013 2.0.1"; "1.0 to 2.0.1"),
#: with an optional release word before or after ("Data Release 2.0"; "3.0 release", case one's
#: draw of 2026-11-03 evening). Anything else ("ABCD collection 3165") is not a release version.
_RELEASE = re.compile(
    rf"^\s*(?:(?:data\s+|fix\s+)?releases?\s+)?(?P<lo>{_VERSION})"
    rf"(?:\s*(?:-|\u2013|\u2014|to|through)\s*(?P<hi>{_VERSION}))?(?:\s+releases?)?\s*$",
    re.IGNORECASE,
)
_DATASET_FILLER = re.compile(r"\b(data|dataset|study|releases?|cohort)\b")


def _dataset_key(name: str) -> str:
    """A dataset's name for matching: its parenthesised acronym when it has one ("Adolescent Brain
    Cognitive Development (ABCD) study" -> "abcd"), else the name without filler words."""
    acronym = re.search(r"\(([A-Za-z][A-Za-z0-9\-]+)\)", name)
    base = acronym.group(1) if acronym else _DATASET_FILLER.sub(" ", _norm_name(name))
    return re.sub(r"[^a-z0-9]", "", base.lower())


def parse_release(release: str) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """``(low, high)`` version tuples: equal for one version, the two ends for a range (the
    author, 2026-11-03: "1.0 \u2013 2.0.1" is a range). None when the string is not a release
    version or range."""
    m = _RELEASE.match(release)
    if m is None:
        return None

    def v(x: str) -> tuple[int, ...]:
        return tuple(int(p) for p in x.split("."))

    lo, hi = v(m.group("lo")), v(m.group("hi") or m.group("lo"))
    return (lo, hi) if lo <= hi else None


def _checked(r: dict[str, Any]) -> bool:
    return bool(r.get("quote_resolved") and r.get("release_in_quote"))


def release_relation(citing: dict[str, Any], described: list[dict[str, Any]]) -> str:
    """Whether a citing paper's release is later than every release of the same dataset the cited
    paper describes: ``postdates``, ``not_later``, or ``undetermined`` (no checked release of the
    same dataset described, or a release that is not a version or range). Release DATES are not
    known here (the KB backlog's dataset-release table); only version numbers are compared."""
    mine = parse_release(str(citing.get("release", ""))) if _checked(citing) else None
    key = _dataset_key(str(citing.get("dataset", "")))
    same = [
        r
        for d in described
        if _checked(d) and _dataset_key(str(d.get("dataset", ""))) == key
        for r in [parse_release(str(d.get("release", "")))]
        if r is not None
    ]
    if mine is None or not same:
        return "undetermined"
    return "postdates" if mine[0] > max(hi for _, hi in same) else "not_later"


# ---------------------------------------------------------------------------
# 5. The releases the cited paper describes (call RD, on its methods slice; 2026-11-03, afternoon)
# ---------------------------------------------------------------------------

CITED_RELEASE_PROMPT = """\
You are reading the methods of a neuroimaging paper that describes a processing pipeline. List each
named release of a dataset whose processing this text describes (e.g. a dataset's release numbers, or
a range of them). For each: dataset (the dataset's name as written), release (the release number or
range as written), verbatim_quote (copied exactly from the text). Only releases the text names. None
named: an empty list.

Text:
\"\"\"
{text}
\"\"\"
"""


def described_releases(
    text: str, model: str, *, client: Any, meter: CallMeter | None = None
) -> list[dict[str, Any]]:
    """The releases the cited paper describes, each quote-checked. Read on the methods slice, not
    the fMRI section: a pipeline paper names its releases in its overview (Hagler et al. (2019),
    \u00a72.1). A failed call is an empty list with the failure recorded in its call entry."""
    if meter is not None:
        meter.label = "RD"
    try:
        raw = _create(client, model, CITED_RELEASE_PROMPT.format(text=text), CitingReleases)
    except Exception:
        return []
    return [
        {"dataset": r.dataset, **_quoted(r.verbatim_quote, r.release, text, key="release")}
        for r in raw.releases
    ]


# ---------------------------------------------------------------------------
# 6. Deterministic rules on the hop's fields (the author, 2026-11-03, afternoon)
# ---------------------------------------------------------------------------


def apply_rules(fields: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Values that follow from an extracted value by rule, never written into the extraction arm.
    Rule ``rigid_no_nonlinear``: an EXTRACTED rigid coregistration transform makes
    ``coregistration.nonlinear_transform_type`` not applicable, when that field was not reported.
    Recorded beside the fields (the spec's derived basis caps confidence at 0.70, which a rule that
    always holds does not fit)."""
    out: dict[str, dict[str, Any]] = {}
    tr = fields.get("coregistration.transform")
    nl = fields.get("coregistration.nonlinear_transform_type")
    if (
        tr is not None
        and nl is not None
        and tr.extraction.status == "EXTRACTED"
        and nl.extraction.status == "MISSING_FROM_PAPER"
        and any(str(getattr(t, "resolved", None)) == "rigid" for t in _terms(tr.extraction.value))
    ):
        out["coregistration.nonlinear_transform_type"] = {
            "value": "not applicable",
            "rule": "rigid_no_nonlinear",
            "source_fields": ["coregistration.transform"],
            "note": "the coregistration transform is rigid, so no nonlinear transform is used",
        }
    return out
