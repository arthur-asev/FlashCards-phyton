from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.v1.routes.pagination import paginate
from app.api.v1.schemas import CardWrite
from app.db.session import get_db
from app.models import Card, Deck, Tag, Topic

router = APIRouter()


def serialize_card(card: Card) -> dict[str, object]:
    return {
        "id": str(card.id),
        "deck_id": str(card.deck_id),
        "topic_id": str(card.topic_id) if card.topic_id else None,
        "front": card.front,
        "back": card.back,
        "explanation": card.explanation,
        "example": card.example,
        "difficulty": card.difficulty,
        "source": card.source,
        "tags": sorted((tag.name for tag in card.tags), key=str.casefold),
        "created_at": card.created_at,
        "updated_at": card.updated_at,
    }


def get_card_or_404(db: Session, card_id: UUID) -> Card:
    card = db.scalar(
        select(Card).options(selectinload(Card.tags)).where(Card.id == card_id)
    )
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    return card


def get_tags(db: Session, names: list[str]) -> list[Tag]:
    tags: list[Tag] = []
    for name in names:
        tag = db.scalar(select(Tag).where(func.lower(Tag.name) == name.casefold()))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def validate_card_references(db: Session, payload: CardWrite) -> None:
    deck = db.get(Deck, payload.deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    if payload.topic_id is None:
        return
    topic = db.get(Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    if deck.subject_id is not None and deck.subject_id != topic.subject_id:
        raise HTTPException(
            status_code=422,
            detail="Card topic must belong to the deck subject.",
        )


def apply_card_payload(db: Session, card: Card, payload: CardWrite) -> None:
    validate_card_references(db, payload)
    card.deck_id = payload.deck_id
    card.topic_id = payload.topic_id
    card.front = payload.front
    card.back = payload.back
    card.explanation = payload.explanation
    card.example = payload.example
    card.difficulty = payload.difficulty
    card.source = payload.source
    card.tags = get_tags(db, payload.tags)


@router.get("")
def list_cards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    deck_id: UUID | None = None,
    subject_id: UUID | None = None,
    topic_id: UUID | None = None,
    tag: str | None = None,
    difficulty: str | None = None,
    sort_by: Literal["created_at", "updated_at", "front"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Card)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Card.front.ilike(pattern),
                Card.back.ilike(pattern),
                Card.explanation.ilike(pattern),
            )
        )
    if deck_id is not None:
        query = query.where(Card.deck_id == deck_id)
    if topic_id is not None:
        query = query.where(Card.topic_id == topic_id)
    if subject_id is not None:
        query = query.join(Deck, Card.deck_id == Deck.id).where(
            Deck.subject_id == subject_id
        )
    if tag and tag.strip():
        query = query.where(
            Card.tags.any(func.lower(Tag.name) == tag.strip().casefold())
        )
    if difficulty and difficulty.strip():
        query = query.where(Card.difficulty.ilike(difficulty.strip()))

    sort_column = {
        "created_at": Card.created_at,
        "updated_at": Card.updated_at,
        "front": Card.front,
    }[sort_by]
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    query = query.options(selectinload(Card.tags)).order_by(ordering, Card.id)
    return paginate(db, query, page, page_size, serialize_card)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_card(payload: CardWrite, db: Session = Depends(get_db)) -> dict[str, object]:
    card = Card()
    apply_card_payload(db, card, payload)
    db.add(card)
    try:
        db.commit()
        db.refresh(card)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Card references could not be saved."
        ) from exc
    return serialize_card(get_card_or_404(db, card.id))


@router.get("/{card_id}")
def get_card(card_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    return serialize_card(get_card_or_404(db, card_id))


@router.put("/{card_id}")
def update_card(
    card_id: UUID,
    payload: CardWrite,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    card = get_card_or_404(db, card_id)
    apply_card_payload(db, card, payload)
    try:
        db.commit()
        db.refresh(card)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Card references could not be saved."
        ) from exc
    return serialize_card(get_card_or_404(db, card.id))


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: UUID, db: Session = Depends(get_db)) -> Response:
    card = get_card_or_404(db, card_id)
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
