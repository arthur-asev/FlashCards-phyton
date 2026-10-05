from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.api.v1.routes.cards import serialize_card
from app.db.session import get_db
from app.models import Card, Review
from app.reviews.scheduling import calculate_schedule

router = APIRouter()


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=0, le=5)


def serialize_review(review: Review, card: Card | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "id": str(review.id),
        "card_id": str(review.card_id),
        "rating": review.rating,
        "interval": review.interval,
        "ease": review.ease,
        "repetitions": review.repetitions,
        "reviewed_at": review.reviewed_at,
        "next_review_at": review.next_review_at,
    }
    if card is not None:
        result["card"] = {"id": str(card.id), "front": card.front, "back": card.back}
    return result


def due_cards_query(
    now: datetime, deck_id: UUID | None = None, topic_ids: list[UUID] | None = None
):
    latest_review_id = (
        select(Review.id)
        .where(Review.card_id == Card.id, Review.user_id.is_(None))
        .order_by(Review.reviewed_at.desc(), Review.id.desc())
        .limit(1)
        .correlate(Card)
        .scalar_subquery()
    )
    latest_review = aliased(Review)
    query = (
        select(Card, latest_review.next_review_at)
        .outerjoin(latest_review, latest_review.id == latest_review_id)
        .where(
            or_(
                latest_review.id.is_(None),
                latest_review.next_review_at.is_(None),
                latest_review.next_review_at <= now,
            )
        )
        .options(selectinload(Card.tags))
    )
    if deck_id is not None:
        query = query.where(Card.deck_id == deck_id)
    if topic_ids:
        query = query.where(Card.topic_id.in_(topic_ids))
    return query


@router.post("/cards/{card_id}/review", status_code=status.HTTP_201_CREATED)
def create_review(
    card_id: UUID,
    payload: ReviewInput,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")

    previous_review = db.scalar(
        select(Review)
        .where(Review.card_id == card_id, Review.user_id.is_(None))
        .order_by(Review.reviewed_at.desc(), Review.id.desc())
        .limit(1)
    )
    reviewed_at = datetime.now(timezone.utc)
    schedule = calculate_schedule(
        rating=payload.rating,
        previous_interval_days=previous_review.interval if previous_review else 0,
        previous_ease_factor=previous_review.ease if previous_review else 2.5,
        previous_repetitions=previous_review.repetitions if previous_review else 0,
        reviewed_at=reviewed_at,
    )
    review = Review(
        card_id=card_id,
        rating=payload.rating,
        interval=schedule.interval_days,
        ease=schedule.ease_factor,
        repetitions=schedule.repetitions,
        reviewed_at=reviewed_at,
        next_review_at=schedule.next_review_at,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return serialize_review(review, card)


@router.get("/reviews/due")
def list_due_cards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    deck_id: UUID | None = None,
    topic_ids: list[UUID] = Query(default=[]),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = due_cards_query(datetime.now(timezone.utc), deck_id, topic_ids).order_by(
        Card.created_at, Card.id
    )
    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    items = []
    for card, next_review_at in rows:
        items.append(
            {
                **serialize_card(card),
                "next_review_at": next_review_at,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/reviews/history")
def list_review_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    card_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = (
        select(Review, Card)
        .join(Card, Review.card_id == Card.id)
        .where(Review.user_id.is_(None))
        .order_by(Review.reviewed_at.desc(), Review.id.desc())
    )
    if card_id is not None:
        query = query.where(Review.card_id == card_id)
    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [serialize_review(review, card) for review, card in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/reviews/stats")
def review_stats(db: Session = Depends(get_db)) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    total_cards = db.scalar(select(func.count()).select_from(Card)) or 0
    total_reviews = (
        db.scalar(
            select(func.count()).select_from(Review).where(Review.user_id.is_(None))
        )
        or 0
    )
    reviewed_cards = (
        db.scalar(
            select(func.count(func.distinct(Review.card_id))).where(
                Review.user_id.is_(None)
            )
        )
        or 0
    )
    due_count = (
        db.scalar(
            select(func.count()).select_from(
                due_cards_query(now).order_by(None).subquery()
            )
        )
        or 0
    )
    return {
        "total_cards": total_cards,
        "reviewed_cards": reviewed_cards,
        "pending_cards": total_cards - reviewed_cards,
        "due_cards": due_count,
        "total_reviews": total_reviews,
    }
