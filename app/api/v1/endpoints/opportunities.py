from typing import List, Optional
from datetime import date
from dataclasses import asdict
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db
# Importamos los servicios existentes
from app.services.operaciones.match_inicial import obtener_oportunidades_empresa
# IMPORTANTE: Importamos los nuevos servicios
from app.services.operaciones.match_augmented import obtener_match_augmented
from app.services.operaciones.precios_IQ import analizar_precios_empresa

router = APIRouter()

# --- 1. MATCH BÁSICO (Ya lo tenías) ---
@router.get("/{nit}/match")
def match_by_nit(
    nit: str = Path(..., description="NIT de la empresa"),
    top_k: int = Query(10, ge=1, le=100),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    fecha_inicio: Optional[date] = Query(None),
    sector_keywords: Optional[str] = Query(None),
    exclusion_keywords: Optional[str] = Query(None),
    location_filter: Optional[str] = Query(None),
    min_cuantia: Optional[float] = Query(None),
    max_cuantia: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    sector_list = [k.strip() for k in sector_keywords.split(",")] if sector_keywords else None
    exclusion_list = [k.strip() for k in exclusion_keywords.split(",")] if exclusion_keywords else None
    rango_cuantia = (min_cuantia, max_cuantia) if min_cuantia and max_cuantia else None
    
    results = obtener_oportunidades_empresa(
        session=db, nit_empresa=nit, fecha_inicio=fecha_inicio, top_k=top_k,
        min_score=min_score, sector_filter=sector_list, exclusion_filter=exclusion_list,
        location_filter=location_filter, rango_cuantia=rango_cuantia
    )
    return [r.to_dict() for r in results]

# --- 2. INFO EMPRESA (Ya lo tenías) ---
@router.get("/{nit}/company")
def get_company_info(
    nit: str = Path(..., description="NIT de la empresa"),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    sql = text("""
        SELECT nit, razon_social, muncomercial, ciiu1, 
               CASE WHEN razon_social_embedding IS NOT NULL THEN true ELSE false END as has_embedding
        FROM companies WHERE nit = :nit LIMIT 1
    """)
    row = db.execute(sql, {"nit": nit.strip()}).fetchone()
    if not row: return {"error": "Empresa no encontrada", "nit": nit}
    return {"nit": row.nit, "razon_social": row.razon_social, "municipio": row.muncomercial, "has_embedding": row.has_embedding}

# --- 3. NUEVO: MATCH AUGMENTED (IA Scoring) ---
@router.get("/{nit}/match-ai")
def match_augmented_by_nit(
    nit: str = Path(...),
    top_k: int = Query(10),
    min_score: float = Query(0.5),
    sector_keywords: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Match avanzado que usa un 'Mock LLM' para re-evaluar la relevancia.
    """
    sector_list = [k.strip() for k in sector_keywords.split(",")] if sector_keywords else None
    
    results = obtener_match_augmented(
        session=db,
        nit_empresa=nit,
        top_k=top_k,
        min_score_inicial=min_score,
        sector_filter=sector_list
    )
    return [asdict(r) for r in results] # Dataclass a dict

# --- 4. NUEVO: PRECIOS IQ (Análisis de Mercado) ---
@router.get("/{nit}/market-analysis")
def market_analysis(
    nit: str = Path(...),
    top_k_analysis: int = Query(50, description="Cuantas licitaciones usar para el análisis"),
    sector_keywords: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Analiza estadísticas de precios (min, max, promedio) de licitaciones similares.
    """
    sector_list = [k.strip() for k in sector_keywords.split(",")] if sector_keywords else None
    
    result = analizar_precios_empresa(
        session=db,
        nit_empresa=nit,
        top_k_analysis=top_k_analysis,
        sector_keywords=sector_list
    )
    return result.to_dict()