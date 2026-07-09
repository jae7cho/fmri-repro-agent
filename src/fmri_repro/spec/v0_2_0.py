"""Version constant for ReplicationSpec v0.2.0 — NOT a reader.

v0.2.0's one change vs 0.1.0 was moving per-voxel temporal z-scoring out of
``IntensityNormalizationConvention`` into the terminal ``temporal_standardization``
:class:`~fmri_repro.spec.preprocessing.PreprocStep` kind.

There is deliberately no ``v0_2_0.StudySpec``. The minor-version modules share the one
mutating :mod:`fmri_repro.spec.preprocessing`, so an old root could only ever pin a version
string while carrying today's (0.3.0) nested models — a document lying about itself. Read
archived v0.2.0 artifacts through :func:`fmri_repro.spec.migrations.parse_any_version`
(migrate-then-parse); a genuine older specimen is retained under ``examples/frozen/``.
"""

from __future__ import annotations

SCHEMA_VERSION = "0.2.0"
