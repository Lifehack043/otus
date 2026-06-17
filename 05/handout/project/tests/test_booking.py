"""
Тесты для приложения бронирования столиков.

Покрывают:
- Доменные инварианты (model, events, aggregates)
- Use cases (handlers)
- Репозитории и Unit of Work
"""
from datetime import datetime, timedelta

import pytest


# =============================================================================
# Domain Model Tests
# =============================================================================

def test_timeslot_invariant_start_must_be_before_end():
    """TimeSlot: start < end."""
    from booking.domain.model import TimeSlot
    start = datetime(2030, 1, 1, 19, 0)
    end = datetime(2030, 1, 1, 18, 0)
    with pytest.raises(ValueError, match="start must be < end"):
        TimeSlot(start=start, end=end)


def test_timeslot_equal_times_fails():
    """TimeSlot: start != end."""
    from booking.domain.model import TimeSlot
    now = datetime(2030, 1, 1, 19, 0)
    with pytest.raises(ValueError, match="start must be < end"):
        TimeSlot(start=now, end=now)


def test_party_size_must_be_positive():
    """PartySize: value >= 1."""
    from booking.domain.model import PartySize
    with pytest.raises(ValueError, match="must be >= 1"):
        PartySize(value=0)
    with pytest.raises(ValueError, match="must be >= 1"):
        PartySize(value=-5)


def test_table_capacity_must_be_positive():
    """TableCapacity: value >= 1."""
    from booking.domain.model import TableCapacity
    with pytest.raises(ValueError, match="must be >= 1"):
        TableCapacity(value=0)
    with pytest.raises(ValueError, match="must be >= 1"):
        TableCapacity(value=-3)


def test_reservation_creation():
    """Reservation создается корректно."""
    from booking.domain.model import Reservation, TimeSlot, PartySize, ReservationStatus
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    r = Reservation(reservation_id="R1", slot=slot, party_size=ps)
    assert r.id == "R1"
    assert r.status == ReservationStatus.CREATED
    assert r.table_id is None


def test_reservation_aggregate_create_emits_event():
    """ReservationAggregate.create() генерирует ReservationCreated."""
    from booking.domain.model import ReservationAggregate, TimeSlot, PartySize, ReservationCreated
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    assert len(agg.events) == 1
    assert isinstance(agg.events[0], ReservationCreated)
    assert agg.events[0].reservation_id == "R1"


def test_reservation_aggregate_assign_table():
    """assign_table() работает только для CREATED."""
    from booking.domain.model import (
        ReservationAggregate, TimeSlot, PartySize, TableId, ReservationStatus, TableAssigned
    )
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    agg.assign_table(TableId("T1"))
    assert agg.root.table_id.value == "T1"
    assert any(isinstance(e, TableAssigned) for e in agg.events)


def test_reservation_aggregate_assign_table_fails_when_not_created():
    """assign_table() падает, если статус не CREATED."""
    from booking.domain.model import (
        ReservationAggregate, TimeSlot, PartySize, TableId, ReservationStatus
    )
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    # Симулируем изменение статуса
    agg._root.status = ReservationStatus.CONFIRMED
    with pytest.raises(ValueError, match="can assign table only for CREATED"):
        agg.assign_table(TableId("T1"))


def test_reservation_aggregate_confirm_requires_table():
    """confirm() требует назначенный стол."""
    from booking.domain.model import ReservationAggregate, TimeSlot, PartySize
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    with pytest.raises(ValueError, match="cannot confirm without assigned table"):
        agg.confirm()


def test_reservation_aggregate_confirm_flow():
    """Полный поток: create -> assign_table -> confirm."""
    from booking.domain.model import (
        ReservationAggregate, TimeSlot, PartySize, TableId, ReservationStatus, ReservationConfirmed
    )
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    agg.assign_table(TableId("T1"))
    agg.confirm()
    assert agg.root.status == ReservationStatus.CONFIRMED
    assert any(isinstance(e, ReservationConfirmed) for e in agg.events)


def test_reservation_aggregate_cancel():
    """cancel() меняет статус на CANCELLED."""
    from booking.domain.model import (
        ReservationAggregate, TimeSlot, PartySize, ReservationStatus, ReservationCancelled
    )
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    agg.cancel()
    assert agg.root.status == ReservationStatus.CANCELLED
    assert any(isinstance(e, ReservationCancelled) for e in agg.events)


