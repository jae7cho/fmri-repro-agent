"""adapt_request (2026-11-14): Opus 5.5 and Fable 5.2 reject sampling parameters and a forced tool
choice, so their requests drop ``temperature`` and send ``tool_choice="auto"``; every other model's
request goes out unchanged, through both clients (``build_client`` and ``CallMeter``)."""

from __future__ import annotations

from typing import Any

import pytest

from extractor_mvp.extractor import adapt_request

SONNET = "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
OPUS = "bedrock/us.anthropic.claude-opus-5-5"
FABLE = "bedrock/us.anthropic.claude-fable-5-2"
FORCED = {"type": "function", "function": {"name": "Extraction"}}


def _req(model: str) -> dict[str, Any]:
    return {"model": model, "temperature": 0.0, "tool_choice": FORCED, "messages": []}


def test_sonnet_request_is_unchanged() -> None:
    req = _req(SONNET)
    assert adapt_request(req) == _req(SONNET)


@pytest.mark.parametrize("model", [OPUS, FABLE])
def test_new_models_drop_temperature_and_force_nothing(model: str) -> None:
    out = adapt_request(_req(model))
    assert "temperature" not in out
    assert out["tool_choice"] == "auto"
    assert out["model"] == model


def test_auto_tool_choice_and_absent_temperature_are_left_alone() -> None:
    req = {"model": OPUS, "tool_choice": "auto", "messages": []}
    assert adapt_request(req) == req


@pytest.mark.parametrize("model", [SONNET, OPUS])
def test_both_clients_send_the_adapted_request(model: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The kwargs that reach ``litellm.completion`` are the adapted ones, from ``adapted_completion``
    (build_client's) and from ``CallMeter.completion`` (the report's)."""
    import litellm

    from extractor_mvp.citation_hop import CallMeter
    from extractor_mvp.extractor import adapted_completion

    seen: list[dict[str, Any]] = []

    def capture(*_a: object, **k: Any) -> object:
        seen.append(k)
        raise RuntimeError("captured")

    monkeypatch.setattr(litellm, "completion", capture)
    for call in (adapted_completion, CallMeter().completion):
        with pytest.raises(RuntimeError, match="captured"):
            call(**_req(model))
    assert seen == [adapt_request(_req(model))] * 2
    assert ("temperature" in seen[0]) is (model == SONNET)
