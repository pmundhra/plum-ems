"""Database base configuration"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr

from app.utils.id_generator import _generate_id


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower()

    # Base provides id, created_at and updated_at for all models
    id: Mapped[str] = mapped_column(
        String(17), primary_key=True, index=True, default=lambda: _generate_id()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
