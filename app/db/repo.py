# app/db/repo.py
from typing import Optional, List, Iterable
from datetime import date

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

try:
    from app.db.schema import PublicLicitacion, EmpresaInfo
except ModuleNotFoundError:
    # Fallback if running relative
    try:
        from db.schema import PublicLicitacion, EmpresaInfo
    except ModuleNotFoundError:
        pass # Schema import handled

# ==============
# LICITACIONES
# ==============

def create_licitacion(
    session: Session,
    entidad: str,
    objeto: Optional[str] = None,
    cuantia: Optional[float] = None,
    modalidad: Optional[str] = None,
    codigo_proceso: Optional[str] = None, 
    estado: Optional[str] = None,
    fecha_public=None,
    ubicacion: Optional[str] = None,
    act_econ: Optional[str] = None,
    enlace: Optional[str] = None,
) -> PublicLicitacion:
    lic = PublicLicitacion(
        entidad=entidad,
        objeto=objeto,
        cuantia=cuantia,
        modalidad=modalidad,
        codigo_proceso=codigo_proceso,
        estado=estado,
        fecha_public=fecha_public,
        ubicacion=ubicacion,
        act_econ=act_econ,
        enlace=enlace,
    )
    session.add(lic)
    session.flush()
    return lic

def search_licitaciones(session: Session, q: str, limit: int = 50) -> Iterable[PublicLicitacion]:
    stmt = (
        select(PublicLicitacion)
        .where(
            (PublicLicitacion.entidad.ilike(f"%{q}%"))
            | (PublicLicitacion.objeto.ilike(f"%{q}%"))
        )
        .order_by(func.coalesce(PublicLicitacion.fecha_public, func.current_date()).desc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()

# ==============
# EMPRESA (INFO)
# ==============

def get_empresa_by_nit(session: Session, nit: str) -> Optional[EmpresaInfo]:
    return session.scalar(select(EmpresaInfo).where(EmpresaInfo.nit == nit))

def create_or_update_empresa(
    session: Session,
    nit: str,
    razon_social: str,
    email_contacto: Optional[str] = None,
    pais: str = "Colombia",
) -> EmpresaInfo:
    emp = get_empresa_by_nit(session, nit)
    if not emp:
        emp = EmpresaInfo(
            nit=nit, 
            razon_social=razon_social,
            correo_contacto=email_contacto,
            pais=pais
        )
        session.add(emp)
    else:
        emp.razon_social = razon_social
        if email_contacto:
            emp.correo_contacto = email_contacto
    
    session.flush()
    return emp
