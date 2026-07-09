"""Versioned root for ReplicationSpec v0.3.0.

Changes vs 0.2.0: the preprocessing chain gains two anatomical-target
:class:`~fmri_repro.spec.preprocessing.PreprocStep` kinds (``brain_extraction``,
``segmentation``), completes the tool/method separation (``method`` +
``filtering_integrated`` on ``NuisanceRegression``; a plain ``ants`` member on
``SpatialNormalizationMethod``), and — new here — puts a **version stamp on the
emitted artifact** (``Preprocessing.schema_version`` / ``written_under``), the
independently-parseable root the emitter ships.

Versioning model (read this before assuming these modules are readers): the version
modules share the one mutating :mod:`fmri_repro.spec.preprocessing`. So
``schema_version`` is a **write-time label** — it records which model a document was
written to conform to, NOT a promise that this module can parse older data. A genuine
v0.1.0/v0.2.0 artifact containing a step whose fields later changed does NOT parse
under its own version module; the supported path for old data is
:func:`fmri_repro.spec.migrations.parse_any_version` (migrate-then-parse). Only
:class:`StudySpec` is re-declared here — to pin ``schema_version`` and assert it equals
the stamp on every nested ``Preprocessing`` (enforced redundancy beats silent drift).
``v0_1_0.py`` stays frozen at ``"0.1.0"`` and ``v0_2_0.py`` at ``"0.2.0"``.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from fmri_repro.spec.v0_1_0 import ReplicationSpec, RunMeta, StudyAnalysis


class StudySpec(BaseModel):
    schema_version: Literal["0.3.0"] = "0.3.0"
    run: RunMeta
    specs: list[ReplicationSpec] = Field(min_length=1)
    study_analysis: StudyAnalysis | None = None

    @model_validator(mode="after")
    def _stamps_match_pinned_version(self) -> Self:
        """Every nested ``Preprocessing.schema_version`` must equal this root's pinned
        version. Holds natively (nested stamps default to 0.3.0); a backstop for a future
        bump that desyncs the outer/inner Literals (today the nested ``Literal["0.3.0"]`` is
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
