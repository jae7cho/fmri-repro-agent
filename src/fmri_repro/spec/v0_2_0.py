"""Versioned root for ReplicationSpec v0.2.0.

One focused change vs 0.1.0: per-voxel temporal z-scoring moves OUT of
``IntensityNormalizationConvention`` and INTO the new terminal
``temporal_standardization`` :class:`~fmri_repro.spec.preprocessing.PreprocStep`
kind, so intensity normalization is magnitude-scaling-only. Both flow in through
the shared :mod:`fmri_repro.spec.preprocessing`; the study/replication/acquisition
assembly is identical to 0.1.0 and is imported unchanged (import-and-re-export).

Only :class:`StudySpec` is re-declared here — to pin ``schema_version`` and
nothing else. Its other fields match ``v0_1_0.StudySpec`` field-for-field
(annotations, defaults, and the ``specs`` ``min_length=1`` constraint) so the
0.2.0 schema differs from 0.1.0 in exactly two ways: the version string and the
preprocessing changes above. ``v0_1_0.py`` stays frozen at ``"0.1.0"``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from fmri_repro.spec.v0_1_0 import ReplicationSpec, RunMeta, StudyAnalysis


class StudySpec(BaseModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    run: RunMeta
    specs: list[ReplicationSpec] = Field(min_length=1)
    study_analysis: StudyAnalysis | None = None
