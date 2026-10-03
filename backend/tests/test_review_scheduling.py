from datetime import datetime, timedelta, timezone

import pytest

from app.reviews.scheduling import MIN_EASE_FACTOR, calculate_schedule

REVIEWED_AT = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


def test_first_successful_review_schedules_one_day() -> None:
    schedule = calculate_schedule(4, 0, 2.5, 0, REVIEWED_AT)

    assert schedule.interval_days == 1
    assert schedule.repetitions == 1
    assert schedule.next_review_at == REVIEWED_AT + timedelta(days=1)


def test_second_successful_review_schedules_six_days() -> None:
    schedule = calculate_schedule(5, 1, 2.5, 1, REVIEWED_AT)

    assert schedule.interval_days == 6
    assert schedule.repetitions == 2


def test_later_review_multiplies_interval_by_ease_factor() -> None:
    schedule = calculate_schedule(5, 6, 2.5, 2, REVIEWED_AT)

    assert schedule.interval_days == 16
    assert schedule.repetitions == 3


def test_failed_review_resets_repetitions_and_schedules_one_day() -> None:
    schedule = calculate_schedule(2, 20, 2.5, 4, REVIEWED_AT)

    assert schedule.interval_days == 1
    assert schedule.repetitions == 0
    assert schedule.ease_factor == 2.18


def test_ease_factor_never_drops_below_minimum() -> None:
    schedule = calculate_schedule(0, 1, MIN_EASE_FACTOR, 1, REVIEWED_AT)

    assert schedule.ease_factor == MIN_EASE_FACTOR


@pytest.mark.parametrize(
    ("rating", "interval", "ease", "repetitions"),
    [(-1, 0, 2.5, 0), (6, 0, 2.5, 0), (3, -1, 2.5, 0), (3, 0, 1.2, 0), (3, 0, 2.5, -1)],
)
def test_schedule_rejects_invalid_prior_state(
    rating: int,
    interval: int,
    ease: float,
    repetitions: int,
) -> None:
    with pytest.raises(ValueError):
        calculate_schedule(rating, interval, ease, repetitions, REVIEWED_AT)
