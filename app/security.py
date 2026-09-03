"""인증에 필요한 암호화 연산을 한 곳에 모은다.

HTTP 요청·응답과 DB 조회는 다루지 않는다. 라우터와 dependency는 이 모듈의
작은 함수만 사용하고, hashing 알고리즘 구현은 라이브러리에 위임한다.
"""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_password_hash = PasswordHash.recommended()


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
