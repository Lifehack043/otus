"""
TODO:

Make `identity` a generic function that preserves the type.
"""
from typing import TypeVar

T = TypeVar("T")


def identity(x: T) -> T:
    return x


result = identity(42)  # int
result2 = identity("hello")  # str
