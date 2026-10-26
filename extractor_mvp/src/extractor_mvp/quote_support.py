"""Quote-support checks for the seven step fields, and the matcher the motion check shares.

``docs/design/DELTA_value_in_quote_step_fields.md`` §5 — the author's rulings of 2026-10-26:

1. **Literal fields** (``target_space``, ``surface_registration``, ``target_surface``,
   ``intensity_normalization.convention``, ``temporal_standardization.method``): the value is
   supported when **an alias of the returned value, taken whole, occurs in the repaired quote**. The
   prompt asks the model for canonical tokens (``extractor.py`` "Canonical values: ..."), so a
   value-in-quote test would reject correct extractions — 7 to 8 on the stored record.
2. **Numeric fields** (``resolution_mm``, ``intensity_normalization.value``): the value's number occurs
   in the quote, **digit-exact** — equal as numbers with no tolerance ("3" and "3.0" are the same
   number; "3" is not supported by "30" or "3.5"; "1,000" is 1000).
3. ``temporal_standardization.method`` gets its table (``synonym_resolver.TS_METHOD_SYNONYMS``, build
   2 §4c, built 2026-10-26 for this check), and the check runs on the span resolver's repaired text:
   :func:`tokens` normalises through ``normalize_with_offset_map``, which is what repairs line-break
   hyphenation (liu_2013's "normal-\\nized").
4. **Aliases are never split into first-use variants here.** Split, ``MNI152 (FSL)`` would yield a bare
   ``MNI152`` and a quote saying only MNI152 would support ``MNI152NLin6Asym``.
5. The word-form matcher is **digit-exact**: a token containing a digit must match exactly; word forms
   are tolerated for alphabetic tokens only (``realignment`` / ``realigned``). ``motion_guard`` uses
   the same matcher, tightened in the same change (0 of 160 resolved motion draws change).
6. A rejected value is ``MissingFromPaper`` with reason :data:`VALUE_UNSUPPORTED`, a member of
   ``cobidas._UNVERIFIABLE_GAP_BASES``, so it renders *examined; could not verify*, never *not reported*.

Which aliases count as "an alias of the returned value":

* a value the resolver mapped to a canonical member → that member's table entry (the member's own
  token is included, since it is a name of the value);
* an ``underspecified`` value (a family term such as "MNI") → the field's underspecified list;
* an ``unrecognized`` value (free text the table does not know) → the value itself, whole.

Everything here is pure and firewall-clean: no KB, no model, only the model's value and the text the
resolver located.
"""

from __future__ import annotations

import re

from extractor_mvp.span_resolver import normalize_with_offset_map
from extractor_mvp.synonym_resolver import (
    INTENSITY_CONVENTION_SYNONYMS,
    SURFACE_REGISTRATION_SYNONYMS,
    SURFACE_REGISTRATION_UNDERSPECIFIED,
    TARGET_SPACE_SYNONYMS,
    TARGET_SPACE_UNDERSPECIFIED,
    TARGET_SURFACE_SYNONYMS,
    TS_METHOD_SYNONYMS,
)

#: Reason base for a step-field value the quote does not support (ruling 6).
VALUE_UNSUPPORTED = "value_unsupported_by_quote"

#: The five Literal fields, by dotted path, with the table and underspecified list that define
#: "an alias of the returned value" (ruling 1). Keyed on the DOTTED path, not the bare field id:
#: ``method`` is the bare id of two fields, and the motion field is deliberately absent here.
SUPPORT_TABLES: dict[str, tuple[dict[str, list[str]], list[str] | None]] = {
    "spatial_normalization.target_space": (TARGET_SPACE_SYNONYMS, TARGET_SPACE_UNDERSPECIFIED),
    "surface_projection.surface_registration": (
        SURFACE_REGISTRATION_SYNONYMS,
        SURFACE_REGISTRATION_UNDERSPECIFIED,
    ),
    "surface_projection.target_surface": (TARGET_SURFACE_SYNONYMS, None),
    "intensity_normalization.convention": (INTENSITY_CONVENTION_SYNONYMS, None),
    "temporal_standardization.method": (TS_METHOD_SYNONYMS, None),
}

#: The two numeric fields (ruling 2).
NUMERIC_FIELDS: frozenset[str] = frozenset(
    {"spatial_normalization.resolution_mm", "intensity_normalization.value"}
)

#: Suffixes stripped once, longest first, only when at least ``_MIN_STEM`` characters remain, and
#: only from alphabetic tokens. Chosen for the word forms seen in preprocessing prose; not a
#: general stemmer.
_SUFFIXES: tuple[str, ...] = ("ation", "ment", "ing", "ies", "ied", "ed", "es", "ly", "s")
_MIN_STEM = 4
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")


def tokens(s: str) -> list[str]:
    """Lower-cased, NFKD-folded alphanumeric tokens of the REPAIRED text.

    ``normalize_with_offset_map`` is the span resolver's own normaliser: it folds ligatures and
    drops line-wrap soft hyphens and pypdf's split-measurement whitespace, so a quote mangled by the
    PDF text layer is matched as the resolver would read it.
    """
    return re.findall(r"[a-z0-9]+", normalize_with_offset_map(s.lower())[0])


