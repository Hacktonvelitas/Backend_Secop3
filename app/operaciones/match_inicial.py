# app/operaciones/match_inicial.py
from __future__ import annotations

import logging
import sys
import numpy as np
from typing import List, Optional, Tuple, Dict
from datetime import date
from dataclasses import dataclass, asdict

from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sklearn.cluster import KMeans

# ============================================================
# LOGGING
# ============================================================
LOGGER = logging.getLogger("match_empresa")
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[match_empresa] %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel("INFO")

# ============================================================
# Helpers
# ============================================================

def _to_np_vec(v) -> Optional[np.ndarray]:
    """Convierte input (String, Bytes, List, o MemoryView) a Numpy Float32"""
    if v is None: return None
    
    # Caso: Ya es una lista (si usas pgvector-python driver)
    if isinstance(v, list):
        return np.array(v, dtype=np.float32)

    # Caso: MemoryView o Bytes
    if isinstance(v, memoryview): v = v.tobytes()
    if isinstance(v, (bytes, bytearray)):
        try:
            arr = np.frombuffer(v, dtype=np.float32)
            if arr.size > 0:
                arr = np.nan_to_num(arr)
            return arr if arr.size > 0 else None
        except: pass

    # Caso: String "[0.1, 0.2, ...]"
    if isinstance(v, str):
        s = v.strip().lstrip("{[").rstrip("}]")
        try:
            nums = [float(x) for x in s.split(",") if x.strip()]
            return np.nan_to_num(np.array(nums, dtype=np.float32))
        except: return None
        
    try:
        arr = np.asarray(v, dtype=np.float32)
        return np.nan_to_num(arr) if arr.size > 0 else None
    except: return None

def _l2_normalize(x: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(x))
    if n == 0.0: return x
    return x / n

# ============================================================
# Estructuras de Salida (DTOs)
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
    vector_licitacion: Optional[np.ndarray] = None # Added for Augmented Match

    def to_dict(self):
        # Excluir vector de la salida dict para no ensuciar JSONs
        d = asdict(self)
        if 'vector_licitacion' in d:
             del d['vector_licitacion']
        return d

# ============================================================
# Consultas SQL
# ============================================================

def _fetch_empresa_vector(session: Session, nit: str) -> Optional[np.ndarray]:
    """Busca el vector de la empresa por NIT."""
    # Nota: Asegúrate que el NIT venga saneado
    clean_nit = nit.replace("-", "").replace(" ", "")
    
    # En nuevo schema: public.empresa.razon_social_vec
    row = session.execute(text("""
        SELECT razon_social_vec
        FROM public.empresa
        WHERE nit = :nit
    """), {"nit": clean_nit}).fetchone()

    if not row or row[0] is None:
        LOGGER.warning(f"Empresa NIT {clean_nit} no encontrada o sin vector (razon_social_vec).")
        return None
    
    vec = _to_np_vec(row[0])
    return _l2_normalize(vec) if vec is not None else None

def _fetch_licitacion_chunks_filtered(
    session: Session, 
    fecha_inicio: Optional[date] = None, 
    limit: int = 10000
) -> List[Tuple]:
    """
    Trae chunks con filtro opcional de fecha.
    Schema nuevo: public_licitacion_chunk joined with public_licitacion
    """
    msg_fecha = f"desde {fecha_inicio}" if fecha_inicio else "todo el histórico"
    LOGGER.info(f"Cargando chunks ({msg_fecha}). Límite: {limit}...")
    
    params = {"limit": limit}
    where_clauses = ["c.embedding_vec IS NOT NULL"]
    
    if fecha_inicio:
        where_clauses.append("l.fecha_public >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio

    sql = f"""
        SELECT 
            c.licitacion_id,
            c.chunk_text,
            c.embedding_vec,
            l.entidad,
            l.objeto,
            l.cuantia,
            l.fecha_public
        FROM public.public_licitacion_chunk c
        JOIN public.public_licitacion l ON c.licitacion_id = l.id
        WHERE {" AND ".join(where_clauses)}
        LIMIT :limit
    """
    
    rows = session.execute(text(sql), params).fetchall()
    
    parsed_data = []
    for lid, txt, v_raw, ent, obj, cuant, fecha in rows:
        vec = _to_np_vec(v_raw)
        if vec is not None:
            # Normalizamos aquí para ahorrar cómputo en el loop principal
            parsed_data.append((lid, txt, _l2_normalize(vec), ent, obj, cuant, fecha))
            
    LOGGER.info(f"Chunks cargados en memoria: {len(parsed_data)}")
    return parsed_data

# ============================================================
# Función Principal (Entry Point para Router)
# ============================================================

def obtener_oportunidades_empresa(
    session: Session, 
    nit_empresa: str, 
    fecha_inicio: Optional[date] = None,
    top_k: int = 20, 
    min_score: float = 0.5,
    n_clusters: int = 3
) -> List[MatchResult]:
    """
    Función orquestadora para ser llamada desde la API o Match Augmented.
    """
    
    # 1. Vector Empresa
    empresa_vec = _fetch_empresa_vector(session, nit_empresa)
    if empresa_vec is None:
        return []

    # 2. Universo de Licitaciones
    # Ajustar límite según capacidad de instancia
    candidates = _fetch_licitacion_chunks_filtered(session, fecha_inicio, limit=20000)
    
    if not candidates:
        LOGGER.warning("No hay licitaciones para comparar.")
        return []

    # 3. Calcular Matches
    matches_temp = {} 
    
    for lid, txt, lic_vec, ent, obj, cuant, fecha in candidates:
        score = float(np.dot(empresa_vec, lic_vec))
        
        if score >= min_score:
            if lid not in matches_temp or score > matches_temp[lid]['score']:
                matches_temp[lid] = {
                    'score': score,
                    'text': txt,
                    'vec': lic_vec, 
                    'ent': ent,
                    'obj': obj,
                    'cuant': float(cuant) if cuant else 0.0,
                    'fecha': str(fecha) if fecha else None
                }

    # Convertir a objetos MatchResult
    results_list = []
    for lid, data in matches_temp.items():
        results_list.append(MatchResult(
            licitacion_id=lid,
            score=data['score'],
            best_chunk_text=data['text'],
            entidad=data['ent'],
            objeto=data['obj'],
            cuantia=data['cuant'],
            fecha_public=data['fecha'],
            vector_licitacion=data['vec'] # Guardamos vector para augmented
        ))
        
    # Ordenar por score inicial
    results_list.sort(key=lambda x: x.score, reverse=True)
    
    # NOTA: En match_inicial cortamos a top_k, pero si va a llamar a augmented,
    # tal vez queramos pasar más candidatos. Por ahora respetamos top_k.
    # Si augmented necesita más, quien llame a esta función debe aumentar top_k.
    top_results = results_list[:top_k]
    
    LOGGER.info(f"Matches encontrados (inicial): {len(top_results)} (Score >= {min_score})")

    # 4. Clustering (K-Means)
    if top_results and len(top_results) >= n_clusters:
        try:
            vecs_for_clustering = []
            for res in top_results:
                vecs_for_clustering.append(res.vector_licitacion)
            
            X = np.vstack(vecs_for_clustering)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            
            for i, res in enumerate(top_results):
                res.cluster_id = int(labels[i])
        except Exception as e:
            LOGGER.error(f"Error en K-Means: {e}")

    return top_results