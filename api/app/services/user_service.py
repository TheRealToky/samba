"""User service — implements User.auth() and account creation (FR-6.1).

Kept as a thin service layer so the shape mirrors the class diagram's methods
rather than leaking DB logic into the routes.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import DEFAULT_ROLE, RoleEnum
from app.core.security import create_access_token, hash_password, needs_rehash, verify_password
from app.models.user import User


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def create_user(self, name: str, email: str, password: str, role: RoleEnum = DEFAULT_ROLE) -> User:
        user = User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            role=role.value,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        """User.auth(): verify credentials, return the user or None."""
        user = self.get_by_email(email.lower())
        if user is None or not verify_password(password, user.password_hash):
            return None
        # Transparent hash upgrade if Argon2 parameters changed.
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            self.db.commit()
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(subject=str(user.id), role=user.role)

    def set_role(self, user: User, role: RoleEnum) -> User:
        user.role = role.value
        self.db.commit()
        self.db.refresh(user)
        return user
