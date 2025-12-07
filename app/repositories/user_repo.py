from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import Usuario
from app.schemas.user import UserCreate
from app.core.security import hash_password

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, user_in: UserCreate) -> Usuario:
        db_obj = Usuario(
            email=user_in.email,
            nombre_completo=user_in.nombre_completo,
            password_hash=hash_password(user_in.password),
            empresa_nit=user_in.empresa_nit,
            rol=user_in.rol,
            is_active=user_in.is_active
        )
        self.session.add(db_obj)
        self.session.flush()
        return db_obj
