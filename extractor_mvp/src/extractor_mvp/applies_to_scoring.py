"""Scoring a field against labels that carry ``applies_to`` (DESIGN_applies_to.md §5, Stage 1,
2026-11-11). No model calls; counts only.

A field is a list of label variants (the labeler's rows, one per part, "all" for a value that holds
throughout) and a list of predicted variants (the record's: one "all" value for an ``Extracted``
field, one per part for a ``Varied`` one). Two scope errors are classes of their own, never mixed
into value errors:

- **collapsed**: the prediction is one "all" value equal to one label variant's value, where the
  label has parts. Scored wrong: a reader would apply it to data it does not describe.
- **split**: the prediction has parts where the label says "all".

Otherwise predicted and label variants are matched one to one, first by ``overlaps`` (the caller's
span test, on quotes with leading and trailing ellipses and quote marks stripped), then, for a label
variant with no quote or whose quote overlapped nothing, by part name (``names_match``: the same
words under the same-string rule, or the same content words). Stage 2c (the author's item 1,
2026-11-11) replaced fork E2's "no alias fallback" with this name fallback; a label variant matched
by neither is missed and an unmatched predicted variant spurious. ``FieldScore.routes`` says which
test matched each label variant. A label variant is matched_correct, matched_wrong or missed; a
predicted variant that matches none is spurious. A field is correct only when every label variant
is matched_correct and nothing is spurious. Variant-level counts are reported beside the field-level
outcome, never instead of it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fmri_repro.spec.provenance import APPLIES_TO_ALL, normalize_applies_to

#: Field-level outcomes.
OUTCOMES: tuple[str, ...] = ("correct", "wrong", "collapsed", "split", "no prediction")
#: Label-variant classes.
LABEL_CLASSES: tuple[str, ...] = ("matched_correct", "matched_wrong", "missed")


def is_all(applies_to: str) -> bool:
    """'all', or the labelers' 'all <qualifier>' form ("all runs"), under the same-string rule."""
    key = normalize_applies_to(applies_to or APPLIES_TO_ALL)
    return key == APPLIES_TO_ALL or key.startswith(APPLIES_TO_ALL + " ")


@dataclass(frozen=True)
class LabelVariant:
    applies_to: str
    value: Any
    quote: str = ""


@dataclass(frozen=True)
class PredictedVariant:
    applies_to: str
    value: Any
    #: the value's sentence and the sentence tying it to its part, as the record holds them
    quotes: tuple[str, ...] = ()


@dataclass
class FieldScore:
    outcome: str
    #: (label applies_to, class) per label variant; "collapsed" / "split" fields carry none
    label_classes: list[tuple[str, str]] = field(default_factory=list)
    #: predicted applies_to that matched no label variant
    spurious: list[str] = field(default_factory=list)
    #: per label variant, the index of the predicted variant it matched (None: missed)
    matches: list[int | None] = field(default_factory=list)
    #: per label variant, how it matched: "quote", "name" or None (missed)
    routes: list[str | None] = field(default_factory=list)

    @property
    def correct(self) -> bool:
        return self.outcome == "correct"


_EDGE = "\u2026.\"'\u00ab\u00bb\u201c\u201d\u2018\u2019\u201e\u201a\u2039\u203a`"


def clean_quote(quote: str) -> str:
    """A quote with leading and trailing ellipses ("…", "...") and quote marks stripped, and the
    whitespace around them: a labeler's "…from the band 0.01-0.1 Hz" overlaps the sentence."""
    return (quote or "").strip().strip(_EDGE + " \t\n").strip()


def names_match(label_applies_to: str, pred_applies_to: str) -> bool:
    """The label's part and the record's are one name: equal under the same-string rule, or equal
    content words (part_names.content_words) when both have any."""
    from extractor_mvp.part_names import content_words

    if normalize_applies_to(label_applies_to) == normalize_applies_to(pred_applies_to):
        return True
    a, b = content_words(label_applies_to), content_words(pred_applies_to)
    return bool(a) and a == b


def quotes_overlap(label: LabelVariant, pred: PredictedVariant) -> bool:
    """The default span test: the label's supporting quote and one of the predicted variant's
    sentences resolve against each other (span_resolver, the resolver the scorers already trust),
    i.e. one sentence contains the other's text. Without the paper's text this is the overlap test
    that needs no offsets; a caller holding both resolved spans passes its own."""
    from extractor_mvp.span_resolver import resolve_quote

    lq = clean_quote(label.quote)
    if not lq:
        return False
    for q in pred.quotes:
        q = clean_quote(q)
        if not q:
            continue
        shorter, longer = sorted((lq, q), key=len)
        if resolve_quote(shorter, longer).span is not None:
            return True
    return False


def score_field(
    labels: list[LabelVariant],
    preds: list[PredictedVariant],
    equal: Callable[[Any, Any], bool],
    overlaps: Callable[[LabelVariant, PredictedVariant], bool] = quotes_overlap,
) -> FieldScore:
    """One field's outcome. ``equal(pred_value, label_value)`` is the field's value comparison."""
    if not labels:
        raise ValueError("a field is scored against at least one label variant")
    label_all = len(labels) == 1 and is_all(labels[0].applies_to)
    if not preds:
        return FieldScore(
            "no prediction",
            [(lv.applies_to, "missed") for lv in labels],
            [],
            [None] * len(labels),
            [None] * len(labels),
        )
    pred_all = len(preds) == 1 and is_all(preds[0].applies_to)
    if label_all and pred_all:
        ok = equal(preds[0].value, labels[0].value)
        cls = "matched_correct" if ok else "matched_wrong"
        return FieldScore(
            "correct" if ok else "wrong", [(labels[0].applies_to, cls)], [], [0], ["all"]
        )
    if label_all:
        return FieldScore("split")
    if pred_all and any(equal(preds[0].value, lv.value) for lv in labels):
        return FieldScore("collapsed")
    # variant matching, one to one, label order: by quote overlap first, then by part name
    # (Stage 2c), each pass over the predicted variants not yet taken
    taken: set[int] = set()
    matches: list[int | None] = [None] * len(labels)
    routes: list[str | None] = [None] * len(labels)
    tests: tuple[tuple[str, Callable[[LabelVariant, PredictedVariant], bool]], ...] = (
        ("quote", overlaps),
        ("name", lambda lv, pv: names_match(lv.applies_to, pv.applies_to)),
    )
    for route, test in tests:
        for li, lv in enumerate(labels):
            if matches[li] is not None:
                continue
            hit = next(
                (
                    i
                    for i, pv in enumerate(preds)
                    if i not in taken and not is_all(pv.applies_to) and test(lv, pv)
                ),
                None,
            )
            if hit is not None:
                taken.add(hit)
                matches[li], routes[li] = hit, route
    classes: list[tuple[str, str]] = []
    for lv, hit in zip(labels, matches, strict=True):
        if hit is None:
            classes.append((lv.applies_to, "missed"))
        else:
            ok = equal(preds[hit].value, lv.value)
            classes.append((lv.applies_to, "matched_correct" if ok else "matched_wrong"))
    spurious = [pv.applies_to for i, pv in enumerate(preds) if i not in taken]
    correct = not spurious and all(c == "matched_correct" for _, c in classes)
    return FieldScore("correct" if correct else "wrong", classes, spurious, matches, routes)
