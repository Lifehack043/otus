from __future__ import annotations

from typing import Optional, List

from booking.domain.model import Reservation, TimeSlot, Table, TableId, TableCapacity, TimeSlot as TableTimeSlot
from booking.domain.repository import ReservationRepository, TableRepository


class InMemoryReservationRepository(ReservationRepository):
    def __init__(self) -> None:
        self._items: dict[str, Reservation] = {}

    def get(self, reservation_id: str) -> Optional[Reservation]:
        return self._items.get(reservation_id)

    def add(self, reservation: Reservation) -> None:
        self._items[reservation.id] = reservation

    def list_for_slot(self, slot: TimeSlot) -> List[Reservation]:
        return [r for r in self._items.values() if r.slot == slot]


class InMemoryTableRepository(TableRepository):
    """In-memory реализация репозитория для Table."""

    def __init__(self) -> None:
        self._items: dict[str, Table] = {}

    def get(self, table_id: TableId) -> Optional[Table]:
        return self._items.get(table_id.value)

    def add(self, table: Table) -> None:
        self._items[table.id.value] = table

    def list_available(self, slot: TimeSlot, min_capacity: int) -> List[Table]:
        """
        Возвращает доступные столы с достаточной вместимостью.
        В реальной реализации здесь была бы проверка пересечения по TimeSlot
        с активными бронированиями.
        """
        return [
            t for t in self._items.values()
            if t.status.value == "AVAILABLE" and t.capacity.value >= min_capacity
        ]


# Заготовка под SQLAlchemy (для лекции / дальнейшего расширения)
class SqlAlchemyReservationRepository(ReservationRepository):
    def __init__(self, session) -> None:
        self.session = session

    def get(self, reservation_id: str) -> Optional[Reservation]:
        raise NotImplementedError

    def add(self, reservation: Reservation) -> None:
        raise NotImplementedError

    def list_for_slot(self, slot: TimeSlot) -> List[Reservation]:
        raise NotImplementedError


class SqlAlchemyTableRepository(TableRepository):
    def __init__(self, session) -> None:
        self.session = session

    def get(self, table_id: TableId) -> Optional[Table]:
        raise NotImplementedError

    def add(self, table: Table) -> None:
        raise NotImplementedError

    def list_available(self, slot: TimeSlot, min_capacity: int) -> List[Table]:
        raise NotImplementedError
