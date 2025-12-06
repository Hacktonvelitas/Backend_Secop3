from __future__ import annotations

from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.init_db import get_db
from db import repo
# Import updated schema classes
from db.schema import PublicLicitacion, Empresa, PublicLicitacionChunk
from operaciones.pipeline import get_available_flows, run_flow_for_one, run_flow_batch
# Import Matching Logic
import operaciones.match_inicial as match_i
import operaciones.match_augmented as match_a
from ai_router import router as ai_router

api = FastAPI(title="Licita API", version="1.0.0")


api.include_router(ai_router)


@api.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@api.get("/")
def index():
    return {
        "name": "Licita API",
        "endpoints": [
            "/health",
            "/licitaciones/search",
            "/licitaciones",
            "/match/inicial",
            "/match/augmented",
            "/pipelines/flows",
            "/pipelines/run/{licitacion_id}",
            "/pipelines/batch",
            "/ai/query",
            "/ai/graphs/assistant",
        ],
    }


# --------- Schemas ----------

class LicitacionIn(BaseModel):
    entidad: str
    objeto: Optional[str] = None
    cuantia: Optional[float] = None
    modalidad: Optional[str] = None
    numero: Optional[str] = None
    # Add other fields if necessary for creating licitaciones
    fecha_public: Optional[date] = None


class MatchRequest(BaseModel):
    nit_empresa: str
    fecha_inicio: Optional[date] = None
    top_k: int = 20
    min_score: float = 0.5


class MatchAugmentedRequest(BaseModel):
    nit_empresa: str
    etiquetas_override: Optional[List[str]] = None
    fecha_inicio: Optional[date] = None
    top_k: int = 50 
    final_k: int = 20


# --------- Rutas básicas ----------

@api.post("/licitaciones", response_model=dict)
def create(lic_in: LicitacionIn, db: Session = Depends(get_db)):
    # Note: repo.create_licitacion might need update if it uses old Licitacion class
    # Assumed repo is compatible or we fix it if errors arise.
    # For now, simplistic creation:
    lic = repo.create_licitacion(db, **lic_in.model_dump())
    db.commit()
    return {"id": lic.id}


@api.get("/licitaciones/search", response_model=List[dict])
def search(q: str, limit: int = 50, db: Session = Depends(get_db)):
    rows = repo.search_licitaciones(db, q=q, limit=limit)
    return [
        {
            "id": x.id,
            "entidad": x.entidad,
            "estado": x.estado,
            "fecha_public": x.fecha_public,
            "cuantia": float(x.cuantia) if x.cuantia is not None else None,
        }
        for x in rows
    ]


# --------- Rutas Match (Nuevas) ----------

@api.post("/match/inicial", response_model=List[dict])
def run_match_inicial(
    payload: MatchRequest, 
    db: Session = Depends(get_db)
):
    """
    Ejecuta el matching básico basado en vectores.
    """
    results = match_i.obtener_oportunidades_empresa(
        session=db,
        nit_empresa=payload.nit_empresa,
        fecha_inicio=payload.fecha_inicio,
        top_k=payload.top_k,
        min_score=payload.min_score
    )
    return [r.to_dict() for r in results]


@api.post("/match/augmented", response_model=List[dict])
def run_match_augmented(
    payload: MatchAugmentedRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta matching aumentando score con etiquetas (tags) de la empresa.
    """
    results = match_a.obtener_match_augmented(
        session=db,
        nit_empresa=payload.nit_empresa,
        etiquetas_override=payload.etiquetas_override,
        fecha_inicio=payload.fecha_inicio,
        top_k=payload.top_k,
        final_k=payload.final_k
    )
    return results


# --------- Orquestador (Legacy / Pipeline) ----------

class BatchRequest(BaseModel):
    flow: str = "all"
    where: Optional[str] = None
    limit: Optional[int] = None


@api.get("/pipelines/flows", response_model=List[str])
def list_flows():
    return get_available_flows()


@api.post("/pipelines/run/{licitacion_id}", response_model=dict)
def run_pipeline_one(
    licitacion_id: int,
    flow: str = Query(default="all"),
    db: Session = Depends(get_db),
):
    try:
        return run_flow_for_one(db, licitacion_id, flow=flow)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/pipelines/batch", response_model=List[dict])
def run_pipeline_batch_ep(
    payload: BatchRequest = Body(...),
    db: Session = Depends(get_db),
):
    try:
        return run_flow_batch(
            db,
            ksflow=payload.flow,
            where_clause=payload.where,
            limit=payload.limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
