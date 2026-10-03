from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


def paginate(
    db: Session,
    query: Select,
    page: int,
    page_size: int,
    serialize: Callable[[Any], dict[str, object]],
) -> dict[str, object]:
    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [serialize(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
