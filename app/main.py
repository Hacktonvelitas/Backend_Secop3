from __future__ import annotations

from datetime import date
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from fastapi import FastAPI, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

# Updated imports to be relative or app-prefixed if possible, 
# but "db.deps" implies running inside app folder or with PYTHONPATH setup.
# I will use "app.db.deps" to be robust if run from root.
try:
    from app.db.deps import get_db
    from app.db import repo
    from app.operaciones.pipeline import get_available_flows, run_flow_for_one, run_flow_batch
    from app.opp_router import router as opp_router
except ModuleNotFoundError:
    # Fallback to local import if running inside app directory
    from db.deps import get_db
    from db import repo
    from operaciones.pipeline import get_available_flows, run_flow_for_one, run_flow_batch
    from opp_router import router as opp_router

api = FastAPI(title="Licita API", version="1.0.0")

# Include Router
api.include_router(opp_router)


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
            "/pipelines/flows",
            "/pipelines/run/{licitacion_id}",
            "/pipelines/batch",
            # Included via opp_router
            "/opportunities/match/inicial",
            "/opportunities/match/augmented",
            "/opportunities/analisis/precios",
            "/opportunities/ai/query",
            "/opportunities/ai/graphs/assistant",
        ],
    }


# --------- Schemas (Basic) ----------

class LicitacionIn(BaseModel):
    entidad: str
    objeto: Optional[str] = None
    cuantia: Optional[float] = None
    modalidad: Optional[str] = None
    # Changed numero to codigo_proceso to match schema/repo
    codigo_proceso: Optional[str] = None
    fecha_public: Optional[date] = None


# --------- Rutas básicas ----------

@api.post("/licitaciones", response_model=dict)
def create(lic_in: LicitacionIn, db: Session = Depends(get_db)):
    # repo.create_licitacion updated to match args
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
