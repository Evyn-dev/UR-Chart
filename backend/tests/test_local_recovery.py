"""Local generation is optional and must not disturb shared chat integrations."""
import httpx
import pytest
from app.config import Settings
from app.services.ai import PatientContext, AIUnavailable, build_provider
from app.services.local_recovery import OllamaRecoveryProvider


def test_local_provider_selected_without_api_key():
    settings = Settings(
        _env_file=None,
        ai_provider="ollama",
        ai_api_key="",
        local_ai_model="llama3.2:3b",
        demo_auth_enabled=False,
    )
    provider = build_provider(settings)
    assert isinstance(provider, OllamaRecoveryProvider)


def test_local_model_receives_only_synthetic_context(monkeypatch):
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": "Follow your approved instructions."}}

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, json):
            seen["url"] = url
            seen["json"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    provider = OllamaRecoveryProvider()
    result = provider.respond(
        "Can I exercise?",
        PatientContext(("Only follow your care plan.",), '{"pain_level":2}'),
        [{"role": "user", "content": "Hello"}],
    )
    assert result == "Follow your approved instructions."
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["json"]["messages"][0]["role"] == "system"
    assert "Only follow your care plan" in seen["json"]["messages"][0]["content"]
    assert seen["json"]["messages"][-1] == {"role": "user", "content": "Can I exercise?"}


def test_local_model_failure_is_safely_reported(monkeypatch):
    class OfflineClient:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "Client", OfflineClient)
    with pytest.raises(AIUnavailable, match="Local AI unavailable"):
        OllamaRecoveryProvider().respond("hello", PatientContext(()), [])
