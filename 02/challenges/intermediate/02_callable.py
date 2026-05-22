"""
TODO:

Make `apply` accept a callable that takes two ints and returns an int.
"""
from typing import Callable


def apply(func: Callable[[int, int], int], x: int, y: int) -> int:
    return func(x, y)


def add(a: int, b: int) -> int:
    return a + b


result = apply(add, 1, 2)
# result: int
