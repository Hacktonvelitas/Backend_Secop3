from typing import List, Optional
from datetime import date
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.match_service import MatchService
from app.services.price_service import PriceService

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
    service = MatchService(db)
    results = service.run_match_inicial(
        nit_empresa=body.nit_empresa,
        top_k=body.top_k,
        min_score=body.min_score,
        fecha_inicio=body.fecha_inicio,
        location_filter=body.location_filter,
        sector_keywords=body.sector_keywords,
        exclusion_keywords=body.exclusion_keywords,
        min_cuantia=body.min_cuantia,
        max_cuantia=body.max_cuantia
    )
    
    return results


@router.post("/match/augmented")
def match_augmented_endpoint(
    body: MatchRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el pipeline completo: 
    Match Inicial (Vectorial) -> Filtros IA Copilot -> Scoring 50/50.
    """
    service = MatchService(db)
    results = service.run_match_augmented(
        nit_empresa=body.nit_empresa,
        top_k=body.top_k,
        min_score_inicial=body.min_score,
        fecha_inicio=body.fecha_inicio,
        location_filter=body.location_filter,
        sector_keywords=body.sector_keywords,
        exclusion_keywords=body.exclusion_keywords,
        min_cuantia=body.min_cuantia,
        max_cuantia=body.max_cuantia
    )
    
    return results


@router.post("/analisis/precios")
def analisis_precios_endpoint(
    body: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analiza rangos de precios basados en oportunidades similares.
    """
    service = PriceService(db)
    result = service.analizar_precios_empresa(
        nit_empresa=body.nit_empresa,
        top_k_analysis=body.top_k,
        sector_keywords=body.sector_keywords
    )
    return asdict(result)
