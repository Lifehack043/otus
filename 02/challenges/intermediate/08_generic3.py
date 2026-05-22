"""
TODO:

Make `Storage` a generic class.
"""
from typing import TypeVar, Generic, List

T = TypeVar("T")


class Storage(Generic[T]):
    def __init__(self) -> None:
        self.items: List[T] = []

    def add(self, item: T) -> None:
        self.items.append(item)

    def get(self, index: int) -> T:
        return self.items[index]


int_storage = Storage[int]()
int_storage.add(1)
str_storage = Storage[str]()
str_storage.add("hello")
