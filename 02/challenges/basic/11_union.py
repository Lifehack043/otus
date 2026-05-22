"""
TODO:

foo should accept either an int or a str.
"""
from typing import Union


def foo(x: Union[int, str]):
    pass


foo(1)
foo("a")
# foo(1.0)
