from typing import Protocol, Any


class Importer(Protocol):
    def read(self, path: str) -> Any:
        ...
