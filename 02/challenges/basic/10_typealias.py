"""
TODO:

Create a type alias `Config` for a dict with str keys and int/str values.
"""
from typing import Dict, Union

Config = Dict[str, Union[int, str]]


def foo(config: Config) -> None:
    pass


foo({"port": 8080, "host": "localhost"})
