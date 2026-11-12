"""Joining two spellings of one part (Stage 2c, the author's item 3, 2026-11-11).

The same-string rule (``normalize_applies_to``) keeps "global connectome (DCw and ECw)" and "global
connectome metrics (DCw, ECw)" apart, though chen_2015 means one part by both. Two part names are
joined when, after dropping punctuation, parentheses and stopwords, one name's content words are a
subset of the other's. Three guards, each a case where a subset does not mean the same part:

- two names that one field carries side by side are never joined (the extractor gave each its own
  value, so the paper treats them as different parts);
- a name whose subset relation reaches more than one chain of names is ambiguous and joins nothing:
  every name in a joined group must be subset-comparable with every other;
- a name with no content words, and the compared-models entry (fork C2), join nothing.

Every join is returned as a ``PartJoin`` so the record logs it and the header line shows it. The
spelling kept is the first one met in render order (the steps' fields in schema order, then the
step-order parts). The paper's own words stay on each value; only grouping changes.

Callers: render.py (the "Values differ by" header), pseudocode.py (one block or table row per
part), scripts/score_smoothing_filtering.py (one stream per part), batch.py (the record's
``part_joins``)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from fmri_repro.spec.provenance import COMPARED_MODELS, normalize_applies_to

#: Words that never distinguish two parts. "a" is not among them: it is also a part's label
#: ("Model A", "session A"), and dropping it would join "Model A" into "Model B".
STOPWORDS = frozenset(
    {"an", "the", "and", "or", "of", "for", "in", "on", "to", "with", "by", "at", "from", "as"}
)


def content_words(words: str) -> frozenset[str]:
    """The name's words with punctuation, parentheses and stopwords dropped, case folded."""
    s = unicodedata.normalize("NFKC", words or "").casefold().replace("&", " and ")
    return frozenset(t for t in re.split(r"[^\w]+", s) if t and t not in STOPWORDS)


@dataclass(frozen=True)
class PartJoin:
    """``joined`` (the paper's words) is shown and grouped as ``into`` (the spelling kept)."""

    joined: str
    into: str
    #: the two names' content words, so the record shows why
    joined_words: tuple[str, ...]
    into_words: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PartRefused:
    """A subset relation that was not joined, and why."""

    names: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_joins(
    fields: Sequence[Iterable[str]],
) -> tuple[list[PartJoin], list[PartRefused]]:
    """``fields``: per field (and the step-order parts as one more), the parts it names, in render
    order. Returns the joins and the refused groups."""
    order: dict[str, str] = {}  # normalized key -> first spelling
    together: set[frozenset[str]] = set()
    for names in fields:
        keys = []
        for n in names:
            k = normalize_applies_to(n)
            if k == COMPARED_MODELS:
                continue
            order.setdefault(k, n)
            keys.append(k)
        for i, a in enumerate(keys):
            for b in keys[i + 1 :]:
                if a != b:
                    together.add(frozenset((a, b)))
    keys = list(order)
    cw = {k: content_words(order[k]) for k in keys}

    def comparable(a: str, b: str) -> bool:
        return bool(cw[a]) and bool(cw[b]) and (cw[a] <= cw[b] or cw[b] <= cw[a])

    # components of the subset relation
    parent = {k: k for k in keys}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if comparable(a, b):
                parent[find(b)] = find(a)
    groups: dict[str, list[str]] = {}
    for k in keys:
        groups.setdefault(find(k), []).append(k)
    joins: list[PartJoin] = []
    refused: list[PartRefused] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        names = tuple(order[m] for m in members)
        pairs = [(a, b) for i, a in enumerate(members) for b in members[i + 1 :]]
        if any(frozenset(p) in together for p in pairs):
            refused.append(PartRefused(names, "one field names two of them side by side"))
            continue
        if not all(comparable(a, b) for a, b in pairs):
            refused.append(PartRefused(names, "ambiguous: not every pair is a subset"))
            continue
        keep = members[0]
        for m in members[1:]:
            joins.append(
                PartJoin(order[m], order[keep], tuple(sorted(cw[m])), tuple(sorted(cw[keep])))
            )
    return joins, refused


def join_map(joins: Iterable[PartJoin]) -> dict[str, str]:
    """normalized key of a joined name -> normalized key of the spelling kept."""
    return {normalize_applies_to(j.joined): normalize_applies_to(j.into) for j in joins}


def part_key(applies_to: str, mapping: dict[str, str]) -> str:
    """The grouping key of a part: its normalized words, or the kept spelling's when joined."""
    k = normalize_applies_to(applies_to)
    return mapping.get(k, k)


def fields_of(rows: Sequence[Any], preprocessing: Any = None) -> list[list[str]]:
    """The part names per field of flattened rows (render.FieldRow), then the step-order parts."""
    out: list[list[str]] = []
    for r in rows:
        if getattr(r, "state", None) == "VARIED":
            out.append([v.applies_to for v in r.variants or []])
    order_parts = getattr(preprocessing, "step_order_parts", None) or []
    if order_parts:
        out.append([p.applies_to for p in order_parts])
    return out


def joins_for(rows: Sequence[Any], preprocessing: Any = None) -> list[PartJoin]:
    return compute_joins(fields_of(rows, preprocessing))[0]


def record_entry(rows: Sequence[Any], preprocessing: Any = None) -> dict[str, Any]:
    """The record's ``part_joins`` entry: every join and every refused group."""
    joins, refused = compute_joins(fields_of(rows, preprocessing))
    return {
        "rule": "content-word subset after dropping punctuation, parentheses and stopwords",
        "joins": [j.as_dict() for j in joins],
        "refused": [r.as_dict() for r in refused],
    }