def test_reservation_aggregate_cancel_idempotent():
    """cancel() идемпотентен."""
    from booking.domain.model import ReservationAggregate, TimeSlot, PartySize, ReservationCancelled
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    agg.cancel()
    agg.cancel()
    cancelled_events = [e for e in agg.events if isinstance(e, ReservationCancelled)]
    assert len(cancelled_events) == 1


def test_reservation_aggregate_cancel_fails_for_completed():
    """cancel() падает для COMPLETED."""
    from booking.domain.model import ReservationAggregate, TimeSlot, PartySize, ReservationStatus
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    agg._root.status = ReservationStatus.COMPLETED
    with pytest.raises(ValueError, match="cannot cancel COMPLETED"):
        agg.cancel()


def test_reservation_aggregate_mark_completed():
    """mark_completed() работает только для CONFIRMED."""
    from booking.domain.model import (
        ReservationAggregate, TimeSlot, PartySize, TableId, ReservationStatus, ReservationCompleted
    )
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    agg.assign_table(TableId("T1"))
    agg.confirm()
    agg.mark_completed()
    assert agg.root.status == ReservationStatus.COMPLETED
    assert any(isinstance(e, ReservationCompleted) for e in agg.events)


def test_reservation_aggregate_mark_completed_fails_for_created():
    """mark_completed() падает для CREATED."""
    from booking.domain.model import ReservationAggregate, TimeSlot, PartySize
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    ps = PartySize(value=4)
    agg = ReservationAggregate.create("R1", slot, ps)
    with pytest.raises(ValueError, match="can complete only CONFIRMED"):
        agg.mark_completed()


# =============================================================================
# Table Domain Model Tests
# =============================================================================

def test_table_creation():
    """Table создается корректно."""
    from booking.domain.model import Table, TableId, TableCapacity, TableStatus
    t = Table(table_id=TableId("T1"), capacity=TableCapacity(4))
    assert t.id.value == "T1"
    assert t.capacity.value == 4
    assert t.status == TableStatus.AVAILABLE


def test_table_aggregate_create_emits_event():
    """TableAggregate.create() генерирует TableCreated."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity, TableCreated
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    assert len(agg.events) == 1
    assert isinstance(agg.events[0], TableCreated)
    assert agg.events[0].table_id == "T1"


def test_table_aggregate_occupy():
    """occupy() меняет статус на OCCUPIED."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity, TableStatus
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.occupy()
    assert agg.root.status == TableStatus.OCCUPIED


def test_table_aggregate_occupy_idempotent():
    """occupy() идемпотентен."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.occupy()
    agg.occupy()
    assert agg.root.status.value == "OCCUPIED"


def test_table_aggregate_release():
    """release() меняет статус на AVAILABLE."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity, TableStatus
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.occupy()
    agg.release()
    assert agg.root.status == TableStatus.AVAILABLE


def test_table_aggregate_release_idempotent():
    """release() идемпотентен."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.release()
    agg.release()
    assert agg.root.status.value == "AVAILABLE"


def test_table_aggregate_remove():
    """remove() меняет статус на REMOVED."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity, TableStatus, TableRemoved
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.remove()
    assert agg.root.status == TableStatus.REMOVED
    assert any(isinstance(e, TableRemoved) for e in agg.events)


def test_table_aggregate_remove_fails_when_occupied():
    """remove() падает для OCCUPIED."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.occupy()
    with pytest.raises(ValueError, match="cannot remove an OCCUPIED table"):
        agg.remove()


def test_table_aggregate_cannot_occupy_removed():
    """occupy() падает для REMOVED."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.remove()
    with pytest.raises(ValueError, match="cannot occupy a REMOVED table"):
        agg.occupy()


def test_table_aggregate_cannot_release_removed():
    """release() падает для REMOVED."""
    from booking.domain.model import TableAggregate, TableId, TableCapacity
    agg = TableAggregate.create(TableId("T1"), TableCapacity(4))
    agg.remove()
    with pytest.raises(ValueError, match="cannot release a REMOVED table"):
        agg.release()


