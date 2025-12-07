from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Tuple
from datetime import date
from dataclasses import asdict
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.match_service import MatchService
from app.services.price_service import PriceService

# Existing AI imports
from app.IA.query_data import process_query
from app.IA.red_contac import process_query_graph

router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
)

# ----------------------------------------------------
# SCHEMAS
# ----------------------------------------------------

class MatchRequest(BaseModel):
    nit_empresa: str
    fecha_inicio: Optional[date] = None
    top_k: int = 10
    min_score: float = 0.5
    
    # Niche Filters
    sector_keywords: Optional[List[str]] = None      # e.g. ["Salud", "Hospital"]
    exclusion_keywords: Optional[List[str]] = None   # e.g. ["Aseo", "Vigilancia"]
    location_filter: Optional[str] = None            # e.g. "Bogota"
    
    # Cuantia Range (min, max)
    min_cuantia: Optional[float] = None
    max_cuantia: Optional[float] = None

class AIQueryRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    debug: Optional[bool] = False

class GraphQuery(BaseModel):
    query_text: str
    debug: bool = False

# ----------------------------------------------------
# MATCH ROUTES
# ----------------------------------------------------

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


# ----------------------------------------------------
# PRECIOS ENDPOINT
# ----------------------------------------------------

class AnalysisRequest(BaseModel):
    nit_empresa: str
    top_k: int = 100
    sector_keywords: Optional[List[str]] = None

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



# ----------------------------------------------------
# AI ROUTES (Keep legacy paths compatible)
# ----------------------------------------------------

@router.post("/ai/query")
def ai_query_old_path(payload: AIQueryRequest):
    # Mapping old path to new structure if needed, or just keeping it
    if not payload.prompt:
        raise HTTPException(status_code=400, detail="Prompt required")
    return process_query(payload.prompt, session_id=payload.session_id, debug=payload.debug)

@router.post("/ai/graphs/assistant")
def graphs_assistant_old_path(body: GraphQuery):
    return process_query_graph(body.query_text, debug=body.debug)
