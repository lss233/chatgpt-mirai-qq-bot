from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt


def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)


def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


def _ensure_valid_secret(secret_key: str) -> str:
    """Reject empty secret keys: an empty HMAC key allows anyone to forge
    valid admin tokens (known empty-key JWT bypass class)."""
    if not secret_key:
        raise ValueError(
            "web.secret_key is empty! Refusing to sign/verify JWT. "
            "A strong key is auto-generated on startup."
        )
    return secret_key


def create_jwt_token(secret_key: str, expires_delta: Optional[timedelta] = None) -> str:
    secret_key = _ensure_valid_secret(secret_key)
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=30)

    to_encode = {"exp": expire}
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def verify_jwt_token(token: str, secret_key: str) -> bool:
    try:
        secret_key = _ensure_valid_secret(secret_key)
        jwt.decode(token, secret_key, algorithms=["HS256"])
        return True
    except ValueError:
        raise
    except Exception:
        return False
