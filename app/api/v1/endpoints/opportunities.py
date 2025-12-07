from typing import List, Optional
from datetime import date
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import get_db

# Import Legacy Operations
from app.services.operaciones.match_inicial import obtener_oportunidades_empresa
from app.services.operaciones.match_augmented import obtener_match_augmented
from app.services.operaciones.precios_IQ import analizar_precios_empresa

router = APIRouter()

# --- Request Schemas ---

class MatchRequest(BaseModel):
    nit_empresa: str
    fecha_inicio: Optional[date] = None
    top_k: int = 10
    min_score: float = 0.5
    
    # Niche Filters
    sector_keywords: Optional[List[str]] = None
    exclusion_keywords: Optional[List[str]] = None
    location_filter: Optional[str] = None
    
    # Cuantia Range (min, max)
    min_cuantia: Optional[float] = None
    max_cuantia: Optional[float] = None

class AnalysisRequest(BaseModel):
    nit_empresa: str
    top_k: int = 100
    sector_keywords: Optional[List[str]] = None

# --- Endpoints ---

@router.post("/match/inicial")
def match_inicial_endpoint(
    body: MatchRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el matching vectorial + filtros duros (Niche Filter).
    """
    # Prepare range tuple if both exist
    rango_cuantia = None
    if body.min_cuantia is not None and body.max_cuantia is not None:
        rango_cuantia = (body.min_cuantia, body.max_cuantia)

    results = obtener_oportunidades_empresa(
        session=db,
        nit_empresa=body.nit_empresa,
        fecha_inicio=body.fecha_inicio,
        top_k=body.top_k,
        min_score=body.min_score,
        sector_filter=body.sector_keywords,
        exclusion_filter=body.exclusion_keywords,
        location_filter=body.location_filter,
        rango_cuantia=rango_cuantia
    )
    
    # Convert dataclasses to dicts
    return [r.to_dict() for r in results]


@router.post("/match/augmented")
def match_augmented_endpoint(
    body: MatchRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el pipeline completo: 
    Match Inicial (Vectorial) -> Filtros IA Copilot -> Scoring 50/50.
    """
    # Prepare range tuple
    rango_cuantia = None
    if body.min_cuantia is not None and body.max_cuantia is not None:
        rango_cuantia = (body.min_cuantia, body.max_cuantia)

    results = obtener_match_augmented(
        session=db,
        nit_empresa=body.nit_empresa,
        fecha_inicio=body.fecha_inicio,
        top_k=body.top_k,
        min_score_inicial=body.min_score,
        sector_filter=body.sector_keywords,
        exclusion_filter=body.exclusion_keywords,
        location_filter=body.location_filter,
        rango_cuantia=rango_cuantia
    )
    
    # Convert dataclasses to dicts
    # Convert dataclasses to dicts
    return [r.to_dict() for r in results]


@router.post("/analisis/precios")
def analisis_precios_endpoint(
    body: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analiza rangos de precios basados en oportunidades similares.
    """
    result = analizar_precios_empresa(
        session=db,
        nit_empresa=body.nit_empresa,
        top_k_analysis=body.top_k,
        sector_keywords=body.sector_keywords
    )
    return asdict(result)
