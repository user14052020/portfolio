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
    comfyui_output_root: Path | None = Field(None, alias="COMFYUI_OUTPUT_ROOT")
    comfyui_client_id: str = Field("portfolio-client", alias="COMFYUI_CLIENT_ID")
    comfyui_diffusion_model_name: str = Field(
        "flux1-krea-dev_fp8_scaled.safetensors", alias="COMFYUI_DIFFUSION_MODEL_NAME"
    )
    comfyui_text_encoder_t5_name: str = Field(
        "t5xxl_fp8_e4m3fn.safetensors", alias="COMFYUI_TEXT_ENCODER_T5_NAME"
    )
    comfyui_text_encoder_clip_l_name: str = Field(
        "clip_l.safetensors", alias="COMFYUI_TEXT_ENCODER_CLIP_L_NAME"
    )
    comfyui_vae_name: str = Field("ae.safetensors", alias="COMFYUI_VAE_NAME")
    comfyui_workflow_template: Path = Field(
        Path("app/integrations/workflows/fashion_flatlay.json"), alias="COMFYUI_WORKFLOW_TEMPLATE"
    )
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    openai_timeout_seconds: float = Field(45.0, alias="OPENAI_TIMEOUT_SECONDS")
    vllm_base_url: str = Field(..., alias="VLLM_BASE_URL")
    vllm_model: str = Field("Qwen/Qwen2.5-3B-Instruct", alias="VLLM_MODEL")
    vllm_api_key: str | None = Field(None, alias="VLLM_API_KEY")
    vllm_timeout_seconds: float = Field(45.0, alias="VLLM_TIMEOUT_SECONDS")
    vllm_temperature: float = Field(0.2, alias="VLLM_TEMPERATURE")
    vllm_max_tokens: int = Field(420, alias="VLLM_MAX_TOKENS")
    chat_message_cooldown_seconds: int = Field(60, alias="CHAT_MESSAGE_COOLDOWN_SECONDS")
    generation_job_timeout_seconds: int = Field(300, alias="GENERATION_JOB_TIMEOUT_SECONDS")
    generation_queue_refresh_cooldown_seconds: int = Field(60, alias="GENERATION_QUEUE_REFRESH_COOLDOWN_SECONDS")
    generation_dispatch_lock_timeout_seconds: int = Field(30, alias="GENERATION_DISPATCH_LOCK_TIMEOUT_SECONDS")
    comfyui_stalled_job_seconds: int = Field(180, alias="COMFYUI_STALLED_JOB_SECONDS")
    comfyui_stalled_job_auto_interrupt: bool = Field(True, alias="COMFYUI_STALLED_JOB_AUTO_INTERRUPT")
    generation_job_poll_interval_seconds: int = Field(10, alias="GENERATION_JOB_POLL_INTERVAL_SECONDS")
    enable_generation_job_poller: bool = Field(True, alias="ENABLE_GENERATION_JOB_POLLER")
    chat_retention_days: int = Field(10, ge=1, le=10, alias="CHAT_RETENTION_DAYS")
    chat_retention_cleanup_interval_seconds: int = Field(
        3600,
        ge=60,
        alias="CHAT_RETENTION_CLEANUP_INTERVAL_SECONDS",
    )
    enable_chat_retention_cleanup: bool = Field(True, alias="ENABLE_CHAT_RETENTION_CLEANUP")
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

    @field_validator("comfyui_output_root", mode="before")
    @classmethod
    def empty_comfyui_output_root_to_none(cls, value: str | Path | None) -> str | Path | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
