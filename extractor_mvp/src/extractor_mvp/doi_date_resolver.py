"""Standalone, OPTIONAL corpus date-resolution tool.

This is NOT wired into the deterministic extraction pipeline (``batch.py`` /
``extractor.py`` / ``pdf_loader.py`` are untouched). It is a separate script that
emits a *reviewable sidecar* mapping each corpus PDF to a confirmed publication date
and its provenance, for a later, separate follow-up that may override ``pdf_date``.
The core pipeline stays offline/deterministic; this tool is what reaches the network.

Per PDF (all extraction offline via pypdf; HTTP via stdlib ``urllib``; title matching
via stdlib ``difflib`` — no new dependency):

1. Extract candidate DOIs from PAGE 1 ONLY (reference lists on later pages contaminate)
   and a candidate title (``/Title`` metadata if it looks real, else the first
   substantial line-block of page-1 text). Title extraction is heuristic.
2. Confirm via CrossRef, gated on a >= 0.90 difflib title match (so we accept a DOI
   only when it is *this paper's* DOI, not a cited one). Fall back across the other
   page-1 DOIs, then a CrossRef bibliographic title search.
3. Pick the EARLIEST of published-online / published-print / issued as an upper bound
   on when the work was done (research predates publication). ``created`` is ignored
   (deposit metadata, not publication).
4. Cross-check the date against OpenAlex; a > ~1yr disagreement flags NEEDS_REVIEW.
5. If the confirmed DOI is a preprint (CrossRef ``type == 'posted-content'``), flag it and
   record the published version of record when discoverable, but KEEP the preprint date:
   it is the tighter upper bound on when preprocessing ran (the work predates the version
   of record by review/production lag). The VOR is surfaced for a human promotion call, not
   silently substituted.
6. Cache every raw API response to disk so re-runs are idempotent and need no network.

The sidecar (CSV) is sorted NEEDS_REVIEW / NO_DOI / confirmed-preprint first for eyeballing.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from pypdf import PdfReader

_DOI_RE = re.compile(r'10\.\d{4,9}/[^\s"<>)\]]+')
_TITLE_MATCH_THRESHOLD = 0.90
_DATE_CONFLICT_DAYS = 366  # > ~1 year apart -> flag
_HTTP_TIMEOUT = 20
_POLITE_SLEEP = 0.3  # seconds between *network* calls (skipped on cache hits)
_DEFAULT_MAILTO = "anonymous@example.com"


# ---------------------------------------------------------------------------
# Result record (one row per paper in the sidecar)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class DateResult:
    filename: str
    primary_doi_extracted: str = ""
    confirmed_doi: str = ""
    title_pdf: str = ""
    title_crossref: str = ""
    title_match_ratio: float = 0.0
    date: str = ""
    date_field: str = ""  # issued | online | print
    date_source: str = ""  # crossref | openalex | title-search
    openalex_date: str = ""
    date_conflict: bool = False
    is_preprint: bool = False  # confirmed DOI is a preprint (posted-content)
    version_of_record_doi: str = ""  # published VOR discovered for a preprint, if any
    status: str = "NEEDS_REVIEW"  # CONFIRMED | NEEDS_REVIEW | NO_DOI
    notes: str = ""


_STATUS_SORT = {"NEEDS_REVIEW": 0, "NO_DOI": 1, "CONFIRMED": 2}


def _sort_tier(r: DateResult) -> float:
    """A CONFIRMED-but-preprint row still needs a human promotion call -> surface it."""
    if r.status == "CONFIRMED" and r.is_preprint:
        return 1.5  # between NO_DOI and plain CONFIRMED
    return _STATUS_SORT.get(r.status, 0)


# ---------------------------------------------------------------------------
# Offline PDF extraction (page 1 only)
# ---------------------------------------------------------------------------


def _clean_doi(raw: str) -> str:
    """Strip trailing punctuation and a trailing literal 'doi' from a raw DOI match."""
    doi = raw.strip().rstrip(".,;:")
    doi = re.sub(r"[)\]}>]+$", "", doi)
    doi = re.sub(r"doi$", "", doi, flags=re.IGNORECASE).rstrip(".,;:/")
    return doi


def _page1_dois(reader: PdfReader) -> list[str]:
    """All DOIs on PAGE 1 (deduped, order-preserving); page 1 avoids reference-list DOIs."""
    if not reader.pages:
        return []
    try:
        text = reader.pages[0].extract_text() or ""
    except Exception:
        return []
    seen: dict[str, None] = {}
    for m in _DOI_RE.finditer(text):
        doi = _clean_doi(m.group(0))
        if doi and doi not in seen:
            seen[doi] = None
    return list(seen)


def _looks_like_real_title(t: str) -> bool:
    if not t or len(t.strip()) < 12:
        return False
    low = t.strip().lower()
    if low.startswith("microsoft word"):
        return False
    if low.endswith((".doc", ".docx", ".pdf", ".tex", ".rtf")):
        return False
    if " " not in t.strip():  # a bare filename/token, not a title
        return False
    return True


def _page1_title(reader: PdfReader) -> str:
    """Prefer /Title metadata if it looks real; else the first substantial page-1 line-block."""
    meta: Any = reader.metadata or {}
    meta_title = str(meta.get("/Title") or "").strip()
    if _looks_like_real_title(meta_title):
        return " ".join(meta_title.split())

    try:
        text = reader.pages[0].extract_text() or "" if reader.pages else ""
    except Exception:
        text = ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    block: list[str] = []
    for ln in lines[:15]:
        # skip obvious non-title early lines
        if _DOI_RE.search(ln) or ln.lower().startswith(("http", "www.", "doi")):
            if not block:
                continue
        if len(ln) >= 20 and any(c.isalpha() for c in ln) and not ln.isupper():
            block.append(ln)
            # a title is usually 1-3 lines; stop once we have a decent span
            if sum(len(b) for b in block) > 60:
                break
        elif block:
            break
    return " ".join(" ".join(block).split())


# ---------------------------------------------------------------------------
# Title normalization + matching (difflib, no new dep)
# ---------------------------------------------------------------------------


def _norm_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)  # strip punctuation
    return " ".join(t.split())


def _title_ratio(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


# ---------------------------------------------------------------------------
# Cached HTTP (stdlib urllib)
# ---------------------------------------------------------------------------


def _cache_key(kind: str, ident: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", ident)[:180]
    return f"{kind}__{safe}.json"


def _http_json(
    url: str, *, mailto: str, cache_dir: Path, cache_name: str
) -> tuple[dict[str, Any] | None, str]:
    """GET JSON with on-disk cache. Returns (parsed_or_None, note). Never raises."""
    cache_path = cache_dir / cache_name
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text()), "cache"
        except Exception:
            pass  # corrupt cache -> refetch
    ua = f"fmri-repro-agent (mailto:{mailto})"
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
    try:
        time.sleep(_POLITE_SLEEP)
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", "replace")
        data = json.loads(body)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(body)
        return data, "net"
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return None, f"neterror:{type(e).__name__}"
    except Exception as e:  # json decode, etc.
        return None, f"error:{type(e).__name__}"


# ---------------------------------------------------------------------------
# CrossRef / OpenAlex
# ---------------------------------------------------------------------------


def _crossref_by_doi(
    doi: str, *, mailto: str, cache_dir: Path
) -> tuple[dict[str, Any] | None, str]:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={urllib.parse.quote(mailto)}"
    data, note = _http_json(
        url, mailto=mailto, cache_dir=cache_dir, cache_name=_cache_key("crossref_doi", doi)
    )
    if data is None:
        return None, note
    msg = data.get("message")
    return (msg if isinstance(msg, dict) else None), note


def _crossref_title_search(
    title: str, *, mailto: str, cache_dir: Path
) -> tuple[list[dict[str, Any]], str]:
    q = urllib.parse.quote(title)
    url = (
        f"https://api.crossref.org/works?query.bibliographic={q}&rows=5"
        f"&mailto={urllib.parse.quote(mailto)}"
    )
    data, note = _http_json(
        url, mailto=mailto, cache_dir=cache_dir, cache_name=_cache_key("crossref_query", title)
    )
    if data is None:
        return [], note
    items = data.get("message", {}).get("items", [])
    return (items if isinstance(items, list) else []), note


def _openalex_by_doi(doi: str, *, mailto: str, cache_dir: Path) -> tuple[str, str]:
    """Returns (publication_date_iso_or_'', note)."""
    url = (
        f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}"
        f"?mailto={urllib.parse.quote(mailto)}"
    )
    data, note = _http_json(
        url, mailto=mailto, cache_dir=cache_dir, cache_name=_cache_key("openalex_doi", doi)
    )
    if data is None:
        return "", note
    return str(data.get("publication_date") or ""), note


# ---------------------------------------------------------------------------
# Date selection
# ---------------------------------------------------------------------------


def _date_parts_to_date(field: dict[str, Any] | None) -> date | None:
    if not isinstance(field, dict):
        return None
    dp = field.get("date-parts")
    if not (isinstance(dp, list) and dp and isinstance(dp[0], list) and dp[0]):
        return None
    parts = [int(x) for x in dp[0][:3] if isinstance(x, int)]
    if not parts:
        return None
    y = parts[0]
    m = parts[1] if len(parts) > 1 else 1
    d = parts[2] if len(parts) > 2 else 1
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _pick_earliest_date(message: dict[str, Any]) -> tuple[date | None, str]:
    """Earliest of published-online, published-print, issued (upper bound). Returns (date, field)."""
    candidates: list[tuple[date, str]] = []
    for field_key, label in (
        ("published-online", "online"),
        ("published-print", "print"),
        ("issued", "issued"),
    ):
        d = _date_parts_to_date(message.get(field_key))
        if d is not None:
            candidates.append((d, label))
    if not candidates:
        return None, ""
    candidates.sort(key=lambda t: t[0])
    return candidates[0]


def _crossref_title(message: dict[str, Any]) -> str:
    t = message.get("title")
    if isinstance(t, list) and t:
        return str(t[0])
    return str(t or "")


def _is_preprint_message(message: dict[str, Any]) -> bool:
    """CrossRef preprints are type 'posted-content' with subtype 'preprint'."""
    return str(message.get("type")) == "posted-content" or str(message.get("subtype")) == "preprint"


def _find_version_of_record(
    pdf_title: str, preprint_doi: str, *, mailto: str, cache_dir: Path
) -> tuple[str, date | None, str]:
    """Locate a published version of record for a preprint via CrossRef title search.

    CrossRef's ``relation.is-preprint-of`` is frequently empty (verified against
    10.1101/084665), so we cannot follow the relation; instead we title-search and take
    the best non-preprint match. Returns (vor_doi, vor_date, note); ('', None, note) if none.
    """
    items, note = _crossref_title_search(pdf_title, mailto=mailto, cache_dir=cache_dir)
    best_ratio, best = 0.0, None
    for it in items:
        if str(it.get("type")) == "posted-content":
            continue  # skip the preprint itself and other preprints
        if str(it.get("DOI") or "").lower() == preprint_doi.lower():
            continue
        r = _title_ratio(pdf_title, _crossref_title(it))
        if r > best_ratio:
            best_ratio, best = r, it
    if best is not None and best_ratio >= _TITLE_MATCH_THRESHOLD:
        d, _ = _pick_earliest_date(best)
        return str(best.get("DOI") or ""), d, note
    return "", None, f"no VOR match (best ratio {best_ratio:.2f})"


# ---------------------------------------------------------------------------
# Per-paper resolution
# ---------------------------------------------------------------------------


def _confirm_via_doi(
    doi: str, pdf_title: str, res: DateResult, *, mailto: str, cache_dir: Path
) -> bool:
    """Try to confirm `doi` as the paper's own via title match. On success, fills res + returns True."""
    msg, note = _crossref_by_doi(doi, mailto=mailto, cache_dir=cache_dir)
    if msg is None:
        res.notes = (res.notes + f"; doi {doi}: {note}").strip("; ")
        return False
    cr_title = _crossref_title(msg)
    ratio = _title_ratio(pdf_title, cr_title) if pdf_title else 0.0
    if ratio < _TITLE_MATCH_THRESHOLD:
        res.notes = (
            res.notes + f"; doi {doi}: title ratio {ratio:.2f} < {_TITLE_MATCH_THRESHOLD}"
        ).strip("; ")
        return False
    d, field = _pick_earliest_date(msg)
    res.confirmed_doi = doi
    res.title_crossref = cr_title
    res.title_match_ratio = round(ratio, 3)
    res.date_source = "crossref"
    res.is_preprint = _is_preprint_message(msg)
    if d is not None:
        res.date = d.isoformat()
        res.date_field = field
    return True


