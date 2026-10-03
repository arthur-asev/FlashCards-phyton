from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.routes.pagination import paginate
from app.api.v1.schemas import SubjectWrite, TagWrite, TopicWrite
from app.db.session import get_db
from app.models import Card, Deck, Subject, Tag, Topic

router = APIRouter()


def serialize_subject(subject: Subject) -> dict[str, object]:
    return {
        "id": str(subject.id),
        "name": subject.name,
        "description": subject.description,
        "created_at": subject.created_at,
        "updated_at": subject.updated_at,
    }


def serialize_topic(topic: Topic) -> dict[str, object]:
    return {
        "id": str(topic.id),
        "subject_id": str(topic.subject_id),
        "name": topic.name,
        "description": topic.description,
        "created_at": topic.created_at,
        "updated_at": topic.updated_at,
    }


def serialize_tag(tag: Tag) -> dict[str, object]:
    return {"id": str(tag.id), "name": tag.name}


def get_or_404(db: Session, model: type, item_id: UUID, label: str):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found.")
    return item


@router.get("/subjects")
def list_subjects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Subject).order_by(Subject.name)
    if search and search.strip():
        query = query.where(Subject.name.ilike(f"%{search.strip()}%"))
    return paginate(db, query, page, page_size, serialize_subject)


@router.post("/subjects", status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectWrite, db: Session = Depends(get_db)
) -> dict[str, object]:
    subject = Subject(name=payload.name, description=payload.description)
    db.add(subject)
    try:
        db.commit()
        db.refresh(subject)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Subject name already exists."
        ) from exc
    return serialize_subject(subject)


@router.get("/subjects/{subject_id}")
def get_subject(subject_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    return serialize_subject(get_or_404(db, Subject, subject_id, "Subject"))


@router.put("/subjects/{subject_id}")
def update_subject(
    subject_id: UUID,
    payload: SubjectWrite,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    subject = get_or_404(db, Subject, subject_id, "Subject")
    subject.name = payload.name
    subject.description = payload.description
    try:
        db.commit()
        db.refresh(subject)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Subject name already exists."
        ) from exc
    return serialize_subject(subject)


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: UUID, db: Session = Depends(get_db)) -> Response:
    subject = get_or_404(db, Subject, subject_id, "Subject")
    topic_count = db.scalar(
        select(func.count()).select_from(Topic).where(Topic.subject_id == subject_id)
    )
    deck_count = db.scalar(
        select(func.count()).select_from(Deck).where(Deck.subject_id == subject_id)
    )
    if topic_count or deck_count:
        raise HTTPException(
            status_code=409, detail="Subject is still used by topics or decks."
        )
    db.delete(subject)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/topics")
def list_topics(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    subject_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Topic).order_by(Topic.name)
    if search and search.strip():
        query = query.where(Topic.name.ilike(f"%{search.strip()}%"))
    if subject_id is not None:
        query = query.where(Topic.subject_id == subject_id)
    return paginate(db, query, page, page_size, serialize_topic)


@router.post("/topics", status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicWrite, db: Session = Depends(get_db)
) -> dict[str, object]:
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=404, detail="Subject not found.")
    topic = Topic(
        subject_id=payload.subject_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(topic)
    try:
        db.commit()
        db.refresh(topic)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Topic already exists in this subject."
        ) from exc
    return serialize_topic(topic)


@router.get("/topics/{topic_id}")
def get_topic(topic_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    return serialize_topic(get_or_404(db, Topic, topic_id, "Topic"))


@router.put("/topics/{topic_id}")
def update_topic(
    topic_id: UUID,
    payload: TopicWrite,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    topic = get_or_404(db, Topic, topic_id, "Topic")
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=404, detail="Subject not found.")
    topic.subject_id = payload.subject_id
    topic.name = payload.name
    topic.description = payload.description
    try:
        db.commit()
        db.refresh(topic)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Topic already exists in this subject."
        ) from exc
    return serialize_topic(topic)


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: UUID, db: Session = Depends(get_db)) -> Response:
    topic = get_or_404(db, Topic, topic_id, "Topic")
    card_count = db.scalar(
        select(func.count()).select_from(Card).where(Card.topic_id == topic_id)
    )
    if card_count:
        raise HTTPException(status_code=409, detail="Topic is still used by cards.")
    db.delete(topic)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tags")
def list_tags(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Tag).order_by(Tag.name)
    if search and search.strip():
        query = query.where(Tag.name.ilike(f"%{search.strip()}%"))
    return paginate(db, query, page, page_size, serialize_tag)


@router.post("/tags", status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagWrite, db: Session = Depends(get_db)) -> dict[str, object]:
    tag = Tag(name=payload.name)
    db.add(tag)
    try:
        db.commit()
        db.refresh(tag)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tag name already exists.") from exc
    return serialize_tag(tag)


@router.get("/tags/{tag_id}")
def get_tag(tag_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    return serialize_tag(get_or_404(db, Tag, tag_id, "Tag"))


@router.put("/tags/{tag_id}")
def update_tag(
    tag_id: UUID,
    payload: TagWrite,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    tag = get_or_404(db, Tag, tag_id, "Tag")
    tag.name = payload.name
    try:
        db.commit()
        db.refresh(tag)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tag name already exists.") from exc
    return serialize_tag(tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: UUID, db: Session = Depends(get_db)) -> Response:
    tag = get_or_404(db, Tag, tag_id, "Tag")
    db.delete(tag)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
