"""Re-resolve a stored record's realignment tool with the current precedence, no model call
(2026-11-09, night 3). The model's answer is taken from the stored resolution: its raw ``answer``
when the record has one (stored from 2026-11-09 night 3), else rebuilt from what the stored
resolution kept (the pipeline and tool as answered, the basis sentence, the sub-items). A motion
method arm the old resolution filled is reset first, then filled again from the new resolution."""

from __future__ import annotations

import copy
from typing import Any

from extractor_mvp.resolution_call import (
    SUB_ITEMS,
    ResolutionAnswer,
    SubItem,
    fill_method_arm,
    interpret,
)

#: The LEFT_MISSING reason the extraction writes, by the method field's extraction status.
_ORIGINAL_REASON = {
    "DEFERRED_TO_CITATION": "deferred_to_citation",
    "MISSING_FROM_PAPER": "not_stated_in_text",
}


def answer_from_stored(res: dict[str, Any]) -> ResolutionAnswer:
    if isinstance(res.get("answer"), dict):
        return ResolutionAnswer.model_validate(res["answer"])
    rp = res.get("resolved_pipeline") or {}
    tool = res.get("realignment_tool") or {}
    items = {}
    for name in SUB_ITEMS:
        it = (res.get("sub_items") or {}).get(name) or {}
        status = (
            it.get("status")
            if it.get("status") in ("stated", "inferred_from_default", "unknown")
            else "unknown"
        )
        items[name] = SubItem.model_validate(
            {
                "status": status,
                "value": it.get("model_said") or it.get("value"),
                "quote": it.get("quote") or it.get("quote_unresolved"),
            }
        )
    return ResolutionAnswer(
        resolved_pipeline=str(rp.get("as_answered") or rp.get("value") or "none"),
        realignment_tool=str(tool.get("as_answered") or tool.get("value") or "none"),
        basis=str(res.get("basis") or ""),
        **items,
    )


def reresolve_record(record: dict[str, Any], text: str) -> dict[str, Any]:
    """A copy of ``record`` with its resolution recomputed (no model call)."""
    from fmri_repro.spec.migrations import parse_any_version

    rec = copy.deepcopy(record)
    old = rec.get("resolution") or {}
    if old.get("status") != "ok":
        return rec
    for step in rec["preprocessing"].get("steps", []):
        if step.get("kind") != "motion_correction":
            continue
        m = step["method"]
        basis = (m.get("inference") or {}).get("basis") or {}
        if basis.get("source_field_ids") == ["resolution_call"]:
            status = m["extraction"]["status"]
            m["inference"] = {
                "status": "LEFT_MISSING",
                "reason": _ORIGINAL_REASON.get(status, "not_stated_in_text"),
            }
    new = interpret(answer_from_stored(old), rec, text)
    rec["resolution"] = new
    prep = fill_method_arm(parse_any_version(rec["preprocessing"]), new)
    step = next((s for s in prep.steps if getattr(s, "kind", None) == "motion_correction"), None)
    for dumped in rec["preprocessing"].get("steps", []):
        if step is not None and dumped.get("kind") == "motion_correction":
            dumped["method"]["inference"] = step.method.inference.model_dump(mode="json")
    rec["reresolved"] = {"date": "2026-11-09", "from": "stored resolution, no model call"}
    return rec