def resolve_one(pdf_path: Path, *, mailto: str, cache_dir: Path) -> DateResult:
    res = DateResult(filename=pdf_path.name)
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        res.status = "NEEDS_REVIEW"
        res.notes = f"pdf_open_failed: {type(e).__name__}"
        return res

    dois = _page1_dois(reader)
    res.title_pdf = _page1_title(reader)
    if dois:
        res.primary_doi_extracted = dois[0]

    # 1) try each page-1 DOI (primary first) with the title-match gate
    for doi in dois:
        if _confirm_via_doi(doi, res.title_pdf, res, mailto=mailto, cache_dir=cache_dir):
            res.status = "CONFIRMED"
            break

    # 1b) if the confirmed DOI is a preprint, locate the published version of record but
    # KEEP the preprint date: it is the tighter upper bound on when preprocessing ran
    # (research predates the version of record by review/production lag). We only surface
    # the VOR so a human can make the promotion call; we do not silently swap the date.
    if res.status == "CONFIRMED" and res.is_preprint and res.title_pdf:
        vor_doi, vor_date, vnote = _find_version_of_record(
            res.title_pdf, res.confirmed_doi, mailto=mailto, cache_dir=cache_dir
        )
        if vor_doi:
            res.version_of_record_doi = vor_doi
            vor_str = f" ({vor_date.isoformat()})" if vor_date else ""
            res.notes = (
                res.notes + f"; preprint {res.confirmed_doi} -> VOR {vor_doi}{vor_str}; "
                "kept preprint date as conservative bound"
            ).strip("; ")
        else:
            res.notes = (res.notes + f"; preprint {res.confirmed_doi}; {vnote}").strip("; ")

    # 2) fall back to CrossRef bibliographic title search
    if res.status != "CONFIRMED":
        if res.title_pdf:
            items, note = _crossref_title_search(res.title_pdf, mailto=mailto, cache_dir=cache_dir)
            best_ratio, best = 0.0, None
            for it in items:
                r = _title_ratio(res.title_pdf, _crossref_title(it))
                if r > best_ratio:
                    best_ratio, best = r, it
            if best is not None and best_ratio >= _TITLE_MATCH_THRESHOLD:
                res.confirmed_doi = str(best.get("DOI") or "")
                res.title_crossref = _crossref_title(best)
                res.title_match_ratio = round(best_ratio, 3)
                res.date_source = "title-search"
                d, field = _pick_earliest_date(best)
                if d is not None:
                    res.date = d.isoformat()
                    res.date_field = field
                res.status = "CONFIRMED"
            else:
                res.title_match_ratio = round(best_ratio, 3)
                res.notes = (
                    res.notes + f"; title-search best ratio {best_ratio:.2f} ({note})"
                ).strip("; ")
                res.status = "NO_DOI" if not dois else "NEEDS_REVIEW"
        else:
            res.status = "NO_DOI" if not dois else "NEEDS_REVIEW"

    # 3) OpenAlex cross-check (only when we have a confirmed DOI + a date)
    if res.confirmed_doi and res.date:
        oa_date, oa_note = _openalex_by_doi(res.confirmed_doi, mailto=mailto, cache_dir=cache_dir)
        res.openalex_date = oa_date
        if oa_date:
            try:
                cr_d = date.fromisoformat(res.date)
                oa_d = date.fromisoformat(oa_date)
                if abs((oa_d - cr_d).days) > _DATE_CONFLICT_DAYS:
                    res.date_conflict = True
                    res.status = "NEEDS_REVIEW"
                    res.notes = (
                        res.notes + f"; date_conflict crossref={res.date} openalex={oa_date}"
                    ).strip("; ")
            except ValueError:
                pass
        else:
            res.notes = (res.notes + f"; openalex: {oa_note}").strip("; ")

    if not res.date and res.status == "CONFIRMED":
        res.status = "NEEDS_REVIEW"
        res.notes = (res.notes + "; confirmed DOI but no usable date").strip("; ")
    return res


