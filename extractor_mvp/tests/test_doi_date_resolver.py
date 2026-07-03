"""Offline tests for the standalone doi_date_resolver tool.

No network, no real PDF: pure helpers are tested directly; PDF reading is faked and
HTTP is served from a pre-populated on-disk cache (the tool's real idempotency path).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from extractor_mvp import doi_date_resolver as dd

_DOI = "10.5555/test.abc123"
_TITLE = "Individual Variability and Test Retest Reliability of Brain Scans"


# --- pure helpers ----------------------------------------------------------


def test_clean_doi_strips_punct_and_doi_suffix():
    assert dd._clean_doi("10.1371/journal.pone.0144963.") == "10.1371/journal.pone.0144963"
    assert dd._clean_doi("10.1234/abc)]") == "10.1234/abc"
    assert dd._clean_doi("10.1234/abcdoi") == "10.1234/abc"


def test_title_ratio_normalizes_and_scores():
    assert dd._title_ratio("The Same Title!", "the same title") == 1.0
    assert dd._title_ratio("alpha beta gamma delta", "wholly unrelated phrasing here") < 0.6
    assert dd._title_ratio("", "x") == 0.0


def test_looks_like_real_title_rejects_junk():
    assert dd._looks_like_real_title("A Real Paper Title About Brains")
    assert not dd._looks_like_real_title("Microsoft Word - draft2.docx")
    assert not dd._looks_like_real_title("manuscript.pdf")
    assert not dd._looks_like_real_title("onetoken")
    assert not dd._looks_like_real_title("short")


def test_date_parts_to_date_full_partial_invalid():
    assert dd._date_parts_to_date({"date-parts": [[2015, 12, 29]]}) == date(2015, 12, 29)
    assert dd._date_parts_to_date({"date-parts": [[2015]]}) == date(2015, 1, 1)
    assert dd._date_parts_to_date({"date-parts": [[2015, 6]]}) == date(2015, 6, 1)
    assert dd._date_parts_to_date(None) is None
    assert dd._date_parts_to_date({"date-parts": [[2015, 13, 1]]}) is None  # bad month


def test_pick_earliest_date_prefers_earliest_and_labels():
    msg = {
        "published-online": {"date-parts": [[2016, 3, 1]]},
        "published-print": {"date-parts": [[2016, 10, 1]]},
        "issued": {"date-parts": [[2016, 10, 1]]},
    }
    assert dd._pick_earliest_date(msg) == (date(2016, 3, 1), "online")
    assert dd._pick_earliest_date({}) == (None, "")


def test_crossref_title_handles_list_and_empty():
    assert dd._crossref_title({"title": ["Hello World"]}) == "Hello World"
    assert dd._crossref_title({"title": []}) == ""


def test_http_json_cache_hit_no_network(tmp_path: Path):
    (tmp_path / "k.json").write_text('{"a": 1}')
    data, note = dd._http_json(
        "http://unused.invalid", mailto="t@e.com", cache_dir=tmp_path, cache_name="k.json"
    )
    assert data == {"a": 1} and note == "cache"


# --- faked PDF reading -----------------------------------------------------


class _FakePage:
    def __init__(self, text: str) -> None:
        self._t = text

    def extract_text(self) -> str:
        return self._t


class _FakeReader:
    def __init__(self, text: str = "", metadata: dict[str, Any] | None = None) -> None:
        self.pages = [_FakePage(text)]
        self.metadata = metadata


def test_page1_dois_and_title_from_fake_reader():
    r = _FakeReader(f"Some Header\n{_DOI}\nmore text")
    assert _DOI in dd._page1_dois(r)
    r2 = _FakeReader("body text", metadata={"/Title": "A Proper Paper Title Here"})
    assert dd._page1_title(r2) == "A Proper Paper Title Here"


# --- resolve_one / resolve_folder / main via cache + faked reader ----------


def _write_cache(cache_dir: Path, name: str, obj: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / name).write_text(json.dumps(obj))


def _fake_pdf(monkeypatch, text: str, title: str | None) -> None:
    meta = {"/Title": title} if title else {}
    monkeypatch.setattr(dd, "PdfReader", lambda _p: _FakeReader(text, metadata=meta))


def test_resolve_one_confirmed_via_doi(tmp_path: Path, monkeypatch):
    _fake_pdf(monkeypatch, f"{_TITLE}\n{_DOI}\n", _TITLE)
    cache = tmp_path / "cache"
    _write_cache(
        cache,
        dd._cache_key("crossref_doi", _DOI),
        {
            "message": {
                "title": [_TITLE],
                "issued": {"date-parts": [[2015, 12, 29]]},
                "published-online": {"date-parts": [[2015, 12, 29]]},
            }
        },
    )
    _write_cache(cache, dd._cache_key("openalex_doi", _DOI), {"publication_date": "2015-12-29"})
    res = dd.resolve_one(tmp_path / "p.pdf", mailto="t@e.com", cache_dir=cache)
    assert res.status == "CONFIRMED"
    assert res.confirmed_doi == _DOI
    assert res.date == "2015-12-29" and res.date_field == "online"
    assert res.date_source == "crossref"
    assert res.openalex_date == "2015-12-29" and res.date_conflict is False


def test_resolve_one_date_conflict_flags_review(tmp_path: Path, monkeypatch):
    _fake_pdf(monkeypatch, f"{_TITLE}\n{_DOI}\n", _TITLE)
    cache = tmp_path / "cache"
    _write_cache(
        cache,
        dd._cache_key("crossref_doi", _DOI),
        {"message": {"title": [_TITLE], "issued": {"date-parts": [[2016, 1, 1]]}}},
    )
    _write_cache(cache, dd._cache_key("openalex_doi", _DOI), {"publication_date": "2018-06-01"})
    res = dd.resolve_one(tmp_path / "p.pdf", mailto="t@e.com", cache_dir=cache)
    assert res.date_conflict is True and res.status == "NEEDS_REVIEW"


def test_resolve_one_title_search_fallback(tmp_path: Path, monkeypatch):
    # DOI's CrossRef title does NOT match the PDF title -> fall back to title search.
    _fake_pdf(monkeypatch, f"{_TITLE}\n{_DOI}\n", _TITLE)
    cache = tmp_path / "cache"
    _write_cache(
        cache,
        dd._cache_key("crossref_doi", _DOI),
        {
            "message": {
                "title": ["A Totally Different Cited Paper"],
                "issued": {"date-parts": [[2010, 1, 1]]},
            }
        },
    )
    _write_cache(
        cache,
        dd._cache_key("crossref_query", _TITLE),
        {
            "message": {
                "items": [
                    {
                        "DOI": "10.9999/real",
                        "title": [_TITLE],
                        "issued": {"date-parts": [[2015, 5, 1]]},
                    }
                ]
            }
        },
    )
    _write_cache(
        cache, dd._cache_key("openalex_doi", "10.9999/real"), {"publication_date": "2015-05-01"}
    )
    res = dd.resolve_one(tmp_path / "p.pdf", mailto="t@e.com", cache_dir=cache)
    assert res.status == "CONFIRMED"
    assert res.confirmed_doi == "10.9999/real"
    assert res.date_source == "title-search" and res.date == "2015-05-01"


def test_resolve_one_preprint_flags_and_finds_vor(tmp_path: Path, monkeypatch):
    # Confirmed DOI is a preprint (posted-content). Keep the preprint date, but flag
    # is_preprint and record the journal-article version of record found via title search.
    _fake_pdf(monkeypatch, f"{_TITLE}\n{_DOI}\n", _TITLE)
    cache = tmp_path / "cache"
    _write_cache(
        cache,
        dd._cache_key("crossref_doi", _DOI),
        {
            "message": {
                "type": "posted-content",
                "subtype": "preprint",
                "title": [_TITLE],
                "issued": {"date-parts": [[2016, 11, 2]]},
            }
        },
    )
    _write_cache(
        cache,
        dd._cache_key("crossref_query", _TITLE),
        {
            "message": {
                "items": [
                    {  # the preprint itself — must be skipped
                        "type": "posted-content",
                        "DOI": _DOI,
                        "title": [_TITLE],
                        "issued": {"date-parts": [[2016, 11, 2]]},
                    },
                    {  # the version of record
                        "type": "journal-article",
                        "DOI": "10.1016/j.neuroimage.2017.06.027",
                        "title": [_TITLE],
                        "issued": {"date-parts": [[2017, 6, 27]]},
                    },
                ]
            }
        },
    )
    _write_cache(cache, dd._cache_key("openalex_doi", _DOI), {"publication_date": "2016-11-02"})
    res = dd.resolve_one(tmp_path / "p.pdf", mailto="t@e.com", cache_dir=cache)
    assert res.status == "CONFIRMED"
    assert res.is_preprint is True
    assert res.date == "2016-11-02"  # preprint date KEPT (conservative bound)
    assert res.version_of_record_doi == "10.1016/j.neuroimage.2017.06.027"
    assert "kept preprint date" in res.notes


def test_resolve_one_no_doi(tmp_path: Path, monkeypatch):
    _fake_pdf(monkeypatch, "Header line\nno identifier here\n", "Header line")
    cache = tmp_path / "cache"
    _write_cache(cache, dd._cache_key("crossref_query", "Header line"), {"message": {"items": []}})
    res = dd.resolve_one(tmp_path / "p.pdf", mailto="t@e.com", cache_dir=cache)
    assert res.status == "NO_DOI"
    assert res.primary_doi_extracted == "" and res.confirmed_doi == ""


def test_resolve_folder_writes_sorted_sidecar_and_main(tmp_path: Path, monkeypatch):
    _fake_pdf(monkeypatch, f"{_TITLE}\n{_DOI}\n", _TITLE)
    (tmp_path / "paper.pdf").write_bytes(b"%PDF-1.4")  # exists for glob; PdfReader is faked
    cache = tmp_path / "cache"
    _write_cache(
        cache,
        dd._cache_key("crossref_doi", _DOI),
        {"message": {"title": [_TITLE], "issued": {"date-parts": [[2020, 1, 1]]}}},
    )
    _write_cache(cache, dd._cache_key("openalex_doi", _DOI), {"publication_date": "2020-01-01"})
    out = tmp_path / "sidecar.csv"
    results = dd.resolve_folder(tmp_path, out, mailto="t@e.com", cache_dir=cache)
    assert out.exists() and len(results) == 1 and results[0].status == "CONFIRMED"
    header = out.read_text().splitlines()[0]
    assert header.startswith("filename,")
    assert (
        dd.main([str(tmp_path), "--out", str(tmp_path / "m.csv"), "--cache-dir", str(cache)]) == 0
    )
