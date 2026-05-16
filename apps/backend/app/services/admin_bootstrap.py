from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Role, User
from app.models.enums import RoleCode
from app.repositories.users import users_repository


class ConfiguredAdminBootstrapService:
    def __init__(
        self,
        *,
        settings: object | None = None,
        password_hasher=None,
        password_verifier=None,
    ) -> None:
        self._settings = settings
        self._password_hasher = password_hasher
        self._password_verifier = password_verifier

    async def ensure_configured_admin(self, session: AsyncSession) -> None:
        settings = self._resolved_settings()
        email = str(getattr(settings, "initial_admin_email", "") or "").strip().lower()
        password = str(getattr(settings, "initial_admin_password", "") or "").strip()
        if not email or not password:
            return

        admin_role, role_created = await self._ensure_admin_role(session)
        configured_admin = await users_repository.get_by_email(session, email)

        changed = role_created
        if configured_admin is None:
            session.add(
                User(
                    email=email,
                    full_name="Portfolio Admin",
                    hashed_password=self._get_password_hash(password),
                    is_active=True,
                    role_id=admin_role.id,
                )
            )
            changed = True
        else:
            changed = self._sync_existing_admin(
                configured_admin,
                admin_role_id=admin_role.id,
                password=password,
            ) or changed

        if changed:
            await session.commit()

    async def _ensure_admin_role(self, session: AsyncSession) -> tuple[Role, bool]:
        admin_role = await session.scalar(select(Role).where(Role.name == RoleCode.ADMIN.value))
        if admin_role is not None:
            return admin_role, False

        admin_role = Role(
            name=RoleCode.ADMIN.value,
            description="Platform administrator",
        )
        session.add(admin_role)
        await session.flush()
        return admin_role, True

    def _sync_existing_admin(self, user: User, *, admin_role_id: int, password: str) -> bool:
        changed = False
        if user.role_id != admin_role_id:
            user.role_id = admin_role_id
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not self._verify_password(password, user.hashed_password):
            user.hashed_password = self._get_password_hash(password)
            changed = True
        if not (user.full_name or "").strip():
            user.full_name = "Portfolio Admin"
            changed = True
        return changed

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        if self._password_verifier is not None:
            return self._password_verifier(plain_password, hashed_password)
        from app.core.security import verify_password as runtime_verify_password

        return runtime_verify_password(plain_password, hashed_password)

    def _get_password_hash(self, password: str) -> str:
        if self._password_hasher is not None:
            return self._password_hasher(password)
        from app.core.security import get_password_hash as runtime_get_password_hash

        return runtime_get_password_hash(password)

    def _resolved_settings(self) -> object:
        return self._settings or get_settings()


configured_admin_bootstrap_service = ConfiguredAdminBootstrapService()
