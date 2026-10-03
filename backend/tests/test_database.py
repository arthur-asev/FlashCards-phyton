from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db import seed
from app.models import Card, Deck, Subject, Tag, User


def create_test_session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_domain_models_create_and_link_records() -> None:
    session_factory = create_test_session_factory()

    with session_factory() as session:
        subject = Subject(name="Biologia")
        user = User(email="learner@example.test", password_hash="hashed", name="Learner")
        session.add_all([subject, user])
        session.flush()
        deck = Deck(name="Cellular biology", subject_id=subject.id, user_id=user.id)
        session.add(deck)
        session.flush()
        card = Card(deck_id=deck.id, front="Front", back="Back")
        card.tags.append(Tag(name="cells"))
        session.add(card)
        session.commit()

        saved_card = session.scalar(select(Card).where(Card.front == "Front"))
        assert saved_card is not None
        assert [tag.name for tag in saved_card.tags] == ["cells"]
        assert saved_card.deck_id == deck.id


def test_user_email_must_be_unique() -> None:
    session_factory = create_test_session_factory()

    with session_factory() as session:
        session.add_all(
            [
                User(email="same@example.test", password_hash="one", name="One"),
                User(email="same@example.test", password_hash="two", name="Two"),
            ]
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Duplicate user email was accepted")


def test_development_seed_is_idempotent(monkeypatch) -> None:
    session_factory = create_test_session_factory()
    monkeypatch.setattr(seed, "SessionLocal", session_factory)

    seed.seed_development_data()
    seed.seed_development_data()

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Subject)) == 1
        assert session.scalar(select(func.count()).select_from(Deck)) == 1
        assert session.scalar(select(func.count()).select_from(Card)) == 1