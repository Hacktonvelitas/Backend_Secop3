# app/operaciones/match_inicial.py
from __future__ import annotations

import logging
import sys
import numpy as np
from typing import List, Optional, Tuple, Dict
from datetime import date
from dataclasses import dataclass, asdict

from sqlalchemy import text
from sqlalchemy.orm import Session
import os
import traceback

LOGGER = logging.getLogger("match_empresa")
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[match_empresa] %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel("INFO")
# Configuration flag for optional LLM fallback when DB returns no matches
USE_LLM_FALLBACK = os.getenv('USE_LLM_FALLBACK', 'true').lower() == 'true'

# ============================================================
# DTOs
# ============================================================

@dataclass
class MatchResult:
    licitacion_id: int
    score: float          
    best_chunk_text: str  
    entidad: str
    objeto: str
    cuantia: float        
    fecha_public: str     
    cluster_id: int = -1
    vector_licitacion: Optional[np.ndarray] = None 

    def to_dict(self):
        d = asdict(self)
        if 'vector_licitacion' in d:
             del d['vector_licitacion']
        return d

# ============================================================
# Helpers
# ============================================================

def _to_np_vec(v) -> Optional[np.ndarray]:
    """Convierte la salida de pgvector a numpy array."""
    if v is None: return None
    if isinstance(v, str):
        # pgvector a veces devuelve string "[0.1, ...]"
        s = v.strip().lstrip("[").rstrip("]")
        try:
             return np.fromstring(s, sep=",", dtype=np.float32)
        except: return None
    return np.array(v, dtype=np.float32)

# ============================================================
# Core Logic
# ============================================================

def _fetch_empresa_vector(session: Session, nit: str) -> Optional[str]:
    """Fetch the company's vector using a fresh DB connection to avoid transaction issues.
    Tries empresa_info first, then companies.
    """
    from sqlalchemy import create_engine, text
    import os
    clean_nit = nit.replace("-", "").replace(" ", "")
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        # Try empresa_info
        try:
            row = conn.execute(text("SELECT razon_social_vec FROM public.empresa_info WHERE nit = :nit"), {"nit": clean_nit}).fetchone()
            if row and row[0] is not None:
                return row[0]
        except Exception as e:
            LOGGER.warning(f"Error consulting empresa_info: {e}. Trying companies...")
        # Try companies
        try:
            row2 = conn.execute(text("SELECT razon_social_embedding FROM public.companies WHERE nit = :nit"), {"nit": clean_nit}).fetchone()
            if row2 and row2[0] is not None:
                return row2[0]
        except Exception as e:
            LOGGER.warning(f"Error consulting companies: {e}")
    LOGGER.warning(f"Empresa NIT {clean_nit} sin vector encontrado.")
    return None

