"""Shared pytest configuration and fixtures for the extractor_mvp test suite.

**The `live` marker.** Enforces the marker's documented contract (see
``[tool.pytest.ini_options]`` in ``pyproject.toml``): tests that need live Bedrock API access +
AWS credentials are skipped by default and run only when explicitly selected with
``pytest -m live``. Without this, ``live`` tests execute in the default run and fail in
credential-less environments (e.g. ``ModuleNotFoundError: boto3`` when litellm tries to
authenticate).

**The shared fixtures below exist because test modules must not import each other.** They were
plain helpers in ``test_batch.py`` and ``test_assemble_v0_3_0.py``, reached by
``from tests.test_batch import _patch`` and ``from tests.test_assemble_v0_3_0 import _assembled``.
That spelling only resolves when the package root is on ``sys.path``, which ``python -m pytest``
provides and the ``pytest`` console script -- the form CI runs -- does not. The result was
``ModuleNotFoundError: No module named 'tests'`` at collection, and the ``extractor-mvp`` job was
red on it from 2026-09-12 to 2026-10-02 while every local run reported a clean count.

Two further reasons it is fixtures here rather than a path setting. The repository root has its
own ``tests/`` package, so ``tests`` is an ambiguous name across this repo: from the root, the
same import fails as ``No module named 'tests.test_batch'`` -- ``tests`` resolving to the *root*
package. Making ``extractor_mvp/tests`` a package too would make that ambiguity permanent. And
the second import was inside a function body, so no collection-time check could ever have caught
it; ``test_tally_scope_is_step_fields_only`` would have failed at runtime instead.

Imports in the helpers below are deliberately function-local: conftest is imported for every
session, and hoisting ``extractor_mvp.batch`` to module scope would move when litellm and boto3
are first imported for the whole suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fmri_repro.spec.preprocessing import Preprocessing

    from extractor_mvp.extractor import PreprocessingExtraction


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # If the caller passed an explicit -m marker expression (e.g. `-m live`), respect it
    # and do nothing -- they have opted into whatever they selected.
    if config.getoption("-m"):
        return
    skip_live = pytest.mark.skip(reason="live test; run with `pytest -m live`")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


# --------------------------------------------------------------------------------------------
# The canned batch run. Used by test_batch.py and test_report_cli.py.
# --------------------------------------------------------------------------------------------

FULL_TEXT = "Methods\nData were normalized to MNI152NLin6Asym at 2 mm.\nResults\nFindings."


def _canned_payload() -> PreprocessingExtraction:
    from extractor_mvp.extraction_result import FieldExtractionResult
    from extractor_mvp.extractor import PreprocessingExtraction

    none = FieldExtractionResult(status="missing")
    return PreprocessingExtraction(
        target_space=FieldExtractionResult(
            status="extracted",
            value="MNI152NLin6Asym",
            verbatim_quote="normalized to MNI152NLin6Asym",
        ),
        resolution_mm=FieldExtractionResult(
            status="extracted", value="2", verbatim_quote="at 2 mm"
        ),
        surface_registration=none,
        target_surface=none,
        intensity_convention=none,
        intensity_value=none,
    )


@pytest.fixture
def canned_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub only the PDF loader and the model call; everything else stays real.

    The orchestrator, the span resolver and the renderer all run, so spans resolve against the
    real slice of FULL_TEXT. A test that stubbed ``extract`` or ``to_report`` outright would
    assert nothing about the artifact the code exists to produce.

    Requesting this fixture gives a test the patched module; a test that then wants a different
    failure mode overrides it in its own body with ``monkeypatch`` as usual, because fixtures run
    first. Four tests in test_batch.py depend on that ordering.
    """
    from types import SimpleNamespace

    import extractor_mvp.batch as batch
    from extractor_mvp.extractor import extract

    monkeypatch.setattr(batch, "load_pdf_text", lambda _path: (FULL_TEXT, "pypdf"))
    payload = _canned_payload()
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: payload))
    )
    monkeypatch.setattr(
        batch,
        "extract",
        lambda paper, model, **kwargs: extract(paper, model, client=fake_client),
    )


# --------------------------------------------------------------------------------------------
# The fully untargeted assembled Preprocessing. Used by test_assemble_v0_3_0.py, and by
# test_batch.py's deferred-base variant.
# --------------------------------------------------------------------------------------------

# pf dict keys are the extractor's names; each value's field_id is the STEP attribute name.
_PF_FIELD_IDS = {
    "target_space": "target_space",
    "resolution_mm": "resolution_mm",
    "target_surface": "target_surface",
    "surface_registration": "surface_registration",
    "intensity_convention": "convention",
    "intensity_value": "value",
    "temporal_standardization_method": "method",
}


def _build_assembled() -> Preprocessing:
    from fmri_repro.spec.provenance import MissingFromPaper

    from extractor_mvp.extractor import _assemble, _missing_pf

    pf = {k: _missing_pf(fid, str, "not_stated_in_text") for k, fid in _PF_FIELD_IDS.items()}
    return _assemble(pf, MissingFromPaper(searched_terms=[], sections_searched=["M"]))


@pytest.fixture
def assembled() -> Preprocessing:
    """_assemble's output with every pf missing -- i.e. every step field untargeted."""
    return _build_assembled()
