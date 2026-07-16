"""Deterministic post-hoc subject check for ``temporal_standardization_method``.

INERT. Nothing in the four-state path imports this; production output is byte-identical to
HEAD. It is built and measured only — consumption is a separate, later decision (the tier-5
precedent: built, validated, builders ignored it; wiring it in was its own deliberate change).

What it is: it makes the ``EXTRACTION_PROMPT`` DECISION RULE's *enumerated* derived-product
exclusions DETERMINISTIC. It does not invent a new rule. Two lists, measured SEPARATELY, because
the two derived-subject failures they target are different classes:

  * ``_PROMPT_TAXONOMY``   — lifted VERBATIM from the DECISION RULE. Measures ENFORCEMENT: what
    deterministic checking buys on terms the prompt already names (the model was *told* and
    overrode it anyway — e.g. viduarre/ICA, extracted 4/10 under the fixed prompt).
  * ``_DECLARED_EXTENSIONS`` — NOT in the prompt. Declared, motivated additions, each citing the
    paper that forced it. Measures COVERAGE: derived-subject shapes the prompt never named (the
    model had no rule to override — e.g. derosa/activation-patterns).

Structural limit (see docs/findings/subject-validator.md): a derived-product denylist is
UNBOUNDED — every paper can coin a new derived product (gradients, eigenvector centrality, ALFF
maps, beta series, parcel timeseries). derosa is the first proof, arriving immediately from a
corpus of twenty. So the honest claim is narrow: this makes ENUMERATED exclusions unoverridable;
it does not solve derived-subject false positives, it enforces the ones already enumerated. The
extension RATE is the measurement that decides deterministic-vs-LLM; one extension is not a trend,
but every addition is logged here so the rate is trackable.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from extractor_mvp.span_resolver import _delete_with_map, normalize_with_offset_map

# Normalization TRIGGER verbs. Superset note: the DECISION RULE's literal operations are
# normalized / standardized / z-scored / "0 mean and 1 variance" / "unit variance". This regex
# generalizes spelling (z-scored/zscored, -ise/-ize) and adds "demeaned" as a same-class
# operation. It only locates WHERE a normalization happens; the derived-product SUBJECT lists
# below are what carry the "enforces the prompt's own rule" claim.
_NORM_VERB = re.compile(r"\b(normali[sz]ed|standardi[sz]ed|z-?scored|demeaned)\b", re.IGNORECASE)

# Lifted VERBATIM from EXTRACTION_PROMPT's DECISION RULE derived-product taxonomy. Do NOT extend
# this tuple: new derived-product shapes belong in _DECLARED_EXTENSIONS so enforcement and
# coverage stay separately measurable.
_PROMPT_TAXONOMY: tuple[str, ...] = (
    "FC",
    "SFC",
    "ReHo",
    "seed-connectivity",
    "correlation matrix",
    "connectivity matrix",
    "gradient",
    "ICA components",  # verbatim from the DECISION RULE ("ICA/PCA components"); the bare acronym
    "PCA components",  # "ICA" was a spec deviation that collided with anatom-ICA-l / cort-ICA-l etc.
    "nuisance regressor",
    "classifier feature",
    "QC metric",
    "statistical map",
)


class _Extension(NamedTuple):
    term: str
    paper: str  # the arm-corpus paper that motivated adding this term
    note: str


# NOT in the prompt. Each entry is a declared, motivated addition — a derived-subject shape the
# DECISION RULE never named. Every addition is logged here; the count is the escalation signal.
_DECLARED_EXTENSIONS: tuple[_Extension, ...] = (
    _Extension(
        term="activation pattern",
        paper="derosa_2025",
        note='arm-1: "Activation patterns were standardized prior to further analysis…" — a '
        "signal-derived product the DECISION RULE does not name (nearest is the CRITICAL "
        "block's 'activation tables', a different referent).",
    ),
)


class DerivedSubject(NamedTuple):
    term: str
    source: str  # "prompt" (enforcement) | "extension" (coverage)


def _agg(s: str) -> str:
    """span_resolver normalization: NFKD + lowercase + delete whitespace/hyphens/markers — the
    same instrument as ``quote_supports_value``, so surface mangling/spacing cannot cause a
    spurious pass or fail."""
    return _delete_with_map(normalize_with_offset_map(s.lower())[0])[0]


def derived_subject_term(quote: str) -> DerivedSubject | None:
    """Return the derived-product term bound as the SUBJECT of the first normalization verb in
    ``quote`` (and which list it came from), or ``None`` if the subject is not lexically a derived
    product.

    Heuristic, and deliberately narrow. For PASSIVE constructions ("X was normalized") the subject
    precedes the verb, so only the span BEFORE the first normalization verb is scanned. Text AFTER
    the verb is intentionally ignored: "the BOLD time series were z-scored before computing
    functional connectivity" is a TRUE positive that merely mentions a derived product downstream.

    KNOWN HOLES (documented, tested as holes, not silently handled):
      * ACTIVE voice ("we normalized the SFC map") puts the object AFTER the verb and is NOT
        caught.
      * Short acronyms (FC / ICA / PCA) are matched by aggregated substring and could over-match
        in principle; on the measured arm-1 slices they do not.

    Taxonomy is lifted verbatim from EXTRACTION_PROMPT's DECISION RULE (``_PROMPT_TAXONOMY``) plus
    declared, motivated additions (``_DECLARED_EXTENSIONS``) — this makes the prompt's existing,
    model-overridable rule deterministic on enumerated terms; it does not invent a rule, and it
    inherits the prompt's coverage gap exactly.
    """
    m = _NORM_VERB.search(quote)
    if m is None:
        return None
    before = _agg(quote[: m.start()])
    if not before:
        return None

    candidates: list[tuple[str, str]] = [(t, "prompt") for t in _PROMPT_TAXONOMY]
    candidates += [(e.term, "extension") for e in _DECLARED_EXTENSIONS]

    # Earliest match wins (in passive voice the grammatical subject is leftmost); ties broken by
    # longest term (prefer "sfc" over the "fc" nested inside it).
    best: tuple[int, int, str, str] | None = None
    for term, source in candidates:
        at = before.find(_agg(term))
        if at >= 0:
            key = (at, -len(_agg(term)), term, source)
            if best is None or key < best:
                best = key
    if best is None:
        return None
    return DerivedSubject(term=best[2], source=best[3])