# =============================================================================
# Domain Service Tests
# =============================================================================

def test_table_allocation_service_selects_best_fit():
    """TableAllocationService выбирает стол с минимальной подходящей вместимостью."""
    from booking.domain.model import Reservation, TimeSlot, PartySize
    from booking.domain.services import TableAllocationService
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    r = Reservation(reservation_id="R1", slot=slot, party_size=PartySize(3))
    service = TableAllocationService()
    tables = [
        {"id": "T1", "capacity": 2},
        {"id": "T2", "capacity": 4},
        {"id": "T3", "capacity": 6},
    ]
    result = service.allocate(r, tables)
    assert result.value == "T2"


def test_table_allocation_service_no_suitable_table():
    """TableAllocationService падает, если нет подходящих столов."""
    from booking.domain.model import Reservation, TimeSlot, PartySize
    from booking.domain.services import TableAllocationService
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    r = Reservation(reservation_id="R1", slot=slot, party_size=PartySize(10))
    service = TableAllocationService()
    tables = [
        {"id": "T1", "capacity": 2},
        {"id": "T2", "capacity": 4},
    ]
    with pytest.raises(ValueError, match="No suitable table available"):
        service.allocate(r, tables)


# =============================================================================
# Factory Tests
# =============================================================================

def test_reservation_factory_creates_valid_reservation():
    """ReservationFactory создает корректную бронь."""
    from booking.domain.factory import ReservationFactory
    r = ReservationFactory.create(
        slot_start=datetime(2030, 1, 1, 19, 0),
        duration_min=90,
        party_size=4,
    )
    assert r.id is not None
    assert r.slot.end == r.slot.start + timedelta(minutes=90)
    assert r.party_size.value == 4


def test_reservation_factory_negative_duration_fails():
    """ReservationFactory падает при отрицательной длительности."""
    from booking.domain.factory import ReservationFactory
    with pytest.raises(ValueError):
        ReservationFactory.create(
            slot_start=datetime(2030, 1, 1, 19, 0),
            duration_min=-10,
            party_size=4,
        )


# =============================================================================
# Repository Tests
# =============================================================================

def test_in_memory_reservation_repository():
    """InMemoryReservationRepository: add/get/list_for_slot."""
    from booking.infrastructure.repositories import InMemoryReservationRepository
    from booking.domain.model import Reservation, TimeSlot, PartySize
    repo = InMemoryReservationRepository()
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    r = Reservation(reservation_id="R1", slot=slot, party_size=PartySize(4))
    repo.add(r)
    assert repo.get("R1") is r
    assert repo.get("R999") is None
    assert repo.list_for_slot(slot) == [r]


def test_in_memory_table_repository():
    """InMemoryTableRepository: add/get/list_available."""
    from booking.infrastructure.repositories import InMemoryTableRepository
    from booking.domain.model import Table, TableId, TableCapacity, TimeSlot, TableStatus
    repo = InMemoryTableRepository()
    t1 = Table(table_id=TableId("T1"), capacity=TableCapacity(4))
    t2 = Table(table_id=TableId("T2"), capacity=TableCapacity(2))
    t2.status = TableStatus.OCCUPIED
    repo.add(t1)
    repo.add(t2)
    assert repo.get(TableId("T1")) is t1
    assert repo.get(TableId("T999")) is None
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    available = repo.list_available(slot, min_capacity=3)
    assert available == [t1]


# =============================================================================
# Unit of Work Tests
# =============================================================================

def test_in_memory_uow_commit():
    """InMemoryUnitOfWork: commit устанавливает committed=True."""
    from booking.infrastructure.uow import InMemoryUnitOfWork
    uow = InMemoryUnitOfWork()
    with uow:
        uow.commit()
    assert uow.committed is True


