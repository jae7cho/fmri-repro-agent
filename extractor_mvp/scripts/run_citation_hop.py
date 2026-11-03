"""Run the citation hop for one stored citing record (DESIGN_citation_hop.md, case one).

Reads the citing paper's stored record (its preprocessing, checking pass and the rest), its full
text for the reference list, and a corpus folder of local PDFs. Writes ``<out>/<paper>.second_hop.json``
and the citing paper's report re-rendered with the second-hop section, ``<out>/<paper>.md``.

Prints ONLY what the hop asked and how it resolved, with wall time, tokens and cost: never a value
read in the cited paper (the author reads the cited paper first and records a key).

Usage:
    python scripts/run_citation_hop.py --record results/batch_coverage_v4/papers/gracia-tabuenca_2024.json \
        --pdf /path/Gracia-Tabuenca_2024.pdf --ref "Hagler et al. (2019)" \
        --corpus-dir /path/tested_lit/sfn_batch --out results/hop_case1 --model <model>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))
sys.path.insert(0, str(_HERE.parent.parent / "src"))

from fmri_repro.spec.migrations import parse_any_version  # noqa: E402

from extractor_mvp.citation_hop import CallMeter, run_hop  # noqa: E402
from extractor_mvp.methods_finder import MethodsSlice  # noqa: E402
from extractor_mvp.pdf_loader import load_pdf_text  # noqa: E402
from extractor_mvp.render import to_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--corpus-dir", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", required=True)
    a = ap.parse_args(argv)

    data = json.loads(a.record.read_text(encoding="utf-8"))
    pid = data["paper_id"]
    if a.out.resolve() == a.record.parent.resolve():
        raise SystemExit("refusing to write beside the stored record")
    a.out.mkdir(parents=True, exist_ok=True)
    prep = parse_any_version(data["preprocessing"])
    citing_text, _parser = load_pdf_text(a.pdf)

    t0 = time.perf_counter()
    meter = CallMeter()
    hop = run_hop(
        citing_text,
        prep,
        a.ref,
        a.corpus_dir,
        a.model,
        verifier=data.get("verifier"),
        meter=meter,
    )
    wall = round(time.perf_counter() - t0, 3)
    (a.out / f"{pid}.second_hop.json").write_text(json.dumps(hop, indent=1), encoding="utf-8")

    verifier = data.get("verifier")
    extra: dict[str, Any] = {
        "verifier": verifier,
        "multiple_pipelines": (verifier or {}).get("multiple_pipelines"),
        "second_hop": hop,
    }
    rec = data.get("motion_inference")
    if isinstance(rec, dict):
        extra["motion_inference"] = SimpleNamespace(**rec)
    report = to_report(
        prep, source=pid, methods_slice=MethodsSlice(text="", **data["methods"]), **extra
    )
    (a.out / f"{pid}.md").write_text(report, encoding="utf-8")

    for r in hop:
        print(f"target {r['part']!r}: status {r.get('status')}")
        print(f"  reference entry: {r['reference']['state']}")
        target = r.get("target") or {}
        print(
            f"  target: {target.get('state')}"
            + (
                f" ({Path(target['path']).name}, doi_confirmed={target.get('doi_confirmed')})"
                if target.get("path")
                else ""
            )
        )
        if r.get("methods"):
            print(
                f"  cited methods slice: found_via={r['methods']['found_via']}, {r['methods']['chars']} chars"
            )
        print(f"  software list asked: {r['scope']['software']}")
        print(
            f"  rows outside calls T and S (not asked): {', '.join(r['scope']['rows_outside_calls']) or '-'}"
        )
        print(f"  fields asked: {len(r['scope']['asked'])}")
        for q in r["scope"]["asked"]:
            print(f"    {q['field']}  ({q['why']})")
        v = r.get("verifier") or {}
        print(f"  checking pass: {v.get('status')}")
        for c in r.get("calls") or []:
            print(
                f"  call {c['call']}: {c['wall_s']} s, in {c['input_tokens']} tok, out {c['output_tokens']} tok, "
                f"cost {c['cost_usd']}"
            )
        print(f"  hop wall time: {r.get('wall_time_s')} s")
    costs = [c["cost_usd"] for c in meter.calls]
    print(
        f"total wall {wall} s; model calls {len(meter.calls)}; "
        f"tokens in {sum(c['input_tokens'] or 0 for c in meter.calls)}, out {sum(c['output_tokens'] or 0 for c in meter.calls)}; "
        f"cost {round(sum(costs), 4) if costs and None not in costs else 'unknown for some calls'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
