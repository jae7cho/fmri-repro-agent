"""Score target_space predictions against the committed v1.2 ground-truth labels. REPORT-ONLY.

Applies the PRE-REGISTERED map (ground_truth/target_space_scoring_map.csv) to the FROZEN predictions
(ground_truth/target_space_predictions_v040_frozen.csv) vs the labels CSV. Emits the error DECOMPOSITION
+ blind rates with Wilson intervals -- not a bare rate (see ground_truth/target_space_README.md).

The map keys on failure_reason, not status alone (value_not_in_literal:underspecified[MNI] -> the
extractor GRABBED a bare MNI term -> family_specified; docs/findings/target_space-false-missing.md).

Errors are partitioned THREE ways, separating "is the model wrong?" from "was the label scoreable?":
  - model error, label REACHABLE           -> scoreable accuracy.
  - model error (LEAK), label UNREACHABLE  -> a GENUINE defect, scoreless only because CALL 7
    native_volume can't be scored (target_space-call7-unreachable.md). NOT absorbed/passive.
  - upstream INPUT-CORRUPTION               -> auto-flagged from the system's own methods_not_found
    slice signal (slice_suspicious column); liu_2005 confirmed by the de-interleave run.

The reachable-only denominator is a scoring-policy exclusion IDENTIFIED POST-HOC (after seeing the score)
-- a-priori-defensible but not pre-registered; BOTH numbers are reported.

Run:  uv run python extractor_mvp/score_target_space.py
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GT = REPO / "ground_truth"
LABELS = GT / "target_space_labels_v1.csv"
PREDS = GT / "target_space_predictions_v040_frozen.csv"
MAP = GT / "target_space_scoring_map.csv"

NON_BLIND = {"oconnor_2017", "mueller_2021"}  # shown as worked-example rows
GESTURES = ("atlas", "standard space")  # bare space gestures (CALL 3 -> absent, not a template)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for k/n. Returns (point, lo, hi)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def load_extracted_map() -> dict[str, str]:
    """EXTRACTED value -> label_state, from the committed map CSV."""
    out: dict[str, str] = {}
    for r in csv.DictReader(MAP.open()):
        if r["extractor_status"] == "EXTRACTED" and r["extractor_value"]:
            out[r["extractor_value"]] = r["label_state"]
    return out


def apply_map(status: str, value: str, fr: str, raw: str, extracted: dict[str, str]) -> str:
    """The committed map, keyed on (status, failure_reason, raw_diagnostic)."""
    if status == "EXTRACTED":
        return extracted.get(value, "family_specified")
    if status == "DEFERRED_TO_CITATION":
        return "deferred"
    fr = fr or ""
    if "underspecified[MNI]" in fr:
        return "family_specified"  # extractor grabbed a bare MNI-family term
    if "no_match" in fr:  # grabbed something; named-vs-unnamed on the raw value
        return "absent" if any(g in (raw or "").lower() for g in GESTURES) else "family_specified"
    return "absent"


def error_class(label: str, pred: str, raw: str) -> str:
    if label == "family_specified" and pred == "absent":
        return "family miss (target not captured at all)"
    if label == "study_specific" and pred == "absent":
        return "study_specific missed (constructed template not captured)"
    if label == "deferred" and pred == "absent":
        if (raw or "").strip():
            return "extract-over-defer (grabbed an inadequate noun phrase instead of deferring)"
        return "deferral not recognized (silent miss; technique-of form)"
    if label == "canonical" and pred == "family_specified":
        return "specificity flattening (resolvable file grabbed as bare MNI)"
    if label == "native_volume" and pred == "family_specified":
        if "mni" in (raw or "").lower():
            return "cross-axis leak (surface template's MNI frame grabbed as volumetric)"
        return "results-space leak (derived-map space grabbed as target; CALL 7(a)) [binder]"
    return f"other mismatch ({label} vs {pred})"


def main() -> int:
    labels = {r["paper_id"]: r["target_space_state"] for r in csv.DictReader(LABELS.open())}
    preds = {
        r["paper_id"]: r
        for r in csv.DictReader(ln for ln in PREDS.open() if not ln.startswith("#"))
    }
    extracted = load_extracted_map()

    correct: list[str] = []
    errors: list[str] = []
    no_pred: list[str] = []
    cls_counts: Counter[str] = Counter()
    rows = []
    for pid in sorted(labels):
        label = labels[pid]
        if pid not in preds:
            no_pred.append(pid)
            continue
        p = preds[pid]
        pred = apply_map(
            p["extractor_status"],
            p["extractor_value"],
            p["failure_reason"],
            p["raw_diagnostic"],
            extracted,
        )
        ok = pred == label
        (correct if ok else errors).append(pid)
        cls = "correct" if ok else error_class(label, pred, p["raw_diagnostic"])
        if not ok:
            cls_counts[cls] += 1
        tag = " [non-blind]" if pid in NON_BLIND else ""
        tag += "" if p["stable"] == "yes" else " [K=3 UNSTABLE]"
        if not ok and label == "native_volume":
            tag += " [unreachable+ACTIVE-leak]"  # label unreachable (CALL 7) BUT the leak is a real defect
        if not ok and p.get("slice_suspicious") == "True":
            tag += " [input-corruption: methods_not_found flag]"
        rows.append(
            f"  {pid:16s} label={label:16s} -> pred={pred:16s} {'OK ' if ok else 'ERR'} {cls}{tag}"
        )

    print("=== target_space score (report-only; map v2 + frozen predictions committed) ===\n")
    print("\n".join(rows))

    # Partition errors: separate "model wrong?" from "label scoreable?"
    unreachable = [p for p in errors if labels[p] == "native_volume"]  # CALL 7 -> can't be scored
    corrupt = [p for p in errors if preds[p].get("slice_suspicious") == "True"]  # system slice flag
    reach_acc = [p for p in errors if p not in unreachable and p not in corrupt]
    print("\n=== error partition (model defect vs scoreability) ===")
    print(
        f"  {len(reach_acc)} model error, label REACHABLE (scoreable accuracy): {sorted(reach_acc)}"
    )
    print(
        f"  {len(unreachable)} model error (LEAK), label UNREACHABLE by construction (CALL 7): {sorted(unreachable)}"
    )
    print(
        "     -- a GENUINE defect, scoreless ONLY because native_volume can't be scored, NOT absorbed;"
    )
    print(
        "     binder's leak yields the WRONG SPACE on any paper whose results-space != preprocessing space."
    )
    print(
        f"  {len(corrupt)} upstream INPUT-CORRUPTION (auto-flagged: methods_not_found slice signal): {sorted(corrupt)}"
    )
    print("     -- liu_2005 confirmed by the de-interleave run; not a model defect.")

    # Blind correct-rate, both denominators, with Wilson 95% intervals
    blind = [p for p in correct + errors if p not in NON_BLIND]
    blind_c = [p for p in correct if p not in NON_BLIND]
    excl = set(unreachable) | set(corrupt)
    reach_blind = [p for p in blind if p not in excl]
    reach_c = [p for p in blind_c if p not in excl]
    pa, la, ha = wilson(len(blind_c), len(blind))
    pb, lb, hb = wilson(len(reach_c), len(reach_blind))
    print("\n=== blind correct-rate (Wilson 95%) — both denominators ===")
    print(f"  all blind        {len(blind_c)}/{len(blind)} = {pa:.1%}  [{la:.0%}, {ha:.0%}]")
    print(
        f"  reachable-only   {len(reach_c)}/{len(reach_blind)} = {pb:.1%}  [{lb:.0%}, {hb:.0%}]  "
        f"(excludes {len(excl)}: {len(unreachable)} unreachable-leak + {len(corrupt)} corruption)"
    )
    print(
        "  NOTE: reachable-only is a scoring-policy exclusion IDENTIFIED POST-HOC (after seeing the score),"
    )
    print(
        "  same shape as the map-v2 correction: a-priori-defensible (an unreachable label can't be scored)"
    )
    print(
        "  but NOT pre-registered; both numbers stand. The excluded leaks are REAL defects -- if design (B)"
    )
    print("  makes native_volume reachable, they would count and the reachable rate would drop.")
    if no_pred:
        print(f"\nNo prediction: {sorted(no_pred)}")
    print("\n=== error-class decomposition ===")
    for cls, n in cls_counts.most_common():
        print(f"  {n:2d}  {cls}")
    print(
        "\n  NB: single-rater, developer-produced -- indicative, not an external benchmark (README caveat)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
