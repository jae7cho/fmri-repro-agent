"""The recorder's table is the 19-paper corpus; the held-out three are in it and stay refused.

DESIGN_motion_full_corpus.md §2.1 and §7 fork 1 (2026-10-26). Nothing here opens a PDF. The table
is checked against the acceptance config's ids and file names; every path through ``main`` is cut
off by a stub client that raises before any paper is loaded, and a stub loader fails the test if a
paper's text is ever asked for. The held-out ids are therefore exercised as IDS only.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import motion_probe
import motion_probe_projection

_CONFIG = Path(__file__).resolve().parents[1] / "configs" / "batch_a1_acceptance_config.yaml"
_HELD = ("liu_2005", "tang_2025", "wheaton_2004")
_SIXTEEN = sorted(set(motion_probe._PROBE_PAPERS) - set(_HELD))


def _config_papers() -> dict[str, str]:
    cfg = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    return {p["paper_id"]: Path(p["path"]).name for p in cfg["papers"]}


class _NoClient:
    """If ``main`` gets as far as building a client, this raises -- no model is ever reached."""

    def __init__(self) -> None:
        raise AssertionError("a client was built: the refusal did not precede it")


def _no_read(paper_id: str) -> Any:
    raise AssertionError(f"_paper({paper_id!r}) was called: a test asked for a paper's text")


@pytest.fixture(autouse=True)
def _cut_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(motion_probe, "_CountingClient", _NoClient)
    monkeypatch.setattr(motion_probe, "_paper", _no_read)


# --- the table -------------------------------------------------------------------------------


def test_table_is_the_acceptance_corpus_ids_and_file_names() -> None:
    """Same 19 ids, same PDF file names, as the config the stored acceptance run was made from."""
    expected = _config_papers()
    got = {pid: entry["pdf"] for pid, entry in motion_probe._PROBE_PAPERS.items()}
    assert len(expected) == 19
    assert got == expected


def test_held_out_ids_are_in_the_table_and_still_named() -> None:
    assert set(_HELD) == set(motion_probe._HELD_OUT)
    assert set(_HELD) <= set(motion_probe._PROBE_PAPERS)


def test_no_licence_is_recorded_until_the_amendment_sets_one() -> None:
    """Default-closed. The amendment that licenses the full-corpus run sets this in the same
    commit; until then no flag value admits a held-out id."""
    assert motion_probe._CORPUS_RUN_LICENCE is None


# --- the guard, every branch, no client, no read ----------------------------------------------


def _main(args: list[str], out: Path) -> None:
    motion_probe.main(["--k", "1", "--results-dir", str(out), *args])


def test_default_list_is_the_whole_corpus_and_is_refused_without_a_licence(tmp_path: Path) -> None:
    out = tmp_path / "never"
    with pytest.raises(SystemExit, match="HELD OUT"):
        _main([], out)
    assert not out.exists()


def test_held_out_refused_with_a_flag_while_no_licence_is_recorded(tmp_path: Path) -> None:
    out = tmp_path / "never"
    with pytest.raises(SystemExit, match="no corpus-run licence is recorded"):
        _main(["--papers", "liu_2005", "--corpus-run", "Amendment 10"], out)
    assert not out.exists()


def test_held_out_refused_when_the_flag_mismatches_the_licence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(motion_probe, "_CORPUS_RUN_LICENCE", "Amendment 10")
    out = tmp_path / "never"
    with pytest.raises(SystemExit, match="does not match the recorded licence"):
        _main(["--papers", "tang_2025", "--corpus-run", "Amendment 9"], out)
    assert not out.exists()


def test_held_out_admitted_by_a_matching_licence_reaches_the_client_before_any_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The accepted path: past both refusals, ``main`` builds the client (the stub raises) and has
    not yet asked for any paper's text."""
    monkeypatch.setattr(motion_probe, "_CORPUS_RUN_LICENCE", "Amendment 10")
    out = tmp_path / "never"
    with pytest.raises(AssertionError, match="a client was built"):
        _main(["--papers", "wheaton_2004", "--corpus-run", "Amendment 10"], out)


