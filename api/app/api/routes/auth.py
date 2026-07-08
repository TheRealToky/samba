"""Auth + user routes (FR-6.1 login, FR-6.2 role-based access)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rbac import require_roles
from app.core.roles import RoleEnum
from app.db import get_db
from app.models.user import User
from app.schemas.user import RoleUpdate, Token, UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    service = UserService(db)
    if service.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    # Self-registration always gets the default (least-privileged) role.
    return service.create_user(name=payload.name, email=payload.email, password=payload.password)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    # OAuth2 form uses `username`; we treat it as the email.
    service = UserService(db)
    user = service.authenticate(email=form.username, password=form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=service.issue_token(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# --- Administrator-only user management (FR-6.2, use case "Manage user & roles") ---

admin_router = APIRouter(prefix="/admin/users", tags=["admin"])


@admin_router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.ADMINISTRATOR)),
) -> list[User]:
    return list(db.execute(select(User).order_by(User.id)).scalars().all())


@admin_router.patch("/{user_id}/role", response_model=UserRead)
def update_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.ADMINISTRATOR)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserService(db).set_role(user, payload.role)
