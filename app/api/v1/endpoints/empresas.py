from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.empresa import EmpresaCreate, EmpresaOut, EmpresaUpdate
from app.repositories.empresa_repo import EmpresaRepository

router = APIRouter()

@router.get("/", response_model=List[EmpresaOut])
def read_empresas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    repo = EmpresaRepository(db)
    # Assuming repo has a get_multi method, if not we might need to add it or use search
    # For now, let's use a simple query if repo doesn't support it directly
    # But looking at standard repos, they usually have it. 
    # If not, I'll implement a basic list here.
    return repo.session.query(repo.model).offset(skip).limit(limit).all()

from app.services.empresa_service import EmpresaService

@router.post("/", response_model=EmpresaOut)
def create_empresa(
    empresa_in: EmpresaCreate,
    db: Session = Depends(get_db)
):
    service = EmpresaService(db)
    try:
        return service.create_empresa(empresa_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{nit}", response_model=EmpresaOut)
def read_empresa(
    nit: str,
    db: Session = Depends(get_db)
):
    repo = EmpresaRepository(db)
    empresa = repo.get_by_nit(nit)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa not found")
    return empresa

@router.put("/{nit}", response_model=EmpresaOut)
def update_empresa(
    nit: str,
    empresa_in: EmpresaUpdate,
    db: Session = Depends(get_db)
):
    repo = EmpresaRepository(db)
    empresa = repo.get_by_nit(nit)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa not found")
    
    empresa = repo.update(empresa, empresa_in)
    db.commit()
    db.refresh(empresa)
    return empresa
