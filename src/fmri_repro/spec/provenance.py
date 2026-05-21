"""Core provenance types for the ReplicationSpec — version-STABLE.

Shared across all spec versions. Future spec versions (``v0_x_y.py``) import
these and build versioned roots/groups on top. Behavior here is contract-frozen;
the test suite in ``tests/spec/test_provenance.py`` is the enforcement mechanism.
"""
# ruff: noqa: UP046
#   Logic-frozen module: ``class Foo(BaseModel, Generic[T])`` is the declared
#   shape. We intentionally do NOT rewrite to PEP 695 ``class Foo[T](BaseModel)``
#   here; that is a type-declaration change, not formatting.

from __future__ import annotations

from datetime import date
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")

# Single calibration edit point. Reasoned, not measured (design doc) — change here.
BASIS_CEILINGS: dict[str, float] = {
    "version_default": 0.95,
    "date_inferred_version": 0.75,
    "prior_publication": 0.60,
    "lab_prior": 0.50,
    "field_convention": 0.40,
}


class Span(BaseModel):
    """Char-offset back-pointer into ParsedPaper.text. Internal-consistency only;
    substring existence vs. the paper is a downstream Tier-1 check."""

    model_config = ConfigDict(frozen=True)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)
    section: str | None = None

    @model_validator(mode="after")
    def _ordered(self) -> Span:
        if self.end <= self.start:
            raise ValueError(f"Span.end ({self.end}) must be > start ({self.start})")
        return self


# --- Extraction stage (Methods Extractor; paper-only) ---
class Extracted(BaseModel, Generic[T]):
    status: Literal["EXTRACTED"] = "EXTRACTED"
    value: T
    spans: list[Span] = Field(min_length=1)  # no extraction without grounding
    confidence: float = Field(ge=0.0, le=1.0)


class MissingFromPaper(BaseModel):
    status: Literal["MISSING_FROM_PAPER"] = "MISSING_FROM_PAPER"
    searched_terms: list[str]  # required (no default); empty list allowed
    sections_searched: list[str]


# --- Inference basis taxonomy (per-arm typed refs for Tier-3 deterministic checks) ---
class VersionDefaultBasis(BaseModel):
    basis_type: Literal["version_default"] = "version_default"
    tool: str
    version: str
    note: str | None = None


class DateInferredVersionBasis(BaseModel):
    basis_type: Literal["date_inferred_version"] = "date_inferred_version"
    tool: str
    inferred_version: str
    paper_date: date
    note: str | None = None


class PriorPublicationBasis(BaseModel):
    basis_type: Literal["prior_publication"] = "prior_publication"
    citation: str
    note: str | None = None


class LabPriorBasis(BaseModel):
    basis_type: Literal["lab_prior"] = "lab_prior"
    lab_id: str  # must resolve to a lab YAML in fmri-defaults-kb (Critic checks)
    note: str | None = None


class FieldConventionBasis(BaseModel):
    basis_type: Literal["field_convention"] = "field_convention"
    source: str
    note: str | None = None


Basis = Annotated[
    VersionDefaultBasis
    | DateInferredVersionBasis
    | PriorPublicationBasis
    | LabPriorBasis
    | FieldConventionBasis,
    Field(discriminator="basis_type"),
]


# --- Inference stage (Pipeline Configurator; only when extraction == MISSING) ---
class AlternativeInference(BaseModel, Generic[T]):
    value: T
    basis: Basis
    confidence: float = Field(ge=0.0, le=1.0)


class InferredDefault(BaseModel, Generic[T]):
    status: Literal["INFERRED_DEFAULT"] = "INFERRED_DEFAULT"
    value: T
    basis: Basis
    confidence: float = Field(ge=0.0, le=1.0)
    alternative_inferences: list[AlternativeInference[T]]  # required; empty OK

    @model_validator(mode="after")
    def _ceiling(self) -> InferredDefault[T]:
        ceil = BASIS_CEILINGS[self.basis.basis_type]
        if self.confidence > ceil:
            raise ValueError(
                f"confidence {self.confidence} > ceiling {ceil} for {self.basis.basis_type}"
            )
        for alt in self.alternative_inferences:
            ac = BASIS_CEILINGS[alt.basis.basis_type]
            if alt.confidence > ac:
                raise ValueError(
                    f"alt confidence {alt.confidence} > ceiling {ac} for {alt.basis.basis_type}"
                )
        return self


class LeftMissing(BaseModel):
    status: Literal["LEFT_MISSING"] = "LEFT_MISSING"
    reason: str | None = None


class NotApplicable(BaseModel):
    """Extraction succeeded; no inference applies. Explicit per never-null ethos."""

    status: Literal["NOT_APPLICABLE"] = "NOT_APPLICABLE"


# --- The coupled two-stage field (Option A) ---
class ProvenancedField(BaseModel, Generic[T]):
    field_id: str  # dotted path e.g. "acquisition.tr" — for flat reports/Critic
    extraction: Annotated[
        Extracted[T] | MissingFromPaper,
        Field(discriminator="status"),
    ]
    inference: Annotated[
        InferredDefault[T] | LeftMissing | NotApplicable,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def couple_stages(self) -> ProvenancedField[T]:
        ext, inf = self.extraction.status, self.inference.status
        if ext == "EXTRACTED" and inf != "NOT_APPLICABLE":
            raise ValueError(
                f"EXTRACTED requires inference=NOT_APPLICABLE (got {inf}); "
                "Configurator must not touch extracted values."
            )
        if ext == "MISSING_FROM_PAPER" and inf == "NOT_APPLICABLE":
            raise ValueError("MISSING_FROM_PAPER requires INFERRED_DEFAULT or LEFT_MISSING.")
        return self
