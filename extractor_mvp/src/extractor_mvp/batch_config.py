"""Batch-run configuration: a model + a list of PDF papers.

PDFs only — no DOI/Unpaywall fetching (dropped; paywalled-paper friction isn't
worth it for the abstract). ``path`` fields are resolved relative to the config
file's location.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class PdfPaper(BaseModel):
    paper_id: str  # short identifier, e.g. "schwartz_2018"
    path: Path  # absolute, or relative to the config file


class BatchConfig(BaseModel):
    model: str  # e.g. "bedrock/anthropic.claude-sonnet-4-5-..."
    output_dir: Path = Path("results/batch")
    # KB/citation fallback for base-pipeline deferrals. Resolved relative to the
    # config file; if the dir is absent the batch runs without citation fallback.
    citation_cache_dir: Path = Path("citation_cache")
    papers: list[PdfPaper] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_paper_ids(self) -> BatchConfig:
        ids = [p.paper_id for p in self.papers]
        if len(set(ids)) != len(ids):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"Duplicate paper_ids: {dupes}")
        return self


def load_batch_config(config_path: Path) -> BatchConfig:
    """Load + validate a YAML config. Relative paper/output paths are resolved
    against the config file's directory so a config is portable."""
    config_path = config_path.resolve()
    base = config_path.parent
    config = BatchConfig.model_validate(yaml.safe_load(config_path.read_text(encoding="utf-8")))

    resolved_papers = [
        PdfPaper(paper_id=p.paper_id, path=p.path if p.path.is_absolute() else (base / p.path))
        for p in config.papers
    ]
    output_dir = (
        config.output_dir if config.output_dir.is_absolute() else (base / config.output_dir)
    )
    cache_dir = (
        config.citation_cache_dir
        if config.citation_cache_dir.is_absolute()
        else (base / config.citation_cache_dir)
    )
    return BatchConfig(
        model=config.model,
        output_dir=output_dir,
        citation_cache_dir=cache_dir,
        papers=resolved_papers,
    )
