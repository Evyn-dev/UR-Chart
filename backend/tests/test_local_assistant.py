import json
import httpx
import pytest
from sqlalchemy import select
from app.config import Settings
from app.models import Patient, RecoveryPlan
from app.services.ai import PatientContext, ApprovedInstructionsProvider, build_provider
from app.services.local_recovery import OllamaRecoveryProvider


def test_hosted_ollama_configuration_never_uses_localhost(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    assert isinstance(build_provider(Settings(_env_file=None, ai_provider="ollama", app_env="production")), ApprovedInstructionsProvider)
    settings = Settings(_env_file=None, ai_provider="ollama")
    assert isinstance(build_provider(settings), OllamaRecoveryProvider)
    monkeypatch.setenv("VERCEL", "1")
    assert isinstance(build_provider(settings), ApprovedInstructionsProvider)


@pytest.mark.parametrize("failure", ["offline", "empty", "malformed", "oversized"])
def test_local_failure_falls_back_without_leaking_errors(monkeypatch, failure):
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
            assert kwargs["follow_redirects"] is False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            if failure == "offline": raise httpx.ConnectError("secret internal detail")
            body = {} if failure == "malformed" else {"message": {"content": "" if failure == "empty" else "x" * 20001}}
            return httpx.Response(200, json=body, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "Client", Client)
    result = OllamaRecoveryProvider().respond("question", PatientContext(("Approved demo content",)), [])
    assert "Deterministic fallback" in result and "Approved demo content" in result
    assert "secret" not in result


def test_local_response_is_labeled_and_uses_existing_chat_protocol(monkeypatch):
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            assert url == "http://127.0.0.1:11434/api/chat"
            assert json["stream"] is False
            assert "Only my records" in json["messages"][0]["content"]
            assert json["messages"][-1]["content"] == "question"
            return httpx.Response(200, json={"message": {"content": "Example draft"}}, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "Client", Client)
    result = OllamaRecoveryProvider().respond("question", PatientContext((), "Only my records"), [])
    assert result.startswith("Local AI draft") and "Example draft" in result


def test_chat_context_is_private_and_conversation_persists(client, app, auth, other):
    for headers, name in [(auth, "OWN MEDICATION"), (other, "FOREIGN SECRET")]:
        assert client.post("/api/medications", headers=headers, json={"name": name, "dosage": "demo", "schedule": "demo"}).status_code == 201
    with app.state.sessions() as db:
        patients = db.scalars(select(Patient).order_by(Patient.user_id)).all()
        db.add(RecoveryPlan(patient_id=patients[1].id, title="Other", approved_by="clinician", approved_instructions="FOREIGN INSTRUCTIONS"))
        db.commit()
    class Spy:
        def respond(self, prompt, context, history):
            assert "OWN MEDICATION" in context.patient_snapshot
            assert "FOREIGN" not in context.patient_snapshot + str(context.approved_instructions) + json.dumps(history)
            return "Deterministic test response"
    app.state.ai = Spy()
    reply = client.post("/api/chat/message", headers=auth, json={"message": "my records"}).json()["data"]
    path = f"/api/chat/conversations/{reply['conversation_id']}"
    assert len(client.get(path, headers=auth).json()["data"]["messages"]) == 2
    assert client.get(path, headers=other).status_code == 404
    assert client.post("/api/chat/message", headers=other, json={"message": "read", "conversation_id": reply["conversation_id"]}).status_code == 404
