from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile


class UnsupportedUploadError(ValueError):
    """Raised when the uploaded filename uses an unsupported extension."""


class InvalidUploadError(ValueError):
    """Raised when uploaded content does not match its supported format."""


SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
XLS_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


def sanitize_filename(filename: str | None) -> str:
    safe_name = PurePosixPath((filename or "").replace("\\", "/")).name
    if not safe_name or safe_name in {".", ".."}:
        raise InvalidUploadError("A filename is required.")
    if len(safe_name) > 255:
        raise InvalidUploadError("Filename is too long.")
    if PurePosixPath(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedUploadError("Unsupported file type.")
    return safe_name


def validate_upload_content(filename: str, content: bytes) -> str:
    extension = PurePosixPath(filename).suffix.lower()
    if not content:
        raise InvalidUploadError("Uploaded file is empty.")

    if extension == ".csv":
        try:
            text_content = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidUploadError("CSV files must use UTF-8 encoding.") from exc
        if not text_content.strip() or "\x00" in text_content:
            raise InvalidUploadError("CSV content is empty or invalid.")
        return "text/csv"

    if extension == ".xls":
        if not content.startswith(XLS_SIGNATURE):
            raise InvalidUploadError("File content does not match the XLS format.")
        return "application/vnd.ms-excel"

    if extension != ".xlsx":
        raise UnsupportedUploadError("Unsupported file type.")

    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                raise InvalidUploadError("File content does not match the ODS format.")
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    except BadZipFile as exc:
        raise InvalidUploadError(
            "File content is not a valid spreadsheet archive."
        ) from exc
