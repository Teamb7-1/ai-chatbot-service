"""화면 라우터 — 세 화면이 실제로 렌더링되는지 검증.

이 파일이 생기기 전까지 앱은 /healthz 말고 전부 404 였다.
템플릿과 디자인 시스템은 다 있는데 서빙하는 라우트가 없었고,
배포는 계속 초록불이었다.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import STATIC_DIR, TEMPLATES_DIR
from app.main import app


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_루트는_채팅으로_보낸다(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["location"] == "/chat"


def test_채팅_화면이_뜬다(client):
    response = client.get("/chat")

    assert response.status_code == 200
    # 입력창과 스크립트가 함께 와야 화면이 동작한다.
    assert '<textarea id="message"' in response.text
    assert 'src="/static/chat.js"' in response.text


def test_로그_화면이_뜬다(client):
    response = client.get("/logs")

    assert response.status_code == 200


def test_데이터_계층_대기를_기록_없음으로_속이지_않는다(client):
    """crud(#36) 가 없는 상태와 기록이 0건인 상태는 다른 화면이어야 한다.

    빈 배열을 넘겨 "아직 기록이 없습니다" 로 보이게 하면, C 의 데이터 계층이
    안 붙은 것을 아무도 눈치채지 못한다. 초록불인데 작동하지 않는 상태다.
    """
    response = client.get("/logs")

    assert "데이터 계층이 아직 연결되지 않았습니다" in response.text
    assert "아직 기록이 없습니다" not in response.text


def test_정적_파일이_서빙된다(client):
    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert "--muted" in response.text


def test_화면_라우트는_API_문서에_없다(client):
    """/docs 는 B·C 가 계약을 보는 곳이다. HTML 라우트가 섞이면 묻힌다."""
    paths = client.get("/openapi.json").json()["paths"]

    assert "/chat" not in paths
    assert "/logs" not in paths


def test_경로_상수가_절대경로다():
    """Vercel 함수의 cwd 는 프로젝트 루트(/var/task)이고 앱은 그 아래 app/ 이다.

    상대경로로 쓰면 /var/task/templates 를 찾다 실패한다.  → 배포에서만 깨진다.
    """
    assert TEMPLATES_DIR.is_absolute()
    assert STATIC_DIR.is_absolute()


def test_작업_디렉터리가_달라도_렌더링된다(client, tmp_path):
    """cwd 를 옮겨 Vercel 의 경로 불일치를 로컬에서 재현한다.

    이 테스트가 없으면 상대경로 회귀가 CI 를 통과하고 배포에서만 터진다.
    """
    original = Path.cwd()
    os.chdir(tmp_path)
    try:
        assert client.get("/chat").status_code == 200
        assert client.get("/logs").status_code == 200
    finally:
        os.chdir(original)
