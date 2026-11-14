from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./urchart.db"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    demo_auth_enabled: bool = False
    demo_tokens: dict[str, str] = {}
    ai_provider: Literal["disabled", "approved_instructions"] = "disabled"
    ai_api_key: str = ""

    @model_validator(mode="after")
    def secure_defaults(self):
        if self.app_env == "production" and self.demo_auth_enabled:
            raise ValueError("Demo authentication is forbidden in production")
        if any(len(token) < 32 or not user.strip() for token, user in self.demo_tokens.items()):
            raise ValueError("Demo tokens need at least 32 characters and a nonempty identity")
        if "*" in self.allowed_origins:
            raise ValueError("CORS origins must be explicit")
        return self
