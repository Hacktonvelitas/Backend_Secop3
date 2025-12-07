from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.empresa import EmpresaInfo, EmpresaDocumentos, Companies
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate

class EmpresaRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_nit(self, nit: str) -> Optional[EmpresaInfo]:
        return self.session.get(EmpresaInfo, nit)

    def create(self, empresa_in: EmpresaCreate) -> EmpresaInfo:
        db_obj = EmpresaInfo(**empresa_in.model_dump())
        self.session.add(db_obj)
        self.session.flush()
        return db_obj

    def update(self, db_obj: EmpresaInfo, empresa_in: EmpresaUpdate) -> EmpresaInfo:
        update_data = empresa_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.session.add(db_obj)
        self.session.flush()
        return db_obj

    def get_vector_data(self, nit: str) -> Optional[Companies]:
        stmt = select(Companies).where(Companies.nit == nit)
        return self.session.execute(stmt).scalars().first()
