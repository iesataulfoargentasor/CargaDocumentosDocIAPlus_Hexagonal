from dataclasses import dataclass
from app.domain.errors import PermissionDenied

@dataclass(frozen=True)
class User:
    username: str
    permissions: frozenset[str]

    def require(self, permission):
        if permission not in self.permissions:
            raise PermissionDenied('Tu cuenta no tiene permiso para esta operación.')

@dataclass(frozen=True)
class Account:
    user: User
    password_hash: str
