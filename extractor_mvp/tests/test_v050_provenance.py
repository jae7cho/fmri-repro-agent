"""The v050 predictions CSV carries emitted provenance, and stays machine-readable.

The header exists because that CSV is GENERATED: score_v050_reextraction.py opens it with
"w", so a hand-written provenance block would be silently lost on the next run. The frozen
CSV has no generator, which is why its hand-maintained header survives — the two files look
alike and are not the same kind of artifact.
"""

from __future__ import annotations

import csv
from pathlib import Path

GT = Path(__file__).resolve().parents[2] / "ground_truth"
V050 = GT / "target_space_predictions_v050.csv"


def _stripped(path: Path) -> list[dict[str, str]]:
    """The repo's comment-stripping idiom, used at score_target_space.py:152 and elsewhere."""
    return list(csv.DictReader(ln for ln in path.open() if not ln.startswith("#")))


def test_header_records_provenance_that_was_recomputed() -> None:
    head = "".join(ln for ln in V050.open() if ln.startswith("#"))
    assert "batch_v050_labelset" in head
    assert "bedrock/us.anthropic.claude-sonnet-4-5" in head, "model pin must be named"
    assert "bae9a84" in head, "source commit must be named"
    assert "Verified at emit time" in head, "the draw match must be stated as a check, not a claim"
    assert "19/19" in head
    # Scoped exactly as the baselines are: the draws live under the ignored results/ tree.
    assert "NOT ON A CLONE" in head


def test_stays_readable_with_the_strip_idiom() -> None:
    rows = _stripped(V050)
    assert len(rows) == 19
    assert {"paper_id", "k3_status", "v3_grade", "label", "correct"} <= set(rows[0])


def test_forgetting_the_strip_fails_silently_not_loudly() -> None:
    """Documents the hazard the header introduces, so whoever adds a reader sees it.

    A reader that omits the strip does NOT raise — it parses the comment lines as data and
    returns more rows than exist. Nothing reads this CSV in code today; score_target_space.py
    will once the vintage moves, and it already uses the strip for the frozen file.
    """
    unstripped = list(csv.DictReader(V050.open()))
    assert len(unstripped) > 19, "if this ever equals 19 the header is gone"
