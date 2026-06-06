"""Three-state discriminated LLM output schema for a single extracted field.

Replaces the implicit (value, quote) binary schema used in v3.

Mapping to provenance.py extraction arms (post-processing responsibility):
  status="extracted"  -> Extracted(value, spans=[resolved_span], confidence=...)
  status="missing"    -> MissingFromPaper(searched_terms, sections_searched)
  status="deferred"   -> DeferredToCitation(deferrals=[Deferral(ref, span, target_kind)],
                                            searched_terms, sections_searched)

provenance.py is FROZEN. This module does not import it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class FieldExtractionResult(BaseModel):
    """Single-field LLM output. Exactly one of three statuses."""

    status: Literal["extracted", "missing", "deferred"]

    # extracted arm
    value: str | None = None
    verbatim_quote: str | None = None

    # deferred arm
    deferral_sentence: str | None = None  # verbatim sentence from paper text
    ref_string: str | None = None  # citation as written: "Glasser et al. 2013"
    target_kind: Literal["paper", "pipeline", "dataset_doc", "supplement"] = "paper"

    # missing + deferred
    searched_terms: list[str] = []
    sections_searched: list[str] = []

    @model_validator(mode="after")
    def enforce_status_constraints(self) -> FieldExtractionResult:
        if self.status == "extracted":
            if self.value is None or self.verbatim_quote is None:
                raise ValueError(
                    "status='extracted' requires both value and verbatim_quote. "
                    "If the field is stated but the exact sentence is unclear, "
                    "use status='missing'."
                )
            if self.deferral_sentence is not None or self.ref_string is not None:
                raise ValueError("status='extracted' must not set deferral_sentence or ref_string.")
        elif self.status == "missing":
            if self.value is not None or self.verbatim_quote is not None:
                raise ValueError("status='missing' must not set value or verbatim_quote.")
            if self.deferral_sentence is not None or self.ref_string is not None:
                raise ValueError("status='missing' must not set deferral fields.")
        elif self.status == "deferred":
            if self.deferral_sentence is None or self.ref_string is None:
                raise ValueError(
                    "status='deferred' requires both deferral_sentence (verbatim) "
                    "and ref_string. If you cannot quote the deferral sentence "
                    "verbatim, use status='missing' instead."
                )
            if self.value is not None or self.verbatim_quote is not None:
                raise ValueError("status='deferred' must not set value or verbatim_quote.")
        return self
