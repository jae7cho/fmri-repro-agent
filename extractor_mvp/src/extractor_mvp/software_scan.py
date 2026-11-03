"""The software list by deterministic scan, then one scoped question per mention (the author's ruling,
2026-11-03).

The model no longer lists software. :func:`scan` finds every mention of a ``kb/tools`` package name
in a paper's text (the reference list excluded), with the sentence around it and, read
deterministically, a version written right after the name. :func:`ask_uses` then asks one scoped
question per mention: what the passage says the tool is used for, quoted, and whether that use is
fMRI processing or produces something the fMRI processing uses. A tool is kept when any of its
mentions answers yes with a quote found in its passage. A tool the KB does not list is never found:
the scan's reach is the KB's (FreeSurfer is not in ``kb/tools`` as of 2026-11-03).
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Literal

from pydantic import BaseModel

from extractor_mvp.span_resolver import resolve_quote

#: A version written right after the name: "FreeSurfer v5.3", "FSL version 5.0.10", "FSL 5.0.10".
#: Dotted only, so a citation number glued to the name ("AFNI48") is never a version.
_VERSION_AFTER = re.compile(r"^[\s,]*(?:v(?:ersion)?\.?\s*)?(\d+\.\d+(?:\.\d+)*)", re.IGNORECASE)
#: A version that is part of the name token (version_token packages): "SPM12".
_GLUED_VERSION = re.compile(r"^(\d+)\b")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
_CONTEXT_SENTENCES = 2


@dataclasses.dataclass(frozen=True)
class Mention:
    """One mention of a KB package in a paper: offsets into the text the scan read."""

    tool_id: str
    display_name: str
    alias: str
    start: int
    end: int
    sentence: str
    passage: str  # the sentence with up to two sentences either side
    version: str | None


def _kb_tools() -> dict[str, dict[str, Any]]:
    from fmri_defaults_kb.tools import load_tool_documents

    return load_tool_documents()


def _body_end(text: str) -> int:
    """Where the reference list starts (the last reference heading), else the end of the text."""
    from extractor_mvp.citation_hop import _REF_HEADING

    heads = list(_REF_HEADING.finditer(text))
    return heads[-1].start() if heads else len(text)


def _sentences(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for m in _SENTENCE_END.finditer(text):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(text)))
    return spans


def scan(text: str, tools: dict[str, dict[str, Any]] | None = None) -> list[Mention]:
    """Every KB package mention in ``text`` before its reference list, one per (tool, sentence):
    an alias matched whole and case-sensitively, the longest alias where two overlap."""
    tools = _kb_tools() if tools is None else tools
    body = text[: _body_end(text)]
    sents = _sentences(body)
    hits: list[tuple[int, int, str, str]] = []  # start, end, tool_id, alias
    for tool_id, doc in tools.items():
        for alias in sorted(doc.get("aliases") or [], key=len, reverse=True):
            # a digit run may follow the name: SPM's version token ("SPM12") or a citation number
            # the text layer glued on ("AFNI48"); a following letter makes it another word ("SPMs")
            for m in re.finditer(rf"(?<![\w-]){re.escape(alias)}(?![A-Za-z_-])", body):
                hits.append((m.start(), m.end(), tool_id, alias))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    kept: list[tuple[int, int, str, str]] = []
    for h in hits:
        if kept and h[0] < kept[-1][1]:
            continue  # inside a longer alias already kept
        kept.append(h)
    out: list[Mention] = []
    seen: set[tuple[str, int]] = set()
    for start, end, tool_id, alias in kept:
        k = next(i for i, (a, b) in enumerate(sents) if a <= start <= b)
        if (tool_id, k) in seen:
            continue
        seen.add((tool_id, k))
        a, b = sents[k]
        pa = sents[max(0, k - _CONTEXT_SENTENCES)][0]
        pb = sents[min(len(sents) - 1, k + _CONTEXT_SENTENCES)][1]
        after = body[end : end + 30]
        if tools[tool_id].get("version_token"):
            g = _GLUED_VERSION.match(after)
            version = g.group(1) if g else None
        else:
            v = _VERSION_AFTER.match(after)
            version = v.group(1) if v else None
        out.append(
            Mention(
                tool_id,
                str(tools[tool_id].get("display_name") or tool_id),
                alias,
                start,
                end,
                body[a:b],
                body[pa:pb],
                version,
            )
        )
    return out


SOFTWARE_USE_PROMPT = """\
You are reading one passage of a neuroimaging paper that names the software package {tool}. Answer
from this passage only.
use: what the passage says {tool} is used for, in a few words; "not stated" when it says nothing.
use_quote: the sentence of the passage that states that use, copied exactly; null when none.
fmri: "yes" when that use is processing the functional (fMRI/BOLD) data, or produces something the
fMRI processing uses (e.g. masks, regions of interest, surfaces, registrations); "no" when the use is
something else (structural-only or diffusion analysis, statistics, acquisition, display); "unclear"
when the passage does not say.

Passage:
\"\"\"
{passage}
\"\"\"
"""


class MentionUse(BaseModel):
    use: str
    use_quote: str | None = None
    fmri: Literal["yes", "no", "unclear"] = "unclear"


def ask_uses(
    mentions: list[Mention], model: str, *, client: Any, meter: Any | None = None
) -> list[dict[str, Any]]:
    """One scoped question per mention. Never raises: a failed call is recorded on its mention."""
    from extractor_mvp.citation_hop import _create

    out = []
    for m in mentions:
        if meter is not None:
            meter.label = (
                f"use:{m.tool_id}@{m.start}"  # one label per mention: attempts are retries
            )
        rec: dict[str, Any] = {
            "tool_id": m.tool_id,
            "display_name": m.display_name,
            "start": m.start,
            "end": m.end,
            "sentence": m.sentence,
            "version": m.version,
        }
        try:
            ans = _create(
                client,
                model,
                SOFTWARE_USE_PROMPT.format(tool=m.display_name, passage=m.passage),
                MentionUse,
            )
        except Exception as exc:
            rec.update(status="call_failed", error=f"{type(exc).__name__}: {exc}"[:300])
            out.append(rec)
            continue
        resolved = (
            bool(ans.use_quote) and resolve_quote(ans.use_quote or "", m.passage).span is not None
        )
        rec.update(
            status="ok",
            use=ans.use,
            use_quote=ans.use_quote,
            quote_resolved=resolved,
            fmri=ans.fmri,
            counts=ans.fmri == "yes" and resolved,
        )
        out.append(rec)
    return out


def tool_list(uses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per tool, in first-mention order: kept when any mention counts; the first version the scan
    read; the counting mention's use and quote."""
    by: dict[str, dict[str, Any]] = {}
    for u in uses:
        t = by.setdefault(
            u["tool_id"],
            {
                "tool_id": u["tool_id"],
                "display_name": u["display_name"],
                "version": None,
                "kept": False,
                "mentions": 0,
            },
        )
        t["mentions"] += 1
        t["version"] = t["version"] or u.get("version")
        if u.get("counts") and not t["kept"]:
            t.update(kept=True, use=u.get("use"), use_quote=u.get("use_quote"))
    return list(by.values())
