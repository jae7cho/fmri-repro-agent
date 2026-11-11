"""A paper's date for the pipeline-defaults block (2026-11-11, the author's item 1).

In order of preference:

1. a stored ``paper_date`` on the record;
2. CrossRef's ``issued`` date for the paper's own DOI: a DOI printed on page 1, accepted only when
   CrossRef's title matches the paper's at 0.90 or more (``doi_date_resolver``'s rule, so a cited
   paper's DOI is never taken);
3. the date the paper prints as accepted, then as received (pages 1-2 of the text layer);
4. the PDF's creation date (the extraction's own proxy).

CrossRef is called with the project's generic client name and no email. The cache holds, per
DOI, only the issued date and whether the title matched, keyed by the DOI's sha256: no DOI is
written to disk or printed (the standing rule for held-out papers)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from extractor_mvp.citation_hop import CROSSREF_USER_AGENT

TITLE_MATCH = 0.90  # doi_date_resolver's gate
_MONTHS = {
    m: i
    for i, ms in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        1,
    )
    for m in ms
}
_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_DATE_FORMS = [
    (re.compile(rf"(\d{{1,2}})\s+{_MONTH},?\s+(\d{{4}})", re.I), ("d", "m", "y")),
    (re.compile(rf"{_MONTH}\s+(\d{{1,2}}),?\s+(\d{{4}})", re.I), ("m", "d", "y")),
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), ("y", "mn", "d")),
]


def parse_printed_date(text: str) -> date | None:
    """The first date in ``text`` written as '12 March 2016', 'March 12, 2016' or
    '2016-03-12'."""
    best: tuple[int, date] | None = None
    for rx, order in _DATE_FORMS:
        m = rx.search(text)
        if not m:
            continue
        parts = dict(zip(order, m.groups(), strict=True))
        try:
            month = _MONTHS[parts["m"].lower().rstrip(".")] if "m" in parts else int(parts["mn"])
            found = date(int(parts["y"]), month, int(parts["d"]))
        except (KeyError, ValueError):
            continue
        if best is None or m.start() < best[0]:
            best = (m.start(), found)
    return best[1] if best else None


def printed_dates(text: str) -> dict[str, date]:
    """The dates the paper prints as received and accepted: 'Received 12 March 2016',
    'Accepted: March 30, 2016', 'Received in revised form ...' is not 'received'."""
    out: dict[str, date] = {}
    for key, rx in (
        ("received", re.compile(r"\breceived(?!\s+in\s+revised)\b[:\s]*", re.I)),
        ("accepted", re.compile(r"\baccepted\b(?:\s+for\s+publication)?[:\s]*", re.I)),
    ):
        for m in rx.finditer(text):
            found = parse_printed_date(text[m.end() : m.end() + 40])
            if found is not None:
                out[key] = found
                break
    return out


def _cache_dir() -> Path:
    return Path(os.environ.get("AESPA_CACHE_DIR", Path.home() / ".cache" / "aespa")) / "paper_dates"


def _http_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": CROSSREF_USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8", "replace"))
            return data
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def _crossref_message(doi: str) -> dict[str, Any] | None:
    data = _http_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
    msg = (data or {}).get("message")
    return msg if isinstance(msg, dict) else None


#: CrossRef lookups go through this (tests replace it); returns the works message or None
FETCH: Callable[[str], dict[str, Any] | None] = _crossref_message


def crossref_issued(path: Path, *, cache_dir: Path | None = None) -> date | None:
    """CrossRef's ``issued`` date for the paper's own DOI (page 1, title match >= 0.90), or
    None. The cache keeps only {issued, matched} per sha256 of the DOI."""
    from pypdf import PdfReader

    from extractor_mvp.doi_date_resolver import (
        _date_parts_to_date,
        _page1_dois,
        _page1_title,
        _title_ratio,
    )

    try:
        reader = PdfReader(str(path))
        dois = _page1_dois(reader)
        title = _page1_title(reader)
    except Exception:
        return None
    cdir = cache_dir or _cache_dir()
    for doi in dois:
        key = hashlib.sha256(doi.lower().encode()).hexdigest()
        cached = cdir / f"{key}.json"
        entry: dict[str, Any] | None = None
        if cached.is_file():
            try:
                entry = json.loads(cached.read_text())
            except ValueError:
                entry = None
        if entry is None:
            msg = FETCH(doi)
            if msg is None:
                continue  # not reachable now: not cached, try the next DOI
            got_title = " ".join(msg.get("title") or [])
            issued = _date_parts_to_date(msg.get("issued"))
            entry = {
                "matched": bool(title) and _title_ratio(title, got_title) >= TITLE_MATCH,
                "issued": issued.isoformat() if issued else None,
            }
            cdir.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(entry))
        if entry.get("matched") and entry.get("issued"):
            return date.fromisoformat(str(entry["issued"]))
    return None


def _front_text(path: Path) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:2])
    except Exception:
        return ""


def paper_date(record: dict[str, Any]) -> tuple[date, str] | None:
    """``(date, what it is)`` by the module's order of preference, or None."""
    if record.get("paper_date"):
        return date.fromisoformat(str(record["paper_date"])[:10]), "the paper's stored date"
    path = Path(str(record.get("path") or ""))
    if not path.is_file():
        return None
    issued = crossref_issued(path)
    if issued is not None:
        return issued, "CrossRef issued date"
    printed = printed_dates(_front_text(path))
    if "accepted" in printed:
        return printed["accepted"], "the paper's printed accepted date"
    if "received" in printed:
        return printed["received"], "the paper's printed received date"
    from extractor_mvp.pdf_loader import pdf_creation_date

    created = pdf_creation_date(path)
    return (created, "the PDF's creation date") if created else None
