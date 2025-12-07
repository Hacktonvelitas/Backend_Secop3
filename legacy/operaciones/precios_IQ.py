# app/operaciones/precios_IQ.py
from __future__ import annotations

import logging
import sys
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sklearn.cluster import KMeans

# Using absolute import to be safe or relative if package refactored
from app.operaciones import match_inicial as match_i

# ============================================================
# LOGGING
# ============================================================
LOGGER = logging.getLogger("precios_iq")
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[precios_iq] %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel("INFO")


@dataclass
class MarketRangeResult:
    nit: str
    total_matches: int
    used_matches: int
    num_clusters: int
    cluster_stats: List[Dict[str, Any]]
    global_range: Dict[str, float]


def _calculate_bounds(values: np.ndarray, alpha: float = 0.05) -> Dict[str, float]:
    """
    Calcula media, mediana y rango con significancia alpha.
    alpha=0.05 => percentiles 5% y 95%.
    """
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
    session: Session, 
    nit_empresa: str,
    top_k_analysis: int = 100,
    n_clusters: int = 3,
    significance_alpha: float = 0.05,
    sector_keywords: Optional[List[str]] = None
) -> MarketRangeResult:
    """
    1. Obtiene matches de la empresa (top_k amplio).
    2. Agrupa licitaciones similares (KMeans sobre embeddings).
    3. Calcula estadisticas de precio para cada cluster.
    """
    
    # 1. Traer datos
    LOGGER.info(f"Analizando precios para NIT={nit_empresa}, buscando {top_k_analysis} matches...")
    
    # Passing new args to match_inicial
    matches = match_i.obtener_oportunidades_empresa(
        session=session,
        nit_empresa=nit_empresa,
        top_k=top_k_analysis,
        min_score=0.45, # Score razonable para análisis de mercado
        n_clusters=1,    # Ignoramos clustering inicial
        sector_filter=sector_keywords,
        # Defaulting other filters to None
    )
    
    if not matches:
        return MarketRangeResult(nit_empresa, 0, 0, 0, [], {})

    # 2. Extract Valid Data (Precios > 0)
    valid_data = []
    vectors = []
    
    for m in matches:
        # Check nulls for cuantia (it is optional now in schema)
        if m.cuantia and m.cuantia > 0 and m.vector_licitacion is not None:
            valid_data.append(m)
            vectors.append(m.vector_licitacion)
            
    if not valid_data:
        LOGGER.warning("Matches encontrados pero sin cuantía válida o vector.")
        return MarketRangeResult(nit_empresa, len(matches), 0, 0, [], {})

    X = np.vstack(vectors)
    X = np.nan_to_num(X) # Safety check
    
    # 3. Clustering
    # Si hay pocos datos, ajustamos k
    real_k = min(n_clusters, len(valid_data))
    if real_k < 2:
        labels = np.zeros(len(valid_data), dtype=int)
        real_k = 1
    else:
        kmeans = KMeans(n_clusters=real_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)

    # 4. Stats per Cluster
    clusters_info = []
    all_prices = []

    for k in range(real_k):
        # Indices de este cluster
        idxs = np.where(labels == k)[0]
        if len(idxs) == 0: continue
        
        cluster_prices = np.array([valid_data[i].cuantia for i in idxs], dtype=float)
        
        # Guardamos para global
        all_prices.extend(cluster_prices)
        
        # Stats
        bounds = _calculate_bounds(cluster_prices, significance_alpha)
        
        # Representative text 
        example_idx = idxs[0]
        example_obj = valid_data[example_idx].objeto or valid_data[example_idx].best_chunk_text[:100]
        
        clusters_info.append({
            "cluster_id": int(k),
            "count": int(len(idxs)),
            "example_topic": example_obj,
            "stats": bounds
        })

    # Sort clusters by count desc
    clusters_info.sort(key=lambda x: x['count'], reverse=True)

    # 5. Global Stats
    global_bounds = _calculate_bounds(np.array(all_prices, dtype=float), significance_alpha)

    return MarketRangeResult(
        nit=nit_empresa,
        total_matches=len(matches),
        used_matches=len(valid_data),
        num_clusters=real_k,
        cluster_stats=clusters_info,
        global_range=global_bounds
    )
