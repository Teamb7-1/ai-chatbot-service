"""인증에 필요한 암호화 연산을 한 곳에 모은다.

HTTP 요청·응답과 DB 조회는 다루지 않는다. 라우터와 dependency는 이 모듈의
작은 함수만 사용하고, hashing 알고리즘 구현은 라이브러리에 위임한다.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class TokenValidationError(Exception):
    """access token이 현재 서비스에서 유효하지 않을 때 발생한다."""


def _secret_key() -> str:
    try:
        return os.environ["SECRET_KEY"]
    except KeyError as exc:
        raise RuntimeError("SECRET_KEY environment variable is required") from exc


def hash_password(password: str) -> str:
    """평문 비밀번호를 현재 권장 알고리즘으로 hash한다."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """평문과 저장된 hash가 일치하는지 확인한다.

    DB에 손상되었거나 지원하지 않는 형식의 값이 있어도 로그인 요청 전체가
    500으로 끝나지 않도록 인증 실패로 처리한다.
    """
    try:
        return _password_hash.verify(password, password_hash)
    except UnknownHashError:
        return False


def create_access_token(
    user_id: int, expires_delta: timedelta | None = None
) -> str:
    """사용자 id를 subject로 갖는 만료 가능한 access token을 발급한다."""
    if user_id < 1:
        raise ValueError("user_id must be a positive integer")

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, _secret_key(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """access token을 검증하고 사용자 id를 반환한다."""
    try:
        payload = jwt.decode(
            token,
            _secret_key(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(payload["sub"])
        if user_id < 1:
            raise ValueError
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError from exc

    return user_id
