from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleFashionItemFacet(Base):
    __tablename__ = "style_fashion_item_facets"
    __table_args__ = (
        UniqueConstraint("style_id", "facet_version", name="uq_style_fashion_item_facets_style_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    facet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    tops_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    bottoms_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    shoes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    accessories_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    hair_makeup_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    signature_details_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
