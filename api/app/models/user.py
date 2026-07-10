"""User entity (class diagram: User).

Attributes: name, email, password_hash, role. Method auth() is implemented in
the service layer (see services/user_service.py).
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.roles import DEFAULT_ROLE
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stored as a string (matches the class diagram); validated against RoleEnum.
    role: Mapped[str] = mapped_column(
        String(50), default=DEFAULT_ROLE.value, server_default=DEFAULT_ROLE.value, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
