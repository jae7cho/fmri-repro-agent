"""Versioned root for the ReplicationSpec — the single live ``StudySpec`` root (currently stamps 0.5.0).

This module is the sole live root. Both additive-patch bumps and the one structural bump so far are
applied IN PLACE (see :mod:`fmri_repro.spec.migrations`), the module keeping its name and its
``Literal`` being bumped, rather than forking a ``v0_4_1.py`` / ``v0_5_0.py``:

- 0.4.0 -> 0.4.1 (additive): the ``study_specific`` ``TargetSpace`` value; pure re-stamp hop.
- 0.4.1 -> 0.5.0 (STRUCTURAL): the five ``literal_type`` fields (``target_space``, ``target_surface``,
  ``surface_registration``, intensity ``convention``, temporal ``method``) retyped to
  ``SpecifiedTerm{verbatim, resolved, resolution}`` so recording a stated term no longer depends on the
  resolver succeeding. The convention *permits* ("may warrant") a distinct root for a structural change
  but does not require one; the existing pattern deliberately avoids per-version roots (a new root only
  stamps over the one shared mutating :mod:`preprocessing`, so it buys nothing here). Old data migrates
  forward via a real doc-transform hop, not a re-stamp.

Earlier provenance-layer change (0.3.0 -> 0.4.0): the shared
:class:`~fmri_repro.spec.provenance.Extracted` model gained an optional
``span_recovered: bool = False`` flag, set True when a quote's char-offset span
was located ONLY by the tolerant corrupted-source tier of the span resolver
(tier 5) rather than a clean exact/near match.

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
    schema_version: Literal["0.5.1"] = "0.5.1"
    run: RunMeta
    specs: list[ReplicationSpec] = Field(min_length=1)
    study_analysis: StudyAnalysis | None = None

    @model_validator(mode="after")
    def _stamps_match_pinned_version(self) -> Self:
        """Every nested ``Preprocessing.schema_version`` must equal this root's pinned
        version. Holds natively (nested stamps default to 0.5.0); a backstop for a future
        bump that desyncs the outer/inner Literals (today the nested ``Literal["0.5.0"]`` is
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
