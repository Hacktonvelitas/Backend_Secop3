# app/operaciones/precios_IQ.py
from __future__ import annotations

import os
import sys
import math
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

import numpy as np
from sqlalchemy import text, select
from sqlalchemy.orm import Session

# Importamos del nuevo schema (ajustar si es necesario para compatibilidad)
from db.schema import PublicLicitacion as Licitacion
from db import repo
import match_inicial as match_i

# ============================================================
# LOGGING
# ============================================================
LOGGER = logging.getLogger("filtro_augmented")
if not LOGGER.handlers:
    # logeamos a stdout para que docker lo muestre
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("[flag_precio] %(levelname)s %(message)s")
    handler.setFormatter(fmt)
    LOGGER.addHandler(handler)

# por defecto INFO, pero puedes subirlo a DEBUG con env
level = os.getenv("FLAG_PRECIO_LOGLEVEL", "INFO").upper()
LOGGER.setLevel(level)

# ============================================================
# Config / Parámetros por defecto
# ============================================================

TOP_K = 50
MIN_NEIGHBORS_FOR_STATS = 10
Z_MAD_THRESHOLD = 2.8

MAX_TARGET_CHUNKS = 128
MAX_CANDIDATES = 5000
MAX_CAND_PER_LIC_CHUNKS = 64

STRICT_FILTER_MODALIDAD = True
STRICT_FILTER_ACT_ECON = True
PENALTY_ESTADO = 0.10  # penalización si cambia 'estado'


# ============================================================
# Helpers básicos
# ============================================================

