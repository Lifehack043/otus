"""
TODO:

Create a TypedDict that extends another TypedDict.
"""
from typing import TypedDict


class Person(TypedDict):
    name: str
    age: int


class Employee(Person):
    employee_id: int
    department: str


def process_employee(emp: Employee) -> None:
    print(f"{emp['name']} (ID: {emp['employee_id']})")


emp: Employee = {
    "name": "John",
    "age": 30,
    "employee_id": 123,
    "department": "Engineering"
}
