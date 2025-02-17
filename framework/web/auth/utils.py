from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt


def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)


def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


def create_jwt_token(secret_key: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=30)

    to_encode = {"exp": expire}
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def verify_jwt_token(token: str, secret_key: str) -> bool:
    try:
        jwt.decode(token, secret_key, algorithms=["HS256"])
        return True
    except:
        return False
