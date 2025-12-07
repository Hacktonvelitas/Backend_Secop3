# app/services/operaciones/match_augmented.py
"""
Augmented match service - uses LLM scoring on top of vector similarity.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple
from datetime import date
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from app.services.operaciones.match_inicial import obtener_oportunidades_empresa, MatchResult

LOGGER = logging.getLogger("match_augmented")
LOGGER.setLevel("INFO")


@dataclass
class AugmentedMatchResult:
    """Match result with AI scoring."""
    licitacion_id: int
    score: float
    ai_score: float
    final_score: float
    chunk_text: str
    entidad: str
    objeto: str
    cuantia: float
    fecha_public: str
    ubicacion: str
    modalidad: str
    ai_explanation: str = ""


def _mock_llm_analysis(nit: str, match: MatchResult) -> Tuple[float, str, bool]:
    """
    Mock LLM analysis - in production, call OpenAI/Gemini.
    Returns: (ai_score, explanation, cumple_requisitos)
    """
    ai_score = 0.7
    if match.cuantia > 500_000_000:
        ai_score = 0.9
    elif match.cuantia > 100_000_000:
        ai_score = 0.8
    
    explanation = "Análisis IA: El objeto parece compatible con el sector de la empresa."
    return ai_score, explanation, True


def obtener_match_augmented(
    session: Session,
    nit_empresa: str,
    fecha_inicio: Optional[date] = None,
    top_k: int = 10,
    min_score_inicial: float = 0.5,
    sector_filter: Optional[List[str]] = None,
    exclusion_filter: Optional[List[str]] = None,
    location_filter: Optional[str] = None,
    rango_cuantia: Optional[Tuple[float, float]] = None
) -> List[AugmentedMatchResult]:
    """
    Get matches with AI-enhanced scoring (50% vector + 50% AI).
    """
    
    # Get initial matches
    candidates = obtener_oportunidades_empresa(
        session=session,
        nit_empresa=nit_empresa,
        fecha_inicio=fecha_inicio,
        top_k=top_k * 3,
        min_score=min_score_inicial,
        sector_filter=sector_filter,
        exclusion_filter=exclusion_filter,
        location_filter=location_filter,
        rango_cuantia=rango_cuantia
    )
    
    if not candidates:
        LOGGER.info("No initial candidates for augmented matching.")
        return []
    
    results = []
    
    for match in candidates:
        ai_score, explanation, cumple = _mock_llm_analysis(nit_empresa, match)
        
        if not cumple:
            continue
        
        # 50/50 scoring
        final_score = (match.score * 0.5) + (ai_score * 0.5)
        
        results.append(AugmentedMatchResult(
            licitacion_id=match.licitacion_id,
            score=match.score,
            ai_score=ai_score,
            final_score=final_score,
            chunk_text=match.chunk_text,
            entidad=match.entidad,
            objeto=match.objeto,
            cuantia=match.cuantia,
            fecha_public=match.fecha_public,
            ubicacion=match.ubicacion,
            modalidad=match.modalidad,
            ai_explanation=explanation
        ))
    
    # Sort by final score
    results.sort(key=lambda x: x.final_score, reverse=True)
    
    return results[:top_k]