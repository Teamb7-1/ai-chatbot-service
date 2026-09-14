from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security import (
    JWT_ALGORITHM,
    TokenValidationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

TEST_SECRET = "test-secret-key-with-more-than-thirty-two-bytes"


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)


def test_비밀번호는_평문과_다른_argon2_hash로_저장된다():
    password = "correct-horse-battery-staple"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2")
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_알수없는_hash_형식은_인증_실패로_처리한다():
    assert verify_password("password", "not-a-password-hash") is False


def test_access_token에서_사용자_id를_복원한다():
    token = create_access_token(user_id=12)

    assert decode_access_token(token) == 12


def test_만료된_access_token을_거부한다():
    token = create_access_token(user_id=12, expires_delta=timedelta(seconds=-1))

    with pytest.raises(TokenValidationError):
        decode_access_token(token)


def test_다른_secret으로_서명된_access_token을_거부한다():
    token = create_access_token(user_id=12)
    invalid_token = jwt.encode(
        {
            "sub": "12",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "different-secret-key-with-more-than-thirty-two-bytes",
        algorithm=JWT_ALGORITHM,
    )

    assert token != invalid_token
    with pytest.raises(TokenValidationError):
        decode_access_token(invalid_token)


def test_subject가_없거나_사용자_id가_아니면_거부한다():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    missing_subject = jwt.encode(
        {"exp": expires_at}, TEST_SECRET, algorithm=JWT_ALGORITHM
    )
    invalid_subject = jwt.encode(
        {"sub": "not-an-id", "exp": expires_at},
        TEST_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(missing_subject)
    with pytest.raises(TokenValidationError):
        decode_access_token(invalid_subject)


def test_SECRET_KEY가_없으면_설정_오류를_드러낸다(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_access_token(user_id=12)


def test_유효하지_않은_사용자_id로_token을_만들지_않는다():
    with pytest.raises(ValueError, match="positive integer"):
        create_access_token(user_id=0)
