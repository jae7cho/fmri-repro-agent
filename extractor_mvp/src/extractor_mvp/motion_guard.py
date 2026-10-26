"""Post-check for ``motion_correction.method`` — ``docs/design/DELTA_value_in_quote_motion.md`` §4.

Rulings 1-4 of 2026-10-26, implemented as recorded:

1. **A post-check on the processed layer; no reask.** :func:`motion_post_check` is pure. It is
   applied by ``extractor.extract_motion_method`` AFTER ``_process_field`` has resolved the quote,
   and it compares the model's OWN value with the model's OWN quote (firewall-clean: no KB, no
   paper text beyond what the model returned). The raw ``FieldExtractionResult`` is untouched, so
   v1, v2, the same-day A/B and every later run stay comparable on the raw layer.
2-3. **Every motion value, with an inflection-tolerant match.** Not tool names only: scoping on the
   scoring heuristic's tool lists would give the guard and the scorer one list's blind spots. The
   match tolerates word forms (``realignment`` against a quote that says ``realigned``) — see
   :func:`_stem_equivalent` for the exact rule; it is deliberately small and legible.
4. **CompCor, ICA-FIX and ICA-AROMA are routed off the motion method in code.** COBIDAS D.3 p.57
   lists them under *Artifact and structured noise removal*. The 2026-10-22 stanza edit said so in
   prose and derosa_2025 returned ``ICA-AROMA`` on all 20 draws across both stanza versions; the
   prompt cannot steer the model off them, so code does.

**Order.** Support is checked first, routing second: a structured-noise tool that is NOT in the
quoted sentence is an unsupported value before it is a routed one, and the more general finding
is the one reported.

**Recorded limit** (DELTA §4): a tool quoted from its own host sentence — a quote of "performed
with SPM12 ..." supports ``SPM12`` — passes here, binding or no binding. That remains CALL 1's job.

**Reasons.** Both are gap reasons on a ``MissingFromPaper`` field and are members of
``cobidas._UNVERIFIABLE_GAP_BASES``, so the motion row renders as *examined; the extractor could
not verify what it found*, never as *not reported* (the conditional-row rule,
``DELTA_conditional_row_unverifiable.md``). A reason left out of that set would render the row as
if the paper had said nothing.
"""

from __future__ import annotations

import re

from extractor_mvp.span_resolver import _first_use_variants, normalize_with_offset_map

#: Base of the reason emitted when the value is not in its own quote (ruling 1-3).
MOTION_VALUE_UNSUPPORTED = "motion_value_unsupported_by_quote"
#: Base of the reason emitted when the value names a D.3 structured-noise tool (ruling 4). The
#: emitted reason is ``f"{MOTION_VALUE_ROUTED}:{tool}"`` with ``tool`` one of
#: :data:`STRUCTURED_NOISE_TOOLS`'s values.
MOTION_VALUE_ROUTED = "motion_value_routed_structured_noise"

#: COBIDAS D.3 p.57, "Artifact and structured noise removal — Name of software/method used (e.g.
#: CompCor, ICA-FIX, ICA-AROMA, etc.)". Keyed on the normalised token sequence the name produces;
#: aCompCor / tCompCor are CompCor variants and are listed so a variant cannot slip past the row.
STRUCTURED_NOISE_TOOLS: dict[tuple[str, ...], str] = {
    ("compcor",): "compcor",
    ("acompcor",): "compcor",
    ("tcompcor",): "compcor",
    ("ica", "fix"): "ica_fix",
    ("ica", "aroma"): "ica_aroma",
}

#: Suffixes stripped once, longest first, and only when at least ``_MIN_STEM`` characters remain.
#: Chosen for the word forms seen in motion-correction prose (realign-ment/-ed/-ing,
#: coregist-ration/-ered, spatial-ly, image-s). Deliberately not a general stemmer.
_SUFFIXES: tuple[str, ...] = ("ation", "ment", "ing", "ies", "ied", "ed", "es", "ly", "s")
_MIN_STEM = 4


def _tokens(s: str) -> list[str]:
    """Lower-cased, NFKD-folded alphanumeric tokens — the same instrument ``quote_supports_value`` uses."""
    return re.findall(r"[a-z0-9]+", normalize_with_offset_map(s.lower())[0])


def _stem(tok: str) -> str:
    for suf in _SUFFIXES:
        if tok.endswith(suf) and len(tok) - len(suf) >= _MIN_STEM:
            return tok[: -len(suf)]
    return tok


def _stem_equivalent(a: str, b: str) -> bool:
    """Two tokens are the same word form when equal, or when their stems agree.

    Tokens shorter than ``_MIN_STEM`` must match exactly (``spm`` is not ``spm12``; ``fd`` is
    ``fd``). Longer tokens match when their stems are equal, or when one stem is a prefix of the
    other, or when their common prefix covers all but one character of the shorter stem — the
    last clause is what joins ``coregistration`` (stem ``coregistr``) to ``coregistered`` (stem
    ``coregister``). Every clause requires the shared material to be at least ``_MIN_STEM`` long.
    """
    if a == b:
        return True
    if len(a) < _MIN_STEM or len(b) < _MIN_STEM:
        return False
    sa, sb = _stem(a), _stem(b)
    if sa == sb:
        return True
    short, long_ = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    if len(short) < _MIN_STEM:
        return False
    if long_.startswith(short):
        return True
    common = 0
    for x, y in zip(sa, sb, strict=False):
        if x != y:
            break
        common += 1
    return common >= _MIN_STEM and common >= len(short) - 1


def quote_supports_value_inflected(value: str, quote: str) -> bool:
    """True iff the value's tokens occur in the quote as a contiguous run, word form tolerated.

    A ``Full Name (ACRONYM)`` first-use value is accepted if any of its variants is found, as the
    base_pipeline guard does. Empty values and empty quotes are unsupported.
    """
    q = _tokens(quote)
    if not q:
        return False
    for variant in _first_use_variants(value):
        v = _tokens(variant)
        if not v or len(v) > len(q):
            continue
        for i in range(len(q) - len(v) + 1):
            if all(_stem_equivalent(v[j], q[i + j]) for j in range(len(v))):
                return True
    return False


def structured_noise_tool(value: str) -> str | None:
    """The D.3 structured-noise tool the value names, or ``None``.

    Matches on the token sequence anywhere in the value, so ``motion correction via ICA-AROMA``
    routes as well as ``ICA-AROMA``: either way the tool the paper named for this step is a
    denoising method, not a realignment tool (CALL 4).
    """
    v = _tokens(value)
    for seq, tool in STRUCTURED_NOISE_TOOLS.items():
        n = len(seq)
        if any(tuple(v[i : i + n]) == seq for i in range(len(v) - n + 1)):
            return tool
    return None


def motion_post_check(value: str | None, quote: str | None) -> str | None:
    """Return the reason to demote an EXTRACTED motion value, or ``None`` to keep it.

    Checked in this order: unsupported (:data:`MOTION_VALUE_UNSUPPORTED`) before routed
    (``f"{MOTION_VALUE_ROUTED}:{tool}"``). ``None`` means the value is in its own quote and names
    no structured-noise tool.
    """
    if not value or not quote:
        return MOTION_VALUE_UNSUPPORTED
    if not quote_supports_value_inflected(value, quote):
        return MOTION_VALUE_UNSUPPORTED
    tool = structured_noise_tool(value)
    if tool is not None:
        return f"{MOTION_VALUE_ROUTED}:{tool}"
    return None