def _stem(tok: str) -> str:
    # "es" is a plural/verb ending only after a sibilant (matches, boxes); otherwise the ending is
    # "s" and the e belongs to the stem (images -> image, not imag).
    if tok.endswith("es") and not tok[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return tok[:-1] if len(tok) - 1 >= _MIN_STEM else tok
    for suf in _SUFFIXES:
        if tok.endswith(suf) and len(tok) - len(suf) >= _MIN_STEM:
            return tok[: -len(suf)]
    return tok


def token_equivalent(a: str, b: str) -> bool:
    """Two tokens are the same word when equal, or — for ALPHABETIC tokens only — when they are
    inflections of one stem: either both stems are equal (``realignment`` / ``realigned`` →
    ``realign``; ``spatially`` / ``spatial``), or BOTH tokens shed a suffix and their stems share a
    common prefix covering all but one character of the shorter (``coregistration`` → ``coregistr``,
    ``coregistered`` → ``coregister``). A bare prefix is NOT equivalence: ``mode`` is not ``model``.
    A token with a digit in it is an identifier, and identifiers match exactly: ``mni152`` is not
    ``mni152nlin6asym`` and ``spm`` is not ``spm12``. Tokens shorter than ``_MIN_STEM`` match exactly."""
    if a == b:
        return True
    if any(ch.isdigit() for ch in a) or any(ch.isdigit() for ch in b):
        return False
    if len(a) < _MIN_STEM or len(b) < _MIN_STEM:
        return False
    sa, sb = _stem(a), _stem(b)
    if sa == sb:
        return True
    if sa == a or sb == b:  # at least one token is an uninflected word: no further tolerance
        return False
    short = min(len(sa), len(sb))
    common = 0
    for x, y in zip(sa, sb, strict=False):
        if x != y:
            break
        common += 1
    return common >= _MIN_STEM and common >= short - 1


def _prefix_or_equivalent(a: str, b: str) -> bool:
    """``token_equivalent``, or ``a`` is the start of ``b``: used only for an UNDERSPECIFIED family term,
    so that "MNI152" is supported by a quote whose identifier is "MNI152NLin6Asym". That is the safe
    direction — the value is less specific than its quote — and the reverse is never allowed."""
    return token_equivalent(a, b) or (len(a) >= 3 and b.startswith(a))


def phrase_in_quote(phrase: str, quote: str, *, family_term: bool = False) -> bool:
    """True iff the phrase's tokens occur in the quote as one contiguous run, token-equivalent.

    The phrase is taken WHOLE — no first-use-variant splitting (ruling 4). With ``family_term`` a
    token may also be the start of the quote's token (see :func:`_prefix_or_equivalent`).
    """
    p = tokens(phrase)
    q = tokens(quote)
    if not p or not q or len(p) > len(q):
        return False
    eq = _prefix_or_equivalent if family_term else token_equivalent
    return any(all(eq(p[j], q[i + j]) for j in range(len(p))) for i in range(len(q) - len(p) + 1))


def number_in_quote(value: float, quote: str) -> bool:
    """True iff a number in the quote equals the value exactly (ruling 2). Thousands separators are
    read as part of the number; nothing else is normalised and no tolerance is applied."""
    for tok in _NUMBER.findall(_THOUSANDS.sub("", quote)):
        try:
            if float(tok) == value:
                return True
        except ValueError:
            continue
    return False


def _alias_text(alias: str) -> str:
    """An intensity-convention alias carries a ``@<value>`` context marker; the number is the
    numeric field's own check, so only the phrase is matched here."""
    return alias.split("@", 1)[0]


def literal_value_supported(
    dotted: str, verbatim: str, resolved: str | None, resolution: str, quote: str
) -> bool:
    """Ruling 1 for one Literal field. See the module docstring for which aliases count."""
    table, underspecified = SUPPORT_TABLES[dotted]
    if resolved is not None and resolved in table:
        candidates = [resolved, *table[resolved]]
    elif resolved is not None:
        # A Literal member with no table entry -- ``other`` on every field, and any member a table
        # does not list. "Other" names nothing the quote could carry, so there is no alias to test;
        # the value passes through unchecked. Recorded as a known limit of ruling 1, not a hole
        # the check pretends to close: a spurious ``other`` asserts no specific value.
        return True
    elif resolution == "underspecified":
        # A family term is supported by the family term OR by a longer identifier that begins with
        # it: the value is then LESS specific than its quote, which asserts nothing the quote does not.
        return any(
            phrase_in_quote(_alias_text(c), quote, family_term=True) for c in underspecified or []
        )
    else:
        candidates = [verbatim]
    return any(phrase_in_quote(_alias_text(c), quote) for c in candidates)


def step_value_supported(dotted: str, value: object, quote: str) -> bool | None:
    """The check ``_process_field`` applies to an EXTRACTED step field.

    Returns ``None`` for a field this check does not cover (the motion field has its own; see
    ``motion_guard``), ``True`` when supported, ``False`` when the value must be demoted.
    """
    if dotted in NUMERIC_FIELDS:
        try:
            return number_in_quote(float(value), quote)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
    if dotted in SUPPORT_TABLES:
        verbatim = getattr(value, "verbatim", None)
        resolved = getattr(value, "resolved", None)
        resolution = getattr(value, "resolution", "unrecognized")
        if verbatim is None:
            return False
        return literal_value_supported(dotted, str(verbatim), resolved, str(resolution), quote)
    return None