def _ensure_flag(session: Session) -> None:
    # Nota: La tabla 'flags' ya no existe en el nuevo schema, 
    # esta función podría fallar si se llama. Se mantiene lógica legacy.
    # Si se requiere, se debería crear tabla flags o eliminar esta llamada.
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS flags (
                codigo VARCHAR(50) PRIMARY KEY,
                nombre VARCHAR(255),
                descripcion TEXT
            )
        """))
        session.execute(text("""
            INSERT INTO flags (codigo, nombre, descripcion)
            VALUES (
              'red_precio',
              'Desviación de precio (comparables)',
              'Evalúa si la cuantía está fuera del rango robusto (IQR/zMAD) de comparables similares.'
            )
            ON CONFLICT (codigo) DO UPDATE
              SET nombre = EXCLUDED.nombre,
                  descripcion = EXCLUDED.descripcion
        """))
        session.commit()
    except Exception as e:
        LOGGER.warning(f"No se pudo asegurar flag red_precio (¿tabla flags eliminada?): {e}")


def _to_np_vec(v) -> Optional[np.ndarray]:
    """
    Versión tolerante: acepta memoryview, bytes, texto {..}, listas, ndarray.
    """
    if v is None:
        return None

    # 1) memoryview -> bytes
    if isinstance(v, memoryview):
        v = v.tobytes()

    # 2) bytes -> intentar como float32
    if isinstance(v, (bytes, bytearray)):
        # primero intentamos como buffer binario
        try:
            arr = np.frombuffer(v, dtype=np.float32)
            if arr.ndim == 1 and arr.size > 0:
                arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
                return arr.astype(np.float32, copy=False)
        except Exception:
            # si no, intentamos decodificar a texto
            try:
                v = v.decode("utf-8")
            except Exception:
                return None

    # 3) strings del estilo "{0.1,0.2}" o "[0.1, 0.2]"
    if isinstance(v, str):
        s = v.strip().lstrip("{[").rstrip("}]")
        if not s:
            return None
        try:
            nums = [float(x) for x in s.split(",") if x.strip() != ""]
            if not nums:
                return None
            arr = np.array(nums, dtype=np.float32)
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
            return arr
        except Exception:
            return None

    # 4) array-like normal
    try:
        arr = np.asarray(v, dtype=np.float32)
        if arr.ndim == 1 and arr.size > 0:
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
            return arr
    except Exception:
        return None

    return None


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(x))
    if not np.isfinite(n) or n == 0.0:
        return x.astype(np.float32, copy=False)
    return (x / n).astype(np.float32, copy=False)


def _fmt_money(x: Optional[float]) -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return f"${x:,.0f}".replace(",", ".")


# ============================================================
# Estadística robusta
# ============================================================

@dataclass
class RobustStats:
    median: float
    mad: float
    z_mad: float
    q1: float
    q3: float
    iqr: float
    lower: float
    upper: float
    n: int


def _robust_stats(values: np.ndarray, target: float) -> RobustStats:
    arr = np.asarray(values, dtype=float)
    med = float(np.median(arr)) if arr.size else 0.0
    abs_dev = np.abs(arr - med) if arr.size else np.array([0.0])
    mad = float(np.median(abs_dev))
    z_mad = 0.0 if mad == 0 or not np.isfinite(target) else float(0.6745 * (target - med) / mad)
    q1 = float(np.percentile(arr, 25)) if arr.size else 0.0
    q3 = float(np.percentile(arr, 75)) if arr.size else 0.0
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return RobustStats(med, mad, z_mad, q1, q3, iqr, lower, upper, int(arr.size))


# ============================================================
# Fetch de vectores (con fallback) — versión con LOGS
# ============================================================

def _fetch_target_vec_any(session: Session, lic_id: int) -> Optional[np.ndarray]:
    """
    1) intenta con chunks.embedding_vec (trim)
    2) intenta sin trim
    3) fallback a licitacion.objeto_vec
    """
    lid_txt = str(lic_id)
    LOGGER.info(f"[target] lic_id={lic_id} → buscando chunks...")

    # 1) con TRIM
    # Adaptado a nueva tabla public_licitacion_chunk
    rows = session.execute(text("""
        SELECT embedding_vec
        FROM public.public_licitacion_chunk
        WHERE licitacion_id = :lid
          AND embedding_vec IS NOT NULL
        ORDER BY
          chunk_idx
        LIMIT :m
    """), {"lid": lic_id, "m": MAX_TARGET_CHUNKS}).fetchall()

    vecs: List[np.ndarray] = []
    for (raw_vec,) in rows:
        nv = _to_np_vec(raw_vec)
        if nv is not None and nv.size > 0:
            vecs.append(_l2_normalize(nv))

    if vecs:
        LOGGER.info(f"[target] lic_id={lic_id} → chunks OK (n={len(vecs)})")
        mean = np.vstack(vecs).mean(axis=0)
        return _l2_normalize(mean)

    # 2) fallback a objeto_vec
    row = session.execute(text("""
        SELECT objeto_vec
        FROM public.public_licitacion
        WHERE id = :id AND objeto_vec IS NOT NULL
    """), {"id": lic_id}).fetchone()

    if row and row[0] is not None:
        nv = _to_np_vec(row[0])
        if nv is not None and nv.size > 0:
            LOGGER.info(f"[target] lic_id={lic_id} → usando objeto_vec (fallback).")
            return _l2_normalize(nv)

    LOGGER.warning(f"[target] lic_id={lic_id} → SIN vector (ni chunks ni objeto_vec).")
    return None


def _fetch_target_meta(session: Session, lic_id: int) -> Dict:
    row = session.execute(text("""
        SELECT modalidad, act_econ, estado, cuantia
        FROM public.public_licitacion WHERE id = :id
    """), {"id": lic_id}).fetchone()
    if not row:
        return {}
    return {
        "modalidad": row[0],
        "act_econ": row[1],
        "estado": row[2],
        "cuantia": float(row[3]) if row[3] is not None else None,
    }


def _fetch_candidate_headers(session: Session, lic_id: int, filt: Dict) -> List[Tuple[int, Optional[str], Optional[str], Optional[str], Optional[float]]]:
    where = ["id <> :id"]
    params = {"id": lic_id, "lim": MAX_CANDIDATES}
    if STRICT_FILTER_MODALIDAD and filt.get("modalidad"):
        where.append("modalidad = :mod")
        params["mod"] = filt["modalidad"]
    if STRICT_FILTER_ACT_ECON and filt.get("act_econ"):
        where.append("act_econ = :act")
        params["act"] = filt["act_econ"]

    sql = f"""
        SELECT id, modalidad, act_econ, estado, cuantia
        FROM public.public_licitacion
        WHERE {" AND ".join(where)}
        ORDER BY id
        LIMIT :lim
    """
    rows = session.execute(text(sql), params).fetchall()
    LOGGER.info(f"[cands] lic_id={lic_id} → candidatos SQL={len(rows)}")
    return rows


def _fetch_candidate_docvecs(session: Session, cand_ids: List[int]) -> Dict[int, np.ndarray]:
    if not cand_ids:
        return {}

    # ids_txt = [str(x) for x in cand_ids] # Ya son ints en DB

    rows = session.execute(text("""
        SELECT
            c.licitacion_id,
            c.embedding_vec,
            ROW_NUMBER() OVER (
                PARTITION BY c.licitacion_id
                ORDER BY c.chunk_idx
            ) AS rn
        FROM public.public_licitacion_chunk c
        WHERE c.licitacion_id = ANY(:ids)
          AND c.embedding_vec IS NOT NULL
    """), {"ids": cand_ids}).fetchall()

    buckets: Dict[int, List[np.ndarray]] = {}
    for lic_id, v, rn in rows:
        if rn > MAX_CAND_PER_LIC_CHUNKS:
            continue
        nv = _to_np_vec(v)
        if nv is None:
            continue
        buckets.setdefault(lic_id, []).append(_l2_normalize(nv))

    out: Dict[int, np.ndarray] = {}
    for lid, vecs in buckets.items():
        if vecs:
            mean = np.vstack(vecs).mean(axis=0)
            out[lid] = _l2_normalize(mean)

    # fallback con objeto_vec
    missing = [cid for cid in cand_ids if cid not in out]
    if missing:
        rows2 = session.execute(text("""
            SELECT id, objeto_vec
            FROM public.public_licitacion
            WHERE id = ANY(:ids) AND objeto_vec IS NOT NULL
        """), {"ids": missing}).fetchall()
        for cid, ov in rows2:
            nv = _to_np_vec(ov)
            if nv is not None:
                out[int(cid)] = _l2_normalize(nv)

    LOGGER.info(f"[cands_vecs] → con vector={len(out)} / solicitados={len(cand_ids)}")
    return out


# ============================================================
# Cosine + penalizaciones
# ============================================================

def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - float(np.dot(_l2_normalize(a), _l2_normalize(b))))


def _penalty(meta_t: Dict, meta_c: Tuple[int, Optional[str], Optional[str], Optional[str], Optional[float]]) -> float:
    _, _, _, est, _ = meta_c
    p = 0.0
    if meta_t.get("estado") and est and str(meta_t["estado"]).strip() != str(est).strip():
        p += PENALTY_ESTADO
    return p


# ============================================================
# Resultado
# ============================================================

@dataclass
class FlagPrecioResult:
    licitacion_id: int
    n_comparables: int
    method: str
    stats: RobustStats
    target_cuantia: Optional[float]
    neighbor_ids: List[int]

# ============================================================
# API principal (Legacy)
# ============================================================

def run_flag_precio_for_one(
    session: Session,
    licitacion_id: int,
    top_k: int = TOP_K,
    min_neighbors: int = MIN_NEIGHBORS_FOR_STATS,
    penalty_estado: float = PENALTY_ESTADO,
) -> FlagPrecioResult:
    global PENALTY_ESTADO
    PENALTY_ESTADO = penalty_estado

    LOGGER.info(f"=== FLAG PRECIO (LEGACY) → licitacion_id={licitacion_id} ===")

    target: Licitacion | None = session.get(Licitacion, licitacion_id)
    if not target:
        raise ValueError(f"Licitación {licitacion_id} no existe")

    # _ensure_flag(session)

    # 1) vector del target
    t_vec = _fetch_target_vec_any(session, licitacion_id)
    t_meta = _fetch_target_meta(session, licitacion_id)
    t_cuantia = t_meta.get("cuantia")

    if t_vec is None:
        LOGGER.warning(f"[{licitacion_id}] → sin vector final.")
        empty = RobustStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
        return FlagPrecioResult(licitacion_id, 0, "skip", empty, t_cuantia, [])

    # 2) candidatas
    cands = _fetch_candidate_headers(session, licitacion_id, t_meta)
    cand_ids = [int(r[0]) for r in cands]
    cand_vecs = _fetch_candidate_docvecs(session, cand_ids)

    scored: List[Tuple[int, float, Optional[float]]] = []
    for tup in cands:
        cid = int(tup[0])
        c_vec = cand_vecs.get(cid)
        if c_vec is None:
            continue
        d = _cosine_distance(t_vec, c_vec)
        s = d + _penalty(t_meta, tup)
        cuant = float(tup[4]) if tup[4] is not None else float("nan")
        scored.append((cid, s, cuant))

    scored.sort(key=lambda x: x[1])
    top = scored[:max(top_k, min_neighbors)]

    vec_cuantias = np.array([x[2] for x in top], dtype=float)
    mask = ~np.isnan(vec_cuantias)
    vec_cuantias = vec_cuantias[mask]
    vec_ids = [int(top[i][0]) for i in range(len(top)) if mask[i]]

    if vec_cuantias.size < min_neighbors:
        LOGGER.warning(f"[{licitacion_id}] → solo {vec_cuantias.size} vecinos con cuantía")
        empty = RobustStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
        return FlagPrecioResult(licitacion_id, int(vec_cuantias.size), "vec_fallback", empty, t_cuantia, vec_ids)

    stats = _robust_stats(vec_cuantias, t_cuantia if t_cuantia is not None else math.nan)
    LOGGER.info(
        f"[{licitacion_id}] → stats: med={stats.median:.2f} zMAD={stats.z_mad:.2f}"
    )

    return FlagPrecioResult(
        licitacion_id=licitacion_id,
        n_comparables=int(vec_cuantias.size),
        method="vec_fallback",
        stats=stats,
        target_cuantia=t_cuantia,
        neighbor_ids=vec_ids,
    )
