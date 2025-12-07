from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.empresa_repo import EmpresaRepository
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate
from app.models.empresa import Empresa

class EmpresaService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = EmpresaRepository(session)

    def get_empresa(self, nit: str) -> Optional[Empresa]:
        return self.repo.get_by_nit(nit)

    def create_empresa(self, empresa_in: EmpresaCreate) -> Empresa:
        # Check if exists
        if self.repo.get_by_nit(empresa_in.nit):
            raise ValueError("Empresa already exists")
        
        empresa = self.repo.create(empresa_in)
        self.session.commit()
        return empresa

    def update_empresa(self, nit: str, empresa_in: EmpresaUpdate) -> Empresa:
        empresa = self.repo.get_by_nit(nit)
        if not empresa:
            raise ValueError("Empresa not found")
        
        updated = self.repo.update(empresa, empresa_in)
        self.session.commit()
        return updated
