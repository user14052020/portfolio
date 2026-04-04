from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.upload import UploadResponse
from app.services.uploads import upload_service


router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    related_entity: str | None = Form(default=None),
    related_entity_id: int | None = Form(default=None),
) -> UploadResponse:
    asset = await upload_service.save_upload(
        session,
        file,
        related_entity=related_entity,
        related_entity_id=related_entity_id,
        uploaded_by_id=current_user.id if current_user else None,
    )
    await session.commit()
    return UploadResponse(asset=asset)

