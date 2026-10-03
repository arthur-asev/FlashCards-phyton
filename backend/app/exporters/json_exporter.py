import json
from collections.abc import Sequence

from app.exporters.base import ExportCard


class JsonExporter:
    media_type = "application/json"
    extension = "json"

    def export(self, data: Sequence[ExportCard]) -> bytes:
        payload = [card.to_json_object() for card in data]
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
