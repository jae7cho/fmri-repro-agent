"""Shared helpers for the batch runners (batch.py + multi_acquisition_batch.py)."""

from __future__ import annotations

import logging
from functools import partial

from extractor_mvp.batch_config import BatchConfig
from extractor_mvp.citation_resolver import CitationResolver
from extractor_mvp.extractor import extract_preprocessing
from extractor_mvp.paper_fetcher import PaperFetcher

logger = logging.getLogger(__name__)


def build_citation_resolver(config: BatchConfig) -> CitationResolver | None:
    """Build a CitationResolver from ``config.citation_cache_dir``, or None.

    Returns None (with a warning) when the cache dir is absent — the batch then
    runs without the base-pipeline citation fallback rather than erroring. The
    extractor callable is model-bound via ``functools.partial`` so it satisfies
    CitationResolver's one-arg ``Callable[[ParsedPaper], ...]`` contract
    (``extract_preprocessing`` itself also requires ``model``).
    """
    cache_dir = config.citation_cache_dir
    if not cache_dir.exists():
        logger.warning(
            "citation_cache_dir %s not found; base-pipeline citation fallback disabled", cache_dir
        )
        return None
    return CitationResolver(
        extractor=partial(extract_preprocessing, model=config.model),
        fetcher=PaperFetcher(cache_dir=cache_dir),
        max_depth=1,
    )
