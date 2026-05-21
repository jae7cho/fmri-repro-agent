"""Versioned root for ReplicationSpec v0.1.0.

The spec is SemVer'd, with **one module per minor version** (this is the v0.1.0
module; a future v0.2.0 will live in a sibling ``v0_2_0.py`` and import the
same version-stable core types from :mod:`fmri_repro.spec.provenance`).

Between-version migrations are intended to be expressed as RFC 6902 JSON Patch
documents. **No migration engine is implemented in this chat** — that is
deferred to a later milestone, along with ``python-jsonpatch`` / ``bsmschema``
integration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from fmri_repro.spec.provenance import ProvenancedField


class PaperRef(BaseModel):
    source: str
    sha256: str | None = None


class RunMeta(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    paper: PaperRef


class AcquisitionParams(BaseModel):
    """SEED ONLY — stub to be grown in later chats."""

    repetition_time_s: ProvenancedField[float]
    echo_time_ms: ProvenancedField[float]
    n_volumes: ProvenancedField[int]


class Preprocessing(BaseModel):
    """TODO: grow in a later chat."""


class FirstLevelModel(BaseModel):
    """TODO: grow in a later chat."""


class GroupLevelModel(BaseModel):
    """TODO: grow in a later chat."""


class Thresholding(BaseModel):
    """TODO: grow in a later chat."""


class ReplicationSpec(BaseModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    run: RunMeta
    acquisition: AcquisitionParams
    preprocessing: Preprocessing
    first_level: FirstLevelModel
    group_level: GroupLevelModel
    thresholding: Thresholding
