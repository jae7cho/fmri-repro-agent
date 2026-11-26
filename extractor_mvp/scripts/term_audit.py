#!/usr/bin/env python3
"""The standing audit of the vocabulary terms in stored records, no model call (B12 of
DESIGN_prompt_schema_2026-11; the audits of 2026-11-24 and D1 made standing).

Run it after every extraction run, before scoring. For the 39 vocabulary fields it reports:

1. **The table self-check.** Every alias, given as the wording, must resolve to its own member.
   D1 found 15 of 448 that did not; ``tests/test_resolver_d2b.py`` holds the same check as a test.
2. **Every stored wording** with the member today's resolver gives it and the papers it occurs
   in. A wording that resolves differently from one paper to the next has one row per member,
   and a row of its own where the member is the model's and not the table's (below).
   Flags: ``token`` (a bare member token, so the model's mapping and not the paper's words),
   ``partial`` (resolved through an alias that covers only part of the wording), ``by rule`` (a
   field rule chose the member, not an alias alone), ``completed`` (a list item that borrowed the
   head noun of the next item), ``sent elsewhere`` (a member token a dated ruling, or the detrend
   field's highest-order rule, resolves to another member), ``stale`` (the stored member differs
   from today's), ``the model's member`` (schema 0.8.0: the stored member is the model's reading
   of the words, ``model_mapped``, and the table resolves them to nothing; the row is an alias
   candidate) and ``the model read`` (the table resolves such words to another member). A term
   stored as ``other`` that is not ``model_mapped`` keeps that member: its "other (phrase)"
   wrapper is not in the record. The detrend field is resolved as the extractor resolves it: the
   term, then the highest order its quote names, for an extracted value. Since D2c that includes
   a value the checking pass supplied, when it resolved to an order (a supplied term that
   resolved to nothing, and a part of a varied value, do not go through that step).
3. **Unresolved wordings by how often they recur across papers.** A wording that recurs is the
   signal to add a member or an alias, as a dated change with tests. Aliases are not guessed ahead
   of the papers.
4. **The token trace.** How many values are bare tokens and, for each, whether an alias of its
   member is in the quote the model gave: ``in quote`` (and no alias of a member the record does
   not also hold for that field), ``competing`` (with such an alias), ``not in quote`` (a
   wording the table lacks, an inference, or a forced token; also a member that has no alias,
   unless the quote is as a whole the wording its rule reads). The member is the one today's
   resolver gives the token; the record's members are the stored ones and today's. The quote is
   read as the resolver reads a value: the longer alias wins, and the field's rules apply. A
   block reads the whole quote, as it reads a whole term: a member named properly in one clause
   counts as not in quote when another clause holds the blocked form ("rigid-body registration
   ... followed by non-rigid warping"). Such a token is listed to be read, which is the safe
   side. On the detrend field the highest-order rule decides: a lower order named beside the
   token's is no competitor, and a higher one always is. Quote spans are put in text order
   first; their stored order is the model's.

Held-out papers (liu_2005, tang_2025, wheaton_2004) are counted and never shown: no field,
wording or quote of theirs reaches the report. A record is held out when its file name contains
one of the three ids, whatever its case, prefix or suffix.

    uv run python scripts/term_audit.py --in results/arms_2026-11-15/B [--in DIR ...] [--out FILE]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import typing
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor_mvp import extractor as ex
from extractor_mvp.coverage_extractor import _DETREND_ORDER, detrend_highest_order
from extractor_mvp.coverage_fields import (
    COVERAGE_SPECS,
    TERM_RULES,
    resolve_shared,
    rule_hits,
    rules_name,
    rules_resolve,
)
from extractor_mvp.synonym_resolver import (
    SYNONYMS_BY_FIELD,
    _alias_regex,
    _alias_term,
    _fold_separators,
    members_named,
    repair_text,
    resolve_to_literal,
)

HELD_OUT = ("liu_2005", "tang_2025", "wheaton_2004")
SPAN_JOIN = " [...] "


def is_held_out(paper: str) -> bool:
    return any(h in paper.lower() for h in HELD_OUT)


@dataclasses.dataclass(frozen=True)
class Field:
    """One vocabulary field: 35 are resolved by ``extractor._resolve_term`` (the coverage calls),
    4 by ``coverage_fields.resolve_shared`` with the exact-member fallback (the shared call)."""

    dotted: str
    is_list: bool
    members: tuple[str, ...]
    synonyms: dict[str, list[str]]
    underspecified: list[str] | None
    literal_type: Any
    shared: bool

    @property
    def table(self) -> tuple[dict[str, list[str]], list[str] | None] | None:
        return (self.synonyms, self.underspecified) if self.synonyms else None


def vocabulary() -> dict[tuple[str, str], Field]:
    """Every vocabulary field, keyed (step kind, field id)."""
    out: dict[tuple[str, str], Field] = {}
    for s in COVERAGE_SPECS:
        if s.value_kind in ("term", "term_list"):
            out[(s.kind, s.field_id)] = Field(
                s.dotted,
                s.value_kind == "term_list",
                tuple(typing.get_args(s.literal_type)),
                s.synonyms or {},
                s.underspecified,
                s.literal_type,
                shared=False,
            )
    for _attr, field_id, dotted, literal_type, _t in ex._FIELD_SPECS:
        if literal_type is not None and field_id in SYNONYMS_BY_FIELD:
            syns, under = SYNONYMS_BY_FIELD[field_id]
            kind = dotted.split(".", 1)[0]
            out[(kind, field_id)] = Field(
                dotted, False, tuple(typing.get_args(literal_type)), syns, under, literal_type, True
            )
    return out


DETREND = "nuisance_regression.detrend"


def resolve(
    field: Field,
    words: list[str],
    value_context: float | None = None,
    rule_quote: str | None = None,
    raise_only: bool = False,
) -> list[tuple[str | None, str]]:
    """(member, resolution) for each stored item, as the extractor resolves them today.
    ``rule_quote`` is the field's quote as the extractor joins it (stored order, one space): the
    detrend field takes the highest order that quote names (coverage_extractor, 2026-10-28). The
    extractor runs that step after resolution, on an extracted value: the coverage call's, and
    since D2c (2026-11-25) one the checking pass supplied (``checker_supplied``), which went
    without it until then. For a supplied value the caller sets ``raise_only``: promote() raises
    an order and leaves a term that resolved to nothing as it is. The step never runs on a part
    of a varied value; for that the caller passes no quote. The four fields of the shared call
    read their table and then their blocks (``coverage_fields.resolve_shared``, D2c)."""
    if field.shared:
        out: list[tuple[str | None, str]] = []
        for w in words:
            r = resolve_shared(field.dotted, w, value_context)
            if r.status == "resolved":
                out.append((r.resolved, "resolved"))
            elif w in field.members:
                out.append((w, "resolved"))
            else:
                status = "underspecified" if r.status == "underspecified" else "unrecognized"
                out.append((None, status))
        return out
    if field.is_list:
        terms = ex._resolve_term_list(words, field.literal_type, field.table, field.dotted)
    else:
        terms = [ex._resolve_term(w, field.literal_type, field.table, field.dotted) for w in words]
    resolved = [(t.resolved, str(t.resolution)) for t in terms]
    unresolved_and_supplied = raise_only and len(resolved) == 1 and resolved[0][0] is None
    if (
        field.dotted == DETREND
        and rule_quote is not None
        and len(resolved) == 1
        and not unresolved_and_supplied
    ):
        highest = detrend_highest_order(resolved[0][0], rule_quote)
        if highest != resolved[0][0]:
            resolved = [(highest, "resolved")]
    return resolved


def gated_value(field: Field, member: object) -> float | None:
    """The sibling value a member's "@VALUE" aliases require, when they all require the same one.
    The extractor resolves the intensity convention with the model's raw intensity value, which a
    record does not keep when that value failed its own check; the stored member tells it."""
    values = {a.rpartition("@")[2] for a in field.synonyms.get(str(member), []) if "@" in a}
    try:
        return float(values.pop()) if len(values) == 1 else None
    except ValueError:
        return None


def self_check() -> tuple[int, list[tuple[str, str, str, list[str | None]]]]:
    """(aliases checked, the ones that do not resolve to their own member)."""
    checked = 0
    failures: list[tuple[str, str, str, list[str | None]]] = []
    for field in vocabulary().values():
        for member, aliases in field.synonyms.items():
            for alias in aliases:
                checked += 1
                term, _, value = alias.rpartition("@") if "@" in alias else (alias, "", "")
                context = float(value) if value else None
                if field.is_list:
                    items = ex._field_items(field.dotted, term, field.literal_type, field.table)
                else:
                    items = [term]
                got = [m for m, _resolution in resolve(field, items, context)]
                if got != [member]:
                    failures.append((field.dotted, member, alias, got))
    return checked, failures


# --- reading records --------------------------------------------------------------------------


def _span_position(span: dict[str, Any]) -> tuple[int, int]:
    for part, key in ((0, "span_in_full_paper"), (1, "span_in_supplement"), (0, "span_in_slice")):
        if isinstance(span.get(key), dict):
            return (part, int(span[key].get("start", 0)))
    return (0, int(span.get("start", 0) or 0))


def quote_in_text_order(spans: list[dict[str, Any]]) -> str:
    """The spans' text joined in the order they stand in the paper. A record stores them in the
    order the model gave them, which differed from text order in 20 of the 55 multi-span cases of
    D1 and misled two codings about order words."""
    return SPAN_JOIN.join(str(s.get("text", "")) for s in sorted(spans, key=_span_position))


@dataclasses.dataclass(frozen=True)
class Value:
    """One stored value of a vocabulary field: its items, its quote and where it came from."""

    paper: str
    held_out: bool
    field: Field
    items: tuple[dict[str, Any], ...]
    quote: str
    value_context: float | None
    #: every member the record holds for this field, over all its parts: as stored, and as
    #: today's resolver gives them (a stale record's other item is not a competitor)
    returned: frozenset[str]
    #: the quote as the extractor joins it, for an extracted value; None for a part of a varied one
    rule_quote: str | None
    #: (member, resolution) of each item today
    now: tuple[tuple[str | None, str], ...]


def iter_values(record: dict[str, Any], paper: str) -> Iterator[Value]:
    fields = vocabulary()
    held = is_held_out(paper)
    holder = record if "preprocessing" in record else (record.get("extraction_json") or {})
    for step in ((holder.get("preprocessing") or {}).get("steps")) or []:
        kind = step.get("kind")
        context = None
        if kind == "intensity_normalization":
            number = ((step.get("value") or {}).get("extraction") or {}).get("value")
            context = float(number) if isinstance(number, (int, float)) else None
        for field_id, pf in step.items():
            field = fields.get((kind, field_id))
            if field is None or not isinstance(pf, dict):
                continue
            ext = pf.get("extraction") or {}
            groups = [(ext.get("value"), ext.get("spans") or [], False)]
            groups += [
                (v.get("value"), v.get("spans") or [], True)
                for v in ext.get("variants") or []
                if isinstance(v, dict)
            ]
            parts = [
                (
                    tuple(
                        it
                        for it in (value if isinstance(value, list) else [value])
                        if isinstance(it, dict) and "verbatim" in it
                    ),
                    spans,
                    is_part,
                )
                for value, spans, is_part in groups
            ]
            read = []
            for items, spans, is_part in parts:
                if not items:
                    continue
                value_context = context
                if value_context is None and field.shared:
                    value_context = gated_value(field, items[0].get("resolved"))
                # the quote the detrend rule reads: see resolve()
                rule_quote = None if is_part else " ".join(str(s.get("text", "")) for s in spans)
                supplied = bool(ext.get("checker_supplied"))
                words = [str(it["verbatim"]) for it in items]
                now = tuple(resolve(field, words, value_context, rule_quote, supplied))
                if supplied and len(now) == 1 and now[0][0] is None:
                    rule_quote = None  # the rule did not read this value: see resolve()
                read.append((items, spans, value_context, rule_quote, now))
            returned = frozenset(
                [str(it["resolved"]) for items, *_ in read for it in items if it.get("resolved")]
                + [m for *_, now in read for m, _resolution in now if m]
            )
            for items, spans, value_context, rule_quote, now in read:
                quote = quote_in_text_order(spans)
                yield Value(
                    paper, held, field, items, quote, value_context, returned, rule_quote, now
                )


def members_in_quote(field: Field, quote: str, value_context: float | None) -> set[str]:
    """The members the quote names, read as the resolver reads a value: an alias inside a longer
    alias of another member does not count, a member the field's rules block on this text is
    dropped, and a member the rules require or find named (an SPM release) is added.

    A member with no alias is not found this way. The ones schema 0.8.0 adds (12param,
    global_signal, the method's fieldmap_less) are resolved by a rule that reads a whole wording:
    their bare token counts as in the quote only when the quote is, as a whole, such a wording,
    and like ``other`` as not in the quote otherwise."""
    named = set(members_named(quote, field.synonyms, value_context))
    rules = TERM_RULES.get(field.dotted)
    if rules:
        named -= {m for m in named if any(rule_hits(p, quote) for p in rules.block.get(m, ()))}
        named |= set(rules_resolve(field.dotted, quote)[:1])  # the one the resolver would take
        named |= rules_name(field.dotted, quote)
    return named


def whole_alias(field: Field, member: str, wording: str) -> bool:
    """Whether some alias of the member covers the whole wording (so the match is not partial)."""
    folded = _fold_separators(repair_text(wording).lower())
    for alias in field.synonyms.get(member, []):
        term = _alias_term(alias.rpartition("@")[0] if "@" in alias else alias, None)
        if term is not None and _alias_regex(term).fullmatch(folded):
            return True
    return False


# --- the audit --------------------------------------------------------------------------------


@dataclasses.dataclass
class Audit:
    records: int = 0
    #: (dotted, wording, member today) -> {"papers", "resolution", "flags", "stale", "model"}
    wordings: dict[tuple[str, str, str | None], dict[str, Any]] = dataclasses.field(
        default_factory=dict
    )
    #: (dotted, wording, the model's member) -> the same row, for a ``model_mapped`` term whose
    #: words the table resolves to nothing. Kept apart from ``wordings``: the same words can stand
    #: under the same member without the model in another paper (a stored "other (phrase)", a
    #: list item the table completes), and that row has flags of its own.
    model_wordings: dict[tuple[str, str, str | None], dict[str, Any]] = dataclasses.field(
        default_factory=dict
    )
    #: dotted -> Counter of trace categories, non-held-out
    trace: dict[str, Counter[str]] = dataclasses.field(default_factory=lambda: defaultdict(Counter))
    #: token values whose member has no alias in the quote, or a competing one: non-held-out
    trace_cases: list[tuple[str, str, str, str, str]] = dataclasses.field(default_factory=list)
    held_out: Counter[str] = dataclasses.field(default_factory=Counter)


def flags(field: Field, wording: str, member: str | None, alone: str | None) -> list[str]:
    """``alone`` is the member the wording resolves to with no neighbouring list item."""
    if wording in field.members:
        return ["token", "sent elsewhere"] if member not in (None, wording) else ["token"]
    if member is None or member == "other":
        return []
    if alone != member:
        return ["completed"]
    table = resolve_to_literal(wording, field.synonyms, field.underspecified)
    if not field.shared and table.resolved != member:
        return ["by rule"]
    return [] if whole_alias(field, member, wording) else ["partial"]


def audit(dirs: list[Path]) -> Audit:
    a = Audit()
    for d in dirs:
        for f in sorted((d / "papers").glob("*.json")):
            record = json.loads(f.read_text(encoding="utf-8"))
            a.records += 1
            for v in iter_values(record, f.stem):
                words = [str(it["verbatim"]) for it in v.items]
                in_quote = members_in_quote(v.field, v.quote, v.value_context)
                for it, word, (resolved_now, resolution_now) in zip(
                    v.items, words, v.now, strict=True
                ):
                    member, resolution = resolved_now, resolution_now
                    stored = it.get("resolved")
                    mapped = it.get("resolution") == "model_mapped" and stored is not None
                    if stored == "other" and word != "other" and not mapped:
                        # "other (phrase)" is stored as the phrase alone; the extractor resolved
                        # it to other, and the phrase cannot be resolved again without its wrapper
                        member, resolution = "other", "resolved"
                    # schema 0.8.0 (C7): the stored member is the model's reading of the words.
                    # The record is not stale for that, and reresolve_terms keeps it. Where the
                    # table resolves the words to nothing, the row stands under the model's
                    # member, an alias candidate; where it resolves them to another member, the
                    # row stands under the table's and says what the model read. Its words are
                    # the paper's, so it is not an "other (phrase)" term whose wrapper is lost.
                    by_model = mapped and resolved_now is None
                    if by_model:
                        member, resolution = str(stored), "model_mapped"
                    is_token = word in v.field.members
                    category = None
                    if is_token:
                        # the token's own member today: a dated ruling may have moved it since the
                        # record was stored (volterra is friston24). Read without the quote, so
                        # the detrend rule does not grade the member it took from that quote.
                        own = resolve(v.field, [word], v.value_context)[0][0]
                        others = {m for m in in_quote if m != own and m not in v.returned}
                        if v.field.dotted == DETREND and own in _DETREND_ORDER:
                            # the highest-order rule: a lower order named beside the token's is no
                            # competitor, and a higher one is, whatever member the record holds
                            # (the rule gave it that member; the model gave the token)
                            rank = _DETREND_ORDER.index
                            others = {
                                m for m in in_quote if m in _DETREND_ORDER and rank(m) > rank(own)
                            }
                        if own not in in_quote:
                            category = "not in quote"
                        else:
                            category = "competing" if others else "in quote"
                    if v.held_out:
                        a.held_out["terms"] += 1
                        a.held_out["tokens"] += is_token
                        a.held_out["unresolved"] += member is None
                        if category:
                            a.held_out[category] += 1
                        continue
                    alone = resolve(v.field, [word], v.value_context, v.rule_quote)[0][0]
                    # One row would take its flags from whichever paper was read first (the
                    # fifth review), so the model's member has a table of its own.
                    rows = a.model_wordings if by_model else a.wordings
                    row = rows.setdefault(
                        (v.field.dotted, word, member),
                        {
                            "papers": set(),
                            "resolution": resolution,
                            "flags": ["the model's member"]
                            if by_model
                            else flags(v.field, word, member, alone),
                            "stale": set(),
                            "model": set(),
                        },
                    )
                    row["papers"].add(v.paper)
                    if stored != member:
                        row["model" if mapped else "stale"].add(str(stored))
                    a.trace[v.field.dotted]["values"] += 1
                    if category:
                        a.trace[v.field.dotted][category] += 1
                        if category != "in quote":
                            a.trace_cases.append((v.field.dotted, v.paper, word, category, v.quote))
    return a


# --- the report -------------------------------------------------------------------------------


def _cell(text: object, limit: int = 110) -> str:
    flat = " ".join(str(text).split()).replace("|", "/")
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def render(a: Audit, dirs: list[Path], quotes: bool = False) -> str:
    checked, failures = self_check()
    lines = [
        "# Term audit",
        "",
        "Record sets: " + ", ".join(f"`{d}`" for d in dirs),
        f"Records read: {a.records}. Held-out papers are counted at the end and never shown.",
        "",
        "## 1. Table self-check",
        "",
        f"Aliases checked: {checked}. Not resolving to their own member: {len(failures)}.",
        "",
    ]
    if failures:
        lines += ["| field | member | alias | resolves to |", "|---|---|---|---|"]
        lines += [f"| {d} | {m} | {_cell(al)} | {got} |" for d, m, al, got in failures]
        lines.append("")
    rules = ", ".join(sorted(TERM_RULES)) or "none"
    lines += [f"Fields with term rules: {rules}.", "", "## 2. Stored wordings, by field", ""]
    by_field: dict[str, list[tuple[str, str | None, dict[str, Any]]]] = defaultdict(list)
    # the table's rows, then the model's: the sort below is stable, so where the same words stand
    # under the same member in as many papers, the table's row comes first (more papers come first)
    for (dotted, wording, member), row in [*a.wordings.items(), *a.model_wordings.items()]:
        by_field[dotted].append((wording, member, row))
    for dotted in sorted(by_field):
        lines += [
            f"### {dotted}",
            "",
            "| wording | member today | papers | flags |",
            "|---|---|---|---|",
        ]
        for wording, member, row in sorted(
            by_field[dotted], key=lambda x: (-len(x[2]["papers"]), x[0], str(x[1]))
        ):
            notes = list(row["flags"])
            if row["stale"]:
                notes.append("stale: stored " + ", ".join(sorted(row["stale"])))
            if row["model"]:
                notes.append("the model read " + ", ".join(sorted(row["model"])))
            shown = member if member is not None else f"({row['resolution']})"
            lines.append(
                f"| {_cell(wording)} | {shown} | {len(row['papers'])} | {'; '.join(notes)} |"
            )
        lines.append("")
    lines += [
        "## 3. Unresolved wordings, most recurring first",
        "",
        "| field | wording | papers | which |",
        "|---|---|---|---|",
    ]
    unresolved = [(k, r) for k, r in a.wordings.items() if k[2] is None]
    for (dotted, wording, _member), row in sorted(
        unresolved, key=lambda x: (-len(x[1]["papers"]), x[0][0], x[0][1])
    ):
        papers = sorted(row["papers"])
        shown = ", ".join(papers[:4]) + (" ..." if len(papers) > 4 else "")
        lines.append(f"| {dotted} | {_cell(wording)} | {len(papers)} | {shown} |")
    lines += [
        "",
        "## 4. Token trace",
        "",
        "A token value is a bare member token in the slot for the paper's words. For each, is an",
        "alias of its member in the quote the model gave? `values` counts list items one by one.",
        "A member with no alias has none to find: `other`, and the members a whole-wording rule",
        "resolves (`12param`, `global_signal`, the method's `fieldmap_less`). The token of one of",
        "these counts as in quote only when the quote is, as a whole, the wording its rule reads.",
        "",
        "| field | values | tokens | in quote | competing | not in quote |",
        "|---|---|---|---|---|---|",
    ]
    total: Counter[str] = Counter()
    for dotted in sorted(a.trace):
        c = a.trace[dotted]
        tokens = c["in quote"] + c["competing"] + c["not in quote"]
        total.update({**c, "tokens": tokens})
        lines.append(
            f"| {dotted} | {c['values']} | {tokens} | {c['in quote']} | {c['competing']} | "
            f"{c['not in quote']} |"
        )
    lines.append(
        f"| total | {total['values']} | {total['tokens']} | {total['in quote']} | "
        f"{total['competing']} | {total['not in quote']} |"
    )
    lines += ["", "Token values to read (competing, or not in quote):", ""]
    head = "| field | paper | token | trace |" + (" quote |" if quotes else "")
    lines += [head, "|---|---|---|---|" + ("---|" if quotes else "")]
    for dotted, paper, token, category, quote in sorted(a.trace_cases):
        tail = f" {_cell(quote, 220)} |" if quotes else ""
        lines.append(f"| {dotted} | {paper} | {token} | {category} |{tail}")
    h = a.held_out
    lines += [
        "",
        "## 5. Held-out papers, counts only",
        "",
        f"Terms {h['terms']}; bare tokens {h['tokens']}; unresolved today {h['unresolved']}; "
        f"tokens in quote {h['in quote']}, competing {h['competing']}, "
        f"not in quote {h['not in quote']}.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--in", dest="dirs", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--quotes", action="store_true", help="show each listed token's quote")
    args = ap.parse_args(argv)
    for d in args.dirs:
        if not (d / "papers").is_dir():
            ap.error(f"--in {d}: no papers/ folder")
    text = render(audit(args.dirs), args.dirs, args.quotes)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
