import asyncio
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.services.style_catalog import seed_style_catalog


async def main() -> None:
    async with SessionLocal() as session:
        created, updated = await seed_style_catalog(session)
        await session.commit()
    print(f"Style catalog seeded: created={created}, updated={updated}")


if __name__ == "__main__":
    asyncio.run(main())
