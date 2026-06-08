from pydantic import BaseModel, Field


class BackupRestoreResult(BaseModel):
    restored: dict[str, int] = Field(default_factory=dict)
    media_files_restored: int = 0
    warnings: list[str] = Field(default_factory=list)
