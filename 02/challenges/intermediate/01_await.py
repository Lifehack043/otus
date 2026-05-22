"""
TODO:

Make `run_async` accept an Awaitable[int].
"""

from collections.abc import Awaitable
from asyncio import Queue


queue: Queue[int] = Queue()
queue2: Queue[str] = Queue()


async def async_function() -> int:
    return await queue.get()


async def async_function2() -> str:
    return await queue2.get()


def run_async(func: Awaitable[int]):
    ...


run_async(async_function())
# run_async(1)
# run_async(async_function2())
