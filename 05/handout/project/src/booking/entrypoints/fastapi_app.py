"""
FastAPI entrypoint для приложения бронирования столиков.

Все маршруты идут через application handlers, которые orchestруют
доменную логику и сохранение через Unit of Work.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from booking.application.commands import (
    CreateReservation,
    CancelReservation,
    CompleteReservation,
    CreateTable,
)
from booking.application.handlers import (
    CreateReservationHandler,
    CancelReservationHandler,
    CompleteReservationHandler,
    CreateTableHandler,
)
from booking.domain.services import TableAllocationService
from booking.infrastructure.uow import InMemoryUnitOfWork


app = FastAPI(title="Restaurant Booking API", version="1.0.0")

# Глобальный UoW (для демо; в продакшене используется dependency injection).
uow = InMemoryUnitOfWork()
allocator = TableAllocationService()


# =============================================================================
# DTO / Schemas
# =============================================================================

class CreateReservationDTO(BaseModel):
    slot_start: datetime = Field(..., description="Начало бронирования")
    duration_min: int = Field(..., ge=1, description="Длительность в минутах")
    party_size: int = Field(..., ge=1, description="Количество гостей")


class CancelReservationDTO(BaseModel):
    reservation_id: str = Field(..., description="ID бронирования")


class CreateTableDTO(BaseModel):
    table_id: str = Field(..., description="Уникальный ID стола")
    capacity: int = Field(..., ge=1, description="Вместимость стола")


class ReservationResponse(BaseModel):
    reservation_id: str
    status: str
    table_id: Optional[str] = None


class TableResponse(BaseModel):
    table_id: str
    capacity: int
    status: str


# =============================================================================
# Routes - Tables
# =============================================================================

@app.post("/tables", response_model=TableResponse, status_code=201)
def create_table(dto: CreateTableDTO):
    """Создать новый стол в ресторане."""
    try:
        handler = CreateTableHandler(uow)
        cmd = CreateTable(table_id=dto.table_id, capacity=dto.capacity)
        table_id = handler(cmd)
        table = uow.tables.get(type('TableId', (), {'value': table_id})())
        # Простой способ получить TableId
        from booking.domain.model import TableId
        table = uow.tables.get(TableId(table_id))
        return TableResponse(
            table_id=table.id.value,
            capacity=table.capacity.value,
            status=table.status.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tables", response_model=List[TableResponse])
def list_tables():
    """Получить список всех столов."""
    from booking.domain.model import TableId
    tables = []
    for t in uow.tables._items.values():
        tables.append(TableResponse(
            table_id=t.id.value,
            capacity=t.capacity.value,
            status=t.status.value,
        ))
    return tables


@app.get("/tables/{table_id}", response_model=TableResponse)
def get_table(table_id: str):
    """Получить информацию о столе."""
    from booking.domain.model import TableId
    table = uow.tables.get(TableId(table_id))
    if table is None:
        raise HTTPException(status_code=404, detail=f"Table {table_id} not found")
    return TableResponse(
        table_id=table.id.value,
        capacity=table.capacity.value,
        status=table.status.value,
    )


# =============================================================================
# Routes - Reservations
# =============================================================================

@app.post("/reservations", response_model=ReservationResponse, status_code=201)
def create_reservation(dto: CreateReservationDTO):
    """Создать бронирование столика."""
    try:
        handler = CreateReservationHandler(uow, allocator)
        cmd = CreateReservation(
            slot_start=dto.slot_start,
            duration_min=dto.duration_min,
            party_size=dto.party_size,
        )
        # Получаем доступные столы из репозитория
        available_tables = [
            {"id": t.id.value, "capacity": t.capacity.value}
            for t in uow.tables._items.values()
            if t.status.value == "AVAILABLE"
        ]
        reservation_id = handler(cmd, available_tables=available_tables)
        saved = uow.reservations.get(reservation_id)
        return ReservationResponse(
            reservation_id=saved.id,
            status=saved.status.value,
            table_id=saved.table_id.value if saved.table_id else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(reservation_id: str):
    """Отменить бронирование."""
    try:
        handler = CancelReservationHandler(uow)
        cmd = CancelReservation(reservation_id=reservation_id)
        handler(cmd)
        return {"message": f"Reservation {reservation_id} cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/reservations/{reservation_id}/complete")
def complete_reservation(reservation_id: str):
    """Завершить бронирование (гости посетили ресторан)."""
    try:
        handler = CompleteReservationHandler(uow)
        from booking.application.commands import CompleteReservation
        cmd = CompleteReservation(reservation_id=reservation_id)
        handler(cmd)
        return {"message": f"Reservation {reservation_id} completed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/reservations", response_model=List[ReservationResponse])
def list_reservations():
    """Получить список всех бронирований."""
    reservations = []
    for r in uow.reservations._items.values():
        reservations.append(ReservationResponse(
            reservation_id=r.id,
            status=r.status.value,
            table_id=r.table_id.value if r.table_id else None,
        ))
    return reservations


@app.get("/reservations/{reservation_id}", response_model=ReservationResponse)
def get_reservation(reservation_id: str):
    """Получить информацию о бронировании."""
    reservation = uow.reservations.get(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail=f"Reservation {reservation_id} not found")
    return ReservationResponse(
        reservation_id=reservation.id,
        status=reservation.status.value,
        table_id=reservation.table_id.value if reservation.table_id else None,
    )
