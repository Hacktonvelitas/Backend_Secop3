# app/db/schema.py
from __future__ import annotations

import os
from datetime import date, datetime
from typing import List, Optional, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    JSON
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

# --- Base declarativa
class Base(DeclarativeBase):
    pass

# Tamaño del vector según entorno (default 1536 segun DDL)
EMBED_DIMS = 1536

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StagingChunks(Base):
    __tablename__ = "staging_chunks"
    __table_args__ = {"schema": "public"}

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    lic_id: Mapped[Optional[str]] = mapped_column(Text)
    doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public.staging_documents.doc_id"))
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    codigos_unspsc: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text)) # TEXT[] in DDL
    act_econ: Mapped[Optional[str]] = mapped_column(String(255))

    # Requisitos Habilitantes (Flags rápidos)
    req_cert_9001: Mapped[bool] = mapped_column(Boolean, default=False)
    req_cert_27001: Mapped[bool] = mapped_column(Boolean, default=False)

    # IA
    objeto_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))

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
    embedding_regla: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))

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
    embedding_contexto: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))

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
    embedding_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))
    metadatos_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    documento: Mapped["LicitacionDocumentos"] = relationship(back_populates="chunks")
    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="chunks")


# =========================================================================
# 4. NÚCLEO EMPRESARIAL (PERFIL 360 + IT SPECIALIZATION)
# =========================================================================

class Empresa(Base):
    __tablename__ = "empresa"
    __table_args__ = {"schema": "public"}

    nit: Mapped[str] = mapped_column(String(20), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(255))
    sigla: Mapped[Optional[str]] = mapped_column(String(50))

    # Ubicación y Contacto
    pais: Mapped[Optional[str]] = mapped_column(String(50), default='Colombia')
    departamento: Mapped[Optional[str]] = mapped_column(String(100))
    municipio: Mapped[Optional[str]] = mapped_column(String(100))
    direccion_legal: Mapped[Optional[str]] = mapped_column(Text)
    correo_contacto: Mapped[Optional[str]] = mapped_column(Text)

    # Perfil Legal y Tamaño
    fecha_constitucion: Mapped[Optional[date]] = mapped_column(Date)
    anios_existencia: Mapped[Optional[int]] = mapped_column(Integer)
    tamano_empresarial: Mapped[Optional[str]] = mapped_column(String(20))
    es_mipyme_acreditada: Mapped[bool] = mapped_column(Boolean, default=False)

    # Incentivos de Ley
    tiene_sello_mujer: Mapped[bool] = mapped_column(Boolean, default=False)
    tiene_pers_discapacidad: Mapped[bool] = mapped_column(Boolean, default=False)
    es_zomac: Mapped[bool] = mapped_column(Boolean, default=False)

    # IA Profile
    razon_social_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))

    # Relaciones
    activos_ti: Mapped[List["EmpresaActivosTI"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    sanciones: Mapped[List["EmpresaSanciones"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    documentos: Mapped[List["EmpresaDocumentos"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="empresa")
    match_runs: Mapped[List["MatchRun"]] = relationship(back_populates="empresa")


class EmpresaDocumentos(Base):
    __tablename__ = "empresa_documentos"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    nombre_archivo: Mapped[Optional[str]] = mapped_column(String(255))
    tipo_documento: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Conexión con S3
    s3_object_key: Mapped[str] = mapped_column(Text)
    s3_bucket_name: Mapped[Optional[str]] = mapped_column(String(100))
    url_publica: Mapped[Optional[str]] = mapped_column(Text)
    
    etag_s3: Mapped[Optional[str]] = mapped_column(String(255))
    procesado_ia: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="documentos")
    chunks: Mapped[List["EmpresaDocumentosChunk"]] = relationship(back_populates="documento", cascade="all, delete-orphan")


class EmpresaDocumentosChunk(Base):
    __tablename__ = "empresa_documentos_chunk"
    __table_args__ = (
        Index("idx_empresa_docs_vec", "embedding_vec", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}),
        {"schema": "public"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    documento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("public.empresa_documentos.id", ondelete="CASCADE"))
    empresa_nit: Mapped[Optional[str]] = mapped_column(ForeignKey("public.empresa.nit"))
    
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer)
    chunk_text: Mapped[Optional[str]] = mapped_column(Text)
    embedding_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))
    
    metadatos_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    documento: Mapped["EmpresaDocumentos"] = relationship(back_populates="chunks")
    # empresa relation optional but good for consistency, though not explicitly back_populated from Empresa unless we add it to Empresa too (which ddl.sql doesn't strictly need relation logic for, but useful in ORM)
    # DDL has FK but I will not add back_populates to Empresa to keep Empresa clean as per DDL logic primarily.


class EmpresaActivosTI(Base):
    __tablename__ = "empresa_activos_ti"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    tipo_activo: Mapped[Optional[str]] = mapped_column(String(50))
    nombre_activo: Mapped[Optional[str]] = mapped_column(String(255))
    especificaciones: Mapped[Optional[dict]] = mapped_column(JSONB)
    cantidad_propia: Mapped[int] = mapped_column(Integer, default=1)
    es_arrendado: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="activos_ti")


