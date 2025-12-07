from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.pipeline_service import PipelineService

router = APIRouter()

class BatchRequest(BaseModel):
    flow: str = "all"
    where: Optional[str] = None
    limit: Optional[int] = None

@router.get("/flows", response_model=List[str])
def list_flows(db: Session = Depends(get_db)):
    service = PipelineService(db)
    return service.get_available_flows()


@router.post("/run/{licitacion_id}", response_model=dict)
def run_pipeline_one(
    licitacion_id: int,
    flow: str = Query(default="all"),
    db: Session = Depends(get_db),
):
    service = PipelineService(db)
    try:
        return service.run_flow_for_one(licitacion_id, flow=flow)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch", response_model=List[dict])
def run_pipeline_batch_ep(
    payload: BatchRequest = Body(...),
    db: Session = Depends(get_db),
):
    service = PipelineService(db)
    try:
        return service.run_flow_batch(
            ksflow=payload.flow,
            where_clause=payload.where,
            limit=payload.limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
