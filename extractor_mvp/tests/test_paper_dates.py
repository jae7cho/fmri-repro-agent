"""The paper's date for the pipeline-defaults block (2026-11-11): CrossRef's issued date, then the
printed accepted / received dates, then the PDF's creation date. No network: CrossRef is faked."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from extractor_mvp import doi_date_resolver, paper_dates


def test_printed_dates_in_the_common_forms() -> None:
    assert paper_dates.parse_printed_date("on 12 March 2016, then") == date(2016, 3, 12)
    assert paper_dates.parse_printed_date("March 30, 2016") == date(2016, 3, 30)
    assert paper_dates.parse_printed_date("2016-12-05") == date(2016, 12, 5)
    assert paper_dates.parse_printed_date("no date here") is None
    text = "Received 4 October 2016; Received in revised form 1 December 2016; Accepted 5 Dec. 2016"
    assert paper_dates.printed_dates(text) == {
        "received": date(2016, 10, 4),
        "accepted": date(2016, 12, 5),
    }


@pytest.fixture
def pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    path = tmp_path / "paper.pdf"
    with path.open("wb") as fh:
        w.write(fh)
    monkeypatch.setattr(
        doi_date_resolver, "_page1_dois", lambda r: ["10.1000/cited", "10.1000/own"]
    )
    monkeypatch.setattr(doi_date_resolver, "_page1_title", lambda r: "A study of synthetic motion")
    return path


def _fake(calls: list[str]) -> Any:
    works = {
        "10.1000/cited": {
            "title": ["Something else entirely"],
            "issued": {"date-parts": [[2001, 5, 1]]},
        },
        "10.1000/own": {
            "title": ["A Study of Synthetic Motion"],
            "issued": {"date-parts": [[2017, 2, 1]]},
        },
    }

    def fetch(doi: str) -> dict[str, Any] | None:
        calls.append(doi)
        return works.get(doi)

    return fetch


def test_crossref_takes_only_the_papers_own_doi_and_caches_no_doi(
    pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(paper_dates, "FETCH", _fake(calls))
    cache = tmp_path / "cache"
    # the cited paper's DOI fails the title match; the paper's own is taken
    assert paper_dates.crossref_issued(pdf, cache_dir=cache) == date(2017, 2, 1)
    names = sorted(p.name for p in cache.iterdir())
    assert names == sorted(
        f"{hashlib.sha256(d.encode()).hexdigest()}.json" for d in ("10.1000/cited", "10.1000/own")
    )
    for p in cache.iterdir():
        text = p.read_text()
        assert "10.1000" not in text and set(json.loads(text)) == {"matched", "issued"}
    # a second lookup reads the cache, no call
    calls.clear()
    assert paper_dates.crossref_issued(pdf, cache_dir=cache) == date(2017, 2, 1)
    assert calls == []


def test_an_unreachable_crossref_is_not_cached(
    pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paper_dates, "FETCH", lambda doi: None)
    cache = tmp_path / "cache"
    assert paper_dates.crossref_issued(pdf, cache_dir=cache) is None
    assert not cache.exists()


def test_the_order_of_preference(pdf: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rec: dict[str, Any] = {"path": str(pdf)}
    monkeypatch.setattr(paper_dates, "crossref_issued", lambda p: date(2017, 2, 1))
    monkeypatch.setattr(
        paper_dates,
        "_front_text",
        lambda p: "Received 4 October 2016; Accepted 5 December 2016",
    )
    assert paper_dates.paper_date(rec) == (date(2017, 2, 1), "CrossRef issued date")
    monkeypatch.setattr(paper_dates, "crossref_issued", lambda p: None)
    assert paper_dates.paper_date(rec) == (date(2016, 12, 5), "the paper's printed accepted date")
    monkeypatch.setattr(paper_dates, "_front_text", lambda p: "Received 4 October 2016")
    assert paper_dates.paper_date(rec) == (date(2016, 10, 4), "the paper's printed received date")
    monkeypatch.setattr(paper_dates, "_front_text", lambda p: "")
    from extractor_mvp import pdf_loader

    monkeypatch.setattr(pdf_loader, "pdf_creation_date", lambda p: date(2018, 1, 1))
    assert paper_dates.paper_date(rec) == (date(2018, 1, 1), "the PDF's creation date")
    monkeypatch.setattr(pdf_loader, "pdf_creation_date", lambda p: None)
    assert paper_dates.paper_date(rec) is None
    assert paper_dates.paper_date({"paper_date": "2015-01-02", "path": str(pdf)}) == (
        date(2015, 1, 2),
        "the paper's stored date",
    )
    assert paper_dates.paper_date({"path": "/no/such.pdf"}) is None
