from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Protocol


EXPORT_FIELDS = (
    "front",
    "back",
    "explanation",
    "example",
    "difficulty",
    "tags",
    "subject",
    "topic",
    "source",
)


@dataclass(frozen=True)
class ExportCard:
    front: str
    back: str
    explanation: str | None = None
    example: str | None = None
    difficulty: str | None = None
    tags: tuple[str, ...] = ()
    subject: str | None = None
    topic: str | None = None
    source: str | None = None

    def to_json_object(self) -> dict[str, object]:
        return asdict(self)

    def to_row(self) -> dict[str, str | None]:
        row = asdict(self)
        row["tags"] = "; ".join(self.tags)
        return row


class Exporter(Protocol):
    media_type: str
    extension: str

    def export(self, data: Sequence[ExportCard]) -> bytes: ...
