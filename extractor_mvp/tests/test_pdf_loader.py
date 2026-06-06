"""Tests for the pypdf text-extraction path, using a real (tiny) fixture PDF."""

from __future__ import annotations

from pathlib import Path

from extractor_mvp.pdf_loader import load_pdf_text


def _make_minimal_pdf(text: str) -> bytes:
    """A minimal single-page PDF with one text-showing operator + valid xref."""
    objs: list[bytes] = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"",  # content, filled below
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    stream = b"BT /F1 12 Tf 72 700 Td (%s) Tj ET" % text.encode()
    objs[3] = b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream)

    pdf = b"%PDF-1.4\n"
    offsets: list[int] = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj" % i + obj + b"endobj\n"
    xref_off = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        pdf += b"%010d 00000 n \n" % off
    pdf += b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref_off)
    return pdf


def test_load_pdf_text_extracts_nonempty(tmp_path: Path):
    p = tmp_path / "mini.pdf"
    p.write_bytes(_make_minimal_pdf("Methods preprocessing MNI152NLin6Asym"))
    text, parser = load_pdf_text(p)
    assert parser == "pypdf"
    assert text.strip()
    assert "Methods" in text


def test_load_pdf_text_failure_on_non_pdf(tmp_path: Path):
    p = tmp_path / "not_a.pdf"
    p.write_text("this is not a pdf", encoding="utf-8")
    text, parser = load_pdf_text(p)
    assert parser == "failed"
    assert text == ""
