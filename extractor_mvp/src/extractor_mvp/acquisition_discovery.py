"""Fork C Pass 1: discover the distinct acquisitions/cohorts a paper analyzes.

The LLM emits each acquisition's verbatim ``paper_name`` + a characterizing
quote; Python slugifies the name deterministically (same precision-discipline as
the synonym resolver — LLM extracts faithfully, Python normalizes) and resolves
the quote to a Span. ``acquisition_id`` therefore does not depend on the LLM.
"""

from __future__ import annotations

import re
from typing import Any

from fmri_repro.spec.provenance import Span
from pydantic import BaseModel

from extractor_mvp.extractor import build_client
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.span_resolver import resolve_quote


class AcquisitionDescriptor(BaseModel):
    """One distinct dataset/cohort/sample with its own preprocessing pipeline."""

    acquisition_id: str  # slugified, stable, used as the Map key
    paper_name: str  # exact term the paper uses (verbatim)
    characterizing_quote: str  # quote where the acquisition is named/introduced
    span: Span | None  # resolved span; None if the quote couldn't be located
    span_failure_reason: str | None  # "quote_not_found" / "quote_ambiguous" / None


class AcquisitionDiscoveryResult(BaseModel):
    acquisitions: list[AcquisitionDescriptor]
    note: str | None = None  # e.g. "single_acquisition_paper", "no_acquisitions_found"


def slugify_paper_name(paper_name: str) -> str:
    """Lowercase, collapse non-alphanumeric runs to single underscores, strip ends."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", paper_name.lower()).strip("_")
    return s or "unnamed_acquisition"


# --- LLM output schema (Pass 1) ---------------------------------------------


class _LLMAcquisition(BaseModel):
    paper_name: str
    characterizing_quote: str


class _LLMAcquisitionList(BaseModel):
    acquisitions: list[_LLMAcquisition]


ACQUISITION_DISCOVERY_PROMPT = """\
You are reading the methods section of an fMRI paper. Your task is to identify
all distinct DATASETS, COHORTS, or SAMPLES the paper analyzes — each one with
its own preprocessing or analysis pipeline.

For each acquisition, return:
1. paper_name: the exact term the paper uses to refer to it (verbatim, copied
   from the text). Examples: "HCP-TRT", "Sample 1", "ABCD cohort", "Discovery
   sample".
2. characterizing_quote: a verbatim quote from the text that introduces or names
   this acquisition. The quote must appear in the text exactly as written.

If the paper describes only ONE dataset/cohort, return that one acquisition.
If the paper does not clearly distinguish multiple acquisitions, return one
acquisition with paper_name describing the overall sample.

Do NOT split a single dataset into multiple acquisitions just because the paper
mentions multiple scanners, sites, or analysis steps within it. The criterion
is: would the preprocessing/analysis be described separately for this group?

Text:
\"\"\"
{text}
\"\"\"
"""


def discover_acquisitions(
    parsed_paper: ParsedPaper, model: str, *, client: Any | None = None
) -> AcquisitionDiscoveryResult:
    """Pass 1: one LLM call -> deterministic acquisition descriptors."""
    client = client or build_client()
    llm: _LLMAcquisitionList = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": ACQUISITION_DISCOVERY_PROMPT.format(text=parsed_paper.text)}
        ],
        response_model=_LLMAcquisitionList,
        temperature=0.0,
        max_retries=2,
    )

    descriptors: list[AcquisitionDescriptor] = []
    used_ids: set[str] = set()
    for a in llm.acquisitions:
        base = slugify_paper_name(a.paper_name)
        acq_id, n = base, 2
        while acq_id in used_ids:  # collision -> _2, _3, ...
            acq_id, n = f"{base}_{n}", n + 1
        used_ids.add(acq_id)
        res = resolve_quote(a.characterizing_quote, parsed_paper.text)
        descriptors.append(
            AcquisitionDescriptor(
                acquisition_id=acq_id,
                paper_name=a.paper_name,
                characterizing_quote=a.characterizing_quote,
                span=res.span,
                span_failure_reason=res.failure_reason,
            )
        )

    if not descriptors:
        note = "no_acquisitions_found"
    elif len(descriptors) == 1:
        note = "single_acquisition_paper"
    else:
        note = None
    return AcquisitionDiscoveryResult(acquisitions=descriptors, note=note)
