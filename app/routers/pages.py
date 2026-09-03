"""화면 라우터 — 템플릿을 렌더링하는 곳은 여기 하나다.

인증(#23 A)과 로그 조회(#36 C)가 아직 없다. 두 자리는 도착하면 한 줄씩
붙일 수 있게 열어뒀고, 그때까지 화면은 "없는 척"이 아니라 "아직 연결 안 됨"
으로 보이게 한다. 빈 목록을 넘겨 "기록이 없습니다"라고 말하면 그건 거짓말이다
— 기록이 없는 것과 읽을 방법이 없는 것은 다르다.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 화면 라우트는 OpenAPI 문서에 넣지 않는다. /docs 는 B·C 가 계약을 보는 곳이라
# HTML 라우트가 섞이면 읽어야 할 것이 묻힌다.
router = APIRouter(tags=["pages"], include_in_schema=False)


@router.get("/")
def index() -> RedirectResponse:
    """진입점.

    로그인 여부에 따라 갈라야 하지만, 그 판단은 인증 의존성 한 곳(deps.py)이
    갖는다 — 평가항목 20. 여기서 쿠키를 읽지 않는다. /chat 에 의존성이 붙으면
    미인증 요청은 그쪽에서 401 로 올라가고, main.py 의 핸들러가 /login 으로
    돌린다.
    """
    return RedirectResponse("/chat", status_code=302)


@router.get("/chat")
def chat_page(request: Request):
    """질문 화면.

    #23 도착 후: def chat_page(request: Request, user: CurrentUser)
    """
    return templates.TemplateResponse(request, "chat.html")


@router.get("/logs")
def logs_page(request: Request):
    """지난 대화 화면.

    #36 도착 후: items = crud.list_chat_logs(db, user.id) 한 줄로 바뀌고
    pending 은 사라진다.
    """
    return templates.TemplateResponse(
        request, "logs.html", {"items": [], "pending": True}
    )
