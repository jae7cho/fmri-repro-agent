#!/usr/bin/env python3
"""The operation-phrase heuristic from the `motion_correction.method` pre-registration.

`docs/findings/motion-method-reachability-prereg.md` enumerates this vocabulary at `:94-111` and
freezes it before the run (C21). It derives `value_kind` from the model's own `value` string; the
model never emits it (`:66`). The state map then reads `value_kind` to predict a label state.

**Amendment 2 (2026-10-21) ruling 5 fixed three defects in the prereg's prose version. Each is
implemented here and calibrated in `tests/test_motion_value_kind.py`.**

1. *The prose contradicted itself.* `tool_name` required "`value` contains none of the above
   **and** matches a tool-shaped pattern", which makes a both-lists match impossible — yet the same
   section says "Both sides are checked, and a `value` matching both is `undecided`, not a
   precedence winner", giving "motion correction via ICA-AROMA" as the case that must halt. Under
   the prose as written that string resolves to `operation_phrase` and never halts. The two tests
   are now INDEPENDENT, and a double match is `undecided`.
2. *The version pattern caught plain numbers.* `\\w+\\s*v?\\d+(\\.\\d+)*` — `\\w` includes digits, so
   any two-digit run matched, including the `1996` inside binder's own citation. Restricted to
   LETTERS followed by digits.
3. *Common imaging acronyms read as tools.* "an initialism of >=2 capitals" matches `EPI` and
   `BOLD`, so any phrase mentioning them would be tool-shaped and halt. Ruled: they are not
   tool-shaped. Implemented as a named exclusion set rather than a narrower pattern, because the
   exclusions are the part a later reader needs to see and argue with.
"""

from __future__ import annotations

import re
from typing import Literal

ValueKind = Literal["operation_phrase", "tool_name", "undecided"]

#: prereg :97-99, verbatim and in order.
_OPERATION_PHRASES: tuple[str, ...] = (
    "realign",
    "motion correction",
    "motion-correction",
    "head motion",
    "head movement",
    "coregist",
    "co-regist",
    "rigid body",
    "rigid-body",
    "volume registration",
    "image registration",
)

#: prereg :101-104, the named package/program tokens.
_TOOL_TOKENS: tuple[str, ...] = (
    "MCFLIRT",
    "mcflirt",
    "3dvolreg",
    "Realign",
    "FLIRT",
    "applywarp",
    "ICA-AROMA",
    "align_epi_anat",
    "fMRIPrep",
    "C-PAC",
    "Freesurfer",
    "SPM8",
    "SPM12",
)

#: An initialism of >=2 capitals, per the prereg's own wording.
_INITIALISM = re.compile(r"\b[A-Z]{2,}\b")

#: Amendment 2 ruling 5, defect 3. These are acquisition/modality acronyms, not tools. Without the
#: exclusion, "EPI images were spatially coregistered" is BOTH an operation phrase and tool-shaped,
#: so it would halt as undecided -- and that string is the shape of binder's committed quote, the
#: paper the prereg designates as the test of whether `undecided` is rare. A heuristic that halts on
#: the test case cannot measure it.
_NOT_TOOL_INITIALISMS: frozenset[str] = frozenset(
    {
        "EPI",  # echo-planar imaging: the modality
        "BOLD",  # the contrast
        "MNI",  # a template space, and target_space's business
        "TR",  # repetition time
        "FD",  # framewise displacement: a CONSUME statistic per CALL 10
        "RMS",  # root mean square: likewise
        "ROI",
        "FOV",
        "SNR",
        "CSF",
        "GM",
        "WM",
    }
)

#: Amendment 2 ruling 5, defect 2. LETTERS then digits: "SPM12", "FSL 5.0.10", "v0.3". A bare year
#: or count no longer matches, so binder's "(Cox, 1996b)" is not tool-shaped on the number alone.
_VERSIONED = re.compile(r"[A-Za-z]+\s*v?\d+(?:\.\d+)*")


def is_operation_phrase(value: str) -> bool:
    """prereg :97-99. Lowercased substring match, checked INDEPENDENTLY of the tool test."""
    low = value.lower()
    return any(p in low for p in _OPERATION_PHRASES)


def is_tool_shaped(value: str) -> bool:
    """prereg :101-104, with ruling 5's defects 2 and 3 fixed. Independent of the phrase test."""
    if any(tok in value for tok in _TOOL_TOKENS):
        return True
    if any(m.group(0) not in _NOT_TOOL_INITIALISMS for m in _INITIALISM.finditer(value)):
        return True
    return bool(_VERSIONED.search(value))


def value_kind(value: str | None) -> ValueKind:
    """Derive `value_kind`. A value matching BOTH lists is ``undecided`` (prereg :110-111).

    ``undecided`` means HALT THE CELL (prereg :106-108): do not default to either side, record it,
    adjudicate by hand, and count it. The count is the empirical measure of whether ruling (b) was
    adequate, and Amendment 2 ruling 4 sets the threshold that would reopen option (c).
    """
    if value is None:
        return "undecided"
    phrase = is_operation_phrase(value)
    tool = is_tool_shaped(value)
    if phrase and tool:
        return "undecided"
    if phrase:
        return "operation_phrase"
    if tool:
        return "tool_name"
    return "undecided"
