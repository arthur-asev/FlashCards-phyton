import csv
from collections.abc import Sequence
from io import StringIO

from app.exporters.base import EXPORT_FIELDS, ExportCard


class CsvExporter:
    media_type = "text/csv; charset=utf-8"
    extension = "csv"

    def export(self, data: Sequence[ExportCard]) -> bytes:
        output = StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(card.to_row() for card in data)
        return output.getvalue().encode("utf-8")
