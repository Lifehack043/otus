"""
TODO:

Create a TypedDict with optional fields.
"""
from typing import TypedDict
from typing_extensions import NotRequired


class Config(TypedDict, total=False):
    host: str
    port: int
    debug: NotRequired[bool]


def connect(config: Config) -> None:
    host = config.get("host", "localhost")
    port = config.get("port", 8080)
    print(f"Connecting to {host}:{port}")


connect({"host": "example.com", "port": 3000})
