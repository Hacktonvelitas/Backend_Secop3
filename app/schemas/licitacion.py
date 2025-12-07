from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# --- Sub-schemas ---

class LicitacionCriterioBase(BaseModel):
    nombre_criterio: Optional[str] = None
    tipo_criterio: Optional[str] = None
    puntaje_maximo: Optional[int] = None
    descripcion_regla: Optional[str] = None

class LicitacionCriterioOut(LicitacionCriterioBase):
    id: int
    licitacion_id: int
    class Config:
        from_attributes = True

class LicitacionObservacionBase(BaseModel):
    fecha_observacion: Optional[datetime] = None
    texto_pregunta: Optional[str] = None
    texto_respuesta: Optional[str] = None
    cambio_requisito: bool = False

class LicitacionObservacionOut(LicitacionObservacionBase):
    id: int
    licitacion_id: int
    class Config:
        from_attributes = True

class LicitacionDocumentoBase(BaseModel):
    nombre_archivo: Optional[str] = None
    tipo_contenido: Optional[str] = None
    url_archivo: Optional[str] = None
    procesado_ia: bool = False

class LicitacionDocumentoOut(LicitacionDocumentoBase):
    id: int
    licitacion_id: int
    class Config:
        from_attributes = True

# --- Licitacion Schemas ---

class LicitacionBase(BaseModel):
    entidad: str
    objeto: Optional[str] = None
    descripcion_general: Optional[str] = None
    modalidad: Optional[str] = None
    tipo_seleccion: Optional[str] = None
    fundamento_legal: Optional[str] = None
    ubicacion: Optional[str] = None
    enlace: Optional[str] = None
    estado: Optional[str] = None
    
    cuantia: Optional[float] = None
    valor_estimado_iva: Optional[float] = None
    presupuesto_ms_oficial: Optional[float] = None
    presupuesto_dc_oficial: Optional[float] = None
    
    fecha_public: Optional[date] = None
    fecha_visita_obra: Optional[datetime] = None
    fecha_cierre_oferta: Optional[datetime] = None
    fecha_adjudicacion_prog: Optional[date] = None
    plazo_meses: Optional[int] = None
    
    codigos_unspsc: Optional[List[str]] = None
    act_econ: Optional[str] = None
    
    req_cert_9001: bool = False
    req_cert_27001: bool = False

class LicitacionCreate(LicitacionBase):
    codigo_proceso: Optional[str] = None

class LicitacionUpdate(LicitacionBase):
    pass

class LicitacionOut(LicitacionBase):
    id: int
    codigo_proceso: Optional[str] = None
    
    criterios: List[LicitacionCriterioOut] = []
    observaciones: List[LicitacionObservacionOut] = []
    documentos: List[LicitacionDocumentoOut] = []
    
    class Config:
        from_attributes = True