def test_in_memory_uow_rollback_on_exception():
    """InMemoryUnitOfWork: исключение вызывает rollback."""
    from booking.infrastructure.uow import InMemoryUnitOfWork
    from booking.domain.model import Reservation, TimeSlot, PartySize
    uow = InMemoryUnitOfWork()
    slot = TimeSlot(start=datetime(2030, 1, 1, 19, 0), end=datetime(2030, 1, 1, 20, 30))
    r = Reservation(reservation_id="R1", slot=slot, party_size=PartySize(4))
    try:
        with uow:
            uow.reservations.add(r)
            raise ValueError("Something went wrong")
    except ValueError:
        pass
    assert uow.committed is False
    assert uow.reservations.get("R1") is None  # Данные очищены


def test_in_memory_uow_has_tables_repo():
    """InMemoryUnitOfWork имеет tables репозиторий."""
    from booking.infrastructure.uow import InMemoryUnitOfWork
    uow = InMemoryUnitOfWork()
    assert uow.tables is not None


# =============================================================================
# Handler Tests
# =============================================================================

def test_create_reservation_happy_path():
    """CreateReservationHandler: полный сценарий."""
    from booking.application.commands import CreateReservation
    from booking.application.handlers import CreateReservationHandler
    from booking.domain.services import TableAllocationService
    from booking.infrastructure.uow import InMemoryUnitOfWork

    uow = InMemoryUnitOfWork()
    handler = CreateReservationHandler(uow, TableAllocationService())

    cmd = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0, 0),
        duration_min=90,
        party_size=3,
    )

    reservation_id = handler(cmd, available_tables=[
        {"id": "T1", "capacity": 2},
        {"id": "T2", "capacity": 4},
    ])

    assert reservation_id
    assert uow.committed is True

    saved = uow.reservations.get(reservation_id)
    assert saved is not None
    assert saved.status.value == "CONFIRMED"
    assert saved.table_id.value == "T2"


def test_create_reservation_timeslot_invariant():
    """CreateReservationHandler: отрицательная длительность."""
    from booking.application.commands import CreateReservation
    from booking.application.handlers import CreateReservationHandler
    from booking.domain.services import TableAllocationService
    from booking.infrastructure.uow import InMemoryUnitOfWork

    uow = InMemoryUnitOfWork()
    handler = CreateReservationHandler(uow, TableAllocationService())

    cmd = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0, 0),
        duration_min=-10,
        party_size=2,
    )

    with pytest.raises(ValueError):
        handler(cmd, available_tables=[{"id": "T1", "capacity": 4}])


def test_cancel_reservation_handler():
    """CancelReservationHandler: отмена бронирования."""
    from booking.application.commands import CreateReservation, CancelReservation
    from booking.application.handlers import CreateReservationHandler, CancelReservationHandler
    from booking.domain.services import TableAllocationService
    from booking.infrastructure.uow import InMemoryUnitOfWork
    from booking.domain.model import ReservationStatus

    uow = InMemoryUnitOfWork()
    create_handler = CreateReservationHandler(uow, TableAllocationService())

    cmd = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0, 0),
        duration_min=90,
        party_size=3,
    )
    reservation_id = create_handler(cmd, available_tables=[{"id": "T1", "capacity": 4}])

    cancel_handler = CancelReservationHandler(uow)
    cancel_handler(CancelReservation(reservation_id=reservation_id))

    saved = uow.reservations.get(reservation_id)
    assert saved.status == ReservationStatus.CANCELLED


def test_cancel_reservation_not_found():
    """CancelReservationHandler: бронирование не найдено."""
    from booking.application.commands import CancelReservation
    from booking.application.handlers import CancelReservationHandler
    from booking.infrastructure.uow import InMemoryUnitOfWork

    uow = InMemoryUnitOfWork()
    handler = CancelReservationHandler(uow)

    with pytest.raises(ValueError, match="not found"):
        handler(CancelReservation(reservation_id="NONEXISTENT"))


