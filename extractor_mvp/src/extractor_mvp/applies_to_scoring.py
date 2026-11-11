"""Scoring a field against labels that carry ``applies_to`` (DESIGN_applies_to.md §5, Stage 1,
2026-11-11). No model calls; counts only.

A field is a list of label variants (the labeler's rows, one per part, "all" for a value that holds
throughout) and a list of predicted variants (the record's: one "all" value for an ``Extracted``
field, one per part for a ``Varied`` one). Two scope errors are classes of their own, never mixed
into value errors:

- **collapsed**: the prediction is one "all" value equal to one label variant's value, where the
  label has parts. Scored wrong: a reader would apply it to data it does not describe.
- **split**: the prediction has parts where the label says "all".

Otherwise predicted and label variants are matched one to one, by ``overlaps`` (the caller's span
test). Fork E2: when quotes do not overlap there is no alias fallback; the label variant is missed
and the predicted one spurious. A label variant is matched_correct, matched_wrong or missed; a
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

    @property
    def correct(self) -> bool:
        return self.outcome == "correct"


def quotes_overlap(label: LabelVariant, pred: PredictedVariant) -> bool:
    """The default span test: the label's supporting quote and one of the predicted variant's
    sentences resolve against each other (span_resolver, the resolver the scorers already trust),
    i.e. one sentence contains the other's text. Without the paper's text this is the overlap test
    that needs no offsets; a caller holding both resolved spans passes its own."""
    from extractor_mvp.span_resolver import resolve_quote

    if not label.quote:
        return False
    for q in pred.quotes:
        if not q:
            continue
        shorter, longer = sorted((label.quote, q), key=len)
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
            "no prediction", [(lv.applies_to, "missed") for lv in labels], [], [None] * len(labels)
        )
    pred_all = len(preds) == 1 and is_all(preds[0].applies_to)
    if label_all and pred_all:
        ok = equal(preds[0].value, labels[0].value)
        cls = "matched_correct" if ok else "matched_wrong"
        return FieldScore("correct" if ok else "wrong", [(labels[0].applies_to, cls)], [], [0])
    if label_all:
        return FieldScore("split")
    if pred_all and any(equal(preds[0].value, lv.value) for lv in labels):
        return FieldScore("collapsed")
    # variant matching, one to one, label order; E2: no alias fallback
    taken: set[int] = set()
    classes: list[tuple[str, str]] = []
    matches: list[int | None] = []
    for lv in labels:
        hit = next(
            (
                i
                for i, pv in enumerate(preds)
                if i not in taken and not is_all(pv.applies_to) and overlaps(lv, pv)
            ),
            None,
        )
        matches.append(hit)
        if hit is None:
            classes.append((lv.applies_to, "missed"))
            continue
        taken.add(hit)
        ok = equal(preds[hit].value, lv.value)
        classes.append((lv.applies_to, "matched_correct" if ok else "matched_wrong"))
    spurious = [pv.applies_to for i, pv in enumerate(preds) if i not in taken]
    correct = not spurious and all(c == "matched_correct" for _, c in classes)
    return FieldScore("correct" if correct else "wrong", classes, spurious, matches)
