from __future__ import annotations

from typing import Mapping, Iterable

from booking.application.commands import (
    CreateReservation,
    CancelReservation,
    CompleteReservation,
    CreateTable,
)
from booking.application.unit_of_work import UnitOfWork
from booking.domain.factory import ReservationFactory
from booking.domain.services import TableAllocationService
from booking.domain.model import TableId, TableCapacity, TableAggregate, ReservationAggregate


class CreateReservationHandler:
    """
    Use Case (Application Service):

    - создает агрегат (Factory)
    - вызывает доменные правила (Domain Service + методы Aggregate Root)
    - сохраняет через UoW/Repository
    """

    def __init__(self, uow: UnitOfWork, allocator: TableAllocationService):
        self.uow = uow
        self.allocator = allocator

    def __call__(self, cmd: CreateReservation, available_tables: Iterable[Mapping]) -> str:
        reservation = ReservationFactory.create(
            slot_start=cmd.slot_start,
            duration_min=cmd.duration_min,
            party_size=cmd.party_size,
        )

        # Создаем агрегат из entity
        agg = ReservationAggregate(reservation)

        table_id = self.allocator.allocate(reservation, available_tables)
        agg.assign_table(table_id)
        agg.confirm()

        with self.uow:
            self.uow.reservations.add(agg.root)
            self.uow.commit()

        return agg.root.id


class CancelReservationHandler:
    """
    Use Case: отмена бронирования.

    - загружает агрегат из репозитория
    - вызывает доменную операцию cancel()
    - сохраняет через UoW
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def __call__(self, cmd: CancelReservation) -> None:
        with self.uow:
            reservation = self.uow.reservations.get(cmd.reservation_id)
            if reservation is None:
                raise ValueError(f"Reservation {cmd.reservation_id} not found")

            from booking.domain.model import ReservationAggregate
            agg = ReservationAggregate(reservation)
            agg.cancel()

            self.uow.reservations.add(agg.root)
            self.uow.commit()


class CompleteReservationHandler:
    """
    Use Case: завершение бронирования (гости посетили ресторан).

    - загружает агрегат из репозитория
    - вызывает доменную операцию mark_completed()
    - освобождает стол
    - сохраняет через UoW
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def __call__(self, cmd: CompleteReservation) -> None:
        with self.uow:
            reservation = self.uow.reservations.get(cmd.reservation_id)
            if reservation is None:
                raise ValueError(f"Reservation {cmd.reservation_id} not found")

            from booking.domain.model import ReservationAggregate
            agg = ReservationAggregate(reservation)
            agg.mark_completed()

            # Освобождаем стол
            if reservation.table_id:
                table = self.uow.tables.get(reservation.table_id)
                if table is not None:
                    table_agg = TableAggregate(table)
                    table_agg.release()
                    self.uow.tables.add(table_agg.root)

            self.uow.reservations.add(agg.root)
            self.uow.commit()


class CreateTableHandler:
    """
    Use Case: создание стола.

    - создает TableAggregate
    - сохраняет через UoW
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def __call__(self, cmd: CreateTable) -> str:
        table_id = TableId(cmd.table_id)
        capacity = TableCapacity(cmd.capacity)

        agg = TableAggregate.create(table_id=table_id, capacity=capacity)

        with self.uow:
            self.uow.tables.add(agg.root)
            self.uow.commit()

        return agg.root.id.value
