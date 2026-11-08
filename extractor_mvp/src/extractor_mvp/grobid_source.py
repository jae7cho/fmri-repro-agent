"""GROBID as a text source, behind the text-layer interface (the author's request of 2026-11-06).

GROBID is the default text source (the author's ruling 1 of 2026-11-08, after
``docs/findings/grobid_rerun_v1.md``): a paper is read through a running GROBID server.
``AESPA_TEXT_SOURCE=pypdf`` (or ``aespa-report --text-source pypdf``) reads it with pypdf as before
(``pdf_loader.load_pdf_text``). No model calls.

A PDF goes to ``/api/processFulltextDocument`` once; the TEI is cached on disk by the PDF's sha256,
the GROBID image label and the server version, so the full and CRF images never share an entry. The text is the TEI
body and back matter flattened (:func:`flatten_tei`). If the server is unreachable, or answers with no TEI, the paper
is read with pypdf and the record says why (``text_source_fallback``).

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
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
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
