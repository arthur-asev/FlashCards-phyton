from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Card, Deck, Subject, Topic


def seed_development_data() -> None:
    with SessionLocal() as session:
        subject = session.scalar(select(Subject).where(Subject.name == "Biologia"))
        if subject is None:
            subject = Subject(name="Biologia", description="Dados de desenvolvimento")
            session.add(subject)
            session.flush()

        topic = session.scalar(
            select(Topic).where(
                Topic.subject_id == subject.id,
                Topic.name == "Biologia celular",
            )
        )
        if topic is None:
            session.add(Topic(subject_id=subject.id, name="Biologia celular"))

        deck = session.scalar(
            select(Deck).where(
                Deck.subject_id == subject.id,
                Deck.name == "Baralho de exemplo",
            )
        )
        if deck is None:
            deck = Deck(subject_id=subject.id, name="Baralho de exemplo")
            session.add(deck)
            session.flush()

        card = session.scalar(
            select(Card).where(
                Card.deck_id == deck.id,
                Card.front == "Qual é a função da membrana plasmática?",
            )
        )
        if card is None:
            session.add(
                Card(
                    deck_id=deck.id,
                    front="Qual é a função da membrana plasmática?",
                    back="Delimitar a célula e regular a troca de substâncias com o meio.",
                )
            )

        session.commit()


if __name__ == "__main__":
    seed_development_data()