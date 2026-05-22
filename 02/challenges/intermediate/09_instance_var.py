"""
TODO:

Add type annotations to instance variables.
"""


class User:
    def __init__(self, name: str, age: int) -> None:
        self.name: str = name
        self.age: int = age
        self.is_active: bool = True


user = User("John", 30)
# user.name = 123
