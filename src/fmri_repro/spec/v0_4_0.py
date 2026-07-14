"""Versioned root for ReplicationSpec v0.4.0.

Changes vs 0.3.0: purely additive at the provenance layer — the shared
:class:`~fmri_repro.spec.provenance.Extracted` model gains an optional
``span_recovered: bool = False`` flag, set True when a quote's char-offset span
was located ONLY by the tolerant corrupted-source tier of the span resolver
(tier 5) rather than a clean exact/near match. There is **no structural change
to the spec chain** (same roots, groups, and steps as 0.3.0); a 0.3.0 document
parses unchanged because the new field is optional-with-default.

Versioning model (read this before assuming these modules are readers): the version
modules share the one mutating :mod:`fmri_repro.spec.preprocessing`. So
``schema_version`` is a **write-time label** — it records which model a document was
written to conform to, NOT a promise that this module can parse older data. A genuine
v0.1.0/v0.2.0/v0.3.0 artifact containing a step whose fields later changed does NOT parse
under its own version module; the supported path for old data is
:func:`fmri_repro.spec.migrations.parse_any_version` (migrate-then-parse). Only
:class:`StudySpec` is re-declared here — to pin ``schema_version`` and assert it equals
the stamp on every nested ``Preprocessing`` (enforced redundancy beats silent drift).
``v0_1_0.py`` stays frozen at ``"0.1.0"``, ``v0_2_0.py`` at ``"0.2.0"``, and
``v0_3_0.py`` at ``"0.3.0"``.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from fmri_repro.spec.core import ReplicationSpec, RunMeta, StudyAnalysis


class StudySpec(BaseModel):
    schema_version: Literal["0.4.0"] = "0.4.0"
    run: RunMeta
    specs: list[ReplicationSpec] = Field(min_length=1)
    study_analysis: StudyAnalysis | None = None

    @model_validator(mode="after")
    def _stamps_match_pinned_version(self) -> Self:
        """Every nested ``Preprocessing.schema_version`` must equal this root's pinned
        version. Holds natively (nested stamps default to 0.4.0); a backstop for a future
        bump that desyncs the outer/inner Literals (today the nested ``Literal["0.4.0"]`` is
        the first-line enforcement)."""
        for i, spec in enumerate(self.specs):
            for j, prep in enumerate(spec.preprocessing):
                if prep.schema_version != self.schema_version:
                    raise ValueError(
                        f"specs[{i}].preprocessing[{j}].schema_version="
                        f"{prep.schema_version!r} != StudySpec.schema_version="
                        f"{self.schema_version!r}"
                    )
        return self
