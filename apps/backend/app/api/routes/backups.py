import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import User
from app.schemas.backup import BackupRestoreResult
from app.services.backups import backup_service


router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("/download")
async def download_backup(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    archive_path = await backup_service.create_backup_archive(session)
    filename = f"portfolio-backup-{archive_path.stem.replace('portfolio-backup-', '')}.zip"

    return FileResponse(
        archive_path,
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(_delete_file, archive_path),
    )


@router.post("/restore", response_model=BackupRestoreResult)
async def restore_backup(
    file: Annotated[UploadFile, File(...)],
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BackupRestoreResult:
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup file must be a .zip archive")

    archive_path = await _store_upload_file(file)
    try:
        result = await backup_service.restore_backup_archive(session, archive_path)
        await session.commit()
        return BackupRestoreResult(**result)
    except (ValueError, zipfile.BadZipFile) as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _delete_file(archive_path)


async def _store_upload_file(file: UploadFile) -> Path:
    import shutil
    import tempfile

    with tempfile.NamedTemporaryFile(prefix="portfolio-restore-", suffix=".zip", delete=False) as handle:
        shutil.copyfileobj(file.file, handle)
        return Path(handle.name)


def _delete_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
