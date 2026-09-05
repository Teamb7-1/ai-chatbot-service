"""pytest 전역 설정.

database.py(#70)는 import 시점에 DATABASE_URL 을 요구한다 — fail-fast 설계다.
그 파일을 직·간접으로 import 하는 테스트 모듈이 하나라도 생기면, 값이 없을 때
수집 단계에서 통째로 죽는다. 여기서 더미를 깔아 import 는 통과하게 한다.

create_engine() 은 첫 connect() 까지 실제로 연결하지 않으므로 더미 URL 은 안전하다.
실제 DB 가 필요한 테스트는 스스로 monkeypatch 하거나 skip 한다.

setdefault 라서 진짜 값이 이미 있으면 건드리지 않는다. 그리고 C 의
test_DATABASE_URL이_없으면_… 는 서브프로세스에서 environ.pop 하므로 영향 없다.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
