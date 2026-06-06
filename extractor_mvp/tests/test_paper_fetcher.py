"""PaperFetcher: alias normalization + Tier-1 cache resolution (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from extractor_mvp.paper_fetcher import PaperFetcher

_INDEX = """\
glasser_2013:
  canonical_id: glasser_2013
  aliases:
    - "glasser et al. 2013"
    - "glasser 2013"
    - "glasser, 2013"
    - "glasser et al., 2013"
  local_pdf: citation_cache/glasser_2013.pdf
  source: local
  verified: true
  notes: "HCP minimal preprocessing pipeline paper"
"""


def _cache(tmp_path: Path, *, with_pdf: bool = True) -> Path:
    """Build a self-contained citation_cache under tmp_path; return the cache dir."""
    cache = tmp_path / "citation_cache"
    cache.mkdir()
    (cache / "index.yaml").write_text(_INDEX, encoding="utf-8")
    if with_pdf:
        (cache / "glasser_2013.pdf").write_bytes(b"%PDF-1.4 dummy")
    return cache


def test_init_raises_if_cache_dir_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        PaperFetcher(tmp_path / "does_not_exist")


def test_normalize_collapses_punct_and_whitespace(tmp_path: Path):
    f = PaperFetcher(_cache(tmp_path))
    assert f._normalize("Glasser et al., 2013") == "glasser et al 2013"
    assert f._normalize("Glasser et al. 2013") == "glasser et al 2013"
    assert f._normalize("Glasser, 2013") == "glasser 2013"
    # the three forms the task calls out collapse to the same key
    assert f._normalize("Glasser et al., 2013") == f._normalize("glasser et al 2013")


def test_resolve_alias_variants_hit_same_pdf(tmp_path: Path):
    cache = _cache(tmp_path)
    f = PaperFetcher(cache)
    expected = (cache / "glasser_2013.pdf").resolve()
    assert f.resolve("Glasser et al. 2013") == expected
    assert f.resolve("glasser 2013") == expected
    assert f.resolve("Glasser, 2013") == expected


def test_resolve_unknown_returns_none(tmp_path: Path):
    f = PaperFetcher(_cache(tmp_path))
    assert f.resolve("Completely Unknown Author 2099") is None


def test_resolve_alias_but_missing_pdf_returns_none(tmp_path: Path):
    # index entry exists but the PDF file is absent -> None (Tier 1 needs the file)
    f = PaperFetcher(_cache(tmp_path, with_pdf=False))
    assert f.resolve("Glasser et al. 2013") is None


def test_resolve_is_cached_in_memory(tmp_path: Path):
    f = PaperFetcher(_cache(tmp_path))
    first = f.resolve("Glasser et al. 2013")
    # normalized key is now memoized; second call serves from memory (no index re-read)
    assert f._normalize("Glasser et al. 2013") in f._resolve_cache
    second = f.resolve("Glasser et al. 2013")
    assert first == second


def test_canonical_id_for(tmp_path: Path):
    f = PaperFetcher(_cache(tmp_path))
    assert f.canonical_id_for("Glasser et al., 2013") == "glasser_2013"
    assert f.canonical_id_for("nobody 1999") is None


def test_compound_citation_resolves_first_matching_subcite(tmp_path: Path):
    # LLMs emit combined refs like this; split on ';' and match each part exactly.
    cache = _cache(tmp_path)
    f = PaperFetcher(cache)
    compound = "Marcus et al., 2013; Glasser et al., 2013"  # Marcus not cached, Glasser is
    assert f.canonical_id_for(compound) == "glasser_2013"
    assert f.resolve(compound) == (cache / "glasser_2013.pdf").resolve()
