"""Score target_space predictions against the committed v1.2 ground-truth labels. REPORT-ONLY.

Applies the PRE-REGISTERED mapping (ground_truth/target_space_scoring_map.csv) to the FROZEN predictions
(ground_truth/target_space_predictions_v040_frozen.csv) and compares to the labels CSV. Emits the
error-class DECOMPOSITION, not an aggregate rate (see ground_truth/target_space_README.md).

The mapping keys on failure_reason, NOT status alone. A MISSING_FROM_PAPER with
value_not_in_literal:underspecified[MNI] means the extractor GRABBED a bare MNI-family term it could not
resolve to a variant -> family_specified (the analogue of the Talairach row; mirrors
generate_sfn_review's value_not_in_literal -> Family-specified). Scoring the status alone (map v1) was
lossy and produced a spurious 9-paper "enum-gap" class; that MISSING status is itself a false-missing
spec defect, scored on the diagnostic here and documented in docs/findings/target_space-false-missing.md.

Denominator: 19 labels, all now with a prediction (binder was run separately 2026-07-31). oconnor/mueller
are non-blind (shown as worked examples) -> the rate is quoted over the BLIND set of 17. Errors partition
into model-accuracy / capability-limited (CALL 7 unreachable) / demonstrated-input-corruption.

Run:  uv run python extractor_mvp/score_target_space.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GT = REPO / "ground_truth"
LABELS = GT / "target_space_labels_v1.csv"
PREDS = GT / "target_space_predictions_v040_frozen.csv"
MAP = GT / "target_space_scoring_map.csv"

NON_BLIND = {"oconnor_2017", "mueller_2021"}  # shown as worked-example rows
# liu_2005's batch MISSING is DEMONSTRATED input-corruption (two-column interleaving): a clean
# de-interleaved slice recovers Talairach 3/3 (target_space-pending-runs.md) -> upstream, not a model error.
INPUT_CORRUPTION = {"liu_2005"}
GESTURES = (
    "atlas",
    "standard space",
)  # bare space gestures (protocol CALL 3 -> absent, not a template)


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
        return extracted.get(value, "family_specified")  # 'other'/unknown -> family
    if status == "DEFERRED_TO_CITATION":
        return "deferred"
    # MISSING_FROM_PAPER — use the diagnostic, not the flattened status
    fr = fr or ""
    if "underspecified[MNI]" in fr:
        return "family_specified"  # extractor grabbed a bare MNI-family term
    if "no_match" in fr:  # grabbed something; apply named-vs-unnamed to the raw value
        return "absent" if any(g in (raw or "").lower() for g in GESTURES) else "family_specified"
    return "absent"  # nothing captured -> honest 'nothing reconstructable'


def error_class(label: str, pred: str, fr: str, raw: str) -> str:
    if label == "family_specified" and pred == "absent":
        return "family miss (target not captured at all)"  # e.g. liu_2005 Talairach
    if label == "study_specific" and pred == "absent":
        return "study_specific missed (constructed template not captured)"
    if label == "deferred" and pred == "absent":
        # two mechanisms wearing one label — split by whether the model grabbed a noun phrase
        if (raw or "").strip():
            return "extract-over-defer (grabbed an inadequate noun phrase instead of deferring)"
        return "deferral not recognized (silent miss; technique-of form)"
    if label == "canonical" and pred == "family_specified":
        return "specificity flattening (resolvable file grabbed as bare MNI)"
    if label == "native_volume" and pred == "family_specified":
        if "mni" in (raw or "").lower():  # grabbed a surface template's MNI frame (chen)
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
        cls = (
            "correct" if ok else error_class(label, pred, p["failure_reason"], p["raw_diagnostic"])
        )
        if not ok:
            cls_counts[cls] += 1
        tag = " [non-blind]" if pid in NON_BLIND else ""
        tag += "" if p["stable"] == "yes" else " [K=3 UNSTABLE]"
        # CALL 7 native_volume is inferred from an absence -> the value-support guard forbids the
        # extractor emitting it (target_space-call7-unreachable.md). Capability-limited, not accuracy.
        tag += (
            " [capability-limited: CALL 7 unreachable]"
            if (not ok and label == "native_volume")
            else ""
        )
        tag += (
            " [input-corruption: recovers on clean slice]"
            if (not ok and pid in INPUT_CORRUPTION)
            else ""
        )
        rows.append(
            f"  {pid:16s} label={label:16s} -> pred={pred:16s} {'OK ' if ok else 'ERR'} {cls}{tag}"
        )

    print("=== target_space score (report-only; map v2 + frozen predictions both committed) ===\n")
    print("\n".join(rows))

    scored = len(correct) + len(errors)
    blind = [p for p in correct + errors if p not in NON_BLIND]
    blind_err = [p for p in errors if p not in NON_BLIND]
    print(
        f"\nScored (have a prediction): {scored}   Correct: {len(correct)}   Error: {len(errors)}"
    )
    print(
        f"BLIND set (excl. oconnor/mueller): {len(blind_err)} error of {len(blind)}  "
        f"[= {len(blind) - len(blind_err)}/{len(blind)} correct]"
    )
    print(f"No prediction (excluded): {sorted(no_pred)}")
    cap = [p for p in errors if labels[p] == "native_volume"]  # CALL 7, unreachable by construction
    corrupt = [
        p for p in errors if p in INPUT_CORRUPTION
    ]  # demonstrated upstream, not a model error
    acc = [p for p in errors if p not in cap and p not in corrupt]
    print(
        f"Of {len(errors)} errors: {len(acc)} model-accuracy + {len(cap)} capability-limited "
        f"(CALL 7 unreachable: {cap}) + {len(corrupt)} demonstrated-input-corruption ({corrupt}). "
        f"See target_space-call7-unreachable.md / target_space-pending-runs.md."
    )

    print("\n=== error-class decomposition (the finding, not the rate) ===")
    for cls, n in cls_counts.most_common():
        print(f"  {n:2d}  {cls}")

    print(
        "\n  NB: decomposition of capability + accuracy classes, not an external benchmark;"
        " single-rater, developer-produced (see README caveat). The MISSING-status false-missing on"
        " the 9 value_not_in_literal papers is a spec defect scored on the diagnostic here"
        " (docs/findings/target_space-false-missing.md)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
