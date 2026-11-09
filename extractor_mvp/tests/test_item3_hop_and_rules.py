"""2026-11-09, the author's items 2 and 3: the step-wide hop, the Europe PMC fallback, the CrossRef DOI
lookup, provider-applied marking, and the shared prompt rules. Synthetic inputs; no model call, no
network (fetches are stubbed)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from extractor_mvp.citation_hop import (
    crossref_doi,
    europepmc_cache_name,
    europepmc_fulltext,
    hop_scope,
    jats_text,
    step_citations,
)
from extractor_mvp.provider_applied import provider_applied
from test_motion_inference import _method, _prep

TEI = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div>
<p>Data were collected at two sites. Head motion was corrected with the standard preprocessing
pipeline <ref type="bibr" target="#b2">[2]</ref>. Head motion affects connectivity
<ref type="bibr" target="#b5">[5]</ref>. Images were smoothed as described
<ref type="bibr" target="#b7">[7]</ref>.</p></div></body></text></TEI>"""


def test_step_citations_follow_every_cited_sentence_on_the_step_with_a_deferral_cue() -> None:
    out = step_citations([("paper", TEI)], ["motion_correction"])
    assert [(label, kind, marker) for label, kind, marker, _s in out] == [
        ("paper", "motion_correction", "[2]")
    ]
    assert out[0][3].startswith("Head motion was corrected with the standard preprocessing")
    smooth = step_citations([("supplement", TEI)], ["spatial_smoothing"])
    assert [(x[0], x[2]) for x in smooth] == [("supplement", "[7]")]
    assert step_citations([("paper", b"not xml")], ["motion_correction"]) == []


def test_a_step_wide_citation_asks_the_steps_deferred_fields() -> None:
    prep = _prep(_method("deferred", ref="[3,][4]"), None)
    plain = hop_scope(prep, "[2]")
    assert not any(t["field"] == "motion_correction.method" for t in plain["tools"])
    wide = hop_scope(prep, "[2]", step_fields=["motion_correction.method"])
    assert any(t["field"] == "motion_correction.method" for t in wide["tools"])


JATS = b"""<article><front/><body>
<sec><title>Results</title><p>Synthetic results.</p></sec>
<sec><title>Methods</title><sec><title>Preprocessing</title>
<p>Processing was based on a synthetic pipeline.</p></sec></sec></body></article>"""


def test_jats_text_keeps_section_titles_on_their_own_lines() -> None:
    assert jats_text(JATS).splitlines() == [
        "Results",
        "Synthetic results.",
        "Methods",
        "Preprocessing",
        "Processing was based on a synthetic pipeline.",
    ]


def test_europepmc_fetches_once_caches_beside_the_paper_and_reads_the_cache(tmp_path: Path) -> None:
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        if "/search?" in url:
            return json.dumps({"resultList": {"result": [{"pmcid": "PMC1"}]}}).encode()
        assert url.endswith("/PMC1/fullTextXML")
        return JATS

    doi = "10.9999/synthetic.1"
    text, path, sha = europepmc_fulltext(doi, tmp_path, fetch=fetch)  # type: ignore[misc]
    assert "Processing was based on a synthetic pipeline." in text
    assert path == tmp_path / europepmc_cache_name(doi) and path.read_bytes() == JATS
    assert len(sha) == 64 and len(calls) == 2
    again = europepmc_fulltext(
        doi, tmp_path, fetch=lambda url: (_ for _ in ()).throw(AssertionError)
    )
    assert again is not None and again[0] == text  # read from the cache, no fetch
    none = europepmc_fulltext(
        "10.9999/none", tmp_path, fetch=lambda url: b'{"resultList": {"result": []}}'
    )
    assert none is None


