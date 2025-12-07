from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.empresa import Empresa, EmpresaDocumentos, Companies
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate

class EmpresaRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_nit(self, nit: str) -> Optional[Empresa]:
        return self.session.get(Empresa, nit)

    def create(self, empresa_in: EmpresaCreate) -> Empresa:
        db_obj = Empresa(**empresa_in.model_dump())
        self.session.add(db_obj)
        self.session.flush()
        return db_obj

    def update(self, db_obj: Empresa, empresa_in: EmpresaUpdate) -> Empresa:
        update_data = empresa_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.session.add(db_obj)
        self.session.flush()
        return db_obj

    def get_vector_data(self, nit: str) -> Optional[Companies]:
        return self.session.get(Companies, nit)
