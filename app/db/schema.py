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
    financieros: Mapped[List["EmpresaFinancieros"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    experiencia: Mapped[List["EmpresaExperiencia"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    partnerships: Mapped[List["EmpresaPartnerships"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    activos_ti: Mapped[List["EmpresaActivosTI"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    equipo: Mapped[List["EmpresaEquipo"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    sanciones: Mapped[List["EmpresaSanciones"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="empresa")
    match_runs: Mapped[List["MatchRun"]] = relationship(back_populates="empresa")
    consorcios: Mapped[List["ConsorcioMiembros"]] = relationship(back_populates="empresa")


class EmpresaFinancieros(Base):
    __tablename__ = "empresa_financieros"
    __table_args__ = (
        UniqueConstraint("empresa_nit", "ano_fiscal"),
        {"schema": "public"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    ano_fiscal: Mapped[int] = mapped_column(Integer)

    activo_corriente: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    activo_total: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    pasivo_corriente: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    pasivo_total: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    patrimonio_neto: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    utilidad_neta: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    k_contratacion_max: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))

    # Computed columns are tricky in ORM, simplified as read-only or ignored for insert
    ind_liquidez: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), server_default=None) # Generated in DB
    ind_endeudamiento: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), server_default=None) # Generated in DB

    empresa: Mapped["Empresa"] = relationship(back_populates="financieros")


class EmpresaExperiencia(Base):
    __tablename__ = "empresa_experiencia"
    __table_args__ = (
        Index("idx_exp_vec", "objeto_embedding", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}), # Simplified index def
        Index("idx_experiencia_tags", "tech_stack_tags", postgresql_using="gin"),
        {"schema": "public"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    numero_contrato: Mapped[Optional[str]] = mapped_column(String(100))
    cliente_nombre: Mapped[Optional[str]] = mapped_column(String(255))
    sector_cliente: Mapped[Optional[str]] = mapped_column(String(50))
    objeto_contrato: Mapped[Optional[str]] = mapped_column(Text)
    valor_ejecutado_pesos: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    fecha_inicio: Mapped[Optional[date]] = mapped_column(Date)
    fecha_fin: Mapped[Optional[date]] = mapped_column(Date)
    codigos_unspsc: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))

    tech_stack_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    es_certificado: Mapped[bool] = mapped_column(Boolean, default=True)
    objeto_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))

    empresa: Mapped["Empresa"] = relationship(back_populates="experiencia")


class EmpresaPartnerships(Base):
    __tablename__ = "empresa_partnerships"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    fabricante: Mapped[Optional[str]] = mapped_column(String(100))
    nivel_partner: Mapped[Optional[str]] = mapped_column(String(100))
    id_partner_global: Mapped[Optional[str]] = mapped_column(String(100))
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)
    certificado_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="partnerships")


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


class EmpresaEquipo(Base):
    __tablename__ = "empresa_equipo"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit", ondelete="CASCADE"))
    nombre_completo: Mapped[Optional[str]] = mapped_column(String(255))
    titulo_academico: Mapped[Optional[str]] = mapped_column(String(255))
    nivel_estudio: Mapped[Optional[str]] = mapped_column(String(50))
    anos_experiencia: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    resumen_perfil: Mapped[Optional[str]] = mapped_column(Text)
    senior_level: Mapped[Optional[str]] = mapped_column(String(20))
    idiomas: Mapped[Optional[dict]] = mapped_column(JSONB)
    cv_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS))
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)

    empresa: Mapped["Empresa"] = relationship(back_populates="equipo")
    tech_skills: Mapped[List["EquipoTechSkills"]] = relationship(back_populates="equipo", cascade="all, delete-orphan")
    certificaciones: Mapped[List["EquipoCertificaciones"]] = relationship(back_populates="equipo", cascade="all, delete-orphan")


class EquipoTechSkills(Base):
    __tablename__ = "equipo_tech_skills"
    __table_args__ = (
        # CheckConstraint("nivel_dominio BETWEEN 1 AND 5"), # Enforced in DB
        {"schema": "public"}
    )

    equipo_id: Mapped[int] = mapped_column(ForeignKey("public.empresa_equipo.id", ondelete="CASCADE"), primary_key=True)
    tecnologia: Mapped[str] = mapped_column(String(100), primary_key=True)
    anos_experiencia: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    nivel_dominio: Mapped[Optional[int]] = mapped_column(Integer)

    equipo: Mapped["EmpresaEquipo"] = relationship(back_populates="tech_skills")


class EquipoCertificaciones(Base):
    __tablename__ = "equipo_certificaciones"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("public.empresa_equipo.id", ondelete="CASCADE"))
    nombre_cert: Mapped[Optional[str]] = mapped_column(String(255))
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)

    equipo: Mapped["EmpresaEquipo"] = relationship(back_populates="certificaciones")


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
# 5. MOTOR DE CONSORCIOS (SIMULADOR)
# =========================================================================

class SimulacionConsorcios(Base):
    __tablename__ = "simulacion_consorcios"
    __table_args__ = {"schema": "public"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    nombre_alianza: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    liquidez_combinada: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    patrimonio_total: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    k_contratacion_total: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    
    miembros: Mapped[List["ConsorcioMiembros"]] = relationship(back_populates="consorcio", cascade="all, delete-orphan")


class ConsorcioMiembros(Base):
    __tablename__ = "consorcio_miembros"
    __table_args__ = {"schema": "public"}

    consorcio_id: Mapped[str] = mapped_column(ForeignKey("public.simulacion_consorcios.id", ondelete="CASCADE"), primary_key=True)
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa.nit"), primary_key=True)
    porcentaje_part: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    consorcio: Mapped["SimulacionConsorcios"] = relationship(back_populates="miembros")
    empresa: Mapped["Empresa"] = relationship(back_populates="consorcios")


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
    score_similitud: Mapped[Optional[float]] = mapped_column(Numeric) # Float in DDL but usually Numeric in SQL
    cluster_asignado: Mapped[Optional[int]] = mapped_column(Integer)
    estado_revision: Mapped[Optional[str]] = mapped_column(String(50), default='pendiente')
    comentario_usuario: Mapped[Optional[str]] = mapped_column(Text)

    run: Mapped["MatchRun"] = relationship(back_populates="results")
    licitacion: Mapped["PublicLicitacion"] = relationship(back_populates="match_results")
