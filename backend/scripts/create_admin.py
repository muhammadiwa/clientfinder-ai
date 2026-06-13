"""
Create initial admin user (idempotent).
Usage: docker compose exec backend python -m scripts.create_admin
       or: make createsuperuser
"""
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User


async def create_admin(
    email: str = "admin@clientfinder.app",
    password: str = "changeme-admin-password",
    full_name: str = "Admin",
) -> User | None:
    """Create the initial admin user if it doesn't exist."""
    await init_db()

    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"User {email} already exists, skipping.")
            return None

        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="owner",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"✓ Admin user created: {email}")
        print(f"  Password: {password}")
        print(f"  User ID:  {user.id}")
        return user


async def main() -> int:
    import os
    email = os.environ.get("ADMIN_EMAIL", "admin@clientfinder.app")
    password = os.environ.get("ADMIN_PASSWORD", "changeme-admin-password")
    full_name = os.environ.get("ADMIN_NAME", "Admin")

    user = await create_admin(email=email, password=password, full_name=full_name)
    return 0 if user is not None else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
