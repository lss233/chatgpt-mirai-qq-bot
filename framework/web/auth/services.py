from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Optional


class AuthService(ABC):
    @abstractmethod
    def is_first_time(self) -> bool:
        pass

    @abstractmethod
    def save_password(self, password: str) -> None:
        pass

    @abstractmethod
    def verify_password(self, password: str) -> bool:
        pass

    @abstractmethod
    def create_access_token(self, expires_delta: Optional[timedelta] = None) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> bool:
        pass


class FileBasedAuthService(AuthService):
    def __init__(self, password_file: Path, secret_key: str):
        self.password_file = password_file
        self.secret_key = secret_key

    def is_first_time(self) -> bool:
        return not self.password_file.exists()

    def save_password(self, password: str) -> None:
        from .utils import hash_password

        self.password_file.parent.mkdir(parents=True, exist_ok=True)
        hashed = hash_password(password)
        with open(self.password_file, "wb") as f:
            f.write(hashed)

    def verify_password(self, password: str) -> bool:
        from .utils import verify_password

        if not self.password_file.exists():
            return False

        with open(self.password_file, "rb") as f:
            hashed = f.read()
        return verify_password(password, hashed)

    def create_access_token(self, expires_delta: Optional[timedelta] = None) -> str:
        from .utils import create_jwt_token

        return create_jwt_token(self.secret_key, expires_delta)

    def verify_token(self, token: str) -> bool:
        from .utils import verify_jwt_token

        return verify_jwt_token(token, self.secret_key)


class MockAuthService(AuthService):
    def __init__(self):
        self._password = None
        self._is_first_time = True

    def is_first_time(self) -> bool:
        return self._is_first_time

    def save_password(self, password: str) -> None:
        self._password = password
        self._is_first_time = False

    def verify_password(self, password: str) -> bool:
        return password == self._password

    def create_access_token(self, expires_delta: Optional[timedelta] = None) -> str:
        return "mock_token"

    def verify_token(self, token: str) -> bool:
        return token == "mock_token"
