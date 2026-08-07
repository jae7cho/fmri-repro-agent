"""Score the REAL 0.5.0 re-extraction (results/batch_v050_labelset) against the v1.2 labels.

Unlike score_target_space.py (which reads FROZEN pre-retype predictions and TRANSLATES their columns),
this reads genuine 0.5.0 output: the SpecifiedTerm{verbatim, resolved, resolution} the retyped extractor
actually wrote. It aggregates K=3, writes a durable real-shape predictions CSV, and grades each paper's
REAL value via map v3's grade_value.

Three things it separates, so no claim launders another:
  1. the value_not_in_literal FIX: frozen value_not_in_literal papers that now record the term (EXTRACTED);
  2. the quote_not_found remainder: a value_not_in_literal paper still MISSING, graded off the diagnostic
     raw -- the OLD side-channel, NOT the fix (agtzidis; documented pypdf-mangle, span-resolution-hard-drop.md);
  3. NON-STATIONARITY movers: rows whose grade differs from the frozen-translated grade for reasons
     orthogonal to the retype (fresh K=3, the model's extraction varies run to run).

Run:  cd extractor_mvp && uv run python score_v050_reextraction.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from score_target_space import (  # reuse the committed v3 grader + Wilson + policy
    DEMONSTRATED_CORRUPTION,
    NON_BLIND,
    grade_value,
    load_member_tier,
    reconstruct_struct,
    wilson,
)

REPO = Path(__file__).resolve().parents[1]
GT = REPO / "ground_truth"
LABELS = GT / "target_space_labels_v1.csv"
FROZEN = GT / "target_space_predictions_v040_frozen.csv"
OUT_CSV = GT / "target_space_predictions_v050.csv"
BATCH = Path(__file__).resolve().parent / "results" / "batch_v050_labelset"
DRAWS = ["draw_1", "draw_2", "draw_3"]
DOTTED = "spatial_normalization.target_space"


def _target_space(paper_json: dict[str, Any]) -> dict[str, Any]:
    ts = None
    for st in paper_json.get("preprocessing", {}).get("steps", []):
        if isinstance(st, dict) and "target_space" in st:
            ts = st["target_space"]
            break
    diag = next(
        (d for d in paper_json.get("diagnostics", []) if DOTTED in str(d.get("field", ""))), None
    )
    ext = (ts or {}).get("extraction", {})
    return {
        "status": ext.get("status"),
        "value": ext.get("value") if ext.get("status") == "EXTRACTED" else None,
        "reason": ((ts or {}).get("inference", {}) or {}).get("reason"),
        "diag_raw": (diag or {}).get("raw_value"),
        "diag_reason": (diag or {}).get("failure_reason"),
    }


def _effective_struct(rec: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """(struct-for-grade_value, scoring_mode): 'fix' = a real EXTRACTED SpecifiedTerm carries the grade;
    'fallback' = MISSING row graded off the diagnostic raw (the OLD mechanism); 'deferred'; 'absent'."""
    if rec["status"] == "EXTRACTED" and isinstance(rec["value"], dict):
        return rec["value"], "fix"
    if rec["status"] == "DEFERRED_TO_CITATION":
        return {"deferred": True}, "deferred"
    raw, dr = rec["diag_raw"], rec["diag_reason"] or ""
    if not raw:
        return {"resolved": None, "verbatim": None, "resolution": "unrecognized"}, "absent"
    resolution = "underspecified" if "underspecified" in dr else "unrecognized"
    return {"resolved": None, "verbatim": raw, "resolution": resolution}, "fallback"


def main() -> int:
    if not (BATCH / "draw_1" / "papers").exists():
        print(f"0.5.0 draws not found under {BATCH} — run the batch first.")
        return 1
    labels = {r["paper_id"]: r["target_space_state"] for r in csv.DictReader(LABELS.open())}
    frozen = {
        r["paper_id"]: r
        for r in csv.DictReader(ln for ln in FROZEN.open() if not ln.startswith("#"))
    }
    member_tier = load_member_tier()

    per_paper: dict[str, list[dict[str, Any]]] = {}
    for draw in DRAWS:
        for jf in sorted((BATCH / draw / "papers").glob("*.json")):
            d = json.loads(jf.read_text())
            per_paper.setdefault(d["paper_id"], []).append(_target_space(d))

    csv_rows: list[dict[str, Any]] = []
    correct: list[str] = []
    errors: list[str] = []
    fix_flips: list[str] = []
    quote_not_found: list[str] = []
    movers: list[tuple[str, str, str]] = []
    for pid in sorted(labels):
        if pid not in per_paper:
            continue
        recs = per_paper[pid]
        statuses = [r["status"] for r in recs]
        maj = Counter(statuses).most_common(1)[0][0]
        stable = len(set(statuses)) == 1
        rec = next(r for r in recs if r["status"] == maj)
        struct, mode = _effective_struct(rec)
        pred = grade_value(struct, member_tier)
        ok = pred == labels[pid]
        (correct if ok else errors).append(pid)

        fr = frozen.get(pid, {})
        vnil = "value_not_in_literal" in (fr.get("failure_reason") or "")
        if vnil and maj == "EXTRACTED":
            fix_flips.append(pid)
        elif vnil and mode == "fallback":
            quote_not_found.append(pid)
        # non-stationarity mover: grade changed vs the frozen-translated grade
        frozen_pred = grade_value(
            reconstruct_struct(
                fr.get("extractor_status", ""),
                fr.get("extractor_value", ""),
                fr.get("failure_reason", ""),
                fr.get("raw_diagnostic", ""),
            ),
            member_tier,
        )
        moved = frozen_pred != pred
        if moved:
            movers.append((pid, frozen_pred, pred))
        verb = struct.get("verbatim") if isinstance(struct, dict) else None
        csv_rows.append(
            {
                "paper_id": pid,
                "k3_status": "/".join(statuses),
                "maj_status": maj,
                "resolved": struct.get("resolved") if isinstance(struct, dict) else "",
                "verbatim": verb or "",
                "resolution": struct.get("resolution", "") if isinstance(struct, dict) else "",
                "diag_raw": rec["diag_raw"] or "",
                "diag_reason": rec["diag_reason"] or "",
                "scoring_mode": mode,
                "stable": "yes" if stable else "no",
                "v3_grade": pred,
                "label": labels[pid],
                "correct": "yes" if ok else "no",
            }
        )

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)

    print("=== 0.5.0 RE-EXTRACTION vs labels (REAL output; map v3) ===\n")
    for r in csv_rows:
        flag = "" if r["correct"] == "yes" else " ERR"
        note = (
            " [quote_not_found -> scored via diagnostic raw = OLD mechanism]"
            if r["scoring_mode"] == "fallback"
            else ""
        )
        print(
            f"  {r['paper_id']:16s} {r['maj_status'][:8]:8s} verbatim={str(r['verbatim'])[:24]:24s}"
            f" -> {r['v3_grade']:16s} {'OK' if r['correct'] == 'yes' else 'ER'}{flag}{note}"
            f"{'' if r['stable'] == 'yes' else ' [K3-UNSTABLE]'}"
        )

    print("\n=== the value_not_in_literal FIX, on real output ===")
    print(
        f"  {len(fix_flips)}/12 flipped to EXTRACTED with the term recorded (verbatim preserved): {sorted(fix_flips)}"
    )
    print(
        f"  {len(quote_not_found)}/12 STILL MISSING via quote_not_found (pypdf-mangle; scored via diagnostic raw = OLD mechanism, NOT the fix): {sorted(quote_not_found)}"
    )

    print(
        "\n=== NON-STATIONARITY movers (grade != frozen-translated grade; orthogonal to the retype) ==="
    )
    for pid, fz, rl in movers:
        print(
            f"  {pid}: frozen-translated={fz} -> real 0.5.0={rl}  (fresh K=3; see per-draw status)"
        )

    blind = [p for p in correct + errors if p not in NON_BLIND]
    blind_c = [p for p in correct if p not in NON_BLIND]
    excl = {p for p in errors if labels[p] == "native_volume"} | set(DEMONSTRATED_CORRUPTION)
    reach = [p for p in blind if p not in excl]
    reach_c = [p for p in blind_c if p not in excl]
    pa, la, ha = wilson(len(blind_c), len(blind))
    pb, lb, hb = wilson(len(reach_c), len(reach))
    print("\n=== score (real 0.5.0 output) vs frozen (translated) ===")
    print(f"  total          {len(correct)} correct / {len(errors)} error        (frozen: 11 / 8)")
    print(
        f"  all blind      {len(blind_c)}/{len(blind)} = {pa:.1%} [{la:.0%},{ha:.0%}]  (frozen: 11/17 = 64.7%)"
    )
    print(
        f"  reachable-only {len(reach_c)}/{len(reach)} = {pb:.1%} [{lb:.0%},{hb:.0%}]  (frozen: 11/14 = 78.6%)"
    )
    print(f"\n  wrote {OUT_CSV.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
