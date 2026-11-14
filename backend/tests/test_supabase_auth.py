from unittest.mock import Mock
import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import authenticated_identity
from app.config import Settings

USER_ID = "11111111-1111-4111-8111-111111111111"


def settings():
    return Settings(
        _env_file=None, app_env="production",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="test-publishable-key",
        demo_auth_enabled=False,
    )


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_supabase_identity_uses_validated_stable_uuid(monkeypatch):
    def fake_get(url, headers, timeout):
        assert url == "https://example.supabase.co/auth/v1/user"
        assert headers["Authorization"] == "Bearer signed-test-token"
        assert headers["apikey"] == "test-publishable-key"
        return Mock(status_code=200, json=lambda: {"id": USER_ID})
    monkeypatch.setattr(httpx, "get", fake_get)
    assert authenticated_identity(settings(), bearer("signed-test-token")) == "supabase:" + USER_ID


def test_rejected_token_is_not_authenticated(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Mock(status_code=401))
    with pytest.raises(HTTPException) as exc:
        authenticated_identity(settings(), bearer("invalid-token"))
    assert exc.value.status_code == 401


def test_missing_token_is_rejected():
    with pytest.raises(HTTPException) as exc:
        authenticated_identity(settings(), None)
    assert exc.value.status_code == 401


def test_auth_outage_fails_closed(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("synthetic outage")
    monkeypatch.setattr(httpx, "get", fail)
    with pytest.raises(HTTPException) as exc:
        authenticated_identity(settings(), bearer("test"))
    assert exc.value.status_code == 503


@pytest.mark.parametrize("demo_settings", [
    {"demo_auth_enabled": True},
    {"hosted_demo_code_hash": "a" * 64},
    {"demo_tokens": {"b" * 40: "synthetic-user"}},
])
def test_all_demo_authentication_is_forbidden_in_production(demo_settings):
    with pytest.raises(ValueError, match="demo authentication"):
        Settings(_env_file=None, app_env="production", **demo_settings)


def test_caregiver_identity_uses_server_only_supabase_admin_key(monkeypatch):
    from app.services.caregivers import verify_caregiver_identity
    settings_value = Settings(
        _env_file=None, app_env="production",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable",
        supabase_service_role_key="server-only-secret",
        redis_url="redis://localhost:6379/0",
    )
    def fake_get(url, headers, timeout):
        assert url == "https://example.supabase.co/auth/v1/admin/users/" + USER_ID
        assert headers["apikey"] == "server-only-secret"
        assert headers["Authorization"] == "Bearer server-only-secret"
        return Mock(status_code=200, json=lambda: {"id": USER_ID})
    monkeypatch.setattr(httpx, "get", fake_get)
    assert verify_caregiver_identity(settings_value, "supabase:" + USER_ID) is None


def test_caregiver_identity_rejects_non_supabase_ids_without_network():
    from app.services.caregivers import verify_caregiver_identity
    settings_value = Settings(
        _env_file=None, app_env="production",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable",
        supabase_service_role_key="server-only-secret",
        redis_url="redis://localhost:6379/0",
    )
    with pytest.raises(HTTPException) as exc:
        verify_caregiver_identity(settings_value, "synthetic-caregiver")
    assert exc.value.status_code == 422


def test_production_requires_shared_rate_limiter_and_supabase_admin_key():
    with pytest.raises(ValueError, match="Production requires Supabase"):
        Settings(_env_file=None, app_env="production",
                 supabase_url="https://example.supabase.co",
                 supabase_publishable_key="publishable")
    with pytest.raises(ValueError, match="Redis URL"):
        Settings(_env_file=None, app_env="production",
                 supabase_url="https://example.supabase.co",
                 supabase_publishable_key="publishable",
                 supabase_service_role_key="server-only-secret")
