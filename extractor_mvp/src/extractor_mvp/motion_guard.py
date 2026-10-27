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

from extractor_mvp.quote_support import token_equivalent, tokens
from extractor_mvp.span_resolver import _first_use_variants, normalize_with_offset_map

#: Base of the reason emitted when the value is not in its own quote (ruling 1-3).
MOTION_VALUE_UNSUPPORTED = "motion_value_unsupported_by_quote"
#: Base of the reason emitted when the value names a D.3 structured-noise tool (ruling 4). The
#: emitted reason is ``f"{MOTION_VALUE_ROUTED}:{tool}"`` with ``tool`` one of
#: :data:`STRUCTURED_NOISE_TOOLS`'s values.
MOTION_VALUE_ROUTED = "motion_value_routed_structured_noise"
#: Base of the DIAGNOSTIC reason (never a gap: the field stays EXTRACTED) emitted when a routed
#: structured-noise tool's own quote names exactly one listed package and the processed value falls
#: back to that package (prereg Amendment 11, 2026-10-27; DELTA §4 ruling 6). Emitted as
#: ``f"{MOTION_VALUE_ROUTED_FALLBACK}:{tool}->{package}"``.
MOTION_VALUE_ROUTED_FALLBACK = "motion_value_routed_fallback_to_package"

#: The realignment-capable list of protocol v1.8 (CALL 1), by lower-cased token. A digit run after
#: the name is the text layer's citation artefact (ruling 5) or, for SPM only, the version that is
#: part of the name token (SPM8, SPM12); the value returned keeps the digits for SPM and drops them
#: for the others, which is how the labels write these packages.
LISTED_PACKAGES: tuple[str, ...] = ("afni", "fsl", "spm", "ants", "brainvoyager")

#: The frozen heuristic's operation-phrase list (scripts/motion_value_kind.py, prereg :97-99),
#: COPIED here because that module is a script, not a package; tests/test_motion_guard.py holds the
#: copy equal to the original, so neither can drift alone. Used only to derive the attribution
#: level on the processed layer (Amendment 11); the heuristic itself is untouched (C21).
_OPERATION_PHRASES_FROZEN: tuple[str, ...] = (
    "realign",
    "motion correction",
    "motion-correction",
    "head motion",
    "head movement",
    "coregist",
    "co-regist",
    "rigid body",
    "rigid-body",
    "volume registration",
    "image registration",
)

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

#: The matcher is shared with the step-field check (quote_support.py) and is DIGIT-EXACT since
#: 2026-10-26 (DELTA_value_in_quote_step_fields.md §5 ruling 5): a token containing a digit must
#: match exactly, so ``mni152`` no longer stands for ``mni152nlin6asym`` through the prefix clause.
#: The 160 resolved motion draws on record are unchanged by the tightening (the replay shows 0).
_tokens = tokens
_stem_equivalent = token_equivalent


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


def attribution_from_quote(quote: str | None) -> str:
    """The attribution level derived on the processed layer (Amendment 11): ``"step"`` if the quoted
    sentence contains an operation phrase from the frozen heuristic's list, else ``"package"``.
    Reported against the labels' column R as an agreement count; never scored."""
    low = (quote or "").lower()
    return "step" if any(p in low for p in _OPERATION_PHRASES_FROZEN) else "package"


def listed_package_in_quote(quote: str | None) -> str | None:
    """The one listed package the quote names, as written, or ``None`` when it names none or more
    than one. A token is a package when it is the name alone or the name followed by a digit run
    (``afni48``, ``spm12``). SPM keeps its digits (the version is part of the name token); the
    others return the bare name."""
    if not quote:
        return None
    found: dict[str, str] = {}
    for raw_tok in re.findall(r"[A-Za-z0-9]+", normalize_with_offset_map(quote)[0]):
        low = raw_tok.lower()
        for name in LISTED_PACKAGES:
            if low == name or (low.startswith(name) and low[len(name) :].isdigit()):
                found.setdefault(name, raw_tok if name == "spm" else raw_tok[: len(name)])
                break
    if len(found) != 1:
        return None
    return next(iter(found.values()))
