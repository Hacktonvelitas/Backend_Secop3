# app/operaciones/pipeline.py
from __future__ import annotations
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

# Importamos los nuevos modulos de matching
import app.operaciones.match_inicial as match_i
import app.operaciones.match_augmented as match_a

# Precios IQ (Legacy flag check removed, new logic is company-centric)
# We won't import the old function since it doesn't exist.
HAS_PRECIO = False


def get_computable_flows() -> List[str]:
    """
    Flujos disponibles.
    """
    base: List[str] = []
    # if HAS_PRECIO: base.append("red_precio")
    return base

def get_interactive_flows() -> List[str]:
    return ["match_augmented"]

def get_available_flows() -> List[str]:
    return get_computable_flows() + get_interactive_flows() + ["all"]


def _run_one_flow(db: Session, lic_id: int, flow: str, json_override: Optional[dict]) -> dict:
    
    # Match Augmented via pipeline
    if flow == "match_augmented":
        # Estrategia: "Check if this Lic ID matches specific Company"
        # Requires 'nit_empresa' in json_override
        
        nit = json_override.get('nit_empresa') if json_override else None
        if not nit:
            return {"flow": "match_augmented", "ok": False, "error": "nit_empresa required in json_override"}
        
        # Corremos match augmented (Top K)
        # Note: This is expensive if we just want to check ONE licitacion. 
        # But our current logic is "Get Top K for Company". 
        # Ideally we should have "Score Pair (Company, Lic)" function.
        # We will use the existing function and check if ID is present.
        
        results = match_a.obtener_match_augmented(db, nit_empresa=nit, top_k=50)
        
        # results is List[AugmentedMatchResult]
        # Check if lic_id is in the results
        match_obj = next((r for r in results if r.base_match.licitacion_id == lic_id), None)
        
        if match_obj:
            data_dict = {
                "licitacion_id": match_obj.base_match.licitacion_id,
                "final_score": match_obj.final_score,
                "ai_explanation": match_obj.ai_explanation,
                "cumple_requisitos": match_obj.cumple_requisitos
            }
        else:
            data_dict = None

        return {
            "flow": "match_augmented",
            "result": {
                "matched": bool(match_obj),
                "data": data_dict
            }
        }

    return {"flow": flow, "status": "skipped_or_unknown"}


def run_flow_for_one(
    db: Session,
    licitacion_id: int,
    flow: str = "all",
    json_override: Optional[dict] = None,
) -> dict:
    if flow == "all":
        flows = get_interactive_flows() # Only run interactive ones if requested implicitly? Usually 'all' runs computables.
        # But we have no computables now.
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
    
    if lic_ids is None:
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
