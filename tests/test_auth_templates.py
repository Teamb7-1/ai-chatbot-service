from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import TEMPLATES_DIR


def render(template_name: str) -> str:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return environment.get_template(template_name).render()


def test_로그인_화면은_JSON_API를_호출하고_채팅으로_이동한다():
    html = render("login.html")

    assert 'id="login-form"' in html
    assert 'autocomplete="username"' in html
    assert 'autocomplete="current-password"' in html
    assert 'fetch("/api/auth/login"' in html
    assert '"Content-Type": "application/json"' in html
    assert 'window.location.href = "/chat"' in html


def test_회원가입_화면은_스키마와_같은_입력_제약을_갖는다():
    html = render("register.html")

    assert 'id="register-form"' in html
    assert 'minlength="3"' in html
    assert 'maxlength="20"' in html
    assert 'minlength="8"' in html
    assert 'autocomplete="new-password"' in html
    assert 'fetch("/api/auth/register"' in html
    assert 'window.location.href = "/login"' in html


def test_인증_화면은_서버_오류를_textContent로_표시한다():
    for template_name in ("login.html", "register.html"):
        html = render(template_name)

        assert "notice.textContent = result.data.message" in html
        assert "notice.innerHTML" not in html
