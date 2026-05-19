"""Seed editable homepage showcase projects.

Use this once after deploying an empty database, or with --replace when the
existing demo project rows should be reset to the bundled homepage defaults.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.integrations.elasticsearch import close_elasticsearch_client
from app.models import Project
from app.seed_data.showcase_projects import DEFAULT_SHOWCASE_PROJECTS
from app.services.search import search_service


async def seed_showcase_projects(*, replace: bool) -> list[Project]:
    async with SessionLocal() as session:
        if replace:
            await session.execute(sa.text("TRUNCATE TABLE project_media, projects RESTART IDENTITY CASCADE"))

        created_or_updated: list[Project] = []
        for project_payload in DEFAULT_SHOWCASE_PROJECTS:
            existing = await session.scalar(select(Project).where(Project.slug == project_payload["slug"]))
            if existing is None:
                project = Project(**project_payload)
                session.add(project)
            else:
                project = existing
                for field, value in project_payload.items():
                    setattr(project, field, value)
            created_or_updated.append(project)

        await session.commit()

        await search_service.ensure_indices()
        for project in created_or_updated:
            await session.refresh(project)
            await search_service.index_project(project)

        return created_or_updated


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed homepage showcase projects into the database.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing project rows and reset ids before inserting the default homepage projects.",
    )
    args = parser.parse_args()

    try:
        projects = await seed_showcase_projects(replace=args.replace)
        print(f"Seeded {len(projects)} showcase projects.")
        for project in projects:
            print(f"- {project.sort_order}: {project.slug}")
    finally:
        await close_elasticsearch_client()


if __name__ == "__main__":
    asyncio.run(main())
