"""GROBID as a text source, behind the text-layer interface (the author's request of 2026-11-06).

GROBID is the default text source (the author's ruling 1 of 2026-11-08, after
``docs/findings/grobid_rerun_v1.md``): a paper is read through a running GROBID server.
``AESPA_TEXT_SOURCE=pypdf`` (or ``aespa-report --text-source pypdf``) reads it with pypdf as before
(``pdf_loader.load_pdf_text``). No model calls.

A PDF goes to ``/api/processFulltextDocument`` once; the TEI is cached on disk by the PDF's sha256,
the GROBID image label and the server version, so the full and CRF images never share an entry. The text is the TEI
body and back matter flattened (:func:`flatten_tei`). If the server is unreachable, or answers with no TEI, the paper
is read with pypdf and the record says why (``text_source_fallback``); so is a well-formed TEI whose
body is implausibly short against pypdf's text (``batch.grobid_output_short``, 2026-11-08).

The text source is recorded as ``grobid-<version>-<image>`` (e.g. ``grobid-0.9.1-crf``) or
``pypdf``. GROBID's API reports its version but not its image, so the image label comes from
``AESPA_GROBID_IMAGE`` (default ``crf``).

The image AESPA expects (the author's ruling 4 of 2026-11-06) is ``lfoppiano/grobid:0.9.1-crf``:
native arm64, 1.7 GB, and its flattened text matched the full image's on the three papers compared
except one competing-interests paragraph (``docs/findings/grobid_gate_v2.md`` section 6). Run it as::

    docker run -d --name grobid -p 8070:8070 lfoppiano/grobid:0.9.1-crf

``lfoppiano/grobid:0.9.1-full`` (amd64 only, 37.4 GB) remains an option; run it on the same port and
set ``AESPA_GROBID_IMAGE=full`` so records and the cache say which image read the paper.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from extractor_mvp.span_resolver import CITATION_CLOSE, CITATION_OPEN

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

#: Environment switches. The default text source is GROBID; pypdf when asked for.
TEXT_SOURCE_ENV = "AESPA_TEXT_SOURCE"
GROBID_URL_ENV = "AESPA_GROBID_URL"
GROBID_IMAGE_ENV = "AESPA_GROBID_IMAGE"
GROBID_CACHE_ENV = "AESPA_GROBID_CACHE"
DEFAULT_URL = "http://localhost:8070"
DEFAULT_IMAGE = "crf"
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / ".grobid_cache"

PYPDF = "pypdf"


def text_source_requested() -> str:
    """ "pypdf" when the flag asks for it, else "grobid" (the default since 2026-11-08)."""
    return PYPDF if os.environ.get(TEXT_SOURCE_ENV, "").strip().lower() == PYPDF else "grobid"


# --- flattening -----------------------------------------------------------------------------------


#: A ref whose own text is bare numerals: digits, ranges (3-5, 3\u20135) and comma lists, as a
#: numbered style prints them (cattarinussi_2026: "4 , 5", "5 -7"; cole_2013: "1,").
_NUM = r"\d+(?:\s*[-\u2013\u2014]\s*\d+)?"
_BARE_NUMERALS = re.compile(rf"{_NUM}(?:\s*,\s*{_NUM})*\s*,?")


def _ref_marker(ref: ET.Element, inside_bracket: bool) -> str:
    """A bibliographic ref as the paper prints it (the author's fix 1 of 2026-11-06): its own text
    verbatim, bracketed as ``[..]`` only when that text is bare numerals and the paper has not
    already opened a bracket around it (weber_2024 prints ``[5, 25, 35]``, GROBID's refs reading
    ``[5,``, ``25,`` and ``35]``). Never the reference's index. The citation is carried between
    ``span_resolver.CITATION_OPEN`` and ``CITATION_CLOSE`` (the author's ruling 2 of 2026-11-06),
    so a quote matches with or without any citation text (tier 5b)."""
    own = " ".join("".join(ref.itertext()).split())
    if not own:
        return ""
    if not inside_bracket and _BARE_NUMERALS.fullmatch(own):
        own = f"[{own}]"
    return f"{CITATION_OPEN}{own}{CITATION_CLOSE}"


def _open_bracket(parts: list[str]) -> bool:
    """True when the text so far has a ``[`` not yet closed."""
    depth = 0
    for c in "".join(parts):
        if c == "[":
            depth += 1
        elif c == "]" and depth:
            depth -= 1
    return depth > 0


def _inline(el: ET.Element) -> str:
    """The text of a <head> or <p>, a bibliographic ref as its marker, any figure or table
    inside it dropped, every other element's text kept."""
    out = [el.text or ""]
    for ch in el:
        if ch.tag == TEI + "ref" and ch.get("type") == "bibr":
            out.append(_ref_marker(ch, _open_bracket(out)))
        elif ch.tag in (TEI + "figure", TEI + "table"):
            pass
        else:
            out.append(_inline(ch))
        out.append(ch.tail or "")
    return "".join(out)


def _walk(el: ET.Element, lines: list[str]) -> None:
    for ch in el:
        if ch.tag in (TEI + "figure", TEI + "table", TEI + "listBibl"):
            continue  # captions, cells, figure text and the reference list are not the paper's prose
        if ch.tag in (TEI + "head", TEI + "p"):
            line = " ".join(_inline(ch).split())
            if line:
                lines.append(line)
            continue
        _walk(ch, lines)


def flatten_tei(tei: bytes | str) -> str:
    """The TEI ``<body>`` and then ``<back>`` as text: each <head> and <p> on its own line, in
    document order; a ``<ref type="bibr">`` as the paper prints it (:func:`_ref_marker`); <figure>,
    <table> and <listBibl> excluded, as is everything outside <text>. <back> is read (the author's
    fix 2 of 2026-11-06): GROBID files a methods section printed after the main text (PNAS,
    Nature Communications) as ``<div type="annex">`` there; viduarre_2017's methods sit in one."""
    root = ET.fromstring(tei)
    text = root.find(f".//{TEI}text")
    if text is None:
        return ""
    lines: list[str] = []
    for part in ("body", "back"):
        el = text.find(f"{TEI}{part}")
        if el is not None:
            _walk(el, lines)
    return "\n".join(lines)


# --- the server and the cache ---------------------------------------------------------------------


@dataclass(frozen=True)
class GrobidText:
    text: str
    text_source: str  # grobid-<version>-<image>
    tei_path: Path


class GrobidUnavailableError(Exception):
    """The server could not be reached, or did not return TEI."""


def _url() -> str:
    return os.environ.get(GROBID_URL_ENV, DEFAULT_URL).rstrip("/")


def _image() -> str:
    return os.environ.get(GROBID_IMAGE_ENV, DEFAULT_IMAGE).strip() or DEFAULT_IMAGE


def _cache_dir() -> Path:
    return Path(os.environ.get(GROBID_CACHE_ENV) or DEFAULT_CACHE)


def _http(url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=300) as resp:
        body: bytes = resp.read()
        return body


def server_version() -> str:
    """GROBID's version, from ``/api/version``; raises GrobidUnavailableError."""
    import json

    try:
        return str(json.loads(_http(f"{_url()}/api/version"))["version"])
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        raise GrobidUnavailableError(f"{type(exc).__name__}: {exc}") from exc


def _multipart(pdf: Path) -> tuple[bytes, str]:
    boundary = "----aespa-grobid-" + hashlib.sha1(pdf.name.encode()).hexdigest()
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="input"; '
        f'filename="{pdf.name}"\r\nContent-Type: application/pdf\r\n\r\n'
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    return head + pdf.read_bytes() + tail, f"multipart/form-data; boundary={boundary}"


def pdf_sha256(pdf: Path) -> str:
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


def fetch_tei(pdf: Path) -> tuple[bytes, str, Path]:
    """The PDF's TEI, from the cache (``<sha256>.<image>.<version>.tei.xml``) or the server, with the
    server's version. Raises GrobidUnavailableError."""
    version = server_version()
    image = _image()
    cache = _cache_dir() / f"{pdf_sha256(pdf)}.{image}.{version}.tei.xml"
    if cache.is_file():
        return cache.read_bytes(), version, cache
    body, ctype = _multipart(pdf)
    try:
        tei = _http(
            f"{_url()}/api/processFulltextDocument", data=body, headers={"Content-Type": ctype}
        )
    except (urllib.error.URLError, OSError) as exc:
        raise GrobidUnavailableError(f"{type(exc).__name__}: {exc}") from exc
    if not tei.lstrip().startswith(b"<"):
        raise GrobidUnavailableError("the server returned no TEI")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(tei)
    return tei, version, cache


def cached_tei(pdf: Path, text_source: str) -> bytes:
    """The TEI a paper's text was read from, out of the cache, named by the record's
    ``text_source`` (``grobid-<version>-<image>``): no server call, so the hop reads the same TEI
    the extraction did. Raises GrobidUnavailableError when the source is not GROBID's or the
    cache has no such entry."""
    version, _, image = text_source.removeprefix("grobid-").rpartition("-")
    if not text_source.startswith("grobid-") or not version or not image:
        raise GrobidUnavailableError(f"not a GROBID text source: {text_source!r}")
    cache = _cache_dir() / f"{pdf_sha256(pdf)}.{image}.{version}.tei.xml"
    if not cache.is_file():
        raise GrobidUnavailableError(f"no cached TEI {cache.name}")
    return cache.read_bytes()


def grobid_text(pdf: Path) -> GrobidText:
    """The PDF's flattened TEI body. Raises GrobidUnavailableError."""
    tei, version, path = fetch_tei(pdf)
    try:
        text = flatten_tei(tei)
    except ET.ParseError as exc:
        raise GrobidUnavailableError(f"the TEI did not parse: {exc}") from exc
    if not text.strip():
        raise GrobidUnavailableError("the TEI body is empty")
    return GrobidText(text, f"grobid-{version}-{_image()}", path)


# --- the citation hop's references: <ref type="bibr" target="#bNN"> -> <biblStruct xml:id="bNN"> --


@dataclass(frozen=True)
class BiblEntry:
    """One ``<listBibl><biblStruct>`` of the TEI: its id and the fields the hop's on-disk lookup
    reads (first author's surname, year, DOI), with the title and every author's surname."""

    bibl_id: str
    title: str | None
    authors: tuple[str, ...]
    year: str | None
    doi: str | None


def _text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    s = " ".join("".join(el.itertext()).split())
    return s or None


def _surnames(el: ET.Element | None) -> tuple[str, ...]:
    if el is None:
        return ()
    return tuple(
        s for a in el.findall(f"{TEI}author") if (s := _text(a.find(f"{TEI}persName/{TEI}surname")))
    )


def bibliography(tei: bytes | str) -> dict[str, BiblEntry]:
    """The TEI's reference list (``<listBibl>``) by ``xml:id``. An entry's authors and title are
    the article's (``<analytic>``) when it has them, else the volume's (``<monogr>``); its year is
    the first ``<date when=..>``'s first four digits; its DOI is ``<idno type="DOI">``."""
    root = ET.fromstring(tei)
    out: dict[str, BiblEntry] = {}
    for b in root.iter(f"{TEI}biblStruct"):
        bid = b.get(XML_ID)
        if not bid:
            continue
        analytic, monogr = b.find(f"{TEI}analytic"), b.find(f"{TEI}monogr")
        authors = _surnames(analytic) or _surnames(monogr)
        title = _text(analytic.find(f"{TEI}title") if analytic is not None else None) or _text(
            monogr.find(f"{TEI}title") if monogr is not None else None
        )
        year = None
        for d in b.iter(f"{TEI}date"):
            m = re.match(r"\d{4}", d.get("when") or "")
            if m:
                year = m.group(0)
                break
        doi = next(
            (
                t
                for i in b.iter(f"{TEI}idno")
                if (i.get("type") or "").upper() == "DOI" and (t := _text(i))
            ),
            None,
        )
        out[bid] = BiblEntry(bid, title, authors, year, doi)
    return out


@dataclass(frozen=True)
class SentenceRef:
    """A ``<ref type="bibr">`` inside a sentence: its own text and its target's id (``bNN``, the
    ``#`` dropped), None when the ref has no target."""

    text: str
    target: str | None


def _key_chars(s: str) -> str:
    """A character's matching key: NFKC, case-folded, letters and digits only. Whitespace,
    punctuation, quotes and the citation delimiters do not count, so a sentence matches however
    the text layer spaced, quoted or delimited it."""
    return "".join(c for c in unicodedata.normalize("NFKC", s).casefold() if c.isalnum())


def _keyed(el: ET.Element, refs: list[ET.Element]) -> list[tuple[str, int | None]]:
    """The text of a <head> or <p> as (key character, index of the bibr ref it sits in or None),
    figures and tables inside it dropped (as :func:`_inline` reads it)."""
    out: list[tuple[str, int | None]] = []

    def add(s: str | None, idx: int | None) -> None:
        for ch in s or "":
            out.extend((k, idx) for k in _key_chars(ch))

    def walk(e: ET.Element) -> None:
        add(e.text, None)
        for ch in e:
            if ch.tag == TEI + "ref" and ch.get("type") == "bibr":
                refs.append(ch)
                add("".join(ch.itertext()), len(refs) - 1)
            elif ch.tag not in (TEI + "figure", TEI + "table"):
                walk(ch)
            add(ch.tail, None)

    walk(el)
    return out


def _blocks(el: ET.Element) -> list[ET.Element]:
    found: list[ET.Element] = []
    for ch in el:
        if ch.tag in (TEI + "figure", TEI + "table", TEI + "listBibl"):
            continue
        if ch.tag in (TEI + "head", TEI + "p"):
            found.append(ch)
        else:
            found.extend(_blocks(ch))
    return found


def refs_in_sentence(tei: bytes | str, sentence: str) -> list[SentenceRef] | None:
    """The bibliographic refs inside ``sentence``, in order, from the first <head> or <p> of the
    TEI's body or back that contains it (compared on :func:`_key_chars`). None when no block
    contains the sentence; an empty list when it does and holds no bibr ref."""
    want = _key_chars(sentence)
    if not want:
        return None
    root = ET.fromstring(tei)
    text = root.find(f".//{TEI}text")
    if text is None:
        return None
    for part in ("body", "back"):
        el = text.find(f"{TEI}{part}")
        if el is None:
            continue
        for block in _blocks(el):
            refs: list[ET.Element] = []
            keyed = _keyed(block, refs)
            at = "".join(k for k, _ in keyed).find(want)
            if at < 0:
                continue
            inside: list[int] = []
            for _k, idx in keyed[at : at + len(want)]:
                if idx is not None and idx not in inside:
                    inside.append(idx)
            out = []
            for i in inside:
                target = (refs[i].get("target") or "").strip().lstrip("#") or None
                out.append(SentenceRef(" ".join("".join(refs[i].itertext()).split()), target))
            return out
    return None


#: The share of a deferring sentence's words (four characters or more, not numerals) that must sit
#: around a ref for :func:`refs_near_sentence` to take it: the extractor's sentence is not always
#: the paper's verbatim (a word or two reworded), so an exact match alone misses it.
MIN_SENTENCE_OVERLAP = 0.6
_WORD = re.compile(r"[^\W_]+")


def _words(s: str) -> set[str]:
    return {
        w
        for t in _WORD.findall(unicodedata.normalize("NFKC", s))
        if len(w := t.casefold()) > 3 and not w.isdigit()
    }


def _spanned(el: ET.Element) -> tuple[str, list[tuple[int, int, ET.Element]]]:
    """The text of a <head> or <p> (figures and tables dropped) and each bibr ref's span in it."""
    parts: list[str] = []
    spans: list[tuple[int, int, ET.Element]] = []
    n = 0

    def add(s: str | None) -> None:
        nonlocal n
        if s:
            parts.append(s)
            n += len(s)

    def walk(e: ET.Element) -> None:
        add(e.text)
        for ch in e:
            if ch.tag == TEI + "ref" and ch.get("type") == "bibr":
                start = n
                add("".join(ch.itertext()))
                spans.append((start, n, ch))
            elif ch.tag not in (TEI + "figure", TEI + "table"):
                walk(ch)
            add(ch.tail)

    walk(el)
    return "".join(parts), spans


def refs_near_sentence(
    tei: bytes | str, sentence: str, keep: Callable[[str], bool]
) -> tuple[list[SentenceRef], float] | None:
    """The deferral's refs when the sentence is not in the TEI verbatim: every run of adjacent
    bibr refs whose own text ``keep`` accepts is scored by the share of the sentence's words found
    within one sentence-length of it, in its own <head> or <p>. The best run is taken when its share
    is at least :data:`MIN_SENTENCE_OVERLAP` and no other run scores as well; else None. Returns
    the run's refs and its share."""
    want = _words(sentence)
    if not want:
        return None
    reach = len(sentence)
    root = ET.fromstring(tei)
    text = root.find(f".//{TEI}text")
    if text is None:
        return None
    scored: list[tuple[float, list[ET.Element]]] = []
    for part in ("body", "back"):
        el = text.find(f"{TEI}{part}")
        if el is None:
            continue
        for block in _blocks(el):
            raw, spans = _spanned(block)
            runs: list[list[tuple[int, int, ET.Element]]] = []
            for sp in spans:
                if not keep(" ".join("".join(sp[2].itertext()).split())):
                    continue
                if runs and not any(c.isalnum() for c in raw[runs[-1][-1][1] : sp[0]]):
                    runs[-1].append(sp)
                else:
                    runs.append([sp])
            for run in runs:
                window = raw[max(0, run[0][0] - reach) : run[-1][1] + reach]
                scored.append((len(want & _words(window)) / len(want), [sp[2] for sp in run]))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    best, refs = scored[0]
    if best < MIN_SENTENCE_OVERLAP or (len(scored) > 1 and scored[1][0] == best):
        return None
    out = [
        SentenceRef(
            " ".join("".join(r.itertext()).split()),
            (r.get("target") or "").strip().lstrip("#") or None,
        )
        for r in refs
    ]
    return out, round(best, 3)
