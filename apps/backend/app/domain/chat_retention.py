from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


MAX_CHAT_RETENTION_DAYS = 10


@dataclass(frozen=True, slots=True)
class ChatRetentionPolicy:
    max_age_days: int = MAX_CHAT_RETENTION_DAYS

    def __post_init__(self) -> None:
        if self.max_age_days < 1 or self.max_age_days > MAX_CHAT_RETENTION_DAYS:
            raise ValueError(f"Chat retention must be between 1 and {MAX_CHAT_RETENTION_DAYS} days.")

    def cutoff(self, now: datetime | None = None) -> datetime:
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        return reference - timedelta(days=self.max_age_days)

    def is_expired(self, created_at: datetime, now: datetime | None = None) -> bool:
        return created_at < self.cutoff(now)
