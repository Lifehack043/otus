"""
TODO:

Add type annotation to class variable `count`.
"""
from typing import ClassVar


class Counter:
    count: ClassVar[int] = 0

    def increment(self) -> None:
        Counter.count += 1


c1 = Counter()
c2 = Counter()
c1.increment()
# Counter.count = "zero"
