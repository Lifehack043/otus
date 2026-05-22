"""
TODO:

Make `first_element` return the first element of a list with proper typing.
"""
from typing import TypeVar, List

T = TypeVar("T")


def first_element(lst: List[T]) -> T | None:
    if lst:
        return lst[0]
    return None


result = first_element([1, 2, 3])  # int | None
result2 = first_element(["a", "b"])  # str | None
result3 = first_element([])  # None
