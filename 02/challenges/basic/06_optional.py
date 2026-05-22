"""
TODO:

foo can accept an integer argument, None or no argument at all.
"""


def foo(x: int | None = 0):
    pass


foo(10)
foo(None)
foo(0)

# foo("10")
