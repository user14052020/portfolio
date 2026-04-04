from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import AssetType, sql_enum
from app.models.mixins import Base, TimestampedMixin


class UploadedAsset(Base, TimestampedMixin):
    __tablename__ = "uploaded_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512), unique=True)
    public_url: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    asset_type: Mapped[AssetType] = mapped_column(sql_enum(AssetType, name="asset_type"))
    storage_backend: Mapped[str] = mapped_column(String(50), default="local")
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    related_entity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    related_entity_id: Mapped[int | None] = mapped_column(nullable=True)

    uploaded_by = relationship("User", back_populates="uploaded_assets")
