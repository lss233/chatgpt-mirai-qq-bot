import bcrypt
import jwt
from datetime import datetime, timedelta, UTC
from typing import Optional
from pathlib import Path

from quart import g
from framework.config.global_config import GlobalConfig


def get_password_file_path() -> Path:
    global_config: GlobalConfig = g.container.resolve(GlobalConfig)
    return Path(global_config.web.password_file)


def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)

def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)

def create_access_token(expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=30)
    

    to_encode = {"exp": expire}
    global_config: GlobalConfig = g.container.resolve(GlobalConfig)
    secret_key = global_config.web.secret_key
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str) -> bool:
    try:
        global_config: GlobalConfig = g.container.resolve(GlobalConfig)
        secret_key = global_config.web.secret_key
        jwt.decode(token, secret_key, algorithms=["HS256"])
        return True

    except:
        return False

def is_first_time() -> bool:
    password_file = get_password_file_path()
    return not password_file.exists()

def save_password(password: str) -> None:
    password_file = get_password_file_path()
    password_file.parent.mkdir(parents=True, exist_ok=True)
    
    hashed = hash_password(password)
    with open(password_file, "wb") as f:
        f.write(hashed)

def verify_saved_password(password: str) -> bool:
    password_file = get_password_file_path()
    if not password_file.exists():
        return False
    
    with open(password_file, "rb") as f:
        hashed = f.read()
    
    return verify_password(password, hashed) 