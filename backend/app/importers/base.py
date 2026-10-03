from typing import Protocol, TypeVar

T = TypeVar("T")


class Importer(Protocol[T]):
    def read(self, path: str) -> T: ...
