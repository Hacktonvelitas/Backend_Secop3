from __future__ import annotations
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, BigInteger, Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, EMBED_DIMS_OPENAI

# =========================================================================
# 2. ZONA DE STAGING (INGESTA CRUDA)
# =========================================================================

class StagingLicitations(Base):
    __tablename__ = "staging_licitations"
    __table_args__ = {"schema": "public"}

    lic_id: Mapped[str] = mapped_column(Text, primary_key=True)
    chunk_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    document_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    first_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class StagingDocuments(Base):
    __tablename__ = "staging_documents"
    __table_args__ = {"schema": "public"}

    doc_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lic_id: Mapped[Optional[str]] = mapped_column(Text)
    source_name: Mapped[Optional[str]] = mapped_column(Text)
    source_ext: Mapped[Optional[str]] = mapped_column(Text)
    sha256: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class StagingChunks(Base):
    __tablename__ = "staging_chunks"
    __table_args__ = {"schema": "public"}

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    lic_id: Mapped[Optional[str]] = mapped_column(Text)
    doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public.staging_documents.doc_id"))
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


# =========================================================================
# 3. NÚCLEO LICITACIONES (PUBLIC TENDERS)
# =========================================================================

class PublicLicitacion(Base):
    __tablename__ = "public_licitacion"
    __table_args__ = (
        Index("idx_lic_entidad", "entidad"),
        Index("idx_lic_cierre", "fecha_cierre_oferta"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo_proceso: Mapped[Optional[str]] = mapped_column(String(255), unique=True)

    # Información General
    entidad: Mapped[str] = mapped_column(String(255))
    objeto: Mapped[Optional[str]] = mapped_column(Text)
    descripcion_general: Mapped[Optional[str]] = mapped_column(Text)
    modalidad: Mapped[Optional[str]] = mapped_column(String(255))
    tipo_seleccion: Mapped[Optional[str]] = mapped_column(String(255))
    fundamento_legal: Mapped[Optional[str]] = mapped_column(Text)
    ubicacion: Mapped[Optional[str]] = mapped_column(String(255))
    enlace: Mapped[Optional[str]] = mapped_column(Text)
    estado: Mapped[Optional[str]] = mapped_column(String(100))

    # Presupuesto y Valores
    cuantia: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    valor_estimado_iva: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    presupuesto_ms_oficial: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    presupuesto_dc_oficial: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))

    # Fechas Críticas
    fecha_public: Mapped[Optional[date]] = mapped_column(Date)
    fecha_visita_obra: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fecha_cierre_oferta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fecha_adjudicacion_prog: Mapped[Optional[date]] = mapped_column(Date)
    plazo_meses: Mapped[Optional[int]] = mapped_column(Integer)

    # Clasificación
    codigos_unspsc: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    act_econ: Mapped[Optional[str]] = mapped_column(String(255))

    # Requisitos Habilitantes (Flags rápidos)
    req_cert_9001: Mapped[bool] = mapped_column(Boolean, default=False)
    req_cert_27001: Mapped[bool] = mapped_column(Boolean, default=False)

    # IA (1536 dims)
    objeto_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_OPENAI))

    # Relaciones
    criterios: Mapped[List["LicitacionCriterios"]] = relationship(back_populates="licitacion", cascade="all, delete-orphan")
    observaciones: Mapped[List["LicitacionObservaciones"]] = relationship(back_populates="licitacion", cascade="all, delete-orphan")
    documentos: Mapped[List["LicitacionDocumentos"]] = relationship(back_populates="licitacion", cascade="all, delete-orphan")
    chunks: Mapped[List["PublicLicitacionChunk"]] = relationship(back_populates="licitacion", cascade="all, delete-orphan")
    match_results: Mapped[List["MatchResult"]] = relationship(back_populates="licitacion")


class LicitacionCriterios(Base):
    __tablename__ = "licitacion_criterios"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("public.public_licitacion.id", ondelete="CASCADE"))
    nombre_criterio: Mapped[Optional[str]] = mapped_column(String(255))
    tipo_criterio: Mapped[Optional[str]] = mapped_column(String(50))
    puntaje_maximo: Mapped[Optional[int]] = mapped_column(Integer)
    descripcion_regla: Mapped[Optional[str]] = mapped_column(Text)
    embedding_regla: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_OPENAI))

    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="criterios")


class LicitacionObservaciones(Base):
    __tablename__ = "licitacion_observaciones"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("public.public_licitacion.id", ondelete="CASCADE"))
    fecha_observacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    texto_pregunta: Mapped[Optional[str]] = mapped_column(Text)
    texto_respuesta: Mapped[Optional[str]] = mapped_column(Text)
    cambio_requisito: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding_contexto: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_OPENAI))

    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="observaciones")


class LicitacionDocumentos(Base):
    __tablename__ = "licitacion_documentos"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("public.public_licitacion.id", ondelete="CASCADE"))
    nombre_archivo: Mapped[Optional[str]] = mapped_column(String(255))
    tipo_contenido: Mapped[Optional[str]] = mapped_column(String(50))
    url_archivo: Mapped[Optional[str]] = mapped_column(Text)
    procesado_ia: Mapped[bool] = mapped_column(Boolean, default=False)

    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="documentos")
    chunks: Mapped[List["PublicLicitacionChunk"]] = relationship(back_populates="documento", cascade="all, delete-orphan")


class PublicLicitacionChunk(Base):
    __tablename__ = "public_licitacion_chunk"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    documento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public.licitacion_documentos.id", ondelete="CASCADE"))
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("public.public_licitacion.id"))
    chunk_idx: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[Optional[str]] = mapped_column(Text)
    embedding_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_OPENAI))
    metadatos_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    documento: Mapped["LicitacionDocumentos"] = relationship(back_populates="chunks")
    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="chunks")
