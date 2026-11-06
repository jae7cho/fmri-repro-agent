"""GROBID as a text source, behind the text-layer interface (the author's request of 2026-11-06).

Flag-gated: ``AESPA_TEXT_SOURCE=grobid`` (or ``aespa-report --text-source grobid``) reads a paper
through a running GROBID server; anything else, the default, reads it with pypdf as before
(``pdf_loader.load_pdf_text``). No model calls.

A PDF goes to ``/api/processFulltextDocument`` once; the TEI is cached on disk by the PDF's sha256,
the GROBID image label and the server version, so the full and CRF images never share an entry. The text is the TEI
body flattened (:func:`flatten_tei`). If the server is unreachable, or answers with no TEI, the paper
is read with pypdf and the record says why (``text_source_fallback``).

The text source is recorded as ``grobid-<version>-<image>`` (e.g. ``grobid-0.9.1-full``) or
``pypdf``. GROBID's API reports its version but not its image, so the image label comes from
``AESPA_GROBID_IMAGE`` (default ``full``).
"""

from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

#: Environment switches. The default text source is pypdf; GROBID only when asked for.
TEXT_SOURCE_ENV = "AESPA_TEXT_SOURCE"
GROBID_URL_ENV = "AESPA_GROBID_URL"
GROBID_IMAGE_ENV = "AESPA_GROBID_IMAGE"
GROBID_CACHE_ENV = "AESPA_GROBID_CACHE"
DEFAULT_URL = "http://localhost:8070"
DEFAULT_IMAGE = "full"
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / ".grobid_cache"

PYPDF = "pypdf"


def text_source_requested() -> str:
    """ "grobid" when the flag asks for it, else "pypdf" (the default)."""
    return "grobid" if os.environ.get(TEXT_SOURCE_ENV, "").strip().lower() == "grobid" else PYPDF


# --- flattening -----------------------------------------------------------------------------------


def _ref_marker(ref: ET.Element) -> str:
    """``[n]`` for a bibliographic ref: n is the reference's position in the paper's list, from
    its target (GROBID's ``#b0`` is the first entry, so n = index + 1, the number a numbered style
    prints); without a usable target, the ref's own text in brackets."""
    target = (ref.get("target") or "").strip()
    if target.startswith("#b") and target[2:].isdigit():
        return f"[{int(target[2:]) + 1}]"
    own = " ".join("".join(ref.itertext()).split())
    return f"[{own}]"


def _inline(el: ET.Element) -> str:
    """The text of a <head> or <p>, a bibliographic ref replaced by its marker, any figure or table
    inside it dropped, every other element's text kept."""
    out = [el.text or ""]
    for ch in el:
        if ch.tag == TEI + "ref" and ch.get("type") == "bibr":
            out.append(_ref_marker(ch))
        elif ch.tag in (TEI + "figure", TEI + "table"):
            pass
        else:
            out.append(_inline(ch))
        out.append(ch.tail or "")
    return "".join(out)


def _walk(el: ET.Element, lines: list[str]) -> None:
    for ch in el:
        if ch.tag in (TEI + "figure", TEI + "table"):
            continue  # captions, cells and figure text are not the paper's prose
        if ch.tag in (TEI + "head", TEI + "p"):
            line = " ".join(_inline(ch).split())
            if line:
                lines.append(line)
            continue
        _walk(ch, lines)


def flatten_tei(tei: bytes | str) -> str:
    """The TEI ``<body>`` as text: each <head> and <p> on its own line, in document order;
    ``<ref type="bibr">`` as ``[n]``; <figure> and <table> excluded; <back> (the reference list,
    acknowledgements, annexes) excluded, as is everything outside <body>."""
    root = ET.fromstring(tei)
    body = root.find(f".//{TEI}text/{TEI}body")
    if body is None:
        return ""
    lines: list[str] = []
    _walk(body, lines)
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
