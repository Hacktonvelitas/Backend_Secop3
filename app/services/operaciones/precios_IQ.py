# app/services/operaciones/precios_IQ.py
"""
Price analysis service - analyzes market prices for company matches.
"""
from __future__ import annotations

import logging
import sys
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from sqlalchemy import text
from sqlalchemy.orm import Session

LOGGER = logging.getLogger("precios_iq")
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[precios_iq] %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel("INFO")


@dataclass
class MarketRangeResult:
    """Result of market price analysis."""
    nit: str
    total_matches: int
    stats: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)


def _calculate_stats(values: np.ndarray, alpha: float = 0.05) -> Dict[str, float]:
    """Calculate price statistics with percentiles."""
    if values.size == 0:
        return {"min": 0, "max": 0, "avg": 0, "median": 0, "p05": 0, "p95": 0}
    
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "avg": float(np.mean(values)),
        "median": float(np.median(values)),
        "p05": float(np.percentile(values, 5)),
        "p95": float(np.percentile(values, 95)),
        "std": float(np.std(values)),
        "count": int(values.size)
    }


def analizar_precios_empresa(
    session: Session,
    nit_empresa: str,
    top_k_analysis: int = 100,
    sector_keywords: Optional[List[str]] = None
) -> MarketRangeResult:
    """
    Analyze market prices for licitaciones matching a company profile.
    """
    
    LOGGER.info(f"Analyzing prices for NIT={nit_empresa}")
    
    # Get company embedding
    sql_company = text("""
        SELECT razon_social_embedding 
        FROM companies 
        WHERE nit = :nit
        LIMIT 1
    """)
    
    row = session.execute(sql_company, {"nit": nit_empresa.strip()}).fetchone()
    
    if not row or not row[0]:
        LOGGER.warning(f"Company {nit_empresa} not found or has no embedding")
        return MarketRangeResult(nit=nit_empresa, total_matches=0, stats={})
    
    company_embedding = row[0]
    
    # Build query with optional sector filter
    where_extra = ""
    params = {
        "company_vec": company_embedding,
        "limit": top_k_analysis
    }
    
    if sector_keywords:
        or_conds = []
        for i, kw in enumerate(sector_keywords):
            key = f"kw_{i}"
            or_conds.append(f"(l.act_econ ILIKE :{key} OR l.objeto ILIKE :{key})")
            params[key] = f"%{kw}%"
        where_extra = f"AND ({' OR '.join(or_conds)})"
    
    sql = text(f"""
        SELECT DISTINCT ON (l.id)
            l.id,
            l.cuantia,
            1 - (c.embedding_vec <=> CAST(:company_vec AS vector)) AS similarity
        FROM chunks c
        JOIN licitacion_keymap k ON k.lic_ext_id = c.lic_id
        JOIN licitacion l ON l.id = k.licitacion_id
        WHERE c.embedding_vec IS NOT NULL
          AND l.cuantia IS NOT NULL
          AND l.cuantia > 0
          {where_extra}
        ORDER BY l.id, similarity DESC
        LIMIT :limit
    """)
    
    rows = session.execute(sql, params).fetchall()
    
    if not rows:
        return MarketRangeResult(nit=nit_empresa, total_matches=0, stats={})
    
    cuantias = np.array([float(r.cuantia) for r in rows], dtype=float)
    
    stats = _calculate_stats(cuantias)
    
    return MarketRangeResult(
        nit=nit_empresa,
        total_matches=len(rows),
        stats=stats
    )