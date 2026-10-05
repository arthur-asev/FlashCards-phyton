from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.importers.spreadsheets import (
    SpreadsheetError,
    SpreadsheetTooLargeError,
    SpreadsheetImporter,
    validate_column_mapping,
)
from app.models import Card, Deck, File as FileRecord, ImportJob, Subject, Tag, Topic

router = APIRouter()
spreadsheet_importer = SpreadsheetImporter()


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: UUID
    deck_id: UUID
    mapping: dict[str, str | int] = Field(min_length=2)
    sheet_name: str | None = None


def get_or_create_tag(db: Session, name: str) -> Tag:
    tag = db.scalar(select(Tag).where(func.lower(Tag.name) == name.casefold()))
    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag


def get_or_create_topic(db: Session, subject_id: UUID, name: str) -> Topic:
    topic = db.scalar(
        select(Topic).where(
            Topic.subject_id == subject_id,
            func.lower(Topic.name) == name.casefold(),
        )
    )
    if topic is None:
        topic = Topic(subject_id=subject_id, name=name)
        db.add(topic)
        db.flush()
    return topic


@router.post("", status_code=status.HTTP_201_CREATED)
def import_spreadsheet(
    request: ImportRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    file_record = db.get(FileRecord, request.file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
    deck = db.get(Deck, request.deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    if not Path(file_record.storage_path).is_file():
        raise HTTPException(status_code=410, detail="Stored file is no longer available.")

    try:
        table = spreadsheet_importer.read(file_record.storage_path, request.sheet_name)
    except SpreadsheetTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except SpreadsheetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    validation = validate_column_mapping(table, request.mapping)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail="Spreadsheet must pass validation before import.")

    normalized_rows = validation["normalized_rows"]
    if not isinstance(normalized_rows, list):
        raise HTTPException(status_code=422, detail="Spreadsheet rows could not be normalized.")
    subject_id = deck.subject_id
    if request.mapping.get("topic") and subject_id is None and any(row.get("topic") for row in normalized_rows):
        raise HTTPException(status_code=422, detail="Set a subject on the deck before importing topics.")

    subject_name: str | None = None
    if subject_id is not None:
        subject = db.get(Subject, subject_id)
        subject_name = subject.name if subject else None
    for row in normalized_rows:
        row_subject = row.get("subject", "").strip()
        if row_subject and subject_name and row_subject.casefold() != subject_name.casefold():
            raise HTTPException(
                status_code=422,
                detail="Spreadsheet subject values must match the selected deck subject.",
            )

    started_at = datetime.now(timezone.utc)
    import_job = ImportJob(
        file_id=file_record.id,
        status="PROCESSING",
        total_rows=len(normalized_rows),
        started_at=started_at,
    )
    db.add(import_job)
    db.commit()
    db.refresh(import_job)

    cards: list[Card] = []
    try:
        for row in normalized_rows:
            tags = [
                get_or_create_tag(db, name.strip())
                for name in row.get("tags", "").split(";")
                if name.strip()
            ]
            topic_name = row.get("topic", "").strip()
            topic_id = (
                get_or_create_topic(db, subject_id, topic_name).id
                if topic_name and subject_id is not None
                else None
            )
            cards.append(
                Card(
                    deck_id=deck.id,
                    topic_id=topic_id,
                    front=row["front"],
                    back=row["back"],
                    explanation=row.get("explanation") or None,
                    difficulty=row.get("difficulty") or None,
                    source=row.get("source") or file_record.filename,
                    tags=tags,
                )
            )
        db.add_all(cards)
        db.flush()
        import_job.status = "COMPLETED"
        import_job.processed_rows = len(cards)
        import_job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        failed_job = db.get(ImportJob, import_job.id)
        if failed_job is not None:
            failed_job.status = "FAILED"
            failed_job.failed_rows = len(normalized_rows)
            failed_job.error_message = "Database rejected the imported records."
            failed_job.completed_at = datetime.now(timezone.utc)
            db.commit()
        raise HTTPException(status_code=500, detail="Unable to save imported cards.") from exc

    return {
        "id": str(import_job.id),
        "file_id": str(file_record.id),
        "deck_id": str(deck.id),
        "status": import_job.status,
        "total_rows": import_job.total_rows,
        "processed_rows": import_job.processed_rows,
        "failed_rows": import_job.failed_rows,
    }
