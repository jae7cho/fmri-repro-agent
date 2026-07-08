"""Offline tests for the standalone command_survey tool (faked PDF text, no network)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from extractor_mvp import command_survey as cs


def _names(commands: list[cs.Command]) -> set[str]:
    return {c.display for c in commands}


# --- real commands are caught ----------------------------------------------


def test_real_commands_caught():
    text = "We ran 3dDespike, then ICA-AROMA, and registered with FLIRT (FSL)."
    toolboxes, cmds = cs.survey_text(text)
    names = _names(cmds)
    assert "3dDespike" in names
    assert "ICA-AROMA" in names
    assert "FLIRT" in names
    assert "AFNI" not in toolboxes  # 'AFNI' not spelled out here
    assert "FSL" in toolboxes


def test_afni_1d_allowlist_gated():
    _, cmds = cs.survey_text("We used 1dplot but the scan took 1day to finish.")
    names = _names(cmds)
    assert "1dplot" in names  # allowlisted
    assert "1day" not in names  # prose, not an AFNI 1d-program


def test_at_scripts_allowlisted_not_generic():
    _, cmds = cs.survey_text("Skull-stripping used @SSwarper on each subject.")
    assert "@SSwarper" in _names(cmds)


def test_freesurfer_and_ants_and_spm_families():
    text = (
        "recon-all and mri_convert; antsRegistration; N4BiasFieldCorrection; spm_realign; DARTEL."
    )
    _, cmds = cs.survey_text(text)
    names = _names(cmds)
    assert {"recon-all", "mri_convert", "antsRegistration", "N4BiasFieldCorrection"} <= names
    assert "spm_realign" in names and "DARTEL" in names


# --- false positives excluded ----------------------------------------------


def test_email_handles_and_affiliations_not_caught():
    text = "Correspondence: author@uni.edu, @stanford. Also 3dfoo@example.org affiliation."
    _, cmds = cs.survey_text(text)
    names = _names(cmds)
    assert not any("uni.edu" in n or "stanford" in n for n in names)
    # a command-looking token inside an email must be dropped
    assert "3dfoo" not in names


def test_collision_words_need_fsl_context():
    prose = "The results held fast, and we ran the analysis first, in the best interest."
    _, cmds = cs.survey_text(prose)
    assert not _names(cmds) & {"fast", "first", "FAST", "FIRST", "bet", "BET"}


def test_collision_words_fire_with_fsl_context():
    text = "Brain extraction used BET (FSL), then FAST for tissue segmentation."
    _, cmds = cs.survey_text(text)
    names = {n.lower() for n in _names(cmds)}
    assert "bet" in names and "fast" in names


# --- function tagging is conservative --------------------------------------


def test_function_seed_and_unknown():
    _, cmds = cs.survey_text("3dDespike ; 3dToolThatIsMadeUp ; recon-all")
    by = {c.display: c.function for c in cmds}
    assert by["3dDespike"] == "despike"
    assert by["recon-all"] == "surface-recon"
    assert by["3dToolThatIsMadeUp"] == "unknown"  # not seeded -> not guessed


def test_all_seed_functions_in_vocab():
    for func in cs._FUNCTION_SEED.values():
        assert func in cs._FUNCTION_VOCAB


# --- folder / report via faked PdfReader -----------------------------------


class _FakePage:
    def __init__(self, text: str) -> None:
        self._t = text

    def extract_text(self) -> str:
        return self._t


class _FakeReader:
    def __init__(self, text: str) -> None:
        self.pages = [_FakePage(text)]


def test_survey_folder_and_report(tmp_path: Path, monkeypatch: Any):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")
    texts = {
        "a.pdf": "We used FSL FLIRT and MCFLIRT for registration and motion.",
        "b.pdf": "Analysis in SPM12. Standard preprocessing was applied.",  # toolbox, prose only
    }
    monkeypatch.setattr(cs, "PdfReader", lambda p: _FakeReader(texts[Path(p).name]))

    papers = cs.survey_folder(tmp_path)
    assert len(papers) == 2
    by_name = {p.filename: p for p in papers}
    assert by_name["a.pdf"].n_commands == 2
    assert by_name["b.pdf"].n_commands == 0
    assert "SPM" in by_name["b.pdf"].toolboxes_named

    out = tmp_path / "survey.csv"
    cs.write_csv(papers, out)
    header = out.read_text().splitlines()[0]
    assert header == "filename,toolboxes_named,commands_found,n_commands"

    report = cs.summarize(papers)
    assert "Papers naming a toolbox but 0 commands: 1" in report
    assert "SPM prose observation" in report

    assert cs.main([str(tmp_path), "--out", str(tmp_path / "m.csv")]) == 0
