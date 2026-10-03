from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import File as FileRecord
from app.services.files import (
    InvalidUploadError,
    UnsupportedUploadError,
    sanitize_filename,
    validate_upload_content,
)

router = APIRouter()
STORAGE_ROOT = settings.storage_path


def serialize_file(record: FileRecord) -> dict[str, str | int]:
    return {
        "id": str(record.id),
        "filename": record.filename,
        "mime_type": record.mime_type,
        "size": record.size,
        "checksum": record.checksum,
        "status": "uploaded",
    }


def get_file_record(file_id: UUID, db: Session) -> FileRecord:
    record = db.get(FileRecord, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return record


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large.")

    try:
        filename = sanitize_filename(file.filename)
        mime_type = validate_upload_content(filename, content)
    except UnsupportedUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    file_id = uuid4()
    stored_path = STORAGE_ROOT / f"{file_id}{Path(filename).suffix.lower()}"
    temporary_path = stored_path.with_name(f".{stored_path.name}.tmp")
    checksum = sha256(content).hexdigest()

    try:
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        temporary_path.write_bytes(content)
        temporary_path.replace(stored_path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail="Unable to store uploaded file."
        ) from exc

    record = FileRecord(
        id=file_id,
        filename=filename,
        mime_type=mime_type,
        size=len(content),
        storage_path=str(stored_path),
        checksum=checksum,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except SQLAlchemyError as exc:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail="Unable to register uploaded file."
        ) from exc

    return serialize_file(record)


@router.get("/{file_id}")
def get_file(file_id: UUID, db: Session = Depends(get_db)) -> dict[str, str | int]:
    return serialize_file(get_file_record(file_id, db))


@router.get("/{file_id}/preview")
def preview_file(file_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    record = get_file_record(file_id, db)
    if not Path(record.storage_path).is_file():
        raise HTTPException(
            status_code=410, detail="Stored file is no longer available."
        )

    return {
        **serialize_file(record),
        "preview": {
            "format": Path(record.filename).suffix.lower().lstrip("."),
            "size_bytes": record.size,
            "checksum": record.checksum,
        },
    }
