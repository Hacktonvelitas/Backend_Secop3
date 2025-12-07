# app/operaciones/match_augmented.py
# Este módulo se encarga de usar LLM (OpenAI) para re-rankear y verificar reglas complejas.
# Se basa en los resultados de match_inicial (Vectorial + Filtros Duros).

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Dict
from datetime import date
from dataclasses import dataclass, field, asdict

from sqlalchemy.orm import Session
from app.services.operaciones.match_inicial import obtener_oportunidades_empresa, MatchResult

# Si tienes un servicio de OpenAI configurado:
# from app.servicios.llm_service import analizar_match_con_gpt  (Ejemplo hipotético)
# Como no tengo acceso a tu libreria de LLM interna, simularé la llamada o asumiré una función simple.

LOGGER = logging.getLogger("match_augmented")
LOGGER.setLevel("INFO")

@dataclass
class AugmentedMatchResult:
    base_match: MatchResult
    ai_score: float = 0.0          # Score dado por el LLM (0.0 a 1.0)
    final_score: float = 0.0       # (base_score * 0.5) + (ai_score * 0.5)
    ai_explanation: str = ""       # Explicación del LLM
    cumple_requisitos: bool = True # Si el LLM detecta que NO cumple un requisito excluyente (e.g. Ubicación Negativa)

    def to_dict(self):
        d = asdict(self)
        # Manually convert base_match using its own to_dict to handle numpy arrays
        if self.base_match:
             d['base_match'] = self.base_match.to_dict()
        return d

def _mock_llm_analysis(empresa_nit: str, match: MatchResult) -> Tuple[float, str, bool]:
    """
    Simulación de llamada a OpenAI. 
    En producción, aquí envías el prompt con chunk_text y perfil de empresa.
    Retorna: (ai_score, explanation, cumple_requisitos)
    """
    # Lógica Dummy para probar el flujo sin gastar tokens reales en dev
    # Si la cuantía es alta, le damos mejor score :)
    ai_score = 0.7 
    if match.cuantia > 500_000_000:
        ai_score = 0.9
    
    explanation = "Análisis IA: El objeto parece compatible con el sector de la empresa."
    return ai_score, explanation, True

def obtener_match_augmented(
    session: Session, 
    nit_empresa: str, 
    fecha_inicio: Optional[date] = None,
    top_k: int = 10,  # Queremos devolver 10 finales
    min_score_inicial: float = 0.5,
    sector_filter: Optional[List[str]] = None,
    exclusion_filter: Optional[List[str]] = None,
    location_filter: Optional[str] = None,
    rango_cuantia: Optional[Tuple[float, float]] = None
) -> List[AugmentedMatchResult]:
    
    # 1. Obtener candidatos del Match Inicial (Hard Filters + Vectores)
    # Pedimos más candidatos (e.g. 3x top_k) para que el LLM tenga de donde filtrar
    candidates = obtener_oportunidades_empresa(
        session=session,
        nit_empresa=nit_empresa,
        fecha_inicio=fecha_inicio,
        top_k=top_k * 3, 
        min_score=min_score_inicial,
        sector_filter=sector_filter,
        exclusion_filter=exclusion_filter,
        location_filter=location_filter,
        rango_cuantia=rango_cuantia,
        n_clusters=1 # Clustering opcional aquí
    )
    
    if not candidates:
        LOGGER.info("No hay candidatos iniciales para análisis aumentado.")
        return []

    results_aug = []

    # 2. Análisis LLM por cada candidato (Costo en tiempo/dinero)
    # Idealmente usar asyncio.gather para hacerlo en paralelo.
    for cand in candidates:
        # LLAMADA A TU SERVICIO LLM
        # Prompt Idea: "Evalúa si la empresa con objetos X, Y... cumple requisitos Z de licitación..."
        # Prompt debe manejar Negaciones ("NO fuera de Bogota")
        
        ai_score, explanation, cumple = _mock_llm_analysis(nit_empresa, cand)
        
        if not cumple:
            # Si el LLM determina que viola una regla dura semántica (ej. "Experiencia en X pero NO en Y")
            # Lo descartamos o le ponemos score 0
            continue 

        # 3. Lógica de Scoring 50/50
        # Normalizar score inicial si viene > 1? Cosine sim max 1.
        base_score = cand.score
        
        # Formula solicitada por Usuario
        final_score = (base_score * 0.5) + (ai_score * 0.5)
        
        aug_res = AugmentedMatchResult(
            base_match=cand,
            ai_score=ai_score,
            final_score=final_score,
            ai_explanation=explanation,
            cumple_requisitos=cumple
        )
        results_aug.append(aug_res)

    # 4. Re-ordenar por Final Score
    results_aug.sort(key=lambda x: x.final_score, reverse=True)
    
    return results_aug[:top_k]