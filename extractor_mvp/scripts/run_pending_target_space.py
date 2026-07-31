"""One-shot K=3 runs for the two PENDING target_space items (needs bedrock creds).

Closes both open items in docs/findings/target_space-pending-runs.md, whose outcomes are PRE-COMMITTED
so neither run can be read one-directionally.

  liu_2005 : feed the de-interleaved slice (ground_truth/liu_2005_deinterleaved_methods.txt) directly as
             ParsedPaper.text, BYPASSING find_methods_section -- which is where the two-column
             interleaving corruption enters on the real PDF. Reports target_space (the new test: does
             Talairach appear?) AND base_pipeline_name (the slice-VALIDITY sanity check: this slice must
             recover BrainVoyager, matching the known-good base_pipeline 3/3 from 2026-07-23; if it does
             NOT, the reconstructed slice is wrong -- HALT, do not read the target_space result).
  binder   : normal path (load PDF -> find_methods_section -> extract). It was never in the batch.

Run (from the extractor_mvp/ package dir, like the other scripts):
      cd extractor_mvp && AWS_PROFILE=<bedrock-capable-profile> uv run python scripts/run_pending_target_space.py
Model pin == the frozen batch (batch_v040_labelset): bedrock sonnet-4-5, so results are comparable.
"""

from __future__ import annotations

from pathlib import Path

from extractor_mvp.extractor import build_client, extract
from extractor_mvp.methods_finder import find_methods_section
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.pdf_loader import load_pdf_text

MODEL = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
K = 3
REPO = Path(__file__).resolve().parents[2]
SLICE = REPO / "ground_truth" / "liu_2005_deinterleaved_methods.txt"
BINDER_PDF = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch/Binder_1999.pdf")


def _field(prep: object, attr: str) -> dict | None:
    for st in prep.steps:  # type: ignore[attr-defined]
        d = st.model_dump(mode="json")
        val = d.get(attr)
        if isinstance(val, dict):
            return val
    return None


def _diag(diags: list, field_substr: str) -> tuple[str | None, str | None]:
    for x in diags:
        if field_substr in str(getattr(x, "field", "")):
            return getattr(x, "failure_reason", None), getattr(x, "raw_value", None)
    return None, None


def run(label: str, text: str, client: object, report_base_pipeline: bool = False) -> None:
    print(f"\n===== {label}  (K={K}, model={MODEL}) =====")
    for k in range(1, K + 1):
        paper = ParsedPaper(text=text, source=label, parser="manual")
        prep, diags, _ = extract(paper, MODEL, client=client)
        ts = _field(prep, "target_space")
        fr, raw = _diag(diags, "target_space")
        status = ts["extraction"]["status"] if ts else "NO_STEP"
        value = ts["extraction"].get("value") if ts else None
        line = f"  draw{k}: target_space status={status} value={value!r} failure_reason={fr!r} raw={raw!r}"
        if report_base_pipeline:
            bp = _field(prep, "base_pipeline_name")
            bstatus = bp["extraction"]["status"] if bp else "NO_STEP"
            bval = bp["extraction"].get("value") if bp else None
            line += (
                f"  |  base_pipeline status={bstatus} value={bval!r}  (BrainVoyager => slice OK)"
            )
        print(line)


def main() -> int:
    client = build_client()
    # liu_2005: de-interleaved slice fed directly (bypass find_methods_section)
    run("liu_2005 [de-interleaved slice]", SLICE.read_text(), client, report_base_pipeline=True)
    # binder: normal path
    text, parser = load_pdf_text(BINDER_PDF)
    if parser == "failed":
        print("\nbinder_1999: pypdf returned no text -- cannot run.")
    else:
        run("binder_1999 [normal path]", find_methods_section(text).text, client)
    print(
        "\nRead against docs/findings/target_space-pending-runs.md (outcomes pre-committed). "
        "For liu_2005, CONFIRM base_pipeline recovered BrainVoyager before reading target_space."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
