"""화면 라우터 — 템플릿을 렌더링하는 곳은 여기 하나다.

인증은 deps.py 의 CurrentUser 한 곳이 판단한다 (#23). 쿠키가 없거나 깨지면
거기서 NOT_AUTHENTICATED 가 올라오고, main.py 의 핸들러가 화면 요청이면
/login 으로 돌린다. 여기서 쿠키를 읽지 않는다.  → 평가항목 20

로그 조회(#36 C)는 아직 없다. 그때까지 화면은 "없는 척"이 아니라 "아직 연결 안 됨"
으로 보이게 한다. 빈 목록을 넘겨 "기록이 없습니다"라고 말하면 그건 거짓말이다
— 기록이 없는 것과 읽을 방법이 없는 것은 다르다.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.deps import CurrentUser

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 화면 라우트는 OpenAPI 문서에 넣지 않는다. /docs 는 B·C 가 계약을 보는 곳이라
# HTML 라우트가 섞이면 읽어야 할 것이 묻힌다.
router = APIRouter(tags=["pages"], include_in_schema=False)


@router.get("/")
def index() -> RedirectResponse:
    """진입점. 미인증이면 /chat 이 다시 /login 으로 보낸다 — 판단은 한 곳에서."""
    return RedirectResponse("/chat", status_code=302)


@router.get("/login")
def login_page(request: Request):
    """로그인 화면. 템플릿(#73, A)이 제출 대상 API 를 자기 안에서 정한다."""
    return templates.TemplateResponse(request, "login.html")


@router.get("/register")
def register_page(request: Request):
    """회원가입 화면."""
    return templates.TemplateResponse(request, "register.html")


@router.get("/chat")
def chat_page(request: Request, user: CurrentUser):
    """질문 화면. 로그인한 사용자만."""
    return templates.TemplateResponse(request, "chat.html", {"user": user})


@router.get("/logs")
def logs_page(request: Request, user: CurrentUser):
    """지난 대화 화면.

    #36 도착 후: items = crud.list_chat_logs(db, user.id) 한 줄로 바뀌고
    pending 은 사라진다.
    """
    return templates.TemplateResponse(
        request, "logs.html", {"user": user, "items": [], "pending": True}
    )
