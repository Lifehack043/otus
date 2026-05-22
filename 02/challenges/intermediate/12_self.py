"""
TODO:

Use Self type for method that returns the instance.
"""
from typing_extensions import Self


class Counter:
    def __init__(self, value: int = 0) -> None:
        self.value: int = value

    def increment(self) -> Self:
        self.value += 1
        return self

    def reset(self) -> Self:
        self.value = 0
        return self


counter = Counter()
counter.increment().increment().reset()
