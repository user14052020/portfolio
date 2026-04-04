import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "Portfolio AI Stylist"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(..., alias="DATABASE_URL")
    sync_database_url: str = Field(..., alias="SYNC_DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    elasticsearch_url: str = Field(..., alias="ELASTICSEARCH_URL")

    secret_key: str = Field(..., alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(43200, alias="REFRESH_TOKEN_EXPIRE_MINUTES")

    initial_admin_email: str = Field("admin@portfolio.dev", alias="INITIAL_ADMIN_EMAIL")
    initial_admin_password: str = Field("admin12345", alias="INITIAL_ADMIN_PASSWORD")

    media_root: Path = Field(Path("/app/media"), alias="MEDIA_ROOT")
    media_url: str = Field("/media", alias="MEDIA_URL")
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list, alias="CORS_ORIGINS")

    comfyui_base_url: str = Field(..., alias="COMFYUI_BASE_URL")
    comfyui_client_id: str = Field("portfolio-client", alias="COMFYUI_CLIENT_ID")
    comfyui_checkpoint_name: str = Field("v1-5-pruned-emaonly.safetensors", alias="COMFYUI_CHECKPOINT_NAME")
    comfyui_workflow_template: Path = Field(
        Path("app/integrations/workflows/fashion_flatlay.json"), alias="COMFYUI_WORKFLOW_TEMPLATE"
    )
    vllm_base_url: str = Field(..., alias="VLLM_BASE_URL")
    vllm_model: str = Field("Qwen/Qwen2.5-3B-Instruct", alias="VLLM_MODEL")
    vllm_api_key: str | None = Field(None, alias="VLLM_API_KEY")
    vllm_timeout_seconds: float = Field(45.0, alias="VLLM_TIMEOUT_SECONDS")
    vllm_temperature: float = Field(0.2, alias="VLLM_TEMPERATURE")
    vllm_max_tokens: int = Field(700, alias="VLLM_MAX_TOKENS")
    enable_search_indexing: bool = Field(True, alias="ENABLE_SEARCH_INDEXING")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