def test_the_sixteen_pass_both_guards_without_a_licence(tmp_path: Path) -> None:
    out = tmp_path / "never"
    with pytest.raises(AssertionError, match="a client was built"):
        _main(["--papers", *_SIXTEEN], out)


def test_an_id_outside_the_corpus_is_refused_before_the_held_out_check(tmp_path: Path) -> None:
    """cabral_2017 has a PDF in the corpus folder and is excluded from the corpus; it is refused as
    an unknown id, as is an id that exists nowhere."""
    out = tmp_path / "never"
    for pid in ("cabral_2017", "nobody_2000"):
        with pytest.raises(SystemExit, match="refused paper id"):
            _main(["--papers", pid, "liu_2005"], out)
    assert not out.exists()


# --- the projection: every recorded paper has a place, or nothing is projected ----------------


def _record(paper_id: str) -> dict[str, Any]:
    return asdict(
        motion_probe.DrawRecord(
            paper_id=paper_id,
            draw=1,
            raw_status="deferred",
            raw_value=None,
            raw_verbatim_quote=None,
            raw_ref_string="x",
            raw_deferral_sentence="x",
            raw_binding=None,
            verbatim=None,
            resolved=None,
            resolution=None,
            span_start=None,
            span_end=None,
            span_text=None,
            span_section=None,
            span_recovered=None,
            extraction_arm="DeferredToCitation",
            left_missing_reason="deferred_to_citation",
            deferral_target_kind_original="paper",
            deferral_target_kind_stored="paper",
            deferral_ref="x",
            completion_attempts=1,
            reask_occurred=False,
            wall_seconds=0.1,
        )
    )


def _run_dir(tmp_path: Path, manifest_papers: list[str], files: list[str]) -> Path:
    run = tmp_path / "run" / "motion_probe"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "model": "m",
                "k": 1,
                "papers": manifest_papers,
                "motion_method_prompt_sha256": "0" * 64,
                "generated_utc": "2026-10-26T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    for pid in files:
        (run / f"{pid}.jsonl").write_text(json.dumps(_record(pid)) + "\n", encoding="utf-8")
    return tmp_path / "run"


def _project(results: Path, out: Path) -> int:
    return motion_probe_projection.main(
        ["--results-dir", str(results), "--run-date", "2026-10-26", "--out", str(out)]
    )


def test_projection_order_lists_the_whole_table_once_with_the_clean_three_last() -> None:
    order = motion_probe_projection._ORDER
    assert len(order) == len(set(order)) == 19
    assert set(order) == set(motion_probe._PROBE_PAPERS)
    assert order[-3:] == _HELD


def test_projection_refuses_a_manifest_paper_not_in_order(tmp_path: Path) -> None:
    results = _run_dir(tmp_path, ["power_2014", "nobody_2000"], ["power_2014"])
    with pytest.raises(SystemExit, match="nobody_2000"):
        _project(results, tmp_path / "p.csv")
    assert not (tmp_path / "p.csv").exists()


def test_projection_refuses_a_record_file_not_in_order(tmp_path: Path) -> None:
    """The on-disk check: a record file whose paper is absent from both the manifest and _ORDER
    is refused, not skipped."""
    results = _run_dir(tmp_path, ["power_2014"], ["power_2014", "nobody_2000"])
    with pytest.raises(SystemExit, match="not in _ORDER"):
        _project(results, tmp_path / "p.csv")
    assert not (tmp_path / "p.csv").exists()


def test_projection_accepts_a_listed_subset(tmp_path: Path) -> None:
    results = _run_dir(tmp_path, ["ciric_2017"], ["ciric_2017"])
    assert _project(results, tmp_path / "p.csv") == 0
    text = (tmp_path / "p.csv").read_text(encoding="utf-8")
    assert "ciric_2017,1,deferred" in text
