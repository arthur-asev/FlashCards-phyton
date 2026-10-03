import app.main as main
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

client = TestClient(main.app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "check_dependencies", lambda: None)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.parametrize(
    "dependency_error",
    [SQLAlchemyError("database unavailable"), RedisError("redis unavailable")],
)
def test_ready_returns_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    dependency_error: Exception,
) -> None:
    def fail_check() -> None:
        raise dependency_error

    monkeypatch.setattr(main, "check_dependencies", fail_check)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Application dependencies are not ready"}
