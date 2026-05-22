"""
TODO:

Use Unpack to unpack a TypedDict as function arguments.
"""
from typing import TypedDict
from typing_extensions import Unpack


class Point(TypedDict):
    x: int
    y: int


def draw_point(**kwargs: Unpack[Point]) -> None:
    print(f"Drawing point at ({kwargs['x']}, {kwargs['y']})")


point: Point = {"x": 10, "y": 20}
draw_point(**point)
