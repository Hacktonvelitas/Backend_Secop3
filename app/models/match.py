from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from sqlalchemy import (
    ForeignKey, Integer, BigInteger, Numeric, String, Text, UniqueConstraint, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

class MatchRun(Base):
    __tablename__ = "match_run"
    __table_args__ = {"schema": "public"}

    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[Optional[str]] = mapped_column(ForeignKey("public.empresa_info.nit"))
    fecha_ejecucion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    filtros_usados: Mapped[Optional[dict]] = mapped_column(JSONB)
    total_encontrados: Mapped[Optional[int]] = mapped_column(Integer)

    empresa: Mapped["EmpresaInfo"] = relationship(back_populates="match_runs")
    results: Mapped[List["MatchResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_result"
    __table_args__ = (
        UniqueConstraint("run_id", "licitacion_id"),
        {"schema": "public"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public.match_run.run_id"))
    licitacion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public.public_licitacion.id"))
    
    score_similitud: Mapped[Optional[float]] = mapped_column(Numeric) 
    cluster_asignado: Mapped[Optional[int]] = mapped_column(Integer)
    estado_revision: Mapped[Optional[str]] = mapped_column(String(50), default='pendiente')
    comentario_usuario: Mapped[Optional[str]] = mapped_column(Text)

    run: Mapped["MatchRun"] = relationship(back_populates="results")
    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="match_results")
