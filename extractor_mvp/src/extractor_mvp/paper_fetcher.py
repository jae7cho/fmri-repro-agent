"""Four-tier paper fetcher for citation resolution.

Resolution order per canonical_id:
  Tier 1: citation_cache/ local PDF (index.yaml lookup, alias-normalized)
  Tier 2: user-supplied PDF (same directory, detected by presence)
  Tier 3: PMC E-utilities fetch (free, no auth; doi -> PMC ID -> PDF URL)
  Tier 4: Unpaywall (DOI -> open-access PDF URL)
  Failure: returns None; caller emits LeftMissing

MVP: Tier 1 and Tier 2 fully implemented.
     Tier 3 and Tier 4 are stubs that log a warning and return None.
     Full network fetch is Part B extension, not MVP.

Alias normalization: lowercase, strip punctuation, collapse whitespace.
No fuzzy matching -- exact match after normalization only (discipline rule).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# punctuation stripped during normalization: . , ( ) [ ]
_PUNCT_RE = re.compile(r"[.,()\[\]]")
_WS_RE = re.compile(r"\s+")
# compound citations like "Marcus et al., 2013; Glasser et al., 2013" are split on
# ';' into individual refs. This is tokenization, NOT fuzzy matching — each part is
# still matched exactly after normalization. (Only ';'; never " and "/"," which
# appear *within* a single citation's author list.)
_SPLIT_RE = re.compile(r"\s*;\s*")


class PaperFetcher:
    """Resolve a citation ref_string to a local PDF path via a cached index.

    The index (``index.yaml``) is read once at construction; ``resolve`` is then
    a pure in-memory lookup (Tier 1) plus a directory scan (Tier 2).
    """

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        if not self.cache_dir.is_dir():
            raise FileNotFoundError(f"citation cache dir not found: {self.cache_dir}")
        # extractor_mvp/ root — index local_pdf paths are relative to it.
        self._project_root = self.cache_dir.parent

        index_path = self.cache_dir / "index.yaml"
        self._index: dict[str, dict] = {}
        if index_path.is_file():
            loaded = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            if loaded:
                self._index = loaded
        else:
            logger.warning("no index.yaml in %s; Tier 1 disabled", self.cache_dir)

        # normalized alias -> canonical_id (built once; resolve never re-reads disk for this)
        self._alias_map: dict[str, str] = {}
        for canonical_id, entry in self._index.items():
            self._alias_map[self._normalize(canonical_id)] = canonical_id
            for alias in entry.get("aliases", []):
                self._alias_map[self._normalize(alias)] = canonical_id

        # in-memory resolve cache: normalized ref -> Path | None
        self._resolve_cache: dict[str, Path | None] = {}

    def _normalize(self, s: str) -> str:
        """lowercase, strip .,()[], collapse whitespace."""
        return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", s.lower())).strip()

    def _candidates(self, ref_string: str) -> list[str]:
        """Normalized lookup keys: the whole ref first, then each ';'-split part."""
        whole = self._normalize(ref_string)
        cands = [whole]
        for part in _SPLIT_RE.split(ref_string):
            n = self._normalize(part)
            if n and n not in cands:
                cands.append(n)
        return cands

    def canonical_id_for(self, ref_string: str) -> str | None:
        """Canonical id for a ref_string (Tier 1 index, else Tier 2 filename), or None.

        For a compound citation, the first sub-citation that resolves wins.
        """
        for cand in self._candidates(ref_string):
            if cand in self._alias_map:
                return self._alias_map[cand]
        for cand in self._candidates(ref_string):
            stem = self._tier2_stem(cand)
            if stem is not None:
                return stem
        return None

    def resolve(self, ref_string: str) -> Path | None:
        """Return the local PDF path for ``ref_string`` or None.

        Tier 1: index alias lookup -> local_pdf. Tier 2: a PDF in cache_dir whose
        normalized filename stem equals the normalized ref. Tiers 3/4 are stubs.
        """
        norm = self._normalize(ref_string)
        if norm in self._resolve_cache:
            return self._resolve_cache[norm]

        path: Path | None = None
        for cand in self._candidates(ref_string):
            path = self._resolve_tier1(cand) or self._resolve_tier2(cand)
            if path is not None:
                break
        if path is None:
            # Tier 3/4 stubs: not implemented in the MVP.
            logger.warning(
                "no local PDF for %r; network tiers (PMC/Unpaywall) are MVP stubs -> None",
                ref_string,
            )
        self._resolve_cache[norm] = path
        return path

    # --- tiers ---------------------------------------------------------------
    def _resolve_tier1(self, norm: str) -> Path | None:
        canonical_id = self._alias_map.get(norm)
        if canonical_id is None:
            return None
        local_pdf = self._index[canonical_id].get("local_pdf")
        if not local_pdf:
            return None
        path = (self._project_root / str(local_pdf)).resolve()
        if not path.is_file():
            logger.warning("index entry %s points at missing PDF %s", canonical_id, path)
            return None
        return path

    def _resolve_tier2(self, norm: str) -> Path | None:
        """User-supplied PDF: a *.pdf in cache_dir whose normalized stem matches."""
        for pdf in self.cache_dir.glob("*.pdf"):
            if self._normalize(pdf.stem.replace("_", " ")) == norm:
                return pdf.resolve()
        return None

    def _tier2_stem(self, norm: str) -> str | None:
        for pdf in self.cache_dir.glob("*.pdf"):
            if self._normalize(pdf.stem.replace("_", " ")) == norm:
                return pdf.stem
        return None
