"""The motion stanza is FROZEN (prereg C11; Amendment 9, 2026-10-26).

Two guards, one fact. ``test_prompt_pin.py`` pins the stanza's hash so an edit is a deliberate,
dated act; this file checks that the probe recorder carries the same hash as its frozen value and
refuses to draw under any other. The pin can be updated to make a test pass; the recorder's refusal
is what stands between an edited stanza and a model call. A stanza change now requires a new prereg
amendment that names the new hash in ``scripts/motion_probe.py``, in the same commit as the edit.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

from extractor_mvp.extractor import MOTION_METHOD_PROMPT

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import motion_probe

_LIVE = hashlib.sha256(MOTION_METHOD_PROMPT.encode("utf-8")).hexdigest()


def test_the_recorder_is_frozen_on_the_live_stanza() -> None:
    """The frozen constant and the stanza actually sent to the model agree. If this fails, either
    the stanza was edited without a new amendment (restore it) or an amendment adopted a new
    version without updating the recorder (update the constant in the same commit)."""
    assert motion_probe._FROZEN_STANZA_SHA256 == _LIVE


def test_the_frozen_hash_is_the_pinned_one() -> None:
    """The pin and the freeze name the same stanza, so neither can drift alone."""
    from test_prompt_pin import _PINNED

    assert motion_probe._FROZEN_STANZA_SHA256 == _PINNED["MOTION_METHOD_PROMPT"]


def test_refuses_any_other_stanza() -> None:
    """Positive control for the refusal: a hash one character off is refused, with the message
    naming the freeze. The live hash passes."""
    other = ("0" if _LIVE[0] != "0" else "1") + _LIVE[1:]
    with pytest.raises(SystemExit, match="FROZEN"):
        motion_probe._refuse_unless_frozen(other)
    motion_probe._refuse_unless_frozen(_LIVE)  # must not raise


class _NoClient:
    """Stands in for the recorder's client so that a missing guard fails the test here, with no
    model call: if ``main`` gets as far as building a client, this raises."""

    def __init__(self) -> None:
        raise AssertionError("a client was built: the refusal did not precede it")


def test_main_refuses_before_touching_the_results_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the frozen value pointed elsewhere, ``main`` exits before creating the results
    directory or building a client -- the refusal precedes every side effect."""
    monkeypatch.setattr(motion_probe, "_FROZEN_STANZA_SHA256", "f" * 64)
    monkeypatch.setattr(motion_probe, "_CountingClient", _NoClient)
    out = tmp_path / "never"
    with pytest.raises(SystemExit, match="FROZEN"):
        motion_probe.main(["--k", "1", "--papers", "power_2014", "--results-dir", str(out)])
    assert not out.exists()


def test_held_out_refusal_still_precedes_any_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The freeze did not displace the C11/C26 guard: under the frozen stanza, a held-out id is
    still refused before a client is built."""
    monkeypatch.setattr(motion_probe, "_CountingClient", _NoClient)
    out = tmp_path / "never"
    with pytest.raises(SystemExit, match="HELD OUT"):
        motion_probe.main(["--k", "1", "--papers", "liu_2005", "--results-dir", str(out)])
    assert not out.exists()
