"""Score base_pipeline predictions against the committed v1.3 ground-truth labels — TIER A and TIER B.

Tier A = strict identity (normalize + strip-version + set-membership; NO alias table, NO KB).
Tier B = Tier A + KB recognize() + the PRE-REGISTERED alias table (ground_truth/tier_b_aliases.csv).
Per protocol line 252 the alias table must be committed BEFORE Tier B is scored; this script reads it
from that committed file, so the table cannot be tuned after seeing scores.

Denominator: N=17 BLIND papers. The 2 protocol-example rows (chen, viduarre) are author-adjudicated,
not blind, and are EXCLUDED from the rate. viduarre is reported SEPARATELY as the fabrication case.

Predictions: read from the FROZEN, committed snapshot ground_truth/predictions_v040_frozen.csv (the
durable record the first number was computed against — base_pipeline is non-stationary, so the
gitignored batch is not reproducible). Falls back to the gitignored batch dir only if the frozen file
is absent. Set SCORER_SOURCE=batch to force the batch dir (used to prove the two agree). Report-only.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

from extractor_mvp.base_pipeline_match import matches_tier_a, matches_tier_b, normalize
from extractor_mvp.pdf_loader import load_pdf_text

REPO = Path(__file__).resolve().parents[1]
LABELS = REPO / "ground_truth" / "base_pipeline_labels_v1.csv"
FROZEN = REPO / "ground_truth" / "predictions_v040_frozen.csv"
ALIASES = REPO / "ground_truth" / "tier_b_aliases.csv"
BATCH = REPO / "extractor_mvp" / "results" / "batch_v040_labelset"
CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
PDF = {  # paper_id -> filename (for the fabrication vs deferral-recognition text check)
    "poldrack_2015": "Poldrack_2015.pdf",
    "viduarre_2017": "Viduarre_2017.pdf",
}

_STATUS_FAM = {  # prediction extraction-status -> label status family
    "EXTRACTED": "REPORTED",
    "DEFERRED_TO_CITATION": "DEFERRED_TO_CITATION",
    "MISSING_FROM_PAPER": "NOT_REPORTED",  # a MISSING prediction is the honest "nothing named"
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


def _read_frozen() -> tuple[dict, dict]:
    rows = list(csv.DictReader(ln for ln in FROZEN.open() if not ln.startswith("#")))
    agg = {
        r["paper_id"]: {
            "maj_status": r["maj_status"],
            "stats": [r["draw1_status"], r["draw2_status"], r["draw3_status"]],
            "vals": [r["draw1_value"], r["draw2_value"], r["draw3_value"]],
        }
        for r in rows
    }
    methods = {r["paper_id"]: set(r["methods_found_via"].split("|")) for r in rows}
    return agg, methods


def _read_batch() -> tuple[dict, dict]:
    agg = json.load(open(BATCH / "aggregate.json"))
    methods: dict[str, set[str]] = {}
    for d in (1, 2, 3):
        for r in csv.DictReader(open(BATCH / f"draw_{d}" / "summary.csv")):
            methods.setdefault(r["paper_id"], set()).add(r.get("methods_found_via", ""))
    return agg, methods


def _load() -> tuple[dict, dict, dict]:
    labels = {r["paper_id"]: r for r in csv.DictReader(open(LABELS))}
    src = os.environ.get("SCORER_SOURCE", "auto")
    if src == "batch" or (src == "auto" and not FROZEN.exists()):
        agg, methods = _read_batch()
    else:
        agg, methods = _read_frozen()
    return labels, agg, methods


def _alias_map() -> dict[str, str]:
    """The committed pre-registered alias table: normalized surface form -> canonical id."""
    return {normalize(r["surface_form"]): r["canonical_id"] for r in csv.DictReader(open(ALIASES))}


def _tier_b(pred: str, label: list[str], amap: dict[str, str]) -> bool:
    """Tier B = matches_tier_b (Tier A + KB recognize + builtin toolbox aliases) + committed CSV table."""
    if matches_tier_b([pred] if pred else [], label):
        return True
    pc = amap.get(normalize(pred)) if pred else None
    return pc is not None and any(amap.get(normalize(x)) == pc for x in label)


def _value_in_paper(paper_id: str, value: str) -> bool:
    full, _ = load_pdf_text(CORPUS / PDF[paper_id])
    toks = [t for t in value.lower().replace("(", " ").replace(")", " ").split() if len(t) > 3]
    # "present" = the distinctive multiword phrase's tokens co-occur (loose: >=2 content tokens hit)
    hits = sum(1 for t in toks if t in full.lower())
    return hits >= max(2, len(toks) - 1)


# poldrack is a contested boundary, not a clean extractor error — recorded, not counted as unambiguous.
_POLDRACK_NOTE = (
    "poldrack_2015 (CONTESTED, not a clean error): the label DEFERRED is author-adjudicated by "
    "reading citation 45 (Power 2014 — a methods paper, not a pipeline spec), a judgment single-pass "
    "extraction structurally cannot make. The extractor's 'Washington University pipeline' extracts a "
    "REAL provenance phrase; distinguishing it from a name needs citation-aware review. Motivating case "
    "for a citation-reading reviewer component (backlog); NOT scored as an unambiguous extractor error."
)


def main() -> int:
    labels, agg, methods = _load()
    amap = _alias_map()
    blind = [pid for pid in labels if "(EXAMPLE)" not in pid]
    assert len(blind) == 17, f"expected 17 blind papers, got {len(blind)}"

    status_ok = 0
    va_num = va_den = 0  # Tier-A value match
    vb_num = 0  # Tier-B value match (same denominator va_den)
    tier_a_full = tier_b_full = 0
    tier_b_recovered: list[str] = []
    errors: dict[str, str] = {}  # clear errors
    contested: dict[str, str] = {}
    rows = []
    for pid in blind:
        lab = labels[pid]
        lstat = lab["status"]
        lvals = [v.strip() for v in lab["value"].split(";") if v.strip()]
        a = agg[pid]
        pfam = _STATUS_FAM.get(a["maj_status"], a["maj_status"])
        vals = [v for v in a["vals"] if v]
        pval = max(set(vals), key=vals.count) if vals else None
        sok = pfam == lstat
        status_ok += sok
        va = vb = None
        if lstat == "REPORTED" and a["maj_status"] == "EXTRACTED":
            va_den += 1
            va = matches_tier_a([pval] if pval else [], lvals)
            vb = _tier_b(pval or "", lvals, amap)
            va_num += va
            vb_num += vb
        a_full = sok and (va if lstat == "REPORTED" else True)
        b_full = sok and (vb if lstat == "REPORTED" else True)
        tier_a_full += bool(a_full)
        tier_b_full += bool(b_full)
        cls = ""
        if not a_full:
            if lstat == "REPORTED" and a["maj_status"] == "EXTRACTED" and va is False:
                cls = "TIER-B recovered" if vb else "genuine value miss"
                if vb:
                    tier_b_recovered.append(pid)
            elif lstat == "REPORTED" and a["maj_status"] == "MISSING_FROM_PAPER":
                if methods[pid] & {"fallback_full_text", "methods_not_found", ""}:
                    cls = "SLICING failure (methods_not_found -> full-text fallback)"
                elif pid == "cole_2013":
                    # A deglue causal test (AFNI48 -> "AFNI 48", K=3, 2026-07-23) still returned
                    # MISSING 3/3: with a CLEAN AFNI token the model still does not extract the bare
                    # "AFNI and Freesurfer" construction, so this is a genuine EXTRACTION failure, NOT
                    # the pypdf glue first hypothesized. See docs/findings/pdf-glue-false-missing.md.
                    cls = "EXTRACTION failure (bare 'AFNI and Freesurfer'; deglue test refutes glue cause)"
                else:
                    cls = "EXTRACTION failure"
                errors[pid] = cls
            elif lstat == "DEFERRED_TO_CITATION" and a["maj_status"] == "EXTRACTED":
                if pid == "poldrack_2015":
                    cls = "CONTESTED (deferral-recognition; author-judgment boundary)"
                    contested[pid] = cls
                else:
                    fab = not _value_in_paper(pid, pval or "")
                    cls = "FABRICATION" if fab else "DEFERRAL-RECOGNITION failure"
                    errors[pid] = cls
            else:
                cls = "other"
        rows.append((pid, lstat, a["maj_status"], pval, sok, va, vb, cls))

    print(
        f"{'paper':14} {'label':10} {'pred':10} {'pred_value':32} {'st':3} {'A':3} {'B':3} {'class'}"
    )
    print("-" * 130)
    for pid, ls, ps, pv, so, va, vb, cls in rows:
        f = lambda x: "-" if x is None else ("ok" if x else "X")  # noqa: E731
        print(
            f"{pid:14} {ls[:10]:10} {ps[:10]:10} {str(pv)[:30]:32} "
            f"{'ok' if so else 'X':3} {f(va):3} {f(vb):3} {cls}"
        )

    print("\n=== RATES (N=17 blind; Wilson 95% CI) ===")
    for name, k, n in [
        ("status agreement", status_ok, 17),
        ("Tier-A full match (status+value)", tier_a_full, 17),
        ("Tier-B full match (status+value)", tier_b_full, 17),
        ("value match | both REPORTED [A]", va_num, va_den),
        ("value match | both REPORTED [B]", vb_num, va_den),
    ]:
        p, lo, hi = wilson(k, n)
        print(f"  {name:34} {k}/{n} = {p * 100:4.1f}%  [{lo * 100:4.1f}, {hi * 100:4.1f}]")
    da = tier_a_full / 17
    db = tier_b_full / 17
    print(
        f"  A->B delta (full match): +{(db - da) * 100:.1f} pts ({tier_b_full - tier_a_full} papers)"
    )
    print(
        "\n  COVERAGE: N=17 blind of 19 analysable corpus papers. binder_1999 is UNLABELED (a status-\n"
        "  rule boundary: does its '(SPMs)' name SPM?); chen_2015's counted row inherits its label from\n"
        "  the example row (non-independent, but CCS is unambiguous). See ground_truth/README.md."
    )

    print("\n=== ERROR DECOMPOSITION (not a lump) ===")
    print(f"  Tier-B recovered (surface variant, same pipeline): {tier_b_recovered}")
    print(f"  CLEAR errors ({len(errors)}): {dict(errors)}")
    print(f"  CONTESTED ({len(contested)}): {list(contested)}")
    print(f"  scored-error count: {len(errors)} clear + {len(contested)} contested")
    print(
        "\n  CAUSE ATTRIBUTION (in-rate vs separately-reported — do not blur them). Within the N=17\n"
        "  rate there is ONE genuine model error (cole_2013), plus liu_2005 (SLICING, upstream-input:\n"
        "  MISSING correct given a bad slice) and poldrack (CONTESTED). cole is genuine: BOTH deglue\n"
        "  variants (AFNI48->'AFNI 48' and AFNI48->'AFNI', K=3 each, 2026-07-23) still returned MISSING\n"
        "  3/3 — the model does not extract bare 'AFNI and Freesurfer' even fully clean, refuting the\n"
        "  PDF-glue hypothesis. viduarre is a SECOND genuine model error (fabrication) but sits OUTSIDE\n"
        "  the rate by design (reported separately)."
    )
    print(f"\n  {_POLDRACK_NOTE}")

    print("\n=== REPORTED SEPARATELY (excluded from the rate) ===")
    vid = agg["viduarre_2017"]
    nz = [x for x in vid["vals"] if x]
    vidval = max(set(nz), key=nz.count)
    print(f"  viduarre_2017: label DEFERRED [Smith, Glasser]; pred {vid['stats']} value={vidval!r}")
    print(
        f"    -> FABRICATION on 2/3 draws ('{vidval}' absent from the paper); the value-support "
        "guard's scope (clean-span path) missed it. Out of the rate (co-adjudicated, non-blind), "
        "central to the error analysis; the guard-scope fix + re-score is the demonstrated before/after."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
