"""Version constant for ReplicationSpec v0.3.0 — NOT a reader.

v0.3.0's changes vs 0.2.0 were: two anatomical-target
:class:`~fmri_repro.spec.preprocessing.PreprocStep` kinds (``brain_extraction``,
``segmentation``), completion of the tool/method separation (``method`` +
``filtering_integrated`` on ``NuisanceRegression``; a plain ``ants`` member on
``SpatialNormalizationMethod``), and a **version stamp on the emitted artifact**
(``Preprocessing.schema_version`` / ``written_under``).

There is deliberately no ``v0_3_0.StudySpec``. The minor-version modules share the one
mutating :mod:`fmri_repro.spec.preprocessing`, so an old root could only ever pin a version
string while carrying today's (0.4.0) nested models — a document lying about itself. Read
archived v0.3.0 artifacts through :func:`fmri_repro.spec.migrations.parse_any_version`
(migrate-then-parse); the sole live root is :class:`fmri_repro.spec.v0_4_0.StudySpec`.
"""

from __future__ import annotations

SCHEMA_VERSION = "0.3.0"
