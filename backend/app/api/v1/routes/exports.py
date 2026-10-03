from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.exporters.base import ExportCard, Exporter
from app.exporters.csv_exporter import CsvExporter
from app.exporters.json_exporter import JsonExporter
from app.exporters.xlsx_exporter import XlsxExporter

router = APIRouter()
MAX_EXPORT_CARDS = 10000


class ExportCardInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front: str = Field(min_length=1, max_length=10000)
    back: str = Field(min_length=1, max_length=10000)
    explanation: str | None = Field(default=None, max_length=10000)
    example: str | None = Field(default=None, max_length=10000)
    difficulty: str | None = Field(default=None, max_length=30)
    tags: list[str] = Field(default_factory=list, max_length=100)
    subject: str | None = Field(default=None, max_length=120)
    topic: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=500)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[ExportCardInput] = Field(
        default_factory=list, max_length=MAX_EXPORT_CARDS
    )


def render_export(request: ExportRequest, exporter: Exporter) -> Response:
    cards = [
        ExportCard(
            front=card.front,
            back=card.back,
            explanation=card.explanation,
            example=card.example,
            difficulty=card.difficulty,
            tags=tuple(card.tags),
            subject=card.subject,
            topic=card.topic,
            source=card.source,
        )
        for card in request.cards
    ]
    try:
        content = exporter.export(cards)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Unable to export cards.") from exc

    return Response(
        content=content,
        media_type=exporter.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="flashcards.{exporter.extension}"'
        },
    )


@router.post("/csv", response_class=Response)
def export_csv(request: ExportRequest) -> Response:
    return render_export(request, CsvExporter())


@router.post("/json", response_class=Response)
def export_json(request: ExportRequest) -> Response:
    return render_export(request, JsonExporter())


@router.post("/xlsx", response_class=Response)
def export_xlsx(request: ExportRequest) -> Response:
    return render_export(request, XlsxExporter())