def test_crossref_doi_is_accepted_only_on_author_year_and_title() -> None:
    entry = SimpleNamespace(
        text="Synthetic, A. (2019) A synthetic title about hierarchies. J Synth 1:2",
        first_author="Synthetic",
        year="2019",
    )

    def hit(family: str, year: int, title: str) -> Any:
        body = {
            "message": {
                "items": [
                    {
                        "DOI": "10.9999/X",
                        "title": [title],
                        "author": [{"family": family}],
                        "issued": {"date-parts": [[year]]},
                    }
                ]
            }
        }
        return lambda url: json.dumps(body).encode()

    assert (
        crossref_doi(entry, fetch=hit("Synthetic", 2019, "A synthetic title about hierarchies"))
        == "10.9999/x"
    )
    assert (
        crossref_doi(entry, fetch=hit("Other", 2019, "A synthetic title about hierarchies")) is None
    )
    assert (
        crossref_doi(entry, fetch=hit("Synthetic", 2018, "A synthetic title about hierarchies"))
        is None
    )
    assert crossref_doi(entry, fetch=hit("Synthetic", 2019, "A different title")) is None


def _pf(quote: str) -> dict[str, Any]:
    return {
        "extraction": {"status": "EXTRACTED", "value": "x", "spans": [{"text": quote}]},
        "inference": {"status": "NOT_APPLICABLE"},
    }


def test_provider_applied_marks_fields_quoted_from_the_release() -> None:
    record = {
        "data_release": {
            "releases": [{"dataset": "Synthetic Imaging Study (SIS)", "release": "2.0"}]
        },
        "preprocessing": {
            "steps": [
                {
                    "kind": "spatial_normalization",
                    "target_space": _pf("Minimally preprocessed SIS data were used."),
                },
                {"kind": "spatial_smoothing", "fwhm_mm": _pf("SIS data were smoothed at 6 mm.")},
                {"kind": "temporal_filtering", "pass_type": _pf("We filtered the data ourselves.")},
            ]
        },
    }
    out = provider_applied(record)
    assert out == {
        "spatial_normalization.target_space": {
            "applied_by": "data_provider",
            "release": "Synthetic Imaging Study (SIS) 2.0",
        }
    }


def test_the_rules_are_in_every_extraction_prompt_and_the_checking_pass_not_the_frozen_stanza() -> (
    None
):
    from extractor_mvp.coverage_extractor import SPATIAL_PROMPT, TEMPORAL_VOLUME_PROMPT
    from extractor_mvp.extractor import (
        EXTRACTION_PROMPT,
        MOTION_METHOD_PROMPT,
        PER_ACQUISITION_EXTRACTION_PROMPT,
    )
    from extractor_mvp.prompt_rules import CHECKING_RULES, PREPROCESSING_RULES
    from extractor_mvp.verifier import VERIFIER_PROMPT

    for p in (
        EXTRACTION_PROMPT,
        PER_ACQUISITION_EXTRACTION_PROMPT,
        SPATIAL_PROMPT,
        TEMPORAL_VOLUME_PROMPT,
    ):
        assert PREPROCESSING_RULES in p
    assert CHECKING_RULES in VERIFIER_PROMPT
    for line in (
        "is motion correction, not coregistration",
        "is reported as applied",
        "is not spatial smoothing",
        "is not applied unless the paper says it was regressed out",
    ):
        assert line in PREPROCESSING_RULES.replace("\n  ", " ") and line in CHECKING_RULES.replace(
            "\n  ", " "
        )
    assert PREPROCESSING_RULES not in MOTION_METHOD_PROMPT  # the pre-registered stanza stays frozen


def test_the_pseudocode_shows_a_provider_applied_step() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_pc", Path(__file__).with_name("test_pseudocode.py")
    )
    assert spec and spec.loader
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    from extractor_mvp.pseudocode import render_pseudocode

    rec = pc._record()
    rec["applied_by"] = {
        "spatial_smoothing.kernel_type": {"applied_by": "data_provider", "release": "SIS 2.0"}
    }
    code = render_pseudocode(rec)
    assert code is not None
    line = pc._line(code, "spatial_smoothing")
    assert line.startswith(
        'spatial_smoothing(applied_by="data_provider" [E], release="SIS 2.0" [E],'
    )
