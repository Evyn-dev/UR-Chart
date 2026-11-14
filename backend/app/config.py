from typing import Literal
import re
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./urchart.db"
    database_schema: str | None = None
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    redis_url: str = ""
    api_rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    sensitive_rate_limit_per_minute: int = Field(default=20, ge=1, le=1000)
    caregiver_invites_per_hour: int = Field(default=10, ge=1, le=1000)
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    demo_auth_enabled: bool = False
    hosted_demo_code_hash: str = ""
    demo_tokens: dict[str, str] = {}
    ai_provider: Literal["disabled", "approved_instructions"] = "disabled"
    ai_api_key: str = ""
    risk_rules_file: str | None = None

    @model_validator(mode="after")
    def secure_defaults(self):
        if self.app_env == "production":
            if self.demo_auth_enabled or self.hosted_demo_code_hash or self.demo_tokens:
                raise ValueError("All demo authentication methods and demo tokens are forbidden in production")
            if not (self.supabase_url and self.supabase_publishable_key and self.supabase_service_role_key):
                raise ValueError("Production requires Supabase URL, publishable key, and server-only service-role key")
            if not self.redis_url.startswith(("redis://", "rediss://")):
                raise ValueError("Production requires a Redis URL for shared rate limiting")
        if self.hosted_demo_code_hash and not re.fullmatch(r"[0-9a-f]{64}", self.hosted_demo_code_hash):
            raise ValueError("Hosted demo code hash must be SHA-256 hex")
        if any(len(token) < 32 or not user.strip() for token, user in self.demo_tokens.items()):
            raise ValueError("Demo tokens need at least 32 characters and a nonempty identity")
        if self.database_schema and not re.fullmatch(r"[a-z_][a-z0-9_]*", self.database_schema):
            raise ValueError("Database schema must be a safe PostgreSQL identifier")
        if bool(self.supabase_url) != bool(self.supabase_publishable_key):
            raise ValueError("Supabase URL and publishable key must both be configured")
        if self.supabase_service_role_key and not self.supabase_url:
            raise ValueError("Supabase service-role key requires a Supabase URL")
        if self.redis_url and not self.redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must use redis:// or rediss://")
        if self.supabase_url and not self.supabase_url.startswith("https://"):
            raise ValueError("Supabase Auth URL must use HTTPS")
        if "*" in self.allowed_origins:
            raise ValueError("CORS origins must be explicit")
        return self
