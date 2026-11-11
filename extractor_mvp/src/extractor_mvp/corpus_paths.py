"""Resolve the local corpus location without hardcoding a home directory.

The corpus PDFs are deliberately absent from this repository (licensing), so every consumer needs
a path to a local copy. Eleven call sites across scripts, scorers and tests hardcoded
``/Users/<account>/Documents/neurorepro/tested_lit/...``. That did two unrelated kinds of damage:
it published the author's macOS account name in a PUBLIC repository, and it made every one of
those call sites fail on any machine but one, which is the opposite of what a reproducibility
tool should do.

``Path.home()`` resolves to the author's own directory on the author's machine -- so nothing moves
-- and to the right place for anyone who lays the corpus out the same way. ``AESPA_TESTED_LIT``
overrides it for a corpus kept anywhere else.

This module deliberately has no imports from the rest of the package: it is read at module scope
by standalone scripts that run before any ``sys.path`` setup.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Environment variable that overrides the default location outright.
ENV_VAR = "AESPA_TESTED_LIT"

#: Where the corpus sits relative to the user's home directory when the variable is unset.
DEFAULT_RELATIVE = Path("Documents") / "neurorepro" / "tested_lit"


def tested_lit_root() -> Path:
    """The directory holding the corpus batches (``sfn_batch``, ``multi_batch``, ``stress_v1``)."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_RELATIVE


def corpus_dir(name: str) -> Path:
    """One corpus batch directory by name, e.g. ``corpus_dir("sfn_batch")``."""
    return tested_lit_root() / name
