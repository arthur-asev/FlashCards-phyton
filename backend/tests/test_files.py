from hashlib import sha256
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import files as file_routes
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(file_routes, "STORAGE_ROOT", tmp_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_upload_persists_csv_and_exposes_metadata_preview(
    client: TestClient,
    tmp_path,
) -> None:
    content = b"front,back\nQuestion,Answer\n"
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("../../cards.csv", content, "text/csv")},
    )

    assert response.status_code == 201
    uploaded = response.json()
    assert uploaded["filename"] == "cards.csv"
    assert uploaded["mime_type"] == "text/csv"
    assert uploaded["size"] == len(content)
    assert uploaded["checksum"] == sha256(content).hexdigest()

    stored_files = list(tmp_path.glob("*.csv"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == content

    metadata = client.get(f"/api/v1/files/{uploaded['id']}")
    preview = client.get(f"/api/v1/files/{uploaded['id']}/preview")
    assert metadata.status_code == 200
    assert metadata.json() == uploaded
    assert preview.status_code == 200
    preview_metadata = preview.json()["preview"]
    assert preview_metadata["format"] == "csv"
    assert preview_metadata["size_bytes"] == len(content)
    assert preview_metadata["checksum"] == uploaded["checksum"]


def test_upload_accepts_valid_xlsx(client: TestClient) -> None:
    workbook = Workbook()
    workbook.active.append(["front", "back"])
    workbook.active.append(["Question", "Answer"])
    content_buffer = BytesIO()
    workbook.save(content_buffer)

    response = client.post(
        "/api/v1/files/upload",
        files={
            "file": (
                "cards.xlsx",
                content_buffer.getvalue(),
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["mime_type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@pytest.mark.parametrize(
    ("filename", "content", "expected_status"),
    [
        ("script.exe", b"payload", 400),
        ("cards.ods", b"not supported", 400),
        ("fake.xlsx", b"not a zip archive", 422),
        ("invalid.csv", b"\xff\xfe", 422),
        ("empty.csv", b"", 422),
    ],
)
def test_upload_rejects_unsupported_or_invalid_content(
    client: TestClient,
    filename: str,
    content: bytes,
    expected_status: int,
) -> None:
    response = client.post(
        "/api/v1/files/upload",
        files={"file": (filename, content, "application/octet-stream")},
    )

    assert response.status_code == expected_status


def test_upload_enforces_configured_size_limit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)

    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("cards.csv", b"a", "text/csv")},
    )

    assert response.status_code == 413


def test_file_preview_returns_not_found_for_unknown_id(client: TestClient) -> None:
    response = client.get("/api/v1/files/00000000-0000-0000-0000-000000000000/preview")

    assert response.status_code == 404
