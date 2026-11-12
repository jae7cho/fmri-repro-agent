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

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
                    "Use status='missing' ONLY when no quotable sentence exists. Uncertainty about whether the sentence "
                    "belongs to THIS field is not grounds for 'missing' — a stated field with a quotable sentence must "
                    "use 'extracted'."
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


class VariantResult(BaseModel):
    """One value the paper states for a part of its data (DESIGN_applies_to.md, 2026-11-11).
    ``applies_to`` is the paper's own words for the part; ``applies_to_quote`` is the sentence that
    ties the value to the part, when it is not the value's own sentence. ``value`` is null only on
    the single "varied across compared models" entry."""

    value: str | None = None
    verbatim_quote: str
    #: 2026-11-11 (pre-rerun item 1): up to two more spans of the text, when the evidence is in two
    #: or three places; each is resolved, and the value is checked against all of them together
    additional_quotes: list[str] = Field(default_factory=list, max_length=2)
    applies_to: str
    applies_to_quote: str | None = None


class StepFieldResult(FieldExtractionResult):
    """A step field's output: the three statuses plus ``varied`` (fork A1), for the extraction,
    temporal/volume and spatial calls only. Every other call keeps :class:`FieldExtractionResult`,
    so its schema is unchanged."""

    status: Literal["extracted", "missing", "deferred", "varied"]  # type: ignore[assignment]
    #: 2026-11-11 (pre-rerun item 1): up to two more spans of the text, with status "extracted",
    #: when the evidence is in two or three places; never one quote stitched from several
    additional_quotes: list[str] = Field(default_factory=list, max_length=2)
    variants: list[VariantResult] = []

    @model_validator(mode="before")
    @classmethod
    def _a_three_state_result(cls, data: Any) -> Any:
        """A :class:`FieldExtractionResult` (a stub, a fixture, another call's answer) is read as
        its fields: the three states are a subset of these four. Adds nothing to the JSON schema."""
        if isinstance(data, FieldExtractionResult) and not isinstance(data, StepFieldResult):
            return data.model_dump()
        return data

    @model_validator(mode="after")
    def enforce_varied_constraints(self) -> StepFieldResult:
        if self.additional_quotes and self.status != "extracted":
            raise ValueError("additional_quotes are set only with status='extracted'.")
        if self.status == "varied":
            if not self.variants:
                raise ValueError("status='varied' requires variants.")
            if self.value is not None or self.verbatim_quote is not None:
                raise ValueError("status='varied' carries its values in variants, not value.")
            if self.deferral_sentence is not None or self.ref_string is not None:
                raise ValueError("status='varied' must not set deferral fields.")
        elif self.variants:
            raise ValueError("variants are set only with status='varied'.")
        return self