def test_complete_reservation_handler():
    """CompleteReservationHandler: завершение бронирования."""
    from booking.application.commands import CreateReservation, CompleteReservation
    from booking.application.handlers import CreateReservationHandler, CompleteReservationHandler
    from booking.domain.services import TableAllocationService
    from booking.infrastructure.uow import InMemoryUnitOfWork
    from booking.domain.model import ReservationStatus, TableId, TableStatus

    uow = InMemoryUnitOfWork()
    create_handler = CreateReservationHandler(uow, TableAllocationService())

    cmd = CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0, 0),
        duration_min=90,
        party_size=3,
    )
    reservation_id = create_handler(cmd, available_tables=[{"id": "T1", "capacity": 4}])

    # Добавляем стол в UoW для проверки освобождения
    from booking.domain.model import Table, TableId, TableCapacity, TableStatus, TableAggregate
    table = Table(table_id=TableId("T1"), capacity=TableCapacity(4))
    table_agg = TableAggregate(table)
    table_agg.occupy()
    uow.tables.add(table_agg.root)

    complete_handler = CompleteReservationHandler(uow)
    complete_handler(CompleteReservation(reservation_id=reservation_id))

    saved = uow.reservations.get(reservation_id)
    assert saved.status == ReservationStatus.COMPLETED

    # Стол должен быть освобожден
    saved_table = uow.tables.get(TableId("T1"))
    assert saved_table.status == TableStatus.AVAILABLE


def test_complete_reservation_not_found():
    """CompleteReservationHandler: бронирование не найдено."""
    from booking.application.commands import CompleteReservation
    from booking.application.handlers import CompleteReservationHandler
    from booking.infrastructure.uow import InMemoryUnitOfWork

    uow = InMemoryUnitOfWork()
    handler = CompleteReservationHandler(uow)

    with pytest.raises(ValueError, match="not found"):
        handler(CompleteReservation(reservation_id="NONEXISTENT"))


def test_create_table_handler():
    """CreateTableHandler: создание стола."""
    from booking.application.commands import CreateTable
    from booking.application.handlers import CreateTableHandler
    from booking.infrastructure.uow import InMemoryUnitOfWork
    from booking.domain.model import TableId

    uow = InMemoryUnitOfWork()
    handler = CreateTableHandler(uow)

    table_id = handler(CreateTable(table_id="T1", capacity=4))
    assert table_id == "T1"
    assert uow.committed is True

    table = uow.tables.get(TableId("T1"))
    assert table is not None
    assert table.capacity.value == 4


def test_create_table_invalid_capacity():
    """CreateTableHandler: невалидная вместимость."""
    from booking.application.commands import CreateTable
    from booking.application.handlers import CreateTableHandler
    from booking.infrastructure.uow import InMemoryUnitOfWork

    uow = InMemoryUnitOfWork()
    handler = CreateTableHandler(uow)

    with pytest.raises(ValueError, match="must be >= 1"):
        handler(CreateTable(table_id="T1", capacity=0))


# =============================================================================
# Full Integration Tests (с таблицами)
# =============================================================================

def test_full_flow_create_table_and_reserve():
    """Полный сценарий: создать стол -> забронировать -> завершить."""
    from booking.application.commands import CreateTable, CreateReservation, CompleteReservation
    from booking.application.handlers import CreateTableHandler, CreateReservationHandler, CompleteReservationHandler
    from booking.domain.services import TableAllocationService
    from booking.infrastructure.uow import InMemoryUnitOfWork
    from booking.domain.model import TableId, ReservationStatus, TableStatus

    uow = InMemoryUnitOfWork()

    # 1. Создаем стол
    table_handler = CreateTableHandler(uow)
    table_handler(CreateTable(table_id="T1", capacity=4))

    # 2. Создаем бронирование
    create_handler = CreateReservationHandler(uow, TableAllocationService())
    reservation_id = create_handler(CreateReservation(
        slot_start=datetime(2030, 1, 1, 19, 0),
        duration_min=60,
        party_size=3,
    ), available_tables=[{"id": "T1", "capacity": 4}])

    reservation = uow.reservations.get(reservation_id)
    assert reservation.status == ReservationStatus.CONFIRMED
    assert reservation.table_id.value == "T1"

    # 3. Завершаем бронирование
    table = uow.tables.get(TableId("T1"))
    from booking.domain.model import TableAggregate
    table_agg = TableAggregate(table)
    table_agg.occupy()
    uow.tables.add(table_agg.root)

    complete_handler = CompleteReservationHandler(uow)
    complete_handler(CompleteReservation(reservation_id=reservation_id))

    assert uow.reservations.get(reservation_id).status == ReservationStatus.COMPLETED
    assert uow.tables.get(TableId("T1")).status == TableStatus.AVAILABLE
