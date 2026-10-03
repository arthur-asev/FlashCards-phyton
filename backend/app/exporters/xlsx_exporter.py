from collections.abc import Sequence
from io import BytesIO

from openpyxl import Workbook

from app.exporters.base import EXPORT_FIELDS, ExportCard


class XlsxExporter:
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    extension = "xlsx"

    def export(self, data: Sequence[ExportCard]) -> bytes:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Flashcards"
        worksheet.append(EXPORT_FIELDS)
        for card in data:
            worksheet.append([card.to_row()[field] for field in EXPORT_FIELDS])

        output = BytesIO()
        workbook.save(output)
        workbook.close()
        return output.getvalue()
