"""B7-1 코딩 학습 Q&A 챗봇 — 앱 진입점.

Vercel은 이 파일의 `app` 변수를 함수 진입점으로 인식한다.
앱 전체가 단일 함수로 배포되므로 라우터 분할 구조는 그대로 유지된다.
"""

import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Vercel 함수의 작업 디렉터리는 이 파일이 있는 폴더가 아니라 프로젝트 루트다.
# 상대경로("templates")로 쓰면 로컬에서만 되고 배포에서 500이 난다.
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="코딩 학습 Q&A 챗봇")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/spike", response_class=HTMLResponse)
def spike(request: Request):
    """Jinja2 + StaticFiles가 Vercel에서 실제로 동작하는지 확인하는 진단 페이지."""
    return templates.TemplateResponse(
        request=request,
        name="spike.html",
        context={
            "cwd": os.getcwd(),
            "base_dir": str(BASE_DIR),
            "templates_ok": (BASE_DIR / "templates").is_dir(),
            "static_ok": (BASE_DIR / "static").is_dir(),
            "python": sys.version.split()[0],
            "on_vercel": bool(os.environ.get("VERCEL")),
        },
    )
