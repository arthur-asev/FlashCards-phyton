from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.v1.routes.pagination import paginate
from app.api.v1.schemas import DeckWrite
from app.db.session import get_db
from app.models import Deck, Subject

router = APIRouter()


def serialize_deck(deck: Deck) -> dict[str, object]:
    return {
        "id": str(deck.id),
        "name": deck.name,
        "description": deck.description,
        "subject_id": str(deck.subject_id) if deck.subject_id else None,
        "created_at": deck.created_at,
        "updated_at": deck.updated_at,
    }


def get_deck_or_404(db: Session, deck_id: UUID) -> Deck:
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return deck


def validate_subject(db: Session, subject_id: UUID | None) -> None:
    if subject_id is not None and db.get(Subject, subject_id) is None:
        raise HTTPException(status_code=404, detail="Subject not found.")


@router.get("")
def list_decks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    subject_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Deck).order_by(Deck.name)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(Deck.name.ilike(pattern), Deck.description.ilike(pattern))
        )
    if subject_id is not None:
        query = query.where(Deck.subject_id == subject_id)
    return paginate(db, query, page, page_size, serialize_deck)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_deck(payload: DeckWrite, db: Session = Depends(get_db)) -> dict[str, object]:
    validate_subject(db, payload.subject_id)
    deck = Deck(
        name=payload.name,
        description=payload.description,
        subject_id=payload.subject_id,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return serialize_deck(deck)


@router.get("/{deck_id}")
def get_deck(deck_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    return serialize_deck(get_deck_or_404(db, deck_id))


@router.put("/{deck_id}")
def update_deck(
    deck_id: UUID,
    payload: DeckWrite,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    deck = get_deck_or_404(db, deck_id)
    validate_subject(db, payload.subject_id)
    deck.name = payload.name
    deck.description = payload.description
    deck.subject_id = payload.subject_id
    db.commit()
    db.refresh(deck)
    return serialize_deck(deck)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: UUID, db: Session = Depends(get_db)) -> Response:
    deck = get_deck_or_404(db, deck_id)
    db.delete(deck)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
