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


# --- reflow of a one-word-per-line text layer (the author's list of 2026-11-05, third round, 4) ---

from extractor_mvp.pdf_loader import reflow_one_word_lines  # noqa: E402

_PROSE = (
    "Methods\n"
    "Functional images were realigned to the first volume and smoothed\n"
    "with a 6 mm kernel before any further analysis was run.\n"
    "\n"
    "Results\n"
    "The main effect of condition was seen in both hemispheres.\n"
)


def _one_word_layer(text: str, *, repeat: int = 8) -> str:
    """The layer pypdf writes for such a PDF: a word per line, a word that continues the printed
    line carries a leading space, and a whitespace-only line stands for a blank one."""
    out: list[str] = []
    for ln in (text * repeat).splitlines():
        words = ln.split()
        if not words:
            out.append(" ")
            continue
        out.append(words[0])
        out.extend(" " + w for w in words[1:])
    return "\n".join(out)


def test_a_one_word_layer_gets_its_printed_lines_back() -> None:
    layer = _one_word_layer(_PROSE)
    text, info = reflow_one_word_lines(layer)
    assert text.splitlines()[:4] == [ln for ln in _PROSE.splitlines() if ln][:4]
    assert info is not None and info["one_word_share_before"] > 0.8
    assert info["lines_after"] == len([ln for ln in (_PROSE * 8).splitlines() if ln])
    assert info["one_word_share_after"] < 0.8


def test_reflow_changes_nothing_but_line_breaks() -> None:
    layer = _one_word_layer(_PROSE)
    text, _ = reflow_one_word_lines(layer)
    assert "".join(text.split()) == "".join(layer.split())
    # every character of the reflowed text, line breaks aside, is the layer's, in order
    kept = iter(layer)
    assert all(any(c == k for k in kept) for c in text.replace("\n", ""))


def test_ordinary_text_is_not_reflowed() -> None:
    ordinary = _PROSE * 20
    assert reflow_one_word_lines(ordinary) == (ordinary, None)


def test_a_short_one_word_text_is_not_reflowed() -> None:
    short = "\n".join(["word"] * 49)
    assert reflow_one_word_lines(short) == (short, None)
    assert reflow_one_word_lines("\n".join(["word"] * 50))[1] is not None


def test_a_whitespace_only_line_ends_the_line_even_before_a_leading_space() -> None:
    # Cattarinussi_2026's layer has 383 whitespace-only lines; 6 are followed by a word that carries
    # a leading space, and the block still ends there
    layer = _one_word_layer(_PROSE) + "\n \n Table\n 1"
    text, _ = reflow_one_word_lines(layer)
    assert text.splitlines()[-1] == " Table 1"
