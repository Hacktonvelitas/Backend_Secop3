from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.licitacion import LicitacionCreate, LicitacionOut, LicitacionUpdate
from app.repositories.licitacion_repo import LicitacionRepository

router = APIRouter()

@router.post("/", response_model=LicitacionOut)
def create_licitacion(lic_in: LicitacionCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva licitación. 
    Para guardar como borrador, envía 'estado': 'BORRADOR' en el body.
    """
    repo = LicitacionRepository(db)
    lic = repo.create(lic_in)
    db.commit()
    db.refresh(lic)
    return lic

@router.get("/search", response_model=List[LicitacionOut])
def search_licitaciones(q: str, limit: int = 50, db: Session = Depends(get_db)):
    repo = LicitacionRepository(db)
    return repo.search(q=q, limit=limit)

@router.get("/{id}", response_model=LicitacionOut)
def get_licitacion(id: int, db: Session = Depends(get_db)):
    repo = LicitacionRepository(db)
    lic = repo.get(id)
    if not lic:
        raise HTTPException(status_code=404, detail="Licitacion not found")
    return lic

@router.put("/{id}", response_model=LicitacionOut)
def update_licitacion(id: int, lic_in: LicitacionUpdate, db: Session = Depends(get_db)):
    repo = LicitacionRepository(db)
    lic = repo.get(id)
    if not lic:
        raise HTTPException(status_code=404, detail="Licitacion not found")
    
    lic = repo.update(lic, lic_in)
    db.commit()
    db.refresh(lic)
    return lic

@router.delete("/{id}")
def delete_licitacion(id: int, db: Session = Depends(get_db)):
    repo = LicitacionRepository(db)
    lic = repo.get(id)
    if not lic:
        raise HTTPException(status_code=404, detail="Licitacion not found")
    
    repo.remove(id)
    db.commit()
    return {"status": "deleted"}
