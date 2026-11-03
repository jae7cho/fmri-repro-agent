"""Count the checking pass's retries per paper under one instructor mode (2026-11-03).

Re-runs the checking pass (its pinned prompt, unchanged) once per stored paper of a batch, on the
same methods slice and the same draft the batch built (the stored ``preprocessing``), through a
``CallMeter`` client in JSON or tool-calling mode. Writes ``<out>/<mode>.json`` with every attempt
(raw reply, finish reason, parse error) and prints ONLY counts: attempts, retries, the parse
errors' types, tokens and cost. Held-out papers are refused.

Usage:
    python scripts/measure_checking_pass_retries.py --results-dir results/batch_coverage_v4 \
        --mode json --out results/checking_pass_retries --model <model>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))
sys.path.insert(0, str(_HERE.parent.parent / "src"))

from fmri_repro.spec.migrations import parse_any_version  # noqa: E402

from extractor_mvp.citation_hop import CallMeter  # noqa: E402
from extractor_mvp.methods_finder import find_methods_section  # noqa: E402
from extractor_mvp.parsed_paper import ParsedPaper  # noqa: E402
from extractor_mvp.pdf_loader import load_pdf_text  # noqa: E402
from extractor_mvp.verifier import run_verifier  # noqa: E402

HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--mode", choices=("json", "tools"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)

    rows = []
    for rec_path in sorted((a.results_dir / "papers").glob("*.json")):
        data = json.loads(rec_path.read_text(encoding="utf-8"))
        pid = data["paper_id"]
        if pid in HELD_OUT:
            raise SystemExit(f"refusing a held-out paper: {pid}")
        text, parser = load_pdf_text(Path(data["path"]))
        paper = ParsedPaper(text=find_methods_section(text).text, source=pid, parser=parser)
        meter = CallMeter()
        meter.label = "checking pass"
        t0 = time.perf_counter()
        out = run_verifier(
            paper, parse_any_version(data["preprocessing"]), a.model, client=meter.client(a.mode)
        )
        rows.append(
            {
                "paper_id": pid,
                "status": out["status"],
                "wall_s": round(time.perf_counter() - t0, 3),
                "attempts": meter.calls,
            }
        )
        n = len(meter.calls)
        errs = [c["parse_error"].split(":", 1)[0] for c in meter.calls if c["parse_error"]]
        print(
            f"{pid}: {out['status']}, attempts {n}, retries {n - 1}, "
            f"parse errors {errs or '-'}, finish {[c['finish_reason'] for c in meter.calls]}",
            flush=True,
        )
        (a.out / f"{a.mode}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")

    calls = [c for r in rows for c in r["attempts"]]
    costs = [c["cost_usd"] for c in calls]
    print(
        f"mode {a.mode}: papers {len(rows)}; status ok {sum(r['status'] == 'ok' for r in rows)}; "
        f"papers with a retry {sum(len(r['attempts']) > 1 for r in rows)}; "
        f"retries {sum(len(r['attempts']) - 1 for r in rows)}; attempts {len(calls)}; "
        f"tokens in {sum(c['input_tokens'] or 0 for c in calls)}, "
        f"out {sum(c['output_tokens'] or 0 for c in calls)}; "
        f"cost {round(sum(costs), 4) if costs and None not in costs else 'unknown for some calls'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