def _search_vectors_in_db(
    session: Session, 
    empresa_vec_str: str,
    limit: int = 100,
    min_score: float = 0.6,
    fecha_inicio: Optional[date] = None,
    location_filter: Optional[str] = None,
    sector_keywords: Optional[List[str]] = None,
    exclusion_keywords: Optional[List[str]] = None,
    min_cuantia: Optional[float] = None,
    max_cuantia: Optional[float] = None
) -> List[MatchResult]:
    
    # Construcción dinámica de filtros WHERE
    where_clauses = ["c.embedding_vec IS NOT NULL"]
    params = {
        "query_vec": empresa_vec_str, 
        "limit": limit,
        "min_sim": min_score
    }

    # 1. Filtro Fecha
    if fecha_inicio:
        where_clauses.append("l.fecha_public >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio

    # 2. Filtro Ubicación
    if location_filter:
        where_clauses.append("l.ubicacion ILIKE :loc")
        params["loc"] = f"%{location_filter}%"

    # 3. Filtro Presupuesto (Cuantía)
    if min_cuantia:
        where_clauses.append("l.cuantia >= :min_cuantia")
        params["min_cuantia"] = min_cuantia
    if max_cuantia:
        where_clauses.append("l.cuantia <= :max_cuantia")
        params["max_cuantia"] = max_cuantia

    # 4. Filtro Palabras Clave Positivas (Sector)
    if sector_keywords:
        or_conds = []
        for i, kw in enumerate(sector_keywords):
            key = f"kw_inc_{i}"
            # Buscamos en Actividad Económica u Objeto
            or_conds.append(f"(l.act_econ ILIKE :{key} OR l.objeto ILIKE :{key})")
            params[key] = f"%{kw}%"
        if or_conds:
            where_clauses.append(f"({' OR '.join(or_conds)})")

    # 5. Filtro Palabras Clave NEGATIVAS (Exclusión)
    if exclusion_keywords:
        for i, kw in enumerate(exclusion_keywords):
            key = f"kw_exc_{i}"
            where_clauses.append(f"l.objeto NOT ILIKE :{key}")
            # Tambien excluir si está en el chunk de texto encontrado
            where_clauses.append(f"c.chunk_text NOT ILIKE :{key}") 
            params[key] = f"%{kw}%"

    # Query optimizada con operador <=> (Cosine Distance)
    # Nota: 1 - (vec <=> vec) convierte la distancia en similitud (0 a 1)
    sql = f"""
        SELECT 
            c.lic_id as licitacion_id,
            c.text as chunk_text,
            c.embedding_vec,
            (1 - (c.embedding_vec <-> (:query_vec)::vector)) as similarity,
            l.entidad,
            l.objeto,
            l.cuantia,
            l.fecha_public
        FROM public.chunks c
        JOIN public.licitacion l ON c.lic_id::int = l.id
        WHERE {" AND ".join(where_clauses)}
          AND (1 - (c.embedding_vec <-> (:query_vec)::vector)) >= :min_sim
        ORDER BY similarity DESC
        LIMIT :limit;
    """

    try:
        rows = session.execute(text(sql), params).fetchall()
    except Exception as e:
        LOGGER.error(f"Error executing vector search query: {e}\n{traceback.format_exc()}")
        rows = []
    
    results = []
    seen_ids = set()

    for lid, txt, vec_raw, score, ent, obj, cuant, fecha in rows:
        if lid in seen_ids:
            continue
        seen_ids.add(lid)

        results.append(MatchResult(
            licitacion_id=lid,
            score=float(score),
            best_chunk_text=txt,
            entidad=ent,
            objeto=obj,
            cuantia=float(cuant) if cuant else 0.0,
            fecha_public=str(fecha) if fecha else None,
            vector_licitacion=_to_np_vec(vec_raw)
        ))
        
    return results

# ============================================================
# Función Principal
# ============================================================

def obtener_oportunidades_empresa(
    session: Session, 
    nit_empresa: str, 
    fecha_inicio: Optional[date] = None,
    top_k: int = 20, 
    min_score: float = 0.5,
    n_clusters: int = 3,
    sector_filter: Optional[List[str]] = None,     # Ej: ['Tecnología', 'Software']
    exclusion_filter: Optional[List[str]] = None,  # Ej: ['Aseo', 'Cafetería', 'Obra Civil']
    location_filter: Optional[str] = None,
    rango_cuantia: Optional[Tuple[float, float]] = None # Ej: (100M, 5000M)
) -> List[MatchResult]:
    
    # 1. Obtener Vector
    empresa_vec_str = _fetch_empresa_vector(session, nit_empresa)
    if not empresa_vec_str:
        return []

    # Desempaquetar rango cuantía
    min_c, max_c = (None, None)
    if rango_cuantia:
        min_c, max_c = rango_cuantia

    # 2. Búsqueda Vectorial Híbrida en DB (Semántica + Filtros)
    matches = _search_vectors_in_db(
        session=session,
        empresa_vec_str=empresa_vec_str,
        limit=top_k * 2, # Traemos un poco más para tener margen en clustering
        min_score=min_score,
        fecha_inicio=fecha_inicio,
        location_filter=location_filter,
        sector_keywords=sector_filter,
        exclusion_keywords=exclusion_filter,
        min_cuantia=min_c,
        max_cuantia=max_c
    )
    
    LOGGER.info(f"Matches encontrados para NIT {nit_empresa}: {len(matches)}")

    # If no matches and fallback enabled, attempt LLM fallback
    if not matches and USE_LLM_FALLBACK:
        try:
            matches = _fallback_llm_match(nit_empresa, top_k)
            LOGGER.info("LLM fallback provided %d matches", len(matches))
        except Exception as e:
            LOGGER.error(f"LLM fallback failed: {e}\n{traceback.format_exc()}")
    if not matches:
        return []
    # Recortar al top_k solicitado
    matches = matches[:top_k]

    # 3. Clustering (K-Means)
    # Agrupa los resultados por similitud temática visual
    if len(matches) >= n_clusters:
        try:
            vecs = [m.vector_licitacion for m in matches if m.vector_licitacion is not None]
            if len(vecs) >= n_clusters:
                X = np.vstack(vecs)
                # Validamos que no haya NaNs
                X = np.nan_to_num(X)
                
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = kmeans.fit_predict(X)
                
                for i, m in enumerate(matches):
                    m.cluster_id = int(labels[i])
        except Exception as e:
            LOGGER.error(f"Error en clustering: {e}")

    return matches

# ---------------------------------------------------------------------------
# Optional LLM fallback implementation (placeholder)
# ---------------------------------------------------------------------------

def _fallback_llm_match(nit: str, top_k: int) -> List[MatchResult]:
    """Generate synthetic matches using an LLM when the DB returns none.
    This is a minimal stub; in a real implementation you would call the
    Gemini or OpenAI API to embed the company name and retrieve similar
    opportunities from an external source or a pre‑computed index.
    """
    # Placeholder implementation: return empty list
    return []