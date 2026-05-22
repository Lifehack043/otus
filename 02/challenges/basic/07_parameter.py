"""
TODO:

Make `name` a keyword-only argument.
"""


def foo(name: str, *, age: int):
    pass


foo("John", age=25)
# foo("John", 25)
