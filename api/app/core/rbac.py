"""Role-based access control dependency (FR-6.2).

Usage in a route:

    @router.get("/admin", dependencies=[Depends(require_roles(RoleEnum.ADMINISTRATOR))])

or to receive the user object:

    def handler(user: User = Depends(require_roles(RoleEnum.DATA_SCIENTIST))):
        ...

Administrators always pass.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.core.roles import RoleEnum
from app.models.user import User


def require_roles(*allowed: RoleEnum) -> Callable[..., User]:
    allowed_values = {r.value for r in allowed}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role == RoleEnum.ADMINISTRATOR.value or user.role in allowed_values:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )

    return dependency
