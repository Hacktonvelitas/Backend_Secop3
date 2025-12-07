from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# --- Empresa Documentos ---
class EmpresaDocumentoBase(BaseModel):
    nombre_archivo: Optional[str] = None
    tipo_documento: Optional[str] = None
    s3_object_key: str
    s3_bucket_name: Optional[str] = None
    url_publica: Optional[str] = None
    etag_s3: Optional[str] = None
    procesado_ia: bool = False

class EmpresaDocumentoCreate(EmpresaDocumentoBase):
    pass

class EmpresaDocumentoOut(EmpresaDocumentoBase):
    id: int
    empresa_nit: str
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Companies (Vectores/Info Adicional) ---
class CompaniesBase(BaseModel):
    razon_social: Optional[str] = None
    muncomercial: Optional[str] = None
    ciiu1: Optional[str] = None
    ciiu2: Optional[str] = None
    ciiu3: Optional[str] = None
    ciiu4: Optional[str] = None

class CompaniesOut(CompaniesBase):
    id: int
    nit: Optional[str] = None
    
    class Config:
        from_attributes = True

# --- Empresa ---
class EmpresaBase(BaseModel):
    razon_social: str
    ciiu1: Optional[str] = None
    ciiu2: Optional[str] = None
    ciiu3: Optional[str] = None
    ciiu4: Optional[str] = None
    
    pais: Optional[str] = "Colombia"
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    direccion_legal: Optional[str] = None
    correo_contacto: Optional[str] = None
    
    fecha_constitucion: Optional[date] = None
    anios_existencia: Optional[int] = None
    tamano_empresarial: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    nit: str

class EmpresaUpdate(BaseModel):
    razon_social: Optional[str] = None
    ciiu1: Optional[str] = None
    ciiu2: Optional[str] = None
    ciiu3: Optional[str] = None
    ciiu4: Optional[str] = None
    pais: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    direccion_legal: Optional[str] = None
    correo_contacto: Optional[str] = None
    fecha_constitucion: Optional[date] = None
    anios_existencia: Optional[int] = None
    tamano_empresarial: Optional[str] = None

class EmpresaOut(EmpresaBase):
    nit: str
    documentos: List[EmpresaDocumentoOut] = []
    # vector_data: Optional[CompaniesOut] = None # Opcional, si quieres devolver info de la tabla companies

    class Config:
        from_attributes = True
