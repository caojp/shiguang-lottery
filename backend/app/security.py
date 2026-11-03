"""用户认证：密码哈希（PBKDF2-SHA256，标准库实现）与 JWT（PyJWT）。

设计说明：
- 密码使用 `hashlib.pbkdf2_hmac`（标准库，避免 bcrypt/passlib 在 slim 镜像上的
  编译或版本兼容问题）；存储格式 `pbkdf2_sha256$iter$salt_hex$hash_hex`。
- Token 使用 HS256，sub 为用户 ID，有效期由 settings.token_expire_minutes 控制。
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from . import db, models
from .settings import get_settings

_PBKDF2_ITERATIONS = 600_000
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, dk_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expire_minutes)
    payload = {"sub": str(user_id), "exp": exp}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


async def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> models.users:
    """FastAPI 依赖：解析 Bearer Token 并返回 users 表行；失败统一 401。"""
    if cred is None:
        raise HTTPException(401, "未登录")
    try:
        payload = jwt.decode(cred.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登录已失效，请重新登录")
    try:
        user_id = int(payload.get("sub", "0"))
    except (TypeError, ValueError):
        raise HTTPException(401, "登录已失效，请重新登录")
    async with db.get_session_factory()() as session:
        row = (
            await session.execute(select(models.users).where(models.users.c.id == user_id))
        ).scalar_one_or_none()
    if row is None:
        raise HTTPException(401, "用户不存在，请重新登录")
    return row
