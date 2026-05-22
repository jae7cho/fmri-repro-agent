"""BIDS-style acquisition references — version-stable, group-agnostic.

Lifted out of :mod:`fmri_repro.spec.v0_1_0` so that downstream group modules
(:mod:`fmri_repro.spec.preprocessing`, future first-level / group-level / etc.)
can refer to acquisitions without importing the heavy versioned root.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FieldMeta(BaseModel):
    """Per-field metadata: report axis, inference applicability, data source.

    Used by both acquisition arm registries and preprocessing step registries.
    For preprocessing fields, ``bids_key`` is typically ``None`` and ``source``
    is typically ``"derived"`` or ``"none"`` (no sidecar/header path).
    """

    justification_axis: Literal["cobidas", "pipeline", "both"]
    inference_applicable: bool
    source: Literal["sidecar", "header", "derived", "none"]
    bids_key: str | None = None
    unit: str | None = None


class AcquisitionEntities(BaseModel):
    """BIDS entities that together with the suffix identify an acquisition protocol."""

    task: str | None = None
    run: int | None = None
    dir: str | None = None  # phase-encoding entity, e.g. "LR" / "AP"
    acq: str | None = None


class AcquisitionRef(BaseModel):
    """Reference to an acquisition in the same :class:`ReplicationSpec`.

    Used by fieldmap ``intended_for`` (anatomical/functional targets) and by
    preprocessing ``applies_to`` / ``intended_fieldmap`` (functional/fieldmap
    targets). Resolution to a present acquisition is enforced at the
    :class:`ReplicationSpec` level.
    """

    suffix: str
    entities: AcquisitionEntities = AcquisitionEntities()


# Order in which BIDS composes entities into a filename stem (relevant subset).
_BIDS_ENTITY_ORDER: tuple[str, ...] = ("task", "acq", "dir", "run")


def bids_stem(suffix: str, entities: AcquisitionEntities) -> str:
    """Compose a BIDS filename stem like ``"task-rest_dir-LR_bold"`` (without
    file extension). Acquisitions without entities reduce to the bare suffix
    (e.g. ``"T1w"``)."""
    parts: list[str] = []
    for ent in _BIDS_ENTITY_ORDER:
        val = getattr(entities, ent)
        if val is not None:
            parts.append(f"{ent}-{val}")
    parts.append(suffix)
    return "_".join(parts)
