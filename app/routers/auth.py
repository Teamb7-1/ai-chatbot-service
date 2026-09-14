"""회원가입·로그인과 현재 사용자 인증 API."""

from fastapi import APIRouter, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app import crud
from app.deps import ACCESS_TOKEN_COOKIE_NAME, CurrentUser, DbSession
from app.schemas import AppError, ErrorCode, LoginRequest, RegisterRequest, UserResponse
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["auth"])

# 존재하지 않는 username도 같은 비용으로 검증해 계정 존재 여부를 추측하기 어렵게 한다.
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


def _is_duplicate_username(error: IntegrityError) -> bool:
    original = error.orig
    diagnostic = getattr(original, "diag", None)
    return (
        getattr(original, "sqlstate", None) == "23505"
        and getattr(diagnostic, "constraint_name", None) == "ix_users_username"
    )


def _set_access_token_cookie(
    response: Response, request: Request, user_id: int
) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=create_access_token(user_id),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


@router.post(
    "/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, db: DbSession) -> UserResponse:
    """새 사용자를 저장하고 공개 가능한 식별 정보만 돌려준다."""
    try:
        user = crud.create_user(db, payload.username, hash_password(payload.password))
    except IntegrityError as exc:
        if _is_duplicate_username(exc):
            raise AppError(ErrorCode.DUPLICATE_USERNAME) from exc
        raise

    return UserResponse.model_validate(user)


@router.post("/auth/login", response_model=UserResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> UserResponse:
    """자격 증명을 확인하고 HttpOnly access token 쿠키를 발급한다."""
    user = crud.get_user_by_username(db, payload.username)
    password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, password_hash)
    if user is None or not password_matches:
        raise AppError(ErrorCode.INVALID_CREDENTIALS)

    _set_access_token_cookie(response, request, user.id)
    return UserResponse.model_validate(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, user: CurrentUser) -> Response:
    """현재 브라우저의 access token 쿠키를 만료시킨다."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return response


@router.get("/me", response_model=UserResponse)
def get_me(user: CurrentUser) -> UserResponse:
    """현재 로그인한 사용자의 공개 프로필을 반환한다."""
    return UserResponse.model_validate(user)
