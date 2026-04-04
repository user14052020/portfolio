from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UploadedAsset
from app.repositories.base import BaseRepository


class UploadsRepository(BaseRepository[UploadedAsset]):
    def __init__(self) -> None:
        super().__init__(UploadedAsset)


uploads_repository = UploadsRepository()

