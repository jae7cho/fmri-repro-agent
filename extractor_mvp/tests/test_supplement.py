"""Fix 4 (the author's list of 2026-11-05): "see Supplementary Material" is not a citation. A
<stem>_supp.pdf beside the paper is read with it; otherwise the fields it holds render "in this
paper's supplement, not read". Offline: the PDF loader and the model are stubbed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import extractor_mvp.batch as batch
from conftest import FULL_TEXT, _canned_payload, stub_client
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import extract

SUPP = "Supplementary methods. Data were normalized to MNI152NLin6Asym at 2 mm. " + (
    "The scanner room was kept at a constant temperature throughout. " * 10
)


def _setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, supp: str | None) -> dict[str, Any]:
    pdf = tmp_path / "p_2020.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    if supp is not None:
        (tmp_path / "p_2020_supp.pdf").write_bytes(b"%PDF-1.4\n")
    texts = {pdf.name: FULL_TEXT, "p_2020_supp.pdf": supp or ""}

    def load(p: Path) -> tuple[str, str]:
        t = texts[Path(p).name]
        return (t, "pypdf") if t else ("", "failed")

    monkeypatch.setattr(batch, "load_pdf_text", load)
    seen: dict[str, Any] = {"pdf": pdf}

    def fake_extract(paper: Any, model: str, **kw: Any) -> Any:
        seen["text"] = paper.text
        seen["verifier_text"] = kw.get("verifier_text")
        payload = _canned_payload()
        if supp:  # a value whose quote sits in the supplement
            payload.target_space = FieldExtractionResult(
                status="extracted",
                value="MNI152NLin6Asym",
                verbatim_quote="Supplementary methods. Data were normalized to MNI152NLin6Asym",
            )
        return extract(paper, model, client=stub_client(payload))

    monkeypatch.setattr(batch, "extract", fake_extract)
    return seen


def test_a_supplement_beside_the_paper_is_read_with_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, SUPP)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    assert "[Supplementary material, read with the paper: p_2020_supp.pdf]" in seen["text"]
    assert seen["text"].endswith(SUPP)
    sup = r.extraction_json["supplement"]  # type: ignore[index]
    assert sup["present"] and sup["read"] and sup["n_chars"] == len(SUPP)
    assert sup["start_in_extraction_text"] == seen["text"].index(SUPP)
    assert "Supplement: p_2020_supp.pdf, read whole with the paper (712 characters; no heading" in (
        r.report or ""
    )


def test_a_record_from_before_supplements_were_sliced_renders_as_it_did() -> None:
    from extractor_mvp.render import _supplement_line

    old = {"path": "x/p_2020_supp.pdf", "present": True, "read": True, "n_chars": 712}
    assert _supplement_line(old) == (
        "Supplement: p_2020_supp.pdf, read with the paper (712 characters)."
    )


def test_a_span_in_the_supplement_gets_supplement_offsets_not_full_paper_ones(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, SUPP)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    spans = [
        sp
        for step in r.extraction_json["preprocessing"]["steps"]  # type: ignore[index]
        for v in step.values()
        if isinstance(v, dict) and isinstance(v.get("extraction"), dict)
        for sp in v["extraction"].get("spans", [])
    ]
    in_supp = [sp for sp in spans if "span_in_supplement" in sp]
    assert in_supp and all("span_in_full_paper" not in sp for sp in in_supp)
    assert in_supp[0]["span_in_supplement"]["start"] == 0


def test_no_supplement_and_an_unreadable_one_are_said(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, None)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    assert r.extraction_json["supplement"]["present"] is False  # type: ignore[index]
    assert "Supplement: none found beside the paper" in (r.report or "")
    assert "[Supplementary material" not in seen["text"]
    seen = _setup(monkeypatch, tmp_path, "x" * 313)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    sup = r.extraction_json["supplement"]  # type: ignore[index]
    assert sup["present"] and not sup["read"] and "313 characters" in sup["reason"]
    assert "found beside the paper, not read (no usable text layer" in (r.report or "")


def test_a_suspicious_slice_sends_the_supplement_to_the_checking_pass_too(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, SUPP)
    no_header = "Nothing here is a heading.\n" + FULL_TEXT.replace("Methods\n", "")
    real_load = batch.load_pdf_text
    monkeypatch.setattr(
        batch,
        "load_pdf_text",
        lambda p: (no_header, "pypdf") if Path(p).name == "p_2020.pdf" else real_load(p),
    )
    batch.process_paper("p_2020", seen["pdf"], "m")
    assert seen["verifier_text"].startswith(no_header) and seen["verifier_text"].endswith(SUPP)


def _deferred_to_supplement_report(read: bool) -> str:
    import sys

    from fmri_repro.spec.preprocessing import Coregistration

    from extractor_mvp.render import to_report

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests" / "kb_client"))
    from test_deferred_defaults import _prep, _version_extracted

    prep = _prep("fMRIPrep", _version_extracted("20.2.0"), "Supplementary Material")
    assert isinstance(prep.steps[0], Coregistration)
    sup = {
        "path": "/x/p_2020_supp.pdf",
        "present": read,
        "read": read,
        "n_chars": 900 if read else 0,
        "reason": None if read else "no supplement beside the paper",
        "fields_deferred": ["coregistration.method"],
    }
    return to_report(prep, source="t", supplement=sup)


def test_a_field_sent_to_the_supplement_says_so_never_a_citation() -> None:
    out = _deferred_to_supplement_report(read=False)
    line = next(ln for ln in out.splitlines() if ln.startswith("- method:"))
    assert line == "- method: in this paper's supplement, not read"
    assert "method: in this paper's supplement, not read" in next(
        ln for ln in out.splitlines() if ln.startswith("- Function-structure")
    )
    read = _deferred_to_supplement_report(read=True)
    assert "- method: in this paper's supplement, read with the paper; no value was taken" in read
    # a field deferred elsewhere keeps its own wording
    assert "- transform: deferred to Supplementary Material — resolve by consulting" in out


def test_process_paper_records_and_renders_a_field_sent_to_the_supplement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, None)

    def fake_extract(paper: Any, model: str, **kw: Any) -> Any:
        payload = _canned_payload()
        payload.resolution_mm = FieldExtractionResult(
            status="deferred",
            deferral_sentence="Data were normalized to MNI152NLin6Asym at 2 mm.",
            ref_string="Supplementary Material",
            target_kind="supplement",
        )
        return extract(paper, model, client=stub_client(payload))

    monkeypatch.setattr(batch, "extract", fake_extract)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    sup = r.extraction_json["supplement"]  # type: ignore[index]
    assert sup["fields_deferred"] == ["spatial_normalization.resolution_mm"]
    assert "- resolution_mm: in this paper's supplement, not read" in (r.report or "")


# --- 2026-11-05 (second round, item 2): the reference list is out of the extraction text ----------

REFS = "\nReferences\nSmith, A., 2004. Advances in FSL. NeuroImage 23, 1.\n"


def test_a_full_text_fallback_reads_no_reference_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, None)
    paper = "Nothing here is a heading.\n" + FULL_TEXT.replace("Methods\n", "") + REFS
    monkeypatch.setattr(batch, "load_pdf_text", lambda p: (paper, "pypdf"))
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    assert r.status == "methods_not_found"
    assert "Advances in FSL" not in seen["text"] and "Advances in FSL" not in seen["verifier_text"]
    assert r.extraction_json["references_excluded_from"] == paper.index("\nReferences") + 1  # type: ignore[index]


def test_a_supplement_s_reference_list_is_not_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, SUPP + REFS)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    assert seen["text"].endswith(SUPP + "\n") or seen["text"].endswith(SUPP)
    assert "Advances in FSL" not in seen["text"]
    sup = r.extraction_json["supplement"]  # type: ignore[index]
    assert sup["references_excluded_from"] == len(SUPP) + 1


def test_a_header_slice_before_the_references_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = _setup(monkeypatch, tmp_path, None)
    monkeypatch.setattr(batch, "load_pdf_text", lambda p: (FULL_TEXT + REFS, "pypdf"))
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    assert r.status == "success" and r.extraction_json["references_excluded_from"] is None  # type: ignore[index]


def test_a_supplement_repeating_the_paper_leaves_no_quote_ambiguous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # the author's list of 2026-11-05, third round, item 2 (Bakker_2012: 6 quotes ambiguous in v2)
    alone = batch.process_paper("p_2020", _setup(monkeypatch, tmp_path, None)["pdf"], "m")
    seen = _setup(monkeypatch, tmp_path, FULL_TEXT + "\n" + SUPP)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    diags = r.extraction_json["diagnostics"]  # type: ignore[index]
    assert not [d for d in diags if "quote_ambiguous" in (d.get("failure_reason") or "")]
    assert r.n_extracted >= alone.n_extracted
    prep = r.extraction_json["preprocessing"]  # type: ignore[index]
    spans = [
        sp
        for st in prep["steps"]
        for f in st.values()
        if isinstance(f, dict)
        for sp in (f.get("extraction") or {}).get("spans") or []
    ]
    in_paper = [sp for sp in spans if sp["text"] in FULL_TEXT]
    assert in_paper and all("span_in_full_paper" in sp for sp in in_paper)


SUPP_WITH_MRI = (
    "Supplementary Tables\nTable S1. Demographics\n"
    + "Age and sex of each group are listed here for the record of the study.\n" * 8
    + "fMRI acquisition\nSupplementary methods. Data were normalized to MNI152NLin6Asym at 2 mm. "
    + "The scanner room was kept at a constant temperature throughout. " * 10
    + "\nSupplementary Results\n"
    + "Effects were seen in every region examined and in both hemispheres.\n" * 8
)


def test_only_the_supplements_mri_sections_are_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # the author's list of 2026-11-05, third round, item 1
    seen = _setup(monkeypatch, tmp_path, SUPP_WITH_MRI)
    r = batch.process_paper("p_2020", seen["pdf"], "m")
    start = SUPP_WITH_MRI.index("fMRI acquisition")
    end = SUPP_WITH_MRI.index("Supplementary Results")
    assert seen["text"].endswith(SUPP_WITH_MRI[start:end])
    assert "Demographics" not in seen["text"] and "Effects were seen" not in seen["text"]
    sup = r.extraction_json["supplement"]  # type: ignore[index]
    assert sup["n_chars"] == len(SUPP_WITH_MRI) and sup["n_chars_read"] == end - start
    assert sup["slice"]["matched_header"] == "fMRI acquisition"
    prep = r.extraction_json["preprocessing"]  # type: ignore[index]
    spans = [
        sp
        for st in prep["steps"]
        for f in st.values()
        if isinstance(f, dict)
        for sp in (f.get("extraction") or {}).get("spans") or []
        if "span_in_supplement" in sp
    ]
    assert spans
    for sp in spans:  # offsets into the supplement's own text, not into the slice
        o = sp["span_in_supplement"]
        assert SUPP_WITH_MRI[o["start"] : o["end"]] == sp["text"]
    assert "its MRI sections read with the paper (from 'fMRI acquisition'" in (r.report or "")
