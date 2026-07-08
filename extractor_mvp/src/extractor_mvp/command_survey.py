"""Standalone, OPTIONAL command-survey tool.

This is NOT wired into the deterministic extraction pipeline (``batch.py`` /
``extractor.py`` / ``pdf_loader.py`` are untouched). It is a separate script that
inventories the specific software COMMANDS / PROGRAMS named in a folder of PDFs
(AFNI, FSL, SPM, FreeSurfer, ANTs) and emits a report.

PURPOSE: measure command-level method reporting -- how often papers name a specific
program (``3dDespike``, ``FLIRT``, ``recon-all``) versus describing steps in prose.
This is a SURVEY / INVENTORY ONLY. It makes NO judgment about whether a command is
deprecated, recommended, or best-practice -- that requires grounding in each tool's
docs/changelogs and is a separate task; no such opinions are encoded here.

Extraction is full-text (all pages) via pypdf; matching is stdlib ``re`` only (no new
dependency). False positives are actively excluded:

* AFNI ``@``-scripts are matched from a curated allowlist of real program names, never a
  generic ``@\\w+`` (which would swallow email handles / affiliations).
* AFNI ``1d``-programs are matched from a curated allowlist (the bare ``1d[A-Za-z]...``
  pattern false-fires on prose like "1day"); ``3d[A-Z]...`` is specific enough to keep.
* Collision-prone FSL words (``BET``, ``FAST``, ``FIRST``) are counted only when an FSL
  context token appears nearby.
* Any token inside an email-like string, or immediately preceded by ``@`` (other than an
  allowlisted ``@``-script), is dropped.

The optional per-command FUNCTION tag is drawn from a conservative SEED mapping keyed to
each tool's primary documented purpose; commands whose main role is outside the fixed
function vocabulary are tagged ``unknown`` rather than guessed.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import re
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Function vocabulary + conservative seed (primary documented purpose only)
# ---------------------------------------------------------------------------

_FUNCTION_VOCAB = frozenset(
    {
        "motion",
        "slice-timing",
        "distortion",
        "registration-linear",
        "registration-nonlinear",
        "skull-strip",
        "despike",
        "nuisance-regression",
        "ica-denoise",
        "smoothing",
        "surface-recon",
        "bias-correction",
    }
)

# Keys are the command token lowercased. Only mappings whose primary documented purpose
# lands squarely inside _FUNCTION_VOCAB are encoded; everything else resolves to "unknown"
# (e.g. FAST/FIRST -> segmentation, FEAT/afni_proc.py -> whole-pipeline, fslmaths -> utility
# are all outside the vocabulary and are deliberately left unknown).
_FUNCTION_SEED: dict[str, str] = {
    # AFNI (per `3dX -help` / afni program list)
    "3ddespike": "despike",
    "3dvolreg": "motion",
    "3dtshift": "slice-timing",
    "3dskullstrip": "skull-strip",
    "3dautomask": "skull-strip",
    "3dallineate": "registration-linear",
    "3dqwarp": "registration-nonlinear",
    "3dtproject": "nuisance-regression",
    "3dblurtofwhm": "smoothing",
    "3dunifize": "bias-correction",
    "align_epi_anat.py": "registration-linear",
    "@sswarper": "skull-strip",
    # FSL (per FSL wiki)
    "mcflirt": "motion",
    "fsl_motion_outliers": "motion",
    "flirt": "registration-linear",
    "fnirt": "registration-nonlinear",
    "topup": "distortion",
    "melodic": "ica-denoise",
    "fsl_regfilt": "ica-denoise",
    "ica-aroma": "ica-denoise",
    "aroma": "ica-denoise",
    "bet": "skull-strip",
    # SPM
    "dartel": "registration-nonlinear",
    # FreeSurfer
    "recon-all": "surface-recon",
    "bbregister": "registration-linear",
    # ANTs
    "antsregistration": "registration-nonlinear",
    "n4biasfieldcorrection": "bias-correction",
}

# Spelling variants of a single program -> (canonical key, canonical display).
_CANONICAL: dict[str, tuple[str, str]] = {
    "aroma": ("ica-aroma", "ICA-AROMA"),
    "ica-aroma": ("ica-aroma", "ICA-AROMA"),
}

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# AFNI
_AFNI_3D_RE = re.compile(r"\b3d[A-Z][A-Za-z0-9_]+\b")  # 3dDespike, 3dvolreg... (not "3dimensional")
_AFNI_1D_RE = re.compile(r"\b1d[A-Za-z][A-Za-z0-9_.]+\b")  # discovered then allowlist-gated
_AFNI_1D_ALLOW = frozenset(
    {
        "1dplot",
        "1dcat",
        "1dtool.py",
        "1dtranspose",
        "1dnorm",
        "1dsum",
        "1dbport",
        "1dmatcalc",
        "1dupsample",
        "1dapar2mat",
        "1ddw_grad_o_mat",
        "1dflagmotion",
        "1dfft",
        "1dgrayplot",
    }
)
_AFNI_LITERAL = ("afni_proc.py", "align_epi_anat.py")
# Curated real AFNI @-script names (verify against the AFNI program list); NOT generic @\w+.
_AFNI_AT = (
    "@SSwarper",
    "@animal_warper",
    "@auto_tlrc",
    "@Align_Centers",
    "@compute_gcor",
    "@radial_correlate",
    "@SUMA_Make_Spec_FS",
    "@ROI_Corr_Mat",
    "@AddEdge",
    "@clip_volume",
)

# FSL
_FSL_EXACT = (
    "FLIRT",
    "FNIRT",
    "MCFLIRT",
    "FEAT",
    "MELODIC",
    "fsl_regfilt",
    "topup",
    "eddy",
    "fsl_motion_outliers",
    "fslmaths",
)
_FSL_EXACT_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _FSL_EXACT) + r")\b", re.I)
_AROMA_RE = re.compile(r"\bICA-AROMA\b|\bAROMA\b", re.I)
_FSL_COLLIDE_RE = re.compile(r"\b(BET|FAST|FIRST)\b", re.I)  # only with nearby FSL context
_FSL_CONTEXT_RE = re.compile(
    r"\b(FSL|FMRIB|FLIRT|FNIRT|MCFLIRT|MELODIC|FEAT|fslmaths|FUGUE|topup)\b", re.I
)
_FSL_CONTEXT_WINDOW = 80  # chars

# SPM (usually prose, not function names -- expect ~zero spm_ hits; reported as a finding)
_SPM_FUNC_RE = re.compile(r"\bspm_[A-Za-z0-9_]+\b")
_SPM_OTHER_RE = re.compile(r"\b(DARTEL|CAT12|VBM8|VBM)\b")

# FreeSurfer / ANTs
_FS_RE = re.compile(r"\brecon-all\b|\bmri_[A-Za-z0-9_]+\b|\bbbregister\b", re.I)
_ANTS_RE = re.compile(r"\bantsRegistration\b|\bN4BiasFieldCorrection\b", re.I)

_TOOLBOX_RE: dict[str, re.Pattern[str]] = {
    "AFNI": re.compile(r"\bAFNI\b"),
    "FSL": re.compile(r"\b(FSL|FMRIB)\b"),
    "SPM": re.compile(r"\bSPM\d{0,2}\b"),
    "FreeSurfer": re.compile(r"\bFreeSurfer\b", re.I),
    "ANTs": re.compile(r"\b(ANTs|ANTS)\b"),
}

_TOOLS = ("AFNI", "FSL", "SPM", "FreeSurfer", "ANTs")


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Command:
    display: str  # command as written in the paper (first occurrence)
    tool: str
    function: str  # a _FUNCTION_VOCAB member, or "unknown"


@dataclasses.dataclass
class PaperSurvey:
    filename: str
    toolboxes_named: list[str]
    commands: list[Command]

    @property
    def n_commands(self) -> int:
        return len(self.commands)

    def commands_by_tool(self) -> dict[str, list[Command]]:
        out: dict[str, list[Command]] = {}
        for c in self.commands:
            out.setdefault(c.tool, []).append(c)
        return out


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _email_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in _EMAIL_RE.finditer(text)]


def _excluded(start: int, text: str, emails: list[tuple[int, int]]) -> bool:
    """Token is inside an email, or immediately preceded by '@' (non-allowlisted handle)."""
    if start > 0 and text[start - 1] == "@":
        return True
    return any(s <= start < e for s, e in emails)


def _function_for(token: str) -> str:
    return _FUNCTION_SEED.get(token.lower(), "unknown")


def survey_text(text: str) -> tuple[list[str], list[Command]]:
    """Return (toolboxes_named, distinct commands) for one paper's full text."""
    emails = _email_spans(text)
    found: dict[str, Command] = {}  # keyed by command.lower() -> first-seen

    def add(raw: str, tool: str) -> None:
        # Collapse spelling variants of one program (e.g. AROMA / ICA-AROMA) to a single
        # canonical entry so distinct-command counts are not inflated. This is spelling
        # hygiene, not a recommended/deprecated judgment.
        key, display = _CANONICAL.get(raw.lower(), (raw.lower(), raw))
        if key not in found:
            found[key] = Command(display=display, tool=tool, function=_function_for(key))

    def collect(regex: re.Pattern[str], tool: str) -> None:
        for m in regex.finditer(text):
            if not _excluded(m.start(), text, emails):
                add(m.group(0), tool)

    # AFNI
    collect(_AFNI_3D_RE, "AFNI")
    for m in _AFNI_1D_RE.finditer(text):
        if m.group(0).lower() in _AFNI_1D_ALLOW and not _excluded(m.start(), text, emails):
            add(m.group(0), "AFNI")
    for lit in _AFNI_LITERAL:
        for m in re.finditer(re.escape(lit), text, re.I):
            if not _excluded(m.start(), text, emails):
                add(m.group(0), "AFNI")
    for at in _AFNI_AT:  # allowlisted @-scripts: the leading '@' is expected, not excluded
        for m in re.finditer(re.escape(at), text, re.I):
            add(m.group(0), "AFNI")

    # FSL
    collect(_FSL_EXACT_RE, "FSL")
    collect(_AROMA_RE, "FSL")
    ctx = [m.start() for m in _FSL_CONTEXT_RE.finditer(text)]
    for m in _FSL_COLLIDE_RE.finditer(text):
        if _excluded(m.start(), text, emails):
            continue
        if any(abs(c - m.start()) <= _FSL_CONTEXT_WINDOW for c in ctx):
            add(m.group(0), "FSL")

    # SPM
    collect(_SPM_FUNC_RE, "SPM")
    collect(_SPM_OTHER_RE, "SPM")

    # FreeSurfer / ANTs
    collect(_FS_RE, "FreeSurfer")
    collect(_ANTS_RE, "ANTs")

    toolboxes = [name for name, rx in _TOOLBOX_RE.items() if rx.search(text)]
    commands = sorted(found.values(), key=lambda c: (_TOOLS.index(c.tool), c.display.lower()))
    return toolboxes, commands


