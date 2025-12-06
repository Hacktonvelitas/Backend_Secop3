# app/operaciones/match_augmented.py
from __future__ import annotations

import logging
import sys
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date

import match_inicial as match_i

# ============================================================
# LOGGING
# ============================================================
LOGGER = logging.getLogger("match_augmented")
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[match_augmented] %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel("INFO")

# ============================================================
# Helpers
# ============================================================

def _fetch_empresa_tags(session: Session, nit: str) -> List[str]:
    """
    Recupera 'labels' o 'tags' de la empresa para el matching aumentado.
    En el nuevo schema, usaremos `empresa_experiencia.tech_stack_tags` y `equipo_tech_skills`.
    Se consolidan en una lista única de strings.
    """
    clean_nit = nit.replace("-", "").replace(" ", "")
    tags = set()

    # 1. Tags de Experiencia (Proyectos previos)
    try:
        rows = session.execute(text("""
            SELECT tech_stack_tags 
            FROM public.empresa_experiencia 
            WHERE empresa_nit = :nit
        """), {"nit": clean_nit}).fetchall()
        
        for (tag_list,) in rows:
            if tag_list:
                for t in tag_list:
                    if t: tags.add(t.lower())

        # 2. Skills del Equipo (opcional, si queremos hilar fino)
        # rows_skills = session.execute(text("""
        #     SELECT ts.tecnologia 
        #     FROM public.empresa_equipo e
        #     JOIN public.equipo_tech_skills ts ON ts.equipo_id = e.id
        #     WHERE e.empresa_nit = :nit
        # """), {"nit": clean_nit}).fetchall()
        # for (tech,) in rows_skills:
        #    if tech: tags.add(tech.lower())

    except Exception as e:
        LOGGER.error(f"Error fetching tags for {nit}: {e}")

    return list(tags)

def _calculate_tag_match_score(match_text: str, tags: List[str]) -> float:
    """
    Calcula un score simple basado en cuántos tags aparecen en el texto del chunk/licitación.
    Podría ser mejorado con embedding matching si los tags tuvieran vectores.
    Aquí hacemos string matching simple "tag IN text".
    """
    if not tags or not match_text:
        return 0.0
    
    text_lower = match_text.lower()
    hits = 0
    for tag in tags:
        if tag in text_lower:
            hits += 1
            
    # Heurística: cada hit suma 0.1, tope 0.5 de boost?
    # O normalizar por len(tags)?
    # Vamos a sumar 0.05 por cada tag encontrado.
    return min(hits * 0.05, 0.5) 

# ============================================================
# Función Principal
# ============================================================

def obtener_match_augmented(
    session: Session, 
    nit_empresa: str,
    etiquetas_override: Optional[List[str]] = None, # Si vienen del front
    fecha_inicio: Optional[date] = None,
    top_k: int = 50, # Pedimos más match inicial para filtrar luego
    final_k: int = 20
) -> List[Dict]:
    """
    1. Llama match_inicial con un top_k amplio.
    2. Busca etiquetas de la empresa (o usa override).
    3. Re-rankea resultados sumando score de etiquetas.
    """
    
    # 1. Match Inicial
    LOGGER.info(f"Ejecutando Match Inicial para {nit_empresa}...")
    base_matches = match_i.obtener_oportunidades_empresa(
        session=session,
        nit_empresa=nit_empresa,
        fecha_inicio=fecha_inicio,
        top_k=top_k, 
        min_score=0.4 # Un poco mas permisivo para dejar entrar cosas que los tags suban
    )
    
    if not base_matches:
        return []

    # 2. Obtener Tags
    if etiquet_override:
        params_tags = [t.lower() for t in etiquet_override]
        LOGGER.info(f"Usando etiquetas override: {len(params_tags)}")
    else:
        params_tags = _fetch_empresa_tags(session, nit_empresa)
        LOGGER.info(f"Etiquetas encontradas en DB para {nit_empresa}: {len(params_tags)} ({params_tags})")

    # 3. Re-Ranking (Augmented)
    augmented_results = []
    
    for m in base_matches:
        # Score base (vectorial)
        base_score = m.score
        
        # Boost por tags
        tag_boost = _calculate_tag_match_score(m.best_chunk_text + " " + (m.objeto or ""), params_tags)
        
        final_score = base_score + tag_boost
        
        # Convertimos a dict y agregamos metadatos de debug
        d = m.to_dict()
        d['score_base'] = base_score
        d['score_tags'] = tag_boost
        d['score_total'] = final_score
        d['matched_tags'] = [t for t in params_tags if t in (m.best_chunk_text + " " + (m.objeto or "")).lower()]
        
        augmented_results.append(d)
        
    # Ordenar por score total
    augmented_results.sort(key=lambda x: x['score_total'], reverse=True)
    
    # Cortar a final_k
    final_results = augmented_results[:final_k]
    
    LOGGER.info(f"Match Augmented finalizado. Retornando {len(final_results)} resultados.")
    return final_results