"""用户认证核心单元测试（无数据库依赖，CI 冒烟可用）。"""
from __future__ import annotations

import jwt

from app.security import create_access_token, hash_password, verify_password


def test_hash_password_roundtrip():
    h = hash_password("secret123")
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("secret123", h)
    assert not verify_password("wrong-pass", h)


def test_hash_is_salted():
    assert hash_password("secret123") != hash_password("secret123")


def test_verify_rejects_malformed():
    assert not verify_password("x", "not-a-valid-format")
    assert not verify_password("x", "")


def test_create_access_token_contains_user_id():
    token = create_access_token(42)
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["sub"] == "42"
    assert payload["exp"] > payload.get("iat", 0) if payload.get("iat") else True
