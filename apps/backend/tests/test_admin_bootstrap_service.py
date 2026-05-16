import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models import Role, User
from app.services.admin_bootstrap import ConfiguredAdminBootstrapService


class FakeSession:
    def __init__(self, *, role: Role | None = None) -> None:
        self.role = role
        self.added: list[object] = []
        self.flush_calls = 0
        self.commit_calls = 0

    async def scalar(self, statement):
        return self.role

    def add(self, obj: object) -> None:
        self.added.append(obj)
        if isinstance(obj, Role):
            self.role = obj

    async def flush(self) -> None:
        self.flush_calls += 1
        if self.role is not None and self.role.id is None:
            self.role.id = 1

    async def commit(self) -> None:
        self.commit_calls += 1


class ConfiguredAdminBootstrapServiceTests(unittest.IsolatedAsyncioTestCase):
    def _hash(self, value: str) -> str:
        return f"hashed::{value}"

    def _verify(self, plain: str, hashed: str) -> bool:
        return hashed == self._hash(plain)

    async def test_service_creates_missing_admin_role_and_user_from_settings(self) -> None:
        service = ConfiguredAdminBootstrapService(
            settings=SimpleNamespace(
                initial_admin_email="admin@portfolio.local",
                initial_admin_password="admin12345",
            ),
            password_hasher=self._hash,
            password_verifier=self._verify,
        )
        session = FakeSession()

        with patch(
            "app.services.admin_bootstrap.users_repository.get_by_email",
            new=AsyncMock(return_value=None),
        ):
            await service.ensure_configured_admin(session)

        self.assertEqual(session.flush_calls, 1)
        self.assertEqual(session.commit_calls, 1)
        created_role = next(item for item in session.added if isinstance(item, Role))
        created_user = next(item for item in session.added if isinstance(item, User))
        self.assertEqual(created_role.name, "admin")
        self.assertEqual(created_user.email, "admin@portfolio.local")
        self.assertTrue(created_user.is_active)
        self.assertEqual(created_user.role_id, created_role.id)
        self.assertTrue(service._verify_password("admin12345", created_user.hashed_password))

    async def test_service_syncs_existing_configured_admin_password_role_and_status(self) -> None:
        service = ConfiguredAdminBootstrapService(
            settings=SimpleNamespace(
                initial_admin_email="admin@portfolio.local",
                initial_admin_password="fresh-password",
            ),
            password_hasher=self._hash,
            password_verifier=self._verify,
        )
        session = FakeSession(role=Role(id=7, name="admin", description="Platform administrator"))
        existing_user = User(
            id=3,
            email="admin@portfolio.local",
            full_name="",
            hashed_password=self._hash("stale-password"),
            is_active=False,
            role_id=2,
        )

        with patch(
            "app.services.admin_bootstrap.users_repository.get_by_email",
            new=AsyncMock(return_value=existing_user),
        ):
            await service.ensure_configured_admin(session)

        self.assertEqual(session.commit_calls, 1)
        self.assertEqual(existing_user.role_id, 7)
        self.assertTrue(existing_user.is_active)
        self.assertEqual(existing_user.full_name, "Portfolio Admin")
        self.assertTrue(service._verify_password("fresh-password", existing_user.hashed_password))

    async def test_service_leaves_already_synced_configured_admin_untouched(self) -> None:
        service = ConfiguredAdminBootstrapService(
            settings=SimpleNamespace(
                initial_admin_email="admin@portfolio.local",
                initial_admin_password="admin12345",
            ),
            password_hasher=self._hash,
            password_verifier=self._verify,
        )
        session = FakeSession(role=Role(id=5, name="admin", description="Platform administrator"))
        existing_user = User(
            id=5,
            email="admin@portfolio.local",
            full_name="Portfolio Admin",
            hashed_password=self._hash("admin12345"),
            is_active=True,
            role_id=5,
        )

        with patch(
            "app.services.admin_bootstrap.users_repository.get_by_email",
            new=AsyncMock(return_value=existing_user),
        ):
            await service.ensure_configured_admin(session)

        self.assertEqual(session.commit_calls, 0)
        self.assertEqual(session.added, [])


if __name__ == "__main__":
    unittest.main()
