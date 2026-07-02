"""Shared pytest configuration for the extractor_mvp test suite.

Enforces the ``live`` marker's documented contract (see ``[tool.pytest.ini_options]``
in ``pyproject.toml``): tests that need live Bedrock API access + AWS credentials are
skipped by default and run only when explicitly selected with ``pytest -m live``.
Without this, ``live`` tests execute in the default run and fail in credential-less
environments (e.g. ``ModuleNotFoundError: boto3`` when litellm tries to authenticate).
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # If the caller passed an explicit -m marker expression (e.g. `-m live`), respect it
    # and do nothing -- they have opted into whatever they selected.
    if config.getoption("-m"):
        return
    skip_live = pytest.mark.skip(reason="live test; run with `pytest -m live`")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
