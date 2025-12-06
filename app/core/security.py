from __future__ import annotations
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from app.core.config import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    return _pwd_ctx.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return _pwd_ctx.verify(raw, hashed)

def encode_jwt(payload: dict, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    data = {"iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=minutes)).timestamp()), **payload}
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_alg)

def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])