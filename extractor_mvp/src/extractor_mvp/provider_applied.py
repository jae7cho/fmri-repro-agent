"""Preprocessing a data provider applied to a released dataset (the author's item 3, 2026-11-09).

The extraction prompts ask for provider-applied preprocessing to be reported as applied, quoted from
the sentence that names the release. This module marks such a field ``applied_by: data_provider``
beside the record (the spec has no field for it): an EXTRACTED field whose quote names one of the
paper's data releases (call R's dataset name, its parenthesised acronym, or the KB's names for the
release, kb/datasets) and says it was preprocessed. No model call.
"""

from __future__ import annotations

import re
from typing import Any

_CUE = re.compile(r"preprocess|processed|pipeline|minimal", re.IGNORECASE)


def _names(release: dict[str, Any]) -> set[str]:
    from fmri_defaults_kb import load_dataset_documents, recognize_dataset

    dataset = str(release.get("dataset") or "").strip()
    names = {dataset} if dataset else set()
    names |= set(re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{1,})\)", dataset))
    m = recognize_dataset(dataset, release.get("release")) if dataset else None
    if m is not None:
        docs = load_dataset_documents()
        for did in m.dataset_ids:
            d = docs.get(did) or {}
            names |= set(d.get("aliases") or []) | set(d.get("family_aliases") or [])
    return {n for n in names if len(n) >= 3}


def provider_applied(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    """``{dotted path: {"applied_by": "data_provider", "release": ...}}`` for every EXTRACTED field
    whose quote names one of the paper's releases and says it was preprocessed."""
    releases = (record.get("data_release") or {}).get("releases") or []
    named = [(r, _names(r)) for r in releases]
    out: dict[str, dict[str, str]] = {}
    for step in (record.get("preprocessing") or {}).get("steps", []):
        for key, pf in step.items():
            if (
                not isinstance(pf, dict)
                or (pf.get("extraction") or {}).get("status") != "EXTRACTED"
            ):
                continue
            quote = " ".join(sp.get("text", "") for sp in pf["extraction"].get("spans") or [])
            if not _CUE.search(quote):
                continue
            for rel, names in named:
                if any(
                    re.search(rf"(?<![A-Za-z0-9]){re.escape(n)}(?![A-Za-z0-9])", quote, re.I)
                    for n in names
                ):
                    label = " ".join(str(x) for x in (rel.get("dataset"), rel.get("release")) if x)
                    out[f"{step.get('kind')}.{key}"] = {
                        "applied_by": "data_provider",
                        "release": label,
                    }
                    break
    return out
