from __future__ import annotations
from typing import Iterable, Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.licitacion import PublicLicitacion
from app.schemas.licitacion import LicitacionCreate

class LicitacionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, lic_in: LicitacionCreate) -> PublicLicitacion:
        db_obj = PublicLicitacion(**lic_in.model_dump())
        self.session.add(db_obj)
        self.session.flush()
        return db_obj

    def search(self, q: str, limit: int = 50) -> List[PublicLicitacion]:
        stmt = (
            select(PublicLicitacion)
            .where(
                (PublicLicitacion.entidad.ilike(f"%{q}%"))
                | (PublicLicitacion.objeto.ilike(f"%{q}%"))
                | (PublicLicitacion.descripcion_general.ilike(f"%{q}%"))
            )
            .order_by(func.coalesce(PublicLicitacion.fecha_public, func.current_date()).desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id(self, id: int) -> Optional[PublicLicitacion]:
        return self.session.get(PublicLicitacion, id)

# Funciones de Flags comentadas por incompatibilidad con nuevo esquema
# def ensure_flag_by_codigo(...)
# def set_flag_for_licitacion(...)
