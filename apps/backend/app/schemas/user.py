from pydantic import BaseModel, field_validator

from app.schemas.common import TimestampedRead


class RoleRead(TimestampedRead):
    id: int
    name: str
    description: str | None = None


class UserRead(TimestampedRead):
    id: int
    email: str
    full_name: str
    is_active: bool
    role: RoleRead


class UserCreateRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role_name: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Email is required")
        return normalized
