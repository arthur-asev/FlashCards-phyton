from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_EASE_FACTOR = 1.3


@dataclass(frozen=True)
class ReviewSchedule:
    interval_days: int
    ease_factor: float
    repetitions: int
    next_review_at: datetime


def calculate_schedule(
    rating: int,
    previous_interval_days: int,
    previous_ease_factor: float,
    previous_repetitions: int,
    reviewed_at: datetime,
) -> ReviewSchedule:
    if not 0 <= rating <= 5:
        raise ValueError("Rating must be between 0 and 5.")
    if previous_interval_days < 0 or previous_repetitions < 0:
        raise ValueError("Previous interval and repetitions cannot be negative.")
    if previous_ease_factor < MIN_EASE_FACTOR:
        raise ValueError(f"Ease factor cannot be lower than {MIN_EASE_FACTOR}.")

    quality_delta = 5 - rating
    ease_factor = max(
        MIN_EASE_FACTOR,
        previous_ease_factor + (0.1 - quality_delta * (0.08 + quality_delta * 0.02)),
    )

    if rating < 3:
        interval_days = 1
        repetitions = 0
    else:
        if previous_repetitions == 0:
            interval_days = 1
        elif previous_repetitions == 1:
            interval_days = 6
        else:
            interval_days = max(1, round(previous_interval_days * ease_factor))
        repetitions = previous_repetitions + 1

    return ReviewSchedule(
        interval_days=interval_days,
        ease_factor=round(ease_factor, 2),
        repetitions=repetitions,
        next_review_at=reviewed_at + timedelta(days=interval_days),
    )
