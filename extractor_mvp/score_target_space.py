"""Score target_space predictions against the committed v1.2 ground-truth labels. REPORT-ONLY.

Applies the PRE-REGISTERED mapping (ground_truth/target_space_scoring_map.csv, committed before this
script ran, so it cannot be tuned to a number) to the FROZEN predictions
(ground_truth/target_space_predictions_v040_frozen.csv) and compares to the labels CSV. Emits the
error-class DECOMPOSITION, not an aggregate rate — the decomposition is the finding (see
ground_truth/target_space_README.md).

Denominator: 19 labels. binder_1999 has no prediction (added post-batch) -> EXCLUDED. oconnor/mueller
are non-blind (shown as worked examples) -> counted but flagged; blind N=17.

Run:  uv run python extractor_mvp/score_target_space.py
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GT = REPO / "ground_truth"
LABELS = GT / "target_space_labels_v1.csv"
PREDS = GT / "target_space_predictions_v040_frozen.csv"
MAP = GT / "target_space_scoring_map.csv"

NON_BLIND = {"oconnor_2017", "mueller_2021"}  # shown as worked-example rows


def load_map() -> tuple[dict[str, str], dict[str, str]]:
    """(status,value) -> label_state for EXTRACTED; status -> label_state for DEFERRED/MISSING."""
    by_value: dict[str, str] = {}
    by_status: dict[str, str] = {}
    for r in csv.DictReader(MAP.open()):
        st, val, lab = r["extractor_status"], r["extractor_value"], r["label_state"]
        if st == "EXTRACTED":
            by_value[val] = lab
        else:
            by_status[st] = lab
    return by_value, by_status


def apply_map(status: str, value: str, by_value: dict[str, str], by_status: dict[str, str]) -> str:
    if status == "EXTRACTED":
        return by_value.get(value, "family_specified")  # 'other'/unknown -> family (per map)
    return by_status[status]


def error_class(label: str, pred: str, raw: str) -> str:
    """Name the error class for a mismatch (per the README taxonomy)."""
    raw_l = (raw or "").lower()
    fam_term = any(t in raw_l for t in ("mni", "epi template"))
    if label == "family_specified" and pred == "absent":
        return "family_flattening (enum gap: no bare-family slot)"
    if label == "study_specific" and pred == "absent":
        return "study_specific missed (detector didn't fire)"
    if label == "deferred" and pred == "absent":
        return "deferral miss (provenance/technique-of form)"
    if label == "canonical" and pred == "absent":
        return "specificity flattening (resolvable file -> bare term)"
    if label == "native_volume" and pred == "absent":
        return "cross-axis leak (surface frame grabbed)" if fam_term else "native missed"
    return f"other mismatch ({label} vs {pred})"


def main() -> int:
    labels = {r["paper_id"]: r["target_space_state"] for r in csv.DictReader(LABELS.open())}
    preds = {
        r["paper_id"]: r
        for r in csv.DictReader(ln for ln in PREDS.open() if not ln.startswith("#"))
    }
    by_value, by_status = load_map()

    correct: list[str] = []
    errors: list[str] = []
    no_pred: list[str] = []
    rows = []
    for pid in sorted(labels):
        label = labels[pid]
        if pid not in preds:
            no_pred.append(pid)
            continue
        p = preds[pid]
        pred = apply_map(p["extractor_status"], p["extractor_value"], by_value, by_status)
        ok = pred == label
        (correct if ok else errors).append(pid)
        cls = "correct" if ok else error_class(label, pred, p["raw_diagnostic"])
        blind = "" if pid not in NON_BLIND else " [non-blind]"
        unstable = "" if p["stable"] == "yes" else " [K=3 UNSTABLE]"
        rows.append(
            f"  {pid:16s} label={label:16s} pred={p['extractor_status']:20s}"
            f"-> {pred:16s} {'OK ' if ok else 'ERR'} {cls}{blind}{unstable}"
        )

    print("=== target_space score (report-only; mapping + predictions both pre-committed) ===\n")
    print("\n".join(rows))
    scored = len(correct) + len(errors)
    print(
        f"\nScored (have a prediction): {scored}    Correct: {len(correct)}    Error: {len(errors)}"
    )
    print(f"No prediction (excluded): {sorted(no_pred)}")

    print("\n=== error-class decomposition (the finding, not the rate) ===")
    from collections import Counter

    cls_counts: Counter[str] = Counter()
    for pid in errors:
        p = preds[pid]
        pred = apply_map(p["extractor_status"], p["extractor_value"], by_value, by_status)
        cls_counts[error_class(labels[pid], pred, p["raw_diagnostic"])] += 1
    for cls, n in cls_counts.most_common():
        print(f"  {n:2d}  {cls}")

    print("\n=== denominators ===")
    print(
        f"  labels: {len(labels)}   scored: {scored}   blind: {scored - len(NON_BLIND & set(preds))}"
        f"   (binder excluded: no prediction)"
    )
    print(
        "  NB: this is a decomposition of capability + accuracy classes, not an external benchmark;"
        " single-rater, developer-produced (see README caveat)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
