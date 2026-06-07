"""Cross-repo bridge: fmri-defaults-kb consumers used by the Configurator.

Import direction is one-way: this package imports ``fmri_defaults_kb``; the
KB never imports anything from ``fmri_repro``. Contract surface is the
basis-type literal set (``KB_BASIS_LITERALS`` ⊆ ``BASIS_CEILINGS``).
"""

from fmri_repro.kb_client.base_pipeline import (
    SEVEN_DEMOTED_FIELDS,
    certain_version,
    fill_dependent_defaults,
    infer_base_pipeline_version,
)

__all__ = [
    "SEVEN_DEMOTED_FIELDS",
    "certain_version",
    "fill_dependent_defaults",
    "infer_base_pipeline_version",
]
