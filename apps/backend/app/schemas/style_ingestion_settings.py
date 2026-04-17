from pydantic import BaseModel, Field, model_validator

from app.schemas.common import TimestampedRead


class StyleIngestionRuntimeSettingsUpdate(BaseModel):
    min_delay_seconds: float = Field(ge=0.0)
    max_delay_seconds: float = Field(ge=0.0)
    jitter_ratio: float = Field(ge=0.0, le=1.0)
    empty_body_cooldown_min_seconds: float = Field(ge=0.0)
    empty_body_cooldown_max_seconds: float = Field(ge=0.0)
    retry_backoff_seconds: float = Field(ge=0.0)
    retry_backoff_jitter_seconds: float = Field(ge=0.0)
    worker_idle_sleep_seconds: float = Field(ge=0.1)
    worker_lease_ttl_seconds: float = Field(ge=5.0)
    worker_lease_heartbeat_interval_seconds: float = Field(ge=1.0)

    @model_validator(mode="after")
    def validate_ranges(self) -> "StyleIngestionRuntimeSettingsUpdate":
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError("max_delay_seconds must be greater than or equal to min_delay_seconds")
        if self.empty_body_cooldown_max_seconds < self.empty_body_cooldown_min_seconds:
            raise ValueError(
                "empty_body_cooldown_max_seconds must be greater than or equal to "
                "empty_body_cooldown_min_seconds"
            )
        if self.worker_lease_heartbeat_interval_seconds >= self.worker_lease_ttl_seconds:
            raise ValueError(
                "worker_lease_heartbeat_interval_seconds must be lower than worker_lease_ttl_seconds"
            )
        return self


class StyleIngestionRuntimeSettingsRead(TimestampedRead):
    id: int
    source_name: str
    min_delay_seconds: float
    max_delay_seconds: float
    jitter_ratio: float
    empty_body_cooldown_min_seconds: float
    empty_body_cooldown_max_seconds: float
    retry_backoff_seconds: float
    retry_backoff_jitter_seconds: float
    worker_idle_sleep_seconds: float
    worker_lease_ttl_seconds: float
    worker_lease_heartbeat_interval_seconds: float
