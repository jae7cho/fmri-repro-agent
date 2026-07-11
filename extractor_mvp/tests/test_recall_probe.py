"""Offline tests for the recall-probe regexes + predicate (no PDF, no KB, no network).

recall_probe lives in scripts/ (not a package), so it is loaded from its path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "recall_probe.py"
_spec = importlib.util.spec_from_file_location("recall_probe", _SCRIPT)
assert _spec is not None and _spec.loader is not None
rp: Any = importlib.util.module_from_spec(_spec)
sys.modules["recall_probe"] = rp  # dataclasses resolves annotations via sys.modules
_spec.loader.exec_module(rp)


# --- regexes ----------------------------------------------------------------


def test_fused_run_matches_long_alpha_runs_only() -> None:
    assert rp._FUSED_RUN.search("ConfigurablePipelinefortheAnalysisofConnectomes")
    assert not rp._FUSED_RUN.search("a normal sentence with short words")
    assert not rp._FUSED_RUN.search("twentyfivecharacters1234")  # <26 alpha before digits


def test_shattered_acronym_matches_spaced_capitals() -> None:
    assert rp._SHATTERED_ACRONYM.search("C P A C") is not None
    # the "P A C" tail of a hyphen-shattered acronym still trips it
    assert rp._SHATTERED_ACRONYM.search("C-P A C version 0.4.0") is not None
    assert rp._SHATTERED_ACRONYM.search("normal Text Here") is None


def test_version_token_requires_v_prefix() -> None:
    assert rp._VERSION_TOKEN.search("C-P A C version 0.4.0") is not None
    assert rp._VERSION_TOKEN.search("v0.4.0") is not None
    assert rp._VERSION_TOKEN.search("v. 2.1.0") is not None
    assert rp._VERSION_TOKEN.search("released in 0.4.0 unprefixed") is None  # no v/version


def test_version_near_proximity() -> None:
    text = "used C-PAC version 0.4.0 to preprocess"
    i = text.index("C-PAC")
    assert rp._version_near(text, i, i + 5) is True
    far = "C-PAC" + (" " * 300) + "version 0.4.0"
    assert rp._version_near(far, 0, 5) is False


def test_fused_stats_per_1k_words() -> None:
    n, per_1k = rp._fused_stats("ConfigurablePipelinefortheAnalysisofConnectomes and more words")
    assert n == 1
    assert per_1k > 0


# --- predicate on synthetic text (no PDF / KB) ------------------------------


def _missing_result() -> dict[str, Any]:
    return {"preprocessing": {"base_pipeline": {"extraction": {"status": "MISSING_FROM_PAPER"}}}}


def test_clean_alias_hit_in_missing_paper_is_suspected_name() -> None:
    text = (
        "Introduction here. Methods: image preprocessing in C-PAC consisted of the following "
        "steps: motion correction and registration. Results follow."
    )
    rep = rp.probe_paper("synthetic", text, _missing_result(), ["C-PAC"])
    kinds = {(s.kind, s.alias) for s in rep.suspected}
    assert ("name", "C-PAC") in kinds
    assert rep.base_status == "MISSING_FROM_PAPER"


def test_fused_shattered_name_and_version_are_flagged_separately() -> None:
    # The extractor could not reasonably have matched the fused form; flag it apart.
    text = (
        "Methods: data was processed using the "
        "ConfigurablePipelinefortheAnalysisofConnectomes(C-PACversion0.4.0). Results follow."
    )
    rep = rp.probe_paper("synthetic", text, _missing_result(), ["C-PAC"])
    kinds = {s.kind for s in rep.suspected}
    assert "fused-name" in kinds
    assert "fused-version" in kinds  # "version 0.4.0" collapses next to the fused C-PAC


def test_no_alias_no_suspicion() -> None:
    text = "Methods: we used an in-house MATLAB script. Results follow."
    rep = rp.probe_paper("synthetic", text, _missing_result(), ["C-PAC", "fmriprep"])
    assert rep.suspected == []


def test_render_records_exclusions() -> None:
    out = rp.render([], ["cabral_2017"])
    assert "Excluded from this screen" in out
    assert "cabral_2017" in out
    assert "10 -> 9" in out and "8/9" in out
