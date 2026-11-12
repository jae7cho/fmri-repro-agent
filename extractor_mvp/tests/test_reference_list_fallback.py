"""Pre-rerun item 5 (2026-11-11): the reference list when GROBID's listBibl is empty or a text layer
keeps no reference heading. Offline; every entry below is invented."""

from __future__ import annotations

from extractor_mvp.citation_hop import (
    match_reference,
    numbered_run_start,
    parse_reference_list,
    reference_section_start,
    resolve_targets,
)

TEI_EMPTY_LISTBIBL = b"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div><p><s>Data were preprocessed as described
in <ref type="bibr" target="#b46">refs. 47</ref> and <ref type="bibr" target="#b47">48</ref>.</s></p>
</div></body><back><div type="references"><listBibl/></div></back></text></TEI>"""
SENTENCE = "Data were preprocessed as described in refs. 47 and 48."


def _name(i: int) -> str:
    """An invented surname per entry number, letters only (47 -> "Qeh")."""
    return "Q" + "".join(chr(97 + int(d)) for d in str(i))


def _headless(n: int = 49, methods: str = "") -> str:
    """A text layer with a numbered reference list and no heading (a PNAS layout under pypdf)."""
    body = "Methods.\n" + methods + "Results were as follows.\n"
    refs = "".join(f"{i}. {_name(i)} A, et al. (2001) Title {i}.\n" for i in range(1, n + 1))
    return body + refs


def test_with_no_heading_the_longest_numbered_run_is_the_list() -> None:
    text = _headless()
    found = reference_section_start(text)
    assert found is not None and found[1] == "numbered_run"
    assert text[found[0] :].startswith(f"1. {_name(1)}")
    entries = parse_reference_list(text)
    assert [e.number for e in entries] == [str(i) for i in range(1, 50)]
    hits = match_reference("refs. 47 and 48", entries)
    assert [(m.state, m.entry.first_author if m.entry else None) for m in hits] == [
        ("resolved", _name(47)),
        ("resolved", _name(48)),
    ]


def test_a_short_numbered_list_in_the_methods_is_not_the_reference_list() -> None:
    methods = "1. Realign the data.\n2. Smooth them.\n3. Filter them.\n"
    text = _headless(methods=methods)
    start = numbered_run_start(text)
    assert start is not None and text[start:].startswith(f"1. {_name(1)}")
    # with only the short list, nothing qualifies
    assert numbered_run_start("Methods.\n" + methods) is None
    # numbers that are not consecutive (1, 4, 9, ...) are not a run, however many
    gappy = "".join(f"{n}. Item {n}.\n" for n in (1, 4, 9, 20, 33, 40, 51))
    assert numbered_run_start(gappy) is None


def test_a_heading_still_wins() -> None:
    text = (
        "Methods.\n1. A step.\n2. Another.\nReferences\n1. Smith J, et al. (2001) T.\n"
        "2. Doe J, et al. (2002) U.\n"
    )
    found = reference_section_start(text)
    assert found is not None and found[1] == "heading"
    assert [e.first_author for e in parse_reference_list(text)] == ["Smith", "Doe"]


def test_an_empty_listbibl_hands_the_marker_to_the_pypdf_list() -> None:
    matches, how, why = resolve_targets(
        "refs. 47 and 48", _headless(), teis=[("paper", TEI_EMPTY_LISTBIBL)], sentences=[SENTENCE]
    )
    assert how == "marker_text" and why == "target_not_in_bibliography"
    assert [(m.state, m.entry.number if m.entry else None) for m in matches] == [
        ("resolved", "47"),
        ("resolved", "48"),
    ]


def test_the_record_says_where_the_list_came_from() -> None:
    from extractor_mvp.full_report import reference_list_record

    rec = reference_list_record(_headless(), [("paper", TEI_EMPTY_LISTBIBL)])
    assert rec == {
        "grobid_listbibl_entries": 0,
        "grobid_listbibl_empty": True,
        "markers_matched_against": "pypdf",
        "pypdf_entries": 49,
        "pypdf_found_by": "numbered_run",
    }
    assert reference_list_record("no list here", [])["pypdf_found_by"] is None


def test_run_paper_records_it() -> None:
    import inspect

    from extractor_mvp import full_report

    src = inspect.getsource(full_report.run_paper)
    assert 'record["hop_reference_list"] = reference_list_record(reference_text, teis)' in src
