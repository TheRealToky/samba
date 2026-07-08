"""User roles (RBAC) — maps to the actors in the SRS use-case diagram.

The diagram generalizes technical and non-technical actors under "Registered
user"; these five concrete roles are the ones called out in the requirements.
"""
from __future__ import annotations

from enum import Enum


class RoleEnum(str, Enum):
    DATA_SCIENTIST = "data_scientist"
    ENVIRONMENTAL_RESEARCHER = "environmental_researcher"
    NGO_POLICYMAKER = "ngo_policymaker"
    STUDENT_PUBLIC = "student_public"
    ADMINISTRATOR = "administrator"

    @classmethod
    def values(cls) -> set[str]:
        return {r.value for r in cls}


# Default role assigned to self-registered users.
DEFAULT_ROLE = RoleEnum.STUDENT_PUBLIC
