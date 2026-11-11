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

import re
import unicodedata
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
    "derived": 0.70,
}


class Span(BaseModel):
    """Char-offset back-pointer into ParsedPaper.text. Internal-consistency only;
    substring existence vs. the paper is a downstream Tier-1 check."""

    model_config = ConfigDict(frozen=True)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)
    section: str | None = None
    # 0.5.3 (2026-10-28, DESIGN_coverage_expansion.md B14 item 1): the named source-text repairs the
    # resolver applied to locate this span (the multiplication sign→/C2, fi→ª, >→4), empty for a clean or a tier-5
    # match. Additive: a span written before 0.5.3 parses with an empty list.
    repairs: list[str] = Field(default_factory=list)

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
    span_recovered: bool = False  # True iff the span was located ONLY by the corrupted-source
    # tolerant tier (span_resolver tier 5), not a clean exact/near match.


# --- Values that differ by what they apply to (0.7.0; DESIGN_applies_to.md, fork A1) ---
#: What a value applies to when it holds for all of the paper's data. An ``Extracted`` value is
#: "all" implicitly; a ``Variant`` never is.
APPLIES_TO_ALL = "all"
#: The one ``applies_to`` a value-less variant may carry (fork C2): the paper compares models and
#: does not describe one.
COMPARED_MODELS = "varied across compared models"


def normalize_applies_to(words: str) -> str:
    """The comparison key of an ``applies_to`` (the author's same-string rule, 2026-11-11): case,
    dashes, '&', punctuation, spacing and a leading 'the' do not distinguish two variants, so 'Parts
    I-II' written with an en dash and 'parts I-II' are one part. The paper's own words are what is stored and shown."""
    s = unicodedata.normalize("NFKC", words).casefold()
    s = re.sub("[\u2010-\u2015\u2212]", "-", s).replace("&", " and ")
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s*-\s*", "-", s)
    tokens = s.split()
    if tokens[:1] == ["the"]:
        tokens = tokens[1:]
    return " ".join(tokens)


class Variant(BaseModel, Generic[T]):
    """One value the paper states for a part of its data: a derived measure, an analysis, a data
    type, a scanner or site, or a named preprocessing variant (``applies_to``, the paper's words).

    ``applies_to_spans`` holds the sentence that ties the value to the part when it is not the
    value's own sentence. ``applies_to_verified`` is False when the words were found in neither: the
    label is then shown as unverified, never dropped and never replaced with "all". ``value`` is
    None only on the single compared-models entry (fork C2)."""

    value: T | None
    spans: list[Span] = Field(min_length=1)
    applies_to: str = Field(min_length=1)
    applies_to_spans: list[Span] = Field(default_factory=list)
    applies_to_verified: bool = True
    confidence: float = Field(ge=0.0, le=1.0)
    span_recovered: bool = False


class Varied(BaseModel, Generic[T]):
    """A field whose value differs by what it applies to (fork A1): the variants and no single
    value, so no code that reads ``Extracted.value`` can take one variant as the paper's.

    Either one or more variants each with a value, or exactly one value-less compared-models entry.
    No variant is "all" and no two share an ``applies_to`` under :func:`normalize_applies_to`.
    ``variants_dropped`` counts the variants whose value or quote did not check, so a reader knows
    the list is not the paper's whole statement."""

    status: Literal["VARIED"] = "VARIED"
    variants: list[Variant[T]] = Field(min_length=1)
    variants_dropped: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _well_formed(self) -> Varied[T]:
        keys = [normalize_applies_to(v.applies_to) for v in self.variants]
        if APPLIES_TO_ALL in keys:
            raise ValueError('a variant never applies to "all"; that value is Extracted')
        if len(set(keys)) != len(keys):
            raise ValueError(f"two variants share an applies_to: {keys}")
        valueless = [v for v in self.variants if v.value is None]
        if valueless and (
            len(self.variants) != 1
            or normalize_applies_to(valueless[0].applies_to) != COMPARED_MODELS
        ):
            raise ValueError(
                f"a value-less variant is only the single {COMPARED_MODELS!r} entry (fork C2)"
            )
        return self


#: The extraction statuses that report what the paper states (the inference arm stays NOT_APPLICABLE)
STATED_STATUSES: frozenset[str] = frozenset({"EXTRACTED", "VARIED"})


class MissingFromPaper(BaseModel):
    status: Literal["MISSING_FROM_PAPER"] = "MISSING_FROM_PAPER"
    searched_terms: list[str]  # required (no default); empty list allowed
    sections_searched: list[str]


class Deferral(BaseModel):
    """One paper→citation hand-off: the citation pointed at and the sentence saying so."""

    ref: str  # citation label / DOI / pipeline name
    span: Span  # the deferring sentence
    target_kind: Literal["paper", "pipeline", "dataset_doc"] = "paper"


class DeferredToCitation(BaseModel):
    """Paper explicitly refers methodological detail to another source.

    Distinct from MISSING_FROM_PAPER (which means "we looked and found nothing"):
    here the paper *names* a citation. Coupled like MISSING for inference
    purposes — ``ProvenancedField`` rejects NOT_APPLICABLE on this arm.
    """

    status: Literal["DEFERRED_TO_CITATION"] = "DEFERRED_TO_CITATION"
    deferrals: list[Deferral] = Field(min_length=1)
    searched_terms: list[str]
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


class DerivedBasis(BaseModel):
    basis_type: Literal["derived"] = "derived"
    source_field_ids: list[str] = Field(min_length=1)
    note: str | None = None


Basis = Annotated[
    VersionDefaultBasis
    | DateInferredVersionBasis
    | PriorPublicationBasis
    | LabPriorBasis
    | FieldConventionBasis
    | DerivedBasis,
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
        Extracted[T] | Varied[T] | MissingFromPaper | DeferredToCitation,
        Field(discriminator="status"),
    ]
    inference: Annotated[
        InferredDefault[T] | LeftMissing | NotApplicable,
        Field(discriminator="status"),
    ]

    @model_validator(mode="after")
    def couple_stages(self) -> ProvenancedField[T]:
        ext, inf = self.extraction.status, self.inference.status
        if ext in STATED_STATUSES and inf != "NOT_APPLICABLE":
            raise ValueError(
                f"{ext} requires inference=NOT_APPLICABLE (got {inf}); "
                "Configurator must not touch extracted values."
            )
        if ext in ("MISSING_FROM_PAPER", "DEFERRED_TO_CITATION") and inf == "NOT_APPLICABLE":
            raise ValueError(f"{ext} requires INFERRED_DEFAULT or LEFT_MISSING.")
        return self
