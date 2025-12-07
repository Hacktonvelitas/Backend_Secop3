from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text
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
    # FK references empresa_info
    empresa_nit: Mapped[Optional[str]] = mapped_column(ForeignKey("public.empresa_info.nit"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    empresa: Mapped["EmpresaInfo"] = relationship(back_populates="usuarios")