# ---------------------------------------------------------------------------
# Folder driver + sidecar
# ---------------------------------------------------------------------------

_FIELDS = [f.name for f in dataclasses.fields(DateResult)]


def resolve_folder(
    input_folder: Path, out_path: Path, *, mailto: str, cache_dir: Path, limit: int | None = None
) -> list[DateResult]:
    pdfs = sorted(p for p in input_folder.glob("*.pdf"))
    if limit is not None:
        pdfs = pdfs[:limit]
    results = [resolve_one(p, mailto=mailto, cache_dir=cache_dir) for p in pdfs]
    # NEEDS_REVIEW / NO_DOI / confirmed-preprint first, then by filename
    results.sort(key=lambda r: (_sort_tier(r), r.filename))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        for r in results:
            w.writerow(dataclasses.asdict(r))
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("input_folder", type=Path, help="folder of *.pdf")
    ap.add_argument(
        "--out", type=Path, default=None, help="sidecar CSV path (default: <folder>/doi_dates.csv)"
    )
    ap.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="raw-response cache (default: <folder>/.doi_date_cache)",
    )
    ap.add_argument(
        "--mailto", default=_DEFAULT_MAILTO, help="email for the CrossRef/OpenAlex polite pool"
    )
    ap.add_argument("--limit", type=int, default=None, help="process only the first N PDFs")
    args = ap.parse_args(argv)

    folder = args.input_folder
    if not folder.is_dir():
        print(f"ERROR: not a folder: {folder}", file=sys.stderr)
        return 1
    out_path = args.out or (folder / "doi_dates.csv")
    cache_dir = args.cache_dir or (folder / ".doi_date_cache")
    results = resolve_folder(
        folder, out_path, mailto=args.mailto, cache_dir=cache_dir, limit=args.limit
    )

    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    print(f"Wrote {out_path} ({len(results)} papers).")
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