class EmpresaSanciones(Base):
    __tablename__ = "empresa_sanciones"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    tipo_sancion: Mapped[Optional[str]] = mapped_column(String(100))
    entidad_sancionadora: Mapped[Optional[str]] = mapped_column(String(255))
    fecha_fin: Mapped[Optional[date]] = mapped_column(Date)
    estado_actual: Mapped[Optional[str]] = mapped_column(String(50))

    empresa: Mapped["Empresa"] = relationship(back_populates="sanciones")


# =========================================================================
# 6. USUARIOS Y SISTEMA DE MATCHING
# =========================================================================

class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    nombre_completo: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(Text)
    empresa_nit: Mapped[Optional[str]] = mapped_column(ForeignKey("public.empresa.nit"))
    rol: Mapped[Optional[str]] = mapped_column(String(50), default='user')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="usuarios")


class MatchRun(Base):
    __tablename__ = "match_run"
    __table_args__ = {"schema": "public"}

    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[Optional[str]] = mapped_column(ForeignKey("public.empresa.nit"))
    fecha_ejecucion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    filtros_usados: Mapped[Optional[dict]] = mapped_column(JSONB)
    total_encontrados: Mapped[Optional[int]] = mapped_column(Integer)

    empresa: Mapped["Empresa"] = relationship(back_populates="match_runs")
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
    score_similitud: Mapped[Optional[float]] = mapped_column(Numeric) # Keeping Numeric to match DDL FLOAT but usually SQLAlchemy Float handles python float better. DDL has FLOAT (which is float8). Numeric is DECIMAL. schema.py had Numeric for others. I'll stick to float python type mapping to Numeric or Float column.
    # DDL: score_similitud FLOAT
    # SQLAlchemy: Float is best for PostgreSQL FLOAT
    # However, existing schema used Numeric which is safer for currency. But score is similarity. I'll leave as Numeric if it was working or change to Float?
    # Original schema.py had Numeric. DDL has FLOAT. I will use Float here to be more accurate to DDL "FLOAT".
    # Wait, previous schema.py had: score_similitud: Mapped[Optional[float]] = mapped_column(Numeric)
    # I will change mapped_column(Numeric) to mapped_column(Float) match DDL "FLOAT" better conceptually, but if it breaks something I can revert.
    # Actually, let's keep it safe. "FLOAT" in PG is double precision.
    # I will change it to Float.

    cluster_asignado: Mapped[Optional[int]] = mapped_column(Integer)
    estado_revision: Mapped[Optional[str]] = mapped_column(String(50), default='pendiente')
    comentario_usuario: Mapped[Optional[str]] = mapped_column(Text)

    run: Mapped["MatchRun"] = relationship(back_populates="results")
    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="match_results")
