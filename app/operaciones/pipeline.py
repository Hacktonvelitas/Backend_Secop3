# app/operaciones/pipeline.py
from __future__ import annotations
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

# Importamos los nuevos modulos de matching
import operaciones.match_inicial as match_i
import operaciones.match_augmented as match_a

# Mantenemos imports legacy si están disponibles, sino ignora
try:
    from .precios_IQ import run_flag_precio_for_one as _run_precio_one
    HAS_PRECIO = True
except Exception:
    HAS_PRECIO = False


def get_computable_flows() -> List[str]:
    """
    Flujos disponibles. Flags legacy pueden seguir o quitarse.
    Agregamos 'match_augmented' como un flujo ejecutable si se desea.
    """
    base: List[str] = []
    if HAS_PRECIO:
        base.append("red_precio")
    
    # Podemos agregar 'match_checker' si quisieras correr validaciones, 
    # pero match es generalmente "Company -> Licitaciones", no "Licitacion -> Check".
    # El pipeline original estaba diseñado para "Valida esta Licitacion".
    # Por ahora lo dejamos simple.
    return base

def get_interactive_flows() -> List[str]:
    return ["red_contactos", "match_augmented"]

def get_available_flows() -> List[str]:
    return get_computable_flows() + get_interactive_flows() + ["all"]


def _run_one_flow(db: Session, lic_id: int, flow: str, json_override: Optional[dict]) -> dict:
    
    # Match Augmented via pipeline
    if flow == "match_augmented":
        # Este flujo es "raro" para una licitación individual, 
        # porque match_augmented es "Empresa -> Lista de Lics".
        # Si se corre para UNA licitación, ¿qué significa?
        # ¿"Esta licitación hace match con la empresa X"?
        # Asumiremos que el payload trae 'nit_empresa' y validamos si esta lic_id sale en el top.
        
        nit = json_override.get('nit_empresa') if json_override else None
        if not nit:
            return {"flow": "match_augmented", "ok": False, "error": "nit_empresa required in json_override"}
        
        # Corremos match augmented
        results = match_a.obtener_match_augmented(db, nit_empresa=nit)
        
        # Verificamos si lic_id esta en results
        match_data = next((r for r in results if r['licitacion_id'] == lic_id), None)
        
        return {
            "flow": "match_augmented",
            "result": {
                "matched": bool(match_data),
                "data": match_data
            }
        }

    # Computables Legacy:
    if flow == "red_precio" and HAS_PRECIO:
        res = _run_precio_one(db, lic_id)
        return {
            "flow": "red_precio",
            "result": {
                "ok": True,
                "flag_applied": (res.target_cuantia is not None) and (
                    res.target_cuantia < res.stats.lower
                    or res.target_cuantia > res.stats.upper
                    or abs(res.stats.z_mad) >= 2.8
                ),
                "detail": {
                    "method": res.method,
                    "n_comparables": res.n_comparables,
                    "median": res.stats.median,
                    "z_mad": res.stats.z_mad,
                    "neighbors": res.neighbor_ids,
                },
            },
        }

    return {"flow": flow, "status": "skipped_or_unknown"}


def run_flow_for_one(
    db: Session,
    licitacion_id: int,
    flow: str = "all",
    json_override: Optional[dict] = None,
) -> dict:
    if flow == "all":
        flows = get_computable_flows()
    else:
        flows = [flow]

    applied = [_run_one_flow(db, licitacion_id, f, json_override) for f in flows]
    
    db.commit()

    return {"licitacion_id": licitacion_id, "applied": applied}


def run_flow_batch(
    db: Session,
    ksflow: str = "all",
    lic_ids: Optional[List[int]] = None,
    where_clause: Optional[str] = None,
    limit: Optional[int] = None,
    json_override: Optional[dict] = None,
) -> List[dict]:
    
    # Cursor de IDs si no vienen dados (solo para computables)
    if lic_ids is None:
        # Ajuste para nuevo schema: tabla public_licitacion
        sql = "SELECT id FROM public.public_licitacion"
        if where_clause:
            sql += f" WHERE {where_clause}"
        sql += " ORDER BY id"
        if limit:
            sql += f" LIMIT {int(limit)}"
        lic_ids = [r[0] for r in db.execute(text(sql)).fetchall()]

    out = []
    for lid in lic_ids:
        out.append(run_flow_for_one(db, lid, flow=ksflow, json_override=json_override))
    return out
