from typing import Protocol, Any


class Exporter(Protocol):
    def export(self, data: Any, destination: str) -> str:
        ...
