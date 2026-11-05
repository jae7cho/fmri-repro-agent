"""The fMRI gate (2026-11-05, fix 1b of the author's list after stress_v1): one cheap call before
extraction asks whether the paper acquires or analyses fMRI, with the sentence that shows it.

Gao_2026 (stress_v1) analyses structural T1 images and EEG and no fMRI at all; the extractor drew a
fMRI preprocessing protocol from it anyway (segmentation, coregistration, normalization, smoothing,
an ICA and a temporal filter from the EEG). A paper the gate answers "no" for, with a sentence that
resolves in its text, gets a report that says "no fMRI in this paper" and nothing else: no
extraction runs.

The gate stops a paper only on that evidence. "yes", "unclear", a "no" whose sentence does not
resolve, and a failed call all let extraction run, and the record says which. The text it reads is
the paper before its reference list (a reference title naming fMRI is not fMRI in the paper), with
every double quotation mark made an apostrophe so a copied sentence needs no escaping
(``citation_hop.json_safe``, one character for one).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from extractor_mvp.span_resolver import resolve_quote

FMRI_GATE_PROMPT = """\
You are deciding whether a paper is in scope for a tool that reports how fMRI data were
preprocessed. Answer from the paper text below only.
fmri: "yes" when the paper itself acquires or analyses functional MRI (BOLD) data -- its own or a
shared dataset's, task or resting state; "no" when it does not (for example only structural MRI,
only diffusion MRI, EEG or MEG, PET, behaviour, genetics, or simulations); "unclear" when the text
does not let you tell.
data: the data the paper analyses, in a few words.
quote: one sentence copied EXACTLY from the text that shows your answer: for "yes" a sentence about
the fMRI data or its processing; for "no" a sentence that says what data the paper does analyse.

Paper text:
\"\"\"
{text}
\"\"\"
"""


class FmriGateAnswer(BaseModel):
    fmri: Literal["yes", "no", "unclear"] = "unclear"
    data: str = ""
    quote: str | None = None


def gate_text(text: str) -> str:
    """The text the gate reads: the paper before its reference list, double quotes made apostrophes."""
    from extractor_mvp.citation_hop import json_safe
    from extractor_mvp.software_scan import _body_end

    return json_safe(text[: _body_end(text)])


def ask_fmri(text: str, model: str, *, client: Any | None = None, meter: Any | None = None) -> dict:
    """One call; returns the gate record and never raises. ``stop`` is True only for a "no" whose
    sentence resolves in the text the gate read."""
    from extractor_mvp.citation_hop import _create

    body = gate_text(text)
    if meter is not None:
        meter.label = "fmri_gate"
    try:
        if client is None:
            from extractor_mvp.extractor import build_client

            client = build_client()
        ans: FmriGateAnswer = _create(
            client, model, FMRI_GATE_PROMPT.format(text=body), FmriGateAnswer
        )
    except Exception as exc:  # the gate never fails a paper: extraction runs
        return {
            "status": "call_failed",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "fmri": None,
            "data": None,
            "quote": None,
            "quote_resolved": None,
            "stop": False,
        }
    resolved = bool(ans.quote) and resolve_quote(ans.quote or "", body).span is not None
    return {
        "status": "ok",
        "error": None,
        "fmri": ans.fmri,
        "data": ans.data,
        "quote": ans.quote,
        "quote_resolved": resolved,
        "stop": ans.fmri == "no" and resolved,
    }


def to_not_fmri_report(source: str, gate: dict) -> str:
    """The whole report for a paper the gate stopped. Not a protocol and not in REPORT_SURFACES:
    there is nothing to cover."""
    quote = " ".join((gate.get("quote") or "").split())
    return (
        f"# Replication Protocol — {source}\n\n"
        "No fMRI in this paper. A first check of the paper's text (before its reference list) found "
        "no functional MRI acquired or analysed, so no preprocessing was extracted and no COBIDAS "
        "coverage is reported.\n\n"
        f"The paper analyses: {gate.get('data') or 'not stated'}  «{quote}»\n"
    )
