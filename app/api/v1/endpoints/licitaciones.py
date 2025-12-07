from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.licitacion import LicitacionCreate, LicitacionOut
from app.repositories.licitacion_repo import LicitacionRepository

router = APIRouter()

@router.post("/", response_model=LicitacionOut)
def create_licitacion(lic_in: LicitacionCreate, db: Session = Depends(get_db)):
    repo = LicitacionRepository(db)
    lic = repo.create(lic_in)
    db.commit()
    db.refresh(lic)
    return lic

@router.get("/search", response_model=List[LicitacionOut])
def search_licitaciones(q: str, limit: int = 50, db: Session = Depends(get_db)):
    repo = LicitacionRepository(db)
    return repo.search(q=q, limit=limit)
