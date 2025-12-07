from __future__ import annotations
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.services.match_service import MatchService

LOGGER = logging.getLogger("price_service")

@dataclass
class MarketRangeResult:
    nit: str
    total_matches: int
    used_matches: int
    num_clusters: int
    cluster_stats: List[Dict[str, Any]]
    global_range: Dict[str, float]

class PriceService:
    def __init__(self, session: Session):
        self.session = session
        self.match_service = MatchService(session)

    def _calculate_bounds(self, values: np.ndarray, alpha: float = 0.05) -> Dict[str, float]:
        if values.size == 0:
            return {"min": 0, "max": 0, "avg": 0, "p05": 0, "p95": 0}
            
        p_lower = np.percentile(values, 100 * alpha)
        p_upper = np.percentile(values, 100 * (1 - alpha))
        
        return {
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "avg": float(np.mean(values)),
            "median": float(np.median(values)),
            "range_lower": float(p_lower),
            "range_upper": float(p_upper),
            "significance": float(alpha)
        }

    def analizar_precios_empresa(
        self, 
        nit_empresa: str,
        top_k_analysis: int = 100,
        n_clusters: int = 3,
        significance_alpha: float = 0.05,
        sector_keywords: Optional[List[str]] = None
    ) -> MarketRangeResult:
        
        LOGGER.info(f"Analizando precios para NIT={nit_empresa}, buscando {top_k_analysis} matches...")
        
        # Use MatchService to get opportunities
        matches = self.match_service.run_match_inicial(
            nit_empresa=nit_empresa,
            top_k=top_k_analysis,
            min_score=0.45,
            sector_keywords=sector_keywords
        )
        
        if not matches:
            return MarketRangeResult(nit_empresa, 0, 0, 0, [], {})

        # Extract Valid Data (Precios > 0)
        valid_cuantias = []
        
        for m in matches:
            c = m.get('cuantia', 0)
            if c and c > 0:
                valid_cuantias.append(c)
                
        if not valid_cuantias:
             return MarketRangeResult(nit_empresa, len(matches), 0, 0, [], {})

        values = np.array(valid_cuantias)
        
        # Simple Global Stats (Clustering removed for simplicity as we don't have vectors in result dicts easily available without extra query)
        # If clustering is needed, we'd need to fetch vectors in MatchService or here.
        # For now, we return global stats.
        
        global_stats = self._calculate_bounds(values, significance_alpha)
        
        return MarketRangeResult(
            nit=nit_empresa,
            total_matches=len(matches),
            used_matches=len(valid_cuantias),
            num_clusters=1,
            cluster_stats=[{"cluster_id": 0, "stats": global_stats, "count": len(valid_cuantias)}],
            global_range=global_stats
        )
