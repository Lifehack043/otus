"""SQLAlchemy-модель пользователя."""

from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class User(Base):
    """Модель пользователя в БД."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
