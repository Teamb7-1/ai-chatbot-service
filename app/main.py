"""B7-1 코딩 학습 Q&A 챗봇 — 앱 진입점.

Vercel은 이 파일의 `app` 변수를 함수 진입점으로 인식하며,
FastAPI 앱 전체가 단일 서버리스 함수로 배포된다.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Vercel 함수의 작업 디렉터리는 이 파일이 있는 폴더가 아니라 프로젝트 루트(/var/task)다.
# 상대경로로 쓰면 /var/task/templates 를 찾다 실패한다.
# 실측 확인: cwd=/var/task, BASE_DIR=/var/task/app
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="코딩 학습 Q&A 챗봇")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/healthz")
def healthz():
    """배포 확인용 헬스체크. CI 스모크 테스트가 이 응답을 검사한다."""
    return {"status": "ok"}
