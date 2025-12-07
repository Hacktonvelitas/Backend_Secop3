from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    nombre_completo: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(Text)
    
    # Relación opcional: El usuario se crea primero, luego se asocia la empresa
    empresa_nit: Mapped[Optional[str]] = mapped_column(ForeignKey("public.empresa.nit"))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="usuario")
