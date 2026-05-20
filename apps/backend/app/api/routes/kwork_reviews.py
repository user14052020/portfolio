from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import KworkReview, User
from app.repositories.kwork_reviews import kwork_reviews_repository
from app.schemas.kwork_review import (
    KworkReviewRead,
    KworkReviewsPage,
    KworkReviewsSyncRequest,
    KworkReviewsSyncResult,
    KworkReviewUpdate,
)
from app.services.kwork_reviews_parser import kwork_reviews_parser


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/", response_model=KworkReviewsPage)
async def list_published_reviews(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    offset: int = 0,
    limit: int = 3,
) -> KworkReviewsPage:
    bounded_offset = max(offset, 0)
    bounded_limit = min(max(limit, 1), 24)
    items, total = await kwork_reviews_repository.list_reviews_page(
        session,
        only_published=True,
        offset=bounded_offset,
        limit=bounded_limit,
    )
    return KworkReviewsPage(items=items, total=total, offset=bounded_offset, limit=bounded_limit)


@router.get("/admin/", response_model=KworkReviewsPage)
async def list_admin_reviews(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
    offset: int = 0,
    limit: int = 10,
) -> KworkReviewsPage:
    bounded_offset = max(offset, 0)
    bounded_limit = min(max(limit, 1), 50)
    items, total = await kwork_reviews_repository.list_reviews_page(
        session,
        only_published=False,
        offset=bounded_offset,
        limit=bounded_limit,
    )
    return KworkReviewsPage(items=items, total=total, offset=bounded_offset, limit=bounded_limit)


@router.post("/sync", response_model=KworkReviewsSyncResult)
async def sync_kwork_reviews(
    payload: KworkReviewsSyncRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> KworkReviewsSyncResult:
    try:
        parsed_reviews = await kwork_reviews_parser.parse_profile_reviews(
            payload.source_url,
            limit=payload.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse Kwork reviews: {exc}",
        ) from exc

    review_rows = [review.to_model_data() for review in parsed_reviews]
    if payload.replace:
        await kwork_reviews_repository.replace_reviews(session, review_rows)
    else:
        await kwork_reviews_repository.upsert_reviews(session, review_rows)
    await session.commit()
    items, total = await kwork_reviews_repository.list_reviews_page(
        session,
        only_published=False,
        offset=0,
        limit=10,
    )
    return KworkReviewsSyncResult(
        source_url=payload.source_url,
        imported=len(review_rows),
        total=total,
        page=KworkReviewsPage(items=items, total=total, offset=0, limit=10),
    )


@router.patch("/{review_id}", response_model=KworkReviewRead)
async def update_kwork_review(
    review_id: int,
    payload: KworkReviewUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> KworkReview:
    review = await kwork_reviews_repository.get(session, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(review, key, value)
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review
