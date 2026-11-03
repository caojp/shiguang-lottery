"""用户认证接口：注册 / 登录 / 当前用户。"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from .. import db, models
from ..schemas import TokenOut, UserCreate
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def _user_out(row: models.users) -> dict:
    return {"id": row.id, "username": row.username}


@router.post("/register", response_model=TokenOut)
async def register(req: UserCreate) -> TokenOut:
    username = req.username.strip()
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(400, "用户名需为 3-20 位字母、数字或下划线")
    if len(req.password) < 6 or len(req.password) > 64:
        raise HTTPException(400, "密码长度需为 6-64 位")

    async with db.get_session_factory()() as session:
        exists = (
            await session.execute(select(models.users.c.id).where(models.users.c.username == username))
        ).scalar_one_or_none()
        if exists is not None:
            raise HTTPException(409, "用户名已存在")
        result = await session.execute(
            models.users.insert()
            .values(username=username, password_hash=hash_password(req.password))
            .returning(models.users.c.id, models.users.c.username, models.users.c.created_at)
        )
        await session.commit()
        row = result.one()
    return TokenOut(access_token=create_access_token(row.id), user=_user_out(row))


@router.post("/login", response_model=TokenOut)
async def login(req: UserCreate) -> TokenOut:
    async with db.get_session_factory()() as session:
        row = (
            await session.execute(select(models.users).where(models.users.c.username == req.username.strip()))
        ).scalar_one_or_none()
    if row is None or not verify_password(req.password, row.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return TokenOut(access_token=create_access_token(row.id), user=_user_out(row))


@router.get("/me")
async def me(user: models.users = Depends(get_current_user)) -> dict:
    return _user_out(user)
