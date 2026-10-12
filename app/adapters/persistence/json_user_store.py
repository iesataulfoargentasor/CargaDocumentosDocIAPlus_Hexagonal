"""Las cuentas permanecen fuera del corpus y se releen para permitir revocación."""
import json
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash
from app.domain.user import User, Account
from app.domain.errors import StorageError

class JsonUserStore:
    def __init__(self, path):
        self.path = Path(path)

    def get_active(self, username):
        try:
            users = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
            row = users.get(username)
            if not row or row.get('active') is not True:
                return None
            permissions = row['permissions']
            if not isinstance(permissions, list) or not all(p in ('read', 'upload') for p in permissions) or not isinstance(row['password_hash'], str):
                raise ValueError()
            return Account(User(username, frozenset(permissions)), row['password_hash'])
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise StorageError('No se pudo leer la configuración local de cuentas.') from exc

class ScryptPasswordVerifier:
    def __init__(self):
        self.dummy_hash = generate_password_hash('dummy-password-never-used')

    def verify(self, stored_hash, password):
        try:
            return check_password_hash(stored_hash or self.dummy_hash, password)
        except (ValueError, TypeError):
            return False
