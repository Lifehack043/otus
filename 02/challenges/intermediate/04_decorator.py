"""
TODO:

Annotate the decorator properly.
"""
from typing import Callable, TypeVar, Any, cast
from functools import wraps

T = TypeVar("T", bound=Callable[..., Any])


def my_decorator(func: T) -> T:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    return cast(T, wrapper)


@my_decorator
def greet(name: str) -> str:
    return f"Hello, {name}!"
