from __future__ import annotations
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, BigInteger, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, EMBED_DIMS_LOCAL

class EmpresaInfo(Base):
    __tablename__ = "empresa_info"
    __table_args__ = {"schema": "public"}

    nit: Mapped[str] = mapped_column(String(20), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(255))
    
    # CIIUs
    ciiu1: Mapped[Optional[str]] = mapped_column(String(255))
    ciiu2: Mapped[Optional[str]] = mapped_column(String(255))
    ciiu3: Mapped[Optional[str]] = mapped_column(String(255))
    ciiu4: Mapped[Optional[str]] = mapped_column(String(255))

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
    
    # Relationships
    documentos: Mapped[List["EmpresaDocumentos"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="empresa")
    match_runs: Mapped[List["MatchRun"]] = relationship(back_populates="empresa")


class Companies(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    razon_social: Mapped[Optional[str]] = mapped_column(Text)
    nit: Mapped[Optional[str]] = mapped_column(Text)
    muncomercial: Mapped[Optional[str]] = mapped_column(Text)
    ciiu1: Mapped[Optional[str]] = mapped_column(Text)
    ciiu2: Mapped[Optional[str]] = mapped_column(Text)
    ciiu3: Mapped[Optional[str]] = mapped_column(Text)
    ciiu4: Mapped[Optional[str]] = mapped_column(Text)
    
    # Embeddings (768 dims)
    razon_social_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_LOCAL))
    ciiu1_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_LOCAL))
    ciiu2_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_LOCAL))
    ciiu3_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_LOCAL))
    ciiu4_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBED_DIMS_LOCAL))


class EmpresaDocumentos(Base):
    __tablename__ = "empresa_documentos"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # FK references empresa_info.nit 
    empresa_nit: Mapped[str] = mapped_column(ForeignKey("public.empresa_info.nit", ondelete="CASCADE"))
    nombre_archivo: Mapped[Optional[str]] = mapped_column(String(255))
    tipo_documento: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Conexión con S3
    s3_object_key: Mapped[str] = mapped_column(Text)
    s3_bucket_name: Mapped[Optional[str]] = mapped_column(String(100))
    url_publica: Mapped[Optional[str]] = mapped_column(Text)
    
    etag_s3: Mapped[Optional[str]] = mapped_column(String(255))
    procesado_ia: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    empresa: Mapped["EmpresaInfo"] = relationship(back_populates="documentos")
