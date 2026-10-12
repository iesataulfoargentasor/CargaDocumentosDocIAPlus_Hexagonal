from app.application.ports import UserRepository, PasswordVerifier

class AuthService:
    def __init__(self, users: UserRepository, passwords: PasswordVerifier):
        self.users, self.passwords = users, passwords

    def get_user(self, username):
        account = self.users.get_active(username)
        return account.user if account else None

    def authenticate(self, username, password):
        account = self.users.get_active(username[:80])
        valid = self.passwords.verify(account.password_hash if account else None, password[:256])
        return account.user if account and valid and len(password) <= 256 else None