def survey_pdf(pdf_path: Path) -> PaperSurvey:
    try:
        reader = PdfReader(str(pdf_path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        text = ""
    toolboxes, commands = survey_text(text)
    return PaperSurvey(filename=pdf_path.name, toolboxes_named=toolboxes, commands=commands)


# ---------------------------------------------------------------------------
# Folder driver + report
# ---------------------------------------------------------------------------


def _fmt_commands(paper: PaperSurvey) -> str:
    parts = []
    for tool, cmds in paper.commands_by_tool().items():
        parts.append(f"{tool}: " + ", ".join(c.display for c in cmds))
    return " | ".join(parts)


def survey_folder(input_folder: Path, limit: int | None = None) -> list[PaperSurvey]:
    pdfs = sorted(p for p in input_folder.glob("*.pdf"))
    if limit is not None:
        pdfs = pdfs[:limit]
    return [survey_pdf(p) for p in pdfs]


def write_csv(papers: list[PaperSurvey], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "toolboxes_named", "commands_found", "n_commands"])
        for p in sorted(papers, key=lambda p: (-p.n_commands, p.filename)):
            w.writerow([p.filename, "; ".join(p.toolboxes_named), _fmt_commands(p), p.n_commands])


def summarize(papers: list[PaperSurvey]) -> str:
    n = len(papers)
    with_cmd = [p for p in papers if p.n_commands]
    toolbox_no_cmd = [p for p in papers if p.toolboxes_named and not p.n_commands]

    per_tool_papers: Counter[str] = Counter()
    per_tool_cmds: Counter[str] = Counter()
    per_function: Counter[str] = Counter()
    for p in papers:
        tools_here = {c.tool for c in p.commands}
        for t in tools_here:
            per_tool_papers[t] += 1
        for c in p.commands:
            per_tool_cmds[c.tool] += 1
            per_function[c.function] += 1

    spm_toolbox = [p for p in papers if "SPM" in p.toolboxes_named]
    spm_cmds = per_tool_cmds.get("SPM", 0)

    lines = ["# Command survey", ""]
    lines.append(f"- Papers surveyed: {n}")
    lines.append(f"- Papers naming >=1 command: {len(with_cmd)}")
    lines.append(f"- Papers naming a toolbox but 0 commands: {len(toolbox_no_cmd)}")
    if toolbox_no_cmd:
        lines.append("    (" + ", ".join(p.filename for p in toolbox_no_cmd) + ")")
    lines.append("")
    lines.append("## Distribution by tool (papers with >=1 cmd / distinct cmds)")
    for t in _TOOLS:
        lines.append(f"- {t}: {per_tool_papers.get(t, 0)} papers / {per_tool_cmds.get(t, 0)} cmds")
    lines.append("")
    lines.append("## Distribution by function")
    for func, cnt in sorted(per_function.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- {func}: {cnt}")
    lines.append("")
    lines.append("## SPM prose observation")
    lines.append(
        f"- {len(spm_toolbox)} paper(s) name the SPM toolbox; {spm_cmds} SPM command token(s) "
        "found -- SPM methods are described in prose, not function names, as expected."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("input_folder", type=Path, help="folder of *.pdf")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="per-paper CSV (default: <folder>/command_survey.csv)",
    )
    ap.add_argument("--limit", type=int, default=None, help="process only the first N PDFs")
    args = ap.parse_args(argv)

    folder = args.input_folder
    if not folder.is_dir():
        print(f"ERROR: not a folder: {folder}", file=sys.stderr)
        return 1
    out_path = args.out or (folder / "command_survey.csv")
    papers = survey_folder(folder, limit=args.limit)
    write_csv(papers, out_path)
    print(summarize(papers))
    print(f"\nWrote {out_path} ({len(papers)} papers).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
