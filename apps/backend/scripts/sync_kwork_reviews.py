"""Sync Kwork profile reviews into the database."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.integrations.elasticsearch import close_elasticsearch_client
from app.repositories.kwork_reviews import kwork_reviews_repository
from app.services.kwork_reviews_parser import DEFAULT_KWORK_PROFILE_URL, kwork_reviews_parser


async def sync_reviews(*, source_url: str, replace: bool, limit: int) -> int:
    parsed_reviews = await kwork_reviews_parser.parse_profile_reviews(source_url, limit=limit)
    review_rows = [review.to_model_data() for review in parsed_reviews]

    async with SessionLocal() as session:
        if replace:
            await kwork_reviews_repository.replace_reviews(session, review_rows)
        else:
            await kwork_reviews_repository.upsert_reviews(session, review_rows)
        await session.commit()
    return len(review_rows)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Kwork profile reviews into the database.")
    parser.add_argument("--source-url", default=DEFAULT_KWORK_PROFILE_URL)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    try:
        imported = await sync_reviews(source_url=args.source_url, replace=args.replace, limit=args.limit)
        print(f"Imported {imported} Kwork reviews from {args.source_url}.")
    finally:
        await close_elasticsearch_client()


if __name__ == "__main__":
    asyncio.run(main())
