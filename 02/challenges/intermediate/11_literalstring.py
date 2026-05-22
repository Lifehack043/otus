"""
TODO:

Use LiteralString for a function that accepts string literals.
"""
from typing_extensions import LiteralString


def log(message: LiteralString) -> None:
    print(message)


log("Hello")
log("Error: something went wrong")
# log(123)
