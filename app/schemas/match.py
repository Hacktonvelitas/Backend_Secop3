from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# --- Match Result ---
class MatchResultBase(BaseModel):
    score_similitud: Optional[float] = None
    cluster_asignado: Optional[int] = None
    estado_revision: Optional[str] = "pendiente"
    comentario_usuario: Optional[str] = None

class MatchResultUpdate(BaseModel):
    estado_revision: Optional[str] = None
    comentario_usuario: Optional[str] = None

class MatchResultOut(MatchResultBase):
    id: int
    run_id: Optional[int] = None
    licitacion_id: Optional[int] = None
    
    class Config:
        from_attributes = True

# --- Match Run ---
class MatchRunBase(BaseModel):
    filtros_usados: Optional[Dict[str, Any]] = None
    total_encontrados: Optional[int] = None

class MatchRunCreate(MatchRunBase):
    empresa_nit: Optional[str] = None

class MatchRunOut(MatchRunBase):
    run_id: int
    empresa_nit: Optional[str] = None
    fecha_ejecucion: Optional[datetime] = None
    results: List[MatchResultOut] = []

    class Config:
        from_attributes = True
