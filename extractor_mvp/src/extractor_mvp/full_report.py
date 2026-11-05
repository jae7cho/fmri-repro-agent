"""One paper through the whole current setup, every model call metered (2026-11-05, fix 2 of the
author's list after stress_v1).

``aespa-report`` ran :func:`batch.process_paper` only: the first hop, the checking pass and the KB
inference arm, with no citation hop, no software scan, no data-release call and no record of what
the calls cost. The stress run of 2026-11-04 needed a scratchpad harness to do the rest; this module
is that harness, moved into the package and retired from the scratchpad.

:func:`run_paper` runs, in order:

1. :func:`batch.process_paper` with one metered client (the fMRI gate, the four extraction calls, the
   checking pass) -- every call it makes goes through the client it is given;
2. the citation hop (:func:`citation_hop.run_hop`) once per distinct reference a field defers to,
   for paper targets, against ``corpus_dirs`` (a supplement is read with the paper, fix 4);
3. call R (:func:`citation_hop.extract_data_release`) on the paper;
4. the KB software scan and its one question per mention (:mod:`software_scan`);
5. the report, rendered with the hop section.

Every attempt of every call is one entry of ``calls`` (:class:`citation_hop.CallMeter`): its label,
attempt number within the label, wall time, tokens, cost, finish reason and parse error. A retry is
an attempt above 1. A paper the fMRI gate stops, or one with no extraction, ends after step 1.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from extractor_mvp.batch import PaperResult, process_paper
from extractor_mvp.citation_hop import CallMeter, extract_data_release, json_safe, run_hop
from extractor_mvp.methods_finder import MethodsSlice
from extractor_mvp.pdf_loader import load_pdf_text
from extractor_mvp.render import to_report
from extractor_mvp.software_scan import ask_uses, scan, tool_list

#: The deferral targets the citation hop takes (Fork E, DESIGN_citation_hop.md). Not "supplement"
#: since fix 4 (2026-11-05): "see Supplementary Material" is not a citation, and the paper's own
#: supplement is read with the paper or reported as not read (batch.load_supplement).
HOP_KINDS: tuple[str, ...] = ("paper",)


@dataclass
class FullResult:
    """What :func:`run_paper` produced. ``record`` is the paper JSON (as ``run_batch`` writes it)
    plus ``second_hop``, ``data_release``, ``software_mentions``, ``citing_software``, ``hop_errors``
    and ``run`` (the per-call log and its totals)."""

    paper_id: str
    status: str
    report: str | None
    record: dict[str, Any] | None
    calls: list[dict[str, Any]] = field(default_factory=list)
    wall_s: float = 0.0
    first: PaperResult | None = None

    @property
    def cost_usd(self) -> float | None:
        costs = [c.get("cost_usd") for c in self.calls]
        return None if any(c is None for c in costs) else round(sum(costs), 4)  # type: ignore[arg-type]

    @property
    def retries(self) -> int:
        return sum(1 for c in self.calls if int(c.get("attempt") or 1) > 1)


def run_totals(calls: list[dict[str, Any]], wall_s: float) -> dict[str, Any]:
    costs = [c.get("cost_usd") for c in calls]
    return {
        "wall_s": round(wall_s, 1),
        "n_calls": len(calls),
        "retries": sum(1 for c in calls if int(c.get("attempt") or 1) > 1),
        "parse_errors": sum(1 for c in calls if c.get("parse_error")),
        "cost_usd": None if any(c is None for c in costs) else round(sum(costs), 4),  # type: ignore[arg-type]
    }


def run_paper(
    paper_id: str,
    pdf: Path,
    model: str,
    corpus_dirs: list[Path],
    *,
    meter: CallMeter | None = None,
) -> FullResult:
    """The whole setup for one PDF. Never raises for a bad paper (``process_paper``'s contract); a
    hop that raises is recorded in ``hop_errors`` and the rest runs."""
    meter = meter or CallMeter()
    meter.label = ""  # the first hop's calls are labelled by their response model
    t0 = time.perf_counter()
    first = process_paper(paper_id, pdf, model, client=meter.client())
    record: dict[str, Any] | None = None
    if first.extraction_json is not None:
        record = {
            "paper_id": paper_id,
            "path": str(pdf),
            "status": first.status,
            **first.extraction_json,
        }
    if record is None or "preprocessing" not in record:
        wall = time.perf_counter() - t0
        if record is not None:
            record["run"] = {**run_totals(meter.calls, wall), "calls": meter.calls}
        return FullResult(
            paper_id, first.status, first.report, record, meter.calls, round(wall, 1), first
        )

    from fmri_repro.spec.migrations import parse_any_version

    prep = parse_any_version(record["preprocessing"])
    citing_text, _parser = load_pdf_text(pdf)
    refs: list[str] = []
    for d in record.get("deferred_fields") or []:
        if d.get("target_kind") in HOP_KINDS and d.get("ref_string") not in refs:
            refs.append(d["ref_string"])
    hops: list[dict[str, Any]] = []
    hop_errors: list[dict[str, Any]] = []
    for ref in refs:
        try:
            hops.extend(
                run_hop(
                    citing_text,
                    prep,
                    ref,
                    corpus_dirs,
                    model,
                    verifier=record.get("verifier"),
                    meter=meter,
                )
            )
        except Exception as exc:  # a hop never costs the paper its report
            hop_errors.append({"ref": ref, "error": f"{type(exc).__name__}: {exc}"[:500]})
    release = extract_data_release(citing_text, model, client=meter.client(), meter=meter)
    try:
        uses = ask_uses(scan(json_safe(citing_text)), model, client=meter.client(), meter=meter)
    except Exception as exc:
        uses = []
        hop_errors.append({"ref": "software_scan", "error": f"{type(exc).__name__}: {exc}"[:500]})
    software = tool_list(uses)
    record.update(
        second_hop=hops,
        hop_errors=hop_errors,
        data_release=release,
        software_mentions=uses,
        citing_software=software,
    )
    report: str | None
    try:
        report = render_record(record)
    except Exception as exc:  # recorded, as process_paper records its own render failure
        report = None
        record["render_error"] = f"{type(exc).__name__}: {exc}"[:500]
    wall = time.perf_counter() - t0
    record["run"] = {**run_totals(meter.calls, wall), "calls": meter.calls}
    return FullResult(paper_id, first.status, report, record, meter.calls, round(wall, 1), first)


def render_record(record: dict[str, Any]) -> str:
    """The report from a stored full record (no model call): the first hop's record and, when
    present, the hop section's inputs. ``scripts/rerender_reports.py`` renders the same way."""
    if record.get("status") == "not_fmri":
        from extractor_mvp.fmri_gate import to_not_fmri_report

        stopped: str = to_not_fmri_report(record["paper_id"], record["fmri_gate"])
        return stopped
    from fmri_repro.spec.migrations import parse_any_version

    prep = parse_any_version(record["preprocessing"])
    extra: dict[str, Any] = {}
    if record.get("multiple_pipelines") is not None:
        extra["multiple_pipelines"] = record["multiple_pipelines"]
    if record.get("verifier") is not None:
        extra["verifier"] = record["verifier"]
    rec = record.get("motion_inference")
    if isinstance(rec, dict):
        extra["motion_inference"] = SimpleNamespace(**rec)
    for key in ("second_hop", "data_release", "citing_software", "supplement"):
        if key in record:
            extra[key] = record[key]
    methods = MethodsSlice(text="", **record["methods"])
    report: str = to_report(prep, source=record["paper_id"], methods_slice=methods, **extra)
    return report
