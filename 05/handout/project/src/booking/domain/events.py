from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


# Domain Events = факты, которые произошли в домене

# --- Reservation Events ---
@dataclass(frozen=True)
class ReservationCreated:
    reservation_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class ReservationConfirmed:
    reservation_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class ReservationCancelled:
    reservation_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class TableAssigned:
    reservation_id: str
    table_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class ReservationCompleted:
    reservation_id: str
    occurred_at: datetime


# --- Table Events ---
@dataclass(frozen=True)
class TableCreated:
    table_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class TableRemoved:
    table_id: str
    occurred_at: datetime
