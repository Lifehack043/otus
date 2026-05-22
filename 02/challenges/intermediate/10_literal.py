"""
TODO:

Use Literal type to restrict `status` to specific values.
"""
from typing import Literal


def set_status(status: Literal["active", "inactive", "pending"]) -> None:
    pass


set_status("active")
# set_status("unknown")
