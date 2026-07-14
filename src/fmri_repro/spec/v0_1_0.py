"""Version constant for ReplicationSpec v0.1.0 — NOT a reader.

There is deliberately no ``v0_1_0.StudySpec``. The minor-version modules share the one
mutating :mod:`fmri_repro.spec.preprocessing`, so an old root could only ever pin a version
string while carrying today's (0.4.0) nested models — a document lying about itself. The
shared, version-stable spec core (``RunMeta``, ``ReplicationSpec``, ``StudyAnalysis``, the
acquisition arms) lives in :mod:`fmri_repro.spec.core`; the sole live root is
:class:`fmri_repro.spec.v0_4_0.StudySpec`.

Read archived v0.1.0 artifacts through :func:`fmri_repro.spec.migrations.parse_any_version`
(migrate-then-parse). The migration floor is 0.2.0 — the 0.1.0→0.2.0 hop is a semantic
restructuring and is not auto-migrated; a genuine v0.1.0 specimen is retained frozen under
``examples/frozen/``.
"""

from __future__ import annotations

SCHEMA_VERSION = "0.1.0"
