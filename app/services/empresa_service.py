from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.empresa_repo import EmpresaRepository
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate
from app.models.empresa import EmpresaInfo

from app.services.embedding_service import EmbeddingService

class EmpresaService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = EmpresaRepository(session)
        self.embedding_service = EmbeddingService()

    def get_empresa(self, nit: str) -> Optional[EmpresaInfo]:
        return self.repo.get_by_nit(nit)

    def create_empresa(self, empresa_in: EmpresaCreate) -> EmpresaInfo:
        # Check if exists
        if self.repo.get_by_nit(empresa_in.nit):
            raise ValueError("Empresa already exists")
        
        # 1. Create in empresa_info
        empresa = self.repo.create(empresa_in)
        
        # 2. Generate Embedding
        if empresa_in.razon_social:
            embedding = self.embedding_service.generate_embedding(empresa_in.razon_social)
            if embedding:
                # 3. Create in companies (for matching)
                self.repo.create_company_vector(
                    nit=empresa_in.nit,
                    razon_social=empresa_in.razon_social,
                    embedding=embedding
                )

        self.session.commit()
        return empresa

    def update_empresa(self, nit: str, empresa_in: EmpresaUpdate) -> EmpresaInfo:
        empresa = self.repo.get_by_nit(nit)
        if not empresa:
            raise ValueError("Empresa not found")
        
        updated = self.repo.update(empresa, empresa_in)
        self.session.commit()
        return updated
