"""Score target_space predictions against the committed v1.2 ground-truth labels. REPORT-ONLY.

Applies the PRE-REGISTERED map (ground_truth/target_space_scoring_map.csv) to the FROZEN predictions
(ground_truth/target_space_predictions_v040_frozen.csv) vs the labels CSV. Emits the error DECOMPOSITION
+ blind rates with Wilson intervals -- not a bare rate (see ground_truth/target_space_README.md).

Map v3 keys on the VALUE the 0.5.0 extractor emits -- the SpecifiedTerm{verbatim, resolved, resolution}
reconstructed from each frozen (pre-0.5.0) row -- not the failure_reason (v2, retained in git history).
A resolved member maps via a documented member->tier lookup; resolved=None + 'underspecified' ->
family_specified; resolved=None + 'unrecognized' -> named-vs-unnamed on the verbatim (see the map CSV).
v2 and v3 give the SAME numbers (11/8) because the value is reconstructed from the same frozen fields;
this is a re-expression that keys on the value the retype made recordable, not a re-grade.

CAVEAT: the frozen predictions are PRE-retype output; reconstruct_struct TRANSLATES old columns into the
new shape. Faithful translation, but NOT genuine 0.5.0 extractor output -- demonstrating the retype needs
a re-extraction at 0.5.0 (docs/findings/target_space-false-missing.md). Also: 'resolution' is PROVENANCE,
not the grader -- completeness derives from the named-vs-unnamed heuristic on the verbatim PLUS the field
(gordon and power are both 'unrecognized' yet grade differently; the heuristic separates them).

Errors are partitioned THREE ways, separating "is the model wrong?" from "was the label scoreable?":
  - model error, label REACHABLE           -> scoreable accuracy.
  - model error (LEAK), label UNREACHABLE  -> a GENUINE defect, scoreless only because CALL 7
    native_volume can't be scored (target_space-call7-unreachable.md). NOT absorbed/passive.
  - INPUT-CORRUPTION, TWO states: SUSPECT (the system's own methods_not_found slice flag -- computed,
    cheap, "input may be corrupted; UNTESTED" -> STAYS in the denominator) vs DEMONSTRATED (a TESTED
    causal claim: a cited run fed a clean slice, passed a validity gate, showed the field recovering ->
    excluded). The flag only SUSPECTS; corruption can be present and non-causal (cole: flagged, tested,
    REFUTED). liu_2005 carries both.

The reachable-only denominator is a scoring-policy exclusion IDENTIFIED POST-HOC (after seeing the score)
-- a-priori-defensible but not pre-registered; BOTH numbers are reported.

Run:  uv run python extractor_mvp/score_target_space.py
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
GT = REPO / "ground_truth"
LABELS = GT / "target_space_labels_v1.csv"
PREDS = GT / "target_space_predictions_v040_frozen.csv"
MAP = GT / "target_space_scoring_map.csv"

NON_BLIND = {"oconnor_2017", "mueller_2021"}  # shown as worked-example rows
GESTURES = ("atlas", "standard space")  # bare space gestures (CALL 3 -> absent, not a template)

# Input-corruption is TWO states. The slice_suspicious flag establishes SUSPICION (computed, cheap,
# untested). DEMONSTRATED causation is a separate TESTED claim -- a cited run that fed a clean/repaired
# slice, passed a slice-validity gate, and showed the field recovering. NOT inferrable from the flag:
# corruption can be present and non-causal (cole -- flagged, looked causal, testing REFUTED it). Only
# DEMONSTRATED rows may leave the model-accuracy denominator; suspect rows stay in, flagged.
DEMONSTRATED_CORRUPTION = {
    "liu_2005": "scripts/run_pending_target_space.py -- de-interleave K=3: BrainVoyager 3/3 "
    "(slice-validity gate) + Talairach 3/3 recovered on the clean slice (2026-07-31)",
}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for k/n. Returns (point, lo, hi)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def load_member_tier() -> dict[str, str]:
    """Resolved-member -> completeness tier, from the committed v3 map CSV (rows with
    resolution == 'resolved'). A DOCUMENTED lookup (Talairach -> family_specified; study_specific
    and native_volume are their own tiers), NOT 'resolved => canonical'."""
    out: dict[str, str] = {}
    for r in csv.DictReader(MAP.open()):
        if r["resolution"] == "resolved" and r["resolved"]:
            out[r["resolved"]] = r["label_state"]
    return out


def reconstruct_struct(status: str, value: str, fr: str, raw: str) -> dict[str, Any]:
    """The SpecifiedTerm{verbatim, resolved, resolution} the 0.5.0 extractor WOULD emit, reconstructed
    from a FROZEN (pre-0.5.0) prediction row. The retype makes recording independent of resolution, so
    a value_not_in_literal row is no longer MISSING: it is EXTRACTED with resolved=None + the verdict."""
    if status == "EXTRACTED":
        return {"resolved": value, "verbatim": value, "resolution": "resolved"}
    if status == "DEFERRED_TO_CITATION":
        return {"deferred": True}
    fr = fr or ""
    if "underspecified" in fr:
        return {"resolved": None, "verbatim": raw, "resolution": "underspecified"}
    if "no_match" in fr:
        return {"resolved": None, "verbatim": raw, "resolution": "unrecognized"}
    return {
        "resolved": None,
        "verbatim": raw or None,
        "resolution": "unrecognized",
    }  # nothing captured


def grade_value(struct: dict[str, Any], member_tier: dict[str, str]) -> str:
    """Map v3: grade the reconstructed VALUE (not the failure_reason). Precedence: resolved member ->
    tier; else 'underspecified' -> family (BEFORE the gesture test, so 'MNI standard space' is not
    misgraded); else no verbatim -> absent; else 'unrecognized' -> named-vs-unnamed on the verbatim."""
    if struct.get("deferred"):
        return "deferred"
    resolved = struct.get("resolved")
    if resolved is not None:
        return member_tier[resolved]
    if struct.get("resolution") == "underspecified":
        return "family_specified"  # bare MNI family
    verbatim = struct.get("verbatim") or ""
    if not verbatim:
        return "absent"  # resolved=None AND nothing captured -> genuine absence
    # 'unrecognized': protocol CALL 3 named-vs-unnamed on the verbatim term
    return "absent" if any(g in verbatim.lower() for g in GESTURES) else "family_specified"


def apply_map(status: str, value: str, fr: str, raw: str, member_tier: dict[str, str]) -> str:
    """v3 (keyed on the VALUE): reconstruct the SpecifiedTerm the 0.5.0 extractor would emit from the
    frozen row, then grade it. v2 (keyed on failure_reason) is in git history; both give 11/8."""
    return grade_value(reconstruct_struct(status, value, fr, raw), member_tier)


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
    member_tier = load_member_tier()

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
            member_tier,
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
        if not ok and pid in DEMONSTRATED_CORRUPTION:
            tag += " [input-corruption DEMONSTRATED (tested; excluded)]"
        elif not ok and p.get("slice_suspicious") == "True":
            tag += " [corruption-SUSPECT (methods_not_found flag; UNTESTED, stays in denominator)]"
        rows.append(
            f"  {pid:16s} label={label:16s} -> pred={pred:16s} {'OK ' if ok else 'ERR'} {cls}{tag}"
        )

    print("=== target_space score (report-only; map v3 + frozen predictions committed) ===\n")
    print("\n".join(rows))

    # Partition errors: separate "model wrong?" from "label scoreable?". Corruption is TWO states --
    # DEMONSTRATED (tested causal -> excluded) vs SUSPECT (flag only, UNTESTED -> STAYS in the denominator).
    unreachable = [p for p in errors if labels[p] == "native_volume"]  # CALL 7 -> can't be scored
    demonstrated = [p for p in errors if p in DEMONSTRATED_CORRUPTION]  # TESTED causal -> excluded
    suspect = [
        p
        for p in errors
        if preds[p].get("slice_suspicious") == "True" and p not in DEMONSTRATED_CORRUPTION
    ]  # flag only, untested -> STAYS in the accuracy denominator, flagged
    reach_acc = [p for p in errors if p not in unreachable and p not in demonstrated]
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
        f"  {len(demonstrated)} upstream INPUT-CORRUPTION, DEMONSTRATED (tested causal -> EXCLUDED): {sorted(demonstrated)}"
    )
    for pid in sorted(demonstrated):
        print(f"     -- {pid}: {DEMONSTRATED_CORRUPTION[pid]}")
    print(
        f"  {len(suspect)} corruption-SUSPECT (methods_not_found flag, UNTESTED -> STAYS in denominator): {sorted(suspect)}"
    )
    print(
        "     -- the flag SUSPECTS; causation needs a cited run (cole: flagged, tested, REFUTED)."
    )

    # Blind correct-rate, both denominators, with Wilson 95% intervals
    blind = [p for p in correct + errors if p not in NON_BLIND]
    blind_c = [p for p in correct if p not in NON_BLIND]
    excl = set(unreachable) | set(
        demonstrated
    )  # ONLY demonstrated corruption excluded; suspect stays IN
    reach_blind = [p for p in blind if p not in excl]
    reach_c = [p for p in blind_c if p not in excl]
    pa, la, ha = wilson(len(blind_c), len(blind))
    pb, lb, hb = wilson(len(reach_c), len(reach_blind))
    print("\n=== blind correct-rate (Wilson 95%) — both denominators ===")
    print(f"  all blind        {len(blind_c)}/{len(blind)} = {pa:.1%}  [{la:.0%}, {ha:.0%}]")
    print(
        f"  reachable-only   {len(reach_c)}/{len(reach_blind)} = {pb:.1%}  [{lb:.0%}, {hb:.0%}]  "
        f"(excludes {len(excl)}: {len(unreachable)} unreachable-leak + {len(demonstrated)} demonstrated-corruption; suspect stays IN)"
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
