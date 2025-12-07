"""Database base configuration"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower()

    # Note: Individual models define their own id column
    # Base provides created_at and updated_at for all models
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
