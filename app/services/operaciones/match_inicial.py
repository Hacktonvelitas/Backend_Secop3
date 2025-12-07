# app/services/operaciones/match_inicial.py
"""
Match service for finding licitaciones that match a company's profile.
Uses cosine similarity between company embeddings and chunk embeddings.
"""
from __future__ import annotations

import logging
import sys
from typing import List, Optional, Tuple
from datetime import date
from dataclasses import dataclass, asdict

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

LOGGER = logging.getLogger(__name__)

if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[match_empresa] %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel("INFO")


@dataclass
class MatchResult:
    """Result of a match between a company and a licitacion chunk."""
    licitacion_id: int
    score: float
    chunk_text: str
    entidad: str
    objeto: str
    cuantia: float
    fecha_public: str
    ubicacion: str
    modalidad: str

    def to_dict(self):
        return asdict(self)


def _fetch_company_embedding(session: Session, nit: str) -> Optional[str]:
    """
    Get the razon_social_embedding for a company by NIT.
    """
    clean_nit = nit.replace("-", "").replace(" ", "").strip()
    
    sql = text("""
        SELECT razon_social_embedding 
        FROM companies 
        WHERE nit = :nit
        LIMIT 1
    """)
    
    row = session.execute(sql, {"nit": clean_nit}).fetchone()
    
    if row and row[0] is not None:
        return row[0]
    
    LOGGER.warning(f"Company NIT {clean_nit} not found or has no embedding.")
    return None


def _search_matching_chunks(
    session: Session,
    company_embedding: str,
    top_k: int = 20,
    min_score: float = 0.5,
    fecha_inicio: Optional[date] = None,
    location_filter: Optional[str] = None,
    sector_keywords: Optional[List[str]] = None,
    exclusion_keywords: Optional[List[str]] = None,
    min_cuantia: Optional[float] = None,
    max_cuantia: Optional[float] = None
) -> List[MatchResult]:
    """
    Search for chunks that match the company embedding using cosine similarity.
    Joins through licitacion_keymap to get licitacion metadata.
    """
    
    # Build WHERE clauses
    where_clauses = ["c.embedding_vec IS NOT NULL"]
    params = {
        "company_vec": company_embedding,
        "min_sim": min_score,
        "limit": top_k * 3  # Get more to allow filtering
    }
    
    # Date filter
    if fecha_inicio:
        where_clauses.append("l.fecha_public >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio
    
    # Location filter
    if location_filter:
        where_clauses.append("l.ubicacion ILIKE :loc")
        params["loc"] = f"%{location_filter}%"
    
    # Cuantia range
    if min_cuantia is not None:
        where_clauses.append("l.cuantia >= :min_cuantia")
        params["min_cuantia"] = min_cuantia
    if max_cuantia is not None:
        where_clauses.append("l.cuantia <= :max_cuantia")
        params["max_cuantia"] = max_cuantia
    
    # Sector keywords (positive filter)
    if sector_keywords:
        or_conds = []
        for i, kw in enumerate(sector_keywords):
            key = f"kw_inc_{i}"
            or_conds.append(f"(l.act_econ ILIKE :{key} OR l.objeto ILIKE :{key})")
            params[key] = f"%{kw}%"
        if or_conds:
            where_clauses.append(f"({' OR '.join(or_conds)})")
    
    # Exclusion keywords (negative filter)
    if exclusion_keywords:
        for i, kw in enumerate(exclusion_keywords):
            key = f"kw_exc_{i}"
            where_clauses.append(f"l.objeto NOT ILIKE :{key}")
            params[key] = f"%{kw}%"
    
    sql = f"""
        SELECT DISTINCT ON (l.id)
            l.id AS licitacion_id,
            1 - (c.embedding_vec <=> CAST(:company_vec AS vector)) AS similarity,
            c.text AS chunk_text,
            l.entidad,
            l.objeto,
            l.cuantia,
            l.fecha_public,
            l.ubicacion,
            l.modalidad
        FROM chunks c
        JOIN licitacion_keymap k ON k.lic_ext_id = c.lic_id
        JOIN licitacion l ON l.id = k.licitacion_id
        WHERE {" AND ".join(where_clauses)}
          AND 1 - (c.embedding_vec <=> CAST(:company_vec AS vector)) >= :min_sim
        ORDER BY l.id, similarity DESC
    """
    
    # Wrap to order by similarity globally
    sql = f"""
        SELECT * FROM ({sql}) sub
        ORDER BY similarity DESC
        LIMIT :limit
    """
    
    rows = session.execute(text(sql), params).fetchall()
    
    results = []
    for row in rows:
        results.append(MatchResult(
            licitacion_id=row.licitacion_id,
            score=float(row.similarity),
            chunk_text=row.chunk_text or "",
            entidad=row.entidad or "",
            objeto=row.objeto or "",
            cuantia=float(row.cuantia) if row.cuantia else 0.0,
            fecha_public=str(row.fecha_public) if row.fecha_public else "",
            ubicacion=row.ubicacion or "",
            modalidad=row.modalidad or ""
        ))
    
    return results[:top_k]


def obtener_oportunidades_empresa(
    session: Session,
    nit_empresa: str,
    fecha_inicio: Optional[date] = None,
    top_k: int = 20,
    min_score: float = 0.5,
    sector_filter: Optional[List[str]] = None,
    exclusion_filter: Optional[List[str]] = None,
    location_filter: Optional[str] = None,
    rango_cuantia: Optional[Tuple[float, float]] = None
) -> List[MatchResult]:
    """
    Main function to get matching opportunities for a company by NIT.
    """
    
    # 1. Get company embedding
    company_embedding = _fetch_company_embedding(session, nit_empresa)
    if not company_embedding:
        return []
    
    # Unpack cuantia range
    min_c, max_c = (None, None)
    if rango_cuantia:
        min_c, max_c = rango_cuantia
    
    # 2. Search matching chunks
    matches = _search_matching_chunks(
        session=session,
        company_embedding=company_embedding,
        top_k=top_k,
        min_score=min_score,
        fecha_inicio=fecha_inicio,
        location_filter=location_filter,
        sector_keywords=sector_filter,
        exclusion_keywords=exclusion_filter,
        min_cuantia=min_c,
        max_cuantia=max_c
    )
    
    LOGGER.info(f"Found {len(matches)} matches for NIT {nit_empresa}")
    return matches