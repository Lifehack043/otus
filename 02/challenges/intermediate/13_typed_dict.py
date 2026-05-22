"""
TODO:

Create a TypedDict for a user with name (str) and age (int).
"""
from typing import TypedDict


class User(TypedDict):
    name: str
    age: int


def greet(user: User) -> str:
    return f"Hello, {user['name']}!"


user: User = {"name": "John", "age": 30}
